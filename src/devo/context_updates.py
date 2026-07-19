from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from .context import load_context_state, save_context_state
from .environment import SNAPSHOT_FILE_NAME
from .projects import get_workspace_root
from .runs import list_runs, run_path
from .scanner import load_registered_project
from .schemas import (
    ContextStatus,
    ContextUpdateStatus,
    EnvironmentSnapshot,
    ProjectContextUpdate,
    ProjectContextUpdateLedger,
    ProjectRegistration,
    ProjectScanResult,
    ValidationCommandRegistry,
    ValidationRunRecord,
)
from .validation_registry import REGISTRY_FILE_NAME, load_registry
from .validation_runner import list_validation_history

CONTEXT_UPDATE_DIR = "context-updates"
CONTEXT_UPDATE_LEDGER = "context-updates-ledger.json"
CONTEXT_UPDATE_SCHEMA_VERSION = "1"
MAX_ITEMS = 8
SENSITIVE_RE = re.compile(r"(secret|password|token|api[_-]?key|private key|connectionstring|connection string|settings\.local)", re.IGNORECASE)


def get_project_context_summary(project_name: str, workspace_root: Path | None = None) -> dict[str, Any]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    state = load_context_state(project_name, workspace_root=root)
    project_dir = root / "projects" / project_name
    scan_path = project_dir / "scan-result.json"
    registry_path = project_dir / REGISTRY_FILE_NAME
    env_path = root / "environment" / project_name / SNAPSHOT_FILE_NAME
    ledger = load_context_update_ledger(project_name, workspace_root=root)
    runs = list_runs(project_name, workspace_root=root)[-5:]
    warnings: list[str] = []
    if not scan_path.exists():
        warnings.append("No scan-result.json found.")
    if state.status != ContextStatus.CONTEXT_APPROVED:
        warnings.append(f"Project context is not approved: {state.status.value}.")
    if not registry_path.exists():
        warnings.append("No validation-commands.json found.")
    if not env_path.exists():
        warnings.append("No environment snapshot found.")
    if not runs:
        warnings.append("No development runs found.")
    suggested = _suggest_context_action(state.status.value, bool(scan_path.exists()), bool(ledger.updates))
    return {
        "project_name": project_name,
        "project_path": str(registration.path),
        "context_status": state.status.value,
        "approved_context_paths": _approved_context_paths(root, project_name),
        "last_scan_result": _scan_summary(scan_path),
        "environment_snapshot": _environment_summary(env_path),
        "validation_registry": _validation_registry_summary(project_name, root),
        "recent_runs": [_run_line(run) for run in runs],
        "latest_run_statuses": [f"{run.run_id}: {run.status.value}" for run in runs],
        "latest_context_update_file": str(state.latest_context_update_file) if state.latest_context_update_file else None,
        "latest_context_update_at": state.latest_context_update_at.isoformat() if state.latest_context_update_at else None,
        "context_update_count": len(ledger.updates),
        "warnings": _dedupe(warnings),
        "suggested_next_context_action": suggested,
    }


