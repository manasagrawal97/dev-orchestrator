from __future__ import annotations

import fnmatch
import json
import re
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from .approvals import DevoApprovalStatus, find_matching_approved_approval
from .projects import get_workspace_root
from .runs import load_run, run_path
from .scanner import load_registered_project
from .schemas import (
    GitDeliveryCheck,
    GitDeliveryReadiness,
    GitDeliveryReport,
    GitFileState,
    GitRepositoryStatus,
    GitSecretSignal,
    ValidationRunRecord,
)
from .validation_runner import list_validation_history

MAX_SECRET_SCAN_BYTES = 512_000
GIT_DELIVERY_DIR = "git-delivery"

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OPENAI_API_KEY", re.compile(r"OPENAI_API_KEY", re.IGNORECASE)),
    ("API_KEY", re.compile(r"\b[A-Z0-9_]*API[_-]?KEY\s*[:=]", re.IGNORECASE)),
    ("SECRET", re.compile(r"\b[A-Z0-9_]*SECRET\s*[:=]", re.IGNORECASE)),
    ("PASSWORD", re.compile(r"\b[A-Z0-9_]*PASSWORD\s*[:=]", re.IGNORECASE)),
    ("TOKEN", re.compile(r"\b[A-Z0-9_]*TOKEN\s*[:=]", re.IGNORECASE)),
    ("PRIVATE KEY", re.compile(r"PRIVATE KEY", re.IGNORECASE)),
    (
        "connection string password",
        re.compile(r"(connection\s*string|server\s*=|data\s+source\s*=).{0,500}password\s*=", re.IGNORECASE | re.DOTALL),
    ),
)


