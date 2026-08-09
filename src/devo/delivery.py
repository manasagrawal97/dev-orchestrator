from __future__ import annotations

import fnmatch
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .git_delivery import get_git_repository_status, run_delivery_check
from .project_planning import (
    QueueItem,
    WorkerReview,
    WorkerRun,
    list_codex_worker_runs,
    load_codex_worker_review,
    load_execution_queue,
)
from .projects import get_workspace_root
from .scanner import load_registered_project

DELIVERY_SCHEMA_VERSION = "1"
DELIVERY_INDEX_JSON = "delivery-index.json"
READY = "ready"
WARNINGS = "warnings"
BLOCKED = "blocked"


class DeliveryCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_worker_run_id: str | None = None
    source_review_id: str | None = None
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    git_status_summary: str
    changed_files: list[str] = Field(default_factory=list)
    staged_files: list[str] = Field(default_factory=list)
    unstaged_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    forbidden_changed_files: list[str] = Field(default_factory=list)
    forbidden_staged_files: list[str] = Field(default_factory=list)
    workspace_artifacts_staged: list[str] = Field(default_factory=list)
    secrets_risk_files: list[str] = Field(default_factory=list)
    validation_evidence_status: str = "not_linked"
    review_status: str = "not_linked"
    queue_item_status: str = "not_linked"
    readiness_status: str = READY
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    readiness_status: str
    blocker_count: int = 0
    warning_count: int = 0
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_worker_run_id: str | None = None
    source_review_id: str | None = None
    path: str
    updated_at: datetime


class DeliveryIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    checks: list[DeliveryIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def delivery_directory(project_name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return root / "projects" / project_name / "delivery"


def delivery_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"{stem}.json", directory / f"{stem}.md"


def run_delivery_readiness_check(
    project_name: str,
    *,
    queue_id: str | None = None,
    item_id: str | None = None,
    write: bool = False,
    workspace_root: Path | None = None,
) -> tuple[DeliveryCheck, Path | None, Path | None]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    delivery_id = _next_delivery_id(project_name, workspace_root=root) if write else "preview"
    now = datetime.now(UTC)
    blockers: list[str] = []
    warnings: list[str] = []
    branch: str | None = None
    remote: str | None = None
    changed_files: list[str] = []
    staged_files: list[str] = []
    unstaged_files: list[str] = []
    untracked_files: list[str] = []
    git_status_summary = "unknown"
    target_repo_path = str(registration.path)
    secret_signal_paths: list[str] = []

    try:
        status = get_git_repository_status(project_name, workspace_root=root)
        target_repo_path = str(status.repo_path)
        branch = status.current_branch
        remote = status.upstream_branch if status.upstream_branch else ("configured" if status.remote_detected else None)
        staged_files = [item.path for item in status.staged_files]
        unstaged_files = [item.path for item in status.unstaged_files]
        untracked_files = [item.path for item in status.untracked_files]
        changed_files = _dedupe([*staged_files, *unstaged_files, *untracked_files])
        git_status_summary = _git_status_summary(staged_files, unstaged_files, untracked_files)
        warnings.extend(status.warnings)
        if not status.working_tree_clean:
            warnings.append("Target repository has uncommitted changes; review them before delivery.")
        if not remote:
            warnings.append("No Git remote/upstream was detected for delivery.")
        legacy_check = run_delivery_check(project_name=project_name, workspace_root=root)
        secret_signal_paths = [signal.path for signal in legacy_check.secret_signals]
    except ValueError as exc:
        blockers.append(str(exc))

    forbidden_changed_files = [path for path in changed_files if _is_forbidden_path(path)]
    forbidden_staged_files = [path for path in staged_files if _is_forbidden_path(path)]
    workspace_artifacts_staged = [path for path in staged_files if _is_workspace_artifact_path(path)]
    secrets_risk_files = _dedupe(
        [
            path
            for path in [*staged_files, *secret_signal_paths]
            if _is_secret_risk_path(path) or path in secret_signal_paths
        ]
    )

    if forbidden_changed_files:
        blockers.append("Forbidden delivery paths are changed: " + ", ".join(forbidden_changed_files))
    if forbidden_staged_files:
        blockers.append("Forbidden delivery paths are staged: " + ", ".join(forbidden_staged_files))
    if workspace_artifacts_staged:
        blockers.append("Workspace artifacts are staged: " + ", ".join(workspace_artifacts_staged))
    if secrets_risk_files:
        blockers.append("Secret-risk files or signals are staged/changed: " + ", ".join(secrets_risk_files))

    queue_item_status = "not_linked"
    review_status = "not_linked"
    validation_evidence_status = "not_linked"
    worker_run: WorkerRun | None = None
    review: WorkerReview | None = None
    normalized_queue_id = queue_id.strip() if queue_id else None
    normalized_item_id = item_id.strip().upper() if item_id else None
    if normalized_queue_id or normalized_item_id:
        if not normalized_queue_id or not normalized_item_id:
            blockers.append("Both --queue and --item are required when linking delivery to a queue item.")
        else:
            queue = load_execution_queue(project_name, normalized_queue_id, workspace_root=root)
            if not queue:
                blockers.append(f"Linked execution queue was not found: {normalized_queue_id}")
            else:
                item = _find_queue_item(queue.items, normalized_item_id)
                if not item:
                    blockers.append(f"Linked queue item was not found: {normalized_item_id}")
                else:
                    queue_item_status = item.status
                    if item.status != "completed":
                        blockers.append(f"Linked queue item {item.item_id} is {item.status}, not completed.")
                    worker_run = _latest_worker_run_for_queue_item(project_name, queue.queue_id, item.item_id, root)
                    if worker_run:
                        review = load_codex_worker_review(project_name, worker_run.worker_run_id, workspace_root=root)
                    else:
                        blockers.append(f"Linked queue item {item.item_id} has no Codex worker run.")

    if worker_run:
        review_status = "missing"
        validation_evidence_status = "missing"
        if not review:
            blockers.append(f"Linked worker run {worker_run.worker_run_id} has no review artifact.")
        else:
            review_status = review.review_status
            validation_evidence_status = review.validation_evidence.validation_status
            if review.review_status != "reviewed_passed":
                blockers.append(f"Linked worker review status is {review.review_status}, not reviewed_passed.")
            if review.validation_evidence.validation_status == "failed":
                blockers.append("Linked worker validation evidence status is failed.")
            elif review.validation_evidence.validation_status != "passed":
                warnings.append(f"Linked worker validation evidence status is {review.validation_evidence.validation_status}, not passed.")

    readiness_status = BLOCKED if blockers else WARNINGS if warnings else READY
    check = DeliveryCheck(
        project=project_name,
        delivery_id=delivery_id,
        source_queue_id=normalized_queue_id,
        source_queue_item_id=normalized_item_id,
        source_worker_run_id=worker_run.worker_run_id if worker_run else None,
        source_review_id=review.review_id if review else None,
        target_repo_path=target_repo_path,
        branch=branch,
        remote=remote,
        git_status_summary=git_status_summary,
        changed_files=changed_files,
        staged_files=staged_files,
        unstaged_files=unstaged_files,
        untracked_files=untracked_files,
        forbidden_changed_files=forbidden_changed_files,
        forbidden_staged_files=forbidden_staged_files,
        workspace_artifacts_staged=workspace_artifacts_staged,
        secrets_risk_files=secrets_risk_files,
        validation_evidence_status=validation_evidence_status,
        review_status=review_status,
        queue_item_status=queue_item_status,
        readiness_status=readiness_status,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
        next_action=_next_action(readiness_status),
        created_at=now,
        updated_at=now,
    )
    if not write:
        return check, None, None
    json_path, markdown_path = write_delivery_check(check, workspace_root=root)
    return check, json_path, markdown_path


def write_delivery_check(check: DeliveryCheck, workspace_root: Path | None = None) -> tuple[Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(check.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_artifact_paths(check.project, check.delivery_id, workspace_root=root)
    json_path.write_text(check.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_check_markdown(check), encoding="utf-8")
    _write_delivery_index(check.project, workspace_root=root)
    return json_path, markdown_path


def load_delivery_check(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryCheck | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryCheck.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_checks(project_name: str, workspace_root: Path | None = None) -> list[DeliveryCheck]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    checks: list[DeliveryCheck] = []
    for path in sorted(directory.glob("del-*.json")):
        if path.name == DELIVERY_INDEX_JSON:
            continue
        try:
            checks.append(DeliveryCheck.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(checks, key=lambda item: item.updated_at, reverse=True)


def load_delivery_index(project_name: str, workspace_root: Path | None = None) -> DeliveryIndex:
    root = workspace_root or get_workspace_root()
    path = delivery_directory(project_name, workspace_root=root) / DELIVERY_INDEX_JSON
    if not path.exists():
        return DeliveryIndex(project=project_name)
    return DeliveryIndex.model_validate_json(path.read_text(encoding="utf-8"))


def render_delivery_check_markdown(check: DeliveryCheck) -> str:
    return "\n".join(
        [
            f"# Delivery Readiness Check: {check.delivery_id}",
            "",
            f"- Project: `{check.project}`",
            f"- Readiness: `{check.readiness_status}`",
            f"- Target repo: `{check.target_repo_path}`",
            f"- Branch: `{check.branch or 'unknown'}`",
            f"- Remote/upstream: `{check.remote or 'unknown'}`",
            f"- Git status: `{check.git_status_summary}`",
            f"- Queue item: `{check.source_queue_id or 'not linked'} / {check.source_queue_item_id or 'not linked'}`",
            f"- Queue item status: `{check.queue_item_status}`",
            f"- Worker run: `{check.source_worker_run_id or 'not linked'}`",
            f"- Review status: `{check.review_status}`",
            f"- Validation evidence status: `{check.validation_evidence_status}`",
            "",
            "## Files",
            "",
            f"- Changed: {len(check.changed_files)}",
            f"- Staged: {len(check.staged_files)}",
            f"- Unstaged: {len(check.unstaged_files)}",
            f"- Untracked: {len(check.untracked_files)}",
            f"- Forbidden changed: {len(check.forbidden_changed_files)}",
            f"- Forbidden staged: {len(check.forbidden_staged_files)}",
            f"- Workspace artifacts staged: {len(check.workspace_artifacts_staged)}",
            f"- Secret-risk files/signals: {len(check.secrets_risk_files)}",
            "",
            "## Blockers",
            "",
            *_markdown_list(check.blockers),
            "",
            "## Warnings",
            "",
            *_markdown_list(check.warnings),
            "",
            "## Next Action",
            "",
            check.next_action,
            "",
        ]
    )


def _write_delivery_index(project_name: str, workspace_root: Path | None = None) -> DeliveryIndex:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    checks = list_delivery_checks(project_name, workspace_root=root)
    entries = [
        DeliveryIndexEntry(
            delivery_id=check.delivery_id,
            readiness_status=check.readiness_status,
            blocker_count=len(check.blockers),
            warning_count=len(check.warnings),
            source_queue_id=check.source_queue_id,
            source_queue_item_id=check.source_queue_item_id,
            source_worker_run_id=check.source_worker_run_id,
            source_review_id=check.source_review_id,
            path=str(delivery_artifact_paths(project_name, check.delivery_id, workspace_root=root)[0]),
            updated_at=check.updated_at,
        )
        for check in checks
    ]
    index = DeliveryIndex(project=project_name, checks=entries, updated_at=datetime.now(UTC))
    (directory / DELIVERY_INDEX_JSON).write_text(index.model_dump_json(indent=2), encoding="utf-8")
    return index


def _next_delivery_id(project_name: str, workspace_root: Path | None = None) -> str:
    checks = list_delivery_checks(project_name, workspace_root=workspace_root)
    highest = 0
    for check in checks:
        try:
            highest = max(highest, int(check.delivery_id.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"DEL-{highest + 1:04d}"


def _latest_worker_run_for_queue_item(project_name: str, queue_id: str, item_id: str, workspace_root: Path) -> WorkerRun | None:
    normalized_queue = queue_id.strip()
    normalized_item = item_id.strip().upper()
    return next(
        (
            worker_run
            for worker_run in list_codex_worker_runs(project_name, workspace_root=workspace_root)
            if worker_run.source_queue_id == normalized_queue and worker_run.source_queue_item_id == normalized_item
        ),
        None,
    )


def _find_queue_item(items: list[QueueItem], item_id: str) -> QueueItem | None:
    normalized = item_id.strip().upper()
    return next((item for item in items if item.item_id.upper() == normalized), None)


def _git_status_summary(staged: list[str], unstaged: list[str], untracked: list[str]) -> str:
    if not staged and not unstaged and not untracked:
        return "clean"
    return f"staged {len(staged)}, unstaged {len(unstaged)}, untracked {len(untracked)}"


def _is_forbidden_path(path: str) -> bool:
    normalized = _normalize_git_path(path)
    first = normalized.split("/", 1)[0]
    forbidden_dirs = {
        ".venv",
        ".pytest_cache",
        "backup",
        "backups",
        "node_modules",
        "restore-test",
        "workspace",
    }
    if first in forbidden_dirs or fnmatch.fnmatch(first, "pt-*"):
        return True
    if normalized.startswith("ui/node_modules/") or normalized.startswith("ui/dist/") or normalized.startswith("ui/coverage/"):
        return True
    if normalized == ".env" or normalized.endswith("/.env") or fnmatch.fnmatch(normalized, "*.env"):
        return True
    if fnmatch.fnmatch(normalized.lower(), "appsettings.*.json"):
        return True
    if any(normalized.lower().endswith(suffix) for suffix in (".key", ".pem", ".pfx")):
        return True
    lower_name = Path(normalized).name.lower()
    return "secret" in lower_name or "password" in lower_name


def _is_workspace_artifact_path(path: str) -> bool:
    return _normalize_git_path(path).startswith("workspace/")


def _is_secret_risk_path(path: str) -> bool:
    normalized = _normalize_git_path(path)
    lower = normalized.lower()
    name = Path(lower).name
    return (
        normalized == ".env"
        or normalized.endswith("/.env")
        or fnmatch.fnmatch(normalized, "*.env")
        or fnmatch.fnmatch(lower, "appsettings.*.json")
        or lower.endswith((".key", ".pem", ".pfx"))
        or "secret" in name
        or "password" in name
    )


def _normalize_git_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _next_action(readiness_status: str) -> str:
    if readiness_status == BLOCKED:
        return "Resolve delivery blockers before requesting delivery approval."
    if readiness_status == WARNINGS:
        return "Review warnings, then rerun delivery check before delivery approval."
    return "Ready for a future delivery approval plan; commit/push remain manual and deferred."


def _markdown_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