def refresh_project_context(
    project_name: str,
    run_id: str | None = None,
    write_draft: bool = False,
    workspace_root: Path | None = None,
) -> tuple[ProjectContextUpdate, Path | None, Path | None]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    if run_id:
        # Fails safely for unknown runs without touching target projects.
        run_path(project_name, run_id, workspace_root=root)
        matching = [run for run in list_runs(project_name, workspace_root=root) if run.run_id == run_id]
        if not matching:
            msg = f"Run not found: {run_id}"
            raise ValueError(msg)
    created_at = datetime.now(UTC)
    update_id = f"context-update-{created_at.strftime('%Y%m%d-%H%M%S')}"
    update = _build_context_update(root, registration, update_id, created_at, run_id)
    md_path: Path | None = None
    json_path: Path | None = None
    if write_draft:
        output_dir = _updates_dir(root, project_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        md_path = output_dir / f"{update_id}.md"
        json_path = output_dir / f"{update_id}.json"
        update = update.model_copy(update={"markdown_path": md_path, "json_path": json_path})
        json_path.write_text(update.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(render_context_update_markdown(update), encoding="utf-8")
        ledger = load_context_update_ledger(project_name, workspace_root=root)
        ledger.updates.append(update)
        ledger.updated_at = datetime.now(UTC)
        save_context_update_ledger(ledger, workspace_root=root)
    return update, md_path, json_path


def apply_context_update(project_name: str, update_file: Path, workspace_root: Path | None = None) -> ProjectContextUpdate:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    source = update_file.expanduser().resolve()
    if not source.exists() or not source.is_file():
        msg = f"Context update file does not exist: {source}"
        raise ValueError(msg)
    generated_dir = _updates_dir(root, project_name).resolve()
    if source.suffix.lower() != ".json" or source.parent.resolve() != generated_dir:
        msg = "Context update apply only accepts generated context-refresh JSON files."
        raise ValueError(msg)
    try:
        update = ProjectContextUpdate.model_validate(json.loads(source.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as exc:
        msg = "Context update file is not a valid generated context update JSON file."
        raise ValueError(msg) from exc
    if update.project_name != project_name:
        msg = f"Context update belongs to project {update.project_name}, not {project_name}."
        raise ValueError(msg)
    if update.schema_version != CONTEXT_UPDATE_SCHEMA_VERSION or update.json_path is None:
        msg = "Context update file is missing generated update metadata."
        raise ValueError(msg)
    if Path(update.json_path).resolve() != source:
        msg = "Context update file path does not match its generated metadata."
        raise ValueError(msg)

    applied_at = datetime.now(UTC)
    applied = update.model_copy(update={"status": ContextUpdateStatus.APPLIED, "applied_at": applied_at})
    source.write_text(applied.model_dump_json(indent=2), encoding="utf-8")
    if applied.markdown_path and Path(applied.markdown_path).exists():
        Path(applied.markdown_path).write_text(render_context_update_markdown(applied), encoding="utf-8")

    ledger = load_context_update_ledger(project_name, workspace_root=root)
    ledger.updates.append(applied)
    ledger.updated_at = applied_at
    save_context_update_ledger(ledger, workspace_root=root)

    state = load_context_state(project_name, workspace_root=root)
    state.latest_context_update_at = applied_at
    state.latest_context_update_file = source
    state.updated_at = applied_at
    save_context_state(state, workspace_root=root)
    return applied


def list_context_updates(project_name: str, workspace_root: Path | None = None) -> ProjectContextUpdateLedger:
    return load_context_update_ledger(project_name, workspace_root=workspace_root)


def load_context_update_ledger(project_name: str, workspace_root: Path | None = None) -> ProjectContextUpdateLedger:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    path = _ledger_path(root, project_name)
    if not path.exists():
        return ProjectContextUpdateLedger(project_name=project_name)
    try:
        ledger = ProjectContextUpdateLedger.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as exc:
        msg = f"Context update ledger is invalid: {path}"
        raise ValueError(msg) from exc
    return ledger


def save_context_update_ledger(ledger: ProjectContextUpdateLedger, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    path = _ledger_path(root, ledger.project_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")


def render_context_update_markdown(update: ProjectContextUpdate) -> str:
    lines = [
        f"# {update.update_id}",
        "",
        f"- schema_version: {update.schema_version}",
        f"- project_name: {update.project_name}",
        f"- project_path: `{update.project_path}`",
        f"- created_at: {update.created_at.isoformat()}",
        f"- source_run_id: {update.source_run_id or 'none'}",
        f"- status: {update.status.value}",
        f"- applied_at: {update.applied_at.isoformat() if update.applied_at else 'none'}",
        "",
        "## Facts Added",
        *_list(update.facts_added),
        "",
        "## Facts Changed",
        *_list(update.facts_changed),
        "",
        "## New Artifacts",
        *_list(update.new_artifacts),
        "",
        "## Recent Runs",
        *_list(update.recent_runs),
        "",
        "## Validation Registry Summary",
        *_list(update.validation_registry_summary),
        "",
        "## Environment Snapshot Summary",
        *_list(update.environment_snapshot_summary),
        "",
        "## Git Delivery Summary",
        *_list(update.git_delivery_summary),
        "",
        "## Approvals Summary",
        *_list(update.approvals_summary),
        "",
        "## Warnings",
        *_list(update.warnings),
        "",
        "## Recommended Next Actions",
        *_list(update.recommended_next_actions),
    ]
    return "\n".join(lines) + "\n"


def _build_context_update(root: Path, registration: ProjectRegistration, update_id: str, created_at: datetime, run_id: str | None) -> ProjectContextUpdate:
    project_name = registration.name
    project_dir = root / "projects" / project_name
    warnings: list[str] = []
    facts_added = [
        f"Registered project path: {registration.path}",
        f"Project markers: {', '.join(registration.detected_markers) if registration.detected_markers else 'none'}",
    ]
    scan_summary = _scan_summary(project_dir / "scan-result.json")
    if scan_summary:
        facts_changed.extend([]) if False else None
        facts_added.extend(scan_summary)
    else:
        warnings.append("No scan-result.json found; run `devo project scan <projectName>` to refresh scan metadata.")
    validation_summary = _validation_registry_summary(project_name, root)
    if not validation_summary:
        warnings.append("No validation registry found.")
    env_summary = _environment_summary(root / "environment" / project_name / SNAPSHOT_FILE_NAME)
    if not env_summary:
        warnings.append("No environment snapshot found.")
    recent_runs = _recent_run_summaries(project_name, root, run_id)
    if not recent_runs:
        warnings.append("No recent runs found.")
    update = ProjectContextUpdate(
        schema_version=CONTEXT_UPDATE_SCHEMA_VERSION,
        update_id=update_id,
        project_name=project_name,
        project_path=registration.path,
        created_at=created_at,
        source_run_id=run_id,
        facts_added=_sanitize_list(facts_added),
        facts_changed=_sanitize_list(_approved_context_summary(root, project_name)),
        new_artifacts=_sanitize_list(_new_artifacts(root, project_name, run_id)),
        recent_runs=_sanitize_list(recent_runs),
        validation_registry_summary=_sanitize_list(validation_summary),
        environment_snapshot_summary=_sanitize_list(env_summary),
        git_delivery_summary=_sanitize_list(_git_delivery_summary(root, project_name, run_id)),
        approvals_summary=_sanitize_list(_approvals_summary(root, project_name, run_id)),
        warnings=_sanitize_list(_dedupe(warnings)),
        recommended_next_actions=_recommended_actions(project_name, bool(scan_summary), bool(validation_summary), bool(env_summary)),
    )
    return update


def _approved_context_paths(root: Path, project_name: str) -> list[str]:
    approved = root / "projects" / project_name / "context" / "approved"
    if not approved.exists():
        return []
    return [str(path) for path in sorted(approved.glob("*.md"))]


def _approved_context_summary(root: Path, project_name: str) -> list[str]:
    state = load_context_state(project_name, workspace_root=root)
    facts: list[str] = [f"Context lifecycle status: {state.status.value}"]
    if state.approved_at:
        facts.append(f"Approved context recorded at {state.approved_at.isoformat()} by {state.approved_by or 'unknown'}.")
    if state.latest_context_update_file:
        facts.append(f"Latest applied context update: {state.latest_context_update_file}")
    return facts


def _scan_summary(scan_path: Path) -> list[str]:
    if not scan_path.exists():
        return []
    try:
        scan = ProjectScanResult.model_validate(json.loads(scan_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return [f"Scan result exists but could not be parsed: {scan_path}"]
    categories = scan.categories.model_dump()
    detected = [f"{key}={len(value)}" for key, value in categories.items() if value]
    return [
        f"Scan result: scanned_at={scan.scanned_at.isoformat()}, files={scan.file_tree.scanned_file_count}, directories={scan.file_tree.scanned_directory_count}.",
        f"Detected categories: {', '.join(detected) if detected else 'none'}.",
        f"Scan warnings: {len(scan.warnings)}.",
    ]


def _validation_registry_summary(project_name: str, root: Path) -> list[str]:
    path = root / "projects" / project_name / REGISTRY_FILE_NAME
    if not path.exists():
        return []
    try:
        registry = load_registry(project_name, workspace_root=root)
    except ValueError:
        return [f"Validation registry exists but could not be parsed: {path}"]
    risk_counts: dict[str, int] = {}
    categories: dict[str, int] = {}
    enabled = 0
    command_labels: list[str] = []
    for command in registry.commands:
        risk_counts[command.risk_level.value] = risk_counts.get(command.risk_level.value, 0) + 1
        categories[command.category.value] = categories.get(command.category.value, 0) + 1
        if command.enabled:
            enabled += 1
        command_labels.append(f"{command.id} ({command.category.value}, {command.risk_level.value}, enabled={command.enabled})")
    return [
        f"Validation registry commands: total={len(registry.commands)}, enabled={enabled}, disabled={len(registry.commands) - enabled}.",
        f"Validation command categories: {_format_counts(categories)}.",
        f"Validation risk levels: {_format_counts(risk_counts)}.",
        f"Validation command ids: {', '.join(command_labels[:MAX_ITEMS]) if command_labels else 'none'}.",
    ]


def _environment_summary(snapshot_path: Path) -> list[str]:
    if not snapshot_path.exists():
        return []
    try:
        snapshot = EnvironmentSnapshot.model_validate(json.loads(snapshot_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return [f"Environment snapshot exists but could not be parsed: {snapshot_path}"]
    lines = [
        f"Environment snapshot created_at={snapshot.created_at.isoformat()}, git_branch={snapshot.project_git_branch or 'unknown'}, git_commit={snapshot.project_git_commit or 'unknown'}.",
        f"Dependency files found: {len(snapshot.dependency_files_found)}; solution files: {len(snapshot.detected_solution_files)}; project files: {len(snapshot.detected_project_files)}.",
        f"Recommended recovery commands recorded: {len(snapshot.recommended_commands)}.",
        f"Environment warnings: {len(snapshot.warnings)}.",
    ]
    if snapshot.warnings:
        lines.extend(f"Environment warning classification: {warning}" for warning in snapshot.warnings[:MAX_ITEMS])
    return lines


def _recent_run_summaries(project_name: str, root: Path, run_id: str | None) -> list[str]:
    runs = list_runs(project_name, workspace_root=root)
    if run_id:
        runs = [run for run in runs if run.run_id == run_id]
    runs = runs[-5:]
    return [_run_line(run) for run in runs]


def _run_line(run: Any) -> str:
    return f"{run.run_id}: status={run.status.value}, goal={run.goal}, updated_at={run.updated_at.isoformat()}"


def _new_artifacts(root: Path, project_name: str, run_id: str | None) -> list[str]:
    artifacts: list[str] = []
    project_dir = root / "projects" / project_name
    for path in [project_dir / "scan-result.json", project_dir / REGISTRY_FILE_NAME, root / "environment" / project_name / SNAPSHOT_FILE_NAME]:
        if path.exists():
            artifacts.append(str(path))
    run_dirs = [run_path(project_name, run_id, workspace_root=root)] if run_id else [root / "runs" / project_name / run.run_id for run in list_runs(project_name, workspace_root=root)[-3:]]
    for directory in run_dirs:
        for pattern in (
            "run-summary.md",
            "artifacts/workflow/batch-report-*.md",
            "artifacts/validation-runs/*/validation-run.md",
            "artifacts/git-delivery/git-delivery-report-*.md",
        ):
            artifacts.extend(str(path) for path in sorted(directory.glob(pattern))[-MAX_ITEMS:])
    return _dedupe(artifacts)[-20:]


def _git_delivery_summary(root: Path, project_name: str, run_id: str | None) -> list[str]:
    reports: list[Path] = []
    reports.extend(sorted((root / "projects" / project_name / "git-delivery").glob("git-delivery-report-*.json")))
    run_dirs = [run_path(project_name, run_id, workspace_root=root)] if run_id else [root / "runs" / project_name / run.run_id for run in list_runs(project_name, workspace_root=root)[-5:]]
    for directory in run_dirs:
        reports.extend(sorted((directory / "artifacts" / "git-delivery").glob("git-delivery-report-*.json")))
    lines: list[str] = []
    for path in reports[-MAX_ITEMS:]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            lines.append(f"Git delivery report could not be parsed: {path}")
            continue
        check = data.get("delivery_check", {}) if isinstance(data, dict) else {}
        status = check.get("status", {}) if isinstance(check, dict) else {}
        lines.append(
            f"{path.name}: readiness={check.get('readiness', 'unknown')}, branch={status.get('current_branch', 'unknown')}, ahead={status.get('ahead', 'unknown')}, behind={status.get('behind', 'unknown')}."
        )
    return lines


def _approvals_summary(root: Path, project_name: str, run_id: str | None) -> list[str]:
    ledgers: list[Path] = []
    run_dirs = [run_path(project_name, run_id, workspace_root=root)] if run_id else [root / "runs" / project_name / run.run_id for run in list_runs(project_name, workspace_root=root)[-5:]]
    for directory in run_dirs:
        ledgers.extend(sorted((directory / "approvals").glob("approvals-ledger.json")))
    lines: list[str] = []
    for path in ledgers[-MAX_ITEMS:]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            lines.append(f"Approval ledger could not be parsed: {path}")
            continue
        approvals = data.get("approvals", {}) if isinstance(data, dict) else {}
        counts: dict[str, int] = {}
        for record in approvals.values() if isinstance(approvals, dict) else []:
            status = str(record.get("status", "unknown")) if isinstance(record, dict) else "unknown"
            counts[status] = counts.get(status, 0) + 1
        lines.append(f"{path.name}: approvals={len(approvals) if isinstance(approvals, dict) else 0}, statuses={_format_counts(counts)}.")
    return lines


def _recommended_actions(project_name: str, has_scan: bool, has_registry: bool, has_env: bool) -> list[str]:
    actions: list[str] = []
    if not has_scan:
        actions.append(f"Run `devo project scan {project_name}` before relying on refreshed context.")
    if not has_registry:
        actions.append(f"Consider `devo validation suggest --project {project_name}` to create validation command metadata.")
    if not has_env:
        actions.append(f"Consider `devo env snapshot --name {project_name} --path <projectPath>` for recovery metadata.")
    actions.append(f"Review this context update draft before applying it with `devo project context-apply --project {project_name} --file <jsonFile>`.")
    return actions


def _suggest_context_action(context_status: str, has_scan: bool, has_updates: bool) -> str:
    if not has_scan:
        return "Run a safe project scan before refreshing context."
    if context_status != ContextStatus.CONTEXT_APPROVED.value:
        return "Approve baseline project context before treating updates as approved knowledge."
    if not has_updates:
        return "Run `devo project context-refresh --project <projectName> --write-draft` after meaningful run or environment changes."
    return "Review latest updates and apply reviewed drafts when they contain useful deterministic facts."


def _updates_dir(root: Path, project_name: str) -> Path:
    return root / "projects" / project_name / CONTEXT_UPDATE_DIR


def _ledger_path(root: Path, project_name: str) -> Path:
    return _updates_dir(root, project_name) / CONTEXT_UPDATE_LEDGER


def _list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _sanitize_list(items: Iterable[str]) -> list[str]:
    sanitized: list[str] = []
    for item in items:
        text = str(item)
        if SENSITIVE_RE.search(text):
            if "settings.local" in text.lower():
                sanitized.append("Local/sensitive settings artifact detected; path/value details omitted.")
            else:
                sanitized.append(SENSITIVE_RE.sub("[sensitive]", text))
        else:
            sanitized.append(text)
    return _dedupe(sanitized)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
