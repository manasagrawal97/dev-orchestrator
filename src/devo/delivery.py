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
    commit_ready: bool = False
    push_ready: bool = False
    commit_hash: str | None = None
    pushed: bool = False
    final_status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
            "next_action": "Controlled commit command is future scope; do not commit or push from Devo yet.",
            "updated_at": now,
        }
    )
    plan = plan.model_copy(
        update={
            "approval_status": "approved",
            "delivery_status": "approved",
            "updated_at": now,
            "next_action": "Delivery approved for a future controlled commit step; Devo still does not commit or push.",
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
        commit_ready=commit_ready,
        push_ready=False,
        commit_hash=None,
        pushed=False,
        final_status=final_status,
        next_action=_report_next_action(final_status, commit_ready),
    )
    return write_delivery_report(report, workspace_root=root)


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
            f"- Approval status: `{report.approval_status}`",
            f"- Delivery readiness: `{report.delivery_readiness_status}`",
            f"- Source plan: `{report.source_delivery_plan_id}`",
            f"- Source check: `{report.source_delivery_check_id or 'unknown'}`",
            f"- Proposed commit message: `{report.proposed_commit_message}`",
            f"- Target repo: `{report.target_repo_path}`",
            f"- Branch: `{report.branch or 'unknown'}`",
            f"- Remote/upstream: `{report.remote or 'unknown'}`",
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
            "## Next Action",
            "",
            report.next_action,
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


def _next_delivery_id(project_name: str, workspace_root: Path | None = None) -> str:
    checks = list_delivery_checks(project_name, workspace_root=workspace_root)
    highest = 0
    for check in checks:
        try:
            highest = max(highest, int(check.delivery_id.rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"DEL-{highest + 1:04d}"


def _require_delivery_plan(project_name: str, delivery_id: str, workspace_root: Path) -> DeliveryPlan:
    plan = load_delivery_plan(project_name, delivery_id, workspace_root=workspace_root)
    if not plan:
        msg = f"Delivery plan not found: {delivery_id}"
        raise ValueError(msg)
    return plan


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


def _plan_next_action(delivery_status: str, approval_status: str) -> str:
    if delivery_status == "blocked":
        return "Resolve delivery blockers and create a new delivery readiness check before approval."
    if approval_status == "not_requested":
        return "Request delivery approval with devo delivery approval-request."
    if approval_status == "requested":
        return "Review the delivery approval request; approve or reject the plan."
    if approval_status == "approved":
        return "Delivery approved for a future controlled commit step; Devo still does not commit or push."
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
        return "Controlled commit command is future scope; do not commit or push from Devo yet."
    if approval_status == "rejected":
        return "Revise the delivery plan or resolve blockers before requesting approval again."
    return "Review delivery approval state."


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


def _report_next_action(final_status: str, commit_ready: bool) -> str:
    if final_status == "blocked":
        return "Resolve report blockers before any future commit preparation."
    if commit_ready:
        return "Commit message is prepared; controlled commit command remains future scope."
    return "Review delivery report before any future commit preparation."


def _markdown_list(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
