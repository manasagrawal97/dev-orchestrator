from __future__ import annotations

import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from .approvals import DevoApprovalStatus, load_approval_ledger
from .projects import get_workspace_root
from .runs import load_run, run_path
from .schemas import ValidationCommand, ValidationRunRecord, ValidationRunStatus, ValidationRiskLevel
from .validation_registry import check_validation_command, get_validation_command

VALIDATION_RUN_SCHEMA_VERSION = "1"
VALIDATION_RUNS_DIR = "validation-runs"
MAX_TERMINAL_OUTPUT_CHARS = 4000
MAX_REPORT_OUTPUT_CHARS = 120_000


class ValidationRunResult:
    def __init__(self, record: ValidationRunRecord, artifact_dir: Path, stdout_text: str = "", stderr_text: str = "") -> None:
        self.record = record
        self.artifact_dir = artifact_dir
        self.stdout_text = stdout_text
        self.stderr_text = stderr_text


def run_validation_command(
    project_name: str,
    command_id: str,
    run_id: str | None = None,
    task_id: str | None = None,
    dry_run: bool = False,
    timeout_seconds: int = 300,
    allow_disabled: bool = False,
    require_approval: bool | None = None,
    write_report: bool = True,
    workspace_root: Path | None = None,
) -> ValidationRunResult:
    root = workspace_root or get_workspace_root()
    if timeout_seconds <= 0:
        msg = "Validation timeout must be greater than zero."
        raise ValueError(msg)
    if run_id:
        load_run(project_name, run_id, workspace_root=root)

    command = get_validation_command(project_name, command_id, workspace_root=root)
    working_dir = Path(command.working_dir) if command.working_dir else None
    if not working_dir or not working_dir.exists() or not working_dir.is_dir():
        msg = f"Validation command working directory does not exist: {working_dir}"
        raise ValueError(msg)

    started_at = datetime.now(UTC)
    validation_run_id = _validation_run_id(command.id, started_at)
    artifact_dir = _artifact_dir(root, project_name, validation_run_id, run_id)
    check = check_validation_command(project_name, command.id, workspace_root=root)
    safety_block = _safety_block_reason(command.command)
    approval_required = require_approval if require_approval is not None else command.approval_required or check.approval_required
    approval_id: str | None = None
    blocked_reason: str | None = None
    status = ValidationRunStatus.DRY_RUN if dry_run else ValidationRunStatus.ERROR
    exit_code: int | None = None
    stdout_text = ""
    stderr_text = ""

    policy_reasons = list(check.reasons)
    if safety_block:
        blocked_reason = safety_block
        policy_reasons.append(safety_block)
        status = ValidationRunStatus.BLOCKED
    elif check.blocked or command.risk_level == ValidationRiskLevel.CRITICAL:
        blocked_reason = "Critical-risk validation commands are blocked."
        status = ValidationRunStatus.BLOCKED
    elif dry_run:
        status = ValidationRunStatus.DRY_RUN
        if not command.enabled:
            policy_reasons.append("Dry run only: command is disabled and would be blocked without --allow-disabled.")
        if approval_required:
            policy_reasons.append("Dry run only: approval would be required before execution.")
    elif not command.enabled and not allow_disabled:
        blocked_reason = "Validation command is disabled. Re-run with --allow-disabled only after policy/approval checks pass."
        status = ValidationRunStatus.BLOCKED
    elif approval_required:
        approval_id = _find_validation_approval(root, project_name, run_id, task_id, command)
        if not approval_id:
            blocked_reason = _approval_block_reason(project_name, run_id, task_id, command)
            status = ValidationRunStatus.BLOCKED
    if not dry_run and not blocked_reason and status != ValidationRunStatus.BLOCKED:
        argv = _parse_command(command.command)
        try:
            completed = subprocess.run(
                argv,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                env=None,
            )
            stdout_text = completed.stdout or ""
            stderr_text = completed.stderr or ""
            exit_code = completed.returncode
            status = ValidationRunStatus.PASSED if completed.returncode == 0 else ValidationRunStatus.FAILED
        except subprocess.TimeoutExpired as exc:
            stdout_text = _decode_timeout_output(exc.stdout)
            stderr_text = _decode_timeout_output(exc.stderr)
            exit_code = None
            status = ValidationRunStatus.TIMED_OUT
            blocked_reason = f"Validation command timed out after {timeout_seconds} seconds."
        except OSError as exc:
            status = ValidationRunStatus.ERROR
            blocked_reason = f"Validation command failed to start: {exc}"

    finished_at = datetime.now(UTC)
    duration_seconds = max(0.0, (finished_at - started_at).total_seconds())
    stdout_path = artifact_dir / "stdout.txt" if write_report else None
    stderr_path = artifact_dir / "stderr.txt" if write_report else None
    report_path = artifact_dir / "validation-run.md" if write_report else None
    record = ValidationRunRecord(
        schema_version=VALIDATION_RUN_SCHEMA_VERSION,
        validation_run_id=validation_run_id,
        project_name=project_name,
        run_id=run_id,
        task_id=task_id,
        command_id=command.id,
        command_name=command.name,
        command=command.command,
        working_dir=working_dir.resolve(),
        category=command.category,
        risk_level=command.risk_level,
        approval_required=approval_required,
        approval_id=approval_id,
        status=status,
        exit_code=exit_code,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        timeout_seconds=timeout_seconds,
        dry_run=dry_run,
        blocked_reason=blocked_reason,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        report_path=report_path,
        policy_reasons=_dedupe(policy_reasons),
    )
    if write_report:
        _write_artifacts(record, artifact_dir, stdout_text, stderr_text)
    return ValidationRunResult(record=record, artifact_dir=artifact_dir, stdout_text=stdout_text, stderr_text=stderr_text)


def list_validation_history(
    project_name: str,
    command_id: str | None = None,
    workspace_root: Path | None = None,
) -> list[ValidationRunRecord]:
    root = workspace_root or get_workspace_root()
    records: list[ValidationRunRecord] = []
    locations = [root / "projects" / project_name / VALIDATION_RUNS_DIR]
    runs_root = root / "runs" / project_name
    if runs_root.exists():
        locations.extend(path / "artifacts" / VALIDATION_RUNS_DIR for path in sorted(runs_root.iterdir()) if path.is_dir())
    for location in locations:
        if not location.exists():
            continue
        for record_path in sorted(location.glob("*/validation-run.json")):
            try:
                data = json.loads(record_path.read_text(encoding="utf-8"))
                record = ValidationRunRecord.model_validate(data)
            except (OSError, json.JSONDecodeError, ValidationError):
                continue
            if record.project_name != project_name:
                continue
            if command_id and record.command_id != command_id:
                continue
            records.append(record)
    return sorted(records, key=lambda item: item.started_at)


def terminal_excerpt(text: str, limit: int = MAX_TERMINAL_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... truncated {len(text) - limit} characters ..."


def _artifact_dir(workspace_root: Path, project_name: str, validation_run_id: str, run_id: str | None) -> Path:
    if run_id:
        return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / VALIDATION_RUNS_DIR / validation_run_id
    return workspace_root / "projects" / project_name / VALIDATION_RUNS_DIR / validation_run_id


def _write_artifacts(record: ValidationRunRecord, artifact_dir: Path, stdout_text: str, stderr_text: str) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = artifact_dir / "stdout.txt"
    stderr_path = artifact_dir / "stderr.txt"
    json_path = artifact_dir / "validation-run.json"
    report_path = artifact_dir / "validation-run.md"
    stdout_path.write_text(stdout_text[:MAX_REPORT_OUTPUT_CHARS], encoding="utf-8")
    stderr_path.write_text(stderr_text[:MAX_REPORT_OUTPUT_CHARS], encoding="utf-8")
    record = record.model_copy(update={"stdout_path": stdout_path, "stderr_path": stderr_path, "report_path": report_path})
    json_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(_render_markdown(record, stdout_text, stderr_text), encoding="utf-8")


def _render_markdown(record: ValidationRunRecord, stdout_text: str, stderr_text: str) -> str:
    lines = [
        f"# validation-run-{record.validation_run_id}",
        "",
        f"- schema_version: {record.schema_version}",
        f"- validation_run_id: {record.validation_run_id}",
        f"- project_name: {record.project_name}",
        f"- run_id: {record.run_id or 'none'}",
        f"- task_id: {record.task_id or 'none'}",
        f"- command_id: {record.command_id}",
        f"- command_name: {record.command_name}",
        f"- command: `{record.command}`",
        f"- working_dir: `{record.working_dir}`",
        f"- category: {record.category.value}",
        f"- risk_level: {record.risk_level.value}",
        f"- approval_required: {record.approval_required}",
        f"- approval_id: {record.approval_id or 'none'}",
        f"- status: {record.status.value}",
        f"- exit_code: {record.exit_code if record.exit_code is not None else 'none'}",
        f"- started_at: {record.started_at.isoformat()}",
        f"- finished_at: {record.finished_at.isoformat() if record.finished_at else 'none'}",
        f"- duration_seconds: {record.duration_seconds}",
        f"- timeout_seconds: {record.timeout_seconds}",
        f"- dry_run: {record.dry_run}",
        f"- blocked_reason: {record.blocked_reason or 'none'}",
        "",
        "## Policy Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in record.policy_reasons or ["none"])
    lines.extend(["", "## Stdout", "", "```text", stdout_text[:MAX_REPORT_OUTPUT_CHARS], "```", "", "## Stderr", "", "```text", stderr_text[:MAX_REPORT_OUTPUT_CHARS], "```", ""])
    return "\n".join(lines)


def _parse_command(command: str) -> list[str]:
    try:
        argv = shlex.split(command, posix=False)
    except ValueError as exc:
        msg = f"Validation command could not be parsed safely: {exc}"
        raise ValueError(msg) from exc
    if not argv:
        msg = "Validation command is empty."
        raise ValueError(msg)
    return [part.strip('"') for part in argv]


def _safety_block_reason(command: str) -> str | None:
    normalized = " ".join(command.lower().split())
    dangerous_patterns = [
        (r"\brm\s+-rf\b", "Command contains rm -rf."),
        (r"\bdel\s+/s\b", "Command contains del /s."),
        (r"\brmdir\s+/s\b", "Command contains rmdir /s."),
        (r"\bremove-item\b.*\b-recurse\b", "Command contains Remove-Item -Recurse."),
        (r"\bformat\b", "Command contains format."),
        (r"\bdiskpart\b", "Command contains diskpart."),
        (r"\bdotnet\s+ef\s+database\s+update\b", "Command contains dotnet ef database update."),
        (r"\b(database\s+update|update-database)\b", "Command contains database update."),
        (r"\b(printenv|set\s*>|env\s*>|dump\s+env|tokens?|credentials?)\b", "Command may expose environment, tokens, or credentials."),
        (r"\b(register-scheduledtask|schtasks|backup\s+restore|restore\s+backup)\b", "Command may modify scheduler or restore state."),
    ]
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, normalized):
            return reason
    return None


def _find_validation_approval(
    workspace_root: Path,
    project_name: str,
    run_id: str | None,
    task_id: str | None,
    command: ValidationCommand,
) -> str | None:
    if not run_id or not task_id:
        return None
    try:
        ledger = load_approval_ledger(project_name, run_id, workspace_root=workspace_root)
    except ValueError:
        return None
    required_fragments = [f"validation-command:{command.id}", f"command:{command.command}"]
    for approval in ledger.approvals.values():
        if approval.status != DevoApprovalStatus.APPROVED or approval.blocked:
            continue
        if approval.task_id != task_id:
            continue
        if approval.action_type not in {"validation", "target_command"}:
            continue
        text = "\n".join(value or "" for value in (approval.requested_reason, approval.approval_note))
        if all(fragment in text for fragment in required_fragments):
            return approval.approval_id
    return None


def _approval_block_reason(project_name: str, run_id: str | None, task_id: str | None, command: ValidationCommand) -> str:
    if not run_id or not task_id:
        return "High-risk validation commands require --run and --task plus a matching approved approval."
    return (
        "High-risk validation command requires a matching approved approval. "
        f"Create one with: devo approval request --project {project_name} --run {run_id} --task {task_id} --action target_command "
        f"--reason \"validation-command:{command.id} command:{command.command}\""
    )


def _validation_run_id(command_id: str, started_at: datetime) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", command_id).strip("-") or "validation"
    return f"{started_at.strftime('%Y%m%d-%H%M%S')}-{safe_id}"


def _decode_timeout_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
