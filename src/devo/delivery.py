from __future__ import annotations

import fnmatch
import getpass
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .git_delivery import GLOBAL_IGNORE_WARNING_DETAIL, get_git_repository_status, run_delivery_check
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
    secret_warning_files: list[str] = Field(default_factory=list)
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


class DeliveryPlanIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    delivery_status: str
    approval_status: str
    readiness_status: str
    blocker_count: int = 0
    warning_count: int = 0
    intended_commit_message: str
    path: str
    updated_at: datetime


class DeliveryApprovalIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    approval_status: str
    readiness_status: str
    blocker_count: int = 0
    warning_count: int = 0
    path: str
    updated_at: datetime


class DeliveryReportIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_id: str
    final_status: str
    commit_ready: bool = False
    push_ready: bool = False
    proposed_commit_message: str
    path: str
    updated_at: datetime


class DeliveryIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    checks: list[DeliveryIndexEntry] = Field(default_factory=list)
    plans: list[DeliveryPlanIndexEntry] = Field(default_factory=list)
    approvals: list[DeliveryApprovalIndexEntry] = Field(default_factory=list)
    reports: list[DeliveryReportIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    source_delivery_check_id: str
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_worker_run_id: str | None = None
    source_review_id: str | None = None
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    intended_commit_message: str
    changed_files: list[str] = Field(default_factory=list)
    staged_files: list[str] = Field(default_factory=list)
    unstaged_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    validation_evidence_status: str = "not_linked"
    review_status: str = "not_linked"
    readiness_status: str = READY
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    approval_status: str = "not_requested"
    delivery_status: str = "planned"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str


class DeliveryApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    approval_status: str = "not_requested"
    requested_at: datetime | None = None
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    reviewer: str | None = None
    approver: str | None = None
    decision_note: str = ""
    approval_notes: list[str] = Field(default_factory=list)
    readiness_status: str = READY
    blocker_count: int = 0
    warning_count: int = 0
    changed_file_count: int = 0
    staged_file_count: int = 0
    validation_evidence_status: str = "not_linked"
    review_status: str = "not_linked"
    next_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    source_delivery_plan_id: str
    source_delivery_check_id: str | None = None
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_worker_run_id: str | None = None
    source_review_id: str | None = None
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    intended_commit_message: str
    proposed_commit_message: str
    changed_files: list[str] = Field(default_factory=list)
    staged_files: list[str] = Field(default_factory=list)
    unstaged_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    validation_summary: str
    review_summary: str
    safety_scan_summary: str
    blocker_summary: str
    warning_summary: str
    approval_status: str
    delivery_readiness_status: str
    readiness_snapshot_status: str | None = None
    readiness_snapshot_at: datetime | None = None
    readiness_currentness: str = "current"
    readiness_snapshot_note: str = "Readiness snapshot captured at report preparation time."
    commit_ready: bool = False
    push_ready: bool = False
    commit_hash: str | None = None
    pushed: bool = False
    push_remote: str | None = None
    push_branch: str | None = None
    push_status: str | None = None
    pushed_at: datetime | None = None
    final_status: str = "draft"
    recovery_status: str = "none"
    recovery_reason: str = ""
    recovery_note: str = ""
    recovery_history: list[str] = Field(default_factory=list)
    last_commit_failure_category: str | None = None
    last_commit_failure_message: str | None = None
    last_commit_failure_retryable: bool = False
    refreshed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str


class DeliveryReportRefresh(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    recovery_status: str
    recovery_reason: str
    reopened: bool = False
    reopen_allowed: bool = False
    approval_status: str
    current_readiness_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_status: str
    commit_ready: bool = False
    next_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryCommitPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    proposed_commit_message: str
    effective_commit_message: str
    eligible_files: list[str] = Field(default_factory=list)
    blocked_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    delivery_readiness_status: str
    commit_ready: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str


class DeliveryCommitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    status: str
    commit_hash: str | None = None
    commit_message: str
    eligible_files: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    failure_category: str | None = None
    failure_retryable: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str


class DeliveryCommitDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    target_repo_path: str
    branch: str | None = None
    upstream: str | None = None
    git_executable_path: str | None = None
    git_version: str | None = None
    git_dir_path: str | None = None
    git_dir_exists: bool = False
    git_dir_attributes: list[str] = Field(default_factory=list)
    git_dir_acl_summary: list[str] = Field(default_factory=list)
    git_index_path: str | None = None
    git_index_exists: bool = False
    git_index_size: int | None = None
    git_index_attributes: list[str] = Field(default_factory=list)
    git_index_acl_summary: list[str] = Field(default_factory=list)
    git_index_lock_path: str | None = None
    git_index_lock_exists: bool = False
    staged_files: list[str] = Field(default_factory=list)
    unstaged_files: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    report_final_status: str
    report_commit_ready: bool
    plan_approval_status: str
    approval_status: str
    last_commit_failure_category: str | None = None
    last_commit_failure_message: str | None = None
    last_commit_failure_retryable: bool = False
    failure_looks_retryable: bool = False
    possible_causes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    probe_requested: bool = False
    probe_ran: bool = False
    can_create_index_lock: bool | None = None
    probe_error: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class IndexLockProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    category: str | None = None
    message: str = ""
    lock_path: str | None = None
    created: bool = False
    removed: bool = False
    cleanup_error: str = ""


class DeliveryPushPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    source_commit_hash: str | None = None
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    push_remote: str | None = None
    push_branch: str | None = None
    push_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str


class DeliveryPush(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    delivery_id: str
    source_delivery_report_id: str
    source_commit_hash: str | None = None
    target_repo_path: str
    branch: str | None = None
    remote: str | None = None
    push_remote: str | None = None
    push_branch: str | None = None
    push_status: str = "preview"
    pushed: bool = False
    pushed_at: datetime | None = None
    push_exit_code: int | None = None
    push_stdout: str = ""
    push_stderr: str = ""
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryLatestSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    target_repo_path: str
    current_git_status_summary: str = "unknown"
    current_repo_is_clean: bool = False
    current_repo_has_pending_changes: bool = False
    latest_delivery_check_id: str | None = None
    latest_delivery_check_status: str | None = None
    latest_delivery_check_is_empty: bool = False
    latest_meaningful_delivery_check_id: str | None = None
    latest_meaningful_delivery_check_status: str | None = None
    latest_plan_id: str | None = None
    latest_plan_status: str | None = None
    latest_approval_id: str | None = None
    latest_approval_status: str | None = None
    latest_report_id: str | None = None
    latest_report_status: str | None = None
    latest_commit_result_id: str | None = None
    latest_commit_result_status: str | None = None
    latest_commit_hash: str | None = None
    latest_push_result_id: str | None = None
    latest_push_result_status: str | None = None
    latest_pushed_delivery_id: str | None = None
    latest_pushed_at: str | None = None
    latest_runner_request_id: str | None = None
    latest_runner_request_status: str | None = None
    latest_runner_run_id: str | None = None
    latest_runner_run_status: str | None = None
    latest_runner_commit_hash: str | None = None
    latest_runner_pushed: bool | None = None
    latest_runner_changed_file_count: int | None = None
    latest_runner_next_action: str | None = None
    next_action: str
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryRunnerRequestIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    status: str
    intended_commit_message: str
    changed_file_count: int = 0
    latest_run_status: str | None = None
    path: str
    updated_at: datetime


class DeliveryRunnerRequestIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    requests: list[DeliveryRunnerRequestIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeliveryRunnerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    request_id: str
    requested_by: str
    requested_from_context: str
    target_repo_path: str
    intended_commit_message: str
    note: str = ""
    expected_changed_files: list[str] = Field(default_factory=list)
    allowed_changed_files: list[str] = Field(default_factory=list)
    forbidden_changed_files: list[str] = Field(default_factory=list)
    validation_summary: str | None = None
    test_summary: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = "requested"
    next_action: str


class DeliveryRunnerRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    request_id: str
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    runner_context: str
    index_lock_probe_result: dict[str, object] = Field(default_factory=dict)
    delivery_check_id: str | None = None
    delivery_plan_id: str | None = None
    delivery_report_id: str | None = None
    commit_hash: str | None = None
    pushed: bool = False
    push_remote: str | None = None
    push_branch: str | None = None
    status: str = "failed"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    steps_run: list[str] = Field(default_factory=list)
    next_action: str


class DeliveryRunnerWatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = DELIVERY_SCHEMA_VERSION
    project: str
    watch_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    mode: str = "once"
    approver: str
    pending_request_count: int = 0
    selected_request_id: str | None = None
    selected_run_id: str | None = None
    delivery_id: str | None = None
    status: str = "failed"
    commit_hash: str | None = None
    pushed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    steps_run: list[str] = Field(default_factory=list)
    next_action: str


def delivery_directory(project_name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return root / "projects" / project_name / "delivery"


def delivery_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"{stem}.json", directory / f"{stem}.md"


def delivery_plan_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"delivery-plan-{stem}.json", directory / f"delivery-plan-{stem}.md"


def delivery_approval_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"delivery-approval-{stem}.json", directory / f"delivery-approval-{stem}.md"


def delivery_report_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"delivery-report-{stem}.json", directory / f"delivery-report-{stem}.md"


def delivery_commit_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"delivery-commit-{stem}.json", directory / f"delivery-commit-{stem}.md"


def delivery_push_artifact_paths(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_directory(project_name, workspace_root=workspace_root)
    stem = delivery_id.lower()
    return directory / f"delivery-push-{stem}.json", directory / f"delivery-push-{stem}.md"


def delivery_runner_request_directory(project_name: str, workspace_root: Path | None = None) -> Path:
    return delivery_directory(project_name, workspace_root=workspace_root) / "runner-requests"


def delivery_runner_request_index_path(project_name: str, workspace_root: Path | None = None) -> Path:
    return delivery_runner_request_directory(project_name, workspace_root=workspace_root) / "runner-request-index.json"


def delivery_runner_request_artifact_paths(project_name: str, request_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_runner_request_directory(project_name, workspace_root=workspace_root)
    stem = request_id.lower()
    return directory / f"runner-request-{stem}.json", directory / f"runner-request-{stem}.md"


def delivery_runner_run_artifact_paths(project_name: str, request_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_runner_request_directory(project_name, workspace_root=workspace_root)
    stem = request_id.lower()
    return directory / f"runner-run-{stem}.json", directory / f"runner-run-{stem}.md"


def delivery_runner_watch_artifact_paths(project_name: str, watch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    directory = delivery_runner_request_directory(project_name, workspace_root=workspace_root)
    stem = watch_id.lower()
    return directory / f"runner-watch-{stem}.json", directory / f"runner-watch-{stem}.md"


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
    secret_warning_files = _documentation_secret_mention_paths(Path(target_repo_path), changed_files, secret_signal_paths)
    if secret_warning_files:
        warnings.append("Documentation-only secret terms detected; review manually if needed: " + ", ".join(secret_warning_files))

    secrets_risk_files = _dedupe(
        [
            path
            for path in [*changed_files, *secret_signal_paths]
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

    readiness_status = BLOCKED if blockers else WARNINGS if any(_warning_affects_readiness(warning) for warning in warnings) else READY
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
        secret_warning_files=secret_warning_files,
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


def create_delivery_plan(
    project_name: str,
    delivery_id: str,
    intended_commit_message: str,
    workspace_root: Path | None = None,
) -> tuple[DeliveryPlan, Path, Path]:
    root = workspace_root or get_workspace_root()
    check = load_delivery_check(project_name, delivery_id, workspace_root=root)
    if not check:
        msg = f"Delivery check not found: {delivery_id}"
        raise ValueError(msg)
    message = intended_commit_message.strip()
    if not message:
        msg = "Intended commit message is required."
        raise ValueError(msg)
    now = datetime.now(UTC)
    delivery_status = "blocked" if check.readiness_status == BLOCKED else "planned"
    plan = DeliveryPlan(
        project=project_name,
        delivery_id=check.delivery_id,
        source_delivery_check_id=check.delivery_id,
        source_queue_id=check.source_queue_id,
        source_queue_item_id=check.source_queue_item_id,
        source_worker_run_id=check.source_worker_run_id,
        source_review_id=check.source_review_id,
        target_repo_path=check.target_repo_path,
        branch=check.branch,
        remote=check.remote,
        intended_commit_message=message,
        changed_files=check.changed_files,
        staged_files=check.staged_files,
        unstaged_files=check.unstaged_files,
        untracked_files=check.untracked_files,
        allowed_scope=[],
        forbidden_scope=_dedupe(
            [
                *check.forbidden_changed_files,
                *check.forbidden_staged_files,
                *check.workspace_artifacts_staged,
                *check.secrets_risk_files,
            ]
        ),
        validation_evidence_status=check.validation_evidence_status,
        review_status=check.review_status,
        readiness_status=check.readiness_status,
        blockers=check.blockers,
        warnings=check.warnings,
        approval_status="not_requested",
        delivery_status=delivery_status,
        created_at=now,
        updated_at=now,
        next_action=_plan_next_action(delivery_status, "not_requested"),
    )
    return write_delivery_plan(plan, workspace_root=root)


def write_delivery_plan(plan: DeliveryPlan, workspace_root: Path | None = None) -> tuple[DeliveryPlan, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(plan.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_plan_artifact_paths(plan.project, plan.delivery_id, workspace_root=root)
    json_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_plan_markdown(plan), encoding="utf-8")
    _write_delivery_index(plan.project, workspace_root=root)
    return plan, json_path, markdown_path


def load_delivery_plan(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryPlan | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_plan_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryPlan.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_plans(project_name: str, workspace_root: Path | None = None) -> list[DeliveryPlan]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    plans: list[DeliveryPlan] = []
    for path in sorted(directory.glob("delivery-plan-*.json")):
        try:
            plans.append(DeliveryPlan.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(plans, key=lambda item: item.updated_at, reverse=True)


def request_delivery_approval(
    project_name: str,
    delivery_id: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[DeliveryApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    plan = _require_delivery_plan(project_name, delivery_id, root)
    existing = load_delivery_approval(project_name, delivery_id, workspace_root=root)
    now = datetime.now(UTC)
    approval = _approval_from_plan(plan, existing=existing).model_copy(
        update={
            "approval_status": "requested",
            "requested_at": existing.requested_at if existing and existing.requested_at else now,
            "reviewed_at": None,
            "approved_at": None,
            "rejected_at": None,
            "decision_note": note.strip(),
            "approval_notes": [*_existing_notes(existing), note.strip() or "Delivery approval requested."],
            "next_action": f"Review delivery approval: devo delivery approve --project {project_name} --plan {delivery_id} --approver \"<name>\" --note \"<note>\"",
            "updated_at": now,
        }
    )
    plan = plan.model_copy(update={"approval_status": "requested", "updated_at": now, "next_action": _plan_next_action(plan.delivery_status, "requested")})
    write_delivery_plan(plan, workspace_root=root)
    return write_delivery_approval(approval, workspace_root=root)


def approve_delivery_plan(
    project_name: str,
    delivery_id: str,
    approver: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[DeliveryPlan, DeliveryApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    plan = _require_delivery_plan(project_name, delivery_id, root)
    if plan.readiness_status == BLOCKED or plan.delivery_status == "blocked":
        msg = "Blocked delivery plans cannot be approved. Resolve blockers and create a new readiness check/plan."
        raise ValueError(msg)
    existing = load_delivery_approval(project_name, delivery_id, workspace_root=root)
    now = datetime.now(UTC)
    approval = _approval_from_plan(plan, existing=existing).model_copy(
        update={
            "approval_status": "approved",
            "reviewed_at": now,
            "approved_at": now,
            "rejected_at": None,
            "reviewer": approver.strip() or None,
            "approver": approver.strip() or None,
            "decision_note": note.strip(),
            "approval_notes": [*_existing_notes(existing), note.strip() or "Delivery plan approved."],
            "next_action": "Prepare a delivery report, then preview any guarded CLI commit before committing.",
            "updated_at": now,
        }
    )
    plan = plan.model_copy(
        update={
            "approval_status": "approved",
            "delivery_status": "approved",
            "updated_at": now,
            "next_action": "Prepare a delivery report with devo delivery report-prepare before guarded commit.",
        }
    )
    write_delivery_plan(plan, workspace_root=root)
    approval, json_path, markdown_path = write_delivery_approval(approval, workspace_root=root)
    return plan, approval, json_path, markdown_path


def reject_delivery_plan(
    project_name: str,
    delivery_id: str,
    reviewer: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[DeliveryPlan, DeliveryApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    plan = _require_delivery_plan(project_name, delivery_id, root)
    existing = load_delivery_approval(project_name, delivery_id, workspace_root=root)
    now = datetime.now(UTC)
    approval = _approval_from_plan(plan, existing=existing).model_copy(
        update={
            "approval_status": "rejected",
            "reviewed_at": now,
            "approved_at": None,
            "rejected_at": now,
            "reviewer": reviewer.strip() or None,
            "decision_note": note.strip(),
            "approval_notes": [*_existing_notes(existing), note.strip() or "Delivery plan rejected."],
            "next_action": "Revise the delivery plan or resolve blockers before requesting approval again.",
            "updated_at": now,
        }
    )
    plan = plan.model_copy(
        update={
            "approval_status": "rejected",
            "delivery_status": "rejected",
            "updated_at": now,
            "next_action": "Delivery rejected; revise the plan before any future delivery step.",
        }
    )
    write_delivery_plan(plan, workspace_root=root)
    approval, json_path, markdown_path = write_delivery_approval(approval, workspace_root=root)
    return plan, approval, json_path, markdown_path


def write_delivery_approval(approval: DeliveryApproval, workspace_root: Path | None = None) -> tuple[DeliveryApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(approval.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_approval_artifact_paths(approval.project, approval.delivery_id, workspace_root=root)
    json_path.write_text(approval.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_approval_markdown(approval), encoding="utf-8")
    _write_delivery_index(approval.project, workspace_root=root)
    return approval, json_path, markdown_path


def load_delivery_approval(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryApproval | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_approval_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryApproval.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_approvals(project_name: str, workspace_root: Path | None = None) -> list[DeliveryApproval]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    approvals: list[DeliveryApproval] = []
    for path in sorted(directory.glob("delivery-approval-*.json")):
        try:
            approvals.append(DeliveryApproval.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(approvals, key=lambda item: item.updated_at, reverse=True)


def prepare_delivery_report(
    project_name: str,
    delivery_id: str,
    workspace_root: Path | None = None,
) -> tuple[DeliveryReport, Path, Path]:
    root = workspace_root or get_workspace_root()
    plan = _require_delivery_plan(project_name, delivery_id, root)
    if plan.approval_status != "approved":
        msg = f"Delivery plan {delivery_id} is not approved."
        raise ValueError(msg)
    current_check, _json_path, _markdown_path = run_delivery_readiness_check(
        project_name,
        queue_id=plan.source_queue_id,
        item_id=plan.source_queue_item_id,
        write=False,
        workspace_root=root,
    )
    blockers = _dedupe([*plan.blockers, *current_check.blockers])
    warnings = _dedupe([*plan.warnings, *current_check.warnings])
    final_status = "blocked" if blockers or current_check.readiness_status == BLOCKED else "ready"
    commit_ready = plan.approval_status == "approved" and final_status == "ready"
    report = DeliveryReport(
        project=project_name,
        delivery_id=plan.delivery_id,
        source_delivery_plan_id=plan.delivery_id,
        source_delivery_check_id=plan.source_delivery_check_id,
        source_queue_id=plan.source_queue_id,
        source_queue_item_id=plan.source_queue_item_id,
        source_worker_run_id=plan.source_worker_run_id,
        source_review_id=plan.source_review_id,
        target_repo_path=current_check.target_repo_path,
        branch=current_check.branch,
        remote=current_check.remote,
        intended_commit_message=plan.intended_commit_message,
        proposed_commit_message=propose_delivery_commit_message(plan),
        changed_files=current_check.changed_files,
        staged_files=current_check.staged_files,
        unstaged_files=current_check.unstaged_files,
        untracked_files=current_check.untracked_files,
        validation_summary=f"Validation evidence status: {current_check.validation_evidence_status}",
        review_summary=f"Worker review status: {current_check.review_status}",
        safety_scan_summary=_safety_scan_summary(current_check),
        blocker_summary=_summary_text(blockers),
        warning_summary=_summary_text(warnings),
        approval_status=plan.approval_status,
        delivery_readiness_status=current_check.readiness_status,
        readiness_snapshot_status=current_check.readiness_status,
        readiness_snapshot_at=current_check.updated_at,
        readiness_currentness="current",
        readiness_snapshot_note="Readiness snapshot captured at report preparation time.",
        commit_ready=commit_ready,
        push_ready=False,
        commit_hash=None,
        pushed=False,
        final_status=final_status,
        next_action=_report_next_action(final_status, commit_ready),
    )
    return write_delivery_report(report, workspace_root=root)


def refresh_delivery_report(
    project_name: str,
    delivery_id: str,
    *,
    note: str = "",
    reopen: bool = False,
    workspace_root: Path | None = None,
) -> tuple[DeliveryReportRefresh, DeliveryReport, Path, Path]:
    root = workspace_root or get_workspace_root()
    report = _require_delivery_report(project_name, delivery_id, root)
    _hydrate_commit_failure_metadata(report, workspace_root=root)
    plan = _require_delivery_plan(project_name, report.source_delivery_plan_id, root)
    approval = load_delivery_approval(project_name, plan.delivery_id, workspace_root=root)
    current_check, _json_path, _markdown_path = run_delivery_readiness_check(
        project_name,
        queue_id=report.source_queue_id,
        item_id=report.source_queue_item_id,
        write=False,
        workspace_root=root,
    )
    _hydrate_commit_failure_metadata(report, workspace_root=root)

    blockers = list(current_check.blockers)
    warnings = _dedupe([*current_check.warnings])
    approval_status = plan.approval_status
    approval_is_approved = approval_status == "approved" and bool(approval and approval.approval_status == "approved")
    current_blocked = current_check.readiness_status == BLOCKED or bool(blockers)
    retryable_blocked_report = (
        report.final_status == "blocked"
        and report.last_commit_failure_retryable
        and bool(report.last_commit_failure_category)
    )
    already_committed = bool(report.commit_hash)
    already_pushed = report.pushed or report.final_status == "pushed"

    reopened = False
    reopen_allowed = False
    recovery_status = "refresh_only"
    recovery_reason = "Current delivery readiness snapshot refreshed."

    if already_pushed:
        recovery_status = "refused" if reopen else "refresh_only"
        recovery_reason = "Delivery report is already pushed; reopening for commit is not allowed."
    elif already_committed:
        recovery_status = "refused" if reopen else "refresh_only"
        recovery_reason = "Delivery report already has a commit hash; refresh is snapshot-only."
    elif not approval_is_approved:
        recovery_status = "refused" if reopen else "refresh_only"
        recovery_reason = "Delivery plan and approval must both be approved before reopening."
    elif current_blocked:
        recovery_status = "refused" if reopen else "refresh_only"
        recovery_reason = "Current delivery readiness is blocked; fix blockers before reopening."
        report.final_status = "blocked"
        report.commit_ready = False
        report.push_ready = False
        report.blocker_summary = _summary_text(blockers)
    elif retryable_blocked_report:
        reopen_allowed = True
        recovery_status = "reopened" if reopen else "reopen_allowed"
        recovery_reason = "Previous guarded commit failure appears retryable and current readiness has no blockers."
        if reopen:
            reopened = True
            report.final_status = "ready"
            report.commit_ready = True
            report.push_ready = False
            report.blocker_summary = "none"
    elif report.final_status == "ready":
        recovery_status = "refresh_only"
        recovery_reason = "Delivery report is already ready."
        report.commit_ready = approval_is_approved and not current_blocked
    else:
        recovery_status = "refused" if reopen else "refresh_only"
        recovery_reason = "Delivery report is not a retryable blocked commit report."

    _refresh_report_snapshot(report, current_check, plan)
    report.approval_status = approval_status
    report.warning_summary = _summary_text(warnings)
    if report.final_status == "ready" and report.commit_ready:
        report.next_action = _report_next_action(report.final_status, report.commit_ready)
    elif already_committed and not already_pushed:
        report.next_action = (
            f"Report refreshed. Commit exists; run devo delivery push-preview --project {project_name} "
            f"--report {delivery_id} before guarded push."
        )
    elif reopen_allowed and not reopen:
        report.next_action = (
            f"Reopen allowed. Run devo delivery report-refresh --project {project_name} --report {delivery_id} "
            '--reopen --note "<reason>", then run commit-preview.'
        )
    elif recovery_status == "refused":
        report.next_action = recovery_reason
    elif report.final_status == "blocked":
        report.next_action = "Resolve delivery report blockers before retrying."
    else:
        report.next_action = _report_next_action(report.final_status, report.commit_ready)

    report.recovery_status = recovery_status
    report.recovery_reason = recovery_reason
    report.recovery_note = note.strip()
    report.refreshed_at = datetime.now(UTC)
    history_note = _recovery_history_note(report.refreshed_at, recovery_status, recovery_reason, note)
    report.recovery_history = [*report.recovery_history, history_note]
    report.updated_at = report.refreshed_at
    report, report_json, report_markdown = write_delivery_report(report, workspace_root=root)

    result = DeliveryReportRefresh(
        project=project_name,
        delivery_id=delivery_id,
        recovery_status=recovery_status,
        recovery_reason=recovery_reason,
        reopened=reopened,
        reopen_allowed=reopen_allowed,
        approval_status=approval_status,
        current_readiness_status=current_check.readiness_status,
        blockers=blockers,
        warnings=warnings,
        final_status=report.final_status,
        commit_ready=report.commit_ready,
        next_action=report.next_action,
    )
    return result, report, report_json, report_markdown


def run_delivery_commit_diagnostics(
    project_name: str,
    delivery_id: str,
    *,
    index_lock_probe: bool = False,
    confirm_probe: bool = False,
    workspace_root: Path | None = None,
) -> DeliveryCommitDiagnostics:
    root = workspace_root or get_workspace_root()
    report = _require_delivery_report(project_name, delivery_id, root)
    _hydrate_commit_failure_metadata(report, workspace_root=root)
    plan = _require_delivery_plan(project_name, report.source_delivery_plan_id, root)
    approval = load_delivery_approval(project_name, plan.delivery_id, workspace_root=root)
    if index_lock_probe and not confirm_probe:
        msg = "--confirm-probe is required with --index-lock-probe."
        raise ValueError(msg)

    current_check, _json_path, _markdown_path = run_delivery_readiness_check(
        project_name,
        queue_id=report.source_queue_id,
        item_id=report.source_queue_item_id,
        write=False,
        workspace_root=root,
    )
    repo_path = Path(current_check.target_repo_path)
    git_dir = _resolve_git_dir(repo_path)
    git_index = git_dir / "index" if git_dir else None
    git_index_lock = git_dir / "index.lock" if git_dir else None
    git_version = _git_version()
    git_executable = shutil.which("git")
    git_index_exists = bool(git_index and git_index.exists())
    git_index_size = git_index.stat().st_size if git_index_exists and git_index else None
    warnings = list(current_check.warnings)
    if index_lock_probe:
        warnings.append(
            "Index-lock probe was explicitly requested. Operator must ensure no other Git process is active."
        )
    possible_causes = _commit_failure_possible_causes(report.last_commit_failure_category)
    next_actions = _commit_diagnostics_next_actions(project_name, delivery_id, report)
    probe_ran = False
    can_create_index_lock: bool | None = None
    probe_error = ""

    if index_lock_probe and git_index_lock:
        probe_ran = True
        probe = _probe_git_index_lock(repo_path)
        can_create_index_lock = probe.ok
        probe_error = "" if probe.ok else probe.message
        if probe.cleanup_error:
            warnings.append("WARNING: .git/index.lock still exists after probe cleanup failure.")

    return DeliveryCommitDiagnostics(
        project=project_name,
        delivery_id=delivery_id,
        target_repo_path=str(repo_path),
        branch=current_check.branch,
        upstream=current_check.remote,
        git_executable_path=git_executable,
        git_version=git_version,
        git_dir_path=str(git_dir) if git_dir else None,
        git_dir_exists=bool(git_dir and git_dir.exists()),
        git_dir_attributes=_path_attribute_summary(git_dir) if git_dir else ["git dir unavailable"],
        git_dir_acl_summary=_windows_acl_summary(git_dir) if git_dir else [],
        git_index_path=str(git_index) if git_index else None,
        git_index_exists=git_index_exists,
        git_index_size=git_index_size,
        git_index_attributes=_path_attribute_summary(git_index) if git_index else ["index path unavailable"],
        git_index_acl_summary=_windows_acl_summary(git_index) if git_index else [],
        git_index_lock_path=str(git_index_lock) if git_index_lock else None,
        git_index_lock_exists=bool(git_index_lock and git_index_lock.exists()),
        staged_files=current_check.staged_files,
        unstaged_files=current_check.unstaged_files,
        untracked_files=current_check.untracked_files,
        report_final_status=report.final_status,
        report_commit_ready=report.commit_ready,
        plan_approval_status=plan.approval_status,
        approval_status=approval.approval_status if approval else "missing",
        last_commit_failure_category=report.last_commit_failure_category,
        last_commit_failure_message=report.last_commit_failure_message,
        last_commit_failure_retryable=report.last_commit_failure_retryable,
        failure_looks_retryable=report.last_commit_failure_retryable,
        possible_causes=possible_causes,
        next_actions=next_actions,
        warnings=_dedupe(warnings),
        probe_requested=index_lock_probe,
        probe_ran=probe_ran,
        can_create_index_lock=can_create_index_lock,
        probe_error=probe_error,
    )


def propose_delivery_commit_message(plan: DeliveryPlan) -> str:
    return plan.intended_commit_message.strip()


def write_delivery_report(report: DeliveryReport, workspace_root: Path | None = None) -> tuple[DeliveryReport, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(report.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_report_artifact_paths(report.project, report.delivery_id, workspace_root=root)
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_report_markdown(report), encoding="utf-8")
    _write_delivery_index(report.project, workspace_root=root)
    return report, json_path, markdown_path


def load_delivery_report(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryReport | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_report_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryReport.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_reports(project_name: str, workspace_root: Path | None = None) -> list[DeliveryReport]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    reports: list[DeliveryReport] = []
    for path in sorted(directory.glob("delivery-report-*.json")):
        try:
            reports.append(DeliveryReport.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(reports, key=lambda item: item.updated_at, reverse=True)


def preview_delivery_commit(
    project_name: str,
    delivery_id: str,
    *,
    message_override: str | None = None,
    workspace_root: Path | None = None,
) -> DeliveryCommitPreview:
    root = workspace_root or get_workspace_root()
    report = _require_delivery_report(project_name, delivery_id, root)
    plan = _require_delivery_plan(project_name, report.source_delivery_plan_id, root)
    approval = load_delivery_approval(project_name, report.source_delivery_plan_id, workspace_root=root)
    current_check, _json_path, _markdown_path = run_delivery_readiness_check(
        project_name,
        queue_id=report.source_queue_id,
        item_id=report.source_queue_item_id,
        write=False,
        workspace_root=root,
    )
    proposed_message = report.proposed_commit_message.strip()
    effective_message = (message_override.strip() if message_override else proposed_message).strip()
    blocked_files = _dedupe(
        [
            *current_check.forbidden_changed_files,
            *current_check.forbidden_staged_files,
            *current_check.workspace_artifacts_staged,
            *current_check.secrets_risk_files,
        ]
    )
    eligible_files = [
        path
        for path in current_check.changed_files
        if path not in blocked_files
        and not _is_forbidden_path(path)
        and not _is_workspace_artifact_path(path)
        and not _is_secret_risk_path(path)
    ]
    blockers = list(current_check.blockers)
    if plan.approval_status != "approved":
        blockers.append(f"Delivery plan {plan.delivery_id} is not approved.")
    if not approval or approval.approval_status != "approved":
        blockers.append(f"Delivery approval for {plan.delivery_id} is not approved.")
    if report.final_status != "ready":
        blockers.append(f"Delivery report {delivery_id} is {report.final_status}, not ready.")
        if report.last_commit_failure_retryable:
            blockers.append(
                f"Delivery report {delivery_id} has retryable guarded commit failure "
                f"{report.last_commit_failure_category}. Last failure: "
                f"{report.last_commit_failure_message or 'not recorded'}"
            )
            blockers.append(
                f"Run diagnostics: devo delivery commit-diagnostics --project {project_name} --report {delivery_id}"
            )
            blockers.append(
                f"After fixing the issue, run recovery: devo delivery report-refresh --project {project_name} "
                f"--report {delivery_id} --reopen --note \"<reason>\""
            )
    if not report.commit_ready:
        blockers.append(f"Delivery report {delivery_id} is not commit-ready.")
    if current_check.readiness_status == BLOCKED:
        blockers.append("Current delivery readiness is blocked.")
    if blocked_files:
        blockers.append("Blocked files are present: " + ", ".join(blocked_files))
    if not eligible_files:
        blockers.append("No commit-eligible changed files were found.")
    if not effective_message:
        blockers.append("Commit message is required.")
    blockers = _dedupe(blockers)
    commit_ready = not blockers
    return DeliveryCommitPreview(
        project=project_name,
        delivery_id=report.delivery_id,
        target_repo_path=current_check.target_repo_path,
        branch=current_check.branch,
        remote=current_check.remote,
        proposed_commit_message=proposed_message,
        effective_commit_message=effective_message,
        eligible_files=eligible_files,
        blocked_files=blocked_files,
        blockers=blockers,
        warnings=_dedupe(current_check.warnings),
        delivery_readiness_status=current_check.readiness_status,
        commit_ready=commit_ready,
        next_action=_commit_preview_next_action(commit_ready, blockers),
    )


def commit_delivery_report(
    project_name: str,
    delivery_id: str,
    *,
    confirm_commit: bool = False,
    message_override: str | None = None,
    author_note: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[DeliveryCommitResult, Path, Path]:
    root = workspace_root or get_workspace_root()
    if not confirm_commit:
        msg = "--confirm-commit is required."
        raise ValueError(msg)
    preview = preview_delivery_commit(project_name, delivery_id, message_override=message_override, workspace_root=root)
    if not preview.commit_ready:
        failure_category = "no_eligible_files" if any("No commit-eligible changed files" in blocker for blocker in preview.blockers) else "unknown"
        result = DeliveryCommitResult(
            project=project_name,
            delivery_id=delivery_id,
            status="blocked",
            commit_message=preview.effective_commit_message,
            eligible_files=preview.eligible_files,
            stderr=_summary_text(preview.blockers),
            failure_category=failure_category,
            failure_retryable=False,
            next_action="Resolve commit blockers before retrying delivery commit.",
        )
        write_delivery_commit_result(result, workspace_root=root)
        _mark_delivery_report_blocked(
            project_name,
            delivery_id,
            result.stderr,
            workspace_root=root,
            failure_category=failure_category,
            failure_message=result.stderr,
            failure_retryable=False,
        )
        raise ValueError("Delivery commit blocked: " + result.stderr)
    repo_path = Path(preview.target_repo_path)
    try:
        index_lock_preflight = _probe_git_index_lock(repo_path)
        if not index_lock_preflight.ok:
            return _write_index_lock_preflight_failure(project_name, delivery_id, preview, index_lock_preflight, root)
        add_result = _run_git(repo_path, ["add", "--", *preview.eligible_files])
        if add_result.returncode != 0:
            return _write_failed_commit_result(project_name, delivery_id, preview, "git add failed", add_result, root)
        commit_result = _run_git(repo_path, ["commit", "-m", preview.effective_commit_message])
        if commit_result.returncode != 0:
            return _write_failed_commit_result(project_name, delivery_id, preview, "git commit failed", commit_result, root)
        hash_result = _run_git(repo_path, ["rev-parse", "HEAD"])
        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else None
        result = DeliveryCommitResult(
            project=project_name,
            delivery_id=delivery_id,
            status="committed",
            commit_hash=commit_hash,
            commit_message=preview.effective_commit_message,
            eligible_files=preview.eligible_files,
            stdout=commit_result.stdout.strip(),
            stderr=commit_result.stderr.strip(),
            returncode=commit_result.returncode,
            next_action=(
                f"Commit created. Preview guarded push with "
                f"devo delivery push-preview --project {project_name} --report {delivery_id}; then run "
                f"devo delivery push --project {project_name} --report {delivery_id} --confirm-push if the preview is safe."
            ),
        )
        _mark_delivery_report_committed(project_name, delivery_id, commit_hash, author_note, workspace_root=root)
        return write_delivery_commit_result(result, workspace_root=root)
    except OSError as exc:
        category, retryable, next_action = _classify_commit_failure("git execution failed", "", str(exc))
        if retryable and category.startswith("index_lock"):
            next_action = _index_lock_retry_next_action(project_name, delivery_id)
        result = DeliveryCommitResult(
            project=project_name,
            delivery_id=delivery_id,
            status="failed",
            commit_message=preview.effective_commit_message,
            eligible_files=preview.eligible_files,
            stderr=str(exc),
            failure_category=category,
            failure_retryable=retryable,
            next_action=next_action,
        )
        _mark_delivery_report_blocked(
            project_name,
            delivery_id,
            str(exc),
            workspace_root=root,
            failure_category=category,
            failure_message=str(exc),
            failure_retryable=retryable,
        )
        return write_delivery_commit_result(result, workspace_root=root)


def write_delivery_commit_result(result: DeliveryCommitResult, workspace_root: Path | None = None) -> tuple[DeliveryCommitResult, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(result.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_commit_artifact_paths(result.project, result.delivery_id, workspace_root=root)
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_commit_markdown(result), encoding="utf-8")
    return result, json_path, markdown_path


def load_delivery_commit_result(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryCommitResult | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_commit_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryCommitResult.model_validate_json(json_path.read_text(encoding="utf-8"))


def preview_delivery_push(
    project_name: str,
    delivery_id: str,
    *,
    remote_override: str | None = None,
    branch_override: str | None = None,
    workspace_root: Path | None = None,
) -> DeliveryPushPreview:
    root = workspace_root or get_workspace_root()
    report = _require_delivery_report(project_name, delivery_id, root)
    repo_path = Path(report.target_repo_path)
    branch = (branch_override.strip() if branch_override else report.branch) or None
    push_remote = (remote_override.strip() if remote_override else _default_push_remote(report.remote)) or None
    blockers: list[str] = []
    warnings: list[str] = []
    current_check, _json_path, _markdown_path = run_delivery_readiness_check(
        project_name,
        queue_id=report.source_queue_id,
        item_id=report.source_queue_item_id,
        write=False,
        workspace_root=root,
    )
    if current_check.readiness_status == BLOCKED:
        blockers.extend(current_check.blockers)
    else:
        warnings.extend(current_check.warnings)
    if not report.commit_hash:
        blockers.append(f"Delivery report {delivery_id} has no commit hash.")
    if report.pushed:
        blockers.append(f"Delivery report {delivery_id} is already pushed.")
    if report.final_status not in {"committed", "pushed"}:
        blockers.append(f"Delivery report {delivery_id} is {report.final_status}, not committed.")
    if not repo_path.exists():
        blockers.append(f"Target repository path does not exist: {repo_path}")
    if not branch:
        blockers.append("Push branch could not be determined.")
    if not push_remote:
        blockers.append("Push remote could not be determined.")
    if push_remote and repo_path.exists():
        remote_check = _run_git(repo_path, ["remote", "get-url", push_remote])
        if remote_check.returncode != 0:
            blockers.append(f"Git remote was not found: {push_remote}")
    if branch and repo_path.exists():
        branch_check = _run_git(repo_path, ["rev-parse", "--verify", branch])
        if branch_check.returncode != 0:
            blockers.append(f"Git branch was not found: {branch}")
    if report.commit_hash and repo_path.exists():
        contains_check = _run_git(repo_path, ["merge-base", "--is-ancestor", report.commit_hash, "HEAD"])
        if contains_check.returncode != 0:
            blockers.append(f"Commit hash is not contained in the current branch: {report.commit_hash}")
    blockers = _dedupe(blockers)
    return DeliveryPushPreview(
        project=project_name,
        delivery_id=delivery_id,
        source_commit_hash=report.commit_hash,
        target_repo_path=report.target_repo_path,
        branch=report.branch,
        remote=report.remote,
        push_remote=push_remote,
        push_branch=branch,
        push_allowed=not blockers,
        blockers=blockers,
        warnings=_dedupe(warnings),
        next_action=_push_preview_next_action(not blockers, blockers),
    )


def push_delivery_report(
    project_name: str,
    delivery_id: str,
    *,
    confirm_push: bool = False,
    remote_override: str | None = None,
    branch_override: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[DeliveryPush, Path, Path]:
    root = workspace_root or get_workspace_root()
    if not confirm_push:
        msg = "--confirm-push is required."
        raise ValueError(msg)
    preview = preview_delivery_push(
        project_name,
        delivery_id,
        remote_override=remote_override,
        branch_override=branch_override,
        workspace_root=root,
    )
    if not preview.push_allowed:
        result = DeliveryPush(
            project=project_name,
            delivery_id=delivery_id,
            source_delivery_report_id=delivery_id,
            source_commit_hash=preview.source_commit_hash,
            target_repo_path=preview.target_repo_path,
            branch=preview.branch,
            remote=preview.remote,
            push_remote=preview.push_remote,
            push_branch=preview.push_branch,
            push_status="blocked",
            blockers=preview.blockers,
            warnings=preview.warnings,
            next_action="Resolve push blockers before retrying delivery push.",
        )
        write_delivery_push_result(result, workspace_root=root)
        _mark_delivery_report_push_blocked(project_name, delivery_id, _summary_text(preview.blockers), workspace_root=root)
        raise ValueError("Delivery push blocked: " + _summary_text(preview.blockers))
    repo_path = Path(preview.target_repo_path)
    try:
        completed = _run_git(repo_path, ["push", preview.push_remote or "", preview.push_branch or ""])
        if completed.returncode != 0:
            result = DeliveryPush(
                project=project_name,
                delivery_id=delivery_id,
                source_delivery_report_id=delivery_id,
                source_commit_hash=preview.source_commit_hash,
                target_repo_path=preview.target_repo_path,
                branch=preview.branch,
                remote=preview.remote,
                push_remote=preview.push_remote,
                push_branch=preview.push_branch,
                push_status="failed",
                pushed=False,
                push_exit_code=completed.returncode,
                push_stdout=completed.stdout.strip(),
                push_stderr=completed.stderr.strip(),
                warnings=preview.warnings,
                next_action="Review the git push failure before retrying delivery push.",
            )
            _mark_delivery_report_push_failed(project_name, delivery_id, _single_line("git push failed", completed.stdout, completed.stderr), workspace_root=root)
            return write_delivery_push_result(result, workspace_root=root)
        now = datetime.now(UTC)
        result = DeliveryPush(
            project=project_name,
            delivery_id=delivery_id,
            source_delivery_report_id=delivery_id,
            source_commit_hash=preview.source_commit_hash,
            target_repo_path=preview.target_repo_path,
            branch=preview.branch,
            remote=preview.remote,
            push_remote=preview.push_remote,
            push_branch=preview.push_branch,
            push_status="pushed",
            pushed=True,
            pushed_at=now,
            push_exit_code=completed.returncode,
            push_stdout=completed.stdout.strip(),
            push_stderr=completed.stderr.strip(),
            warnings=preview.warnings,
            next_action="Delivery pushed. Review remote state and close any external delivery checklist manually.",
        )
        _mark_delivery_report_pushed(project_name, delivery_id, result, workspace_root=root)
        return write_delivery_push_result(result, workspace_root=root)
    except OSError as exc:
        result = DeliveryPush(
            project=project_name,
            delivery_id=delivery_id,
            source_delivery_report_id=delivery_id,
            source_commit_hash=preview.source_commit_hash,
            target_repo_path=preview.target_repo_path,
            branch=preview.branch,
            remote=preview.remote,
            push_remote=preview.push_remote,
            push_branch=preview.push_branch,
            push_status="failed",
            pushed=False,
            push_stderr=str(exc),
            warnings=preview.warnings,
            next_action="Review the git execution failure before retrying delivery push.",
        )
        _mark_delivery_report_push_failed(project_name, delivery_id, str(exc), workspace_root=root)
        return write_delivery_push_result(result, workspace_root=root)


def write_delivery_push_result(result: DeliveryPush, workspace_root: Path | None = None) -> tuple[DeliveryPush, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(result.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_push_artifact_paths(result.project, result.delivery_id, workspace_root=root)
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_push_markdown(result), encoding="utf-8")
    return result, json_path, markdown_path


def load_delivery_push_result(project_name: str, delivery_id: str, workspace_root: Path | None = None) -> DeliveryPush | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_push_artifact_paths(project_name, delivery_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryPush.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_commit_results(project_name: str, workspace_root: Path | None = None) -> list[DeliveryCommitResult]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    results: list[DeliveryCommitResult] = []
    for path in sorted(directory.glob("delivery-commit-*.json")):
        try:
            results.append(DeliveryCommitResult.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(results, key=lambda item: item.updated_at, reverse=True)


def list_delivery_push_results(project_name: str, workspace_root: Path | None = None) -> list[DeliveryPush]:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    results: list[DeliveryPush] = []
    for path in sorted(directory.glob("delivery-push-*.json")):
        try:
            results.append(DeliveryPush.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(results, key=lambda item: item.updated_at, reverse=True)


def create_delivery_runner_request(
    project_name: str,
    intended_commit_message: str,
    note: str,
    *,
    allow_empty_request: bool = False,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerRequest, Path, Path]:
    root = workspace_root or get_workspace_root()
    message = intended_commit_message.strip()
    if not message:
        msg = "Intended commit message is required."
        raise ValueError(msg)
    check, _json_path, _markdown_path = run_delivery_readiness_check(project_name, write=False, workspace_root=root)
    blockers = list(check.blockers)
    if not check.changed_files and not allow_empty_request:
        blockers.append("Target repository is clean; use --allow-empty-request only for explicit no-change runner requests.")
    if blockers:
        msg = "Delivery runner request blocked: " + _summary_text(_dedupe(blockers))
        raise ValueError(msg)
    request_id = _next_runner_request_id(project_name, workspace_root=root)
    now = datetime.now(UTC)
    request = DeliveryRunnerRequest(
        project=project_name,
        request_id=request_id,
        requested_by=_current_operator_name(),
        requested_from_context="devo delivery runner-request",
        target_repo_path=check.target_repo_path,
        intended_commit_message=message,
        note=note.strip(),
        expected_changed_files=check.changed_files,
        forbidden_changed_files=_dedupe(
            [
                *check.forbidden_changed_files,
                *check.forbidden_staged_files,
                *check.workspace_artifacts_staged,
                *check.secrets_risk_files,
            ]
        ),
        warnings=check.warnings,
        created_at=now,
        updated_at=now,
        status="requested",
        next_action=_runner_run_command(project_name, request_id),
    )
    return write_delivery_runner_request(request, workspace_root=root)


def write_delivery_runner_request(
    request: DeliveryRunnerRequest,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerRequest, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(request.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_runner_request_artifact_paths(request.project, request.request_id, workspace_root=root)
    json_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_runner_request_markdown(request), encoding="utf-8")
    _write_delivery_runner_request_index(request.project, workspace_root=root)
    return request, json_path, markdown_path


def load_delivery_runner_request(
    project_name: str,
    request_id: str,
    workspace_root: Path | None = None,
) -> DeliveryRunnerRequest | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_runner_request_artifact_paths(project_name, request_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryRunnerRequest.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_delivery_runner_requests(project_name: str, workspace_root: Path | None = None) -> list[DeliveryRunnerRequest]:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    requests: list[DeliveryRunnerRequest] = []
    for path in sorted(directory.glob("runner-request-*.json")):
        try:
            requests.append(DeliveryRunnerRequest.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(requests, key=lambda item: item.updated_at, reverse=True)


def write_delivery_runner_run(
    run: DeliveryRunnerRun,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(run.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_runner_run_artifact_paths(run.project, run.request_id, workspace_root=root)
    json_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_runner_run_markdown(run), encoding="utf-8")
    _write_delivery_runner_request_index(run.project, workspace_root=root)
    return run, json_path, markdown_path


def load_delivery_runner_run(
    project_name: str,
    request_id: str,
    workspace_root: Path | None = None,
) -> DeliveryRunnerRun | None:
    root = workspace_root or get_workspace_root()
    json_path, _markdown_path = delivery_runner_run_artifact_paths(project_name, request_id, workspace_root=root)
    if not json_path.exists():
        return None
    return DeliveryRunnerRun.model_validate_json(json_path.read_text(encoding="utf-8"))


def write_delivery_runner_watch(
    watch: DeliveryRunnerWatch,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerWatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(watch.project, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = delivery_runner_watch_artifact_paths(watch.project, watch.watch_id, workspace_root=root)
    json_path.write_text(watch.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_delivery_runner_watch_markdown(watch), encoding="utf-8")
    return watch, json_path, markdown_path


def list_delivery_runner_watches(project_name: str, workspace_root: Path | None = None) -> list[DeliveryRunnerWatch]:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(project_name, workspace_root=root)
    if not directory.exists():
        return []
    watches: list[DeliveryRunnerWatch] = []
    for path in sorted(directory.glob("runner-watch-*.json")):
        try:
            watches.append(DeliveryRunnerWatch.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(watches, key=lambda item: item.started_at, reverse=True)


def run_delivery_runner_watch(
    project_name: str,
    *,
    approver: str,
    once: bool = False,
    confirm_runner_watch: bool = False,
    request_id: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerWatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    approver_name = approver.strip()
    if not confirm_runner_watch:
        msg = "Refusing to run trusted runner watch without --confirm-runner-watch."
        raise ValueError(msg)
    if not approver_name:
        msg = "--approver is required."
        raise ValueError(msg)
    if not once:
        msg = "--once is required. Continuous runner watch is deferred to TASK-DEVO-127."
        raise ValueError(msg)

    watch = _new_runner_watch(project_name, approver_name, mode="once")
    steps = list(watch.steps_run)
    blockers: list[str] = []
    warnings: list[str] = []
    pending_requests = _pending_runner_requests(project_name, workspace_root=root)
    watch.pending_request_count = len(pending_requests)
    steps.append(f"found pending runner requests: {len(pending_requests)}")

    selected_request: DeliveryRunnerRequest | None = None
    if request_id:
        requested = load_delivery_runner_request(project_name, request_id, workspace_root=root)
        if not requested:
            blockers.append(f"Delivery runner request not found: {request_id}")
        elif requested.status != "requested":
            blockers.append(f"Delivery runner request {request_id} is {requested.status}, not requested.")
        else:
            selected_request = requested
    elif pending_requests:
        selected_request = pending_requests[0]

    if blockers:
        return _finish_runner_watch(watch, "blocked", blockers, warnings, steps, root)
    if not selected_request:
        return _finish_runner_watch(
            watch,
            "no_pending",
            blockers,
            warnings,
            steps,
            root,
            next_action="No pending runner requests.",
        )

    watch.selected_request_id = selected_request.request_id
    steps.append(f"selected runner request {selected_request.request_id}")
    run, _run_json, _run_md = run_delivery_runner_request(
        project_name,
        selected_request.request_id,
        approver=approver_name,
        confirm_runner_delivery=True,
        workspace_root=root,
    )
    watch.selected_run_id = run.run_id
    watch.delivery_id = run.delivery_report_id or run.delivery_plan_id or run.delivery_check_id
    watch.commit_hash = run.commit_hash
    watch.pushed = run.pushed
    warnings.extend(run.warnings)
    blockers.extend(run.blockers)
    steps.extend(run.steps_run)
    status = "completed" if run.status == "completed" else "blocked" if run.status == "blocked" else "failed"
    next_action = (
        "Trusted runner watch completed one request."
        if status == "completed"
        else run.next_action
    )
    return _finish_runner_watch(watch, status, blockers, warnings, steps, root, next_action=next_action)


def run_delivery_runner_request(
    project_name: str,
    request_id: str,
    *,
    approver: str,
    confirm_runner_delivery: bool = False,
    workspace_root: Path | None = None,
) -> tuple[DeliveryRunnerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    if not confirm_runner_delivery:
        msg = "--confirm-runner-delivery is required."
        raise ValueError(msg)
    request = load_delivery_runner_request(project_name, request_id, workspace_root=root)
    if not request:
        msg = f"Delivery runner request not found: {request_id}"
        raise ValueError(msg)
    if request.status in {"cancelled", "completed", "consumed"}:
        msg = f"Delivery runner request {request_id} is {request.status}; create a new request for another delivery."
        raise ValueError(msg)

    run = _new_runner_run(project_name, request)
    steps = list(run.steps_run)
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        registration = load_registered_project(project_name, workspace_root=root)
        repo_path = Path(request.target_repo_path)
        if repo_path.resolve() != registration.path.resolve():
            blockers.append(f"Request target repo path no longer matches project registration: {repo_path} != {registration.path}")
        if not repo_path.exists():
            blockers.append(f"Target repository path does not exist: {repo_path}")
        if blockers:
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)

        status = get_git_repository_status(project_name, workspace_root=root)
        steps.append("verified target repo path, branch, and upstream")
        if not status.current_branch:
            blockers.append("Current Git branch could not be determined.")
        if not status.upstream_branch:
            warnings.append("No upstream branch was detected; push preview may block.")

        probe = _probe_git_index_lock(repo_path)
        run.index_lock_probe_result = _probe_result_payload(probe)
        steps.append("index-lock preflight")
        if not probe.ok:
            blockers.append(probe.message)
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)

        check, _check_json, _check_md = run_delivery_readiness_check(project_name, write=True, workspace_root=root)
        steps.append(f"delivery check {check.delivery_id}")
        run.delivery_check_id = check.delivery_id
        warnings.extend(check.warnings)
        if check.blockers:
            blockers.extend(check.blockers)
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)
        mismatch = _changed_file_mismatch(request.expected_changed_files, check.changed_files)
        if mismatch:
            blockers.append(mismatch)
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)

        plan, _plan_json, _plan_md = create_delivery_plan(project_name, check.delivery_id, request.intended_commit_message, workspace_root=root)
        run.delivery_plan_id = plan.delivery_id
        steps.append(f"delivery plan {plan.delivery_id}")
        request_delivery_approval(
            project_name,
            plan.delivery_id,
            request.note or "Trusted local delivery runner approval requested.",
            workspace_root=root,
        )
        steps.append(f"approval requested {plan.delivery_id}")
        approve_delivery_plan(
            project_name,
            plan.delivery_id,
            approver,
            f"Approved trusted local delivery runner request {request.request_id}.",
            workspace_root=root,
        )
        steps.append(f"approval approved {plan.delivery_id}")
        report, _report_json, _report_md = prepare_delivery_report(project_name, plan.delivery_id, workspace_root=root)
        run.delivery_report_id = report.delivery_id
        steps.append(f"delivery report {report.delivery_id}")
        preview = preview_delivery_commit(project_name, report.delivery_id, workspace_root=root)
        steps.append("commit preview")
        if not preview.commit_ready:
            blockers.extend(preview.blockers)
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)
        commit, _commit_json, _commit_md = commit_delivery_report(
            project_name,
            report.delivery_id,
            confirm_commit=True,
            author_note=f"Trusted local delivery runner request {request.request_id}.",
            workspace_root=root,
        )
        steps.append("guarded commit")
        run.commit_hash = commit.commit_hash
        if commit.status != "committed":
            detail = commit.stderr or commit.stdout or commit.failure_category or "Guarded commit did not complete."
            blockers.append(detail)
            status_name = "blocked" if commit.status == "blocked" else "failed"
            return _finish_runner_run(project_name, request, run, status_name, blockers, warnings, steps, root)
        push_preview = preview_delivery_push(project_name, report.delivery_id, workspace_root=root)
        steps.append("push preview")
        if not push_preview.push_allowed:
            blockers.extend(push_preview.blockers)
            return _finish_runner_run(project_name, request, run, "blocked", blockers, warnings, steps, root)
        push, _push_json, _push_md = push_delivery_report(project_name, report.delivery_id, confirm_push=True, workspace_root=root)
        steps.append("guarded push")
        run.pushed = push.pushed
        run.push_remote = push.push_remote
        run.push_branch = push.push_branch
        if not push.pushed:
            blockers.extend(push.blockers)
            if push.push_stderr:
                blockers.append(push.push_stderr)
            return _finish_runner_run(project_name, request, run, "failed", blockers, warnings, steps, root)
        return _finish_runner_run(project_name, request, run, "completed", blockers, warnings, steps, root)
    except ValueError as exc:
        blockers.append(str(exc))
        return _finish_runner_run(project_name, request, run, "failed", blockers, warnings, steps, root)


def build_delivery_latest_summary(project_name: str, workspace_root: Path | None = None) -> DeliveryLatestSummary:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    target_repo_path = str(Path(registration.path).expanduser())
    warnings: list[str] = []
    current_git_status_summary = "unknown"
    current_repo_is_clean = False
    try:
        status = get_git_repository_status(project_name, workspace_root=root)
        target_repo_path = str(status.repo_path)
        staged_files = [item.path for item in status.staged_files]
        unstaged_files = [item.path for item in status.unstaged_files]
        untracked_files = [item.path for item in status.untracked_files]
        current_git_status_summary = _git_status_summary(staged_files, unstaged_files, untracked_files)
        current_repo_is_clean = status.working_tree_clean
        warnings.extend(status.warnings)
    except ValueError as exc:
        warnings.append(f"Current Git status unavailable: {exc}")

    checks = list_delivery_checks(project_name, workspace_root=root)
    plans = list_delivery_plans(project_name, workspace_root=root)
    approvals = list_delivery_approvals(project_name, workspace_root=root)
    reports = list_delivery_reports(project_name, workspace_root=root)
    commit_results = list_delivery_commit_results(project_name, workspace_root=root)
    push_results = list_delivery_push_results(project_name, workspace_root=root)
    runner_requests = list_delivery_runner_requests(project_name, workspace_root=root)

    latest_check = checks[0] if checks else None
    latest_meaningful_check = next((check for check in checks if not _is_empty_delivery_check(check)), None)
    latest_plan = plans[0] if plans else None
    latest_approval = approvals[0] if approvals else None
    latest_report = reports[0] if reports else None
    latest_commit = commit_results[0] if commit_results else None
    latest_push = push_results[0] if push_results else None
    latest_runner_request = runner_requests[0] if runner_requests else None
    latest_runner_run = (
        load_delivery_runner_run(project_name, latest_runner_request.request_id, workspace_root=root)
        if latest_runner_request
        else None
    )
    latest_pushed_report = next((report for report in reports if report.pushed), None)
    latest_pushed_push = next((push for push in push_results if push.pushed), None)
    latest_pushed_delivery_id = latest_pushed_push.delivery_id if latest_pushed_push else latest_pushed_report.delivery_id if latest_pushed_report else None
    latest_pushed_at = (
        latest_pushed_push.pushed_at.isoformat()
        if latest_pushed_push and latest_pushed_push.pushed_at
        else latest_pushed_report.pushed_at.isoformat()
        if latest_pushed_report and latest_pushed_report.pushed_at
        else None
    )
    next_action = _delivery_latest_next_action(
        project_name,
        latest_check,
        latest_plan,
        latest_report,
        latest_commit,
        latest_push,
        current_repo_is_clean,
    )
    return DeliveryLatestSummary(
        project=project_name,
        target_repo_path=target_repo_path,
        current_git_status_summary=current_git_status_summary,
        current_repo_is_clean=current_repo_is_clean,
        current_repo_has_pending_changes=not current_repo_is_clean,
        latest_delivery_check_id=latest_check.delivery_id if latest_check else None,
        latest_delivery_check_status=latest_check.readiness_status if latest_check else None,
        latest_delivery_check_is_empty=_is_empty_delivery_check(latest_check) if latest_check else False,
        latest_meaningful_delivery_check_id=latest_meaningful_check.delivery_id if latest_meaningful_check else None,
        latest_meaningful_delivery_check_status=latest_meaningful_check.readiness_status if latest_meaningful_check else None,
        latest_plan_id=latest_plan.delivery_id if latest_plan else None,
        latest_plan_status=latest_plan.delivery_status if latest_plan else None,
        latest_approval_id=latest_approval.delivery_id if latest_approval else None,
        latest_approval_status=latest_approval.approval_status if latest_approval else None,
        latest_report_id=latest_report.delivery_id if latest_report else None,
        latest_report_status=latest_report.final_status if latest_report else None,
        latest_commit_result_id=latest_commit.delivery_id if latest_commit else None,
        latest_commit_result_status=latest_commit.status if latest_commit else None,
        latest_commit_hash=latest_commit.commit_hash if latest_commit else latest_report.commit_hash if latest_report else None,
        latest_push_result_id=latest_push.delivery_id if latest_push else None,
        latest_push_result_status=latest_push.push_status if latest_push else None,
        latest_pushed_delivery_id=latest_pushed_delivery_id,
        latest_pushed_at=latest_pushed_at,
        latest_runner_request_id=latest_runner_request.request_id if latest_runner_request else None,
        latest_runner_request_status=latest_runner_request.status if latest_runner_request else None,
        latest_runner_run_id=latest_runner_run.run_id if latest_runner_run else None,
        latest_runner_run_status=latest_runner_run.status if latest_runner_run else None,
        latest_runner_commit_hash=latest_runner_run.commit_hash if latest_runner_run else None,
        latest_runner_pushed=latest_runner_run.pushed if latest_runner_run else None,
        latest_runner_changed_file_count=len(latest_runner_request.expected_changed_files) if latest_runner_request else None,
        latest_runner_next_action=_runner_latest_next_action(
            project_name,
            latest_runner_request,
            latest_runner_run,
            current_repo_is_clean,
        ),
        next_action=next_action,
        warnings=_dedupe(warnings),
    )


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
            f"- Secret documentation warnings: {len(check.secret_warning_files)}",
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


def render_delivery_plan_markdown(plan: DeliveryPlan) -> str:
    return "\n".join(
        [
            f"# Delivery Plan: {plan.delivery_id}",
            "",
            f"- Project: `{plan.project}`",
            f"- Delivery status: `{plan.delivery_status}`",
            f"- Approval status: `{plan.approval_status}`",
            f"- Readiness: `{plan.readiness_status}`",
            f"- Source check: `{plan.source_delivery_check_id}`",
            f"- Intended commit message: `{plan.intended_commit_message}`",
            f"- Target repo: `{plan.target_repo_path}`",
            f"- Branch: `{plan.branch or 'unknown'}`",
            f"- Remote/upstream: `{plan.remote or 'unknown'}`",
            f"- Queue item: `{plan.source_queue_id or 'not linked'} / {plan.source_queue_item_id or 'not linked'}`",
            f"- Worker run: `{plan.source_worker_run_id or 'not linked'}`",
            f"- Review status: `{plan.review_status}`",
            f"- Validation evidence status: `{plan.validation_evidence_status}`",
            "",
            "## Files",
            "",
            f"- Changed: {len(plan.changed_files)}",
            f"- Staged: {len(plan.staged_files)}",
            f"- Unstaged: {len(plan.unstaged_files)}",
            f"- Untracked: {len(plan.untracked_files)}",
            "",
            "## Forbidden Scope",
            "",
            *_markdown_list(plan.forbidden_scope),
            "",
            "## Blockers",
            "",
            *_markdown_list(plan.blockers),
            "",
            "## Warnings",
            "",
            *_markdown_list(plan.warnings),
            "",
            "## Next Action",
            "",
            plan.next_action,
            "",
        ]
    )


def render_delivery_approval_markdown(approval: DeliveryApproval) -> str:
    return "\n".join(
        [
            f"# Delivery Approval: {approval.delivery_id}",
            "",
            f"- Project: `{approval.project}`",
            f"- Approval status: `{approval.approval_status}`",
            f"- Readiness: `{approval.readiness_status}`",
            f"- Blockers: {approval.blocker_count}",
            f"- Warnings: {approval.warning_count}",
            f"- Changed files: {approval.changed_file_count}",
            f"- Staged files: {approval.staged_file_count}",
            f"- Review status: `{approval.review_status}`",
            f"- Validation evidence status: `{approval.validation_evidence_status}`",
            f"- Reviewer: `{approval.reviewer or 'not set'}`",
            f"- Approver: `{approval.approver or 'not set'}`",
            f"- Decision note: {approval.decision_note or 'none'}",
            "",
            "## Notes",
            "",
            *_markdown_list(approval.approval_notes),
            "",
            "## Next Action",
            "",
            approval.next_action,
            "",
        ]
    )


def render_delivery_report_markdown(report: DeliveryReport) -> str:
    return "\n".join(
        [
            f"# Delivery Report Draft: {report.delivery_id}",
            "",
            f"- Project: `{report.project}`",
            f"- Final status: `{report.final_status}`",
            f"- Commit ready: `{report.commit_ready}`",
            f"- Push ready: `{report.push_ready}`",
            f"- Push status: `{report.push_status or 'none'}`",
            f"- Pushed: `{report.pushed}`",
            f"- Approval status: `{report.approval_status}`",
            f"- Readiness snapshot status: `{report.readiness_snapshot_status or report.delivery_readiness_status}`",
            f"- Readiness snapshot at: `{report.readiness_snapshot_at.isoformat() if report.readiness_snapshot_at else 'unknown'}`",
            f"- Readiness currentness: `{report.readiness_currentness}`",
            f"- Readiness note: {report.readiness_snapshot_note}",
            f"- Recovery status: `{report.recovery_status}`",
            f"- Last commit failure category: `{report.last_commit_failure_category or 'none'}`",
            f"- Last commit failure retryable: `{report.last_commit_failure_retryable}`",
            f"- Source plan: `{report.source_delivery_plan_id}`",
            f"- Source check: `{report.source_delivery_check_id or 'unknown'}`",
            f"- Proposed commit message: `{report.proposed_commit_message}`",
            f"- Target repo: `{report.target_repo_path}`",
            f"- Branch: `{report.branch or 'unknown'}`",
            f"- Remote/upstream: `{report.remote or 'unknown'}`",
            f"- Push target: `{report.push_remote or 'unknown'} {report.push_branch or 'unknown'}`",
            "",
            "## Files",
            "",
            f"- Changed: {len(report.changed_files)}",
            f"- Staged: {len(report.staged_files)}",
            f"- Unstaged: {len(report.unstaged_files)}",
            f"- Untracked: {len(report.untracked_files)}",
            "",
            "## Evidence Summary",
            "",
            f"- Validation: {report.validation_summary}",
            f"- Review: {report.review_summary}",
            f"- Safety scan: {report.safety_scan_summary}",
            f"- Blockers: {report.blocker_summary}",
            f"- Warnings: {report.warning_summary}",
            "",
            "## Recovery History",
            "",
            *_markdown_list(report.recovery_history),
            "",
            "## Next Action",
            "",
            report.next_action,
            "",
        ]
    )


def render_delivery_commit_markdown(result: DeliveryCommitResult) -> str:
    return "\n".join(
        [
            f"# Delivery Commit Result: {result.delivery_id}",
            "",
            f"- Project: `{result.project}`",
            f"- Status: `{result.status}`",
            f"- Commit hash: `{result.commit_hash or 'none'}`",
            f"- Commit message: `{result.commit_message}`",
            f"- Files: {len(result.eligible_files)}",
            f"- Return code: `{result.returncode if result.returncode is not None else 'not available'}`",
            f"- Failure category: `{result.failure_category or 'none'}`",
            f"- Failure retryable: `{result.failure_retryable}`",
            "",
            "## Eligible Files",
            "",
            *_markdown_list(result.eligible_files),
            "",
            "## Git Output",
            "",
            f"- stdout: {result.stdout or 'none'}",
            f"- stderr: {result.stderr or 'none'}",
            "",
            "## Next Action",
            "",
            result.next_action,
            "",
        ]
    )


def render_delivery_push_markdown(result: DeliveryPush) -> str:
    return "\n".join(
        [
            f"# Delivery Push Result: {result.delivery_id}",
            "",
            f"- Project: `{result.project}`",
            f"- Status: `{result.push_status}`",
            f"- Pushed: `{result.pushed}`",
            f"- Commit hash: `{result.source_commit_hash or 'none'}`",
            f"- Remote: `{result.push_remote or 'unknown'}`",
            f"- Branch: `{result.push_branch or 'unknown'}`",
            f"- Return code: `{result.push_exit_code if result.push_exit_code is not None else 'not available'}`",
            f"- Pushed at: `{result.pushed_at.isoformat() if result.pushed_at else 'not pushed'}`",
            "",
            "## Blockers",
            "",
            *_markdown_list(result.blockers),
            "",
            "## Warnings",
            "",
            *_markdown_list(result.warnings),
            "",
            "## Git Output",
            "",
            f"- stdout: {result.push_stdout or 'none'}",
            f"- stderr: {result.push_stderr or 'none'}",
            "",
            "## Next Action",
            "",
            result.next_action,
            "",
        ]
    )


def render_delivery_runner_request_markdown(request: DeliveryRunnerRequest) -> str:
    return "\n".join(
        [
            f"# Delivery Runner Request: {request.request_id}",
            "",
            f"- Project: `{request.project}`",
            f"- Status: `{request.status}`",
            f"- Requested by: `{request.requested_by}`",
            f"- Requested from: `{request.requested_from_context}`",
            f"- Target repo: `{request.target_repo_path}`",
            f"- Commit message: `{request.intended_commit_message}`",
            f"- Note: {request.note or 'none'}",
            f"- Expected changed files: {len(request.expected_changed_files)}",
            "",
            "## Expected Changed Files",
            "",
            *_markdown_list(request.expected_changed_files),
            "",
            "## Warnings",
            "",
            *_markdown_list(request.warnings),
            "",
            "## Blockers",
            "",
            *_markdown_list(request.blockers),
            "",
            "## Next Action",
            "",
            request.next_action,
            "",
        ]
    )


def render_delivery_runner_run_markdown(run: DeliveryRunnerRun) -> str:
    return "\n".join(
        [
            f"# Delivery Runner Run: {run.request_id}",
            "",
            f"- Project: `{run.project}`",
            f"- Request: `{run.request_id}`",
            f"- Run id: `{run.run_id}`",
            f"- Status: `{run.status}`",
            f"- Commit hash: `{run.commit_hash or 'none'}`",
            f"- Pushed: `{run.pushed}`",
            f"- Remote: `{run.push_remote or 'unknown'}`",
            f"- Branch: `{run.push_branch or 'unknown'}`",
            f"- Started at: `{run.started_at.isoformat()}`",
            f"- Completed at: `{run.completed_at.isoformat() if run.completed_at else 'not completed'}`",
            "",
            "## Steps Run",
            "",
            *_markdown_list(run.steps_run),
            "",
            "## Index Lock Probe",
            "",
            f"- Can create index.lock: `{run.index_lock_probe_result.get('ok', 'unknown')}`",
            f"- Message: {run.index_lock_probe_result.get('message', 'none')}",
            "",
            "## Blockers",
            "",
            *_markdown_list(run.blockers),
            "",
            "## Warnings",
            "",
            *_markdown_list(run.warnings),
            "",
            "## Next Action",
            "",
            run.next_action,
            "",
        ]
    )


def render_delivery_runner_watch_markdown(watch: DeliveryRunnerWatch) -> str:
    return "\n".join(
        [
            f"# Delivery Runner Watch: {watch.watch_id}",
            "",
            f"- Project: `{watch.project}`",
            f"- Watch id: `{watch.watch_id}`",
            f"- Mode: `{watch.mode}`",
            f"- Status: `{watch.status}`",
            f"- Approver: `{watch.approver}`",
            f"- Pending requests: `{watch.pending_request_count}`",
            f"- Selected request: `{watch.selected_request_id or 'none'}`",
            f"- Selected run: `{watch.selected_run_id or 'none'}`",
            f"- Delivery id: `{watch.delivery_id or 'none'}`",
            f"- Commit hash: `{watch.commit_hash or 'none'}`",
            f"- Pushed: `{watch.pushed}`",
            f"- Started at: `{watch.started_at.isoformat()}`",
            f"- Completed at: `{watch.completed_at.isoformat() if watch.completed_at else 'not completed'}`",
            "",
            "## Steps Run",
            "",
            *_markdown_list(watch.steps_run),
            "",
            "## Blockers",
            "",
            *_markdown_list(watch.blockers),
            "",
            "## Warnings",
            "",
            *_markdown_list(watch.warnings),
            "",
            "## Next Action",
            "",
            watch.next_action,
            "",
        ]
    )


def _write_delivery_index(project_name: str, workspace_root: Path | None = None) -> DeliveryIndex:
    root = workspace_root or get_workspace_root()
    directory = delivery_directory(project_name, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    checks = list_delivery_checks(project_name, workspace_root=root)
    plans = list_delivery_plans(project_name, workspace_root=root)
    approvals = list_delivery_approvals(project_name, workspace_root=root)
    reports = list_delivery_reports(project_name, workspace_root=root)
    check_entries = [
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
    plan_entries = [
        DeliveryPlanIndexEntry(
            delivery_id=plan.delivery_id,
            delivery_status=plan.delivery_status,
            approval_status=plan.approval_status,
            readiness_status=plan.readiness_status,
            blocker_count=len(plan.blockers),
            warning_count=len(plan.warnings),
            intended_commit_message=plan.intended_commit_message,
            path=str(delivery_plan_artifact_paths(project_name, plan.delivery_id, workspace_root=root)[0]),
            updated_at=plan.updated_at,
        )
        for plan in plans
    ]
    approval_entries = [
        DeliveryApprovalIndexEntry(
            delivery_id=approval.delivery_id,
            approval_status=approval.approval_status,
            readiness_status=approval.readiness_status,
            blocker_count=approval.blocker_count,
            warning_count=approval.warning_count,
            path=str(delivery_approval_artifact_paths(project_name, approval.delivery_id, workspace_root=root)[0]),
            updated_at=approval.updated_at,
        )
        for approval in approvals
    ]
    report_entries = [
        DeliveryReportIndexEntry(
            delivery_id=report.delivery_id,
            final_status=report.final_status,
            commit_ready=report.commit_ready,
            push_ready=report.push_ready,
            proposed_commit_message=report.proposed_commit_message,
            path=str(delivery_report_artifact_paths(project_name, report.delivery_id, workspace_root=root)[0]),
            updated_at=report.updated_at,
        )
        for report in reports
    ]
    index = DeliveryIndex(
        project=project_name,
        checks=check_entries,
        plans=plan_entries,
        approvals=approval_entries,
        reports=report_entries,
        updated_at=datetime.now(UTC),
    )
    (directory / DELIVERY_INDEX_JSON).write_text(index.model_dump_json(indent=2), encoding="utf-8")
    return index


def _write_delivery_runner_request_index(project_name: str, workspace_root: Path | None = None) -> DeliveryRunnerRequestIndex:
    root = workspace_root or get_workspace_root()
    directory = delivery_runner_request_directory(project_name, workspace_root=root)
    directory.mkdir(parents=True, exist_ok=True)
    requests = list_delivery_runner_requests(project_name, workspace_root=root)
    entries = []
    for request in requests:
        latest_run = load_delivery_runner_run(project_name, request.request_id, workspace_root=root)
        entries.append(
            DeliveryRunnerRequestIndexEntry(
                request_id=request.request_id,
                status=request.status,
                intended_commit_message=request.intended_commit_message,
                changed_file_count=len(request.expected_changed_files),
                latest_run_status=latest_run.status if latest_run else None,
                path=str(delivery_runner_request_artifact_paths(project_name, request.request_id, workspace_root=root)[0]),
                updated_at=request.updated_at,
            )
        )
    index = DeliveryRunnerRequestIndex(project=project_name, requests=entries, updated_at=datetime.now(UTC))
    delivery_runner_request_index_path(project_name, workspace_root=root).write_text(index.model_dump_json(indent=2), encoding="utf-8")
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


def _next_runner_request_id(project_name: str, workspace_root: Path | None = None) -> str:
    requests = list_delivery_runner_requests(project_name, workspace_root=workspace_root)
    highest = 0
    for request in requests:
        try:
            highest = max(highest, int(request.request_id.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"REQ-{highest + 1:04d}"


def _new_runner_run(project_name: str, request: DeliveryRunnerRequest) -> DeliveryRunnerRun:
    now = datetime.now(UTC)
    return DeliveryRunnerRun(
        project=project_name,
        request_id=request.request_id,
        run_id=f"RUN-{now.strftime('%Y%m%d%H%M%S')}-{request.request_id.lower()}",
        started_at=now,
        runner_context="devo delivery runner-run",
        status="failed",
        steps_run=["loaded runner request"],
        next_action="Runner has not completed.",
    )


def _new_runner_watch(project_name: str, approver: str, *, mode: str) -> DeliveryRunnerWatch:
    now = datetime.now(UTC)
    return DeliveryRunnerWatch(
        project=project_name,
        watch_id=f"WATCH-{now.strftime('%Y%m%d%H%M%S%f')}",
        started_at=now,
        mode=mode,
        approver=approver,
        status="failed",
        steps_run=["started trusted runner watch"],
        next_action="Runner watch has not completed.",
    )


def _finish_runner_watch(
    watch: DeliveryRunnerWatch,
    status: str,
    blockers: list[str],
    warnings: list[str],
    steps: list[str],
    workspace_root: Path,
    *,
    next_action: str | None = None,
) -> tuple[DeliveryRunnerWatch, Path, Path]:
    watch.status = status
    watch.completed_at = datetime.now(UTC)
    watch.blockers = _dedupe(blockers)
    watch.warnings = _dedupe(warnings)
    watch.steps_run = _dedupe(steps)
    watch.next_action = next_action or _runner_watch_next_action(watch.status, watch.blockers)
    return write_delivery_runner_watch(watch, workspace_root=workspace_root)


def _pending_runner_requests(project_name: str, workspace_root: Path) -> list[DeliveryRunnerRequest]:
    requests = list_delivery_runner_requests(project_name, workspace_root=workspace_root)
    pending = [request for request in requests if request.status == "requested"]
    return sorted(pending, key=lambda item: item.created_at)


def _runner_watch_next_action(status: str, blockers: list[str]) -> str:
    if status == "no_pending":
        return "No pending runner requests."
    if status == "completed":
        return "Trusted runner watch completed one request."
    if blockers:
        return "Resolve runner watch blockers before retrying: " + _summary_text(blockers)
    return "Review runner watch artifact."


def _finish_runner_run(
    project_name: str,
    request: DeliveryRunnerRequest,
    run: DeliveryRunnerRun,
    status: str,
    blockers: list[str],
    warnings: list[str],
    steps: list[str],
    workspace_root: Path,
) -> tuple[DeliveryRunnerRun, Path, Path]:
    now = datetime.now(UTC)
    run.status = status
    run.completed_at = now
    run.blockers = _dedupe(blockers)
    run.warnings = _dedupe(warnings)
    run.steps_run = _dedupe(steps)
    run.next_action = _runner_next_action(project_name, request.request_id, status, run.blockers, run.commit_hash, run.pushed)
    request_status = "completed" if status == "completed" else "failed" if status == "failed" else "requested"
    updated_request = request.model_copy(
        update={
            "status": request_status,
            "updated_at": now,
            "blockers": run.blockers,
            "warnings": _dedupe([*request.warnings, *run.warnings]),
            "next_action": run.next_action,
        }
    )
    write_delivery_runner_request(updated_request, workspace_root=workspace_root)
    return write_delivery_runner_run(run, workspace_root=workspace_root)


def _runner_next_action(
    project_name: str,
    request_id: str,
    status: str,
    blockers: list[str],
    commit_hash: str | None,
    pushed: bool,
) -> str:
    if status == "completed" and pushed:
        return f"Trusted delivery runner completed and pushed commit {commit_hash or 'unknown'}."
    if blockers:
        return "Resolve runner blockers before creating a new runner request: " + _summary_text(blockers)
    return _runner_run_command(project_name, request_id)


def _runner_latest_next_action(
    project_name: str,
    request: DeliveryRunnerRequest | None,
    latest_run: DeliveryRunnerRun | None,
    current_repo_is_clean: bool,
) -> str:
    if not request:
        if current_repo_is_clean:
            return "No runner action needed; repository is clean and no runner request exists."
        return (
            "Create a runner request after validating the current changes: "
            f'.\\.venv\\Scripts\\devo.exe delivery runner-request --project {project_name} '
            '--message "<commit message>" --note "<task note>"'
        )
    if latest_run and latest_run.status == "completed" and latest_run.pushed:
        return f"Runner delivery completed; no runner action needed for {request.request_id}."
    if request.status == "completed":
        return f"Runner request {request.request_id} is completed; no runner action needed."
    if latest_run and latest_run.status in {"blocked", "failed"}:
        return (
            f"Review {request.request_id} with devo delivery runner-show --project {project_name} "
            f"--request {request.request_id}, then create a fresh request after fixing blockers."
        )
    if request.status == "requested":
        return _runner_run_command(project_name, request.request_id)
    return f"Review runner request {request.request_id}: devo delivery runner-show --project {project_name} --request {request.request_id}"


def _runner_run_command(project_name: str, request_id: str) -> str:
    return (
        f'.\\.venv\\Scripts\\devo.exe delivery runner-run --project {project_name} --request {request_id} '
        '--approver "Manas" --confirm-runner-delivery'
    )


def _current_operator_name() -> str:
    return os.environ.get("USERNAME") or os.environ.get("USER") or getpass.getuser() or "unknown"


def _probe_result_payload(probe: IndexLockProbeResult) -> dict[str, object]:
    return {
        "ok": probe.ok,
        "category": probe.category,
        "message": probe.message,
        "lock_path": probe.lock_path,
        "created": probe.created,
        "removed": probe.removed,
    }


def _changed_file_mismatch(expected: list[str], current: list[str]) -> str | None:
    expected_set = set(expected)
    current_set = set(current)
    if expected_set == current_set:
        return None
    added = sorted(current_set - expected_set)
    removed = sorted(expected_set - current_set)
    parts = []
    if added:
        parts.append("unexpected files: " + ", ".join(added))
    if removed:
        parts.append("missing expected files: " + ", ".join(removed))
    return "Current changed files differ from runner request snapshot; " + "; ".join(parts)


def _require_delivery_plan(project_name: str, delivery_id: str, workspace_root: Path) -> DeliveryPlan:
    plan = load_delivery_plan(project_name, delivery_id, workspace_root=workspace_root)
    if not plan:
        msg = f"Delivery plan not found: {delivery_id}"
        raise ValueError(msg)
    return plan


def _require_delivery_report(project_name: str, delivery_id: str, workspace_root: Path) -> DeliveryReport:
    report = load_delivery_report(project_name, delivery_id, workspace_root=workspace_root)
    if not report:
        msg = f"Delivery report not found: {delivery_id}"
        raise ValueError(msg)
    return report


def _approval_from_plan(plan: DeliveryPlan, existing: DeliveryApproval | None = None) -> DeliveryApproval:
    now = datetime.now(UTC)
    return DeliveryApproval(
        project=plan.project,
        delivery_id=plan.delivery_id,
        approval_status=existing.approval_status if existing else "not_requested",
        requested_at=existing.requested_at if existing else None,
        reviewed_at=existing.reviewed_at if existing else None,
        approved_at=existing.approved_at if existing else None,
        rejected_at=existing.rejected_at if existing else None,
        reviewer=existing.reviewer if existing else None,
        approver=existing.approver if existing else None,
        decision_note=existing.decision_note if existing else "",
        approval_notes=existing.approval_notes if existing else [],
        readiness_status=plan.readiness_status,
        blocker_count=len(plan.blockers),
        warning_count=len(plan.warnings),
        changed_file_count=len(plan.changed_files),
        staged_file_count=len(plan.staged_files),
        validation_evidence_status=plan.validation_evidence_status,
        review_status=plan.review_status,
        next_action=existing.next_action if existing else _approval_next_action("not_requested", plan),
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )


def _existing_notes(existing: DeliveryApproval | None) -> list[str]:
    return list(existing.approval_notes) if existing else []


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


def _is_empty_delivery_check(check: DeliveryCheck) -> bool:
    return (
        len(check.changed_files) == 0
        and len(check.staged_files) == 0
        and len(check.unstaged_files) == 0
        and len(check.untracked_files) == 0
        and len(check.blockers) == 0
        and len(check.warnings) == 0
        and check.readiness_status == READY
    )


def _check_has_no_file_changes(check: DeliveryCheck | None) -> bool:
    return bool(check) and not check.changed_files and not check.staged_files and not check.unstaged_files and not check.untracked_files


def _delivery_latest_next_action(
    project_name: str,
    latest_check: DeliveryCheck | None,
    latest_plan: DeliveryPlan | None,
    latest_report: DeliveryReport | None,
    latest_commit: DeliveryCommitResult | None,
    latest_push: DeliveryPush | None,
    current_repo_is_clean: bool,
) -> str:
    if latest_check and current_repo_is_clean and _check_has_no_file_changes(latest_check) and not latest_check.blockers:
        return "No delivery needed; repository is clean."
    if latest_check and latest_check.blockers:
        return f"Fix blockers from {latest_check.delivery_id}, then rerun devo delivery check --project {project_name} --write."
    if current_repo_is_clean and latest_push and latest_push.pushed:
        return "Delivery completed and pushed. Run delivery check again if current repository state matters."
    if current_repo_is_clean and latest_report and latest_report.pushed:
        return "Delivery completed and pushed. Run delivery check again if current repository state matters."
    if not current_repo_is_clean and (not latest_check or _check_has_no_file_changes(latest_check)):
        return f"Run devo delivery check --project {project_name} --write to capture current delivery readiness."
    if latest_plan and latest_plan.approval_status == "approved":
        if not latest_report or latest_report.source_delivery_plan_id != latest_plan.delivery_id:
            return f"Approved plan exists; run devo delivery report-prepare --project {project_name} --plan {latest_plan.delivery_id}."
    if latest_report and latest_report.final_status == "ready" and not latest_report.commit_hash:
        return f"Report is ready; run devo delivery commit-preview --project {project_name} --report {latest_report.delivery_id}."
    if latest_report and latest_report.commit_hash and not latest_report.pushed:
        return f"Commit exists; run devo delivery push-preview --project {project_name} --report {latest_report.delivery_id}."
    if latest_commit and latest_commit.status == "committed" and not (
        (latest_push and latest_push.delivery_id == latest_commit.delivery_id and latest_push.pushed)
        or (latest_report and latest_report.delivery_id == latest_commit.delivery_id and latest_report.pushed)
    ):
        return f"Commit exists; run devo delivery push-preview --project {project_name} --report {latest_commit.delivery_id}."
    if latest_check and latest_check.changed_files and not latest_check.blockers:
        return f"Create a delivery plan: devo delivery plan --project {project_name} --delivery {latest_check.delivery_id} --message \"<message>\"."
    if latest_push and latest_push.pushed:
        return "Delivery completed and pushed. Run delivery check again if current repository state matters."
    if latest_report and latest_report.pushed:
        return "Delivery completed and pushed. Run delivery check again if current repository state matters."
    if current_repo_is_clean:
        return "No delivery needed; repository is clean."
    return f"Run devo delivery check --project {project_name} --write to capture current delivery readiness."


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


DOC_SECRET_TERMS_RE = re.compile(
    r"(\.env\b|\bapi[ _-]?keys?\b|\btokens?\b|\bsecrets?\b|\bcredentials?\b|\bpasswords?\b)",
    re.IGNORECASE,
)


def _documentation_secret_mention_paths(repo_path: Path, paths: list[str], secret_signal_paths: list[str]) -> list[str]:
    signal_paths = set(secret_signal_paths)
    warning_paths: list[str] = []
    for path in paths:
        if path in signal_paths or not _is_documentation_path(path):
            continue
        full_path = repo_path / path
        if not full_path.exists() or not full_path.is_file():
            continue
        try:
            if full_path.stat().st_size > 512_000:
                continue
            text = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if DOC_SECRET_TERMS_RE.search(text):
            warning_paths.append(path)
    return _dedupe(warning_paths)


def _is_documentation_path(path: str) -> bool:
    normalized = _normalize_git_path(path).lower()
    return normalized == "readme.md" or (normalized.startswith("docs/") and normalized.endswith(".md"))


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


def _warning_affects_readiness(warning: str) -> bool:
    return warning != GLOBAL_IGNORE_WARNING_DETAIL


def _next_action(readiness_status: str) -> str:
    if readiness_status == BLOCKED:
        return "Resolve delivery blockers before requesting delivery approval."
    if readiness_status == WARNINGS:
        return "Review warnings, then rerun delivery check before delivery approval."
    return "Ready for a future delivery approval plan; commit/push remain manual and deferred."


def _plan_next_action(delivery_status: str, approval_status: str) -> str:
    if delivery_status == "blocked":
        return "Resolve delivery blockers and create a new delivery readiness check before approval."
    if approval_status == "not_requested":
        return "Request delivery approval with devo delivery approval-request."
    if approval_status == "requested":
        return "Review the delivery approval request; approve or reject the plan."
    if approval_status == "approved":
        return "Prepare a delivery report with devo delivery report-prepare before guarded commit."
    if approval_status == "rejected":
        return "Delivery rejected; revise the plan before any future delivery step."
    return "Review delivery plan state."


def _approval_next_action(approval_status: str, plan: DeliveryPlan) -> str:
    if plan.delivery_status == "blocked" or plan.readiness_status == BLOCKED:
        return "Resolve delivery blockers before requesting or approving delivery."
    if approval_status == "not_requested":
        return "Request delivery approval with devo delivery approval-request."
    if approval_status == "requested":
        return "Approve or reject the delivery plan after review."
    if approval_status == "approved":
        return "Prepare a delivery report, then preview any guarded CLI commit before committing."
    if approval_status == "rejected":
        return "Revise the delivery plan or resolve blockers before requesting approval again."
    return "Review delivery approval state."


def _commit_preview_next_action(commit_ready: bool, blockers: list[str]) -> str:
    if commit_ready:
        return "Ready for guarded CLI commit with --confirm-commit. After commit, run delivery push-preview before --confirm-push."
    if any(_is_retryable_report_blocker(blocker) for blocker in blockers):
        return (
            "Delivery report is blocked by a retryable guarded commit failure. Run delivery commit-diagnostics first; "
            'after fixing the OS/Git issue, run delivery report-refresh --reopen --note "<reason>" and commit-preview again.'
        )
    if blockers:
        return "Resolve commit blockers before running guarded delivery commit."
    return "Review delivery commit preview."


def _run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=False,
        capture_output=True,
        text=True,
    )


def _probe_git_index_lock(repo_path: Path) -> IndexLockProbeResult:
    git_dir = _resolve_git_dir(repo_path)
    if not git_dir:
        return IndexLockProbeResult(
            ok=False,
            category="index_lock_probe_failed",
            message="Unable to resolve .git directory for index-lock preflight.",
        )
    git_index_lock = git_dir / "index.lock"
    if git_index_lock.exists():
        return IndexLockProbeResult(
            ok=False,
            category="index_lock_exists",
            message=f".git/index.lock already exists; refusing guarded commit preflight: {git_index_lock}",
            lock_path=str(git_index_lock),
        )
    created = False
    try:
        with git_index_lock.open("x", encoding="utf-8") as handle:
            handle.write("devo guarded commit index-lock preflight\n")
        created = True
    except FileExistsError as exc:
        return IndexLockProbeResult(
            ok=False,
            category="index_lock_exists",
            message=f".git/index.lock appeared during guarded commit preflight: {exc}",
            lock_path=str(git_index_lock),
        )
    except PermissionError as exc:
        return IndexLockProbeResult(
            ok=False,
            category="index_lock_permission_denied",
            message=f"Permission denied creating .git/index.lock during guarded commit preflight: {exc}",
            lock_path=str(git_index_lock),
        )
    except OSError as exc:
        return IndexLockProbeResult(
            ok=False,
            category="index_lock_probe_failed",
            message=f"Could not create .git/index.lock during guarded commit preflight: {exc}",
            lock_path=str(git_index_lock),
        )
    if created and git_index_lock.exists():
        try:
            git_index_lock.unlink()
        except OSError as exc:
            return IndexLockProbeResult(
                ok=False,
                category="index_lock_probe_failed",
                message=f"Created .git/index.lock during guarded commit preflight but could not remove it: {exc}",
                lock_path=str(git_index_lock),
                created=True,
                cleanup_error=str(exc),
            )
    return IndexLockProbeResult(ok=True, message="Index-lock preflight passed.", lock_path=str(git_index_lock), created=True, removed=True)


def _index_lock_retry_next_action(project_name: str, delivery_id: str) -> str:
    return (
        f"Run devo delivery commit-diagnostics --project {project_name} --report {delivery_id} "
        "--index-lock-probe --confirm-probe. If this context cannot create .git/index.lock, run live delivery from "
        "normal PowerShell with .\\.venv\\Scripts\\devo.exe. After fixing the context, run "
        f"devo delivery report-refresh --project {project_name} --report {delivery_id} --reopen --note \"<reason>\", "
        f"then devo delivery commit-preview --project {project_name} --report {delivery_id}, then guarded commit."
    )


def _write_index_lock_preflight_failure(
    project_name: str,
    delivery_id: str,
    preview: DeliveryCommitPreview,
    probe: IndexLockProbeResult,
    workspace_root: Path,
) -> tuple[DeliveryCommitResult, Path, Path]:
    category = probe.category or "index_lock_probe_failed"
    detail = f"index-lock preflight failed before staging: {probe.message}"
    result = DeliveryCommitResult(
        project=project_name,
        delivery_id=delivery_id,
        status="blocked",
        commit_message=preview.effective_commit_message,
        eligible_files=preview.eligible_files,
        stderr=detail,
        failure_category=category,
        failure_retryable=True,
        next_action=_index_lock_retry_next_action(project_name, delivery_id),
    )
    _mark_delivery_report_blocked(
        project_name,
        delivery_id,
        detail,
        workspace_root=workspace_root,
        failure_category=category,
        failure_message=detail,
        failure_retryable=True,
    )
    return write_delivery_commit_result(result, workspace_root=workspace_root)


def _write_failed_commit_result(
    project_name: str,
    delivery_id: str,
    preview: DeliveryCommitPreview,
    label: str,
    completed: subprocess.CompletedProcess[str],
    workspace_root: Path,
) -> tuple[DeliveryCommitResult, Path, Path]:
    detail = _single_line(label, completed.stdout, completed.stderr)
    category, retryable, next_action = _classify_commit_failure(label, completed.stdout, completed.stderr)
    if retryable and category.startswith("index_lock"):
        next_action = _index_lock_retry_next_action(project_name, delivery_id)
    result = DeliveryCommitResult(
        project=project_name,
        delivery_id=delivery_id,
        status="failed",
        commit_message=preview.effective_commit_message,
        eligible_files=preview.eligible_files,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        returncode=completed.returncode,
        failure_category=category,
        failure_retryable=retryable,
        next_action=next_action,
    )
    _mark_delivery_report_blocked(
        project_name,
        delivery_id,
        detail,
        workspace_root=workspace_root,
        failure_category=category,
        failure_message=detail,
        failure_retryable=retryable,
    )
    return write_delivery_commit_result(result, workspace_root=workspace_root)


def _mark_delivery_report_committed(
    project_name: str,
    delivery_id: str,
    commit_hash: str | None,
    author_note: str | None,
    workspace_root: Path,
) -> None:
    report = _require_delivery_report(project_name, delivery_id, workspace_root)
    note = f" Author note: {author_note.strip()}" if author_note and author_note.strip() else ""
    report.commit_hash = commit_hash
    report.final_status = "committed"
    report.commit_ready = False
    report.push_ready = bool(commit_hash)
    report.pushed = False
    report.push_status = "not_pushed"
    _mark_readiness_snapshot_historical(report)
    report.updated_at = datetime.now(UTC)
    report.next_action = (
        f"Commit created. Preview guarded push with devo delivery push-preview --project {project_name} "
        f"--report {delivery_id}; if safe, run devo delivery push --project {project_name} --report {delivery_id} --confirm-push.{note}"
    )
    write_delivery_report(report, workspace_root=workspace_root)


def _mark_delivery_report_blocked(
    project_name: str,
    delivery_id: str,
    detail: str,
    workspace_root: Path,
    *,
    failure_category: str | None = None,
    failure_message: str | None = None,
    failure_retryable: bool = False,
) -> None:
    report = load_delivery_report(project_name, delivery_id, workspace_root=workspace_root)
    if not report:
        return
    report.final_status = "blocked"
    report.commit_ready = False
    report.push_ready = False
    report.updated_at = datetime.now(UTC)
    report.blocker_summary = detail or report.blocker_summary
    if failure_category:
        report.last_commit_failure_category = failure_category
        report.last_commit_failure_message = failure_message or detail
        report.last_commit_failure_retryable = failure_retryable
        report.recovery_status = "none"
        report.recovery_reason = "Guarded delivery commit failed."
        report.recovery_history = [
            *report.recovery_history,
            _recovery_history_note(report.updated_at, "commit_failed", report.last_commit_failure_message or detail, ""),
        ]
    if failure_retryable:
        report.next_action = _index_lock_retry_next_action(project_name, delivery_id)
    else:
        report.next_action = "Resolve delivery commit blockers before retrying."
    write_delivery_report(report, workspace_root=workspace_root)


def _mark_delivery_report_push_blocked(project_name: str, delivery_id: str, detail: str, workspace_root: Path) -> None:
    report = load_delivery_report(project_name, delivery_id, workspace_root=workspace_root)
    if not report:
        return
    report.push_status = "blocked"
    report.push_ready = False
    _mark_readiness_snapshot_historical(report)
    report.updated_at = datetime.now(UTC)
    report.blocker_summary = detail or report.blocker_summary
    report.next_action = "Resolve delivery push blockers before retrying."
    write_delivery_report(report, workspace_root=workspace_root)


def _mark_delivery_report_push_failed(project_name: str, delivery_id: str, detail: str, workspace_root: Path) -> None:
    report = load_delivery_report(project_name, delivery_id, workspace_root=workspace_root)
    if not report:
        return
    report.push_status = "failed"
    report.push_ready = True
    report.final_status = "failed"
    _mark_readiness_snapshot_historical(report)
    report.updated_at = datetime.now(UTC)
    report.warning_summary = detail or report.warning_summary
    report.next_action = "Review delivery push failure before retrying."
    write_delivery_report(report, workspace_root=workspace_root)


def _mark_delivery_report_pushed(project_name: str, delivery_id: str, result: DeliveryPush, workspace_root: Path) -> None:
    report = _require_delivery_report(project_name, delivery_id, workspace_root)
    report.pushed = True
    report.push_ready = False
    report.push_remote = result.push_remote
    report.push_branch = result.push_branch
    report.push_status = result.push_status
    report.pushed_at = result.pushed_at
    report.final_status = "pushed"
    _mark_readiness_snapshot_historical(report)
    report.updated_at = datetime.now(UTC)
    report.next_action = (
        f"Delivery pushed. Review push result with devo delivery push-show --project {project_name} --delivery {delivery_id}; "
        "run delivery check again if current repository state matters."
    )
    write_delivery_report(report, workspace_root=workspace_root)


def _mark_readiness_snapshot_historical(report: DeliveryReport) -> None:
    report.readiness_currentness = "historical_snapshot"
    if not report.readiness_snapshot_status:
        report.readiness_snapshot_status = report.delivery_readiness_status
    if not report.readiness_snapshot_at:
        report.readiness_snapshot_at = report.created_at
    report.readiness_snapshot_note = "Historical readiness snapshot; run delivery check for current repo state."


def _refresh_report_snapshot(report: DeliveryReport, current_check: DeliveryCheck, plan: DeliveryPlan) -> None:
    report.target_repo_path = current_check.target_repo_path
    report.branch = current_check.branch
    report.remote = current_check.remote
    report.changed_files = current_check.changed_files
    report.staged_files = current_check.staged_files
    report.unstaged_files = current_check.unstaged_files
    report.untracked_files = current_check.untracked_files
    report.validation_summary = f"Validation evidence status: {current_check.validation_evidence_status}"
    report.review_summary = f"Worker review status: {current_check.review_status}"
    report.safety_scan_summary = _safety_scan_summary(current_check)
    report.delivery_readiness_status = current_check.readiness_status
    report.readiness_snapshot_status = current_check.readiness_status
    report.readiness_snapshot_at = current_check.updated_at
    report.readiness_currentness = "current"
    report.readiness_snapshot_note = "Readiness snapshot refreshed by delivery report-refresh."
    report.source_delivery_check_id = plan.source_delivery_check_id


def _hydrate_commit_failure_metadata(report: DeliveryReport, *, workspace_root: Path) -> None:
    if report.last_commit_failure_category:
        return
    commit_result = load_delivery_commit_result(report.project, report.delivery_id, workspace_root=workspace_root)
    if not commit_result or commit_result.status not in {"blocked", "failed"}:
        return
    label = "git commit failed" if commit_result.status == "failed" else "delivery commit blocked"
    category = commit_result.failure_category
    retryable = commit_result.failure_retryable
    if not category:
        category, retryable, _next_action = _classify_commit_failure(label, commit_result.stdout, commit_result.stderr)
    report.last_commit_failure_category = category
    report.last_commit_failure_message = _single_line(label, commit_result.stdout, commit_result.stderr)
    report.last_commit_failure_retryable = retryable


def _classify_commit_failure(label: str, stdout: str, stderr: str) -> tuple[str, bool, str]:
    text = " ".join(part.strip() for part in (label, stdout, stderr) if part and part.strip()).lower()
    if "index.lock" in text and "permission denied" in text:
        return (
            "index_lock_permission_denied",
            True,
            "Run delivery commit-diagnostics, fix the .git/index.lock permission issue, then run delivery report-refresh --reopen before retrying commit.",
        )
    if "index.lock" in text and ("file exists" in text or "exists" in text or "another git process" in text):
        return (
            "index_lock_exists",
            True,
            "Run delivery commit-diagnostics, ensure no Git process is running, remove a stale lock only after manual verification, then run delivery report-refresh --reopen.",
        )
    if "index-lock preflight" in text or "guarded commit preflight" in text:
        return (
            "index_lock_probe_failed",
            True,
            "Run delivery commit-diagnostics with --index-lock-probe --confirm-probe, fix the execution context, then run delivery report-refresh --reopen before retrying commit.",
        )
    if "no commit-eligible changed files" in text:
        return ("no_eligible_files", False, "Create or select commit-eligible changes before retrying delivery commit.")
    if "git commit failed" in text:
        return ("git_commit_failed", False, "Review the git commit failure before retrying delivery commit.")
    return ("unknown", False, "Review the git failure before retrying delivery commit.")


def _commit_failure_possible_causes(category: str | None) -> list[str]:
    if category == "index_lock_permission_denied":
        return [
            "existing Git/index operation conflict",
            "OS or ACL permission issue on .git or .git/index",
            "antivirus or Controlled Folder Access blocking lock creation",
            "terminal/user permission mismatch",
            "read-only or protected .git directory",
        ]
    if category == "index_lock_exists":
        return [
            "another Git process is currently running",
            "stale .git/index.lock left by an interrupted Git process",
        ]
    if category == "index_lock_probe_failed":
        return [
            "current process cannot safely create and remove .git/index.lock",
            "unexpected .git directory or index-lock path state",
            "OS, ACL, antivirus, or terminal sandbox restriction",
        ]
    if category == "git_commit_failed":
        return ["Git commit returned a non-zero exit code; inspect raw stderr before retrying."]
    if category == "no_eligible_files":
        return ["No commit-eligible files were present when guarded commit ran."]
    return ["Commit failure cause is unknown; inspect raw stderr and current Git state."]


def _commit_diagnostics_next_actions(project_name: str, delivery_id: str, report: DeliveryReport) -> list[str]:
    if report.last_commit_failure_retryable and report.last_commit_failure_category in {
        "index_lock_permission_denied",
        "index_lock_exists",
        "index_lock_probe_failed",
    }:
        return [
            "Check that .git/index.lock is absent and no Git process is active.",
            "Review .git and .git/index permissions, antivirus, Controlled Folder Access, and terminal/user permissions.",
            (
                f"If this context cannot create .git/index.lock, run live delivery from normal PowerShell with "
                f".\\.venv\\Scripts\\devo.exe."
            ),
            (
                f"After fixing the OS/Git issue, run devo delivery report-refresh --project {project_name} "
                f"--report {delivery_id} --reopen --note \"<reason>\"."
            ),
            f"Then run devo delivery commit-preview --project {project_name} --report {delivery_id}.",
            "Do not bypass Devo with a manual commit unless explicitly approved.",
        ]
    if report.commit_hash and not report.pushed:
        return [f"Commit exists; run devo delivery push-preview --project {project_name} --report {delivery_id} before guarded push."]
    if report.pushed:
        return ["Delivery is already pushed; no commit retry is needed."]
    return ["Resolve the reported blockers, refresh the delivery report, and preview guarded commit before retrying."]


def _resolve_git_dir(repo_path: Path) -> Path | None:
    result = _run_git(repo_path, ["rev-parse", "--git-dir"])
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = repo_path / path
    return path


def _git_version() -> str | None:
    try:
        result = subprocess.run(["git", "--version"], check=False, capture_output=True, text=True, timeout=5)
    except OSError:
        return None
    except subprocess.TimeoutExpired:
        return "timeout"
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _path_attribute_summary(path: Path) -> list[str]:
    if not path.exists():
        return ["missing"]
    try:
        stat_result = path.stat()
    except OSError as exc:
        return [f"stat unavailable: {exc}"]
    attrs = ["directory" if path.is_dir() else "file", f"mode={oct(stat_result.st_mode & 0o777)}"]
    if not os.access(path, os.R_OK):
        attrs.append("not_readable")
    if not os.access(path, os.W_OK):
        attrs.append("not_writable")
    if path.name.startswith("."):
        attrs.append("dotfile")
    file_attributes = getattr(stat_result, "st_file_attributes", None)
    if file_attributes is not None:
        attrs.append(f"windows_attributes={file_attributes}")
    return attrs


def _windows_acl_summary(path: Path) -> list[str]:
    if os.name != "nt" or not path.exists():
        return []
    try:
        result = subprocess.run(["icacls", str(path)], check=False, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 and result.stderr.strip():
        lines.append(f"icacls stderr: {' '.join(result.stderr.split())}")
    return lines[:8]


def _is_retryable_report_blocker(blocker: str) -> bool:
    text = blocker.lower()
    return "retryable guarded commit failure" in text or "index_lock_" in text or "index.lock" in text


def _recovery_history_note(when: datetime | None, status: str, reason: str, note: str) -> str:
    timestamp = (when or datetime.now(UTC)).isoformat()
    clean_note = note.strip()
    suffix = f" Note: {clean_note}" if clean_note else ""
    return f"{timestamp} | {status}: {reason}{suffix}"


def _default_push_remote(remote: str | None) -> str | None:
    if not remote:
        return None
    if "/" in remote:
        return remote.split("/", 1)[0]
    if remote == "configured":
        return "origin"
    return remote


def _push_preview_next_action(push_allowed: bool, blockers: list[str]) -> str:
    if push_allowed:
        return "Ready for guarded CLI push with --confirm-push."
    if blockers:
        return "Resolve push blockers before running guarded delivery push."
    return "Review delivery push preview."


def _safety_scan_summary(check: DeliveryCheck) -> str:
    return (
        f"forbidden changed {len(check.forbidden_changed_files)}, "
        f"forbidden staged {len(check.forbidden_staged_files)}, "
        f"workspace staged {len(check.workspace_artifacts_staged)}, "
        f"secret-risk {len(check.secrets_risk_files)}"
    )


def _summary_text(items: list[str]) -> str:
    if not items:
        return "none"
    return "; ".join(items)


def _single_line(label: str, stdout: str, stderr: str) -> str:
    details = " ".join(part.strip() for part in (stdout, stderr) if part and part.strip())
    details = " ".join(details.split())
    return f"{label}: {details}" if details else label


def _report_next_action(final_status: str, commit_ready: bool) -> str:
    if final_status == "blocked":
        return "Resolve report blockers before any future commit preparation."
    if commit_ready:
        return "Preview guarded commit with devo delivery commit-preview before running --confirm-commit."
    return "Review delivery report before any future commit preparation."


def _markdown_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
