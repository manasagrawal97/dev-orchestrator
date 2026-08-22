from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pydantic import ValidationError
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .projects import get_workspace_root
from .scanner import load_registered_project
from .work_packages import BUILT_IN_LANES

PLANNING_DIR_NAME = "planning"
PROJECT_BRIEF_JSON = "project-brief.json"
PROJECT_BRIEF_MD = "project-brief.md"
BLUEPRINT_JSON = "blueprint.json"
BLUEPRINT_MD = "blueprint.md"
BACKLOG_JSON = "backlog.json"
BACKLOG_MD = "backlog.md"
BACKLOG_REFINEMENT_PROMPT_MD = "backlog-refinement-prompt.md"
INTAKE_TEMPLATE_MD = "intake-template.md"
INTAKE_PROMPT_MD = "intake-prompt.md"
BATCHES_DIR_NAME = "batches"
BATCH_INDEX_JSON = "batch-index.json"
BATCH_APPROVALS_DIR_NAME = "approvals"
QUEUES_DIR_NAME = "queues"
QUEUE_INDEX_JSON = "queue-index.json"
EXECUTION_POLICIES_DIR_NAME = "execution-policies"
EXECUTION_POLICY_INDEX_JSON = "execution-policy-index.json"
QUEUE_WORKER_RUNS_DIR_NAME = "queue-worker-runs"
QUEUE_WORKER_RUN_INDEX_JSON = "queue-worker-run-index.json"
HANDOFFS_DIR_NAME = "handoffs"
HANDOFF_INDEX_JSON = "handoff-index.json"
WORKERS_DIR_NAME = "workers"
CODEX_WORKER_DIR_NAME = "codex"
WORKER_RUN_INDEX_JSON = "worker-run-index.json"
WORKER_REPORTS_DIR_NAME = "reports"
WORKER_REVIEWS_DIR_NAME = "reviews"
WORKER_REVIEW_INDEX_JSON = "review-index.json"
WORKER_RUN_PLANS_DIR_NAME = "run-plans"
WORKER_RUN_PLAN_INDEX_JSON = "run-plan-index.json"
WORKER_LOGS_DIR_NAME = "logs"
PLANNING_SCHEMA_VERSION = "1"
ALLOWED_BACKLOG_STATUSES = {"draft", "reviewed", "approved", "superseded"}
ALLOWED_TASK_STATUSES = {"draft", "ready", "approved", "in_progress", "blocked", "completed", "superseded"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_BATCH_STATUSES = {"draft", "reviewed", "approved", "in_progress", "completed", "blocked", "superseded"}
ALLOWED_BATCH_APPROVAL_STATUSES = {"not_requested", "requested", "approved", "rejected"}
ALLOWED_BATCH_REVIEW_STATUSES = {"not_reviewed", "reviewed", "needs_changes"}
ALLOWED_QUEUE_STATUSES = {"draft", "ready", "running", "paused_usage_limit", "paused_failure", "waiting_review", "completed", "cancelled", "superseded"}
ALLOWED_QUEUE_ITEM_STATUSES = {"pending", "running", "waiting_review", "paused", "blocked", "failed", "completed", "skipped", "superseded"}
ALLOWED_EXECUTION_POLICY_STATUSES = {"draft", "requested", "approved", "rejected", "expired", "cancelled", "completed"}
ALLOWED_QUEUE_WORKER_RUN_STATUSES = {
    "no_policy",
    "blocked",
    "no_ready_item",
    "handoff_ready",
    "waiting_worker",
    "waiting_review",
    "waiting_validation",
    "ready_for_delivery_request",
    "delivery_requested",
    "completed",
    "paused",
    "failed",
    "cancelled",
}
PAUSED_QUEUE_STATUSES = {"paused_usage_limit", "paused_failure", "waiting_review"}
ALLOWED_HANDOFF_STATUSES = {"draft", "used", "superseded"}
ALLOWED_HANDOFF_TYPES = {"task", "batch", "queue_next"}
ALLOWED_WORKER_RUN_MODES = {"manual_handoff", "assisted_handoff", "supervised_cli", "future_queue_worker"}
ALLOWED_WORKER_RUN_STATUSES = {
    "planned",
    "running",
    "completed",
    "failed",
    "paused_usage_limit",
    "blocked_needs_approval",
    "cancelled",
    "waiting_review",
    "superseded",
}
ALLOWED_WORKER_REPORT_STATUSES = {"missing", "present", "validated", "rejected"}
ALLOWED_WORKER_REPORTED_STATUSES = {"completed", "failed", "blocked", "partial", "usage_limit", "needs_approval"}
ALLOWED_WORKER_REVIEW_STATUSES = {"draft", "reviewed_passed", "reviewed_needs_changes", "rejected"}
ALLOWED_VALIDATION_EVIDENCE_STATUSES = {"not_provided", "provided", "passed", "failed", "partial"}
ALLOWED_WORKER_RUN_PLAN_STATUSES = {"draft", "ready", "blocked", "superseded"}
ALLOWED_WORKER_RUN_PLAN_APPROVAL_STATUSES = {"not_requested", "requested", "approved", "rejected"}
ALLOWED_WORKER_PREFLIGHT_STATUSES = {"not_run", "passed", "warnings", "blocked"}
SELECTABLE_TASK_STATUSES = {"draft", "ready", "approved"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
DEFAULT_EXECUTION_POLICY_PAUSE_CONDITIONS = [
    "tests failed",
    "secret risk",
    "forbidden path",
    "changed files outside allowed scope",
    "too many files",
    "unclear worker output",
    "usage limit",
    "commit failure",
    "push failure",
]


class ProjectBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    title: str
    summary: str
    problem_statement: str = ""
    goals: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    target_users: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    tech_stack_notes: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BlueprintMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    summary: str
    target_outcome: str
    status: str = "draft"


class BlueprintEpic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    milestone_id: str | None = None
    title: str
    summary: str
    status: str = "draft"


class ProjectBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    title: str
    brief_reference: str
    vision_summary: str
    milestones: list[BlueprintMilestone] = Field(default_factory=list)
    epics: list[BlueprintEpic] = Field(default_factory=list)
    architecture_notes: list[str] = Field(default_factory=list)
    risk_summary: list[str] = Field(default_factory=list)
    validation_strategy: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BacklogTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    summary: str
    milestone_id: str | None = None
    epic_id: str | None = None
    lane: str
    risk_level: str
    status: str = "draft"
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectBacklog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    title: str
    blueprint_reference: str
    status: str = "draft"
    tasks: list[BacklogTask] = Field(default_factory=list)
    task_count: int = 0
    ready_task_count: int = 0
    blocked_task_count: int = 0
    completed_task_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BacklogValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    task_count: int = 0


class BatchTaskSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria_summary: str = ""
    validation_expectations_summary: str = ""


class ProjectBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batch_id: str
    title: str
    summary: str
    source_backlog_reference: str
    status: str = "draft"
    task_ids: list[str] = Field(default_factory=list)
    task_count: int = 0
    completed_task_count: int = 0
    blocked_task_count: int = 0
    risk_summary: dict[str, int] = Field(default_factory=dict)
    lane_summary: dict[str, int] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    approval_status: str = "not_requested"
    review_status: str = "not_reviewed"
    review_notes: list[str] = Field(default_factory=list)
    task_snapshots: list[BatchTaskSnapshot] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batch_id: str
    approval_status: str = "not_requested"
    review_status: str = "not_reviewed"
    requested_at: datetime | None = None
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    reviewer: str | None = None
    approver: str | None = None
    decision_note: str = ""
    review_notes: list[str] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    risk_summary: dict[str, int] = Field(default_factory=dict)
    lane_summary: dict[str, int] = Field(default_factory=dict)
    task_count: int = 0
    high_risk_task_count: int = 0
    blocked_dependency_count: int = 0
    scope_summary: list[str] = Field(default_factory=list)
    validation_summary: list[str] = Field(default_factory=list)
    next_action: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    title: str
    status: str
    task_count: int
    approval_status: str
    path: str
    updated_at: datetime


class BatchIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batches: list[BatchIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchExecutionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    policy_id: str
    batch_id: str
    queue_id: str | None = None
    title: str
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requested_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    expires_at: datetime | None = None
    approver: str | None = None
    reviewer: str | None = None
    decision_note: str = ""
    allowed_task_ids: list[str] = Field(default_factory=list)
    allowed_queue_item_ids: list[str] = Field(default_factory=list)
    allowed_file_patterns: list[str] = Field(default_factory=list)
    forbidden_file_patterns: list[str] = Field(default_factory=list)
    max_tasks: int = 1
    max_tasks_per_run: int = 1
    max_changed_files_per_task: int = 20
    max_total_changed_files: int = 20
    validation_commands: list[str] = Field(default_factory=list)
    auto_delivery_allowed: bool = True
    auto_push_allowed: bool = True
    requires_worker_review: bool = True
    requires_validation_evidence: bool = True
    pause_conditions: list[str] = Field(default_factory=lambda: list(DEFAULT_EXECUTION_POLICY_PAUSE_CONDITIONS))
    risk_level: str = "medium"
    notes: list[str] = Field(default_factory=list)
    next_action: str = ""


class ExecutionPolicyIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    batch_id: str
    queue_id: str | None = None
    title: str
    status: str
    task_count: int
    auto_delivery_allowed: bool
    auto_push_allowed: bool
    path: str
    updated_at: datetime


class ExecutionPolicyIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    policies: list[ExecutionPolicyIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionPolicyCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    policy_id: str
    usable: bool = False
    status: str = "missing"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""


class QueueWorkerPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    policy_id: str
    usable: bool = False
    status: str = "blocked"
    batch_id: str | None = None
    queue_id: str | None = None
    selected_queue_item_id: str | None = None
    selected_task_id: str | None = None
    eligible_queue_item_ids: list[str] = Field(default_factory=list)
    skipped_queue_item_summaries: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy_check_summary: str = ""
    selection_reason: str = ""
    next_action: str = ""


class QueueWorkerRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    run_id: str
    policy_id: str
    batch_id: str | None = None
    queue_id: str | None = None
    selected_queue_item_id: str | None = None
    selected_task_id: str | None = None
    selected_handoff_id: str | None = None
    selected_worker_run_id: str | None = None
    mode: str = "assisted"
    status: str = "blocked"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    approver: str | None = None
    steps_run: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_queue_item_summaries: list[str] = Field(default_factory=list)
    policy_check_summary: str = ""
    selection_reason: str = ""
    pause_reason: str = ""
    failure_reason: str = ""
    cancel_reason: str = ""
    retry_of: str | None = None
    paused_at: datetime | None = None
    resumed_at: datetime | None = None
    failed_at: datetime | None = None
    cancelled_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str = ""


class QueueWorkerEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_exists: bool = False
    worker_run_exists: bool = False
    worker_report_imported: bool = False
    worker_review_exists: bool = False
    worker_review_passed: bool = False
    validation_evidence_exists: bool = False
    validation_passed: bool = False
    delivery_request_exists: bool = False
    delivery_completed: bool = False
    missing_evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QueueWorkerStatusReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    has_runs: bool = False
    run_id: str | None = None
    policy_id: str | None = None
    queue_id: str | None = None
    selected_queue_item_id: str | None = None
    selected_task_id: str | None = None
    selected_handoff_id: str | None = None
    selected_worker_run_id: str | None = None
    status: str = "no_runs"
    pause_reason: str = ""
    failure_reason: str = ""
    retry_of: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    evidence: QueueWorkerEvidenceSummary = Field(default_factory=QueueWorkerEvidenceSummary)
    next_action: str = ""


class QueueWorkerRunIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    policy_id: str
    batch_id: str | None = None
    queue_id: str | None = None
    selected_queue_item_id: str | None = None
    selected_task_id: str | None = None
    selected_worker_run_id: str | None = None
    status: str
    path: str
    updated_at: datetime


class QueueWorkerRunIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    runs: list[QueueWorkerRunIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str
    reason: str


class BatchSuggestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    suggested_tasks: list[BatchSuggestion] = Field(default_factory=list)
    skipped_tasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PlanningProgressGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    task_count: int = 0
    active_task_count: int = 0
    completed_task_count: int = 0
    blocked_task_count: int = 0
    ready_task_count: int = 0
    approved_task_count: int = 0
    draft_task_count: int = 0
    completion_percent: float = 0.0
    readiness_percent: float = 0.0
    blocked_percent: float = 0.0


class ProjectProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    has_brief: bool = False
    brief_status: str = "missing"
    has_blueprint: bool = False
    blueprint_status: str = "missing"
    has_backlog: bool = False
    backlog_status: str = "missing"
    task_count: int = 0
    completed_task_count: int = 0
    active_task_count: int = 0
    blocked_task_count: int = 0
    approved_task_count: int = 0
    ready_task_count: int = 0
    draft_task_count: int = 0
    project_completion_percent: float = 0.0
    backlog_readiness_percent: float = 0.0
    blocked_percent: float = 0.0
    batch_count: int = 0
    approved_batch_count: int = 0
    completed_batch_count: int = 0
    active_batch_count: int = 0
    batch_completion_percent: float = 0.0
    latest_batch_id: str | None = None
    latest_batch_status: str | None = None
    milestone_progress: list[PlanningProgressGroup] = Field(default_factory=list)
    epic_progress: list[PlanningProgressGroup] = Field(default_factory=list)
    next_action: str = "Create a Project Brief."
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectIntakeStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    target_repo_path: str
    brief_status: str = "missing"
    blueprint_status: str = "missing"
    backlog_status: str = "missing"
    task_count: int = 0
    ready_task_count: int = 0
    blocked_task_count: int = 0
    batch_count: int = 0
    latest_batch_id: str | None = None
    latest_batch_status: str | None = None
    latest_batch_approval_status: str | None = None
    queue_count: int = 0
    latest_queue_id: str | None = None
    latest_queue_status: str | None = None
    handoff_count: int = 0
    latest_handoff_id: str | None = None
    latest_handoff_status: str | None = None
    project_completion_percent: float = 0.0
    backlog_readiness_percent: float = 0.0
    blocked_percent: float = 0.0
    next_action: str
    next_command: str
    helper_commands: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str = "pending"
    batch_id: str
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class ExecutionQueue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    queue_id: str
    title: str
    source_batch_id: str
    source_backlog_reference: str
    status: str = "ready"
    items: list[QueueItem] = Field(default_factory=list)
    item_count: int = 0
    pending_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    blocked_count: int = 0
    failed_count: int = 0
    pause_reason: str | None = None
    resume_hint: str | None = None
    current_item_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_id: str
    title: str
    source_batch_id: str
    status: str
    item_count: int
    pending_count: int
    completed_count: int
    blocked_count: int
    path: str
    updated_at: datetime


class QueueIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    queues: list[QueueIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodexHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    handoff_id: str
    handoff_type: str
    source_queue_id: str | None = None
    source_batch_id: str | None = None
    source_item_id: str | None = None
    source_task_id: str | None = None
    title: str
    status: str = "draft"
    prompt_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HandoffIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str
    handoff_type: str
    title: str
    status: str
    source_queue_id: str | None = None
    source_batch_id: str | None = None
    source_item_id: str | None = None
    source_task_id: str | None = None
    prompt_path: str
    updated_at: datetime


class HandoffIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    handoffs: list[HandoffIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkerReportMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_status: str = "missing"
    reported_changed_files: list[str] = Field(default_factory=list)
    reported_validation: list[str] = Field(default_factory=list)
    reported_commit_hash: str | None = None
    safety_warnings: list[str] = Field(default_factory=list)
    reviewer_notes: list[str] = Field(default_factory=list)
    imported_at: datetime | None = None


class CodexWorkerReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    worker_run_id: str
    source_handoff_id: str | None = None
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_task_id: str | None = None
    status_reported_by_worker: str
    summary: str
    changed_files: list[str] = Field(default_factory=list)
    validation_attempted: bool = False
    validation_results: list[str] = Field(default_factory=list)
    tests_run: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    commit_hash: str | None = None
    safety_warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    follow_up_needed: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    reported_at: datetime | None = None


class WorkerReportValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report: CodexWorkerReport | None = None


class ValidationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_status: str = "not_provided"
    commands_reported: list[str] = Field(default_factory=list)
    tests_reported: list[str] = Field(default_factory=list)
    validation_summary: str = ""
    evidence_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkerReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    review_id: str
    worker_run_id: str
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_task_id: str | None = None
    source_handoff_id: str | None = None
    source_report_path: str | None = None
    review_status: str = "draft"
    reviewer: str | None = None
    decision_note: str = ""
    validation_evidence: ValidationEvidence = Field(default_factory=ValidationEvidence)
    changed_files_review: list[str] = Field(default_factory=list)
    safety_review: list[str] = Field(default_factory=list)
    acceptance_criteria_review: list[str] = Field(default_factory=list)
    follow_up_items: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    next_action: str = ""


class WorkerReviewIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    worker_run_id: str
    review_status: str
    validation_status: str
    reviewer: str | None = None
    path: str
    updated_at: datetime


class WorkerReviewIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    reviews: list[WorkerReviewIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkerRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    worker_run_id: str
    worker_type: str = "codex_cli"
    mode: str = "manual_handoff"
    source_handoff_id: str | None = None
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_batch_id: str | None = None
    source_task_id: str | None = None
    title: str
    status: str = "planned"
    prompt_path: str
    transcript_path: str | None = None
    report_path: str | None = None
    target_repo_path: str
    execution_exit_code: int | None = None
    execution_command_label: str | None = None
    execution_started_by: str | None = None
    execution_log_path: str | None = None
    execution_stderr_log_path: str | None = None
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    report: WorkerReportMetadata = Field(default_factory=WorkerReportMetadata)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status_note: str = ""
    next_action: str = ""


class WorkerRunIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_run_id: str
    worker_type: str
    mode: str
    title: str
    status: str
    source_handoff_id: str | None = None
    source_queue_id: str | None = None
    source_queue_item_id: str | None = None
    source_batch_id: str | None = None
    source_task_id: str | None = None
    report_status: str = "missing"
    next_action: str
    path: str
    updated_at: datetime


class WorkerRunIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    worker_runs: list[WorkerRunIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodexPreflightCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: str
    detail: str


class CodexPreflightResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    worker_run_id: str
    status: str
    checks: list[CodexPreflightCheck] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""


class CodexExecutableDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    launcher_type: str = "not_found"
    executable_path: str | None = None
    executable_source: str = "not_found"
    wrapper_path: str | None = None
    wsl_distribution: str | None = None
    command_preview: str = ""
    exists: bool = False
    is_windowsapps_alias: bool = False
    command_resolution_note: str = ""
    launch_risk: str = "unknown"
    launch_blockers: list[str] = Field(default_factory=list)
    launch_warnings: list[str] = Field(default_factory=list)
    candidate_paths: list[str] = Field(default_factory=list)
    npm_global_bin_candidates: list[str] = Field(default_factory=list)
    wsl_available: bool | None = None
    execution_supported: bool = False
    recommended_next_action: str = ""


class CodexRunPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    plan_id: str
    worker_run_id: str
    handoff_id: str
    queue_id: str | None = None
    queue_item_id: str | None = None
    task_id: str | None = None
    batch_id: str | None = None
    status: str = "draft"
    target_repo_path: str
    prompt_path: str
    proposed_working_directory: str
    proposed_command_label: str = "Codex CLI supervised worker"
    proposed_command_preview: str
    launcher_type: str = "path_detection"
    codex_executable_path: str | None = None
    codex_executable_source: str = "path_detection"
    codex_wrapper_path: str | None = None
    codex_wsl_distribution: str | None = None
    command_resolution_note: str = ""
    launch_risk: str = "unknown"
    launch_blockers: list[str] = Field(default_factory=list)
    launch_warnings: list[str] = Field(default_factory=list)
    approval_required: bool = True
    approval_status: str = "not_requested"
    approval_note: str | None = None
    preflight_status: str = "not_run"
    preflight_checks: list[CodexPreflightCheck] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodexRunPlanIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str
    worker_run_id: str
    handoff_id: str
    status: str
    approval_status: str
    preflight_status: str
    path: str
    next_action: str
    updated_at: datetime


class CodexRunPlanIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    run_plans: list[CodexRunPlanIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodexExecutionPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    worker_run_id: str
    plan_id: str
    ready: bool
    launcher_type: str = "not_found"
    executable_path: str | None = None
    wrapper_path: str | None = None
    wsl_distribution: str | None = None
    executable_source: str = "not_found"
    command_resolution_note: str = ""
    launch_risk: str = "unknown"
    command_preview: str = ""
    execution_supported: bool = False
    command_label: str = "Codex CLI supervised worker"
    proposed_working_directory: str
    prompt_path: str
    log_path: str
    stderr_log_path: str
    approval_status: str
    preflight_status: str
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    next_action: str = ""


class CodexExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    worker_run_id: str
    plan_id: str
    status: str
    exit_code: int
    launch_error_type: str | None = None
    launch_error_message: str | None = None
    log_path: str
    stderr_log_path: str
    started_at: datetime
    completed_at: datetime
    next_action: str


class CodexQueueWorkerStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    queue_id: str
    queue_status: str
    current_item_id: str | None = None
    current_item_status: str | None = None
    current_task_id: str | None = None
    selected_item_source: str = "none"
    source_handoff_id: str | None = None
    linked_worker_run_id: str | None = None
    linked_worker_run_status: str | None = None
    linked_run_plan_id: str | None = None
    linked_run_plan_status: str | None = None
    latest_worker_execution_status: str | None = None
    latest_worker_execution_exit_code: int | None = None
    latest_worker_execution_log_path: str | None = None
    latest_worker_report_status: str | None = None
    latest_worker_review_id: str | None = None
    latest_worker_review_status: str | None = None
    latest_worker_validation_status: str | None = None
    current_queue_item_completion_ready: bool = False
    current_queue_item_completion_blockers: list[str] = Field(default_factory=list)
    current_queue_item_review_status: str | None = None
    current_queue_item_validation_status: str | None = None
    next_action: str


class CodexWorkerFlowSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    queue_id: str
    queue_status: str
    selected_item_id: str | None = None
    selected_item_status: str | None = None
    source_handoff_id: str | None = None
    linked_worker_run_id: str | None = None
    linked_worker_run_status: str | None = None
    linked_run_plan_id: str | None = None
    linked_run_plan_status: str | None = None
    linked_run_plan_preflight_status: str | None = None
    worker_report_status: str | None = None
    worker_review_status: str | None = None
    validation_evidence_status: str | None = None
    completion_ready: bool = False
    completion_blockers: list[str] = Field(default_factory=list)
    next_commands: list[str] = Field(default_factory=list)


class QueueItemCompletionReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    queue_id: str
    item_id: str
    item_status: str
    linked_worker_run_id: str | None = None
    review_id: str | None = None
    review_status: str | None = None
    validation_status: str | None = None
    completion_ready: bool = True
    blockers: list[str] = Field(default_factory=list)
    next_action: str = ""


class WorkerArtifactPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_dir: Path
    codex_dir: Path
    worker_run_index_json: Path
    reports_dir: Path
    reviews_dir: Path
    review_index_json: Path
    run_plans_dir: Path
    run_plan_index_json: Path
    logs_dir: Path


class PlanningArtifactPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_dir: Path
    brief_json: Path
    brief_markdown: Path
    blueprint_json: Path
    blueprint_markdown: Path
    backlog_json: Path
    backlog_markdown: Path
    backlog_refinement_prompt: Path
    batches_dir: Path
    batch_approvals_dir: Path
    batch_index_json: Path
    queues_dir: Path
    queue_index_json: Path
    execution_policies_dir: Path
    execution_policy_index_json: Path
    queue_worker_runs_dir: Path
    queue_worker_run_index_json: Path
    handoffs_dir: Path
    handoff_index_json: Path


def planning_artifact_paths(project_name: str, workspace_root: Path | None = None) -> PlanningArtifactPaths:
    root = workspace_root or get_workspace_root()
    planning_dir = root / "projects" / project_name / PLANNING_DIR_NAME
    return PlanningArtifactPaths(
        planning_dir=planning_dir,
        brief_json=planning_dir / PROJECT_BRIEF_JSON,
        brief_markdown=planning_dir / PROJECT_BRIEF_MD,
        blueprint_json=planning_dir / BLUEPRINT_JSON,
        blueprint_markdown=planning_dir / BLUEPRINT_MD,
        backlog_json=planning_dir / BACKLOG_JSON,
        backlog_markdown=planning_dir / BACKLOG_MD,
        backlog_refinement_prompt=planning_dir / BACKLOG_REFINEMENT_PROMPT_MD,
        batches_dir=planning_dir / BATCHES_DIR_NAME,
        batch_approvals_dir=planning_dir / BATCHES_DIR_NAME / BATCH_APPROVALS_DIR_NAME,
        batch_index_json=planning_dir / BATCHES_DIR_NAME / BATCH_INDEX_JSON,
        queues_dir=planning_dir / QUEUES_DIR_NAME,
        queue_index_json=planning_dir / QUEUES_DIR_NAME / QUEUE_INDEX_JSON,
        execution_policies_dir=planning_dir / EXECUTION_POLICIES_DIR_NAME,
        execution_policy_index_json=planning_dir / EXECUTION_POLICIES_DIR_NAME / EXECUTION_POLICY_INDEX_JSON,
        queue_worker_runs_dir=planning_dir / QUEUE_WORKER_RUNS_DIR_NAME,
        queue_worker_run_index_json=planning_dir / QUEUE_WORKER_RUNS_DIR_NAME / QUEUE_WORKER_RUN_INDEX_JSON,
        handoffs_dir=planning_dir / HANDOFFS_DIR_NAME,
        handoff_index_json=planning_dir / HANDOFFS_DIR_NAME / HANDOFF_INDEX_JSON,
    )


def worker_artifact_paths(project_name: str, workspace_root: Path | None = None) -> WorkerArtifactPaths:
    root = workspace_root or get_workspace_root()
    worker_dir = root / "projects" / project_name / WORKERS_DIR_NAME
    codex_dir = worker_dir / CODEX_WORKER_DIR_NAME
    return WorkerArtifactPaths(
        worker_dir=worker_dir,
        codex_dir=codex_dir,
        worker_run_index_json=codex_dir / WORKER_RUN_INDEX_JSON,
        reports_dir=codex_dir / WORKER_REPORTS_DIR_NAME,
        reviews_dir=codex_dir / WORKER_REVIEWS_DIR_NAME,
        review_index_json=codex_dir / WORKER_REVIEWS_DIR_NAME / WORKER_REVIEW_INDEX_JSON,
        run_plans_dir=codex_dir / WORKER_RUN_PLANS_DIR_NAME,
        run_plan_index_json=codex_dir / WORKER_RUN_PLANS_DIR_NAME / WORKER_RUN_PLAN_INDEX_JSON,
        logs_dir=codex_dir / WORKER_LOGS_DIR_NAME,
    )


def worker_run_artifact_paths(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_worker_run_id(worker_run_id)
    return paths.codex_dir / f"worker-run-{safe_id}.json", paths.codex_dir / f"worker-run-{safe_id}.md"


def worker_report_template_paths(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_worker_run_id(worker_run_id)
    return paths.reports_dir / f"report-{safe_id}-template.json", paths.reports_dir / f"report-{safe_id}-template.md"


def worker_report_artifact_paths(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_worker_run_id(worker_run_id)
    return paths.reports_dir / f"report-{safe_id}.json", paths.reports_dir / f"report-{safe_id}.md"


def worker_review_artifact_paths(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_worker_run_id(worker_run_id)
    return paths.reviews_dir / f"review-{safe_id}.json", paths.reviews_dir / f"review-{safe_id}.md"


def worker_run_plan_artifact_paths(project_name: str, plan_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_run_plan_id(plan_id)
    return paths.run_plans_dir / f"run-plan-{safe_id}.json", paths.run_plans_dir / f"run-plan-{safe_id}.md"


def worker_execution_log_paths(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_worker_run_id(worker_run_id)
    return paths.logs_dir / f"worker-run-{safe_id}.log", paths.logs_dir / f"worker-run-{safe_id}.stderr.log"


def create_project_brief(
    project_name: str,
    title: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> tuple[ProjectBrief, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Brief source file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Brief source path must be a file: {source_path}"
        raise ValueError(msg)

    text = _read_planning_text_file(source_path)
    now = datetime.now(UTC)
    existing = load_project_brief(project_name, workspace_root=root)
    created_at = existing.created_at if existing else now
    brief = ProjectBrief(
        project=project_name,
        title=_clean_planning_text(title).strip(),
        summary=_summarize_text(text),
        problem_statement=_extract_section(text, ("problem", "problem statement")),
        goals=_extract_list_section(text, ("goals", "objectives")),
        non_goals=_extract_list_section(text, ("non-goals", "non goals", "out of scope")),
        target_users=_extract_list_section(text, ("target users", "users", "audience")),
        constraints=_extract_list_section(text, ("constraints", "rules")),
        assumptions=_extract_list_section(text, ("assumptions",)),
        risks=_extract_list_section(text, ("risks",)),
        tech_stack_notes=_extract_list_section(text, ("tech stack", "technology", "stack")),
        validation_expectations=_extract_list_section(text, ("validation", "tests", "acceptance")),
        source_notes=[f"Created from source file: {source_path.name}", "Deterministic import; no AI or Codex automation was used."],
        status="draft",
        created_at=created_at,
        updated_at=now,
    )
    if not brief.title:
        msg = "Brief title must not be empty."
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    _write_model(paths.brief_json, brief)
    paths.brief_markdown.write_text(render_project_brief_markdown(brief, source_text=text), encoding="utf-8")
    return brief, paths


def load_project_brief(project_name: str, workspace_root: Path | None = None) -> ProjectBrief | None:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.brief_json.exists():
        return None
    return ProjectBrief.model_validate_json(paths.brief_json.read_text(encoding="utf-8"))


def approve_project_brief(project_name: str, workspace_root: Path | None = None) -> tuple[ProjectBrief, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    if not brief:
        msg = f"Project brief not found for project: {project_name}"
        raise ValueError(msg)
    updated = brief.model_copy(update={"status": "approved", "updated_at": datetime.now(UTC)})
    paths = planning_artifact_paths(project_name, workspace_root=root)
    _write_model(paths.brief_json, updated)
    paths.brief_markdown.write_text(render_project_brief_markdown(updated), encoding="utf-8")
    return updated, paths


def create_project_blueprint(project_name: str, workspace_root: Path | None = None) -> tuple[ProjectBlueprint, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    if not brief:
        msg = f"Project brief not found for project: {project_name}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    now = datetime.now(UTC)
    existing = load_project_blueprint(project_name, workspace_root=root)
    created_at = existing.created_at if existing else now
    milestones = _default_milestones(brief)
    blueprint = ProjectBlueprint(
        project=project_name,
        title=f"{brief.title} Blueprint",
        brief_reference=str(paths.brief_json),
        vision_summary=brief.summary,
        milestones=milestones,
        epics=_default_epics(milestones),
        architecture_notes=_default_architecture_notes(brief),
        risk_summary=_default_risk_summary(brief),
        validation_strategy=_default_validation_strategy(brief),
        open_questions=_default_open_questions(brief),
        status="draft",
        created_at=created_at,
        updated_at=now,
    )
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    _write_model(paths.blueprint_json, blueprint)
    paths.blueprint_markdown.write_text(render_project_blueprint_markdown(blueprint), encoding="utf-8")
    return blueprint, paths


def load_project_blueprint(project_name: str, workspace_root: Path | None = None) -> ProjectBlueprint | None:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.blueprint_json.exists():
        return None
    return ProjectBlueprint.model_validate_json(paths.blueprint_json.read_text(encoding="utf-8"))


def approve_project_blueprint(project_name: str, workspace_root: Path | None = None) -> tuple[ProjectBlueprint, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    if not blueprint:
        msg = f"Project blueprint not found for project: {project_name}"
        raise ValueError(msg)
    updated = blueprint.model_copy(update={"status": "approved", "updated_at": datetime.now(UTC)})
    paths = planning_artifact_paths(project_name, workspace_root=root)
    _write_model(paths.blueprint_json, updated)
    paths.blueprint_markdown.write_text(render_project_blueprint_markdown(updated), encoding="utf-8")
    return updated, paths


def create_project_backlog(project_name: str, workspace_root: Path | None = None) -> tuple[ProjectBacklog, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    if not blueprint:
        msg = f"Project blueprint not found for project: {project_name}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    now = datetime.now(UTC)
    existing = load_project_backlog(project_name, workspace_root=root)
    created_at = existing.created_at if existing else now
    tasks = _default_backlog_tasks(blueprint, now)
    backlog = _with_backlog_counts(
        ProjectBacklog(
            project=project_name,
            title=f"{blueprint.title} Backlog",
            blueprint_reference=str(paths.blueprint_json),
            status="draft",
            tasks=tasks,
            created_at=created_at,
            updated_at=now,
        )
    )
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    _write_model(paths.backlog_json, backlog)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(backlog), encoding="utf-8")
    return backlog, paths


def load_project_backlog(project_name: str, workspace_root: Path | None = None) -> ProjectBacklog | None:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.backlog_json.exists():
        return None
    return ProjectBacklog.model_validate_json(paths.backlog_json.read_text(encoding="utf-8"))


def approve_project_backlog(project_name: str, workspace_root: Path | None = None) -> tuple[ProjectBacklog, PlanningArtifactPaths]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    tasks = [
        task.model_copy(update={"status": "ready" if task.status == "draft" else task.status, "updated_at": now})
        for task in backlog.tasks
    ]
    updated = _with_backlog_counts(backlog.model_copy(update={"status": "approved", "tasks": tasks, "updated_at": now}))
    paths = planning_artifact_paths(project_name, workspace_root=root)
    _write_model(paths.backlog_json, updated)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(updated), encoding="utf-8")
    return updated, paths


def get_backlog_task(project_name: str, task_id: str, workspace_root: Path | None = None) -> BacklogTask:
    backlog = load_project_backlog(project_name, workspace_root=workspace_root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    normalized = task_id.strip().upper()
    for task in backlog.tasks:
        if task.id.upper() == normalized:
            return task
    msg = f"Backlog task not found: {task_id}"
    raise ValueError(msg)


def generate_backlog_refinement_prompt(project_name: str, workspace_root: Path | None = None) -> tuple[Path, str]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not blueprint:
        msg = f"Project blueprint not found for project: {project_name}"
        raise ValueError(msg)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    prompt = render_backlog_refinement_prompt(project_name, brief, blueprint, backlog)
    paths.backlog_refinement_prompt.write_text(prompt, encoding="utf-8")
    return paths.backlog_refinement_prompt, prompt


def validate_refined_backlog_file(
    project_name: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> tuple[BacklogValidationResult, ProjectBacklog | None]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Refined backlog file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Refined backlog path must be a file: {source_path}"
        raise ValueError(msg)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        backlog = ProjectBacklog.model_validate_json(source_path.read_text(encoding="utf-8-sig"))
    except (ValueError, ValidationError) as exc:
        return BacklogValidationResult(valid=False, errors=[f"Invalid backlog JSON: {exc}"]), None

    if backlog.project != project_name:
        errors.append(f"Backlog project must be {project_name}, got {backlog.project}.")
    if backlog.status not in ALLOWED_BACKLOG_STATUSES:
        errors.append(f"Invalid backlog status: {backlog.status}.")
    seen: set[str] = set()
    all_task_ids = {task.id.strip().upper() for task in backlog.tasks}
    known_lanes = set(BUILT_IN_LANES)
    for task in backlog.tasks:
        normalized_id = task.id.strip().upper()
        if normalized_id in seen:
            errors.append(f"Duplicate task id: {task.id}.")
        seen.add(normalized_id)
        if task.status not in ALLOWED_TASK_STATUSES:
            errors.append(f"Invalid status for {task.id}: {task.status}.")
        if task.risk_level not in ALLOWED_RISK_LEVELS:
            errors.append(f"Invalid risk level for {task.id}: {task.risk_level}.")
        if task.lane not in known_lanes:
            errors.append(f"Unknown lane for {task.id}: {task.lane}.")
        for dependency in task.dependencies:
            if dependency.strip().upper() not in all_task_ids:
                warnings.append(f"Task {task.id} depends on unknown task id: {dependency}.")
    result = BacklogValidationResult(valid=not errors, errors=errors, warnings=warnings, task_count=len(backlog.tasks))
    return result, backlog if result.valid else None


def import_refined_backlog(
    project_name: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> tuple[ProjectBacklog, PlanningArtifactPaths, BacklogValidationResult]:
    root = workspace_root or get_workspace_root()
    result, backlog = validate_refined_backlog_file(project_name, source_file, workspace_root=root)
    if not result.valid or not backlog:
        msg = "Refined backlog validation failed: " + "; ".join(result.errors)
        raise ValueError(msg)
    now = datetime.now(UTC)
    safe_tasks = [task.model_copy(update={"status": _safe_import_task_status(task.status), "updated_at": now}) for task in backlog.tasks]
    imported = _with_backlog_counts(backlog.model_copy(update={"status": "draft", "tasks": safe_tasks, "updated_at": now}))
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    _write_model(paths.backlog_json, imported)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(imported), encoding="utf-8")
    return imported, paths, result


def create_project_batch(
    project_name: str,
    title: str,
    task_ids: list[str],
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    normalized_ids = _normalize_task_ids(task_ids)
    if not normalized_ids:
        msg = "At least one task id is required."
        raise ValueError(msg)
    if len(set(normalized_ids)) != len(normalized_ids):
        msg = "Duplicate task ids are not allowed."
        raise ValueError(msg)
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    missing = [task_id for task_id in normalized_ids if task_id not in task_by_id]
    if missing:
        msg = f"Backlog task id not found: {', '.join(missing)}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    batch_id = _next_batch_id(project_name, workspace_root=root)
    tasks = [task_by_id[task_id] for task_id in normalized_ids]
    now = datetime.now(UTC)
    batch = _build_batch_from_tasks(
        project_name=project_name,
        batch_id=batch_id,
        title=title.strip() or f"Planning Batch {batch_id}",
        tasks=tasks,
        backlog=backlog,
        source_backlog_reference=str(paths.backlog_json),
        now=now,
    )
    json_path, markdown_path = _write_project_batch(project_name, batch, workspace_root=root)
    return batch, json_path, markdown_path


def suggest_project_batch(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> BatchSuggestionResult:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    safe_limit = max(1, limit)
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    completed = {task_id for task_id, task in task_by_id.items() if task.status == "completed"}
    selected: list[BacklogTask] = []
    skipped: list[str] = []
    warnings: list[str] = []
    candidates = sorted(
        [task for task in backlog.tasks if task.status in SELECTABLE_TASK_STATUSES],
        key=lambda task: (RISK_ORDER.get(task.risk_level, 99), task.lane, task.id),
    )
    for task in candidates:
        if len(selected) >= safe_limit:
            break
        selected_ids = {item.id.strip().upper() for item in selected}
        dependencies = [dependency.strip().upper() for dependency in task.dependencies]
        missing_dependencies = [dependency for dependency in dependencies if dependency not in task_by_id]
        unresolved = [dependency for dependency in dependencies if dependency not in completed and dependency not in selected_ids]
        if missing_dependencies:
            skipped.append(f"{task.id}: missing dependency {', '.join(missing_dependencies)}")
            continue
        if unresolved:
            skipped.append(f"{task.id}: unresolved dependency {', '.join(unresolved)}")
            continue
        selected.append(task)
    if not selected:
        warnings.append("No ready batch candidates found.")
    suggestions = [
        BatchSuggestion(
            task_id=task.id,
            title=task.title,
            lane=task.lane,
            risk_level=task.risk_level,
            status=task.status,
            reason=_suggestion_reason(task),
        )
        for task in selected
    ]
    return BatchSuggestionResult(project=project_name, suggested_tasks=suggestions, skipped_tasks=skipped, warnings=warnings)


def create_suggested_project_batch(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchSuggestionResult]:
    root = workspace_root or get_workspace_root()
    suggestion = suggest_project_batch(project_name, limit=limit, workspace_root=root)
    task_ids = [task.task_id for task in suggestion.suggested_tasks]
    if not task_ids:
        msg = "No suggested tasks are available for a batch."
        raise ValueError(msg)
    batch, json_path, markdown_path = create_project_batch(
        project_name,
        title="Suggested planning batch",
        task_ids=task_ids,
        workspace_root=root,
    )
    return batch, json_path, markdown_path, suggestion


def load_batch_index(project_name: str, workspace_root: Path | None = None) -> BatchIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.batch_index_json.exists():
        return BatchIndex(project=project_name)
    return BatchIndex.model_validate_json(paths.batch_index_json.read_text(encoding="utf-8"))


def list_project_batches(project_name: str, workspace_root: Path | None = None) -> list[ProjectBatch]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.batches_dir.exists():
        return []
    batches: list[ProjectBatch] = []
    for path in sorted(paths.batches_dir.glob("batch-*.json")):
        if path.name == BATCH_INDEX_JSON:
            continue
        try:
            batches.append(ProjectBatch.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(batches, key=lambda batch: batch.updated_at, reverse=True)


def load_project_batch(project_name: str, batch_id: str, workspace_root: Path | None = None) -> ProjectBatch | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = project_batch_artifact_paths(project_name, batch_id, workspace_root=root)
    if not json_path.exists():
        return None
    return ProjectBatch.model_validate_json(json_path.read_text(encoding="utf-8"))


def batch_approval_artifact_paths(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_batch_id(batch_id)
    return paths.batch_approvals_dir / f"batch-{safe_id}-approval.json", paths.batch_approvals_dir / f"batch-{safe_id}-approval.md"


def execution_policy_artifact_paths(project_name: str, policy_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_policy_id(policy_id)
    return paths.execution_policies_dir / f"execution-policy-{safe_id}.json", paths.execution_policies_dir / f"execution-policy-{safe_id}.md"


def queue_worker_run_artifact_paths(project_name: str, run_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_queue_worker_run_id(run_id)
    return paths.queue_worker_runs_dir / f"queue-worker-run-{safe_id}.json", paths.queue_worker_runs_dir / f"queue-worker-run-{safe_id}.md"


def load_batch_approval(project_name: str, batch_id: str, workspace_root: Path | None = None) -> BatchApproval | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = batch_approval_artifact_paths(project_name, batch_id, workspace_root=root)
    if not json_path.exists():
        return None
    return BatchApproval.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_batch_approvals(project_name: str, workspace_root: Path | None = None) -> list[BatchApproval]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.batch_approvals_dir.exists():
        return []
    approvals: list[BatchApproval] = []
    for path in sorted(paths.batch_approvals_dir.glob("batch-*-approval.json")):
        try:
            approvals.append(BatchApproval.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(approvals, key=lambda approval: approval.updated_at, reverse=True)


def load_execution_policy_index(project_name: str, workspace_root: Path | None = None) -> ExecutionPolicyIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.execution_policy_index_json.exists():
        return ExecutionPolicyIndex(project=project_name)
    return ExecutionPolicyIndex.model_validate_json(paths.execution_policy_index_json.read_text(encoding="utf-8"))


def list_execution_policies(project_name: str, workspace_root: Path | None = None) -> list[BatchExecutionPolicy]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.execution_policies_dir.exists():
        return []
    policies: list[BatchExecutionPolicy] = []
    for path in sorted(paths.execution_policies_dir.glob("execution-policy-*.json")):
        if path.name == EXECUTION_POLICY_INDEX_JSON:
            continue
        try:
            policies.append(BatchExecutionPolicy.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(policies, key=lambda policy: policy.updated_at, reverse=True)


def load_execution_policy(project_name: str, policy_id: str, workspace_root: Path | None = None) -> BatchExecutionPolicy | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = execution_policy_artifact_paths(project_name, policy_id, workspace_root=root)
    if not json_path.exists():
        return None
    return BatchExecutionPolicy.model_validate_json(json_path.read_text(encoding="utf-8"))


def load_queue_worker_run_index(project_name: str, workspace_root: Path | None = None) -> QueueWorkerRunIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.queue_worker_run_index_json.exists():
        return QueueWorkerRunIndex(project=project_name)
    return QueueWorkerRunIndex.model_validate_json(paths.queue_worker_run_index_json.read_text(encoding="utf-8"))


def list_queue_worker_runs(project_name: str, workspace_root: Path | None = None) -> list[QueueWorkerRun]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.queue_worker_runs_dir.exists():
        return []
    runs: list[QueueWorkerRun] = []
    for path in sorted(paths.queue_worker_runs_dir.glob("queue-worker-run-*.json")):
        if path.name == QUEUE_WORKER_RUN_INDEX_JSON:
            continue
        try:
            runs.append(QueueWorkerRun.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(runs, key=lambda run: run.updated_at, reverse=True)


def load_queue_worker_run(project_name: str, run_id: str, workspace_root: Path | None = None) -> QueueWorkerRun | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = queue_worker_run_artifact_paths(project_name, run_id, workspace_root=root)
    if not json_path.exists():
        return None
    return QueueWorkerRun.model_validate_json(json_path.read_text(encoding="utf-8"))


def create_batch_execution_policy(
    project_name: str,
    *,
    batch_id: str,
    title: str,
    queue_id: str | None = None,
    allowed_task_ids: list[str] | None = None,
    allowed_file_patterns: list[str] | None = None,
    forbidden_file_patterns: list[str] | None = None,
    max_tasks: int | None = None,
    max_tasks_per_run: int = 1,
    max_changed_files_per_task: int = 20,
    validation_commands: list[str] | None = None,
    auto_delivery_allowed: bool = True,
    auto_push_allowed: bool = True,
    expires_at: datetime | None = None,
    note: str = "",
    workspace_root: Path | None = None,
) -> tuple[BatchExecutionPolicy, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    batch = _require_batch(project_name, batch_id, root)
    normalized_queue_id = _normalize_queue_id(queue_id) if queue_id else None
    queue = None
    if normalized_queue_id:
        queue = load_execution_queue(project_name, normalized_queue_id, workspace_root=root)
        if not queue:
            msg = f"Execution queue not found: {queue_id}"
            raise ValueError(msg)
        if _normalize_batch_id(queue.source_batch_id) != _normalize_batch_id(batch.batch_id):
            msg = f"Execution queue {normalized_queue_id} is not for batch {batch.batch_id}."
            raise ValueError(msg)
    normalized_allowed_tasks = _normalize_task_ids(allowed_task_ids or [])
    if not normalized_allowed_tasks:
        normalized_allowed_tasks = list(batch.task_ids)
    batch_tasks = {_normalize_task_id(task_id) for task_id in batch.task_ids}
    unknown_tasks = [task_id for task_id in normalized_allowed_tasks if _normalize_task_id(task_id) not in batch_tasks]
    if unknown_tasks:
        msg = f"Allowed task ids are not in batch {batch.batch_id}: {', '.join(unknown_tasks)}"
        raise ValueError(msg)
    allowed_queue_items = [item.item_id for item in queue.items if _normalize_task_id(item.task_id) in {_normalize_task_id(task) for task in normalized_allowed_tasks}] if queue else []
    cleaned_title = _clean_planning_text(title).strip()
    if not cleaned_title:
        msg = "Policy title must not be empty."
        raise ValueError(msg)
    effective_max_tasks = max_tasks if max_tasks is not None else max(1, len(normalized_allowed_tasks))
    _validate_positive_limit("--max-tasks", effective_max_tasks)
    _validate_positive_limit("--max-tasks-per-run", max_tasks_per_run)
    _validate_positive_limit("--max-changed-files-per-task", max_changed_files_per_task)
    now = datetime.now(UTC)
    notes: list[str] = []
    cleaned_note = note.strip()
    if cleaned_note:
        notes.append(f"{now.isoformat()}: {cleaned_note}")
    max_total_changed_files = effective_max_tasks * max_changed_files_per_task
    policy = BatchExecutionPolicy(
        project=project_name,
        policy_id=_next_policy_id(project_name, workspace_root=root),
        batch_id=batch.batch_id,
        queue_id=normalized_queue_id,
        title=cleaned_title,
        status="draft",
        created_at=now,
        updated_at=now,
        expires_at=expires_at,
        allowed_task_ids=normalized_allowed_tasks,
        allowed_queue_item_ids=allowed_queue_items,
        allowed_file_patterns=_clean_string_list(allowed_file_patterns or []),
        forbidden_file_patterns=_clean_string_list(forbidden_file_patterns or []),
        max_tasks=effective_max_tasks,
        max_tasks_per_run=max_tasks_per_run,
        max_changed_files_per_task=max_changed_files_per_task,
        max_total_changed_files=max_total_changed_files,
        validation_commands=_clean_string_list(validation_commands or []),
        auto_delivery_allowed=auto_delivery_allowed,
        auto_push_allowed=auto_push_allowed,
        notes=notes,
        risk_level=_highest_policy_risk(batch),
        next_action=f"Request policy approval: devo project execution-policy-request --project {project_name} --policy <policyId> --note \"<note>\"",
    )
    return _write_execution_policy(project_name, policy, workspace_root=root)


def request_execution_policy(
    project_name: str,
    policy_id: str,
    *,
    note: str = "",
    workspace_root: Path | None = None,
) -> tuple[BatchExecutionPolicy, Path, Path]:
    root = workspace_root or get_workspace_root()
    policy = _require_execution_policy(project_name, policy_id, root)
    if policy.status not in {"draft", "requested"}:
        msg = f"Execution policy must be draft or requested, not {policy.status}."
        raise ValueError(msg)
    if not policy.allowed_task_ids and not policy.allowed_queue_item_ids:
        msg = "Execution policy must include allowed tasks or queue items before approval request."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = _with_timed_note(policy.notes, note, "request", now)
    warnings = []
    if not policy.forbidden_file_patterns:
        warnings.append("Warning: no forbidden file patterns recorded.")
    updated = policy.model_copy(
        update={
            "status": "requested",
            "requested_at": policy.requested_at or now,
            "updated_at": now,
            "notes": [*notes, *warnings],
            "next_action": f"Approve or reject: devo project execution-policy-approve --project {project_name} --policy {policy.policy_id} --approver \"<name>\" --note \"<note>\"",
        }
    )
    return _write_execution_policy(project_name, updated, workspace_root=root)


def approve_execution_policy(
    project_name: str,
    policy_id: str,
    *,
    approver: str,
    note: str = "",
    workspace_root: Path | None = None,
) -> tuple[BatchExecutionPolicy, Path, Path]:
    root = workspace_root or get_workspace_root()
    policy = _require_execution_policy(project_name, policy_id, root)
    if policy.status != "requested":
        msg = f"Execution policy must be requested before approval, not {policy.status}."
        raise ValueError(msg)
    cleaned_approver = approver.strip()
    if not cleaned_approver:
        msg = "Approver must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = _with_timed_note(policy.notes, note, "approval", now)
    updated = policy.model_copy(
        update={
            "status": "approved",
            "approved_at": now,
            "approver": cleaned_approver,
            "decision_note": note.strip() or policy.decision_note,
            "updated_at": now,
            "notes": notes,
            "next_action": "TASK-DEVO-129 autonomous queue worker loop can use this approved policy.",
        }
    )
    return _write_execution_policy(project_name, updated, workspace_root=root)


def reject_execution_policy(
    project_name: str,
    policy_id: str,
    *,
    reviewer: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[BatchExecutionPolicy, Path, Path]:
    root = workspace_root or get_workspace_root()
    policy = _require_execution_policy(project_name, policy_id, root)
    cleaned_reviewer = reviewer.strip()
    cleaned_note = note.strip()
    if not cleaned_reviewer:
        msg = "Reviewer must not be empty."
        raise ValueError(msg)
    if not cleaned_note:
        msg = "Rejection note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = _with_timed_note(policy.notes, cleaned_note, "rejection", now)
    updated = policy.model_copy(
        update={
            "status": "rejected",
            "rejected_at": now,
            "reviewer": cleaned_reviewer,
            "decision_note": cleaned_note,
            "updated_at": now,
            "notes": notes,
            "next_action": "Revise or create a smaller execution policy.",
        }
    )
    return _write_execution_policy(project_name, updated, workspace_root=root)


def check_execution_policy(
    project_name: str,
    policy_id: str,
    workspace_root: Path | None = None,
) -> ExecutionPolicyCheckResult:
    root = workspace_root or get_workspace_root()
    policy = load_execution_policy(project_name, policy_id, workspace_root=root)
    if not policy:
        return ExecutionPolicyCheckResult(
            project=project_name,
            policy_id=_normalize_policy_id(policy_id),
            status="missing",
            blockers=[f"Execution policy not found: {policy_id}"],
            next_action=f"List policies: devo project execution-policy-list --project {project_name}",
        )
    blockers: list[str] = []
    warnings: list[str] = []
    now = datetime.now(UTC)
    if policy.status != "approved":
        blockers.append(f"Policy status is {policy.status}; approved is required.")
    if policy.expires_at and policy.expires_at <= now:
        blockers.append(f"Policy expired at {policy.expires_at.isoformat()}.")
    batch = load_project_batch(project_name, policy.batch_id, workspace_root=root)
    if not batch:
        blockers.append(f"Referenced batch not found: {policy.batch_id}.")
    elif policy.allowed_task_ids:
        batch_tasks = {_normalize_task_id(task_id) for task_id in batch.task_ids}
        missing = [task_id for task_id in policy.allowed_task_ids if _normalize_task_id(task_id) not in batch_tasks]
        if missing:
            blockers.append(f"Allowed tasks missing from batch {policy.batch_id}: {', '.join(missing)}.")
    if policy.queue_id:
        queue = load_execution_queue(project_name, policy.queue_id, workspace_root=root)
        if not queue:
            blockers.append(f"Referenced queue not found: {policy.queue_id}.")
        elif policy.allowed_queue_item_ids:
            queue_items = {_normalize_queue_item_id(item.item_id) for item in queue.items}
            missing_items = [item_id for item_id in policy.allowed_queue_item_ids if _normalize_queue_item_id(item_id) not in queue_items]
            if missing_items:
                blockers.append(f"Allowed queue items missing from queue {policy.queue_id}: {', '.join(missing_items)}.")
    if not policy.allowed_task_ids and not policy.allowed_queue_item_ids:
        blockers.append("Policy has no allowed tasks or queue items.")
    for label, value in [
        ("max_tasks", policy.max_tasks),
        ("max_tasks_per_run", policy.max_tasks_per_run),
        ("max_changed_files_per_task", policy.max_changed_files_per_task),
        ("max_total_changed_files", policy.max_total_changed_files),
    ]:
        if value < 1:
            blockers.append(f"{label} must be positive.")
    if policy.auto_push_allowed and not policy.auto_delivery_allowed:
        blockers.append("auto_push_allowed requires auto_delivery_allowed.")
    if not policy.validation_commands:
        warnings.append("No validation commands recorded; future autonomous execution should pause for explicit validation guidance.")
    if not policy.forbidden_file_patterns:
        warnings.append("No forbidden file patterns recorded.")
    usable = not blockers
    next_action = "TASK-DEVO-129 autonomous queue worker loop can use this approved policy." if usable else "Resolve blockers before autonomous execution."
    return ExecutionPolicyCheckResult(
        project=project_name,
        policy_id=policy.policy_id,
        usable=usable,
        status=policy.status,
        blockers=blockers,
        warnings=warnings,
        next_action=next_action,
    )


def plan_queue_worker_run(project_name: str, policy_id: str, workspace_root: Path | None = None) -> QueueWorkerPlan:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    normalized_policy_id = _normalize_policy_id(policy_id)
    policy = load_execution_policy(project_name, normalized_policy_id, workspace_root=root)
    if not policy:
        return QueueWorkerPlan(
            project=project_name,
            policy_id=normalized_policy_id,
            status="no_policy",
            blockers=[f"Execution policy not found: {policy_id}"],
            policy_check_summary="Policy missing.",
            next_action=f"List policies: devo project execution-policy-list --project {project_name}",
        )
    policy_check = check_execution_policy(project_name, policy.policy_id, workspace_root=root)
    blockers = list(policy_check.blockers)
    warnings = list(policy_check.warnings)
    policy_summary = f"usable={policy_check.usable}; status={policy_check.status}; blockers={len(policy_check.blockers)}; warnings={len(policy_check.warnings)}"
    if not policy.queue_id:
        blockers.append("Queue worker v1 requires policy.queue_id.")
    if not policy.validation_commands:
        blockers.append("Queue worker v1 requires validation_commands in the approved policy.")
    batch = load_project_batch(project_name, policy.batch_id, workspace_root=root)
    queue = load_execution_queue(project_name, policy.queue_id, workspace_root=root) if policy.queue_id else None
    if policy.queue_id and not queue and not any("Referenced queue not found" in blocker for blocker in blockers):
        blockers.append(f"Referenced queue not found: {policy.queue_id}.")
    if not batch and not any("Referenced batch not found" in blocker for blocker in blockers):
        blockers.append(f"Referenced batch not found: {policy.batch_id}.")
    if blockers:
        return QueueWorkerPlan(
            project=project_name,
            policy_id=policy.policy_id,
            usable=False,
            status="blocked",
            batch_id=policy.batch_id,
            queue_id=policy.queue_id,
            blockers=blockers,
            warnings=warnings,
            policy_check_summary=policy_summary,
            next_action="Resolve policy blockers before queue-worker-run.",
        )
    assert queue is not None
    eligible, skipped = _select_policy_queue_items(project_name, policy, queue, workspace_root=root)
    if not eligible:
        return QueueWorkerPlan(
            project=project_name,
            policy_id=policy.policy_id,
            usable=False,
            status="no_ready_item",
            batch_id=policy.batch_id,
            queue_id=queue.queue_id,
            skipped_queue_item_summaries=skipped,
            blockers=["No pending or running queue item matched the approved policy bounds."],
            warnings=warnings,
            policy_check_summary=policy_summary,
            selection_reason="No pending or running queue item matched the approved policy bounds.",
            next_action="Review queue state and policy scope before retrying.",
        )
    selected = eligible[0]
    existing_worker = _latest_worker_run_for_queue_item(project_name, queue.queue_id, selected.item_id, workspace_root=root)
    review = load_codex_worker_review(project_name, existing_worker.worker_run_id, workspace_root=root) if existing_worker else None
    worker_blockers = _queue_worker_existing_worker_blockers(existing_worker, review)
    if worker_blockers:
        return QueueWorkerPlan(
            project=project_name,
            policy_id=policy.policy_id,
            usable=False,
            status="blocked",
            batch_id=policy.batch_id,
            queue_id=queue.queue_id,
            selected_queue_item_id=selected.item_id,
            selected_task_id=selected.task_id,
            eligible_queue_item_ids=[item.item_id for item in eligible],
            skipped_queue_item_summaries=skipped,
            blockers=worker_blockers,
            warnings=warnings,
            policy_check_summary=policy_summary,
            selection_reason=f"Selected {selected.item_id} but existing worker/review state needs attention.",
            next_action="Review the existing worker output before creating another queue-worker run.",
        )
    return QueueWorkerPlan(
        project=project_name,
        policy_id=policy.policy_id,
        usable=True,
        status="handoff_ready" if existing_worker else "waiting_worker",
        batch_id=policy.batch_id,
        queue_id=queue.queue_id,
        selected_queue_item_id=selected.item_id,
        selected_task_id=selected.task_id,
        eligible_queue_item_ids=[item.item_id for item in eligible],
        skipped_queue_item_summaries=skipped,
        warnings=warnings,
        policy_check_summary=policy_summary,
        selection_reason=f"Selected first eligible queue item {selected.item_id} for task {selected.task_id}.",
        next_action=f"Run once: devo project queue-worker-run --project {project_name} --policy {policy.policy_id} --once --confirm-queue-worker",
    )


def run_queue_worker_once(project_name: str, policy_id: str, *, approver: str | None = None, workspace_root: Path | None = None) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    plan = plan_queue_worker_run(project_name, policy_id, workspace_root=root)
    now = datetime.now(UTC)
    run = QueueWorkerRun(
        project=project_name,
        run_id=_next_queue_worker_run_id(project_name, workspace_root=root),
        policy_id=plan.policy_id,
        batch_id=plan.batch_id,
        queue_id=plan.queue_id,
        selected_queue_item_id=plan.selected_queue_item_id,
        selected_task_id=plan.selected_task_id,
        status=plan.status,
        started_at=now,
        updated_at=now,
        approver=approver.strip() if approver and approver.strip() else None,
        steps_run=["loaded execution policy", "checked policy", "selected eligible queue item"],
        blockers=list(plan.blockers),
        warnings=list(plan.warnings),
        skipped_queue_item_summaries=list(plan.skipped_queue_item_summaries),
        policy_check_summary=plan.policy_check_summary,
        selection_reason=plan.selection_reason,
        pause_reason="blocked" if plan.blockers else plan.status,
        next_action=plan.next_action,
    )
    if not plan.usable:
        return _write_queue_worker_run(project_name, run, workspace_root=root)
    assert plan.queue_id is not None
    assert plan.selected_queue_item_id is not None
    handoff = _create_or_reuse_handoff_for_queue_item(project_name, plan.queue_id, plan.selected_queue_item_id, workspace_root=root)
    worker_run = _latest_worker_run_for_queue_item(project_name, plan.queue_id, plan.selected_queue_item_id, workspace_root=root)
    steps = [*run.steps_run, f"handoff ready: {handoff.handoff_id}"]
    if not worker_run:
        worker_run, _worker_json, _worker_md = create_codex_worker_run_from_handoff(project_name, handoff.handoff_id, workspace_root=root)
        steps.append(f"created assisted/manual Codex worker run: {worker_run.worker_run_id}")
    else:
        steps.append(f"reused existing Codex worker run: {worker_run.worker_run_id}")
    updated = run.model_copy(
        update={
            "status": "waiting_worker",
            "selected_handoff_id": handoff.handoff_id,
            "selected_worker_run_id": worker_run.worker_run_id,
            "steps_run": steps,
            "pause_reason": "waiting_worker",
            "next_action": f"Use devo worker codex run-show --project {project_name} --run {worker_run.worker_run_id}, then give the generated handoff to Codex and import/review the result before queue completion.",
        }
    )
    return _write_queue_worker_run(project_name, updated, workspace_root=root)


def get_queue_worker_status_report(project_name: str, workspace_root: Path | None = None) -> QueueWorkerStatusReport:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    runs = list_queue_worker_runs(project_name, workspace_root=root)
    if not runs:
        return QueueWorkerStatusReport(
            project=project_name,
            next_action=f"Plan a queue worker run: devo project queue-worker-plan --project {project_name} --policy <POL-ID>",
        )
    run = runs[0]
    evidence = summarize_queue_worker_evidence(project_name, run, workspace_root=root)
    blockers = [*run.blockers, *evidence.blockers]
    warnings = [*run.warnings, *evidence.warnings]
    return QueueWorkerStatusReport(
        project=project_name,
        has_runs=True,
        run_id=run.run_id,
        policy_id=run.policy_id,
        queue_id=run.queue_id,
        selected_queue_item_id=run.selected_queue_item_id,
        selected_task_id=run.selected_task_id,
        selected_handoff_id=run.selected_handoff_id,
        selected_worker_run_id=run.selected_worker_run_id,
        status=run.status,
        pause_reason=run.pause_reason,
        failure_reason=run.failure_reason,
        retry_of=run.retry_of,
        blockers=blockers,
        warnings=warnings,
        missing_evidence=evidence.missing_evidence,
        evidence=evidence,
        next_action=_queue_worker_next_action_for_status(project_name, run, run.status, evidence, blockers),
    )


def summarize_queue_worker_evidence(
    project_name: str,
    run: QueueWorkerRun,
    workspace_root: Path | None = None,
) -> QueueWorkerEvidenceSummary:
    root = workspace_root or get_workspace_root()
    missing: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []

    handoff = load_codex_handoff(project_name, run.selected_handoff_id, workspace_root=root) if run.selected_handoff_id else None
    worker_run = load_codex_worker_run(project_name, run.selected_worker_run_id, workspace_root=root) if run.selected_worker_run_id else None
    report = load_codex_worker_report(project_name, run.selected_worker_run_id, workspace_root=root) if run.selected_worker_run_id else None
    review = load_codex_worker_review(project_name, run.selected_worker_run_id, workspace_root=root) if run.selected_worker_run_id else None

    handoff_exists = handoff is not None
    worker_run_exists = worker_run is not None
    worker_report_imported = report is not None
    worker_review_exists = review is not None
    worker_review_passed = bool(review and review.review_status == "reviewed_passed")
    validation_status = review.validation_evidence.validation_status if review else "not_provided"
    validation_evidence_exists = validation_status != "not_provided"
    validation_passed = validation_status == "passed"
    delivery_request_exists = run.status in {"delivery_requested", "completed"}
    delivery_completed = run.status == "completed"

    if not run.selected_handoff_id:
        missing.append("Handoff not recorded.")
    elif not handoff_exists:
        blockers.append(f"Linked handoff is missing: {run.selected_handoff_id}.")
    if not run.selected_worker_run_id:
        missing.append("Worker run not recorded.")
    elif not worker_run_exists:
        blockers.append(f"Linked worker run is missing: {run.selected_worker_run_id}.")
    if worker_run_exists and not worker_report_imported:
        missing.append("Worker result/report not imported.")
    if report and report.status_reported_by_worker in {"usage_limit", "blocked", "failed", "needs_approval"}:
        blockers.append(f"Worker report says {report.status_reported_by_worker}.")
    if worker_report_imported and not worker_review_exists:
        missing.append("Worker review not recorded.")
    if review and review.review_status in {"reviewed_needs_changes", "rejected"}:
        blockers.append(f"Worker review status is {review.review_status}.")
    if review and not validation_evidence_exists:
        missing.append("Validation evidence not recorded.")
    if review and validation_status == "failed":
        blockers.append("Validation evidence failed.")
    elif review and validation_evidence_exists and not validation_passed:
        warnings.append(f"Validation evidence status is {validation_status}.")
    if not delivery_request_exists:
        missing.append("Delivery request not created.")
    elif not delivery_completed:
        missing.append("Delivery not completed.")

    return QueueWorkerEvidenceSummary(
        handoff_exists=handoff_exists,
        worker_run_exists=worker_run_exists,
        worker_report_imported=worker_report_imported,
        worker_review_exists=worker_review_exists,
        worker_review_passed=worker_review_passed,
        validation_evidence_exists=validation_evidence_exists,
        validation_passed=validation_passed,
        delivery_request_exists=delivery_request_exists,
        delivery_completed=delivery_completed,
        missing_evidence=missing,
        blockers=blockers,
        warnings=warnings,
    )


def pause_queue_worker_run(
    project_name: str,
    run_id: str,
    reason: str,
    workspace_root: Path | None = None,
) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    run = _require_queue_worker_run(project_name, run_id, root)
    if run.status in {"completed", "cancelled"}:
        msg = f"Cannot pause queue worker run in terminal status {run.status}."
        raise ValueError(msg)
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        msg = "Pause reason is required."
        raise ValueError(msg)
    now = datetime.now(UTC)
    updated = run.model_copy(
        update={
            "status": "paused",
            "pause_reason": cleaned_reason,
            "paused_at": now,
            "updated_at": now,
            "steps_run": [*run.steps_run, f"paused: {cleaned_reason}"],
            "next_action": f"Resume when safe: devo project queue-worker-resume --project {project_name} --run {run.run_id} --confirm-resume",
        }
    )
    return _write_queue_worker_run(project_name, updated, workspace_root=root)


def resume_queue_worker_run(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    run = _require_queue_worker_run(project_name, run_id, root)
    if run.status not in {"paused", "waiting_worker", "handoff_ready", "waiting_review", "waiting_validation"}:
        msg = f"Queue worker run status is not resumable: {run.status}"
        raise ValueError(msg)
    policy_blockers, policy_warnings, policy_summary = _queue_worker_recheck_selected_run(project_name, run, root)
    now = datetime.now(UTC)
    evidence = summarize_queue_worker_evidence(project_name, run, workspace_root=root)
    blockers = [*policy_blockers, *evidence.blockers]
    warnings = [*policy_warnings, *evidence.warnings]
    status = "blocked" if blockers else _queue_worker_status_from_evidence(run, evidence)
    updated = run.model_copy(
        update={
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "policy_check_summary": policy_summary or run.policy_check_summary,
            "resumed_at": now,
            "updated_at": now,
            "steps_run": [*run.steps_run, "resume requested; policy and selected queue item rechecked"],
            "next_action": _queue_worker_next_action_for_status(project_name, run, status, evidence, blockers),
        }
    )
    return _write_queue_worker_run(project_name, updated, workspace_root=root)


def fail_queue_worker_run(
    project_name: str,
    run_id: str,
    reason: str,
    workspace_root: Path | None = None,
) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    run = _require_queue_worker_run(project_name, run_id, root)
    if run.status in {"completed", "cancelled"}:
        msg = f"Cannot fail queue worker run in terminal status {run.status}."
        raise ValueError(msg)
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        msg = "Failure reason is required."
        raise ValueError(msg)
    now = datetime.now(UTC)
    updated = run.model_copy(
        update={
            "status": "failed",
            "failure_reason": cleaned_reason,
            "failed_at": now,
            "updated_at": now,
            "steps_run": [*run.steps_run, f"failed: {cleaned_reason}"],
            "next_action": f"Inspect evidence, then retry only if safe: devo project queue-worker-retry --project {project_name} --run {run.run_id} --confirm-retry",
        }
    )
    return _write_queue_worker_run(project_name, updated, workspace_root=root)


def retry_queue_worker_run(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    previous = _require_queue_worker_run(project_name, run_id, root)
    if previous.status in {"completed", "cancelled"}:
        msg = f"Cannot retry queue worker run in terminal status {previous.status}."
        raise ValueError(msg)
    policy_blockers, policy_warnings, policy_summary = _queue_worker_recheck_selected_run(project_name, previous, root)
    if policy_blockers:
        msg = "; ".join(policy_blockers)
        raise ValueError(msg)
    now = datetime.now(UTC)
    handoff = load_codex_handoff(project_name, previous.selected_handoff_id, workspace_root=root) if previous.selected_handoff_id else None
    status = "waiting_worker" if handoff else "handoff_ready"
    next_action = (
        f"Create a fresh worker run from the handoff: devo worker codex run-create --project {project_name} --handoff {handoff.handoff_id}"
        if handoff
        else f"Create a fresh queue handoff: devo project handoff-next --project {project_name} --queue {previous.queue_id or '<queueId>'}"
    )
    retry = QueueWorkerRun(
        project=project_name,
        run_id=_next_queue_worker_run_id(project_name, workspace_root=root),
        policy_id=previous.policy_id,
        batch_id=previous.batch_id,
        queue_id=previous.queue_id,
        selected_queue_item_id=previous.selected_queue_item_id,
        selected_task_id=previous.selected_task_id,
        selected_handoff_id=handoff.handoff_id if handoff else None,
        selected_worker_run_id=None,
        status=status,
        started_at=now,
        updated_at=now,
        approver=previous.approver,
        retry_of=previous.run_id,
        steps_run=[f"retry of queue worker run {previous.run_id}", "policy and selected queue item rechecked"],
        warnings=policy_warnings,
        policy_check_summary=policy_summary or previous.policy_check_summary,
        selection_reason=previous.selection_reason,
        pause_reason=status,
        next_action=next_action,
    )
    return _write_queue_worker_run(project_name, retry, workspace_root=root)


def cancel_queue_worker_run(
    project_name: str,
    run_id: str,
    reason: str,
    workspace_root: Path | None = None,
) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    run = _require_queue_worker_run(project_name, run_id, root)
    if run.status in {"completed", "cancelled"}:
        msg = f"Cannot cancel queue worker run in terminal status {run.status}."
        raise ValueError(msg)
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        msg = "Cancel reason is required."
        raise ValueError(msg)
    now = datetime.now(UTC)
    updated = run.model_copy(
        update={
            "status": "cancelled",
            "cancel_reason": cleaned_reason,
            "cancelled_at": now,
            "updated_at": now,
            "steps_run": [*run.steps_run, f"cancelled: {cleaned_reason}"],
            "next_action": "No action needed for this cancelled queue-worker run.",
        }
    )
    return _write_queue_worker_run(project_name, updated, workspace_root=root)


def request_batch_approval(
    project_name: str,
    batch_id: str,
    note: str = "",
    reviewer: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    review_notes = list(existing.review_notes if existing else [])
    cleaned = note.strip()
    if cleaned:
        review_notes.append(f"{now.isoformat()}: request: {cleaned}")
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="requested",
        review_status=existing.review_status if existing else "not_reviewed",
        review_notes=review_notes,
        requested_at=now,
        reviewer=reviewer or (existing.reviewer if existing else None),
        now=now,
    )
    updated_batch = batch.model_copy(update={"approval_status": "requested", "updated_at": now})
    _write_project_batch(project_name, updated_batch, workspace_root=root)
    return _write_batch_approval(project_name, approval, workspace_root=root)


def approve_project_batch(
    project_name: str,
    batch_id: str,
    note: str = "",
    approver: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval, Path, Path, bool]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    direct_approval = existing is None or existing.approval_status != "requested"
    review_notes = list(existing.review_notes if existing else [])
    cleaned = note.strip()
    if cleaned:
        review_notes.append(f"{now.isoformat()}: approval: {cleaned}")
    review_status = existing.review_status if existing else batch.review_status
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="approved",
        review_status=review_status if review_status != "not_reviewed" else "reviewed",
        review_notes=review_notes,
        approved_at=now,
        approver=approver or (existing.approver if existing else None),
        decision_note=cleaned or (existing.decision_note if existing else ""),
        now=now,
    )
    updated = batch.model_copy(update={"status": "approved", "approval_status": "approved", "review_status": approval.review_status, "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md, direct_approval


def reject_project_batch(
    project_name: str,
    batch_id: str,
    note: str,
    approver: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    cleaned = note.strip()
    if not cleaned:
        msg = "Decision note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    review_notes = list(existing.review_notes if existing else [])
    review_notes.append(f"{now.isoformat()}: rejection: {cleaned}")
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="rejected",
        review_status="needs_changes",
        review_notes=review_notes,
        rejected_at=now,
        approver=approver or (existing.approver if existing else None),
        decision_note=cleaned,
        now=now,
    )
    updated = batch.model_copy(update={"approval_status": "rejected", "review_status": "needs_changes", "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md


def review_project_batch(
    project_name: str,
    batch_id: str,
    note: str,
    needs_changes: bool = False,
    reviewer: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval | None, Path | None, Path | None]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    cleaned = note.strip()
    if not cleaned:
        msg = "Review note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = [*batch.review_notes, f"{now.isoformat()}: {cleaned}"]
    review_status = "needs_changes" if needs_changes else "reviewed"
    status = "reviewed" if batch.status == "draft" and not needs_changes else batch.status
    updated = batch.model_copy(update={"status": status, "review_status": review_status, "review_notes": notes, "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    if not existing:
        return updated, json_path, markdown_path, None, None, None
    approval = _build_batch_approval(
        updated,
        existing=existing,
        approval_status=existing.approval_status,
        review_status=review_status,
        review_notes=notes,
        reviewed_at=now,
        reviewer=reviewer or existing.reviewer,
        now=now,
    )
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md


def project_batch_artifact_paths(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_batch_id(batch_id)
    return paths.batches_dir / f"batch-{safe_id}.json", paths.batches_dir / f"batch-{safe_id}.md"


def calculate_project_progress(project_name: str, workspace_root: Path | None = None) -> ProjectProgress:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    batches = list_project_batches(project_name, workspace_root=root)
    tasks = backlog.tasks if backlog else []
    active_tasks = [task for task in tasks if task.status != "superseded"]
    active_task_count = len(active_tasks)
    completed_task_count = sum(1 for task in active_tasks if task.status == "completed")
    blocked_task_count = sum(1 for task in active_tasks if task.status == "blocked")
    approved_task_count = sum(1 for task in active_tasks if task.status == "approved")
    ready_task_count = sum(1 for task in active_tasks if task.status == "ready")
    draft_task_count = sum(1 for task in active_tasks if task.status == "draft")
    ready_like_count = sum(1 for task in active_tasks if task.status in {"ready", "approved", "completed"})
    active_batches = [batch for batch in batches if batch.status != "superseded"]
    latest_batch = batches[0] if batches else None
    warnings = _progress_warnings(brief, blueprint, backlog, active_tasks, batches)
    return ProjectProgress(
        project=project_name,
        has_brief=brief is not None,
        brief_status=brief.status if brief else "missing",
        has_blueprint=blueprint is not None,
        blueprint_status=blueprint.status if blueprint else "missing",
        has_backlog=backlog is not None,
        backlog_status=backlog.status if backlog else "missing",
        task_count=len(tasks),
        completed_task_count=completed_task_count,
        active_task_count=active_task_count,
        blocked_task_count=blocked_task_count,
        approved_task_count=approved_task_count,
        ready_task_count=ready_task_count,
        draft_task_count=draft_task_count,
        project_completion_percent=_percent(completed_task_count, active_task_count),
        backlog_readiness_percent=_percent(ready_like_count, active_task_count),
        blocked_percent=_percent(blocked_task_count, active_task_count),
        batch_count=len(batches),
        approved_batch_count=sum(1 for batch in active_batches if batch.approval_status == "approved"),
        completed_batch_count=sum(1 for batch in active_batches if batch.status == "completed"),
        active_batch_count=len(active_batches),
        batch_completion_percent=_percent(sum(1 for batch in active_batches if batch.status == "completed"), len(active_batches)),
        latest_batch_id=latest_batch.batch_id if latest_batch else None,
        latest_batch_status=latest_batch.status if latest_batch else None,
        milestone_progress=_aggregate_progress_groups(active_tasks, blueprint.milestones if blueprint else [], "milestone_id"),
        epic_progress=_aggregate_progress_groups(active_tasks, blueprint.epics if blueprint else [], "epic_id"),
        next_action=_progress_next_action(project_name, brief, blueprint, backlog, batches),
        warnings=warnings,
        generated_at=datetime.now(UTC),
    )


def build_project_intake_status(project_name: str, workspace_root: Path | None = None) -> ProjectIntakeStatus:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    brief = load_project_brief(project_name, workspace_root=root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    batches = list_project_batches(project_name, workspace_root=root)
    queues = list_execution_queues(project_name, workspace_root=root)
    handoffs = list_codex_handoffs(project_name, workspace_root=root)
    progress = calculate_project_progress(project_name, workspace_root=root)
    latest_batch = batches[0] if batches else None
    latest_batch_approval = load_batch_approval(project_name, latest_batch.batch_id, workspace_root=root) if latest_batch else None
    latest_queue = queues[0] if queues else None
    latest_handoff = handoffs[0] if handoffs else None
    next_action, next_command, helper_commands = _intake_next_step(
        project_name,
        brief,
        blueprint,
        backlog,
        latest_batch,
        latest_batch_approval,
        latest_queue,
        latest_handoff,
    )
    return ProjectIntakeStatus(
        project=project_name,
        target_repo_path=str(registration.path),
        brief_status=brief.status if brief else "missing",
        blueprint_status=blueprint.status if blueprint else "missing",
        backlog_status=backlog.status if backlog else "missing",
        task_count=backlog.task_count if backlog else 0,
        ready_task_count=backlog.ready_task_count if backlog else 0,
        blocked_task_count=backlog.blocked_task_count if backlog else 0,
        batch_count=len(batches),
        latest_batch_id=latest_batch.batch_id if latest_batch else None,
        latest_batch_status=latest_batch.status if latest_batch else None,
        latest_batch_approval_status=(
            latest_batch_approval.approval_status if latest_batch_approval else latest_batch.approval_status if latest_batch else None
        ),
        queue_count=len(queues),
        latest_queue_id=latest_queue.queue_id if latest_queue else None,
        latest_queue_status=latest_queue.status if latest_queue else None,
        handoff_count=len(handoffs),
        latest_handoff_id=latest_handoff.handoff_id if latest_handoff else None,
        latest_handoff_status=latest_handoff.status if latest_handoff else None,
        project_completion_percent=progress.project_completion_percent,
        backlog_readiness_percent=progress.backlog_readiness_percent,
        blocked_percent=progress.blocked_percent,
        next_action=next_action,
        next_command=next_command,
        helper_commands=helper_commands,
        generated_at=datetime.now(UTC),
    )


def render_intake_template(project_name: str) -> str:
    return "\n".join(
        [
            f"# Intake Template: {project_name}",
            "",
            "Use this local-first template before creating a Project Brief.",
            "",
            "## Title",
            "",
            "<short feature or product title>",
            "",
            "## Problem / Goal",
            "",
            "<what problem are we solving, or what outcome should exist?>",
            "",
            "## Why Now",
            "",
            "<why this matters now>",
            "",
            "## Target Users",
            "",
            "- <user or operator>",
            "",
            "## Must-Have Outcomes",
            "",
            "- <observable outcome>",
            "",
            "## Non-Goals",
            "",
            "- <what should stay out of scope>",
            "",
            "## Constraints",
            "",
            "- <safety, platform, time, local-only, or workflow constraints>",
            "",
            "## Risks",
            "",
            "- <known risk or uncertainty>",
            "",
            "## Known Files / Areas",
            "",
            "- <docs, source areas, modules, or commands likely involved>",
            "",
            "## Validation Expectations",
            "",
            "- <checks or tests expected later>",
            "",
            "## Delivery Expectations",
            "",
            "- <commit/push, runner, or review expectations>",
            "",
            "## Notes For Codex",
            "",
            "- <implementation or inspection notes>",
            "",
        ]
    )


def write_intake_template(project_name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    path = paths.planning_dir / INTAKE_TEMPLATE_MD
    path.write_text(render_intake_template(project_name), encoding="utf-8")
    return path


def render_intake_prompt(project_name: str, idea: str | None = None, workspace_root: Path | None = None) -> str:
    status = build_project_intake_status(project_name, workspace_root=workspace_root)
    idea_text = idea.strip() if idea and idea.strip() else "<paste rough idea here>"
    return "\n".join(
        [
            f"# Intake Refinement Prompt: {project_name}",
            "",
            "You are helping refine a rough project idea into Devo planning artifacts.",
            "Devo is local-first and Phase 1 is not autonomous: do not claim Devo will call AI APIs, run Codex by itself, approve work, modify target repositories, validate, commit, or push.",
            "",
            "## Rough Idea",
            "",
            idea_text,
            "",
            "## Current Devo Planning State",
            "",
            f"- Brief: {status.brief_status}",
            f"- Blueprint: {status.blueprint_status}",
            f"- Backlog: {status.backlog_status}",
            f"- Tasks: {status.task_count} ready={status.ready_task_count} blocked={status.blocked_task_count}",
            f"- Batches: {status.batch_count} latest={status.latest_batch_id or 'none'} approval={status.latest_batch_approval_status or 'none'}",
            f"- Queues: {status.queue_count} latest={status.latest_queue_id or 'none'} status={status.latest_queue_status or 'none'}",
            f"- Handoffs: {status.handoff_count} latest={status.latest_handoff_id or 'none'}",
            "",
            "## Produce",
            "",
            "- Project brief draft",
            "- Blueprint outline",
            "- Candidate milestones",
            "- Candidate backlog/tasks",
            "- Batch suggestion",
            "- Risks and non-goals",
            "- Validation expectations",
            "",
            "## Output Guidance",
            "",
            "- Keep the plan small enough for approved Devo batches.",
            "- Identify assumptions and open questions.",
            "- Separate must-haves from nice-to-haves.",
            "- Mention files or areas only when supported by known context.",
            "- Do not include secrets or local setting values.",
            "- End with the next Devo command the operator should run.",
            "",
            "## Current Suggested Next Devo Action",
            "",
            f"- Next action: {status.next_action}",
            f"- Command: {status.next_command}",
            "",
        ]
    )


def write_intake_prompt(project_name: str, idea: str | None = None, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    path = paths.planning_dir / INTAKE_PROMPT_MD
    path.write_text(render_intake_prompt(project_name, idea=idea, workspace_root=root), encoding="utf-8")
    return path


def render_project_progress_markdown(progress: ProjectProgress) -> str:
    lines = [
        f"# Project Progress: {progress.project}",
        "",
        f"- Generated: `{progress.generated_at.isoformat()}`",
        f"- Brief: `{progress.brief_status}`",
        f"- Blueprint: `{progress.blueprint_status}`",
        f"- Backlog: `{progress.backlog_status}`",
        f"- Tasks: `{progress.task_count}`",
        f"- Active tasks: `{progress.active_task_count}`",
        f"- Completed tasks: `{progress.completed_task_count}`",
        f"- Blocked tasks: `{progress.blocked_task_count}`",
        f"- Project completion: `{progress.project_completion_percent:.1f}%`",
        f"- Backlog readiness: `{progress.backlog_readiness_percent:.1f}%`",
        f"- Blocked: `{progress.blocked_percent:.1f}%`",
        f"- Batches: `{progress.batch_count}`",
        f"- Approved batches: `{progress.approved_batch_count}`",
        f"- Completed batches: `{progress.completed_batch_count}`",
        f"- Batch completion: `{progress.batch_completion_percent:.1f}%`",
        f"- Latest batch: `{progress.latest_batch_id or 'none'}`",
        f"- Latest batch status: `{progress.latest_batch_status or 'none'}`",
        "",
        "## Next Action",
        "",
        progress.next_action,
        "",
    ]
    _append_list_section(lines, "Warnings", progress.warnings)
    lines.extend(["## Milestone Progress", ""])
    _append_progress_groups(lines, progress.milestone_progress)
    lines.extend(["## Epic Progress", ""])
    _append_progress_groups(lines, progress.epic_progress)
    return "\n".join(lines).rstrip() + "\n"


def create_execution_queue_from_batch(
    project_name: str,
    batch_id: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    if batch.approval_status != "approved" or batch.status not in {"approved", "in_progress", "completed"}:
        msg = f"Project batch must be approved before queue creation: {batch.batch_id}"
        raise ValueError(msg)
    queue_id = _next_queue_id(project_name, workspace_root=root)
    now = datetime.now(UTC)
    items = [
        QueueItem(
            item_id=f"QI{index:03d}",
            task_id=task.task_id,
            title=task.title,
            lane=task.lane,
            risk_level=task.risk_level,
            status="pending",
            batch_id=batch.batch_id,
            dependencies=task.dependencies,
            acceptance_criteria=[task.acceptance_criteria_summary] if task.acceptance_criteria_summary else [],
            validation_expectations=[task.validation_expectations_summary] if task.validation_expectations_summary else [],
        )
        for index, task in enumerate(batch.task_snapshots, start=1)
    ]
    queue = _with_queue_counts(
        ExecutionQueue(
            project=project_name,
            queue_id=queue_id,
            title=f"Execution queue for {batch.title}",
            source_batch_id=batch.batch_id,
            source_backlog_reference=batch.source_backlog_reference,
            status="ready",
            items=items,
            pause_reason=None,
            resume_hint="Start the queue when ready, then generate a Codex handoff prompt with devo project handoff-next.",
            current_item_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    return _write_execution_queue(project_name, queue, workspace_root=root)


def list_execution_queues(project_name: str, workspace_root: Path | None = None) -> list[ExecutionQueue]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.queues_dir.exists():
        return []
    queues: list[ExecutionQueue] = []
    for path in sorted(paths.queues_dir.glob("queue-*.json")):
        if path.name == QUEUE_INDEX_JSON:
            continue
        try:
            queues.append(ExecutionQueue.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(queues, key=lambda queue: queue.updated_at, reverse=True)


def load_queue_index(project_name: str, workspace_root: Path | None = None) -> QueueIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.queue_index_json.exists():
        return QueueIndex(project=project_name)
    return QueueIndex.model_validate_json(paths.queue_index_json.read_text(encoding="utf-8"))


def load_handoff_index(project_name: str, workspace_root: Path | None = None) -> HandoffIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.handoff_index_json.exists():
        return HandoffIndex(project=project_name)
    return HandoffIndex.model_validate_json(paths.handoff_index_json.read_text(encoding="utf-8"))


def load_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> ExecutionQueue | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = queue_artifact_paths(project_name, queue_id, workspace_root=root)
    if not json_path.exists():
        return None
    return ExecutionQueue.model_validate_json(json_path.read_text(encoding="utf-8"))


def load_codex_handoff(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> CodexHandoff | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _prompt_path = handoff_artifact_paths(project_name, handoff_id, workspace_root=root)
    if not json_path.exists():
        return None
    return CodexHandoff.model_validate_json(json_path.read_text(encoding="utf-8"))


def start_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    if queue.status not in {"draft", "ready", *PAUSED_QUEUE_STATUSES}:
        msg = f"Queue cannot be started from status: {queue.status}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [item.model_copy() for item in queue.items]
    current_item_id = queue.current_item_id if _find_queue_item(items, queue.current_item_id) else None
    running_item = next((item for item in items if item.status == "running"), None)
    if running_item:
        current_item_id = running_item.item_id
    elif current_item_id:
        current = _find_queue_item(items, current_item_id)
        if current and current.status in {"pending", "paused", "blocked"}:
            replacement = current.model_copy(update={"status": "running", "started_at": current.started_at or now})
            _replace_queue_item(items, replacement)
            current_item_id = replacement.item_id
    elif not current_item_id:
        next_item = next((item for item in items if item.status == "pending"), None)
        if next_item:
            replacement = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, replacement)
            current_item_id = replacement.item_id
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": "running" if current_item_id else "completed",
                "items": items,
                "pause_reason": None,
                "resume_hint": "Queue is running. Generate a Codex handoff prompt with devo project handoff-next.",
                "current_item_id": current_item_id,
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def get_queue_next_item(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, QueueItem | None]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    current = _find_queue_item(queue.items, queue.current_item_id)
    if current and current.status in {"running", "waiting_review", "paused", "blocked", "failed"}:
        return queue, current
    pending = next((item for item in queue.items if item.status == "pending"), None)
    return queue, pending


def complete_queue_item(
    project_name: str,
    queue_id: str,
    item_id: str,
    note: str,
    confirm_without_review: bool = False,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    now = datetime.now(UTC)
    item = _require_queue_item(queue, item_id)
    readiness = get_queue_item_completion_readiness(project_name, queue.queue_id, item.item_id, workspace_root=root)
    if not readiness.completion_ready and not confirm_without_review:
        msg = _queue_completion_blocked_message(project_name, readiness)
        raise ValueError(msg)
    if confirm_without_review and not note.strip():
        msg = "--confirm-without-review requires a non-empty --note explaining the manual override."
        raise ValueError(msg)
    notes = _append_note(item.notes, note, now)
    if confirm_without_review and not readiness.completion_ready:
        notes = _append_note(
            notes,
            "WARNING: queue item completed with --confirm-without-review before reviewed_passed worker review evidence was available.",
            now,
        )
    completed = item.model_copy(update={"status": "completed", "completed_at": now, "notes": notes})
    items = [entry.model_copy() for entry in queue.items]
    _replace_queue_item(items, completed)
    current_item_id: str | None = None
    status = queue.status
    if status == "running":
        next_item = next((entry for entry in items if entry.status == "pending"), None)
        if next_item:
            running = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, running)
            current_item_id = running.item_id
        else:
            status = "completed"
    elif all(entry.status in {"completed", "skipped", "superseded"} for entry in items):
        status = "completed"
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "current_item_id": current_item_id,
                "pause_reason": None if status == "completed" else queue.pause_reason,
                "resume_hint": "Queue completed." if status == "completed" else queue.resume_hint,
                "updated_at": now,
            }
        )
    )
    _update_backlog_task_status(project_name, item.task_id, "completed", workspace_root=root)
    return _write_execution_queue(project_name, updated, workspace_root=root)


def block_queue_item(
    project_name: str,
    queue_id: str,
    item_id: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    now = datetime.now(UTC)
    item = _require_queue_item(queue, item_id)
    notes = _append_note(item.notes, note, now)
    blocked = item.model_copy(update={"status": "blocked", "notes": notes})
    items = [entry.model_copy() for entry in queue.items]
    _replace_queue_item(items, blocked)
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": "waiting_review",
                "items": items,
                "pause_reason": "blocked_item",
                "resume_hint": f"Review blocked item {blocked.item_id}; generate a new handoff only after the blocker is resolved.",
                "current_item_id": blocked.item_id,
                "updated_at": now,
            }
        )
    )
    _update_backlog_task_status(project_name, item.task_id, "blocked", workspace_root=root)
    return _write_execution_queue(project_name, updated, workspace_root=root)


def pause_execution_queue(
    project_name: str,
    queue_id: str,
    reason: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    normalized_reason = reason.strip().lower()
    if normalized_reason == "usage_limit":
        status = "paused_usage_limit"
    elif normalized_reason == "failure":
        status = "paused_failure"
    elif normalized_reason in {"review", "manual"}:
        status = "waiting_review"
    else:
        msg = "Pause reason must be one of: usage_limit, failure, review, manual."
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [entry.model_copy() for entry in queue.items]
    current = _find_queue_item(items, queue.current_item_id)
    if current and current.status == "running":
        _replace_queue_item(items, current.model_copy(update={"status": "paused"}))
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "pause_reason": normalized_reason,
                "resume_hint": note.strip() or f"Resume when {normalized_reason} is resolved.",
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def resume_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    if queue.status not in PAUSED_QUEUE_STATUSES:
        msg = f"Queue cannot be resumed from status: {queue.status}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [entry.model_copy() for entry in queue.items]
    current_item_id = queue.current_item_id
    current = _find_queue_item(items, current_item_id)
    if current and current.status in {"paused", "blocked"}:
        running = current.model_copy(update={"status": "running", "started_at": current.started_at or now})
        _replace_queue_item(items, running)
        current_item_id = running.item_id
    elif not current_item_id:
        next_item = next((entry for entry in items if entry.status == "pending"), None)
        if next_item:
            running = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, running)
            current_item_id = running.item_id
    status = "running" if current_item_id else "completed"
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "pause_reason": None,
                "resume_hint": "Queue resumed. Generate a Codex handoff prompt with devo project handoff-next.",
                "current_item_id": current_item_id,
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def queue_artifact_paths(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_queue_id(queue_id)
    return paths.queues_dir / f"queue-{safe_id}.json", paths.queues_dir / f"queue-{safe_id}.md"


def handoff_artifact_paths(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_handoff_id(handoff_id)
    return paths.handoffs_dir / f"handoff-{safe_id}.json", paths.handoffs_dir / f"handoff-{safe_id}.md"


def create_codex_handoff_for_queue_next(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue, item = get_queue_next_item(project_name, queue_id, workspace_root=root)
    if queue.status == "completed":
        msg = f"Execution queue is completed: {queue.queue_id}"
        raise ValueError(msg)
    if not item:
        msg = f"Execution queue has no running or pending item: {queue.queue_id}"
        raise ValueError(msg)
    task = _try_get_backlog_task(project_name, item.task_id, root)
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        queue=queue,
        queue_item=item,
        task=task,
        batch=load_project_batch(project_name, queue.source_batch_id, workspace_root=root),
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        prompt=prompt,
        source_queue_id=queue.queue_id,
        source_batch_id=queue.source_batch_id,
        source_item_id=item.item_id,
        source_task_id=item.task_id,
        workspace_root=root,
    )


def create_codex_handoff_for_task(project_name: str, task_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    task = get_backlog_task(project_name, task_id, workspace_root=root)
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="task",
        title=f"{task.id}: {task.title}",
        task=task,
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="task",
        title=f"{task.id}: {task.title}",
        prompt=prompt,
        source_task_id=task.id,
        workspace_root=root,
    )


def create_codex_handoff_for_batch(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    tasks = [_try_get_backlog_task(project_name, task_id, root) for task_id in batch.task_ids]
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="batch",
        title=f"{batch.batch_id}: {batch.title}",
        batch=batch,
        tasks=[task for task in tasks if task],
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="batch",
        title=f"{batch.batch_id}: {batch.title}",
        prompt=prompt,
        source_batch_id=batch.batch_id,
        workspace_root=root,
    )


def list_codex_handoffs(project_name: str, workspace_root: Path | None = None) -> list[CodexHandoff]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    index = load_handoff_index(project_name, workspace_root=root)
    handoffs: list[CodexHandoff] = []
    for entry in index.handoffs:
        handoff = load_codex_handoff(project_name, entry.handoff_id, workspace_root=root)
        if handoff:
            handoffs.append(handoff)
    return sorted(handoffs, key=lambda item: item.updated_at, reverse=True)


def mark_codex_handoff_used(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    handoff = load_codex_handoff(project_name, handoff_id, workspace_root=root)
    if not handoff:
        msg = f"Codex handoff not found: {handoff_id}"
        raise ValueError(msg)
    updated = handoff.model_copy(update={"status": "used", "updated_at": datetime.now(UTC)})
    return _write_codex_handoff_model(project_name, updated, workspace_root=root)


def create_codex_worker_run_from_handoff(
    project_name: str,
    handoff_id: str,
    workspace_root: Path | None = None,
) -> tuple[WorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    handoff = load_codex_handoff(project_name, handoff_id, workspace_root=root)
    if not handoff:
        msg = f"Codex handoff not found: {handoff_id}"
        raise ValueError(msg)
    worker_run_id = _next_worker_run_id(project_name, workspace_root=root)
    now = datetime.now(UTC)
    task = _try_get_backlog_task(project_name, handoff.source_task_id, root) if handoff.source_task_id else None
    queue_item: QueueItem | None = None
    if handoff.source_queue_id and handoff.source_item_id:
        queue = load_execution_queue(project_name, handoff.source_queue_id, workspace_root=root)
        queue_item = _find_queue_item(queue.items, handoff.source_item_id) if queue else None
    worker_run = WorkerRun(
        project=project_name,
        worker_run_id=worker_run_id,
        worker_type="codex_cli",
        mode="manual_handoff",
        source_handoff_id=handoff.handoff_id,
        source_queue_id=handoff.source_queue_id,
        source_queue_item_id=handoff.source_item_id,
        source_batch_id=handoff.source_batch_id,
        source_task_id=handoff.source_task_id,
        title=f"Codex worker run for {handoff.handoff_id}: {handoff.title}",
        status="planned",
        prompt_path=handoff.prompt_path,
        target_repo_path=str(registration.path),
        allowed_scope=_worker_allowed_scope(task, queue_item),
        forbidden_scope=_worker_forbidden_scope(task),
        validation_expectations=_worker_validation_expectations(task, queue_item),
        safety_boundaries=_worker_safety_boundaries(project_name),
        created_at=now,
        updated_at=now,
        next_action=_worker_run_next_action(project_name, worker_run_id, "planned"),
    )
    return _write_worker_run(project_name, worker_run, workspace_root=root)


def prepare_codex_worker_for_queue_next(
    project_name: str,
    queue_id: str,
    workspace_root: Path | None = None,
) -> tuple[CodexHandoff, WorkerRun, CodexRunPlan, CodexPreflightResult, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue, item = get_queue_next_item(project_name, queue_id, workspace_root=root)
    if not item:
        msg = f"Execution queue has no running or pending item: {queue.queue_id}"
        raise ValueError(msg)
    handoff = _find_handoff_for_queue_item(project_name, queue.queue_id, item.item_id, workspace_root=root)
    if not handoff:
        handoff, _handoff_json, _handoff_md = create_codex_handoff_for_queue_next(project_name, queue.queue_id, workspace_root=root)
    worker_run, _worker_json, _worker_md = create_codex_worker_run_from_handoff(project_name, handoff.handoff_id, workspace_root=root)
    plan, preflight, plan_json, plan_md = create_codex_worker_run_plan(project_name, worker_run.worker_run_id, workspace_root=root)
    return handoff, worker_run, plan, preflight, plan_json, plan_md


def get_codex_queue_worker_status(
    project_name: str,
    queue_id: str,
    *,
    item_id: str | None = None,
    workspace_root: Path | None = None,
) -> CodexQueueWorkerStatus:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    item, selected_item_source = _select_queue_worker_status_item(queue, item_id)
    worker_run = _latest_worker_run_for_queue_item(project_name, queue.queue_id, item.item_id if item else None, workspace_root=root)
    run_plan = _latest_run_plan_for_worker(project_name, worker_run.worker_run_id if worker_run else None, workspace_root=root)
    report = load_codex_worker_report(project_name, worker_run.worker_run_id, workspace_root=root) if worker_run else None
    review = load_codex_worker_review(project_name, worker_run.worker_run_id, workspace_root=root) if worker_run else None
    readiness = get_queue_item_completion_readiness(project_name, queue.queue_id, item.item_id, workspace_root=root) if item else None
    return CodexQueueWorkerStatus(
        project=project_name,
        queue_id=queue.queue_id,
        queue_status=queue.status,
        current_item_id=item.item_id if item else None,
        current_item_status=item.status if item else None,
        current_task_id=item.task_id if item else None,
        selected_item_source=selected_item_source,
        source_handoff_id=worker_run.source_handoff_id if worker_run else None,
        linked_worker_run_id=worker_run.worker_run_id if worker_run else None,
        linked_worker_run_status=worker_run.status if worker_run else None,
        linked_run_plan_id=run_plan.plan_id if run_plan else None,
        linked_run_plan_status=run_plan.status if run_plan else None,
        latest_worker_execution_status=worker_run.status if worker_run and worker_run.execution_exit_code is not None else None,
        latest_worker_execution_exit_code=worker_run.execution_exit_code if worker_run else None,
        latest_worker_execution_log_path=worker_run.execution_log_path if worker_run else None,
        latest_worker_report_status=report.status_reported_by_worker if report else (worker_run.report.report_status if worker_run else None),
        latest_worker_review_id=review.review_id if review else None,
        latest_worker_review_status=review.review_status if review else None,
        latest_worker_validation_status=review.validation_evidence.validation_status if review else None,
        current_queue_item_completion_ready=readiness.completion_ready if readiness else False,
        current_queue_item_completion_blockers=readiness.blockers if readiness else ["No current or pending queue item found."],
        current_queue_item_review_status=readiness.review_status if readiness else None,
        current_queue_item_validation_status=readiness.validation_status if readiness else None,
        next_action=(
            readiness.next_action
            if readiness and (item.status == "waiting_review" or (worker_run and worker_run.execution_exit_code is not None))
            else _queue_worker_next_action(project_name, queue.queue_id, item, worker_run, run_plan)
        ),
    )


def get_codex_worker_flow_summary(
    project_name: str,
    queue_id: str,
    *,
    item_id: str | None = None,
    workspace_root: Path | None = None,
) -> CodexWorkerFlowSummary:
    root = workspace_root or get_workspace_root()
    status = get_codex_queue_worker_status(project_name, queue_id, item_id=item_id, workspace_root=root)
    queue = _require_queue(project_name, queue_id, root)
    item = _find_queue_item(queue.items, status.current_item_id)
    readiness = (
        get_queue_item_completion_readiness(project_name, queue.queue_id, item.item_id, workspace_root=root)
        if item
        else None
    )
    plan = load_codex_run_plan(project_name, status.linked_run_plan_id, workspace_root=root) if status.linked_run_plan_id else None
    commands = _worker_flow_next_commands(project_name, status, readiness, plan)
    return CodexWorkerFlowSummary(
        project=project_name,
        queue_id=status.queue_id,
        queue_status=status.queue_status,
        selected_item_id=status.current_item_id,
        selected_item_status=status.current_item_status,
        source_handoff_id=status.source_handoff_id,
        linked_worker_run_id=status.linked_worker_run_id,
        linked_worker_run_status=status.linked_worker_run_status,
        linked_run_plan_id=status.linked_run_plan_id,
        linked_run_plan_status=status.linked_run_plan_status,
        linked_run_plan_preflight_status=plan.preflight_status if plan else None,
        worker_report_status=status.latest_worker_report_status,
        worker_review_status=status.latest_worker_review_status,
        validation_evidence_status=status.latest_worker_validation_status,
        completion_ready=status.current_queue_item_completion_ready,
        completion_blockers=status.current_queue_item_completion_blockers,
        next_commands=commands,
    )


def get_queue_item_completion_readiness(
    project_name: str,
    queue_id: str,
    item_id: str,
    workspace_root: Path | None = None,
) -> QueueItemCompletionReadiness:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    item = _require_queue_item(queue, item_id)
    worker_run = _latest_worker_run_for_queue_item(project_name, queue.queue_id, item.item_id, workspace_root=root)
    review = load_codex_worker_review(project_name, worker_run.worker_run_id, workspace_root=root) if worker_run else None
    review_status = review.review_status if review else None
    validation_status = review.validation_evidence.validation_status if review else None
    blockers: list[str] = []
    review_required = bool(worker_run) or item.status == "waiting_review"
    if item.status == "completed":
        blockers.append("Queue item is already completed.")
    if review_required:
        if not worker_run:
            blockers.append("Queue item is waiting for review but no linked Codex worker run was found.")
        elif not review:
            blockers.append(f"Linked worker run {worker_run.worker_run_id} has no worker review artifact.")
        elif review.review_status != "reviewed_passed":
            blockers.append(f"Worker review status is {review.review_status}, not reviewed_passed.")
        if review and review.validation_evidence.validation_status == "failed":
            blockers.append("Worker review validation evidence status is failed.")
    ready = not blockers
    next_action = _queue_completion_next_action(project_name, queue.queue_id, item, worker_run, review, blockers)
    return QueueItemCompletionReadiness(
        project=project_name,
        queue_id=queue.queue_id,
        item_id=item.item_id,
        item_status=item.status,
        linked_worker_run_id=worker_run.worker_run_id if worker_run else None,
        review_id=review.review_id if review else None,
        review_status=review_status,
        validation_status=validation_status,
        completion_ready=ready,
        blockers=blockers,
        next_action=next_action,
    )


def load_worker_run_index(project_name: str, workspace_root: Path | None = None) -> WorkerRunIndex:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.worker_run_index_json.exists():
        return WorkerRunIndex(project=project_name)
    return WorkerRunIndex.model_validate_json(paths.worker_run_index_json.read_text(encoding="utf-8"))


def load_codex_worker_run(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> WorkerRun | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = worker_run_artifact_paths(project_name, worker_run_id, workspace_root=root)
    if not json_path.exists():
        return None
    return WorkerRun.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_codex_worker_runs(project_name: str, workspace_root: Path | None = None) -> list[WorkerRun]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    worker_runs: list[WorkerRun] = []
    if paths.worker_run_index_json.exists():
        index = load_worker_run_index(project_name, workspace_root=root)
        for entry in index.worker_runs:
            worker_run = load_codex_worker_run(project_name, entry.worker_run_id, workspace_root=root)
            if worker_run:
                worker_runs.append(worker_run)
    else:
        for path in sorted(paths.codex_dir.glob("worker-run-*.json")):
            if path.name == WORKER_RUN_INDEX_JSON:
                continue
            try:
                worker_runs.append(WorkerRun.model_validate_json(path.read_text(encoding="utf-8")))
            except (ValueError, ValidationError):
                continue
    return sorted(worker_runs, key=lambda item: item.updated_at, reverse=True)


def update_codex_worker_run_status(
    project_name: str,
    worker_run_id: str,
    status: str,
    note: str = "",
    workspace_root: Path | None = None,
) -> tuple[WorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = load_codex_worker_run(project_name, worker_run_id, workspace_root=root)
    if not worker_run:
        msg = f"Codex worker run not found: {worker_run_id}"
        raise ValueError(msg)
    normalized_status = status.strip().lower()
    if normalized_status not in ALLOWED_WORKER_RUN_STATUSES:
        msg = f"Invalid worker run status: {status}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    updates: dict[str, object] = {
        "status": normalized_status,
        "status_note": note.strip(),
        "updated_at": now,
        "next_action": _worker_run_next_action(project_name, worker_run.worker_run_id, normalized_status),
    }
    if normalized_status == "running" and not worker_run.started_at:
        updates["started_at"] = now
    if normalized_status in {"completed", "failed", "cancelled", "superseded"}:
        updates["completed_at"] = now
    updated = worker_run.model_copy(update=updates)
    return _write_worker_run(project_name, updated, workspace_root=root)


def mark_codex_worker_run_handoff_used(
    project_name: str,
    worker_run_id: str,
    workspace_root: Path | None = None,
) -> tuple[WorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = load_codex_worker_run(project_name, worker_run_id, workspace_root=root)
    if not worker_run:
        msg = f"Codex worker run not found: {worker_run_id}"
        raise ValueError(msg)
    if not worker_run.source_handoff_id:
        msg = f"Codex worker run has no linked handoff: {worker_run_id}"
        raise ValueError(msg)
    mark_codex_handoff_used(project_name, worker_run.source_handoff_id, workspace_root=root)
    updated = worker_run.model_copy(
        update={
            "status_note": "Linked handoff marked used. This does not imply worker completion.",
            "updated_at": datetime.now(UTC),
            "next_action": _worker_run_next_action(project_name, worker_run.worker_run_id, worker_run.status),
        }
    )
    return _write_worker_run(project_name, updated, workspace_root=root)


def create_codex_worker_report_template(
    project_name: str,
    worker_run_id: str,
    workspace_root: Path | None = None,
) -> tuple[Path, Path, CodexWorkerReport]:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = worker_report_template_paths(project_name, worker_run.worker_run_id, workspace_root=root)
    template = CodexWorkerReport(
        project=project_name,
        worker_run_id=worker_run.worker_run_id,
        source_handoff_id=worker_run.source_handoff_id,
        source_queue_id=worker_run.source_queue_id,
        source_queue_item_id=worker_run.source_queue_item_id,
        source_task_id=worker_run.source_task_id,
        status_reported_by_worker="partial",
        summary="Replace this with the manual Codex final report summary.",
        changed_files=[],
        validation_attempted=False,
        validation_results=[],
        tests_run=[],
        commands_run=[],
        commit_hash=None,
        safety_warnings=[],
        blockers=[],
        follow_up_needed=[],
        notes=[
            "Fill this template from the manual Codex final report.",
            "This report is evidence, not proof of completion.",
        ],
        reported_at=datetime.now(UTC),
    )
    _write_model(json_path, template)
    markdown_path.write_text(render_codex_worker_report_template_markdown(template), encoding="utf-8")
    return json_path, markdown_path, template


def validate_codex_worker_report_file(
    project_name: str,
    worker_run_id: str,
    report_file: Path,
    workspace_root: Path | None = None,
) -> WorkerReportValidationResult:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    source_path = report_file.expanduser().resolve()
    if not source_path.exists():
        return WorkerReportValidationResult(valid=False, errors=[f"Report file does not exist: {source_path}"])
    if not source_path.is_file():
        return WorkerReportValidationResult(valid=False, errors=[f"Report path must be a file: {source_path}"])
    try:
        report = CodexWorkerReport.model_validate_json(source_path.read_text(encoding="utf-8-sig"))
    except (ValueError, ValidationError) as exc:
        return WorkerReportValidationResult(valid=False, errors=[f"Invalid Codex worker report JSON: {exc}"])
    errors: list[str] = []
    warnings: list[str] = []
    if report.project != project_name:
        errors.append(f"Report project must be {project_name}, got {report.project}.")
    if _normalize_worker_run_id(report.worker_run_id) != worker_run.worker_run_id:
        errors.append(f"Report worker_run_id must be {worker_run.worker_run_id}, got {report.worker_run_id}.")
    if report.source_handoff_id != worker_run.source_handoff_id:
        warnings.append("Report source_handoff_id does not match the worker run source handoff.")
    if report.status_reported_by_worker not in ALLOWED_WORKER_REPORTED_STATUSES:
        errors.append(f"Invalid status_reported_by_worker: {report.status_reported_by_worker}.")
    if not report.summary.strip():
        errors.append("Report summary is required.")
    if report.status_reported_by_worker == "completed" and not report.changed_files:
        warnings.append("Worker reported completed but changed_files is empty.")
    if not report.validation_results:
        warnings.append("validation_results is empty; independent validation/review is still required.")
    if report.commit_hash:
        warnings.append("commit_hash is worker-reported only; verify delivery independently before trusting it.")
    if report.commands_run:
        warnings.append("commands_run is worker-reported only; Devo did not execute or verify those commands during import.")
    return WorkerReportValidationResult(valid=not errors, errors=errors, warnings=warnings, report=report if not errors else None)


def import_codex_worker_report(
    project_name: str,
    worker_run_id: str,
    report_file: Path,
    workspace_root: Path | None = None,
) -> tuple[WorkerRun, CodexWorkerReport, WorkerReportValidationResult, Path, Path, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    validation = validate_codex_worker_report_file(project_name, worker_run.worker_run_id, report_file, workspace_root=root)
    if not validation.valid or not validation.report:
        msg = "Codex worker report validation failed: " + "; ".join(validation.errors)
        raise ValueError(msg)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = worker_report_artifact_paths(project_name, worker_run.worker_run_id, workspace_root=root)
    report = validation.report.model_copy(update={"worker_run_id": worker_run.worker_run_id})
    _write_model(json_path, report)
    markdown_path.write_text(render_codex_worker_report_markdown(report, validation), encoding="utf-8")
    now = datetime.now(UTC)
    report_status = "validated" if not validation.warnings else "present"
    metadata = WorkerReportMetadata(
        report_status=report_status,
        reported_changed_files=report.changed_files,
        reported_validation=_reported_validation_summary(report),
        reported_commit_hash=report.commit_hash,
        safety_warnings=[*report.safety_warnings, *validation.warnings],
        reviewer_notes=[
            "Imported report is worker-provided evidence only.",
            "Queue/task completion still requires independent validation/review and explicit Devo action.",
        ],
        imported_at=now,
    )
    mapped_status = _worker_status_from_report_status(report.status_reported_by_worker)
    updated = worker_run.model_copy(
        update={
            "status": mapped_status,
            "report_path": str(markdown_path),
            "report": metadata,
            "updated_at": now,
            "completed_at": now if mapped_status == "failed" else worker_run.completed_at,
            "status_note": f"Imported manual Codex report with worker status {report.status_reported_by_worker}.",
            "next_action": _worker_report_next_action(project_name, worker_run.worker_run_id, report.status_reported_by_worker),
        }
    )
    updated_worker_run, worker_json, worker_markdown = _write_worker_run(project_name, updated, workspace_root=root)
    return updated_worker_run, report, validation, json_path, markdown_path, worker_json, worker_markdown


def load_codex_worker_report(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> CodexWorkerReport | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = worker_report_artifact_paths(project_name, worker_run_id, workspace_root=root)
    if not json_path.exists():
        return None
    return CodexWorkerReport.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_codex_worker_reports(project_name: str, workspace_root: Path | None = None) -> list[CodexWorkerReport]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    reports: list[CodexWorkerReport] = []
    for path in sorted(paths.reports_dir.glob("report-*.json")):
        if path.name.endswith("-template.json"):
            continue
        try:
            reports.append(CodexWorkerReport.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(reports, key=lambda report: report.reported_at or datetime.min.replace(tzinfo=UTC), reverse=True)


def create_codex_worker_review_template(
    project_name: str,
    worker_run_id: str,
    workspace_root: Path | None = None,
) -> tuple[WorkerReview, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    existing = load_codex_worker_review(project_name, worker_run.worker_run_id, workspace_root=root)
    if existing:
        json_path, markdown_path = worker_review_artifact_paths(project_name, worker_run.worker_run_id, workspace_root=root)
        return existing, json_path, markdown_path
    report = load_codex_worker_report(project_name, worker_run.worker_run_id, workspace_root=root)
    queue_item = _linked_queue_item(project_name, worker_run, workspace_root=root)
    report_json, _report_md = worker_report_artifact_paths(project_name, worker_run.worker_run_id, workspace_root=root)
    evidence = ValidationEvidence(
        validation_status="provided" if report and (report.validation_results or report.tests_run or report.commands_run) else "not_provided",
        commands_reported=report.commands_run if report else [],
        tests_reported=report.tests_run if report else [],
        validation_summary="; ".join(report.validation_results) if report and report.validation_results else "",
        evidence_paths=[str(report_json)] if report and report_json.exists() else [],
        warnings=["Worker-reported validation must be independently reviewed."] if report and (report.commands_run or report.tests_run) else [],
    )
    review = WorkerReview(
        project=project_name,
        review_id=f"REV-{worker_run.worker_run_id}",
        worker_run_id=worker_run.worker_run_id,
        source_queue_id=worker_run.source_queue_id,
        source_queue_item_id=worker_run.source_queue_item_id,
        source_task_id=worker_run.source_task_id,
        source_handoff_id=worker_run.source_handoff_id,
        source_report_path=str(report_json) if report and report_json.exists() else None,
        validation_evidence=evidence,
        changed_files_review=[f"Review changed file: {path}" for path in (report.changed_files if report else worker_run.report.reported_changed_files)],
        safety_review=[*worker_run.safety_boundaries, *(report.safety_warnings if report else worker_run.report.safety_warnings)],
        acceptance_criteria_review=queue_item.acceptance_criteria if queue_item else [],
        follow_up_items=report.follow_up_needed if report else [],
        next_action=_worker_review_next_action(project_name, worker_run, "draft"),
    )
    return _write_worker_review(project_name, review, workspace_root=root)


def load_worker_review_index(project_name: str, workspace_root: Path | None = None) -> WorkerReviewIndex:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.review_index_json.exists():
        return WorkerReviewIndex(project=project_name)
    return WorkerReviewIndex.model_validate_json(paths.review_index_json.read_text(encoding="utf-8"))


def load_codex_worker_review(project_name: str, worker_run_id: str, workspace_root: Path | None = None) -> WorkerReview | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = worker_review_artifact_paths(project_name, worker_run_id, workspace_root=root)
    if not json_path.exists():
        return None
    return WorkerReview.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_codex_worker_reviews(project_name: str, workspace_root: Path | None = None) -> list[WorkerReview]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    reviews: list[WorkerReview] = []
    if paths.review_index_json.exists():
        index = load_worker_review_index(project_name, workspace_root=root)
        for entry in index.reviews:
            review = load_codex_worker_review(project_name, entry.worker_run_id, workspace_root=root)
            if review:
                reviews.append(review)
    else:
        for path in sorted(paths.reviews_dir.glob("review-*.json")):
            if path.name == WORKER_REVIEW_INDEX_JSON:
                continue
            try:
                reviews.append(WorkerReview.model_validate_json(path.read_text(encoding="utf-8")))
            except (ValueError, ValidationError):
                continue
    return sorted(reviews, key=lambda item: item.updated_at, reverse=True)


def attach_codex_worker_review_evidence(
    project_name: str,
    worker_run_id: str,
    validation_status: str,
    summary: str,
    workspace_root: Path | None = None,
) -> tuple[WorkerReview, Path, Path]:
    root = workspace_root or get_workspace_root()
    normalized_status = validation_status.strip().lower()
    if normalized_status not in ALLOWED_VALIDATION_EVIDENCE_STATUSES - {"not_provided"}:
        msg = f"Invalid validation evidence status: {validation_status}"
        raise ValueError(msg)
    review = load_codex_worker_review(project_name, worker_run_id, workspace_root=root)
    if not review:
        review, _json_path, _markdown_path = create_codex_worker_review_template(project_name, worker_run_id, workspace_root=root)
    cleaned = summary.strip()
    if not cleaned:
        msg = "Validation evidence summary must not be empty."
        raise ValueError(msg)
    evidence = review.validation_evidence.model_copy(
        update={
            "validation_status": normalized_status,
            "validation_summary": cleaned,
            "warnings": [
                *review.validation_evidence.warnings,
                "Evidence was recorded manually; Devo did not run validation automatically.",
            ],
        }
    )
    updated = review.model_copy(
        update={
            "validation_evidence": evidence,
            "updated_at": datetime.now(UTC),
            "next_action": _worker_review_next_action(project_name, _require_worker_run(project_name, worker_run_id, root), review.review_status),
        }
    )
    return _write_worker_review(project_name, updated, workspace_root=root)


def record_codex_worker_review(
    project_name: str,
    worker_run_id: str,
    review_status: str,
    reviewer: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[WorkerReview, WorkerRun, Path, Path, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    normalized_status = review_status.strip().lower()
    if normalized_status not in ALLOWED_WORKER_REVIEW_STATUSES - {"draft"}:
        msg = f"Invalid worker review status: {review_status}"
        raise ValueError(msg)
    cleaned_reviewer = reviewer.strip()
    if not cleaned_reviewer:
        msg = "Reviewer is required."
        raise ValueError(msg)
    cleaned_note = note.strip()
    if not cleaned_note:
        msg = "Review note is required."
        raise ValueError(msg)
    review = load_codex_worker_review(project_name, worker_run.worker_run_id, workspace_root=root)
    if not review:
        review, _json_path, _markdown_path = create_codex_worker_review_template(project_name, worker_run.worker_run_id, workspace_root=root)
    now = datetime.now(UTC)
    updated_review = review.model_copy(
        update={
            "review_status": normalized_status,
            "reviewer": cleaned_reviewer,
            "decision_note": cleaned_note,
            "updated_at": now,
            "next_action": _worker_review_next_action(project_name, worker_run, normalized_status),
        }
    )
    updated_review, review_json, review_markdown = _write_worker_review(project_name, updated_review, workspace_root=root)
    worker_note = f"Worker review {updated_review.review_id} recorded as {normalized_status} by {cleaned_reviewer}."
    updated_worker = worker_run.model_copy(
        update={
            "status_note": worker_note,
            "updated_at": now,
            "next_action": updated_review.next_action,
        }
    )
    updated_worker, worker_json, worker_markdown = _write_worker_run(project_name, updated_worker, workspace_root=root)
    return updated_review, updated_worker, review_json, review_markdown, worker_json, worker_markdown


def run_codex_worker_preflight(
    project_name: str,
    worker_run_id: str,
    *,
    codex_path: str | None = None,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
    workspace_root: Path | None = None,
) -> CodexPreflightResult:
    root = workspace_root or get_workspace_root()
    checks: list[CodexPreflightCheck] = []
    blocked_reasons: list[str] = []
    warnings: list[str] = []

    try:
        registration = load_registered_project(project_name, workspace_root=root)
        checks.append(CodexPreflightCheck(name="project_registered", status="OK", detail=f"Project is registered at {registration.path}."))
    except ValueError as exc:
        blocked_reasons.append(str(exc))
        checks.append(CodexPreflightCheck(name="project_registered", status="FAIL", detail=str(exc)))
        return _codex_preflight_result(project_name, _normalize_worker_run_id(worker_run_id), checks, blocked_reasons, warnings)

    worker_run = load_codex_worker_run(project_name, worker_run_id, workspace_root=root)
    if not worker_run:
        blocked_reasons.append(f"Codex worker run not found: {worker_run_id}")
        checks.append(CodexPreflightCheck(name="worker_run_exists", status="FAIL", detail=f"Codex worker run not found: {worker_run_id}"))
        return _codex_preflight_result(project_name, _normalize_worker_run_id(worker_run_id), checks, blocked_reasons, warnings)
    checks.append(CodexPreflightCheck(name="worker_run_exists", status="OK", detail=f"Worker run exists: {worker_run.worker_run_id}."))

    if worker_run.status in {"planned", "waiting_review", "paused_usage_limit", "blocked_needs_approval"}:
        checks.append(CodexPreflightCheck(name="worker_run_status", status="OK", detail=f"Worker run status is suitable for planning: {worker_run.status}."))
    else:
        blocked_reasons.append(f"Worker run status is not suitable for run planning: {worker_run.status}.")
        checks.append(CodexPreflightCheck(name="worker_run_status", status="FAIL", detail=f"Status is {worker_run.status}."))

    if worker_run.source_handoff_id:
        handoff = load_codex_handoff(project_name, worker_run.source_handoff_id, workspace_root=root)
        if handoff:
            checks.append(CodexPreflightCheck(name="handoff_exists", status="OK", detail=f"Linked handoff exists: {handoff.handoff_id}."))
        else:
            blocked_reasons.append(f"Linked handoff is missing: {worker_run.source_handoff_id}.")
            checks.append(CodexPreflightCheck(name="handoff_exists", status="FAIL", detail=f"Missing handoff: {worker_run.source_handoff_id}."))
    else:
        blocked_reasons.append("Worker run has no linked handoff id.")
        checks.append(CodexPreflightCheck(name="handoff_exists", status="FAIL", detail="Worker run has no linked handoff id."))

    prompt_path = Path(worker_run.prompt_path)
    if prompt_path.exists() and prompt_path.is_file():
        checks.append(CodexPreflightCheck(name="prompt_file_exists", status="OK", detail=f"Prompt file exists: {prompt_path}."))
    else:
        blocked_reasons.append(f"Prompt file is missing: {prompt_path}.")
        checks.append(CodexPreflightCheck(name="prompt_file_exists", status="FAIL", detail=f"Prompt file is missing: {prompt_path}."))

    target_repo_path = Path(worker_run.target_repo_path)
    if target_repo_path.exists() and target_repo_path.is_dir():
        checks.append(CodexPreflightCheck(name="target_repo_path_exists", status="OK", detail=f"Target repo path exists: {target_repo_path}."))
    else:
        blocked_reasons.append(f"Target repo path is missing: {target_repo_path}.")
        checks.append(CodexPreflightCheck(name="target_repo_path_exists", status="FAIL", detail=f"Target repo path is missing: {target_repo_path}."))

    if worker_run.source_queue_id:
        queue = load_execution_queue(project_name, worker_run.source_queue_id, workspace_root=root)
        if queue:
            checks.append(CodexPreflightCheck(name="linked_queue", status="OK", detail=f"Linked queue exists: {queue.queue_id}."))
            if worker_run.source_queue_item_id and not _find_queue_item(queue.items, worker_run.source_queue_item_id):
                warnings.append(f"Linked queue item not found in queue: {worker_run.source_queue_item_id}.")
                checks.append(CodexPreflightCheck(name="linked_queue_item", status="WARN", detail=f"Queue item not found: {worker_run.source_queue_item_id}."))
        else:
            warnings.append(f"Linked queue metadata is missing: {worker_run.source_queue_id}.")
            checks.append(CodexPreflightCheck(name="linked_queue", status="WARN", detail=f"Linked queue metadata missing: {worker_run.source_queue_id}."))

    if worker_run.source_task_id and not _try_get_backlog_task(project_name, worker_run.source_task_id, root):
        warnings.append(f"Linked backlog task metadata is missing: {worker_run.source_task_id}.")
        checks.append(CodexPreflightCheck(name="linked_task", status="WARN", detail=f"Linked backlog task metadata missing: {worker_run.source_task_id}."))
    elif worker_run.source_task_id:
        checks.append(CodexPreflightCheck(name="linked_task", status="OK", detail=f"Linked backlog task exists: {worker_run.source_task_id}."))

    executable = diagnose_codex_executable(codex_path, codex_wrapper=codex_wrapper, codex_wsl=codex_wsl, target_repo_path=worker_run.target_repo_path)
    if executable.launch_blockers:
        blocked_reasons.extend(executable.launch_blockers)
        check_name = _codex_launcher_check_name(executable)
        checks.append(CodexPreflightCheck(name=check_name, status="FAIL", detail=executable.command_resolution_note))
    elif executable.executable_path:
        check_name = _codex_launcher_check_name(executable)
        checks.append(CodexPreflightCheck(name=check_name, status="OK", detail=executable.command_resolution_note))
    elif executable.wrapper_path:
        checks.append(CodexPreflightCheck(name=_codex_launcher_check_name(executable), status="OK", detail=executable.command_resolution_note))
    else:
        warnings.append("Codex executable was not found on PATH by safe detection; future supervised execution may need configuration.")
        checks.append(CodexPreflightCheck(name="codex_path_detection", status="WARN", detail="Codex executable was not found on PATH. No command was executed."))
    warnings.extend(executable.launch_warnings)

    return _codex_preflight_result(project_name, worker_run.worker_run_id, checks, blocked_reasons, warnings)


def create_codex_worker_run_plan(
    project_name: str,
    worker_run_id: str,
    *,
    codex_path: str | None = None,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[CodexRunPlan, CodexPreflightResult, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run = _require_worker_run(project_name, worker_run_id, root)
    preflight = run_codex_worker_preflight(
        project_name,
        worker_run.worker_run_id,
        codex_path=codex_path,
        codex_wrapper=codex_wrapper,
        codex_wsl=codex_wsl,
        workspace_root=root,
    )
    executable = diagnose_codex_executable(codex_path, codex_wrapper=codex_wrapper, codex_wsl=codex_wsl, target_repo_path=worker_run.target_repo_path)
    plan_id = _next_run_plan_id(project_name, workspace_root=root)
    now = datetime.now(UTC)
    status = "ready" if preflight.status in {"passed", "warnings"} and not preflight.blocked_reasons else "blocked"
    plan = CodexRunPlan(
        project=project_name,
        plan_id=plan_id,
        worker_run_id=worker_run.worker_run_id,
        handoff_id=worker_run.source_handoff_id or "",
        queue_id=worker_run.source_queue_id,
        queue_item_id=worker_run.source_queue_item_id,
        task_id=worker_run.source_task_id,
        batch_id=worker_run.source_batch_id,
        status=status,
        target_repo_path=worker_run.target_repo_path,
        prompt_path=worker_run.prompt_path,
        proposed_working_directory=worker_run.target_repo_path,
        proposed_command_label="Codex CLI supervised worker",
        proposed_command_preview=_plan_command_preview(executable, worker_run.prompt_path),
        launcher_type=executable.launcher_type,
        codex_executable_path=executable.executable_path,
        codex_executable_source=executable.executable_source,
        codex_wrapper_path=executable.wrapper_path,
        codex_wsl_distribution=executable.wsl_distribution,
        command_resolution_note=executable.command_resolution_note,
        launch_risk=executable.launch_risk,
        launch_blockers=executable.launch_blockers,
        launch_warnings=executable.launch_warnings,
        approval_required=True,
        approval_status="not_requested",
        preflight_status=preflight.status,
        preflight_checks=preflight.checks,
        safety_boundaries=worker_run.safety_boundaries,
        allowed_scope=worker_run.allowed_scope,
        forbidden_scope=worker_run.forbidden_scope,
        validation_expectations=worker_run.validation_expectations,
        blocked_reasons=preflight.blocked_reasons,
        warnings=preflight.warnings,
        next_action=_run_plan_next_action(project_name, plan_id, preflight.status, preflight.blocked_reasons),
        created_at=now,
        updated_at=now,
    )
    written, json_path, markdown_path = _write_codex_run_plan(project_name, plan, workspace_root=root)
    return written, preflight, json_path, markdown_path


def load_codex_run_plan(project_name: str, plan_id: str, workspace_root: Path | None = None) -> CodexRunPlan | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = worker_run_plan_artifact_paths(project_name, plan_id, workspace_root=root)
    if not json_path.exists():
        return None
    return CodexRunPlan.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_codex_run_plans(project_name: str, workspace_root: Path | None = None) -> list[CodexRunPlan]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    plans: list[CodexRunPlan] = []
    if paths.run_plan_index_json.exists():
        index = load_codex_run_plan_index(project_name, workspace_root=root)
        for entry in index.run_plans:
            plan = load_codex_run_plan(project_name, entry.plan_id, workspace_root=root)
            if plan:
                plans.append(plan)
    else:
        for path in sorted(paths.run_plans_dir.glob("run-plan-*.json")):
            if path.name == WORKER_RUN_PLAN_INDEX_JSON:
                continue
            try:
                plans.append(CodexRunPlan.model_validate_json(path.read_text(encoding="utf-8")))
            except (ValueError, ValidationError):
                continue
    return sorted(plans, key=lambda item: item.updated_at, reverse=True)


def load_codex_run_plan_index(project_name: str, workspace_root: Path | None = None) -> CodexRunPlanIndex:
    paths = worker_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.run_plan_index_json.exists():
        return CodexRunPlanIndex(project=project_name)
    return CodexRunPlanIndex.model_validate_json(paths.run_plan_index_json.read_text(encoding="utf-8"))


def approve_codex_run_plan(project_name: str, plan_id: str, note: str = "", workspace_root: Path | None = None) -> tuple[CodexRunPlan, Path, Path]:
    root = workspace_root or get_workspace_root()
    plan = load_codex_run_plan(project_name, plan_id, workspace_root=root)
    if not plan:
        msg = f"Codex run plan not found: {plan_id}"
        raise ValueError(msg)
    updated = plan.model_copy(
        update={
            "approval_status": "approved",
            "approval_note": note.strip() or plan.approval_note,
            "updated_at": datetime.now(UTC),
            "next_action": (
                "Planning approval recorded. Preview or run the guarded one-shot execution only with "
                "execute-preview or execute --confirm-execute; review is still required afterward."
            ),
        }
    )
    return _write_codex_run_plan(project_name, updated, workspace_root=root)


def create_codex_wrapper_template(
    output_path: Path,
    *,
    wrapper_type: str = "cmd",
    force: bool = False,
    workspace_root: Path | None = None,
) -> Path:
    root = workspace_root or get_workspace_root()
    kind = wrapper_type.strip().lower()
    if kind != "cmd":
        msg = "Only --type cmd is supported for Codex wrapper templates in this version."
        raise ValueError(msg)
    path = output_path.expanduser()
    if path.suffix.lower() != ".cmd":
        path = path.with_suffix(".cmd")
    resolved_parent = path.parent.resolve()
    resolved_path = resolved_parent / path.name
    if resolved_path.exists() and not force:
        msg = f"Codex wrapper template already exists: {resolved_path}. Use --force to overwrite."
        raise ValueError(msg)
    _ensure_wrapper_template_location_is_safe(resolved_path, root)
    resolved_parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(_render_cmd_wrapper_template(), encoding="utf-8", newline="\r\n")
    return resolved_path


def preview_codex_worker_execution(
    project_name: str,
    worker_run_id: str,
    plan_id: str,
    *,
    codex_path: str | None = None,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
    workspace_root: Path | None = None,
) -> CodexExecutionPreview:
    root = workspace_root or get_workspace_root()
    worker_run, plan = _load_worker_run_and_plan_for_execution(project_name, worker_run_id, plan_id, root)
    log_path, stderr_log_path = worker_execution_log_paths(project_name, worker_run.worker_run_id, workspace_root=root)
    blocked_reasons, warnings, executable = _codex_execution_blockers(worker_run, plan, codex_path=codex_path, codex_wrapper=codex_wrapper, codex_wsl=codex_wsl)
    return CodexExecutionPreview(
        project=project_name,
        worker_run_id=worker_run.worker_run_id,
        plan_id=plan.plan_id,
        ready=not blocked_reasons,
        launcher_type=executable.launcher_type,
        executable_path=executable.executable_path,
        wrapper_path=executable.wrapper_path,
        wsl_distribution=executable.wsl_distribution,
        executable_source=executable.executable_source,
        command_resolution_note=executable.command_resolution_note,
        launch_risk=executable.launch_risk,
        command_preview=_plan_command_preview(executable, plan.prompt_path),
        execution_supported=executable.execution_supported,
        command_label=plan.proposed_command_label,
        proposed_working_directory=plan.proposed_working_directory,
        prompt_path=plan.prompt_path,
        log_path=str(log_path),
        stderr_log_path=str(stderr_log_path),
        approval_status=plan.approval_status,
        preflight_status=plan.preflight_status,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        safety_boundaries=plan.safety_boundaries,
        next_action=_execution_preview_next_action(project_name, worker_run.worker_run_id, plan.plan_id, blocked_reasons),
    )


def execute_codex_worker_run(
    project_name: str,
    worker_run_id: str,
    plan_id: str,
    *,
    started_by: str = "operator",
    codex_path: str | None = None,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
    workspace_root: Path | None = None,
    timeout_seconds: int = 3600,
) -> tuple[CodexExecutionResult, WorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    worker_run, plan = _load_worker_run_and_plan_for_execution(project_name, worker_run_id, plan_id, root)
    preview = preview_codex_worker_execution(
        project_name,
        worker_run.worker_run_id,
        plan.plan_id,
        codex_path=codex_path,
        codex_wrapper=codex_wrapper,
        codex_wsl=codex_wsl,
        workspace_root=root,
    )
    if preview.blocked_reasons:
        msg = "Codex execution is blocked: " + "; ".join(preview.blocked_reasons)
        raise ValueError(msg)
    execution_diagnostic = diagnose_codex_executable(
        codex_path,
        codex_wrapper=codex_wrapper,
        codex_wsl=codex_wsl,
        target_repo_path=worker_run.target_repo_path,
    )
    if not (codex_path or codex_wrapper or codex_wsl) and (plan.codex_wrapper_path or plan.codex_wsl_distribution or plan.codex_executable_path):
        execution_diagnostic = diagnose_codex_executable(
            plan.codex_executable_path,
            codex_wrapper=plan.codex_wrapper_path,
            codex_wsl=plan.codex_wsl_distribution,
            target_repo_path=worker_run.target_repo_path,
        )
    command_args = _launcher_subprocess_args(execution_diagnostic)
    if not command_args:
        raise ValueError("Codex launcher was not resolved for execution.")

    prompt_text = Path(plan.prompt_path).read_text(encoding="utf-8")
    log_path = Path(preview.log_path)
    stderr_log_path = Path(preview.stderr_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(UTC)
    running = worker_run.model_copy(
        update={
            "mode": "supervised_cli",
            "status": "running",
            "started_at": worker_run.started_at or started_at,
            "updated_at": started_at,
            "execution_command_label": plan.proposed_command_label,
            "execution_started_by": started_by.strip() or "operator",
            "execution_log_path": str(log_path),
            "execution_stderr_log_path": str(stderr_log_path),
            "transcript_path": str(log_path),
            "status_note": "Supervised Codex process started by Devo.",
            "next_action": _worker_run_next_action(project_name, worker_run.worker_run_id, "running"),
        }
    )
    _write_worker_run(project_name, running, workspace_root=root)

    launch_error_type: str | None = None
    launch_error_message: str | None = None
    try:
        completed = subprocess.run(
            command_args,
            input=prompt_text,
            text=True,
            capture_output=True,
            cwd=plan.proposed_working_directory,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = int(completed.returncode)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
        stderr = (stderr + "\nCodex execution timed out.").strip() + "\n"
    except (PermissionError, FileNotFoundError, OSError) as exc:
        exit_code = _codex_launch_exception_exit_code(exc)
        stdout = ""
        launch_error_type = type(exc).__name__
        launch_error_message = str(exc)
        stderr = _render_codex_launch_failure_stderr(" ".join(command_args), launch_error_type, launch_error_message)

    completed_at = datetime.now(UTC)
    log_path.write_text(_render_execution_log(plan, started_at, completed_at, exit_code, stdout), encoding="utf-8")
    stderr_log_path.write_text(stderr, encoding="utf-8")
    status = "failed" if launch_error_type else _classify_codex_execution_status(exit_code, stdout, stderr)
    next_action = _codex_launch_failure_next_action() if launch_error_type else _worker_run_next_action(project_name, worker_run.worker_run_id, status)
    status_note = (
        f"Codex failed to launch before producing output: {launch_error_type}: {launch_error_message}"
        if launch_error_type
        else _execution_status_note(status, exit_code)
    )
    updated_run = running.model_copy(
        update={
            "status": status,
            "completed_at": completed_at,
            "updated_at": completed_at,
            "execution_exit_code": exit_code,
            "status_note": status_note,
            "next_action": next_action,
        }
    )
    written_run, _json_path, _markdown_path = _write_worker_run(project_name, updated_run, workspace_root=root)
    _update_linked_queue_from_worker_execution(project_name, written_run, status, workspace_root=root)
    result = CodexExecutionResult(
        project=project_name,
        worker_run_id=worker_run.worker_run_id,
        plan_id=plan.plan_id,
        status=status,
        exit_code=exit_code,
        launch_error_type=launch_error_type,
        launch_error_message=launch_error_message,
        log_path=str(log_path),
        stderr_log_path=str(stderr_log_path),
        started_at=started_at,
        completed_at=completed_at,
        next_action=next_action,
    )
    return result, written_run, log_path, stderr_log_path


def render_codex_run_plan_markdown(plan: CodexRunPlan) -> str:
    lines = [
        f"# Codex Run Plan: {plan.plan_id}",
        "",
        f"- Project: `{plan.project}`",
        f"- Worker run: `{plan.worker_run_id}`",
        f"- Handoff: `{plan.handoff_id or 'none'}`",
        f"- Queue: `{plan.queue_id or 'none'}`",
        f"- Queue item: `{plan.queue_item_id or 'none'}`",
        f"- Task: `{plan.task_id or 'none'}`",
        f"- Batch: `{plan.batch_id or 'none'}`",
        f"- Status: `{plan.status}`",
        f"- Approval required: `{plan.approval_required}`",
        f"- Approval status: `{plan.approval_status}`",
        f"- Approval note: `{plan.approval_note or 'none'}`",
        f"- Preflight status: `{plan.preflight_status}`",
        f"- Target repo path: `{plan.target_repo_path}`",
        f"- Prompt path: `{plan.prompt_path}`",
        f"- Proposed working directory: `{plan.proposed_working_directory}`",
        f"- Proposed command label: `{plan.proposed_command_label}`",
        f"- Proposed command preview: `{plan.proposed_command_preview}`",
        f"- Codex executable path: `{plan.codex_executable_path or 'none'}`",
        f"- Codex executable source: `{plan.codex_executable_source}`",
        f"- Command resolution note: `{plan.command_resolution_note or 'none'}`",
        f"- Launch risk: `{plan.launch_risk}`",
        f"- Created: `{plan.created_at.isoformat()}`",
        f"- Updated: `{plan.updated_at.isoformat()}`",
        "",
        "## Next Action",
        "",
        plan.next_action or "No next action recorded.",
        "",
    ]
    _append_preflight_section(lines, plan.preflight_checks)
    _append_list_section(lines, "Blocked Reasons", plan.blocked_reasons)
    _append_list_section(lines, "Warnings", plan.warnings)
    _append_list_section(lines, "Launch Blockers", plan.launch_blockers)
    _append_list_section(lines, "Launch Warnings", plan.launch_warnings)
    _append_list_section(lines, "Allowed Scope", plan.allowed_scope)
    _append_list_section(lines, "Forbidden Scope", plan.forbidden_scope)
    _append_list_section(lines, "Validation Expectations", plan.validation_expectations)
    _append_list_section(lines, "Safety Boundaries", plan.safety_boundaries)
    lines.extend(
        [
            "## Safety Note",
            "",
            "This run plan is a safe preview only. Devo did not run Codex, call AI APIs, execute target commands, validate, commit, push, complete queue/tasks, or modify the target repository.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_codex_worker_report_template_markdown(report: CodexWorkerReport) -> str:
    return "\n".join(
        [
            f"# Codex Worker Report Template: {report.worker_run_id}",
            "",
            "Fill the JSON template from Codex's manual final report, then run:",
            "",
            f"```powershell\ndevo worker codex report-validate --project {report.project} --run {report.worker_run_id} --file <reportFile>\n```",
            "",
            "Do not treat this report as proof of completion. Import/review/validation remain separate Devo steps.",
            "",
        ]
    )


def render_codex_worker_report_markdown(report: CodexWorkerReport, validation: WorkerReportValidationResult | None = None) -> str:
    lines = [
        f"# Codex Worker Report: {report.worker_run_id}",
        "",
        f"- Project: `{report.project}`",
        f"- Worker reported status: `{report.status_reported_by_worker}`",
        f"- Source handoff: `{report.source_handoff_id or 'none'}`",
        f"- Source queue: `{report.source_queue_id or 'none'}`",
        f"- Source queue item: `{report.source_queue_item_id or 'none'}`",
        f"- Source task: `{report.source_task_id or 'none'}`",
        f"- Validation attempted: `{report.validation_attempted}`",
        f"- Commit hash: `{report.commit_hash or 'none'}`",
        f"- Reported at: `{report.reported_at.isoformat() if report.reported_at else 'none'}`",
        "",
        "## Summary",
        "",
        report.summary or "No summary recorded.",
        "",
    ]
    _append_list_section(lines, "Changed Files", report.changed_files)
    _append_list_section(lines, "Validation Results", report.validation_results)
    _append_list_section(lines, "Tests Run", report.tests_run)
    _append_list_section(lines, "Commands Run", report.commands_run)
    _append_list_section(lines, "Safety Warnings", report.safety_warnings)
    _append_list_section(lines, "Blockers", report.blockers)
    _append_list_section(lines, "Follow-Up Needed", report.follow_up_needed)
    _append_list_section(lines, "Notes", report.notes)
    if validation:
        _append_list_section(lines, "Import Warnings", validation.warnings)
    lines.extend(
        [
            "## Safety Note",
            "",
            "This imported report is worker-provided evidence only. Devo did not run Codex, execute target commands, verify validation, mark queue/task completion, commit, push, or modify the target repository during import.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_codex_worker_review_markdown(review: WorkerReview) -> str:
    lines = [
        f"# Codex Worker Review: {review.worker_run_id}",
        "",
        f"- Project: `{review.project}`",
        f"- Review id: `{review.review_id}`",
        f"- Review status: `{review.review_status}`",
        f"- Reviewer: `{review.reviewer or 'none'}`",
        f"- Source handoff: `{review.source_handoff_id or 'none'}`",
        f"- Source queue: `{review.source_queue_id or 'none'}`",
        f"- Source queue item: `{review.source_queue_item_id or 'none'}`",
        f"- Source task: `{review.source_task_id or 'none'}`",
        f"- Source report path: `{review.source_report_path or 'none'}`",
        f"- Validation status: `{review.validation_evidence.validation_status}`",
        f"- Created: `{review.created_at.isoformat()}`",
        f"- Updated: `{review.updated_at.isoformat()}`",
        "",
        "## Decision Note",
        "",
        review.decision_note or "No decision recorded yet.",
        "",
        "## Validation Evidence",
        "",
        review.validation_evidence.validation_summary or "No validation summary recorded yet.",
        "",
    ]
    _append_list_section(lines, "Commands Reported", review.validation_evidence.commands_reported)
    _append_list_section(lines, "Tests Reported", review.validation_evidence.tests_reported)
    _append_list_section(lines, "Evidence Paths", review.validation_evidence.evidence_paths)
    _append_list_section(lines, "Validation Warnings", review.validation_evidence.warnings)
    _append_list_section(lines, "Acceptance Criteria Review", review.acceptance_criteria_review)
    _append_list_section(lines, "Changed Files Review", review.changed_files_review)
    _append_list_section(lines, "Safety Review", review.safety_review)
    _append_list_section(lines, "Follow-Up Items", review.follow_up_items)
    lines.extend(
        [
            "## Next Action",
            "",
            review.next_action or "No next action recorded.",
            "",
            "## Safety Note",
            "",
            "This review is workspace-only evidence. It does not run validation, complete queue/task state, commit, push, or modify the target repository.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_codex_worker_run_markdown(worker_run: WorkerRun) -> str:
    lines = [
        f"# Codex Worker Run: {worker_run.worker_run_id}",
        "",
        f"- Project: `{worker_run.project}`",
        f"- Worker type: `{worker_run.worker_type}`",
        f"- Mode: `{worker_run.mode}`",
        f"- Status: `{worker_run.status}`",
        f"- Title: {worker_run.title}",
        f"- Target repo path: `{worker_run.target_repo_path}`",
        f"- Prompt path: `{worker_run.prompt_path}`",
        f"- Transcript path: `{worker_run.transcript_path or 'none'}`",
        f"- Report path: `{worker_run.report_path or 'none'}`",
        f"- Execution exit code: `{worker_run.execution_exit_code if worker_run.execution_exit_code is not None else 'none'}`",
        f"- Execution command label: `{worker_run.execution_command_label or 'none'}`",
        f"- Execution started by: `{worker_run.execution_started_by or 'none'}`",
        f"- Execution log path: `{worker_run.execution_log_path or 'none'}`",
        f"- Execution stderr log path: `{worker_run.execution_stderr_log_path or 'none'}`",
        f"- Source handoff: `{worker_run.source_handoff_id or 'none'}`",
        f"- Source queue: `{worker_run.source_queue_id or 'none'}`",
        f"- Source queue item: `{worker_run.source_queue_item_id or 'none'}`",
        f"- Source batch: `{worker_run.source_batch_id or 'none'}`",
        f"- Source task: `{worker_run.source_task_id or 'none'}`",
        f"- Created: `{worker_run.created_at.isoformat()}`",
        f"- Updated: `{worker_run.updated_at.isoformat()}`",
        f"- Started: `{worker_run.started_at.isoformat() if worker_run.started_at else 'none'}`",
        f"- Completed: `{worker_run.completed_at.isoformat() if worker_run.completed_at else 'none'}`",
        "",
        "## Status Note",
        "",
        worker_run.status_note or "No status note recorded.",
        "",
        "## Next Action",
        "",
        worker_run.next_action or "No next action recorded.",
        "",
    ]
    _append_list_section(lines, "Allowed Scope", worker_run.allowed_scope)
    _append_list_section(lines, "Forbidden Scope", worker_run.forbidden_scope)
    _append_list_section(lines, "Validation Expectations", worker_run.validation_expectations)
    _append_list_section(lines, "Safety Boundaries", worker_run.safety_boundaries)
    lines.extend(
        [
            "## Worker Report Metadata",
            "",
            f"- Report status: `{worker_run.report.report_status}`",
            f"- Reported commit hash: `{worker_run.report.reported_commit_hash or 'none'}`",
            f"- Imported at: `{worker_run.report.imported_at.isoformat() if worker_run.report.imported_at else 'none'}`",
            "",
        ]
    )
    _append_list_section(lines, "Reported Changed Files", worker_run.report.reported_changed_files)
    _append_list_section(lines, "Reported Validation", worker_run.report.reported_validation)
    _append_list_section(lines, "Safety Warnings", worker_run.report.safety_warnings)
    _append_list_section(lines, "Reviewer Notes", worker_run.report.reviewer_notes)
    lines.extend(
        [
            "## Safety Note",
            "",
            "This worker run is a workspace-only tracking record. A supervised execution may launch Codex only through the explicit guarded execute command. Devo does not trust worker output, mark queue/task completion, run validation, commit, push, or modify delivery state automatically.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_codex_handoff_prompt(
    project_name: str,
    *,
    handoff_type: str,
    title: str,
    workspace_root: Path | None = None,
    queue: ExecutionQueue | None = None,
    queue_item: QueueItem | None = None,
    task: BacklogTask | None = None,
    batch: ProjectBatch | None = None,
    tasks: list[BacklogTask] | None = None,
) -> str:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    selected_tasks = tasks or ([task] if task else [])
    lane = queue_item.lane if queue_item else (task.lane if task else _summarize_batch_dict(batch.lane_summary if batch else {}, "unknown"))
    risk = queue_item.risk_level if queue_item else (task.risk_level if task else _summarize_batch_dict(batch.risk_summary if batch else {}, "unknown"))
    dependencies = queue_item.dependencies if queue_item else (task.dependencies if task else (batch.dependencies if batch else []))
    acceptance = queue_item.acceptance_criteria if queue_item else (task.acceptance_criteria if task else _batch_acceptance(batch, selected_tasks))
    validation = queue_item.validation_expectations if queue_item else (task.validation_expectations if task else _batch_validation(batch, selected_tasks))
    allowed_scope = task.allowed_scope if task else _collect_task_scope(selected_tasks, "allowed")
    forbidden_scope = task.forbidden_scope if task else _collect_task_scope(selected_tasks, "forbidden")
    lines = [
        f"# Codex Handoff: {title}",
        "",
        "Continue DevOrchestrator-managed project work using this generated Devo handoff prompt.",
        "",
        "## Project",
        "",
        f"- Project: `{project_name}`",
        f"- Target repo path: `{registration.path}`",
        f"- Handoff type: `{handoff_type}`",
        f"- Lane: `{lane}`",
        f"- Risk level: `{risk}`",
        "",
        "## Devo Context",
        "",
        "- Devo is the workflow controller for planning, scope, queue state, validation records, and delivery reports.",
        "- This prompt is a handoff artifact only. Devo is not invoking Codex or an AI API automatically.",
        "- Execute only the selected task or approved batch scope described below.",
        "",
    ]
    if queue:
        lines.extend(
            [
                "## Source Queue",
                "",
                f"- Queue id: `{queue.queue_id}`",
                f"- Queue status: `{queue.status}`",
                f"- Source batch: `{queue.source_batch_id}`",
                f"- Current item: `{queue.current_item_id or 'none'}`",
                "",
            ]
        )
    if queue_item:
        lines.extend(
            [
                "## Queue Item",
                "",
                f"- Item id: `{queue_item.item_id}`",
                f"- Task id: `{queue_item.task_id}`",
                f"- Title: {queue_item.title}",
                f"- Status: `{queue_item.status}`",
                "",
            ]
        )
    if batch:
        lines.extend(
            [
                "## Source Batch",
                "",
                f"- Batch id: `{batch.batch_id}`",
                f"- Title: {batch.title}",
                f"- Status: `{batch.status}`",
                f"- Approval status: `{batch.approval_status}`",
                f"- Task count: `{batch.task_count}`",
                "",
            ]
        )
        if batch.task_snapshots:
            lines.extend(["### Batch Tasks", ""])
            for snapshot in batch.task_snapshots:
                lines.append(f"- `{snapshot.task_id}` {snapshot.title} ({snapshot.lane}, {snapshot.risk_level})")
            lines.append("")
    if task:
        lines.extend(_task_prompt_section(task))
    elif selected_tasks:
        for selected in selected_tasks:
            lines.extend(_task_prompt_section(selected))
    lines.extend(
        [
            "## Dependencies",
            "",
            *_bullet_lines(dependencies, "No dependencies recorded."),
            "",
            "## Acceptance Criteria",
            "",
            *_bullet_lines(acceptance, "No acceptance criteria recorded."),
            "",
            "## Validation Expectations",
            "",
            *_bullet_lines(validation, "No validation expectations recorded. Use the project's approved validation method only."),
            "",
            "## Allowed Scope",
            "",
            *_bullet_lines(allowed_scope, "Only the task or batch scope described in this handoff."),
            "",
            "## Forbidden Scope",
            "",
            *_bullet_lines(
                forbidden_scope,
                "Do not modify unrelated files, generated artifacts, secrets, local settings, backups, database files, migrations, or scripts.",
            ),
            "",
            "## Safety Boundaries",
            "",
            "- Do not exceed this task/batch scope.",
            "- Do not touch PersonalOS unless the selected project is PersonalOS and the task explicitly says so.",
            "- Do not commit generated workspace artifacts.",
            "- Do not stage workspace/, ui/node_modules/, ui/dist/, .venv/, .env, .pytest_cache/, or pt-* folders.",
            "- Do not run backup/restore, scheduler modification, destructive commands, or target project commands unless explicitly approved for this handoff.",
            "- Do not add AI API/model integration or invoke Codex CLI automation automatically.",
            "- Ask for explicit trusted approval if a safety gate blocks the edit.",
            "",
            "## Required Validation Instructions",
            "",
            "- Run only validation that is approved for this task/batch.",
            "- Record skipped validation honestly when approval is absent or unsafe.",
            "- Run diff checks before staging if source files change.",
            "- Do not fabricate validation, review, audit, commit, or push evidence.",
            "",
            "## Expected Final Report",
            "",
            "- Changed files",
            "- Implementation summary",
            "- Validation performed and results",
            "- Devo artifacts generated or updated",
            "- Commit hash and push result, if delivery is approved",
            "- Final source repo status",
            "- Confirmation generated workspace artifacts were not committed",
            "",
        ]
    )
    return "\n".join(lines)


def render_execution_queue_markdown(queue: ExecutionQueue) -> str:
    lines = [
        f"# {queue.title}",
        "",
        f"- Project: `{queue.project}`",
        f"- Queue id: `{queue.queue_id}`",
        f"- Source batch: `{queue.source_batch_id}`",
        f"- Status: `{queue.status}`",
        f"- Current item: `{queue.current_item_id or 'none'}`",
        f"- Items: `{queue.item_count}`",
        f"- Pending: `{queue.pending_count}`",
        f"- Running: `{queue.running_count}`",
        f"- Completed: `{queue.completed_count}`",
        f"- Blocked: `{queue.blocked_count}`",
        f"- Failed: `{queue.failed_count}`",
        f"- Pause reason: `{queue.pause_reason or 'none'}`",
        f"- Resume hint: {queue.resume_hint or 'none'}",
        f"- Created: `{queue.created_at.isoformat()}`",
        f"- Updated: `{queue.updated_at.isoformat()}`",
        "",
        "## Items",
        "",
    ]
    if not queue.items:
        lines.extend(["No queue items recorded.", ""])
    for item in queue.items:
        lines.extend(
            [
                f"### {item.item_id}: {item.title}",
                "",
                f"- Task: `{item.task_id}`",
                f"- Status: `{item.status}`",
                f"- Lane: `{item.lane}`",
                f"- Risk: `{item.risk_level}`",
                f"- Dependencies: `{', '.join(item.dependencies) if item.dependencies else 'none'}`",
                f"- Started: `{item.started_at.isoformat() if item.started_at else 'none'}`",
                f"- Completed: `{item.completed_at.isoformat() if item.completed_at else 'none'}`",
                "",
            ]
        )
        _append_list_section(lines, "Acceptance Criteria", item.acceptance_criteria)
        _append_list_section(lines, "Validation Expectations", item.validation_expectations)
        _append_list_section(lines, "Notes", item.notes)
    lines.extend(
        [
            "## Safety Note",
            "",
            "Execution queue state is tracking only. Devo does not run Codex, run validation, commit, push, or modify target repositories from this queue.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_queue_worker_run_markdown(run: QueueWorkerRun) -> str:
    lines = [
        f"# Queue Worker Run {run.run_id}",
        "",
        f"- Project: `{run.project}`",
        f"- Run id: `{run.run_id}`",
        f"- Policy id: `{run.policy_id}`",
        f"- Batch id: `{run.batch_id or 'none'}`",
        f"- Queue id: `{run.queue_id or 'none'}`",
        f"- Selected queue item: `{run.selected_queue_item_id or 'none'}`",
        f"- Selected task: `{run.selected_task_id or 'none'}`",
        f"- Handoff id: `{run.selected_handoff_id or 'none'}`",
        f"- Worker run id: `{run.selected_worker_run_id or 'none'}`",
        f"- Mode: `{run.mode}`",
        f"- Status: `{run.status}`",
        f"- Started: `{run.started_at.isoformat()}`",
        f"- Completed: `{run.completed_at.isoformat() if run.completed_at else 'none'}`",
        f"- Updated: `{run.updated_at.isoformat()}`",
        f"- Approver: `{run.approver or 'none'}`",
        f"- Retry of: `{run.retry_of or 'none'}`",
        f"- Pause reason: `{run.pause_reason or 'none'}`",
        f"- Failure reason: `{run.failure_reason or 'none'}`",
        f"- Cancel reason: `{run.cancel_reason or 'none'}`",
        "",
        "## Policy Check",
        "",
        run.policy_check_summary or "No policy check summary recorded.",
        "",
        "## Selection",
        "",
        run.selection_reason or "No queue item selected.",
        "",
    ]
    _append_list_section(lines, "Steps Run", run.steps_run)
    _append_list_section(lines, "Blockers", run.blockers)
    _append_list_section(lines, "Warnings", run.warnings)
    _append_list_section(lines, "Skipped Queue Items", run.skipped_queue_item_summaries)
    lines.extend(
        [
            "## Next Action",
            "",
            run.next_action or "Review the queue-worker run.",
            "",
            "## Safety Note",
            "",
            "Queue worker v1 prepares and controls the approved queue path. It does not execute Codex automatically, complete tasks, run validation, create delivery requests, commit, push, or modify target repositories.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_project_batch_markdown(batch: ProjectBatch) -> str:
    lines = [
        f"# {batch.title}",
        "",
        f"- Project: `{batch.project}`",
        f"- Batch id: `{batch.batch_id}`",
        f"- Status: `{batch.status}`",
        f"- Approval status: `{batch.approval_status}`",
        f"- Review status: `{batch.review_status}`",
        f"- Source backlog: `{batch.source_backlog_reference}`",
        f"- Task count: `{batch.task_count}`",
        f"- Completed tasks: `{batch.completed_task_count}`",
        f"- Blocked tasks: `{batch.blocked_task_count}`",
        f"- Created: `{batch.created_at.isoformat()}`",
        f"- Updated: `{batch.updated_at.isoformat()}`",
        "",
        "## Summary",
        "",
        batch.summary or "No summary recorded.",
        "",
    ]
    _append_mapping_section(lines, "Risk Summary", batch.risk_summary)
    _append_mapping_section(lines, "Lane Summary", batch.lane_summary)
    _append_list_section(lines, "Dependencies", batch.dependencies)
    _append_list_section(lines, "Dependency Warnings", batch.dependency_warnings)
    _append_list_section(lines, "Review Notes", batch.review_notes)
    lines.extend(["## Task Snapshots", ""])
    if not batch.task_snapshots:
        lines.extend(["No tasks recorded.", ""])
    for task in batch.task_snapshots:
        lines.extend(
            [
                f"### {task.task_id}: {task.title}",
                "",
                f"- Status: `{task.status}`",
                f"- Lane: `{task.lane}`",
                f"- Risk: `{task.risk_level}`",
                f"- Dependencies: `{', '.join(task.dependencies) if task.dependencies else 'none'}`",
                f"- Acceptance criteria: {task.acceptance_criteria_summary or 'none'}",
                f"- Validation: {task.validation_expectations_summary or 'none'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Note",
            "",
            "Planning approval only: batch approval does not approve implementation execution. Execution queue, Codex automation, implementation approval, validation, commit, and push are future workflow steps.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_batch_approval_markdown(approval: BatchApproval) -> str:
    lines = [
        f"# Batch Approval: {approval.batch_id}",
        "",
        f"- Project: `{approval.project}`",
        f"- Batch id: `{approval.batch_id}`",
        f"- Approval status: `{approval.approval_status}`",
        f"- Review status: `{approval.review_status}`",
        f"- Requested at: `{approval.requested_at.isoformat() if approval.requested_at else 'none'}`",
        f"- Reviewed at: `{approval.reviewed_at.isoformat() if approval.reviewed_at else 'none'}`",
        f"- Approved at: `{approval.approved_at.isoformat() if approval.approved_at else 'none'}`",
        f"- Rejected at: `{approval.rejected_at.isoformat() if approval.rejected_at else 'none'}`",
        f"- Reviewer: `{approval.reviewer or 'none'}`",
        f"- Approver: `{approval.approver or 'none'}`",
        f"- Task count: `{approval.task_count}`",
        f"- High-risk tasks: `{approval.high_risk_task_count}`",
        f"- Blocked dependencies: `{approval.blocked_dependency_count}`",
        f"- Updated: `{approval.updated_at.isoformat()}`",
        "",
        "## Decision Note",
        "",
        approval.decision_note or "No decision note recorded.",
        "",
    ]
    _append_mapping_section(lines, "Risk Summary", approval.risk_summary)
    _append_mapping_section(lines, "Lane Summary", approval.lane_summary)
    _append_list_section(lines, "Scope Summary", approval.scope_summary)
    _append_list_section(lines, "Validation Summary", approval.validation_summary)
    _append_list_section(lines, "Dependency Warnings", approval.dependency_warnings)
    _append_list_section(lines, "Review Notes", approval.review_notes)
    lines.extend(
        [
            "## Next Action",
            "",
            approval.next_action or "No next action recorded.",
            "",
            "## Safety Note",
            "",
            "Batch approval is planning approval only. It does not create a queue, run Codex, execute target commands, run validation, commit, push, restore backups, or modify target repositories.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_execution_policy_markdown(policy: BatchExecutionPolicy) -> str:
    lines = [
        f"# Execution Policy: {policy.policy_id}",
        "",
        f"- Project: `{policy.project}`",
        f"- Policy id: `{policy.policy_id}`",
        f"- Batch id: `{policy.batch_id}`",
        f"- Queue id: `{policy.queue_id or 'none'}`",
        f"- Title: {policy.title}",
        f"- Status: `{policy.status}`",
        f"- Risk level: `{policy.risk_level}`",
        f"- Auto delivery allowed: `{policy.auto_delivery_allowed}`",
        f"- Auto push allowed: `{policy.auto_push_allowed}`",
        f"- Requires worker review: `{policy.requires_worker_review}`",
        f"- Requires validation evidence: `{policy.requires_validation_evidence}`",
        f"- Max tasks: `{policy.max_tasks}`",
        f"- Max tasks per run: `{policy.max_tasks_per_run}`",
        f"- Max changed files per task: `{policy.max_changed_files_per_task}`",
        f"- Max total changed files: `{policy.max_total_changed_files}`",
        f"- Requested at: `{policy.requested_at.isoformat() if policy.requested_at else 'none'}`",
        f"- Approved at: `{policy.approved_at.isoformat() if policy.approved_at else 'none'}`",
        f"- Rejected at: `{policy.rejected_at.isoformat() if policy.rejected_at else 'none'}`",
        f"- Expires at: `{policy.expires_at.isoformat() if policy.expires_at else 'none'}`",
        f"- Approver: `{policy.approver or 'none'}`",
        f"- Reviewer: `{policy.reviewer or 'none'}`",
        f"- Decision note: {policy.decision_note or 'none'}",
        f"- Created: `{policy.created_at.isoformat()}`",
        f"- Updated: `{policy.updated_at.isoformat()}`",
        "",
    ]
    _append_list_section(lines, "Allowed Tasks", policy.allowed_task_ids)
    _append_list_section(lines, "Allowed Queue Items", policy.allowed_queue_item_ids)
    _append_list_section(lines, "Allowed File Patterns", policy.allowed_file_patterns)
    _append_list_section(lines, "Forbidden File Patterns", policy.forbidden_file_patterns)
    _append_list_section(lines, "Validation Commands", policy.validation_commands)
    _append_list_section(lines, "Pause Conditions", policy.pause_conditions)
    _append_list_section(lines, "Notes", policy.notes)
    lines.extend(
        [
            "## Safety Note",
            "",
            "This is a bounded approval contract only. It does not execute queue items, run Codex, run validation, create runner requests, commit, push, or bypass delivery safety gates.",
            "",
            "## Next Action",
            "",
            policy.next_action or "Review policy status.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_backlog_refinement_prompt(
    project_name: str,
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint,
    backlog: ProjectBacklog,
) -> str:
    example = _with_backlog_counts(
        ProjectBacklog(
            project=project_name,
            title="Refined implementation backlog",
            blueprint_reference=backlog.blueprint_reference,
            status="draft",
            tasks=[
                BacklogTask(
                    id="T001",
                    title="Small implementation task",
                    summary="One implementation-ready task description.",
                    milestone_id=blueprint.milestones[0].id if blueprint.milestones else None,
                    epic_id=blueprint.epics[0].id if blueprint.epics else None,
                    lane="small-feature",
                    risk_level="medium",
                    status="draft",
                    dependencies=[],
                    acceptance_criteria=["Concrete user-visible or technical acceptance criterion."],
                    validation_expectations=["Registered validation command or manual validation evidence needed."],
                    allowed_scope=["Specific files or areas allowed for this task."],
                    forbidden_scope=["DB/migrations/secrets/scripts/backups unless explicitly approved."],
                    notes=["Planning only; not approved for implementation."],
                    source="codex-refinement",
                )
            ],
        )
    )
    return "\n".join(
        [
            f"# Backlog Refinement Handoff: {project_name}",
            "",
            "You are Codex acting as a planning worker. This is planning only.",
            "",
            "## Hard Rules",
            "",
            "- Do not modify source code.",
            "- Do not run build, test, restore, backup, migration, database, scheduler, app, or external API commands.",
            "- Do not call AI/model APIs.",
            "- Preserve Devo's safety model, approvals, validation evidence, and target repository boundaries.",
            "- Do not suggest unapproved risky work as ordinary low-risk tasks.",
            "- Refine the backlog into small implementation-ready tasks suitable for later work packages/batches.",
            "",
            "## Project Brief Summary",
            "",
            brief.summary if brief else "No Project Brief artifact is available.",
            "",
            "## Blueprint",
            "",
            render_project_blueprint_markdown(blueprint).strip(),
            "",
            "## Current Backlog",
            "",
            render_project_backlog_markdown(backlog).strip(),
            "",
            "## Lane Guidance",
            "",
            _lane_summary(),
            "",
            "## Risk Guidance",
            "",
            "- low: docs, display-only UI, tests, tiny scoped cleanup",
            "- medium: ordinary source changes with bounded behavior impact",
            "- high: build/test/run, config, scripts, target repo validation, or broader source behavior",
            "- critical: destructive, secrets, DB migrations/data, restore/delete, scheduler, deployment, or unbounded execution",
            "",
            "## Required Output",
            "",
            "Return only a Devo-compatible refined backlog JSON object. Do not wrap it in Markdown.",
            "",
            "Required task fields: id, title, summary, milestone_id, epic_id, lane, risk_level, status, dependencies, acceptance_criteria, validation_expectations, allowed_scope, forbidden_scope, notes, source, created_at, updated_at.",
            "",
            "Use task statuses from: draft, ready, approved, in_progress, blocked, completed, superseded.",
            "Use backlog status draft unless a human explicitly asks for reviewed/approved.",
            "",
            "## Output JSON Example",
            "",
            "```json",
            example.model_dump_json(indent=2),
            "```",
            "",
        ]
    )


def render_project_brief_markdown(brief: ProjectBrief, source_text: str | None = None) -> str:
    lines = [
        f"# {brief.title}",
        "",
        f"- Project: `{brief.project}`",
        f"- Status: `{brief.status}`",
        f"- Created: `{brief.created_at.isoformat()}`",
        f"- Updated: `{brief.updated_at.isoformat()}`",
        "",
        "## Summary",
        "",
        brief.summary or "No summary recorded.",
        "",
        "## Problem Statement",
        "",
        brief.problem_statement or "No problem statement recorded.",
        "",
    ]
    _append_list_section(lines, "Goals", brief.goals)
    _append_list_section(lines, "Non-Goals", brief.non_goals)
    _append_list_section(lines, "Target Users", brief.target_users)
    _append_list_section(lines, "Constraints", brief.constraints)
    _append_list_section(lines, "Assumptions", brief.assumptions)
    _append_list_section(lines, "Risks", brief.risks)
    _append_list_section(lines, "Tech Stack Notes", brief.tech_stack_notes)
    _append_list_section(lines, "Validation Expectations", brief.validation_expectations)
    _append_list_section(lines, "Source Notes", brief.source_notes)
    if source_text:
        lines.extend(["## Original Brief Text", "", "```text", source_text.rstrip(), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def render_project_blueprint_markdown(blueprint: ProjectBlueprint) -> str:
    lines = [
        f"# {blueprint.title}",
        "",
        f"- Project: `{blueprint.project}`",
        f"- Status: `{blueprint.status}`",
        f"- Brief reference: `{blueprint.brief_reference}`",
        f"- Created: `{blueprint.created_at.isoformat()}`",
        f"- Updated: `{blueprint.updated_at.isoformat()}`",
        "",
        "## Vision Summary",
        "",
        blueprint.vision_summary or "No vision summary recorded.",
        "",
        "## Milestones",
        "",
    ]
    if blueprint.milestones:
        for milestone in blueprint.milestones:
            lines.extend(
                [
                    f"### {milestone.id}: {milestone.title}",
                    "",
                    f"- Status: `{milestone.status}`",
                    f"- Summary: {milestone.summary}",
                    f"- Target outcome: {milestone.target_outcome}",
                    "",
                ]
            )
    else:
        lines.extend(["No milestones recorded.", ""])
    lines.extend(["## Epics", ""])
    if blueprint.epics:
        for epic in blueprint.epics:
            lines.extend(
                [
                    f"### {epic.id}: {epic.title}",
                    "",
                    f"- Status: `{epic.status}`",
                    f"- Milestone: `{epic.milestone_id or 'none'}`",
                    f"- Summary: {epic.summary}",
                    "",
                ]
            )
    else:
        lines.extend(["No epics recorded.", ""])
    _append_list_section(lines, "Architecture Notes", blueprint.architecture_notes)
    _append_list_section(lines, "Risk Summary", blueprint.risk_summary)
    _append_list_section(lines, "Validation Strategy", blueprint.validation_strategy)
    _append_list_section(lines, "Open Questions", blueprint.open_questions)
    return "\n".join(lines).rstrip() + "\n"


def render_project_backlog_markdown(backlog: ProjectBacklog) -> str:
    lines = [
        f"# {backlog.title}",
        "",
        f"- Project: `{backlog.project}`",
        f"- Status: `{backlog.status}`",
        f"- Blueprint reference: `{backlog.blueprint_reference}`",
        f"- Task count: `{backlog.task_count}`",
        f"- Ready tasks: `{backlog.ready_task_count}`",
        f"- Blocked tasks: `{backlog.blocked_task_count}`",
        f"- Completed tasks: `{backlog.completed_task_count}`",
        f"- Created: `{backlog.created_at.isoformat()}`",
        f"- Updated: `{backlog.updated_at.isoformat()}`",
        "",
        "## Starter Backlog Guidance",
        "",
        "This is a deterministic starter backlog. It is not implementation-ready by default.",
        "",
        "Before using it for real implementation work:",
        "",
        f"- Run `devo project backlog-prompt --project {backlog.project}` to generate a Codex/manual planning handoff.",
        "- Use `devo project backlog-import --project <project> --file <refined-backlog.json>` to import a refined backlog.",
        "- Review and approve the refined backlog before creating or approving batches.",
        "",
        "## Tasks",
        "",
    ]
    if not backlog.tasks:
        lines.extend(["No tasks recorded.", ""])
    for task in backlog.tasks:
        lines.extend(
            [
                f"### {task.id}: {task.title}",
                "",
                f"- Status: `{task.status}`",
                f"- Lane: `{task.lane}`",
                f"- Risk: `{task.risk_level}`",
                f"- Milestone: `{task.milestone_id or 'none'}`",
                f"- Epic: `{task.epic_id or 'none'}`",
                f"- Source: {task.source}",
                "",
                task.summary,
                "",
            ]
        )
        _append_list_section(lines, "Acceptance Criteria", task.acceptance_criteria)
        _append_list_section(lines, "Validation Expectations", task.validation_expectations)
        _append_list_section(lines, "Allowed Scope", task.allowed_scope)
        _append_list_section(lines, "Forbidden Scope", task.forbidden_scope)
        _append_list_section(lines, "Dependencies", task.dependencies)
        _append_list_section(lines, "Notes", task.notes)
    return "\n".join(lines).rstrip() + "\n"


def _default_backlog_tasks(blueprint: ProjectBlueprint, now: datetime) -> list[BacklogTask]:
    tasks: list[BacklogTask] = []
    sources: list[tuple[str, str | None, str | None, str]] = []
    for epic in blueprint.epics:
        sources.append((epic.title, epic.milestone_id, epic.id, epic.summary))
    if not sources:
        for milestone in blueprint.milestones:
            sources.append((milestone.title, milestone.id, None, milestone.summary))
    if not sources:
        sources.append(("Planning Follow-Up", None, None, blueprint.vision_summary))

    for index, (title, milestone_id, epic_id, summary) in enumerate(sources, start=1):
        tasks.append(
            BacklogTask(
                id=f"T{index:03d}",
                title=_short_title(title, fallback=f"Task {index}"),
                summary=summary,
                milestone_id=milestone_id,
                epic_id=epic_id,
                lane="small-feature",
                risk_level="medium",
                status="draft",
                acceptance_criteria=[
                    "Refine this placeholder into concrete implementation criteria during TASK-DEVO-076 planning handoff.",
                ],
                validation_expectations=blueprint.validation_strategy[:5] or ["Define validation before implementation."],
                allowed_scope=["Planning placeholder only; implementation scope must be refined before batch approval."],
                forbidden_scope=[
                    "Do not execute implementation from this placeholder.",
                    "Do not run AI/API/Codex automation from backlog creation.",
                ],
                notes=["Deterministic starter task generated from the current blueprint."],
                source=f"blueprint:{epic_id or milestone_id or 'overview'}",
                created_at=now,
                updated_at=now,
            )
        )
    return tasks


def _with_backlog_counts(backlog: ProjectBacklog) -> ProjectBacklog:
    ready = sum(1 for task in backlog.tasks if task.status in {"ready", "approved"})
    blocked = sum(1 for task in backlog.tasks if task.status == "blocked")
    completed = sum(1 for task in backlog.tasks if task.status == "completed")
    return backlog.model_copy(
        update={
            "task_count": len(backlog.tasks),
            "ready_task_count": ready,
            "blocked_task_count": blocked,
            "completed_task_count": completed,
        }
    )


def _safe_import_task_status(status: str) -> str:
    if status in {"completed", "superseded"}:
        return status
    return "draft"


def _normalize_task_ids(task_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in task_ids:
        for item in raw.split(","):
            cleaned = item.strip().upper()
            if cleaned:
                normalized.append(cleaned)
    return normalized


def _normalize_task_id(task_id: str) -> str:
    return task_id.strip().upper()


def _normalize_batch_id(batch_id: str) -> str:
    cleaned = batch_id.strip()
    if cleaned.lower().startswith("batch-"):
        cleaned = cleaned[6:]
    return cleaned.upper()


def _normalize_policy_id(policy_id: str) -> str:
    cleaned = policy_id.strip()
    if cleaned.lower().startswith("execution-policy-"):
        cleaned = cleaned[17:]
    if cleaned.lower().startswith("policy-"):
        cleaned = cleaned[7:]
    return cleaned.upper()


def _normalize_queue_item_id(item_id: str) -> str:
    return item_id.strip().upper()


def _normalize_queue_id(queue_id: str) -> str:
    cleaned = queue_id.strip()
    if cleaned.lower().startswith("queue-"):
        cleaned = cleaned[6:]
    return cleaned.upper()


def _normalize_handoff_id(handoff_id: str) -> str:
    cleaned = handoff_id.strip()
    if cleaned.lower().startswith("handoff-"):
        cleaned = cleaned[8:]
    return cleaned.upper()


def _normalize_worker_run_id(worker_run_id: str) -> str:
    cleaned = worker_run_id.strip()
    if cleaned.lower().startswith("worker-run-"):
        cleaned = cleaned[11:]
    return cleaned.upper()


def _normalize_queue_worker_run_id(run_id: str) -> str:
    cleaned = run_id.strip()
    if cleaned.lower().startswith("queue-worker-run-"):
        cleaned = cleaned[17:]
    return cleaned.upper()


def _normalize_run_plan_id(plan_id: str) -> str:
    cleaned = plan_id.strip()
    if cleaned.lower().startswith("run-plan-"):
        cleaned = cleaned[9:]
    return cleaned.upper()


def _next_batch_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_batch_id(batch.batch_id) for batch in list_project_batches(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"B{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_queue_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_queue_id(queue.queue_id) for queue in list_execution_queues(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"Q{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_handoff_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_handoff_id(handoff.handoff_id) for handoff in list_codex_handoffs(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"H{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_worker_run_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_worker_run_id(worker.worker_run_id) for worker in list_codex_worker_runs(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"WR{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_run_plan_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_run_plan_id(plan.plan_id) for plan in list_codex_run_plans(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"RP{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_policy_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_policy_id(policy.policy_id) for policy in list_execution_policies(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"POL-{index:04d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_queue_worker_run_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_queue_worker_run_id(run.run_id) for run in list_queue_worker_runs(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"QWR-{index:04d}"
        if candidate not in existing:
            return candidate
        index += 1


def _build_batch_from_tasks(
    *,
    project_name: str,
    batch_id: str,
    title: str,
    tasks: list[BacklogTask],
    backlog: ProjectBacklog,
    source_backlog_reference: str,
    now: datetime,
) -> ProjectBatch:
    task_ids = [task.id for task in tasks]
    dependency_warnings = _batch_dependency_warnings(tasks, backlog)
    return ProjectBatch(
        project=project_name,
        batch_id=batch_id,
        title=title,
        summary=_batch_summary(tasks),
        source_backlog_reference=source_backlog_reference,
        status="draft",
        task_ids=task_ids,
        task_count=len(tasks),
        completed_task_count=sum(1 for task in tasks if task.status == "completed"),
        blocked_task_count=sum(1 for task in tasks if task.status == "blocked"),
        risk_summary=_count_by(tasks, "risk_level"),
        lane_summary=_count_by(tasks, "lane"),
        dependencies=_batch_dependencies(tasks),
        approval_status="not_requested",
        review_notes=[],
        task_snapshots=[_task_snapshot(task) for task in tasks],
        dependency_warnings=dependency_warnings,
        created_at=now,
        updated_at=now,
    )


def _write_project_batch(project_name: str, batch: ProjectBatch, workspace_root: Path | None = None) -> tuple[Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = project_batch_artifact_paths(project_name, batch.batch_id, workspace_root=root)
    _write_model(json_path, batch)
    markdown_path.write_text(render_project_batch_markdown(batch), encoding="utf-8")
    _write_batch_index(project_name, workspace_root=root)
    return json_path, markdown_path


def _write_batch_approval(project_name: str, approval: BatchApproval, workspace_root: Path | None = None) -> tuple[BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batch_approvals_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = batch_approval_artifact_paths(project_name, approval.batch_id, workspace_root=root)
    _write_model(json_path, approval)
    markdown_path.write_text(render_batch_approval_markdown(approval), encoding="utf-8")
    return approval, json_path, markdown_path


def _write_execution_policy(project_name: str, policy: BatchExecutionPolicy, workspace_root: Path | None = None) -> tuple[BatchExecutionPolicy, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.execution_policies_dir.mkdir(parents=True, exist_ok=True)
    if policy.status not in ALLOWED_EXECUTION_POLICY_STATUSES:
        msg = f"Invalid execution policy status: {policy.status}"
        raise ValueError(msg)
    if policy.risk_level not in ALLOWED_RISK_LEVELS:
        msg = f"Invalid execution policy risk level: {policy.risk_level}"
        raise ValueError(msg)
    json_path, markdown_path = execution_policy_artifact_paths(project_name, policy.policy_id, workspace_root=root)
    _write_model(json_path, policy)
    markdown_path.write_text(render_execution_policy_markdown(policy), encoding="utf-8")
    _write_execution_policy_index(project_name, workspace_root=root)
    return policy, json_path, markdown_path


def _write_queue_worker_run(project_name: str, run: QueueWorkerRun, workspace_root: Path | None = None) -> tuple[QueueWorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queue_worker_runs_dir.mkdir(parents=True, exist_ok=True)
    if run.status not in ALLOWED_QUEUE_WORKER_RUN_STATUSES:
        msg = f"Invalid queue worker run status: {run.status}"
        raise ValueError(msg)
    json_path, markdown_path = queue_worker_run_artifact_paths(project_name, run.run_id, workspace_root=root)
    _write_model(json_path, run)
    markdown_path.write_text(render_queue_worker_run_markdown(run), encoding="utf-8")
    _write_queue_worker_run_index(project_name, workspace_root=root)
    return run, json_path, markdown_path


def _write_batch_index(project_name: str, workspace_root: Path | None = None) -> BatchIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)
    batches = list_project_batches(project_name, workspace_root=root)
    entries = [
        BatchIndexEntry(
            batch_id=batch.batch_id,
            title=batch.title,
            status=batch.status,
            task_count=batch.task_count,
            approval_status=batch.approval_status,
            path=str(project_batch_artifact_paths(project_name, batch.batch_id, workspace_root=root)[0]),
            updated_at=batch.updated_at,
        )
        for batch in batches
    ]
    index = BatchIndex(project=project_name, batches=entries, updated_at=datetime.now(UTC))
    _write_model(paths.batch_index_json, index)
    return index


def _write_execution_policy_index(project_name: str, workspace_root: Path | None = None) -> ExecutionPolicyIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.execution_policies_dir.mkdir(parents=True, exist_ok=True)
    policies = list_execution_policies(project_name, workspace_root=root)
    entries = [
        ExecutionPolicyIndexEntry(
            policy_id=policy.policy_id,
            batch_id=policy.batch_id,
            queue_id=policy.queue_id,
            title=policy.title,
            status=policy.status,
            task_count=len(policy.allowed_task_ids),
            auto_delivery_allowed=policy.auto_delivery_allowed,
            auto_push_allowed=policy.auto_push_allowed,
            path=str(execution_policy_artifact_paths(project_name, policy.policy_id, workspace_root=root)[0]),
            updated_at=policy.updated_at,
        )
        for policy in policies
    ]
    index = ExecutionPolicyIndex(project=project_name, policies=entries, updated_at=datetime.now(UTC))
    _write_model(paths.execution_policy_index_json, index)
    return index


def _write_queue_worker_run_index(project_name: str, workspace_root: Path | None = None) -> QueueWorkerRunIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queue_worker_runs_dir.mkdir(parents=True, exist_ok=True)
    runs = list_queue_worker_runs(project_name, workspace_root=root)
    entries = [
        QueueWorkerRunIndexEntry(
            run_id=run.run_id,
            policy_id=run.policy_id,
            batch_id=run.batch_id,
            queue_id=run.queue_id,
            selected_queue_item_id=run.selected_queue_item_id,
            selected_task_id=run.selected_task_id,
            selected_worker_run_id=run.selected_worker_run_id,
            status=run.status,
            path=str(queue_worker_run_artifact_paths(project_name, run.run_id, workspace_root=root)[0]),
            updated_at=run.updated_at,
        )
        for run in runs
    ]
    index = QueueWorkerRunIndex(project=project_name, runs=entries, updated_at=datetime.now(UTC))
    _write_model(paths.queue_worker_run_index_json, index)
    return index


def _write_execution_queue(project_name: str, queue: ExecutionQueue, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queues_dir.mkdir(parents=True, exist_ok=True)
    for item in queue.items:
        if item.status not in ALLOWED_QUEUE_ITEM_STATUSES:
            msg = f"Invalid queue item status: {item.status}"
            raise ValueError(msg)
    queue = _with_queue_counts(queue)
    json_path, markdown_path = queue_artifact_paths(project_name, queue.queue_id, workspace_root=root)
    _write_model(json_path, queue)
    markdown_path.write_text(render_execution_queue_markdown(queue), encoding="utf-8")
    _write_queue_index(project_name, workspace_root=root)
    return queue, json_path, markdown_path


def _write_queue_index(project_name: str, workspace_root: Path | None = None) -> QueueIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queues_dir.mkdir(parents=True, exist_ok=True)
    queues = list_execution_queues(project_name, workspace_root=root)
    entries = [
        QueueIndexEntry(
            queue_id=queue.queue_id,
            title=queue.title,
            source_batch_id=queue.source_batch_id,
            status=queue.status,
            item_count=queue.item_count,
            pending_count=queue.pending_count,
            completed_count=queue.completed_count,
            blocked_count=queue.blocked_count,
            path=str(queue_artifact_paths(project_name, queue.queue_id, workspace_root=root)[0]),
            updated_at=queue.updated_at,
        )
        for queue in queues
    ]
    index = QueueIndex(project=project_name, queues=entries, updated_at=datetime.now(UTC))
    _write_model(paths.queue_index_json, index)
    return index


def _write_codex_handoff(
    project_name: str,
    *,
    handoff_type: str,
    title: str,
    prompt: str,
    workspace_root: Path | None = None,
    source_queue_id: str | None = None,
    source_batch_id: str | None = None,
    source_item_id: str | None = None,
    source_task_id: str | None = None,
) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    normalized_type = handoff_type.strip().lower()
    if normalized_type not in ALLOWED_HANDOFF_TYPES:
        msg = f"Invalid handoff type: {handoff_type}"
        raise ValueError(msg)
    handoff_id = _next_handoff_id(project_name, workspace_root=root)
    _json_path, prompt_path = handoff_artifact_paths(project_name, handoff_id, workspace_root=root)
    now = datetime.now(UTC)
    handoff = CodexHandoff(
        project=project_name,
        handoff_id=handoff_id,
        handoff_type=normalized_type,
        source_queue_id=source_queue_id,
        source_batch_id=source_batch_id,
        source_item_id=source_item_id,
        source_task_id=source_task_id,
        title=title,
        status="draft",
        prompt_path=str(prompt_path),
        created_at=now,
        updated_at=now,
    )
    return _write_codex_handoff_model(project_name, handoff, prompt=prompt, workspace_root=root)


def _write_codex_handoff_model(
    project_name: str,
    handoff: CodexHandoff,
    *,
    prompt: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)
    if handoff.status not in ALLOWED_HANDOFF_STATUSES:
        msg = f"Invalid handoff status: {handoff.status}"
        raise ValueError(msg)
    json_path, prompt_path = handoff_artifact_paths(project_name, handoff.handoff_id, workspace_root=root)
    updated = handoff.model_copy(update={"prompt_path": str(prompt_path), "updated_at": handoff.updated_at})
    _write_model(json_path, updated)
    if prompt is not None:
        prompt_path.write_text(prompt, encoding="utf-8")
    elif not prompt_path.exists():
        prompt_path.write_text(f"# Codex Handoff: {updated.title}\n\nPrompt content is unavailable.\n", encoding="utf-8")
    _write_handoff_index(project_name, workspace_root=root)
    return updated, json_path, prompt_path


def _write_handoff_index(project_name: str, workspace_root: Path | None = None) -> HandoffIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)
    handoffs = []
    for path in sorted(paths.handoffs_dir.glob("handoff-*.json")):
        if path.name == HANDOFF_INDEX_JSON:
            continue
        try:
            handoffs.append(CodexHandoff.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    handoffs = sorted(handoffs, key=lambda item: item.updated_at, reverse=True)
    entries = [
        HandoffIndexEntry(
            handoff_id=handoff.handoff_id,
            handoff_type=handoff.handoff_type,
            title=handoff.title,
            status=handoff.status,
            source_queue_id=handoff.source_queue_id,
            source_batch_id=handoff.source_batch_id,
            source_item_id=handoff.source_item_id,
            source_task_id=handoff.source_task_id,
            prompt_path=handoff.prompt_path,
            updated_at=handoff.updated_at,
        )
        for handoff in handoffs
    ]
    index = HandoffIndex(project=project_name, handoffs=entries, updated_at=datetime.now(UTC))
    _write_model(paths.handoff_index_json, index)
    return index


def _write_worker_run(project_name: str, worker_run: WorkerRun, workspace_root: Path | None = None) -> tuple[WorkerRun, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    if worker_run.worker_type != "codex_cli":
        msg = f"Invalid worker type: {worker_run.worker_type}"
        raise ValueError(msg)
    if worker_run.mode not in ALLOWED_WORKER_RUN_MODES:
        msg = f"Invalid worker run mode: {worker_run.mode}"
        raise ValueError(msg)
    if worker_run.status not in ALLOWED_WORKER_RUN_STATUSES:
        msg = f"Invalid worker run status: {worker_run.status}"
        raise ValueError(msg)
    if worker_run.report.report_status not in ALLOWED_WORKER_REPORT_STATUSES:
        msg = f"Invalid worker report status: {worker_run.report.report_status}"
        raise ValueError(msg)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.codex_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = worker_run_artifact_paths(project_name, worker_run.worker_run_id, workspace_root=root)
    updated = worker_run.model_copy(update={"worker_run_id": _normalize_worker_run_id(worker_run.worker_run_id)})
    _write_model(json_path, updated)
    markdown_path.write_text(render_codex_worker_run_markdown(updated), encoding="utf-8")
    _write_worker_run_index(project_name, workspace_root=root)
    return updated, json_path, markdown_path


def _write_worker_run_index(project_name: str, workspace_root: Path | None = None) -> WorkerRunIndex:
    root = workspace_root or get_workspace_root()
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.codex_dir.mkdir(parents=True, exist_ok=True)
    worker_runs: list[WorkerRun] = []
    for path in sorted(paths.codex_dir.glob("worker-run-*.json")):
        if path.name == WORKER_RUN_INDEX_JSON:
            continue
        try:
            worker_runs.append(WorkerRun.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    worker_runs = sorted(worker_runs, key=lambda item: item.updated_at, reverse=True)
    entries = [
        WorkerRunIndexEntry(
            worker_run_id=worker_run.worker_run_id,
            worker_type=worker_run.worker_type,
            mode=worker_run.mode,
            title=worker_run.title,
            status=worker_run.status,
            source_handoff_id=worker_run.source_handoff_id,
            source_queue_id=worker_run.source_queue_id,
            source_queue_item_id=worker_run.source_queue_item_id,
            source_batch_id=worker_run.source_batch_id,
            source_task_id=worker_run.source_task_id,
            report_status=worker_run.report.report_status,
            next_action=worker_run.next_action,
            path=str(worker_run_artifact_paths(project_name, worker_run.worker_run_id, workspace_root=root)[0]),
            updated_at=worker_run.updated_at,
        )
        for worker_run in worker_runs
    ]
    index = WorkerRunIndex(project=project_name, worker_runs=entries, updated_at=datetime.now(UTC))
    _write_model(paths.worker_run_index_json, index)
    return index


def _write_worker_review(project_name: str, review: WorkerReview, workspace_root: Path | None = None) -> tuple[WorkerReview, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    if review.review_status not in ALLOWED_WORKER_REVIEW_STATUSES:
        msg = f"Invalid worker review status: {review.review_status}"
        raise ValueError(msg)
    if review.validation_evidence.validation_status not in ALLOWED_VALIDATION_EVIDENCE_STATUSES:
        msg = f"Invalid validation evidence status: {review.validation_evidence.validation_status}"
        raise ValueError(msg)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.reviews_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = worker_review_artifact_paths(project_name, review.worker_run_id, workspace_root=root)
    updated = review.model_copy(update={"worker_run_id": _normalize_worker_run_id(review.worker_run_id)})
    _write_model(json_path, updated)
    markdown_path.write_text(render_codex_worker_review_markdown(updated), encoding="utf-8")
    _write_worker_review_index(project_name, workspace_root=root)
    return updated, json_path, markdown_path


def _write_worker_review_index(project_name: str, workspace_root: Path | None = None) -> WorkerReviewIndex:
    root = workspace_root or get_workspace_root()
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.reviews_dir.mkdir(parents=True, exist_ok=True)
    reviews: list[WorkerReview] = []
    for path in sorted(paths.reviews_dir.glob("review-*.json")):
        if path.name == WORKER_REVIEW_INDEX_JSON:
            continue
        try:
            reviews.append(WorkerReview.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    reviews = sorted(reviews, key=lambda item: item.updated_at, reverse=True)
    entries = [
        WorkerReviewIndexEntry(
            review_id=review.review_id,
            worker_run_id=review.worker_run_id,
            review_status=review.review_status,
            validation_status=review.validation_evidence.validation_status,
            reviewer=review.reviewer,
            path=str(worker_review_artifact_paths(project_name, review.worker_run_id, workspace_root=root)[0]),
            updated_at=review.updated_at,
        )
        for review in reviews
    ]
    index = WorkerReviewIndex(project=project_name, reviews=entries, updated_at=datetime.now(UTC))
    _write_model(paths.review_index_json, index)
    return index


def _write_codex_run_plan(project_name: str, plan: CodexRunPlan, workspace_root: Path | None = None) -> tuple[CodexRunPlan, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    if plan.status not in ALLOWED_WORKER_RUN_PLAN_STATUSES:
        msg = f"Invalid run plan status: {plan.status}"
        raise ValueError(msg)
    if plan.approval_status not in ALLOWED_WORKER_RUN_PLAN_APPROVAL_STATUSES:
        msg = f"Invalid run plan approval status: {plan.approval_status}"
        raise ValueError(msg)
    if plan.preflight_status not in ALLOWED_WORKER_PREFLIGHT_STATUSES:
        msg = f"Invalid run plan preflight status: {plan.preflight_status}"
        raise ValueError(msg)
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.run_plans_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = worker_run_plan_artifact_paths(project_name, plan.plan_id, workspace_root=root)
    updated = plan.model_copy(update={"plan_id": _normalize_run_plan_id(plan.plan_id)})
    _write_model(json_path, updated)
    markdown_path.write_text(render_codex_run_plan_markdown(updated), encoding="utf-8")
    _write_codex_run_plan_index(project_name, workspace_root=root)
    return updated, json_path, markdown_path


def _write_codex_run_plan_index(project_name: str, workspace_root: Path | None = None) -> CodexRunPlanIndex:
    root = workspace_root or get_workspace_root()
    paths = worker_artifact_paths(project_name, workspace_root=root)
    paths.run_plans_dir.mkdir(parents=True, exist_ok=True)
    plans: list[CodexRunPlan] = []
    for path in sorted(paths.run_plans_dir.glob("run-plan-*.json")):
        if path.name == WORKER_RUN_PLAN_INDEX_JSON:
            continue
        try:
            plans.append(CodexRunPlan.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    plans = sorted(plans, key=lambda item: item.updated_at, reverse=True)
    entries = [
        CodexRunPlanIndexEntry(
            plan_id=plan.plan_id,
            worker_run_id=plan.worker_run_id,
            handoff_id=plan.handoff_id,
            status=plan.status,
            approval_status=plan.approval_status,
            preflight_status=plan.preflight_status,
            path=str(worker_run_plan_artifact_paths(project_name, plan.plan_id, workspace_root=root)[0]),
            next_action=plan.next_action,
            updated_at=plan.updated_at,
        )
        for plan in plans
    ]
    index = CodexRunPlanIndex(project=project_name, run_plans=entries, updated_at=datetime.now(UTC))
    _write_model(paths.run_plan_index_json, index)
    return index


def _find_handoff_for_queue_item(project_name: str, queue_id: str, item_id: str, workspace_root: Path | None = None) -> CodexHandoff | None:
    for handoff in list_codex_handoffs(project_name, workspace_root=workspace_root):
        if (
            handoff.handoff_type == "queue_next"
            and handoff.source_queue_id == _normalize_queue_id(queue_id)
            and handoff.source_item_id == item_id.strip().upper()
        ):
            return handoff
    return None


def _create_or_reuse_handoff_for_queue_item(project_name: str, queue_id: str, item_id: str, workspace_root: Path | None = None) -> CodexHandoff:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    item = _require_queue_item(queue, item_id)
    existing = _find_handoff_for_queue_item(project_name, queue.queue_id, item.item_id, workspace_root=root)
    if existing:
        return existing
    task = _try_get_backlog_task(project_name, item.task_id, root)
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        queue=queue,
        queue_item=item,
        task=task,
        batch=load_project_batch(project_name, queue.source_batch_id, workspace_root=root),
        workspace_root=root,
    )
    handoff, _json_path, _markdown_path = _write_codex_handoff(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        prompt=prompt,
        source_queue_id=queue.queue_id,
        source_batch_id=queue.source_batch_id,
        source_item_id=item.item_id,
        source_task_id=item.task_id,
        workspace_root=root,
    )
    return handoff


def _select_policy_queue_items(
    project_name: str,
    policy: BatchExecutionPolicy,
    queue: ExecutionQueue,
    workspace_root: Path | None = None,
) -> tuple[list[QueueItem], list[str]]:
    root = workspace_root or get_workspace_root()
    allowed_tasks = {_normalize_task_id(task_id) for task_id in policy.allowed_task_ids}
    allowed_items = {_normalize_queue_item_id(item_id) for item_id in policy.allowed_queue_item_ids}
    eligible: list[QueueItem] = []
    skipped: list[str] = []
    for item in queue.items:
        reason = _queue_worker_item_skip_reason(project_name, policy, item, allowed_tasks, allowed_items, workspace_root=root)
        if reason:
            skipped.append(f"{item.item_id}: {reason}")
            continue
        eligible.append(item)
    return eligible[: max(1, policy.max_tasks_per_run)], skipped


def _queue_worker_item_skip_reason(
    project_name: str,
    policy: BatchExecutionPolicy,
    item: QueueItem,
    allowed_tasks: set[str],
    allowed_items: set[str],
    workspace_root: Path | None = None,
) -> str:
    if _normalize_batch_id(item.batch_id) != _normalize_batch_id(policy.batch_id):
        return f"batch {item.batch_id} is outside policy batch {policy.batch_id}"
    if allowed_tasks and _normalize_task_id(item.task_id) not in allowed_tasks:
        return f"task {item.task_id} is outside allowed_task_ids"
    if allowed_items and _normalize_queue_item_id(item.item_id) not in allowed_items:
        return f"item {item.item_id} is outside allowed_queue_item_ids"
    if item.status in {"completed", "cancelled", "skipped", "superseded"}:
        return f"item status is {item.status}"
    if item.status in {"blocked", "failed", "paused", "waiting_review"}:
        return f"item status {item.status} requires review or manual recovery"
    if item.status not in {"pending", "running"}:
        return f"item status {item.status} is not eligible for queue worker v1"
    if not _try_get_backlog_task(project_name, item.task_id, workspace_root or get_workspace_root()):
        return f"task {item.task_id} is missing from backlog"
    return ""


def _queue_worker_existing_worker_blockers(worker_run: WorkerRun | None, review: WorkerReview | None) -> list[str]:
    blockers: list[str] = []
    if worker_run and worker_run.status in {"failed", "blocked_needs_approval", "cancelled"}:
        blockers.append(f"Existing worker run {worker_run.worker_run_id} has status {worker_run.status}.")
    if review and review.review_status in {"reviewed_needs_changes", "rejected"}:
        blockers.append(f"Existing worker review {review.review_id} has status {review.review_status}.")
    if review and review.validation_evidence.validation_status == "failed":
        blockers.append(f"Existing worker review {review.review_id} has failed validation evidence.")
    return blockers


def _latest_worker_run_for_queue_item(
    project_name: str,
    queue_id: str,
    item_id: str | None,
    workspace_root: Path | None = None,
) -> WorkerRun | None:
    if not item_id:
        return None
    normalized_queue = _normalize_queue_id(queue_id)
    normalized_item = item_id.strip().upper()
    return next(
        (
            worker_run
            for worker_run in list_codex_worker_runs(project_name, workspace_root=workspace_root)
            if worker_run.source_queue_id == normalized_queue and worker_run.source_queue_item_id == normalized_item
        ),
        None,
    )


def _latest_run_plan_for_worker(project_name: str, worker_run_id: str | None, workspace_root: Path | None = None) -> CodexRunPlan | None:
    if not worker_run_id:
        return None
    normalized_worker = _normalize_worker_run_id(worker_run_id)
    return next(
        (plan for plan in list_codex_run_plans(project_name, workspace_root=workspace_root) if plan.worker_run_id == normalized_worker),
        None,
    )


def _select_queue_worker_status_item(queue: ExecutionQueue, item_id: str | None = None) -> tuple[QueueItem | None, str]:
    if item_id:
        return _require_queue_item(queue, item_id), "requested"
    if queue.current_item_id:
        item = _find_queue_item(queue.items, queue.current_item_id)
        if item:
            return item, "current"
    for status in ("running", "waiting_review", "paused", "blocked", "failed"):
        item = next((entry for entry in queue.items if entry.status == status), None)
        if item:
            return item, status
    completed = [entry for entry in queue.items if entry.status == "completed"]
    if completed:
        return sorted(completed, key=lambda entry: entry.completed_at or datetime.min.replace(tzinfo=UTC), reverse=True)[0], "latest_completed"
    pending = next((entry for entry in queue.items if entry.status == "pending"), None)
    if pending:
        return pending, "next_pending"
    return (queue.items[-1], "latest") if queue.items else (None, "none")


def _linked_queue_item(project_name: str, worker_run: WorkerRun, workspace_root: Path | None = None) -> QueueItem | None:
    if not worker_run.source_queue_id or not worker_run.source_queue_item_id:
        return None
    queue = load_execution_queue(project_name, worker_run.source_queue_id, workspace_root=workspace_root)
    if not queue:
        return None
    return _find_queue_item(queue.items, worker_run.source_queue_item_id)


def _update_linked_queue_from_worker_execution(
    project_name: str,
    worker_run: WorkerRun,
    worker_status: str,
    workspace_root: Path | None = None,
) -> None:
    if not worker_run.source_queue_id or not worker_run.source_queue_item_id:
        return
    root = workspace_root or get_workspace_root()
    queue = load_execution_queue(project_name, worker_run.source_queue_id, workspace_root=root)
    if not queue:
        return
    item = _find_queue_item(queue.items, worker_run.source_queue_item_id)
    if not item:
        return
    now = datetime.now(UTC)
    queue_status, item_status, pause_reason, resume_hint = _queue_state_for_worker_status(worker_status, item.item_id)
    notes = _append_note(item.notes, _queue_note_for_worker_status(worker_run.worker_run_id, worker_status), now)
    updated_item = item.model_copy(update={"status": item_status, "notes": notes})
    items = [entry.model_copy() for entry in queue.items]
    _replace_queue_item(items, updated_item)
    updated_queue = _with_queue_counts(
        queue.model_copy(
            update={
                "status": queue_status,
                "items": items,
                "pause_reason": pause_reason,
                "resume_hint": resume_hint,
                "current_item_id": updated_item.item_id,
                "updated_at": now,
            }
        )
    )
    _write_execution_queue(project_name, updated_queue, workspace_root=root)


def _queue_state_for_worker_status(worker_status: str, item_id: str) -> tuple[str, str, str | None, str]:
    if worker_status == "waiting_review":
        return (
            "waiting_review",
            "waiting_review",
            "worker_waiting_review",
            f"Review worker output for {item_id}; complete the item only after human review and validation.",
        )
    if worker_status == "paused_usage_limit":
        return (
            "paused_usage_limit",
            "paused",
            "usage_limit",
            f"Resume when Codex usage resets, then create or execute another worker run for {item_id}.",
        )
    if worker_status == "blocked_needs_approval":
        return (
            "waiting_review",
            "blocked",
            "worker_needs_approval",
            f"Review approval/safety blocker for {item_id} before continuing.",
        )
    if worker_status == "failed":
        return (
            "paused_failure",
            "failed",
            "worker_failed",
            f"Review worker failure for {item_id}; create a new handoff or worker run only after cause is understood.",
        )
    return (
        "waiting_review",
        "waiting_review",
        "worker_review",
        f"Review worker state for {item_id} before continuing.",
    )


def _queue_note_for_worker_status(worker_run_id: str, worker_status: str) -> str:
    return f"Worker run {worker_run_id} ended with status {worker_status}; queue item is not completed automatically."


def _queue_worker_next_action(
    project_name: str,
    queue_id: str,
    item: QueueItem | None,
    worker_run: WorkerRun | None,
    run_plan: CodexRunPlan | None,
) -> str:
    if not item:
        return f"No active queue item found. Inspect the queue with devo project queue-show --project {project_name} --queue {queue_id}."
    if not worker_run:
        return f"Prepare a worker for the item: devo worker codex prepare-next --project {project_name} --queue {queue_id}"
    if not run_plan:
        return f"Create a run plan: devo worker codex run-plan --project {project_name} --run {worker_run.worker_run_id}"
    if run_plan.approval_status != "approved":
        return f"Review and approve the run plan if safe: devo worker codex run-plan-approve --project {project_name} --plan {run_plan.plan_id}"
    if worker_run.execution_exit_code is None:
        return (
            f"Preview or execute the approved worker run: devo worker codex execute-preview --project {project_name} --run {worker_run.worker_run_id} --plan {run_plan.plan_id}"
        )
    if worker_run.status == "waiting_review":
        return (
            f"Review logs and import a worker report, then complete explicitly only if safe: devo project queue-complete-item --project {project_name} --queue {queue_id} --item {item.item_id} --note \"<reviewed result>\""
        )
    return worker_run.next_action or "Review worker and queue status."


def _queue_completion_next_action(
    project_name: str,
    queue_id: str,
    item: QueueItem,
    worker_run: WorkerRun | None,
    review: WorkerReview | None,
    blockers: list[str],
) -> str:
    if item.status == "completed":
        return f"Queue item is already completed. Inspect evidence with devo worker codex flow-summary --project {project_name} --queue {queue_id} --item {item.item_id}."
    if not blockers:
        return (
            f"Completion ready. Complete explicitly with devo project queue-complete-item --project {project_name} "
            f"--queue {queue_id} --item {item.item_id} --note \"<reviewed result>\""
        )
    if not worker_run:
        return f"Inspect queue worker state with devo worker codex queue-status --project {project_name} --queue {queue_id}."
    if not review:
        return f"Create worker review evidence with devo worker codex review-template --project {project_name} --run {worker_run.worker_run_id}."
    if review.review_status == "reviewed_needs_changes":
        return (
            f"Fix or rerun worker output before completion. Consider devo project queue-block-item --project {project_name} "
            f"--queue {queue_id} --item {item.item_id} --note \"<needed changes>\"."
        )
    if review.review_status == "rejected":
        return (
            f"Do not complete this item. Block or replace the worker output with devo project queue-block-item --project {project_name} "
            f"--queue {queue_id} --item {item.item_id} --note \"<rejection reason>\"."
        )
    if review.validation_evidence.validation_status == "failed":
        return f"Validation evidence failed. Fix/re-run worker output or attach updated evidence before queue completion."
    return (
        f"Record reviewed_passed only after independent review: devo worker codex review-record --project {project_name} "
        f"--run {worker_run.worker_run_id} --status reviewed_passed --reviewer \"<name>\" --note \"<note>\"."
    )


def _queue_completion_blocked_message(project_name: str, readiness: QueueItemCompletionReadiness) -> str:
    lines = [
        f"Queue item {readiness.item_id} is not completion-ready.",
        *[f"- {blocker}" for blocker in readiness.blockers],
    ]
    if readiness.linked_worker_run_id:
        lines.extend(
            [
                f"Next: devo worker codex review-template --project {project_name} --run {readiness.linked_worker_run_id}",
                (
                    f"Then: devo worker codex review-record --project {project_name} --run {readiness.linked_worker_run_id} "
                    '--status reviewed_passed --reviewer "<name>" --note "<note>"'
                ),
            ]
        )
    lines.append(readiness.next_action)
    lines.append("Emergency override: rerun with --confirm-without-review and a non-empty --note. This is discouraged.")
    return "\n".join(lines)


def _worker_flow_next_commands(
    project_name: str,
    status: CodexQueueWorkerStatus,
    readiness: QueueItemCompletionReadiness | None,
    plan: CodexRunPlan | None = None,
) -> list[str]:
    if not status.current_item_id:
        return [f"devo project queue-show --project {project_name} --queue {status.queue_id}"]
    if not status.linked_worker_run_id:
        return [f"devo worker codex prepare-next --project {project_name} --queue {status.queue_id}"]
    if not status.linked_run_plan_id:
        return [f"devo worker codex run-plan --project {project_name} --run {status.linked_worker_run_id}"]
    if plan and plan.approval_status != "approved":
        return [
            f"devo worker codex run-plan-show --project {project_name} --plan {status.linked_run_plan_id}",
            f"devo worker codex run-plan-approve --project {project_name} --plan {status.linked_run_plan_id} --note \"<review note>\"",
        ]
    if status.linked_run_plan_status and status.linked_worker_run_status in {"planned", "blocked_needs_approval", "paused_usage_limit"}:
        return [
            f"devo worker codex run-plan-show --project {project_name} --plan {status.linked_run_plan_id}",
            f"devo worker codex execute-preview --project {project_name} --run {status.linked_worker_run_id} --plan {status.linked_run_plan_id}",
        ]
    if status.latest_worker_report_status in {None, "missing"}:
        return [
            f"devo worker codex report-template --project {project_name} --run {status.linked_worker_run_id}",
            f"devo worker codex report-import --project {project_name} --run {status.linked_worker_run_id} --file <filledReportFile>",
        ]
    if status.latest_worker_review_status != "reviewed_passed":
        return [
            f"devo worker codex review-template --project {project_name} --run {status.linked_worker_run_id}",
            f"devo worker codex review-record --project {project_name} --run {status.linked_worker_run_id} --status reviewed_passed --reviewer \"<name>\" --note \"<note>\"",
        ]
    if readiness and readiness.completion_ready:
        return [
            f"devo project queue-complete-item --project {project_name} --queue {status.queue_id} --item {status.current_item_id} --note \"<reviewed result>\""
        ]
    if status.current_item_status == "completed":
        return [f"devo project queue-show --project {project_name} --queue {status.queue_id}"]
    return [status.next_action]


def _worker_review_next_action(project_name: str, worker_run: WorkerRun, review_status: str) -> str:
    if review_status == "draft":
        return f"Fill review evidence, then record a decision with devo worker codex review-record --project {project_name} --run {worker_run.worker_run_id} --status reviewed_passed --reviewer \"<name>\" --note \"<note>\"."
    if review_status == "reviewed_passed":
        if worker_run.source_queue_id and worker_run.source_queue_item_id:
            return (
                f"Review passed. Complete explicitly only if validation/delivery evidence is sufficient: devo project queue-complete-item --project {project_name} "
                f"--queue {worker_run.source_queue_id} --item {worker_run.source_queue_item_id} --note \"<reviewed result>\""
            )
        return "Review passed. No linked queue item exists; continue with the appropriate delivery workflow manually."
    if review_status == "reviewed_needs_changes":
        if worker_run.source_queue_id and worker_run.source_queue_item_id:
            return (
                f"Review needs changes. Keep the queue item incomplete; consider devo project queue-block-item --project {project_name} "
                f"--queue {worker_run.source_queue_id} --item {worker_run.source_queue_item_id} --note \"<needed changes>\" or prepare a follow-up worker run."
            )
        return "Review needs changes. Prepare a follow-up handoff or worker run after clarifying scope."
    if review_status == "rejected":
        if worker_run.source_queue_id and worker_run.source_queue_item_id:
            return (
                f"Review rejected. Keep the queue item incomplete; block or replace the worker output before completion: devo project queue-block-item --project {project_name} "
                f"--queue {worker_run.source_queue_id} --item {worker_run.source_queue_item_id} --note \"<rejection reason>\""
            )
        return "Review rejected. Do not deliver this worker output; create a new handoff only after scope is clear."
    return "Review worker evidence before any queue/task completion, validation, commit, or push."


def _with_queue_counts(queue: ExecutionQueue) -> ExecutionQueue:
    items = queue.items
    return queue.model_copy(
        update={
            "item_count": len(items),
            "pending_count": sum(1 for item in items if item.status == "pending"),
            "running_count": sum(1 for item in items if item.status == "running"),
            "completed_count": sum(1 for item in items if item.status == "completed"),
            "blocked_count": sum(1 for item in items if item.status == "blocked"),
            "failed_count": sum(1 for item in items if item.status == "failed"),
        }
    )


def _require_queue(project_name: str, queue_id: str, workspace_root: Path) -> ExecutionQueue:
    queue = load_execution_queue(project_name, queue_id, workspace_root=workspace_root)
    if not queue:
        msg = f"Execution queue not found: {queue_id}"
        raise ValueError(msg)
    return queue


def _require_queue_item(queue: ExecutionQueue, item_id: str) -> QueueItem:
    normalized = item_id.strip().upper()
    for item in queue.items:
        if item.item_id.upper() == normalized:
            return item
    msg = f"Queue item not found: {item_id}"
    raise ValueError(msg)


def _require_worker_run(project_name: str, worker_run_id: str, workspace_root: Path) -> WorkerRun:
    worker_run = load_codex_worker_run(project_name, worker_run_id, workspace_root=workspace_root)
    if not worker_run:
        msg = f"Codex worker run not found: {worker_run_id}"
        raise ValueError(msg)
    return worker_run


def _find_queue_item(items: list[QueueItem], item_id: str | None) -> QueueItem | None:
    if not item_id:
        return None
    normalized = item_id.strip().upper()
    return next((item for item in items if item.item_id.upper() == normalized), None)


def _replace_queue_item(items: list[QueueItem], replacement: QueueItem) -> None:
    for index, item in enumerate(items):
        if item.item_id.upper() == replacement.item_id.upper():
            items[index] = replacement
            return


def _append_note(notes: list[str], note: str, timestamp: datetime) -> list[str]:
    cleaned = note.strip()
    if not cleaned:
        cleaned = "No note provided."
    return [*notes, f"{timestamp.isoformat()}: {cleaned}"]


def _update_backlog_task_status(project_name: str, task_id: str, status: str, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        return
    now = datetime.now(UTC)
    updated_tasks: list[BacklogTask] = []
    changed = False
    normalized = task_id.strip().upper()
    for task in backlog.tasks:
        if task.id.strip().upper() == normalized:
            updated_tasks.append(task.model_copy(update={"status": status, "updated_at": now}))
            changed = True
        else:
            updated_tasks.append(task)
    if not changed:
        return
    updated = _with_backlog_counts(backlog.model_copy(update={"tasks": updated_tasks, "updated_at": now}))
    paths = planning_artifact_paths(project_name, workspace_root=root)
    _write_model(paths.backlog_json, updated)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(updated), encoding="utf-8")


def _task_snapshot(task: BacklogTask) -> BatchTaskSnapshot:
    return BatchTaskSnapshot(
        task_id=task.id,
        title=task.title,
        lane=task.lane,
        risk_level=task.risk_level,
        status=task.status,
        dependencies=task.dependencies,
        acceptance_criteria_summary=_summary_list(task.acceptance_criteria),
        validation_expectations_summary=_summary_list(task.validation_expectations),
    )


def _require_batch(project_name: str, batch_id: str, workspace_root: Path) -> ProjectBatch:
    batch = load_project_batch(project_name, batch_id, workspace_root=workspace_root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    return batch


def _require_execution_policy(project_name: str, policy_id: str, workspace_root: Path) -> BatchExecutionPolicy:
    policy = load_execution_policy(project_name, policy_id, workspace_root=workspace_root)
    if not policy:
        msg = f"Execution policy not found: {policy_id}"
        raise ValueError(msg)
    return policy


def _require_queue_worker_run(project_name: str, run_id: str, workspace_root: Path) -> QueueWorkerRun:
    run = load_queue_worker_run(project_name, run_id, workspace_root=workspace_root)
    if not run:
        msg = f"Queue worker run not found: {run_id}"
        raise ValueError(msg)
    return run


def _queue_worker_recheck_selected_run(project_name: str, run: QueueWorkerRun, workspace_root: Path) -> tuple[list[str], list[str], str]:
    blockers: list[str] = []
    warnings: list[str] = []
    policy = load_execution_policy(project_name, run.policy_id, workspace_root=workspace_root)
    if not policy:
        return [f"Execution policy not found: {run.policy_id}"], warnings, "Policy missing."
    policy_check = check_execution_policy(project_name, policy.policy_id, workspace_root=workspace_root)
    blockers.extend(policy_check.blockers)
    warnings.extend(policy_check.warnings)
    policy_summary = f"usable={policy_check.usable}; status={policy_check.status}; blockers={len(policy_check.blockers)}; warnings={len(policy_check.warnings)}"
    if not run.queue_id:
        blockers.append("Queue worker run has no queue id.")
        return blockers, warnings, policy_summary
    queue = load_execution_queue(project_name, run.queue_id, workspace_root=workspace_root)
    if not queue:
        blockers.append(f"Referenced queue not found: {run.queue_id}.")
        return blockers, warnings, policy_summary
    if not run.selected_queue_item_id:
        blockers.append("Queue worker run has no selected queue item.")
        return blockers, warnings, policy_summary
    item = _find_queue_item(queue.items, run.selected_queue_item_id)
    if not item:
        blockers.append(f"Selected queue item not found: {run.selected_queue_item_id}.")
        return blockers, warnings, policy_summary
    allowed_tasks = {_normalize_task_id(task_id) for task_id in policy.allowed_task_ids}
    allowed_items = {_normalize_queue_item_id(item_id) for item_id in policy.allowed_queue_item_ids}
    reason = _queue_worker_item_skip_reason(project_name, policy, item, allowed_tasks, allowed_items, workspace_root=workspace_root)
    if reason:
        blockers.append(f"Selected queue item {item.item_id} is no longer within approved policy scope: {reason}.")
    return blockers, warnings, policy_summary


def _queue_worker_status_from_evidence(run: QueueWorkerRun, evidence: QueueWorkerEvidenceSummary) -> str:
    if evidence.blockers:
        if any("failed" in blocker.lower() or "rejected" in blocker.lower() for blocker in evidence.blockers):
            return "failed"
        return "blocked"
    if not evidence.handoff_exists:
        return "handoff_ready"
    if not evidence.worker_run_exists or not evidence.worker_report_imported:
        return "waiting_worker"
    if not evidence.worker_review_exists:
        return "waiting_review"
    if not evidence.validation_passed:
        return "waiting_validation"
    if run.status in {"delivery_requested", "completed"}:
        return run.status
    return "ready_for_delivery_request"


def _queue_worker_next_action_for_status(
    project_name: str,
    run: QueueWorkerRun,
    status: str,
    evidence: QueueWorkerEvidenceSummary,
    blockers: list[str],
) -> str:
    if status == "completed":
        return "No action needed; queue-worker run is completed."
    if status == "cancelled":
        return "No action needed for this cancelled queue-worker run."
    if status == "paused":
        return f"Resume when safe: devo project queue-worker-resume --project {project_name} --run {run.run_id} --confirm-resume"
    if status == "failed":
        return f"Inspect evidence, then retry only if safe: devo project queue-worker-retry --project {project_name} --run {run.run_id} --confirm-retry"
    if status == "blocked" or blockers:
        return "Resolve blockers, then retry or resume the queue-worker run."
    return _queue_worker_next_action_for_run(project_name, run, evidence)


def _queue_worker_next_action_for_run(project_name: str, run: QueueWorkerRun, evidence: QueueWorkerEvidenceSummary) -> str:
    if not evidence.handoff_exists:
        return f"Create or inspect the queue handoff: devo project handoff-next --project {project_name} --queue {run.queue_id or '<queueId>'}"
    if not evidence.worker_run_exists:
        return f"Create a worker run from the handoff: devo worker codex run-create --project {project_name} --handoff {run.selected_handoff_id}"
    if not evidence.worker_report_imported:
        return (
            f"Import a worker report after Codex/manual work: devo worker codex report-import --project {project_name} "
            f"--run {run.selected_worker_run_id} --file <filledReportFile>"
        )
    if not evidence.worker_review_exists:
        return f"Create worker review evidence: devo worker codex review-template --project {project_name} --run {run.selected_worker_run_id}"
    if not evidence.validation_passed:
        return f"Record passing validation evidence before delivery for worker run {run.selected_worker_run_id}."
    if not evidence.delivery_request_exists:
        return "Create a trusted delivery runner request only after reviewed validation evidence is complete."
    if not evidence.delivery_completed:
        return "Wait for or inspect the trusted delivery runner result."
    return "No action needed."


def _validate_positive_limit(label: str, value: int) -> None:
    if value < 1:
        msg = f"{label} must be at least 1."
        raise ValueError(msg)


def _clean_string_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in values:
        for item in str(raw).split(","):
            value = item.strip()
            if value and value not in cleaned:
                cleaned.append(value)
    return cleaned


def _with_timed_note(notes: list[str], note: str, label: str, now: datetime) -> list[str]:
    cleaned = note.strip()
    if not cleaned:
        return list(notes)
    return [*notes, f"{now.isoformat()}: {label}: {cleaned}"]


def _highest_policy_risk(batch: ProjectBatch) -> str:
    if not batch.risk_summary:
        return "medium"
    known = [risk for risk, count in batch.risk_summary.items() if count > 0 and risk in RISK_ORDER]
    if not known:
        return "medium"
    return max(known, key=lambda risk: RISK_ORDER.get(risk, 0))


def _build_batch_approval(
    batch: ProjectBatch,
    *,
    existing: BatchApproval | None = None,
    approval_status: str,
    review_status: str,
    review_notes: list[str],
    requested_at: datetime | None = None,
    reviewed_at: datetime | None = None,
    approved_at: datetime | None = None,
    rejected_at: datetime | None = None,
    reviewer: str | None = None,
    approver: str | None = None,
    decision_note: str = "",
    now: datetime,
) -> BatchApproval:
    created_at = existing.created_at if existing else now
    return BatchApproval(
        project=batch.project,
        batch_id=batch.batch_id,
        approval_status=approval_status,
        review_status=review_status,
        requested_at=requested_at or (existing.requested_at if existing else None),
        reviewed_at=reviewed_at or (existing.reviewed_at if existing else None),
        approved_at=approved_at or (existing.approved_at if existing else None),
        rejected_at=rejected_at or (existing.rejected_at if existing else None),
        reviewer=reviewer or (existing.reviewer if existing else None),
        approver=approver or (existing.approver if existing else None),
        decision_note=decision_note or (existing.decision_note if existing else ""),
        review_notes=review_notes,
        dependency_warnings=batch.dependency_warnings,
        risk_summary=batch.risk_summary,
        lane_summary=batch.lane_summary,
        task_count=batch.task_count,
        high_risk_task_count=sum(batch.risk_summary.get(risk, 0) for risk in ("high", "critical")),
        blocked_dependency_count=len(batch.dependency_warnings),
        scope_summary=_batch_scope_summary(batch),
        validation_summary=_batch_validation_summary(batch),
        next_action=_batch_approval_next_action(batch.project, batch.batch_id, approval_status, review_status),
        created_at=created_at,
        updated_at=now,
    )


def _batch_scope_summary(batch: ProjectBatch) -> list[str]:
    items = [
        f"{batch.task_count} task(s): {', '.join(batch.task_ids) if batch.task_ids else 'none'}",
        f"Lanes: {_format_count_summary(batch.lane_summary)}",
        f"Risks: {_format_count_summary(batch.risk_summary)}",
    ]
    if batch.dependencies:
        items.append(f"External dependencies: {', '.join(batch.dependencies)}")
    return items


def _batch_validation_summary(batch: ProjectBatch) -> list[str]:
    summaries = [snapshot.validation_expectations_summary for snapshot in batch.task_snapshots if snapshot.validation_expectations_summary]
    if not summaries:
        return ["No validation expectations recorded."]
    return sorted(set(summaries))


def _batch_approval_next_action(project_name: str, batch_id: str, approval_status: str, review_status: str) -> str:
    if approval_status == "approved":
        return f"Create execution queue: devo project queue-create --project {project_name} --batch {batch_id}"
    if approval_status == "rejected" or review_status == "needs_changes":
        return "Revise backlog/batch manually or create a new batch."
    if approval_status == "requested":
        return f"Review or approve batch: devo project batch-approval-show --project {project_name} --batch {batch_id}"
    return f"Request batch approval: devo project batch-approval-request --project {project_name} --batch {batch_id} --note \"<note>\""


def _format_count_summary(summary: dict[str, int]) -> str:
    if not summary:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(summary.items()))


def _batch_summary(tasks: list[BacklogTask]) -> str:
    if not tasks:
        return "No tasks selected."
    lanes = ", ".join(sorted({task.lane for task in tasks}))
    risks = ", ".join(sorted({task.risk_level for task in tasks}, key=lambda risk: RISK_ORDER.get(risk, 99)))
    return f"Planning batch with {len(tasks)} task(s), lanes: {lanes}, risks: {risks}."


def _count_by(tasks: list[BacklogTask], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(getattr(task, field_name))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _batch_dependencies(tasks: list[BacklogTask]) -> list[str]:
    selected = {task.id.strip().upper() for task in tasks}
    dependencies: set[str] = set()
    for task in tasks:
        for dependency in task.dependencies:
            normalized = dependency.strip().upper()
            if normalized and normalized not in selected:
                dependencies.add(normalized)
    return sorted(dependencies)


def _batch_dependency_warnings(tasks: list[BacklogTask], backlog: ProjectBacklog) -> list[str]:
    selected = {task.id.strip().upper() for task in tasks}
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    warnings: list[str] = []
    for task in tasks:
        for dependency in task.dependencies:
            normalized = dependency.strip().upper()
            dependency_task = task_by_id.get(normalized)
            if not dependency_task:
                warnings.append(f"{task.id} depends on unknown task {dependency}.")
            elif normalized not in selected:
                warnings.append(f"{task.id} depends on {dependency_task.id}, which is not included in this batch.")
            elif dependency_task.status != "completed" and dependency_task.id != task.id:
                warnings.append(f"{task.id} depends on {dependency_task.id}, which is included but not completed.")
    return warnings


def _suggestion_reason(task: BacklogTask) -> str:
    dependency_text = "dependencies satisfied" if not task.dependencies else "dependencies completed or included"
    return f"{task.status} task, {task.risk_level} risk, {dependency_text}."


def _progress_next_action(
    project_name: str,
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint | None,
    backlog: ProjectBacklog | None,
    batches: list[ProjectBatch],
) -> str:
    if not brief:
        return f"Create a Project Brief: devo project brief-create --project {project_name} --title \"<title>\" --file <brief.md>"
    if brief.status != "approved":
        return f"Approve the Project Brief: devo project brief-approve --project {project_name}"
    if not blueprint:
        return f"Create a Blueprint: devo project blueprint-create --project {project_name}"
    if blueprint.status != "approved":
        return f"Approve the Blueprint: devo project blueprint-approve --project {project_name}"
    if not backlog:
        return f"Create a Backlog: devo project backlog-create --project {project_name}"
    if backlog.status != "approved":
        return f"Approve the Backlog: devo project backlog-approve --project {project_name}"
    if not batches:
        return f"Create or suggest a Batch: devo project batch-suggest --project {project_name} --limit 10"
    latest_batch = batches[0]
    if not any(batch.approval_status == "approved" for batch in batches):
        return f"Review and approve a Batch: devo project batch-show --project {project_name} --batch {latest_batch.batch_id}"
    return "Approved planning batch is ready; create an execution queue or generate a batch handoff."


def _intake_next_step(
    project_name: str,
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint | None,
    backlog: ProjectBacklog | None,
    latest_batch: ProjectBatch | None,
    latest_batch_approval: BatchApproval | None,
    latest_queue: ExecutionQueue | None,
    latest_handoff: CodexHandoff | None,
) -> tuple[str, str, list[str]]:
    if not brief:
        return (
            "Create a project brief.",
            f'devo project brief-create --project {project_name} --title "<title>" --file <brief.md>',
            [
                f"devo project intake-template --project {project_name}",
                f'devo project intake-prompt --project {project_name} --idea "<rough idea>"',
            ],
        )
    if brief.status != "approved":
        return (
            "Approve or revise the project brief.",
            f"devo project brief-approve --project {project_name}",
            [f"devo project brief-show --project {project_name}"],
        )
    if not blueprint:
        return (
            "Create a blueprint from the approved brief.",
            f"devo project blueprint-create --project {project_name}",
            [f"devo project brief-show --project {project_name}"],
        )
    if blueprint.status != "approved":
        return (
            "Approve or revise the blueprint.",
            f"devo project blueprint-approve --project {project_name}",
            [f"devo project blueprint-show --project {project_name}"],
        )
    if not backlog:
        return (
            "Create a starter backlog from the approved blueprint.",
            f"devo project backlog-create --project {project_name}",
            [f"devo project blueprint-show --project {project_name}"],
        )
    if backlog.status != "approved":
        return (
            "Approve or refine the backlog.",
            f"devo project backlog-approve --project {project_name}",
            [
                f"devo project backlog-prompt --project {project_name}",
                f"devo project backlog-show --project {project_name}",
            ],
        )
    if not latest_batch:
        return (
            "Create or suggest a planning batch from approved backlog tasks.",
            f"devo project batch-suggest --project {project_name} --limit 10",
            [f"devo project batch-suggest --project {project_name} --limit 10 --write"],
        )
    approval_status = latest_batch_approval.approval_status if latest_batch_approval else latest_batch.approval_status
    if approval_status != "approved":
        if approval_status == "requested":
            return (
                "Review or approve the latest planning batch.",
                f"devo project batch-approval-show --project {project_name} --batch {latest_batch.batch_id}",
                [
                    f'devo project batch-review --project {project_name} --batch {latest_batch.batch_id} --note "<review note>"',
                    f'devo project batch-approve --project {project_name} --batch {latest_batch.batch_id} --note "<decision note>"',
                ],
            )
        return (
            "Request approval for the latest planning batch.",
            f'devo project batch-approval-request --project {project_name} --batch {latest_batch.batch_id} --note "<note>"',
            [f"devo project batch-show --project {project_name} --batch {latest_batch.batch_id}"],
        )
    if not latest_queue:
        return (
            "Create an execution queue from the approved batch.",
            f"devo project queue-create --project {project_name} --batch {latest_batch.batch_id}",
            [f"devo project batch-show --project {project_name} --batch {latest_batch.batch_id}"],
        )
    if not latest_handoff:
        return (
            "Generate a Codex handoff for the current queue item.",
            f"devo project handoff-next --project {project_name} --queue {latest_queue.queue_id}",
            [f"devo project queue-next --project {project_name} --queue {latest_queue.queue_id}"],
        )
    return (
        "Use the latest Codex handoff or create a worker run from it.",
        f"devo worker codex run-create --project {project_name} --handoff {latest_handoff.handoff_id}",
        [f"devo project handoff-show --project {project_name} --handoff {latest_handoff.handoff_id}"],
    )


def _progress_warnings(
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint | None,
    backlog: ProjectBacklog | None,
    active_tasks: list[BacklogTask],
    batches: list[ProjectBatch],
) -> list[str]:
    warnings: list[str] = []
    if not brief:
        warnings.append("Project Brief is missing.")
    if not blueprint:
        warnings.append("Blueprint is missing.")
    if not backlog:
        warnings.append("Backlog is missing.")
    if backlog and not active_tasks:
        warnings.append("Backlog has no active tasks.")
    blocked = [task.id for task in active_tasks if task.status == "blocked"]
    if blocked:
        warnings.append(f"Blocked tasks: {', '.join(blocked)}.")
    if batches and not any(batch.approval_status == "approved" for batch in batches):
        warnings.append("No planning batch is approved.")
    return warnings


def _aggregate_progress_groups(
    tasks: list[BacklogTask],
    groups: list[BlueprintMilestone] | list[BlueprintEpic],
    field_name: str,
) -> list[PlanningProgressGroup]:
    title_by_id = {group.id: group.title for group in groups}
    group_ids = set(title_by_id)
    for task in tasks:
        group_id = getattr(task, field_name) or "unassigned"
        group_ids.add(group_id)
    results: list[PlanningProgressGroup] = []
    for group_id in sorted(group_ids):
        group_tasks = [task for task in tasks if (getattr(task, field_name) or "unassigned") == group_id]
        active_count = len(group_tasks)
        completed = sum(1 for task in group_tasks if task.status == "completed")
        blocked = sum(1 for task in group_tasks if task.status == "blocked")
        ready = sum(1 for task in group_tasks if task.status == "ready")
        approved = sum(1 for task in group_tasks if task.status == "approved")
        draft = sum(1 for task in group_tasks if task.status == "draft")
        ready_like = sum(1 for task in group_tasks if task.status in {"ready", "approved", "completed"})
        results.append(
            PlanningProgressGroup(
                id=group_id,
                title=title_by_id.get(group_id),
                task_count=active_count,
                active_task_count=active_count,
                completed_task_count=completed,
                blocked_task_count=blocked,
                ready_task_count=ready,
                approved_task_count=approved,
                draft_task_count=draft,
                completion_percent=_percent(completed, active_count),
                readiness_percent=_percent(ready_like, active_count),
                blocked_percent=_percent(blocked, active_count),
            )
        )
    return results


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _summary_list(values: list[str]) -> str:
    if not values:
        return ""
    text = "; ".join(values[:3])
    if len(values) > 3:
        text += f"; +{len(values) - 3} more"
    return text


def _lane_summary() -> str:
    lines: list[str] = []
    for lane_id, lane in sorted(BUILT_IN_LANES.items()):
        lines.append(f"- {lane_id}: {lane.name}")
        if lane.default_validation_commands:
            lines.append(f"  - default validation: {', '.join(lane.default_validation_commands)}")
        if lane.notes:
            lines.append(f"  - note: {lane.notes[0]}")
    return "\n".join(lines)


def _try_get_backlog_task(project_name: str, task_id: str, workspace_root: Path) -> BacklogTask | None:
    try:
        return get_backlog_task(project_name, task_id, workspace_root=workspace_root)
    except ValueError:
        return None


def _worker_allowed_scope(task: BacklogTask | None, queue_item: QueueItem | None) -> list[str]:
    if task and task.allowed_scope:
        return task.allowed_scope
    if queue_item:
        return [
            f"Only the linked queue item {queue_item.item_id} / task {queue_item.task_id}.",
            "Use the linked Codex handoff prompt as the execution scope.",
        ]
    return [
        "Use the linked Codex handoff prompt as the execution scope.",
        "Do not expand beyond the source batch, queue item, or task referenced by the handoff.",
    ]


def _worker_forbidden_scope(task: BacklogTask | None) -> list[str]:
    defaults = [
        "Do not run Codex CLI automatically from Devo.",
        "Do not call AI/model APIs.",
        "Do not execute target repo build/test/run/restore/migration/database/script commands unless separately approved in the handoff.",
        "Do not modify generated workspace artifacts as delivery evidence.",
        "Do not mark Devo queue/task completion from worker output alone.",
        "Do not commit or push target changes from this worker-run tracking command.",
    ]
    if task and task.forbidden_scope:
        return [*task.forbidden_scope, *defaults]
    return defaults


def _worker_validation_expectations(task: BacklogTask | None, queue_item: QueueItem | None) -> list[str]:
    if task and task.validation_expectations:
        return task.validation_expectations
    if queue_item and queue_item.validation_expectations:
        return queue_item.validation_expectations
    return [
        "Worker-reported validation is informational until a future Devo report import/review step validates it.",
        "Record skipped validation honestly if validation approval or safe command execution is unavailable.",
    ]


def _worker_safety_boundaries(project_name: str) -> list[str]:
    return [
        "Worker run records are workspace-only tracking artifacts.",
        "Codex may be invoked only by the guarded execute command with an approved run plan and explicit confirmation.",
        "Codex output is not trusted as implementation complete until reviewed/imported.",
        "Target repository source must not be changed by worker-run create/list/show/status commands.",
        f"Keep work inside the registered project scope for {project_name}.",
    ]


def _worker_run_next_action(project_name: str, worker_run_id: str, status: str) -> str:
    if status == "planned":
        return (
            f"Inspect preflight or create a run plan with devo worker codex preflight --project {project_name} --run {worker_run_id}. "
            "Use the guarded run-plan and execute-preview flow before any supervised execute --confirm-execute run."
        )
    if status == "running":
        return f"Track the supervised Codex session; Devo will update status after process exit or use devo worker codex run-status --project {project_name} --run {worker_run_id} if manual correction is needed."
    if status == "completed":
        return f"Review/import worker report evidence with devo worker codex report-template --project {project_name} --run {worker_run_id}; do not automatically complete queue/task state."
    if status == "failed":
        return "Review the failure, preserve evidence, and create a new handoff or worker run only after scope is clear."
    if status == "paused_usage_limit":
        return "Pause or resume the linked queue with devo project queue-pause/queue-resume as appropriate, then create a new worker run when ready."
    if status == "blocked_needs_approval":
        return "Stop and request explicit trusted approval before continuing or creating another worker run."
    if status == "cancelled":
        return "No automatic queue/task change was made; create a fresh handoff if work should continue."
    if status == "waiting_review":
        return f"Review worker evidence manually and prepare a report with devo worker codex report-template --project {project_name} --run {worker_run_id} before any queue/task completion, validation, commit, or push."
    if status == "superseded":
        return "Use the newer worker run or handoff; this record remains historical only."
    return "Review worker run status."


def _worker_status_from_report_status(status_reported_by_worker: str) -> str:
    if status_reported_by_worker == "completed":
        return "waiting_review"
    if status_reported_by_worker == "failed":
        return "failed"
    if status_reported_by_worker in {"blocked", "needs_approval"}:
        return "blocked_needs_approval"
    if status_reported_by_worker == "usage_limit":
        return "paused_usage_limit"
    if status_reported_by_worker == "partial":
        return "waiting_review"
    return "waiting_review"


def _worker_report_next_action(project_name: str, worker_run_id: str, status_reported_by_worker: str) -> str:
    if status_reported_by_worker == "completed":
        return (
            "Review imported report manually, verify validation independently, then use "
            f"devo project queue-complete-item only after review. Inspect with devo worker codex report-show --project {project_name} --run {worker_run_id}."
        )
    if status_reported_by_worker == "usage_limit":
        return "Review partial report, pause/resume the linked queue if needed, and create a new worker run when usage resets."
    if status_reported_by_worker in {"blocked", "needs_approval"}:
        return "Review blockers and request explicit trusted approval before continuing."
    if status_reported_by_worker == "failed":
        return "Review failure evidence and create a new handoff or worker run only after the cause is understood."
    return "Review imported report manually before any queue/task completion, validation, commit, or push."


def _load_worker_run_and_plan_for_execution(
    project_name: str,
    worker_run_id: str,
    plan_id: str,
    workspace_root: Path,
) -> tuple[WorkerRun, CodexRunPlan]:
    worker_run = load_codex_worker_run(project_name, worker_run_id, workspace_root=workspace_root)
    if not worker_run:
        msg = f"Codex worker run not found: {worker_run_id}"
        raise ValueError(msg)
    plan = load_codex_run_plan(project_name, plan_id, workspace_root=workspace_root)
    if not plan:
        msg = f"Codex run plan not found: {plan_id}"
        raise ValueError(msg)
    if plan.worker_run_id != worker_run.worker_run_id:
        msg = f"Run plan {plan.plan_id} belongs to worker run {plan.worker_run_id}, not {worker_run.worker_run_id}."
        raise ValueError(msg)
    return worker_run, plan


WINDOWSAPPS_ALIAS_MESSAGE = (
    "Codex resolved to WindowsApps app execution alias and may not be launchable by Devo. "
    "Use --codex-path with a real executable/wrapper path."
)


SUPPORTED_CODEX_WRAPPER_SUFFIXES = {".cmd", ".bat", ".exe", ".ps1"}


def diagnose_codex_executable(
    codex_path: str | None = None,
    *,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
    target_repo_path: str | None = None,
) -> CodexExecutableDiagnostic:
    candidates = _detect_codex_candidates()
    npm_candidates = _npm_global_bin_candidates()
    wsl_available = shutil.which("wsl") is not None
    if codex_path and codex_wrapper:
        detail = "Use only one Codex launcher option: --codex-path or --codex-wrapper."
        return CodexExecutableDiagnostic(
            launcher_type="blocked",
            executable_source="blocked",
            command_resolution_note=detail,
            launch_risk="blocked",
            launch_blockers=[detail],
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            recommended_next_action="Choose one launcher option and recreate the run plan.",
        )
    if codex_wsl and (codex_path or codex_wrapper):
        detail = "Use only one Codex launcher option: --codex-path, --codex-wrapper, or --codex-wsl."
        return CodexExecutableDiagnostic(
            launcher_type="blocked",
            executable_source="blocked",
            command_resolution_note=detail,
            launch_risk="blocked",
            launch_blockers=[detail],
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            recommended_next_action="Choose one launcher option and recreate the run plan.",
        )
    if codex_wrapper and codex_wrapper.strip():
        return _diagnose_codex_wrapper(
            codex_wrapper,
            target_repo_path=target_repo_path,
            candidates=candidates,
            npm_candidates=npm_candidates,
            wsl_available=wsl_available,
        )
    if codex_wsl and codex_wsl.strip():
        distro = codex_wsl.strip()
        blockers: list[str] = []
        risk = "medium"
        note = f"WSL Codex launcher requested for distribution: {distro}. Execution is preview-only in this Devo version."
        if not wsl_available:
            blockers.append("wsl.exe was not found on PATH.")
            risk = "blocked"
        blockers.append("WSL Codex execution is not implemented yet; use this as planning guidance only.")
        return CodexExecutableDiagnostic(
            launcher_type="wsl_codex",
            executable_source="wsl_codex",
            wsl_distribution=distro,
            command_preview=f"wsl.exe -d {distro} -- codex <prompt>",
            exists=wsl_available,
            command_resolution_note=note,
            launch_risk=risk if not blockers else "blocked",
            launch_blockers=blockers,
            launch_warnings=[] if blockers else ["WSL launcher support is experimental and should be reviewed before execution."],
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            execution_supported=False,
            recommended_next_action="Use --codex-path or --codex-wrapper for guarded execution until WSL execution is implemented.",
        )
    if codex_path and codex_path.strip():
        explicit_path = Path(codex_path.strip()).expanduser()
        if not explicit_path.exists():
            detail = f"Explicit Codex executable path does not exist: {explicit_path}."
            return CodexExecutableDiagnostic(
                launcher_type="path_override",
                executable_source="path_override",
                command_resolution_note=detail,
                launch_risk="blocked",
                launch_blockers=[detail],
                candidate_paths=candidates,
                npm_global_bin_candidates=npm_candidates,
                wsl_available=wsl_available,
                recommended_next_action="Provide --codex-path with an existing real executable or wrapper path.",
            )
        if not explicit_path.is_file():
            detail = f"Explicit Codex executable path is not a file: {explicit_path}."
            return CodexExecutableDiagnostic(
                launcher_type="path_override",
                executable_source="path_override",
                command_resolution_note=detail,
                launch_risk="blocked",
                launch_blockers=[detail],
                candidate_paths=candidates,
                npm_global_bin_candidates=npm_candidates,
                wsl_available=wsl_available,
                recommended_next_action="Provide --codex-path with a real executable or wrapper file.",
            )
        resolved = str(explicit_path.resolve())
        if _is_windowsapps_codex_alias(resolved):
            detail = f"{WINDOWSAPPS_ALIAS_MESSAGE} Path: {resolved}."
            return CodexExecutableDiagnostic(
                launcher_type="blocked_windowsapps",
                executable_path=resolved,
                executable_source="path_override",
                exists=True,
                is_windowsapps_alias=True,
                command_resolution_note=detail,
                launch_risk="blocked",
                launch_blockers=[detail],
                candidate_paths=candidates,
                npm_global_bin_candidates=npm_candidates,
                wsl_available=wsl_available,
                recommended_next_action="Create or choose a non-WindowsApps wrapper, then pass it with --codex-path.",
            )
        return CodexExecutableDiagnostic(
            launcher_type="path_override",
            executable_path=resolved,
            executable_source="path_override",
            command_preview=f"{resolved} <prompt>",
            exists=True,
            command_resolution_note=f"Using explicit Codex executable path: {resolved}.",
            launch_risk="low",
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            execution_supported=True,
            recommended_next_action="Use execute-preview before guarded execution.",
        )
    detected = shutil.which("codex")
    if detected:
        resolved = str(Path(detected).expanduser().resolve())
        if _is_windowsapps_codex_alias(resolved):
            detail = f"{WINDOWSAPPS_ALIAS_MESSAGE} Path: {resolved}."
            return CodexExecutableDiagnostic(
                launcher_type="blocked_windowsapps",
                executable_path=resolved,
                executable_source="path_detection",
                exists=True,
                is_windowsapps_alias=True,
                command_resolution_note=detail,
                launch_risk="blocked",
                launch_blockers=[detail],
                candidate_paths=candidates,
                npm_global_bin_candidates=npm_candidates,
                wsl_available=wsl_available,
                recommended_next_action="Run devo worker codex doctor, then use --codex-path with a non-WindowsApps wrapper path.",
            )
        return CodexExecutableDiagnostic(
            launcher_type="path_detection",
            executable_path=resolved,
            executable_source="path_detection",
            command_preview=f"{resolved} <prompt>",
            exists=True,
            command_resolution_note=f"Codex executable appears on PATH: {resolved}.",
            launch_risk="low",
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            execution_supported=True,
            recommended_next_action="Use execute-preview before guarded execution.",
        )
    return CodexExecutableDiagnostic(
        launcher_type="not_found",
        executable_source="not_found",
        command_resolution_note="Codex executable was not found on PATH.",
        launch_risk="not_found",
        launch_warnings=["Codex executable was not found on PATH by safe detection; future supervised execution may need configuration."],
        candidate_paths=candidates,
        npm_global_bin_candidates=npm_candidates,
        wsl_available=wsl_available,
        execution_supported=False,
        recommended_next_action="Install Codex CLI or pass --codex-path with a real executable/wrapper path.",
    )


def _diagnose_codex_wrapper(
    codex_wrapper: str,
    *,
    target_repo_path: str | None,
    candidates: list[str],
    npm_candidates: list[str],
    wsl_available: bool,
) -> CodexExecutableDiagnostic:
    wrapper = Path(codex_wrapper.strip()).expanduser()
    source = _wrapper_launcher_type(wrapper)
    if not wrapper.exists():
        detail = f"Codex wrapper path does not exist: {wrapper}."
        return CodexExecutableDiagnostic(
            launcher_type=source,
            executable_source=source,
            wrapper_path=str(wrapper),
            command_resolution_note=detail,
            launch_risk="blocked",
            launch_blockers=[detail],
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            recommended_next_action="Create the wrapper first or pass an existing wrapper path.",
        )
    if not wrapper.is_file():
        detail = f"Codex wrapper path is not a file: {wrapper}."
        return CodexExecutableDiagnostic(
            launcher_type=source,
            executable_source=source,
            wrapper_path=str(wrapper),
            command_resolution_note=detail,
            launch_risk="blocked",
            launch_blockers=[detail],
            candidate_paths=candidates,
            npm_global_bin_candidates=npm_candidates,
            wsl_available=wsl_available,
            recommended_next_action="Pass a wrapper file path.",
        )
    resolved = str(wrapper.resolve())
    blockers: list[str] = []
    warnings: list[str] = []
    suffix = wrapper.suffix.lower()
    if suffix not in SUPPORTED_CODEX_WRAPPER_SUFFIXES:
        blockers.append("Codex wrapper must be a .cmd, .bat, .ps1, or executable file.")
    if _is_windowsapps_codex_alias(resolved):
        blockers.append(f"{WINDOWSAPPS_ALIAS_MESSAGE} Path: {resolved}.")
    location_warning = _wrapper_location_warning(resolved, target_repo_path)
    if location_warning:
        blockers.append(location_warning)
    command_preview = _launcher_command_preview(
        CodexExecutableDiagnostic(launcher_type=source, executable_source=source, wrapper_path=resolved)
    )
    return CodexExecutableDiagnostic(
        launcher_type=source,
        executable_source=source,
        wrapper_path=resolved,
        command_preview=command_preview,
        exists=True,
        is_windowsapps_alias=_is_windowsapps_codex_alias(resolved),
        command_resolution_note=f"Using explicit Codex wrapper path: {resolved}.",
        launch_risk="blocked" if blockers else "medium",
        launch_blockers=blockers,
        launch_warnings=warnings or ["Wrapper launchers are operator-controlled; verify the wrapper contains no secrets and does not use shell indirection."],
        candidate_paths=candidates,
        npm_global_bin_candidates=npm_candidates,
        wsl_available=wsl_available,
        execution_supported=not blockers,
        recommended_next_action=(
            "Resolve wrapper blockers before creating a run plan."
            if blockers
            else "Use execute-preview before guarded execution; do not commit local wrapper files."
        ),
    )


def _resolve_codex_executable(codex_path: str | None = None) -> tuple[str | None, str, str, str | None]:
    diagnostic = diagnose_codex_executable(codex_path)
    error = diagnostic.launch_blockers[0] if diagnostic.launch_blockers else None
    return diagnostic.executable_path, diagnostic.executable_source, diagnostic.command_resolution_note, error


def _is_windowsapps_codex_alias(path: str) -> bool:
    lowered = str(path).replace("/", "\\").lower()
    return "\\windowsapps\\" in lowered and (lowered.endswith("\\codex.exe") or lowered.endswith("\\codex"))


def _detect_codex_candidates() -> list[str]:
    candidates: list[str] = []
    for name in ("codex", "codex.exe", "codex.cmd", "codex.bat"):
        detected = shutil.which(name)
        if detected:
            resolved = str(Path(detected).expanduser().resolve())
            if resolved not in candidates:
                candidates.append(resolved)
    return candidates


def _npm_global_bin_candidates() -> list[str]:
    candidates: list[str] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(str(Path(appdata) / "npm"))
    prefix = os.environ.get("PREFIX")
    if prefix:
        candidates.append(str(Path(prefix) / "bin"))
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(str(Path(program_files) / "nodejs"))
    return [candidate for candidate in candidates if candidate]


def _wrapper_launcher_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".cmd", ".bat"}:
        return "wrapper_cmd"
    if suffix == ".ps1":
        return "wrapper_ps1"
    return "path_override"


def _wrapper_location_warning(wrapper_path: str, target_repo_path: str | None) -> str | None:
    if not target_repo_path:
        return None
    try:
        wrapper = Path(wrapper_path).resolve()
        target = Path(target_repo_path).resolve()
    except OSError:
        return None
    try:
        relative = wrapper.relative_to(target)
    except ValueError:
        return None
    parts = [part.lower() for part in relative.parts]
    if len(parts) >= 2 and parts[0] == "workspace" and parts[1] in {"tmp", "local"}:
        return None
    return (
        f"Codex wrapper is inside the target repository at {wrapper}. "
        "Use an external path or an ignored local path such as workspace/tmp so the wrapper is not accidentally committed."
    )


def _launcher_command_preview(diagnostic: CodexExecutableDiagnostic) -> str:
    if diagnostic.launcher_type == "wrapper_ps1" and diagnostic.wrapper_path:
        return f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File {diagnostic.wrapper_path} <prompt>"
    if diagnostic.launcher_type == "wrapper_cmd" and diagnostic.wrapper_path:
        return f"cmd.exe /d /c {diagnostic.wrapper_path} <prompt>"
    if diagnostic.wrapper_path:
        return f"{diagnostic.wrapper_path} <prompt>"
    if diagnostic.executable_path:
        return f"{diagnostic.executable_path} <prompt>"
    if diagnostic.launcher_type == "wsl_codex" and diagnostic.wsl_distribution:
        return f"wsl.exe -d {diagnostic.wsl_distribution} -- codex <prompt>"
    return "codex <prompt>"


def _plan_command_preview(diagnostic: CodexExecutableDiagnostic, prompt_path: str) -> str:
    return (diagnostic.command_preview or _launcher_command_preview(diagnostic)).replace("<prompt>", f"< {prompt_path}")


def _launcher_subprocess_args(diagnostic: CodexExecutableDiagnostic) -> list[str]:
    if diagnostic.launcher_type == "wrapper_ps1" and diagnostic.wrapper_path:
        powershell = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell.exe"
        return [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", diagnostic.wrapper_path]
    if diagnostic.launcher_type == "wrapper_cmd" and diagnostic.wrapper_path:
        command_processor = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
        return [command_processor, "/d", "/c", diagnostic.wrapper_path]
    if diagnostic.wrapper_path:
        return [diagnostic.wrapper_path]
    if diagnostic.executable_path:
        return [diagnostic.executable_path]
    return []


def _ensure_wrapper_template_location_is_safe(path: Path, workspace_root: Path) -> None:
    try:
        repo_root = Path.cwd().resolve()
        resolved = path.resolve()
    except OSError:
        return
    safe_workspace_roots = [
        (workspace_root / "tmp").resolve(),
        (workspace_root / "local").resolve(),
    ]
    if any(_is_relative_to(resolved, safe_root) for safe_root in safe_workspace_roots):
        return
    if _is_relative_to(resolved, repo_root):
        msg = (
            f"Refusing to create Codex wrapper template under committed source path: {resolved}. "
            "Use an external path or an ignored local path such as workspace/tmp."
        )
        raise ValueError(msg)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _render_cmd_wrapper_template() -> str:
    return "\r\n".join(
        [
            "@echo off",
            "rem Devo Codex launcher wrapper template.",
            "rem Edit CODEX_REAL_COMMAND to point at a real non-WindowsApps Codex executable.",
            "rem Do not store secrets in this file. Do not commit this wrapper unless it is intentionally reviewed.",
            "rem Keep this file in an ignored local path such as workspace\\tmp or outside the repository.",
            "",
            "set \"CODEX_REAL_COMMAND=C:\\Path\\To\\Real\\codex.exe\"",
            "if not exist \"%CODEX_REAL_COMMAND%\" (",
            "  echo CODEX_REAL_COMMAND does not exist: %CODEX_REAL_COMMAND% 1>&2",
            "  exit /b 127",
            ")",
            "",
            "\"%CODEX_REAL_COMMAND%\"",
            "exit /b %ERRORLEVEL%",
            "",
        ]
    )


def _codex_launcher_check_name(executable: CodexExecutableDiagnostic) -> str:
    if executable.launcher_type in {"wrapper_cmd", "wrapper_ps1"}:
        return "codex_wrapper"
    if executable.launcher_type == "wsl_codex":
        return "codex_wsl"
    if executable.executable_source == "path_override":
        return "codex_path_override"
    return "codex_path_detection"


def _codex_execution_blockers(
    worker_run: WorkerRun,
    plan: CodexRunPlan,
    *,
    codex_path: str | None = None,
    codex_wrapper: str | None = None,
    codex_wsl: str | None = None,
) -> tuple[list[str], list[str], CodexExecutableDiagnostic]:
    blocked_reasons: list[str] = []
    warnings: list[str] = list(plan.warnings)
    if plan.approval_status != "approved":
        blocked_reasons.append(f"Run plan approval status is {plan.approval_status}; approval is required before execution.")
    if plan.preflight_status == "blocked":
        blocked_reasons.append("Run plan preflight is blocked.")
    elif plan.preflight_status not in {"passed", "warnings"}:
        blocked_reasons.append(f"Run plan preflight status is {plan.preflight_status}; passed or warnings is required.")
    if plan.status == "blocked":
        blocked_reasons.extend(plan.blocked_reasons or ["Run plan status is blocked."])
    prompt_path = Path(plan.prompt_path)
    if not prompt_path.exists() or not prompt_path.is_file():
        blocked_reasons.append(f"Prompt file is missing: {prompt_path}.")
    target_repo_path = Path(plan.proposed_working_directory)
    if not target_repo_path.exists() or not target_repo_path.is_dir():
        blocked_reasons.append(f"Target repo path is missing: {target_repo_path}.")
    if Path(worker_run.target_repo_path) != Path(plan.proposed_working_directory):
        warnings.append("Run plan working directory differs from worker-run target repo path; review before execution.")
    executable = diagnose_codex_executable(
        codex_path or (None if (codex_wrapper or codex_wsl) else plan.codex_executable_path),
        codex_wrapper=codex_wrapper or (None if (codex_path or codex_wsl) else plan.codex_wrapper_path),
        codex_wsl=codex_wsl or (None if (codex_path or codex_wrapper) else plan.codex_wsl_distribution),
        target_repo_path=worker_run.target_repo_path,
    )
    if not (codex_path or codex_wrapper or codex_wsl) and (plan.codex_executable_path or plan.codex_wrapper_path or plan.codex_wsl_distribution):
        executable = executable.model_copy(
            update={
                "launcher_type": plan.launcher_type or executable.launcher_type,
                "executable_source": plan.codex_executable_source,
                "wrapper_path": plan.codex_wrapper_path or executable.wrapper_path,
                "wsl_distribution": plan.codex_wsl_distribution or executable.wsl_distribution,
                "command_resolution_note": plan.command_resolution_note or executable.command_resolution_note,
                "launch_risk": plan.launch_risk or executable.launch_risk,
                "launch_blockers": plan.launch_blockers or executable.launch_blockers,
                "launch_warnings": plan.launch_warnings or executable.launch_warnings,
                "execution_supported": executable.execution_supported and plan.launcher_type != "wsl_codex",
            }
        )
    if executable.launch_blockers:
        blocked_reasons.extend(executable.launch_blockers)
    elif executable.launcher_type == "not_found":
        blocked_reasons.append("Codex executable was not found on PATH.")
    elif not executable.execution_supported:
        blocked_reasons.append("Codex launcher is not supported for guarded execution.")
    elif codex_path and plan.codex_executable_path and Path(codex_path).resolve() != Path(plan.codex_executable_path).resolve():
        warnings.append("Execution is using --codex-path override that differs from the run-plan stored executable path.")
    elif codex_wrapper and plan.codex_wrapper_path and Path(codex_wrapper).resolve() != Path(plan.codex_wrapper_path).resolve():
        warnings.append("Execution is using --codex-wrapper override that differs from the run-plan stored wrapper path.")
    elif executable.executable_source == "path_override":
        warnings.append("Execution uses an explicit Codex executable path; confirm this is intended for dogfood/testing or controlled operation.")
    elif executable.launcher_type in {"wrapper_cmd", "wrapper_ps1"}:
        warnings.append("Execution uses an explicit Codex wrapper path; confirm the wrapper is local, reviewed, and not committed.")
    warnings.extend(executable.launch_warnings)
    return blocked_reasons, warnings, executable


def _execution_preview_next_action(project_name: str, worker_run_id: str, plan_id: str, blocked_reasons: list[str]) -> str:
    if blocked_reasons:
        return "Resolve execution blockers before running Codex."
    return (
        f"Run only when ready: devo worker codex execute --project {project_name} --run {worker_run_id} --plan {plan_id} --confirm-execute. "
        "After execution, manually review logs and import a worker report."
    )


def _classify_codex_execution_status(exit_code: int, stdout: str, stderr: str) -> str:
    combined = f"{stdout}\n{stderr}".lower()
    usage_limit_signals = ["usage limit", "rate limit", "quota", "limit reached", "too many requests"]
    approval_block_signals = ["approval required", "permission denied", "blocked by policy", "requires approval", "safety"]
    if any(signal in combined for signal in usage_limit_signals):
        return "paused_usage_limit"
    if any(signal in combined for signal in approval_block_signals):
        return "blocked_needs_approval"
    if exit_code == 0:
        return "waiting_review"
    return "failed"


def _codex_launch_exception_exit_code(exc: OSError) -> int:
    if isinstance(exc, FileNotFoundError):
        return 127
    if isinstance(exc, PermissionError):
        return 126
    return 1


def _render_codex_launch_failure_stderr(executable_path: str, error_type: str, error_message: str) -> str:
    return "\n".join(
        [
            "Codex failed to launch before producing output.",
            f"Executable: {executable_path}",
            f"Error type: {error_type}",
            f"Error message: {error_message}",
            "",
            "Next actions:",
            "- Run devo worker codex doctor.",
            "- Use --codex-path with a real non-WindowsApps executable or wrapper path.",
            "- Retry only after creating or updating a safe run-plan.",
            "",
        ]
    )


def _codex_launch_failure_next_action() -> str:
    return (
        "Review launch failure logs, run devo worker codex doctor, and use --codex-path with a real non-WindowsApps "
        "executable or wrapper before creating a new or updated run-plan. Do not complete queue/task state."
    )


def _execution_status_note(status: str, exit_code: int) -> str:
    if status == "waiting_review":
        return f"Supervised Codex process exited with code {exit_code}. Review logs and import a worker report before queue/task updates."
    if status == "paused_usage_limit":
        return f"Supervised Codex output looked like a usage limit pause. Exit code: {exit_code}."
    if status == "blocked_needs_approval":
        return f"Supervised Codex output looked like a safety or approval block. Exit code: {exit_code}."
    return f"Supervised Codex process failed or stopped with exit code {exit_code}. Review logs before deciding next action."


def _render_execution_log(plan: CodexRunPlan, started_at: datetime, completed_at: datetime, exit_code: int, stdout: str) -> str:
    return "\n".join(
        [
            f"# Codex Execution Log: {plan.worker_run_id}",
            "",
            f"Project: {plan.project}",
            f"Run plan: {plan.plan_id}",
            f"Started: {started_at.isoformat()}",
            f"Completed: {completed_at.isoformat()}",
            f"Exit code: {exit_code}",
            "",
            "Safety: this log is execution evidence only. It is not proof of completion, validation, review, commit, push, or queue/task completion.",
            "",
            "## Stdout",
            "",
            stdout or "",
            "",
        ]
    )


def _codex_preflight_result(
    project_name: str,
    worker_run_id: str,
    checks: list[CodexPreflightCheck],
    blocked_reasons: list[str],
    warnings: list[str],
) -> CodexPreflightResult:
    if blocked_reasons:
        status = "blocked"
        next_action = "Resolve blocked preflight checks before creating or using a Codex run plan."
    elif warnings:
        status = "warnings"
        next_action = f"Review warnings, then create a safe preview with devo worker codex run-plan --project {project_name} --run {worker_run_id}."
    else:
        status = "passed"
        next_action = f"Create a safe preview with devo worker codex run-plan --project {project_name} --run {worker_run_id}."
    return CodexPreflightResult(
        project=project_name,
        worker_run_id=worker_run_id,
        status=status,
        checks=checks,
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        next_action=next_action,
    )


def _run_plan_next_action(project_name: str, plan_id: str, preflight_status: str, blocked_reasons: list[str]) -> str:
    if blocked_reasons or preflight_status == "blocked":
        return f"Resolve blocked preflight checks, then recreate the run plan: devo worker codex run-plan --project {project_name} --run <workerRunId>."
    return (
        f"Inspect this run plan with devo worker codex run-plan-show --project {project_name} --plan {plan_id}. "
        "If approval is recorded and preflight is acceptable, use execute-preview before any guarded execute --confirm-execute run."
    )


def _reported_validation_summary(report: CodexWorkerReport) -> list[str]:
    values: list[str] = []
    if report.validation_results:
        values.extend(report.validation_results)
    if report.tests_run:
        values.extend(f"test: {item}" for item in report.tests_run)
    if report.commands_run:
        values.extend(f"command: {item}" for item in report.commands_run)
    return values


def _task_prompt_section(task: BacklogTask) -> list[str]:
    return [
        "## Task",
        "",
        f"- Task id: `{task.id}`",
        f"- Title: {task.title}",
        f"- Status: `{task.status}`",
        f"- Lane: `{task.lane}`",
        f"- Risk level: `{task.risk_level}`",
        f"- Milestone: `{task.milestone_id or 'none'}`",
        f"- Epic: `{task.epic_id or 'none'}`",
        "",
        "### Summary",
        "",
        task.summary or "No summary recorded.",
        "",
    ]


def _bullet_lines(values: list[str], fallback: str) -> list[str]:
    if not values:
        return [f"- {fallback}"]
    return [f"- {value}" for value in values]


def _summarize_batch_dict(values: dict[str, int], fallback: str) -> str:
    if not values:
        return fallback
    return ", ".join(f"{key} ({value})" for key, value in sorted(values.items()))


def _batch_acceptance(batch: ProjectBatch | None, tasks: list[BacklogTask]) -> list[str]:
    values: list[str] = []
    for task in tasks:
        values.extend(f"{task.id}: {item}" for item in task.acceptance_criteria)
    if values:
        return values
    if not batch:
        return []
    return [f"{snapshot.task_id}: {snapshot.acceptance_criteria_summary}" for snapshot in batch.task_snapshots if snapshot.acceptance_criteria_summary]


def _batch_validation(batch: ProjectBatch | None, tasks: list[BacklogTask]) -> list[str]:
    values: list[str] = []
    for task in tasks:
        values.extend(f"{task.id}: {item}" for item in task.validation_expectations)
    if values:
        return values
    if not batch:
        return []
    return [
        f"{snapshot.task_id}: {snapshot.validation_expectations_summary}"
        for snapshot in batch.task_snapshots
        if snapshot.validation_expectations_summary
    ]


def _collect_task_scope(tasks: list[BacklogTask], kind: str) -> list[str]:
    values: list[str] = []
    for task in tasks:
        source = task.allowed_scope if kind == "allowed" else task.forbidden_scope
        values.extend(f"{task.id}: {item}" for item in source)
    return values


def _default_milestones(brief: ProjectBrief) -> list[BlueprintMilestone]:
    goals = brief.goals[:3] or [brief.summary or brief.title]
    milestones: list[BlueprintMilestone] = []
    for index, goal in enumerate(goals, start=1):
        milestones.append(
            BlueprintMilestone(
                id=f"M{index:03d}",
                title=_short_title(goal, fallback=f"Milestone {index}"),
                summary=goal,
                target_outcome=f"Deliver the planned outcome for: {_short_title(goal, fallback=brief.title)}.",
            )
        )
    return milestones


def _default_epics(milestones: list[BlueprintMilestone]) -> list[BlueprintEpic]:
    epics = [
        BlueprintEpic(
            id="E001",
            milestone_id=milestones[0].id if milestones else None,
            title="Planning Foundation",
            summary="Convert the approved brief into structured backlog and execution planning artifacts.",
        ),
        BlueprintEpic(
            id="E002",
            milestone_id=milestones[0].id if milestones else None,
            title="Validation And Delivery",
            summary="Define validation expectations and delivery evidence before implementation batches start.",
        ),
    ]
    return epics


def _default_architecture_notes(brief: ProjectBrief) -> list[str]:
    notes = ["MVP blueprint is deterministic and template-based; no AI or Codex automation was used."]
    notes.extend(brief.tech_stack_notes[:5])
    return notes


def _default_risk_summary(brief: ProjectBrief) -> list[str]:
    if brief.risks:
        return brief.risks
    return ["Risks need review before backlog and batch approval."]


def _default_validation_strategy(brief: ProjectBrief) -> list[str]:
    if brief.validation_expectations:
        return brief.validation_expectations
    return ["Define registered validation commands before approving implementation batches."]


def _default_open_questions(brief: ProjectBrief) -> list[str]:
    questions = ["What is the smallest useful first implementation batch?"]
    if not brief.goals:
        questions.append("Which concrete goals should be promoted into backlog tasks?")
    if not brief.validation_expectations:
        questions.append("What validation evidence should each batch produce?")
    return questions


def _read_planning_text_file(path: Path) -> str:
    return _clean_planning_text(path.read_text(encoding="utf-8-sig"))


def _clean_planning_text(text: str) -> str:
    return text.replace("\ufeff", "")


def _extract_section(text: str, headings: tuple[str, ...]) -> str:
    text = _clean_planning_text(text)
    items = _extract_list_section(text, headings)
    return " ".join(items).strip()


def _extract_list_section(text: str, headings: tuple[str, ...]) -> list[str]:
    text = _clean_planning_text(text)
    lines = text.splitlines()
    captured: list[str] = []
    in_section = False
    for raw_line in lines:
        line = raw_line.strip()
        heading = _normalize_heading(line)
        if heading:
            if in_section:
                break
            if heading in headings:
                in_section = True
            continue
        if not in_section or not line:
            continue
        captured.append(_clean_list_item(line))
    return captured[:20]


def _normalize_heading(line: str) -> str | None:
    stripped = line.strip().strip(":").strip()
    if not stripped:
        return None
    stripped = re.sub(r"^#{1,6}\s*", "", stripped).strip()
    if stripped != line.strip().strip(":").strip() or line.endswith(":"):
        return stripped.lower()
    return None


def _clean_list_item(line: str) -> str:
    return re.sub(r"^[-*0-9.)\s]+", "", line).strip()


def _summarize_text(text: str) -> str:
    text = _clean_planning_text(text)
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        cleaned = " ".join(line.strip().lstrip("#").strip() for line in paragraph.splitlines() if line.strip())
        if cleaned:
            return cleaned[:500]
    return "No summary recorded."


def _short_title(value: str, fallback: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .")
    if not cleaned:
        return fallback
    return cleaned[:80]


def _append_list_section(lines: list[str], title: str, values: list[str]) -> None:
    lines.extend([f"## {title}", ""])
    if values:
        for value in values:
            lines.append(f"- {value}")
    else:
        lines.append("No items recorded.")
    lines.append("")


def _append_preflight_section(lines: list[str], checks: list[CodexPreflightCheck]) -> None:
    lines.extend(["## Preflight Checks", ""])
    if checks:
        for check in checks:
            lines.append(f"- `{check.status}` {check.name}: {check.detail}")
    else:
        lines.append("No preflight checks recorded.")
    lines.append("")


def _append_mapping_section(lines: list[str], title: str, values: dict[str, int]) -> None:
    lines.extend([f"## {title}", ""])
    if values:
        for key, value in sorted(values.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("No items recorded.")
    lines.append("")


def _append_progress_groups(lines: list[str], groups: list[PlanningProgressGroup]) -> None:
    if not groups:
        lines.extend(["No progress groups recorded.", ""])
        return
    for group in groups:
        label = f"{group.id}: {group.title}" if group.title else group.id
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Tasks: `{group.task_count}`",
                f"- Completed: `{group.completed_task_count}`",
                f"- Blocked: `{group.blocked_task_count}`",
                f"- Completion: `{group.completion_percent:.1f}%`",
                f"- Readiness: `{group.readiness_percent:.1f}%`",
                "",
            ]
        )


def _write_model(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _require_project(project_name: str, workspace_root: Path) -> None:
    load_registered_project(project_name, workspace_root=workspace_root)