def get_git_repository_status(project_name: str, workspace_root: Path | None = None) -> GitRepositoryStatus:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    repo_path = Path(registration.path).expanduser().resolve()
    if not repo_path.exists():
        msg = f"Project path does not exist: {repo_path}"
        raise ValueError(msg)
    if not repo_path.is_dir():
        msg = f"Project path must be a directory: {repo_path}"
        raise ValueError(msg)

    inside = _git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0:
        detail = _git_error_detail(inside)
        if "dubious ownership" in detail.lower():
            msg = f"Git rejected repository access for project path due to dubious ownership: {repo_path}"
            raise ValueError(msg)
        msg = f"Project path is not a git repository: {repo_path}"
        raise ValueError(msg)
    if inside.stdout.strip().lower() != "true":
        msg = f"Project path is not inside a git work tree: {repo_path}"
        raise ValueError(msg)
    top_level = _git_value(repo_path, ["rev-parse", "--show-toplevel"])
    if not top_level:
        msg = f"Could not determine git repository root for project path: {repo_path}"
        raise ValueError(msg)
    git_root = Path(top_level).resolve()
    if git_root != repo_path:
        msg = f"Project path is inside a git work tree but is not the repository root: {repo_path} (git root: {git_root})"
        raise ValueError(msg)

    warnings: list[str] = []
    branch = _git_value(repo_path, ["branch", "--show-current"])
    if not branch:
        branch = _git_value(repo_path, ["rev-parse", "--short", "HEAD"])
        if branch:
            warnings.append("Repository appears to be in detached HEAD state.")
    head_commit = _git_value(repo_path, ["rev-parse", "HEAD"])
    upstream = _git_value(repo_path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    remotes = _git(repo_path, ["remote"])
    remote_detected = bool(remotes.stdout.strip()) if remotes.returncode == 0 else False
    ahead: int | None = None
    behind: int | None = None
    if upstream:
        counts = _git(repo_path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
        if counts.returncode == 0:
            parts = counts.stdout.strip().split()
            if len(parts) == 2:
                ahead = _safe_int(parts[0])
                behind = _safe_int(parts[1])
        else:
            warnings.append("Could not determine ahead/behind counts for upstream branch.")
    else:
        warnings.append("No upstream branch is configured.")
    if not remote_detected:
        warnings.append("No Git remote is configured.")

    status_lines = _git(repo_path, ["status", "--porcelain=v1", "-uall"])
    if status_lines.returncode != 0:
        msg = f"Could not read git status: {status_lines.stderr.strip() or status_lines.stdout.strip()}"
        raise ValueError(msg)
    staged, unstaged, untracked = _parse_porcelain_status(status_lines.stdout)

    return GitRepositoryStatus(
        project_name=project_name,
        repo_path=repo_path,
        is_git_repo=True,
        current_branch=branch or None,
        head_commit=head_commit or None,
        upstream_branch=upstream or None,
        remote_detected=remote_detected,
        ahead=ahead,
        behind=behind,
        working_tree_clean=not staged and not unstaged and not untracked,
        staged_files=staged,
        unstaged_files=unstaged,
        untracked_files=untracked,
        warnings=_dedupe(warnings),
    )


def run_delivery_check(
    project_name: str,
    run_id: str | None = None,
    task_id: str | None = None,
    commit_message: str | None = None,
    workspace_root: Path | None = None,
) -> GitDeliveryCheck:
    root = workspace_root or get_workspace_root()
    if run_id:
        load_run(project_name, run_id, workspace_root=root)
    status = get_git_repository_status(project_name, workspace_root=root)
    checks: list[str] = [
        "project path exists",
        "project path is a directory",
        "path is a git repository",
        "git status parsed",
    ]
    warnings = list(status.warnings)
    blockers: list[str] = []

    forbidden_staged = _forbidden_changed_files(status.staged_files)
    forbidden_changed = _forbidden_changed_files([*status.unstaged_files, *status.untracked_files])
    if forbidden_staged:
        blockers.extend(f"Forbidden file staged: {path}" for path in forbidden_staged)
    if forbidden_changed:
        warnings.extend(f"Forbidden/risky changed file is present but not staged: {path}" for path in forbidden_changed)
    checks.append("forbidden file patterns checked")

    secret_signals = _scan_secret_signals(status.repo_path, [*status.staged_files, *status.unstaged_files, *status.untracked_files])
    staged_paths = {item.path for item in status.staged_files}
    staged_secret_signals = [signal for signal in secret_signals if signal.path in staged_paths]
    if staged_secret_signals:
        blockers.extend(f"Secret-like signal staged in {signal.path}: {signal.signal_type}" for signal in staged_secret_signals)
    for signal in secret_signals:
        if signal.path not in staged_paths:
            warnings.append(f"Secret-like signal in changed file {signal.path}: {signal.signal_type}")
    checks.append("secret-like changed text files scanned")

    diff_check = _git(status.repo_path, ["diff", "--check"])
    checks.append("git diff --check")
    if diff_check.returncode == 0:
        checks.append("git diff --check: passed")
    else:
        blockers.append(_single_line("git diff --check failed", diff_check.stdout, diff_check.stderr))

    validation_evidence = _validation_evidence(project_name, run_id, task_id, workspace_root=root)
    if run_id or task_id:
        checks.append("validation evidence inspected")
        if not validation_evidence:
            warnings.append("No validation run evidence was found for this run/task.")

    approval_evidence = _approval_evidence(project_name, run_id, task_id, workspace_root=root)
    if run_id and task_id:
        checks.append("approval ledger inspected for git_commit/git_push")

    if status.behind and status.behind > 0:
        blockers.append("Remote upstream has commits not present locally; review or integrate before pushing.")
    if not status.remote_detected:
        warnings.append("No Git remote detected; push guidance may be unavailable.")
    checks.append("push readiness inspected")

    readiness = _readiness(blockers, warnings, status)
    suggested_commit = _suggest_commit_command(status, commit_message)
    suggested_push = _suggest_push_command(status)
    return GitDeliveryCheck(
        project_name=project_name,
        repo_path=status.repo_path,
        run_id=run_id,
        task_id=task_id,
        status=status,
        readiness=readiness,
        checks_performed=_dedupe(checks),
        warnings=_dedupe(warnings),
        blockers=_dedupe(blockers),
        forbidden_files=_dedupe([*forbidden_staged, *forbidden_changed]),
        secret_signals=secret_signals,
        validation_evidence=validation_evidence,
        approval_evidence=approval_evidence,
        suggested_commit_command=suggested_commit,
        suggested_push_command=suggested_push,
        next_human_action=_next_human_action(readiness, status, suggested_commit, suggested_push),
    )


def create_delivery_report(
    project_name: str,
    run_id: str | None = None,
    task_id: str | None = None,
    commit_message: str | None = None,
    workspace_root: Path | None = None,
) -> GitDeliveryReport:
    root = workspace_root or get_workspace_root()
    check = run_delivery_check(project_name, run_id=run_id, task_id=task_id, commit_message=commit_message, workspace_root=root)
    created_at = datetime.now(UTC)
    slug = created_at.strftime("%Y%m%d-%H%M%S")
    artifact_dir = _report_dir(root, project_name, run_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    md_path = artifact_dir / f"git-delivery-report-{slug}.md"
    json_path = artifact_dir / f"git-delivery-report-{slug}.json"
    report = GitDeliveryReport(
        project_name=project_name,
        repo_path=check.repo_path,
        run_id=run_id,
        task_id=task_id,
        created_at=created_at,
        markdown_path=md_path,
        json_path=json_path,
        requested_commit_message=commit_message,
        delivery_check=check,
    )
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_render_report_markdown(report), encoding="utf-8")
    return report


def _git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    safe_directory = f"safe.directory={repo_path}"
    return subprocess.run(["git", "-c", safe_directory, *args], cwd=repo_path, capture_output=True, text=True, shell=False)


def _git_value(repo_path: Path, args: list[str]) -> str | None:
    completed = _git(repo_path, args)
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _parse_porcelain_status(output: str) -> tuple[list[GitFileState], list[GitFileState], list[GitFileState]]:
    staged: list[GitFileState] = []
    unstaged: list[GitFileState] = []
    untracked: list[GitFileState] = []
    for raw_line in output.splitlines():
        if not raw_line:
            continue
        if len(raw_line) < 3:
            continue
        xy = raw_line[:2]
        path = _status_path(raw_line[3:])
        if xy == "??":
            untracked.append(GitFileState(path=path, status="untracked"))
            continue
        index_status = xy[0]
        worktree_status = xy[1]
        if index_status != " ":
            staged.append(GitFileState(path=path, status=index_status))
        if worktree_status != " ":
            unstaged.append(GitFileState(path=path, status=worktree_status))
    return staged, unstaged, untracked


def _status_path(raw_path: str) -> str:
    if " -> " in raw_path:
        raw_path = raw_path.split(" -> ", 1)[1]
    return raw_path.strip().strip('"')


def _forbidden_changed_files(files: Iterable[GitFileState]) -> list[str]:
    forbidden: list[str] = []
    for item in files:
        if _is_forbidden_path(item.path):
            forbidden.append(item.path)
    return _dedupe(forbidden)


def _is_forbidden_path(path: str) -> bool:
    normalized = path.replace("\\", "/").strip("/").lower()
    parts = [part for part in normalized.split("/") if part]
    name = parts[-1] if parts else normalized
    if name == ".env" or name.endswith(".env"):
        return True
    if name.endswith((".pem", ".key")):
        return True
    if name in {"id_rsa", "id_ed25519"}:
        return True
    if fnmatch.fnmatch(name, "secrets.*"):
        return True
    forbidden_dirs = {"workspace", "backup", "backups", ".venv", "node_modules", ".pytest_cache", "__pycache__", "bin", "obj", ".packages"}
    if any(part in forbidden_dirs or part.startswith("restore-test") for part in parts):
        return True
    if "logs" in parts and any(signal in name for signal in ("secret", "password", "token")):
        return True
    return False


def _scan_secret_signals(repo_path: Path, files: Iterable[GitFileState]) -> list[GitSecretSignal]:
    signals: list[GitSecretSignal] = []
    seen: set[tuple[str, str]] = set()
    for item in files:
        full_path = repo_path / item.path
        if not full_path.exists() or not full_path.is_file():
            continue
        try:
            if full_path.stat().st_size > MAX_SECRET_SCAN_BYTES:
                continue
            data = full_path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for signal_type, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                key = (item.path, signal_type)
                if key not in seen:
                    seen.add(key)
                    signals.append(GitSecretSignal(path=item.path, signal_type=signal_type))
    return signals


def _validation_evidence(project_name: str, run_id: str | None, task_id: str | None, workspace_root: Path) -> list[str]:
    if not run_id and not task_id:
        return []
    try:
        records = list_validation_history(project_name, workspace_root=workspace_root)
    except (ValueError, OSError, ValidationError):
        return []
    filtered = []
    for record in records:
        if run_id and record.run_id != run_id:
            continue
        if task_id and record.task_id != task_id:
            continue
        filtered.append(record)
    return [_validation_line(record) for record in filtered[-5:]]


def _validation_line(record: ValidationRunRecord) -> str:
    return f"{record.validation_run_id}: {record.command_id} {record.status.value} exit={record.exit_code if record.exit_code is not None else 'none'}"


def _approval_evidence(project_name: str, run_id: str | None, task_id: str | None, workspace_root: Path) -> list[str]:
    if not run_id or not task_id:
        return ["No run/task supplied; approval ledger not checked."]
    evidence: list[str] = []
    for action in ("git_commit", "git_push"):
        try:
            approval = find_matching_approved_approval(project_name, run_id, task_id, action, workspace_root=workspace_root)
        except ValueError as exc:
            evidence.append(f"{action}: policy/ledger check unavailable ({exc})")
            continue
        if approval and approval.status == DevoApprovalStatus.APPROVED:
            evidence.append(f"{action}: approved by {approval.approved_by or 'unknown'} ({approval.approval_id})")
        else:
            evidence.append(f"{action}: no matching approved Devo approval record")
    evidence.append("Devo approval records do not bypass Codex, OS, or GitHub approval policy.")
    return evidence


def _readiness(blockers: list[str], warnings: list[str], status: GitRepositoryStatus) -> GitDeliveryReadiness:
    if blockers:
        return GitDeliveryReadiness.BLOCKED
    if warnings or not status.working_tree_clean:
        return GitDeliveryReadiness.WARNING
    return GitDeliveryReadiness.READY


def _suggest_commit_command(status: GitRepositoryStatus, commit_message: str | None) -> str | None:
    if status.working_tree_clean:
        return None
    message = commit_message or "<commit message>"
    return f"git commit -m {shlex.quote(message)}"


def _suggest_push_command(status: GitRepositoryStatus) -> str | None:
    if status.ahead and status.ahead > 0:
        branch = status.current_branch or "HEAD"
        return f"git push origin {branch}"
    return None


def _next_human_action(
    readiness: GitDeliveryReadiness,
    status: GitRepositoryStatus,
    suggested_commit: str | None,
    suggested_push: str | None,
) -> str:
    if readiness == GitDeliveryReadiness.BLOCKED:
        return "Resolve delivery blockers before committing or pushing."
    if suggested_push:
        return f"Review the report, then push deliberately if intended. If push is blocked by Codex approval policy, user must run git push manually: {suggested_push}"
    if suggested_commit:
        return f"Review changed files, stage intentional changes, and commit when ready: {suggested_commit}"
    if status.working_tree_clean:
        return "No delivery action is needed; the repository appears clean."
    return "Review repository changes before delivery."


def _report_dir(workspace_root: Path, project_name: str, run_id: str | None) -> Path:
    if run_id:
        return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / GIT_DELIVERY_DIR
    return workspace_root / "projects" / project_name / GIT_DELIVERY_DIR


def _render_report_markdown(report: GitDeliveryReport) -> str:
    check = report.delivery_check
    status = check.status
    lines = [
        "# Git Delivery Report",
        "",
        f"- project: {report.project_name}",
        f"- repo path: `{report.repo_path}`",
        f"- run id: {report.run_id or 'none'}",
        f"- task id: {report.task_id or 'none'}",
        f"- created_at: {report.created_at.isoformat()}",
        f"- readiness: {check.readiness.value}",
        "",
        "## Repository",
        f"- branch: {status.current_branch or 'unknown'}",
        f"- head commit: {status.head_commit or 'unknown'}",
        f"- upstream: {status.upstream_branch or 'none'}",
        f"- ahead: {status.ahead if status.ahead is not None else 'unknown'}",
        f"- behind: {status.behind if status.behind is not None else 'unknown'}",
        f"- working tree clean: {status.working_tree_clean}",
        "",
        "## File Status",
        *(_format_file_list("staged", status.staged_files)),
        *(_format_file_list("unstaged", status.unstaged_files)),
        *(_format_file_list("untracked", status.untracked_files)),
        "",
        "## Checks Performed",
        *[f"- {item}" for item in check.checks_performed],
        "",
        "## Blockers",
        *(_format_text_list(check.blockers)),
        "",
        "## Warnings",
        *(_format_text_list(check.warnings)),
        "",
        "## Secret Signals",
        *(_format_text_list([f"{signal.path}: {signal.signal_type}" for signal in check.secret_signals])),
        "",
        "## Validation Evidence",
        *(_format_text_list(check.validation_evidence)),
        "",
        "## Approval Evidence",
        *(_format_text_list(check.approval_evidence)),
        "",
        "## Suggested Commands",
        f"- commit: `{check.suggested_commit_command or 'none'}`",
        f"- push: `{check.suggested_push_command or 'none'}`",
        "",
        "## Next Human Action",
        check.next_human_action,
        "",
        "Note: Devo does not push automatically and does not bypass external approval policies. If push is blocked by Codex approval policy, user must run git push manually.",
    ]
    return "\n".join(lines) + "\n"


def _format_file_list(label: str, files: list[GitFileState]) -> list[str]:
    if not files:
        return [f"- {label}: none"]
    return [f"- {label}: {item.path} ({item.status})" for item in files]


def _format_text_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _single_line(prefix: str, stdout: str, stderr: str) -> str:
    detail = " ".join((stdout or stderr or "").split())
    return f"{prefix}: {detail}" if detail else prefix


def _git_error_detail(completed: subprocess.CompletedProcess[str]) -> str:
    return " ".join((completed.stderr or completed.stdout or "").split())


def _safe_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped

