from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from .backups import list_backup_inventory
from .delivery import (
    build_delivery_latest_summary,
    list_delivery_checks,
    list_delivery_plans,
    list_delivery_reports,
    list_delivery_runner_requests,
    load_delivery_runner_run,
)
from .doctor import run_doctor_with_timing
from .git_delivery import get_git_repository_status
from .project_onboarding import build_project_onboarding_report
from .project_planning import (
    calculate_project_progress,
    get_codex_queue_worker_status,
    get_patch_proposal_summary,
    list_batch_approvals,
    list_codex_handoffs,
    list_codex_run_plans,
    list_codex_worker_reports,
    list_codex_worker_reviews,
    list_codex_worker_runs,
    list_project_batches,
    list_execution_policies,
    list_execution_queues,
    list_queue_worker_runs,
    load_codex_worker_run,
    load_project_backlog,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
)
from .project_settings import load_project_settings, project_settings_path
from .projects import get_workspace_root
from .runs import list_runs, load_current_selection, load_run
from .scanner import load_registered_project
from .validation_registry import list_validation_commands, registry_path
from .validation_runner import list_validation_history
from .work_history import build_project_activity_summary, list_work_package_summaries
from .work_packages import WorkPackage, get_work_package_next_step, load_work_package

READ_MODEL_SCHEMA_VERSION = "1"


class WorkPackageOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = READ_MODEL_SCHEMA_VERSION
    project_name: str
    run_id: str
    goal: str | None = None
    lane: str = "unknown"
    status: str = "unknown"
    scope_status: str = "unknown"
    approval_status: str = "unknown"
    validation_status: str = "unknown"
    delivery_status: str = "unknown"
    next_phase: str = "unknown"
    next_command: str | None = None
    stop_conditions_summary: list[str] = Field(default_factory=list)


class PatchProposalOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = READ_MODEL_SCHEMA_VERSION
    project_name: str
    queue_worker_run_id: str
    worker_evidence_id: str | None = None
    worker_status: str | None = None
    patch_proposal_present: bool = False
    patch_artifact_path: str | None = None
    patch_artifact_exists: bool = False
    linked_policy_id: str | None = None
    queue_item_id: str | None = None
    task_id: str | None = None
    safe_next_action: str = "unknown"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RunOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = READ_MODEL_SCHEMA_VERSION
    project_name: str
    run_id: str
    goal: str = "unknown"
    run_status: str = "unknown"
    work_package_status: str = "not available"
    lane: str | None = None
    approval_bundle_status: str | None = None
    latest_validation_status: str = "none"
    latest_validation_run_id: str | None = None
    delivery_commit: str | None = None
    delivery_summary: str | None = None
    generated_visual_reports: list[str] = Field(default_factory=list)
    suggested_next_action: str = "unknown"
    work_package: WorkPackageOverview | None = None


class ProjectOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = READ_MODEL_SCHEMA_VERSION
    project_name: str
    project_path: str | None = None
    is_current_project: bool = False
    current_run_id: str | None = None
    onboarding_status: str = "unknown"
    doctor_overall_status: str = "unknown"
    settings_summary: dict[str, object] = Field(default_factory=dict)
    git_summary: dict[str, object] = Field(default_factory=dict)
    validation_registry_summary: dict[str, object] = Field(default_factory=dict)
    backup_summary: dict[str, object] = Field(default_factory=dict)
    delivery_check_count: int = 0
    latest_delivery_id: str | None = None
    latest_delivery_readiness_status: str | None = None
    latest_delivery_blocker_count: int = 0
    latest_delivery_warning_count: int = 0
    delivery_next_action: str | None = None
    delivery_plan_count: int = 0
    latest_delivery_plan_id: str | None = None
    latest_delivery_plan_status: str | None = None
    latest_delivery_approval_status: str | None = None
    latest_delivery_plan_next_action: str | None = None
    delivery_report_count: int = 0
    latest_delivery_report_id: str | None = None
    latest_delivery_report_status: str | None = None
    latest_delivery_commit_ready: bool = False
    latest_delivery_push_ready: bool = False
    latest_delivery_report_next_action: str | None = None
    latest_delivery_commit_hash: str | None = None
    latest_delivery_commit_status: str | None = None
    latest_delivery_pushed: bool = False
    latest_delivery_commit_next_action: str | None = None
    latest_delivery_push_status: str | None = None
    latest_delivery_push_remote: str | None = None
    latest_delivery_push_branch: str | None = None
    latest_delivery_pushed_at: str | None = None
    latest_delivery_push_next_action: str | None = None
    latest_delivery_summary_status: str | None = None
    latest_delivery_summary_id: str | None = None
    latest_delivery_summary_kind: str | None = None
    latest_delivery_summary_next_action: str | None = None
    current_repo_has_pending_changes: bool = False
    current_repo_is_clean: bool = False
    latest_meaningful_delivery_id: str | None = None
    latest_pushed_delivery_id: str | None = None
    latest_runner_request_id: str | None = None
    latest_runner_request_status: str | None = None
    latest_runner_run_id: str | None = None
    latest_runner_run_status: str | None = None
    latest_runner_commit_hash: str | None = None
    latest_runner_pushed: bool | None = None
    latest_runner_next_action: str | None = None
    brief_status: str = "missing"
    blueprint_status: str = "missing"
    blueprint_milestone_count: int = 0
    blueprint_epic_count: int = 0
    backlog_status: str = "missing"
    backlog_task_count: int = 0
    backlog_ready_count: int = 0
    backlog_blocked_count: int = 0
    backlog_completed_count: int = 0
    backlog_refinement_prompt_exists: bool = False
    backlog_refinement_prompt_path: str | None = None
    batch_count: int = 0
    approved_batch_count: int = 0
    latest_batch_id: str | None = None
    latest_batch_status: str | None = None
    latest_batch_approval_status: str | None = None
    latest_batch_review_status: str | None = None
    batch_approval_requested_count: int = 0
    batch_approved_count: int = 0
    batch_rejected_count: int = 0
    batch_needs_changes_count: int = 0
    batch_approval_next_action: str = "Create a Project Brief."
    execution_policy_count: int = 0
    approved_execution_policy_count: int = 0
    latest_execution_policy_id: str | None = None
    latest_execution_policy_status: str | None = None
    latest_execution_policy_batch_id: str | None = None
    latest_execution_policy_queue_id: str | None = None
    execution_policy_next_action: str = "Create a Project Brief."
    queue_count: int = 0
    latest_queue_id: str | None = None
    latest_queue_status: str | None = None
    current_queue_item: str | None = None
    queue_pending_count: int = 0
    queue_completed_count: int = 0
    queue_blocked_count: int = 0
    queue_next_action: str = "Create a Project Brief."
    linked_worker_run_id: str | None = None
    linked_worker_run_status: str | None = None
    linked_run_plan_id: str | None = None
    current_queue_item_worker_status: str | None = None
    current_queue_item_review_status: str | None = None
    current_queue_item_completion_ready: bool = False
    current_queue_item_completion_blockers: list[str] = Field(default_factory=list)
    current_queue_item_validation_status: str | None = None
    queue_worker_next_action: str | None = None
    queue_worker_run_count: int = 0
    latest_queue_worker_run_id: str | None = None
    latest_queue_worker_run_status: str | None = None
    latest_queue_worker_run_policy_id: str | None = None
    latest_queue_worker_run_selected_item: str | None = None
    latest_queue_worker_run_selected_task: str | None = None
    latest_queue_worker_run_worker_run_id: str | None = None
    latest_queue_worker_run_delivery_request_id: str | None = None
    latest_queue_worker_run_delivery_request_status: str | None = None
    latest_queue_worker_run_next_action: str | None = None
    handoff_count: int = 0
    latest_handoff_id: str | None = None
    latest_handoff_type: str | None = None
    latest_handoff_status: str | None = None
    latest_handoff_path: str | None = None
    handoff_next_action: str = "Create a Project Brief."
    worker_run_count: int = 0
    latest_worker_run_id: str | None = None
    latest_worker_run_status: str | None = None
    latest_worker_run_next_action: str | None = None
    latest_worker_execution_status: str | None = None
    latest_worker_execution_exit_code: int | None = None
    latest_worker_execution_log_path: str | None = None
    latest_worker_execution_next_action: str | None = None
    latest_worker_report_status: str | None = None
    latest_worker_report_path: str | None = None
    latest_worker_report_summary: str | None = None
    latest_worker_report_next_action: str | None = None
    latest_worker_review_id: str | None = None
    latest_worker_review_status: str | None = None
    latest_worker_validation_status: str | None = None
    latest_worker_review_reviewer: str | None = None
    latest_worker_review_decision_note: str | None = None
    review_next_action: str | None = None
    codex_run_plan_count: int = 0
    latest_codex_run_plan_id: str | None = None
    latest_codex_run_plan_status: str | None = None
    latest_codex_preflight_status: str | None = None
    latest_codex_run_plan_next_action: str | None = None
    project_completion_percent: float = 0.0
    backlog_readiness_percent: float = 0.0
    blocked_percent: float = 0.0
    batch_completion_percent: float = 0.0
    progress_next_action: str = "Create a Project Brief."
    planning_next_action: str = "Create a Project Brief."
    recent_runs: list[RunOverview] = Field(default_factory=list)
    recent_work_packages: list[WorkPackageOverview] = Field(default_factory=list)
    suggested_next_action: str = "unknown"


def build_project_overview(project_name: str, limit: int = 10, workspace_root: Path | None = None) -> ProjectOverview:
    overview, _timing = build_project_overview_with_timing(project_name, limit=limit, workspace_root=workspace_root)
    return overview


def build_project_overview_with_timing(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> tuple[ProjectOverview, dict[str, float]]:
    root = workspace_root or get_workspace_root()
    safe_limit = _safe_limit(limit)
    timing: dict[str, float] = {}
    started = perf_counter()
    selection = _timed("current_ms", timing, lambda: load_current_selection(workspace_root=root))
    registration = _timed("registration_ms", timing, lambda: _safe_project_registration(project_name, root))
    onboarding = _timed("onboarding_ms", timing, lambda: _safe_onboarding_status(project_name, root))
    doctor = _timed("doctor_ms", timing, lambda: _safe_doctor_status(project_name, root))
    activity = _timed("activity_ms", timing, lambda: _safe_project_activity(project_name, safe_limit, root))
    runs = _timed("recent_runs_ms", timing, lambda: _safe_recent_runs(project_name, safe_limit, root))
    work = _timed("recent_work_packages_ms", timing, lambda: _safe_recent_work_packages(project_name, safe_limit, root))
    settings = _timed("settings_ms", timing, lambda: _settings_summary(project_name, root))
    git = _timed("git_ms", timing, lambda: _git_summary(project_name, root))
    validation = _timed("validation_registry_ms", timing, lambda: _validation_registry_summary(project_name, root))
    planning = _timed("planning_ms", timing, lambda: _planning_summary(project_name, root))
    delivery = _timed("delivery_ms", timing, lambda: _delivery_summary(project_name, root))
    backup = _timed("backup_ms", timing, _backup_summary)
    timing["total_ms"] = _elapsed_ms(started)
    planning_next_action = str(planning["planning_next_action"])
    suggested_next_action = planning_next_action
    return (
        ProjectOverview(
            project_name=project_name,
            project_path=str(registration.path) if registration else None,
            is_current_project=bool(selection and selection.project_name == project_name),
            current_run_id=selection.run_id if selection and selection.project_name == project_name else None,
            onboarding_status=onboarding,
            doctor_overall_status=doctor,
            settings_summary=settings,
            git_summary=git,
            validation_registry_summary=validation,
            backup_summary=backup,
            delivery_check_count=int(delivery["delivery_check_count"]),
            latest_delivery_id=str(delivery["latest_delivery_id"]) if delivery["latest_delivery_id"] else None,
            latest_delivery_readiness_status=(
                str(delivery["latest_delivery_readiness_status"]) if delivery["latest_delivery_readiness_status"] else None
            ),
            latest_delivery_blocker_count=int(delivery["latest_delivery_blocker_count"]),
            latest_delivery_warning_count=int(delivery["latest_delivery_warning_count"]),
            delivery_next_action=str(delivery["delivery_next_action"]) if delivery["delivery_next_action"] else None,
            delivery_plan_count=int(delivery["delivery_plan_count"]),
            latest_delivery_plan_id=str(delivery["latest_delivery_plan_id"]) if delivery["latest_delivery_plan_id"] else None,
            latest_delivery_plan_status=str(delivery["latest_delivery_plan_status"]) if delivery["latest_delivery_plan_status"] else None,
            latest_delivery_approval_status=(
                str(delivery["latest_delivery_approval_status"]) if delivery["latest_delivery_approval_status"] else None
            ),
            latest_delivery_plan_next_action=(
                str(delivery["latest_delivery_plan_next_action"]) if delivery["latest_delivery_plan_next_action"] else None
            ),
            delivery_report_count=int(delivery["delivery_report_count"]),
            latest_delivery_report_id=str(delivery["latest_delivery_report_id"]) if delivery["latest_delivery_report_id"] else None,
            latest_delivery_report_status=(
                str(delivery["latest_delivery_report_status"]) if delivery["latest_delivery_report_status"] else None
            ),
            latest_delivery_commit_ready=bool(delivery["latest_delivery_commit_ready"]),
            latest_delivery_push_ready=bool(delivery["latest_delivery_push_ready"]),
            latest_delivery_report_next_action=(
                str(delivery["latest_delivery_report_next_action"]) if delivery["latest_delivery_report_next_action"] else None
            ),
            latest_delivery_commit_hash=str(delivery["latest_delivery_commit_hash"]) if delivery["latest_delivery_commit_hash"] else None,
            latest_delivery_commit_status=(
                str(delivery["latest_delivery_commit_status"]) if delivery["latest_delivery_commit_status"] else None
            ),
            latest_delivery_pushed=bool(delivery["latest_delivery_pushed"]),
            latest_delivery_commit_next_action=(
                str(delivery["latest_delivery_commit_next_action"]) if delivery["latest_delivery_commit_next_action"] else None
            ),
            latest_delivery_push_status=str(delivery["latest_delivery_push_status"]) if delivery["latest_delivery_push_status"] else None,
            latest_delivery_push_remote=str(delivery["latest_delivery_push_remote"]) if delivery["latest_delivery_push_remote"] else None,
            latest_delivery_push_branch=str(delivery["latest_delivery_push_branch"]) if delivery["latest_delivery_push_branch"] else None,
            latest_delivery_pushed_at=str(delivery["latest_delivery_pushed_at"]) if delivery["latest_delivery_pushed_at"] else None,
            latest_delivery_push_next_action=(
                str(delivery["latest_delivery_push_next_action"]) if delivery["latest_delivery_push_next_action"] else None
            ),
            latest_delivery_summary_status=(
                str(delivery["latest_delivery_summary_status"]) if delivery["latest_delivery_summary_status"] else None
            ),
            latest_delivery_summary_id=str(delivery["latest_delivery_summary_id"]) if delivery["latest_delivery_summary_id"] else None,
            latest_delivery_summary_kind=(
                str(delivery["latest_delivery_summary_kind"]) if delivery["latest_delivery_summary_kind"] else None
            ),
            latest_delivery_summary_next_action=(
                str(delivery["latest_delivery_summary_next_action"]) if delivery["latest_delivery_summary_next_action"] else None
            ),
            current_repo_has_pending_changes=bool(delivery["current_repo_has_pending_changes"]),
            current_repo_is_clean=bool(delivery["current_repo_is_clean"]),
            latest_meaningful_delivery_id=(
                str(delivery["latest_meaningful_delivery_id"]) if delivery["latest_meaningful_delivery_id"] else None
            ),
            latest_pushed_delivery_id=str(delivery["latest_pushed_delivery_id"]) if delivery["latest_pushed_delivery_id"] else None,
            latest_runner_request_id=str(delivery["latest_runner_request_id"]) if delivery["latest_runner_request_id"] else None,
            latest_runner_request_status=(
                str(delivery["latest_runner_request_status"]) if delivery["latest_runner_request_status"] else None
            ),
            latest_runner_run_id=str(delivery["latest_runner_run_id"]) if delivery["latest_runner_run_id"] else None,
            latest_runner_run_status=str(delivery["latest_runner_run_status"]) if delivery["latest_runner_run_status"] else None,
            latest_runner_commit_hash=str(delivery["latest_runner_commit_hash"]) if delivery["latest_runner_commit_hash"] else None,
            latest_runner_pushed=(
                bool(delivery["latest_runner_pushed"]) if delivery["latest_runner_pushed"] is not None else None
            ),
            latest_runner_next_action=str(delivery["latest_runner_next_action"]) if delivery["latest_runner_next_action"] else None,
            brief_status=str(planning["brief_status"]),
            blueprint_status=str(planning["blueprint_status"]),
            blueprint_milestone_count=int(planning["blueprint_milestone_count"]),
            blueprint_epic_count=int(planning["blueprint_epic_count"]),
            backlog_status=str(planning["backlog_status"]),
            backlog_task_count=int(planning["backlog_task_count"]),
            backlog_ready_count=int(planning["backlog_ready_count"]),
            backlog_blocked_count=int(planning["backlog_blocked_count"]),
            backlog_completed_count=int(planning["backlog_completed_count"]),
            backlog_refinement_prompt_exists=bool(planning["backlog_refinement_prompt_exists"]),
            backlog_refinement_prompt_path=str(planning["backlog_refinement_prompt_path"]) if planning["backlog_refinement_prompt_path"] else None,
            batch_count=int(planning["batch_count"]),
            approved_batch_count=int(planning["approved_batch_count"]),
            latest_batch_id=str(planning["latest_batch_id"]) if planning["latest_batch_id"] else None,
            latest_batch_status=str(planning["latest_batch_status"]) if planning["latest_batch_status"] else None,
            latest_batch_approval_status=str(planning["latest_batch_approval_status"]) if planning["latest_batch_approval_status"] else None,
            latest_batch_review_status=str(planning["latest_batch_review_status"]) if planning["latest_batch_review_status"] else None,
            batch_approval_requested_count=int(planning["batch_approval_requested_count"]),
            batch_approved_count=int(planning["batch_approved_count"]),
            batch_rejected_count=int(planning["batch_rejected_count"]),
            batch_needs_changes_count=int(planning["batch_needs_changes_count"]),
            batch_approval_next_action=str(planning["batch_approval_next_action"]),
            execution_policy_count=int(planning["execution_policy_count"]),
            approved_execution_policy_count=int(planning["approved_execution_policy_count"]),
            latest_execution_policy_id=str(planning["latest_execution_policy_id"]) if planning["latest_execution_policy_id"] else None,
            latest_execution_policy_status=str(planning["latest_execution_policy_status"]) if planning["latest_execution_policy_status"] else None,
            latest_execution_policy_batch_id=str(planning["latest_execution_policy_batch_id"]) if planning["latest_execution_policy_batch_id"] else None,
            latest_execution_policy_queue_id=str(planning["latest_execution_policy_queue_id"]) if planning["latest_execution_policy_queue_id"] else None,
            execution_policy_next_action=str(planning["execution_policy_next_action"]),
            queue_count=int(planning["queue_count"]),
            latest_queue_id=str(planning["latest_queue_id"]) if planning["latest_queue_id"] else None,
            latest_queue_status=str(planning["latest_queue_status"]) if planning["latest_queue_status"] else None,
            current_queue_item=str(planning["current_queue_item"]) if planning["current_queue_item"] else None,
            queue_pending_count=int(planning["queue_pending_count"]),
            queue_completed_count=int(planning["queue_completed_count"]),
            queue_blocked_count=int(planning["queue_blocked_count"]),
            queue_next_action=str(planning["queue_next_action"]),
            linked_worker_run_id=str(planning["linked_worker_run_id"]) if planning["linked_worker_run_id"] else None,
            linked_worker_run_status=str(planning["linked_worker_run_status"]) if planning["linked_worker_run_status"] else None,
            linked_run_plan_id=str(planning["linked_run_plan_id"]) if planning["linked_run_plan_id"] else None,
            current_queue_item_worker_status=(
                str(planning["current_queue_item_worker_status"]) if planning["current_queue_item_worker_status"] else None
            ),
            current_queue_item_review_status=(
                str(planning["current_queue_item_review_status"]) if planning["current_queue_item_review_status"] else None
            ),
            current_queue_item_completion_ready=bool(planning["current_queue_item_completion_ready"]),
            current_queue_item_completion_blockers=list(planning["current_queue_item_completion_blockers"]),
            current_queue_item_validation_status=(
                str(planning["current_queue_item_validation_status"]) if planning["current_queue_item_validation_status"] else None
            ),
            queue_worker_next_action=str(planning["queue_worker_next_action"]) if planning["queue_worker_next_action"] else None,
            queue_worker_run_count=int(planning["queue_worker_run_count"]),
            latest_queue_worker_run_id=str(planning["latest_queue_worker_run_id"]) if planning["latest_queue_worker_run_id"] else None,
            latest_queue_worker_run_status=str(planning["latest_queue_worker_run_status"]) if planning["latest_queue_worker_run_status"] else None,
            latest_queue_worker_run_policy_id=str(planning["latest_queue_worker_run_policy_id"]) if planning["latest_queue_worker_run_policy_id"] else None,
            latest_queue_worker_run_selected_item=(
                str(planning["latest_queue_worker_run_selected_item"]) if planning["latest_queue_worker_run_selected_item"] else None
            ),
            latest_queue_worker_run_selected_task=(
                str(planning["latest_queue_worker_run_selected_task"]) if planning["latest_queue_worker_run_selected_task"] else None
            ),
            latest_queue_worker_run_worker_run_id=(
                str(planning["latest_queue_worker_run_worker_run_id"]) if planning["latest_queue_worker_run_worker_run_id"] else None
            ),
            latest_queue_worker_run_delivery_request_id=(
                str(planning["latest_queue_worker_run_delivery_request_id"]) if planning["latest_queue_worker_run_delivery_request_id"] else None
            ),
            latest_queue_worker_run_delivery_request_status=(
                str(planning["latest_queue_worker_run_delivery_request_status"]) if planning["latest_queue_worker_run_delivery_request_status"] else None
            ),
            latest_queue_worker_run_next_action=(
                str(planning["latest_queue_worker_run_next_action"]) if planning["latest_queue_worker_run_next_action"] else None
            ),
            handoff_count=int(planning["handoff_count"]),
            latest_handoff_id=str(planning["latest_handoff_id"]) if planning["latest_handoff_id"] else None,
            latest_handoff_type=str(planning["latest_handoff_type"]) if planning["latest_handoff_type"] else None,
            latest_handoff_status=str(planning["latest_handoff_status"]) if planning["latest_handoff_status"] else None,
            latest_handoff_path=str(planning["latest_handoff_path"]) if planning["latest_handoff_path"] else None,
            handoff_next_action=str(planning["handoff_next_action"]),
            worker_run_count=int(planning["worker_run_count"]),
            latest_worker_run_id=str(planning["latest_worker_run_id"]) if planning["latest_worker_run_id"] else None,
            latest_worker_run_status=str(planning["latest_worker_run_status"]) if planning["latest_worker_run_status"] else None,
            latest_worker_run_next_action=str(planning["latest_worker_run_next_action"]) if planning["latest_worker_run_next_action"] else None,
            latest_worker_execution_status=str(planning["latest_worker_execution_status"]) if planning["latest_worker_execution_status"] else None,
            latest_worker_execution_exit_code=(
                int(planning["latest_worker_execution_exit_code"]) if planning["latest_worker_execution_exit_code"] is not None else None
            ),
            latest_worker_execution_log_path=str(planning["latest_worker_execution_log_path"]) if planning["latest_worker_execution_log_path"] else None,
            latest_worker_execution_next_action=str(planning["latest_worker_execution_next_action"]) if planning["latest_worker_execution_next_action"] else None,
            latest_worker_report_status=str(planning["latest_worker_report_status"]) if planning["latest_worker_report_status"] else None,
            latest_worker_report_path=str(planning["latest_worker_report_path"]) if planning["latest_worker_report_path"] else None,
            latest_worker_report_summary=str(planning["latest_worker_report_summary"]) if planning["latest_worker_report_summary"] else None,
            latest_worker_report_next_action=str(planning["latest_worker_report_next_action"]) if planning["latest_worker_report_next_action"] else None,
            latest_worker_review_id=str(planning["latest_worker_review_id"]) if planning["latest_worker_review_id"] else None,
            latest_worker_review_status=str(planning["latest_worker_review_status"]) if planning["latest_worker_review_status"] else None,
            latest_worker_validation_status=(
                str(planning["latest_worker_validation_status"]) if planning["latest_worker_validation_status"] else None
            ),
            latest_worker_review_reviewer=str(planning["latest_worker_review_reviewer"]) if planning["latest_worker_review_reviewer"] else None,
            latest_worker_review_decision_note=(
                str(planning["latest_worker_review_decision_note"]) if planning["latest_worker_review_decision_note"] else None
            ),
            review_next_action=str(planning["review_next_action"]) if planning["review_next_action"] else None,
            codex_run_plan_count=int(planning["codex_run_plan_count"]),
            latest_codex_run_plan_id=str(planning["latest_codex_run_plan_id"]) if planning["latest_codex_run_plan_id"] else None,
            latest_codex_run_plan_status=str(planning["latest_codex_run_plan_status"]) if planning["latest_codex_run_plan_status"] else None,
            latest_codex_preflight_status=str(planning["latest_codex_preflight_status"]) if planning["latest_codex_preflight_status"] else None,
            latest_codex_run_plan_next_action=str(planning["latest_codex_run_plan_next_action"]) if planning["latest_codex_run_plan_next_action"] else None,
            project_completion_percent=float(planning["project_completion_percent"]),
            backlog_readiness_percent=float(planning["backlog_readiness_percent"]),
            blocked_percent=float(planning["blocked_percent"]),
            batch_completion_percent=float(planning["batch_completion_percent"]),
            progress_next_action=str(planning["progress_next_action"]),
            planning_next_action=str(planning["planning_next_action"]),
            recent_runs=runs,
            recent_work_packages=work,
            suggested_next_action=suggested_next_action,
        ),
        timing,
    )


def build_run_overview(project_name: str, run_id: str, workspace_root: Path | None = None) -> RunOverview:
    root = workspace_root or get_workspace_root()
    try:
        run = load_run(project_name, run_id, workspace_root=root)
    except ValueError:
        return RunOverview(project_name=project_name, run_id=run_id, suggested_next_action="Run not found.")

    latest_validation = _latest_validation(project_name, run_id, root)
    visual_reports = _visual_reports_for_run(project_name, run_id, root)
    try:
        package = load_work_package(project_name, run_id, workspace_root=root)
    except ValueError:
        return RunOverview(
            project_name=project_name,
            run_id=run_id,
            goal=run.goal,
            run_status=run.status.value,
            latest_validation_status=_validation_status(latest_validation),
            latest_validation_run_id=getattr(latest_validation, "validation_run_id", None),
            generated_visual_reports=visual_reports,
            suggested_next_action="No work-package artifact found.",
        )

    work_overview = build_work_package_overview(project_name, run_id, workspace_root=root)
    return RunOverview(
        project_name=project_name,
        run_id=run_id,
        goal=run.goal,
        run_status=run.status.value,
        work_package_status=package.status.value,
        lane=package.lane,
        approval_bundle_status=package.approval_bundle_status,
        latest_validation_status=_validation_status(latest_validation, package.validation_status),
        latest_validation_run_id=getattr(latest_validation, "validation_run_id", None) or package.validation_run_id,
        delivery_commit=package.commit_hash,
        delivery_summary=package.delivery_summary,
        generated_visual_reports=visual_reports,
        suggested_next_action=work_overview.next_phase,
        work_package=work_overview,
    )


def build_work_package_overview(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkPackageOverview:
    root = workspace_root or get_workspace_root()
    try:
        package = load_work_package(project_name, run_id, workspace_root=root)
    except ValueError:
        return WorkPackageOverview(
            project_name=project_name,
            run_id=run_id,
            status="not available",
            scope_status="missing work-package artifact",
            next_phase="No work-package artifact found.",
        )
    next_step = get_work_package_next_step(package)
    return WorkPackageOverview(
        project_name=package.project,
        run_id=package.run_id,
        goal=package.goal,
        lane=package.lane,
        status=package.status.value,
        scope_status=_scope_status(package),
        approval_status=package.approval_bundle_status or ("requested" if package.approval_bundle_id else "not requested"),
        validation_status=package.validation_status or "not available",
        delivery_status=_delivery_status(package),
        next_phase=next_step.next_action,
        next_command=next_step.required_command or next_step.suggested_prompt_command,
        stop_conditions_summary=list(next_step.stop_conditions),
    )


def build_patch_proposal_overview(project_name: str, run_id: str, workspace_root: Path | None = None) -> PatchProposalOverview:
    root = workspace_root or get_workspace_root()
    try:
        summary = get_patch_proposal_summary(project_name, run_id, workspace_root=root)
    except ValueError as exc:
        return PatchProposalOverview(
            project_name=project_name,
            queue_worker_run_id=run_id,
            patch_proposal_present=False,
            safe_next_action=f"Patch proposal unavailable: {exc}",
            blockers=[str(exc)],
        )
    return PatchProposalOverview(
        project_name=summary.project,
        queue_worker_run_id=summary.queue_worker_run_id,
        worker_evidence_id=summary.worker_evidence_id,
        worker_status=summary.worker_status,
        patch_proposal_present=summary.patch_proposal_present,
        patch_artifact_path=summary.patch_artifact_path,
        patch_artifact_exists=summary.patch_artifact_exists,
        linked_policy_id=summary.linked_policy_id,
        queue_item_id=summary.queue_item_id,
        task_id=summary.task_id,
        safe_next_action=summary.safe_next_action,
        blockers=list(summary.blockers),
        warnings=list(summary.warnings),
    )


def _safe_project_registration(project_name: str, workspace_root: Path):
    try:
        return load_registered_project(project_name, workspace_root=workspace_root)
    except ValueError:
        return None


def _safe_onboarding_status(project_name: str, workspace_root: Path) -> str:
    try:
        return build_project_onboarding_report(project_name, include_doctor=False, workspace_root=workspace_root).overall_status.value
    except Exception:
        return "unknown"


def _safe_doctor_status(project_name: str, workspace_root: Path) -> str:
    try:
        report, _timing = run_doctor_with_timing(project_name=project_name, workspace_root=workspace_root)
        return report.overall_status.value
    except Exception:
        return "unknown"


def _safe_project_activity(project_name: str, limit: int, workspace_root: Path):
    try:
        return build_project_activity_summary(project_name, limit=limit, workspace_root=workspace_root)
    except ValueError:
        return None


def _safe_recent_runs(project_name: str, limit: int, workspace_root: Path) -> list[RunOverview]:
    try:
        runs = sorted(list_runs(project_name, workspace_root=workspace_root), key=lambda item: item.updated_at, reverse=True)
    except ValueError:
        return []
    return [build_run_overview(project_name, run.run_id, workspace_root=workspace_root) for run in runs[:limit]]


def _safe_recent_work_packages(project_name: str, limit: int, workspace_root: Path) -> list[WorkPackageOverview]:
    try:
        summaries = list_work_package_summaries(project_name, limit=limit, workspace_root=workspace_root)
    except ValueError:
        return []
    return [
        build_work_package_overview(project_name, summary.run_id, workspace_root=workspace_root)
        for summary in summaries
        if summary.has_work_package
    ]


def _settings_summary(project_name: str, workspace_root: Path) -> dict[str, object]:
    try:
        path = project_settings_path(project_name, workspace_root=workspace_root)
        settings = load_project_settings(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return {"status": "unavailable", "detail": str(exc)}
    return {
        "status": "configured" if path.exists() else "missing",
        "path": str(path),
        "default_lane": settings.default_lane,
        "default_validation_command": settings.default_validation_command,
        "default_full_test_command": settings.default_full_test_command,
        "default_branch": settings.default_branch,
        "allow_auto_scope_template": settings.allow_auto_scope_template,
        "delivery_mode": settings.delivery_mode.value,
    }


def _git_summary(project_name: str, workspace_root: Path) -> dict[str, object]:
    try:
        status = get_git_repository_status(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return {"status": "unavailable", "detail": str(exc)}
    return {
        "status": "ok",
        "branch": status.current_branch,
        "head_commit": status.head_commit,
        "upstream_branch": status.upstream_branch,
        "remote_detected": status.remote_detected,
        "working_tree_clean": status.working_tree_clean,
        "ahead": status.ahead,
        "behind": status.behind,
        "warnings": status.warnings,
    }


def _validation_registry_summary(project_name: str, workspace_root: Path) -> dict[str, object]:
    path = registry_path(project_name, workspace_root=workspace_root)
    try:
        commands = list_validation_commands(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return {"status": "unavailable", "path": str(path), "detail": str(exc)}
    by_category: dict[str, int] = {}
    for command in commands:
        category = command.category.value
        by_category[category] = by_category.get(category, 0) + 1
    return {
        "status": "configured" if path.exists() else "missing",
        "path": str(path),
        "command_count": len(commands),
        "command_ids": [command.id for command in commands],
        "categories": by_category,
    }


def _backup_summary() -> dict[str, object]:
    root = os.getenv("DEVO_BACKUP_ROOT")
    if not root:
        return {"status": "SKIP", "detail": "No DEVO_BACKUP_ROOT configured."}
    try:
        inventory = list_backup_inventory(Path(root))
    except ValueError as exc:
        return {"status": "WARN", "backup_root": root, "detail": str(exc)}
    status = "WARN" if inventory.incomplete_backups or inventory.invalid_backup_folders else "OK"
    return {
        "status": status,
        "backup_root": str(inventory.backup_root),
        "normal_count": len(inventory.normal_backups),
        "protected_count": len(inventory.protected_backups),
        "incomplete_count": len(inventory.incomplete_backups),
        "invalid_count": len(inventory.invalid_backup_folders),
    }


def _planning_summary(project_name: str, workspace_root: Path) -> dict[str, object]:
    try:
        brief = load_project_brief(project_name, workspace_root=workspace_root)
        blueprint = load_project_blueprint(project_name, workspace_root=workspace_root)
        backlog = load_project_backlog(project_name, workspace_root=workspace_root)
        batches = list_project_batches(project_name, workspace_root=workspace_root)
        batch_approvals = list_batch_approvals(project_name, workspace_root=workspace_root)
        execution_policies = list_execution_policies(project_name, workspace_root=workspace_root)
        queues = list_execution_queues(project_name, workspace_root=workspace_root)
        queue_worker_runs = list_queue_worker_runs(project_name, workspace_root=workspace_root)
        handoffs = list_codex_handoffs(project_name, workspace_root=workspace_root)
        worker_runs = list_codex_worker_runs(project_name, workspace_root=workspace_root)
        worker_reports = list_codex_worker_reports(project_name, workspace_root=workspace_root)
        worker_reviews = list_codex_worker_reviews(project_name, workspace_root=workspace_root)
        run_plans = list_codex_run_plans(project_name, workspace_root=workspace_root)
        progress = calculate_project_progress(project_name, workspace_root=workspace_root)
    except Exception as exc:
        return {
            "brief_status": "unknown",
            "blueprint_status": "unknown",
            "blueprint_milestone_count": 0,
            "blueprint_epic_count": 0,
            "backlog_status": "unknown",
            "backlog_task_count": 0,
            "backlog_ready_count": 0,
            "backlog_blocked_count": 0,
            "backlog_completed_count": 0,
            "backlog_refinement_prompt_exists": False,
            "backlog_refinement_prompt_path": None,
            "batch_count": 0,
            "approved_batch_count": 0,
            "latest_batch_id": None,
            "latest_batch_status": None,
            "latest_batch_approval_status": None,
            "latest_batch_review_status": None,
            "batch_approval_requested_count": 0,
            "batch_approved_count": 0,
            "batch_rejected_count": 0,
            "batch_needs_changes_count": 0,
            "batch_approval_next_action": f"Review planning artifacts: {exc}",
            "execution_policy_count": 0,
            "approved_execution_policy_count": 0,
            "latest_execution_policy_id": None,
            "latest_execution_policy_status": None,
            "latest_execution_policy_batch_id": None,
            "latest_execution_policy_queue_id": None,
            "execution_policy_next_action": f"Review execution policy artifacts: {exc}",
            "queue_count": 0,
            "latest_queue_id": None,
            "latest_queue_status": None,
            "current_queue_item": None,
            "queue_pending_count": 0,
            "queue_completed_count": 0,
            "queue_blocked_count": 0,
            "queue_next_action": f"Review planning artifacts: {exc}",
            "linked_worker_run_id": None,
            "linked_worker_run_status": None,
            "linked_run_plan_id": None,
            "current_queue_item_worker_status": None,
            "current_queue_item_review_status": None,
            "current_queue_item_completion_ready": False,
            "current_queue_item_completion_blockers": [f"Review queue worker artifacts: {exc}"],
            "current_queue_item_validation_status": None,
            "queue_worker_next_action": f"Review queue worker artifacts: {exc}",
            "queue_worker_run_count": 0,
            "latest_queue_worker_run_id": None,
            "latest_queue_worker_run_status": None,
            "latest_queue_worker_run_policy_id": None,
            "latest_queue_worker_run_selected_item": None,
            "latest_queue_worker_run_selected_task": None,
            "latest_queue_worker_run_worker_run_id": None,
            "latest_queue_worker_run_delivery_request_id": None,
            "latest_queue_worker_run_delivery_request_status": None,
            "latest_queue_worker_run_next_action": f"Review queue worker artifacts: {exc}",
            "handoff_count": 0,
            "latest_handoff_id": None,
            "latest_handoff_type": None,
            "latest_handoff_status": None,
            "latest_handoff_path": None,
            "handoff_next_action": f"Review planning artifacts: {exc}",
            "worker_run_count": 0,
            "latest_worker_run_id": None,
            "latest_worker_run_status": None,
            "latest_worker_run_next_action": f"Review worker artifacts: {exc}",
            "latest_worker_execution_status": None,
            "latest_worker_execution_exit_code": None,
            "latest_worker_execution_log_path": None,
            "latest_worker_execution_next_action": f"Review worker execution artifacts: {exc}",
            "latest_worker_report_status": None,
            "latest_worker_report_path": None,
            "latest_worker_report_summary": None,
            "latest_worker_report_next_action": f"Review worker report artifacts: {exc}",
            "latest_worker_review_id": None,
            "latest_worker_review_status": None,
            "latest_worker_validation_status": None,
            "latest_worker_review_reviewer": None,
            "latest_worker_review_decision_note": None,
            "review_next_action": f"Review worker review artifacts: {exc}",
            "codex_run_plan_count": 0,
            "latest_codex_run_plan_id": None,
            "latest_codex_run_plan_status": None,
            "latest_codex_preflight_status": None,
            "latest_codex_run_plan_next_action": f"Review Codex run-plan artifacts: {exc}",
            "project_completion_percent": 0.0,
            "backlog_readiness_percent": 0.0,
            "blocked_percent": 0.0,
            "batch_completion_percent": 0.0,
            "progress_next_action": f"Review planning artifacts: {exc}",
            "planning_next_action": f"Review planning artifacts: {exc}",
        }
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    latest_batch = batches[0] if batches else None
    latest_batch_approval = next((approval for approval in batch_approvals if latest_batch and approval.batch_id == latest_batch.batch_id), None)
    latest_execution_policy = execution_policies[0] if execution_policies else None
    latest_queue = queues[0] if queues else None
    latest_queue_worker_run = queue_worker_runs[0] if queue_worker_runs else None
    latest_handoff = handoffs[0] if handoffs else None
    latest_worker_run = worker_runs[0] if worker_runs else None
    latest_worker_report = worker_reports[0] if worker_reports else None
    latest_worker_review = worker_reviews[0] if worker_reviews else None
    latest_run_plan = run_plans[0] if run_plans else None
    queue_worker_status = None
    if latest_queue:
        try:
            queue_worker_status = get_codex_queue_worker_status(project_name, latest_queue.queue_id, workspace_root=workspace_root)
        except Exception:
            queue_worker_status = None
    latest_worker_report_run = None
    if latest_worker_report:
        try:
            latest_worker_report_run = load_codex_worker_run(project_name, latest_worker_report.worker_run_id, workspace_root=workspace_root)
        except ValueError:
            latest_worker_report_run = None
    if not brief:
        next_action = f"Create a Project Brief: devo project brief-create --project {project_name} --title \"<title>\" --file <brief.md>"
    elif brief.status != "approved":
        next_action = f"Approve the Project Brief: devo project brief-approve --project {project_name}"
    elif not blueprint:
        next_action = f"Create a Blueprint: devo project blueprint-create --project {project_name}"
    elif blueprint.status != "approved":
        next_action = f"Approve the Blueprint: devo project blueprint-approve --project {project_name}"
    elif not backlog:
        next_action = f"Create a Backlog: devo project backlog-create --project {project_name}"
    elif backlog.status != "approved":
        next_action = f"Approve the Backlog: devo project backlog-approve --project {project_name}"
    elif not batches:
        next_action = f"Create or suggest a Batch: devo project batch-suggest --project {project_name} --limit 10"
    elif not any(batch.approval_status == "approved" for batch in batches):
        if latest_batch_approval and latest_batch_approval.approval_status == "requested":
            next_action = f"Review requested Batch approval: devo project batch-approval-show --project {project_name} --batch {latest_batch.batch_id if latest_batch else '<batchId>'}"
        else:
            next_action = f"Request Batch approval: devo project batch-approval-request --project {project_name} --batch {latest_batch.batch_id if latest_batch else '<batchId>'} --note \"<note>\""
    elif not queues:
        next_action = f"Create an Execution Queue: devo project queue-create --project {project_name} --batch {latest_batch.batch_id if latest_batch else '<batchId>'}"
    elif not any(policy.status == "approved" for policy in execution_policies):
        next_action = (
            f"Create a Batch Execution Policy: devo project execution-policy-create --project {project_name} "
            f"--batch {latest_batch.batch_id if latest_batch else '<batchId>'} --queue {latest_queue.queue_id if latest_queue else '<queueId>'} --title \"<title>\""
        )
    else:
        next_action = f"Continue the Execution Queue: devo project queue-next --project {project_name} --queue {latest_queue.queue_id if latest_queue else '<queueId>'}"
    queue_next_action = _queue_next_action(project_name, latest_queue)
    handoff_next_action = _handoff_next_action(project_name, latest_queue, latest_handoff)
    return {
        "brief_status": brief.status if brief else "missing",
        "blueprint_status": blueprint.status if blueprint else "missing",
        "blueprint_milestone_count": len(blueprint.milestones) if blueprint else 0,
        "blueprint_epic_count": len(blueprint.epics) if blueprint else 0,
        "backlog_status": backlog.status if backlog else "missing",
        "backlog_task_count": backlog.task_count if backlog else 0,
        "backlog_ready_count": backlog.ready_task_count if backlog else 0,
        "backlog_blocked_count": backlog.blocked_task_count if backlog else 0,
        "backlog_completed_count": backlog.completed_task_count if backlog else 0,
        "backlog_refinement_prompt_exists": paths.backlog_refinement_prompt.exists(),
        "backlog_refinement_prompt_path": str(paths.backlog_refinement_prompt),
        "batch_count": len(batches),
        "approved_batch_count": sum(1 for batch in batches if batch.approval_status == "approved"),
        "latest_batch_id": latest_batch.batch_id if latest_batch else None,
        "latest_batch_status": latest_batch.status if latest_batch else None,
        "latest_batch_approval_status": (latest_batch_approval.approval_status if latest_batch_approval else latest_batch.approval_status) if latest_batch else None,
        "latest_batch_review_status": (latest_batch_approval.review_status if latest_batch_approval else latest_batch.review_status) if latest_batch else None,
        "batch_approval_requested_count": sum(1 for approval in batch_approvals if approval.approval_status == "requested"),
        "batch_approved_count": sum(1 for approval in batch_approvals if approval.approval_status == "approved"),
        "batch_rejected_count": sum(1 for approval in batch_approvals if approval.approval_status == "rejected"),
        "batch_needs_changes_count": sum(1 for approval in batch_approvals if approval.review_status == "needs_changes"),
        "batch_approval_next_action": latest_batch_approval.next_action if latest_batch_approval else next_action,
        "execution_policy_count": len(execution_policies),
        "approved_execution_policy_count": sum(1 for policy in execution_policies if policy.status == "approved"),
        "latest_execution_policy_id": latest_execution_policy.policy_id if latest_execution_policy else None,
        "latest_execution_policy_status": latest_execution_policy.status if latest_execution_policy else None,
        "latest_execution_policy_batch_id": latest_execution_policy.batch_id if latest_execution_policy else None,
        "latest_execution_policy_queue_id": latest_execution_policy.queue_id if latest_execution_policy else None,
        "execution_policy_next_action": (
            latest_execution_policy.next_action
            if latest_execution_policy
            else (
                f"Create a Batch Execution Policy: devo project execution-policy-create --project {project_name} "
                f"--batch {latest_batch.batch_id if latest_batch else '<batchId>'} --title \"<title>\""
            )
        ),
        "queue_count": len(queues),
        "latest_queue_id": latest_queue.queue_id if latest_queue else None,
        "latest_queue_status": latest_queue.status if latest_queue else None,
        "current_queue_item": latest_queue.current_item_id if latest_queue else None,
        "queue_pending_count": latest_queue.pending_count if latest_queue else 0,
        "queue_completed_count": latest_queue.completed_count if latest_queue else 0,
        "queue_blocked_count": latest_queue.blocked_count if latest_queue else 0,
        "queue_next_action": queue_next_action,
        "linked_worker_run_id": queue_worker_status.linked_worker_run_id if queue_worker_status else None,
        "linked_worker_run_status": queue_worker_status.linked_worker_run_status if queue_worker_status else None,
        "linked_run_plan_id": queue_worker_status.linked_run_plan_id if queue_worker_status else None,
        "current_queue_item_worker_status": queue_worker_status.latest_worker_execution_status if queue_worker_status else None,
        "current_queue_item_review_status": queue_worker_status.current_queue_item_review_status if queue_worker_status else None,
        "current_queue_item_completion_ready": queue_worker_status.current_queue_item_completion_ready if queue_worker_status else False,
        "current_queue_item_completion_blockers": queue_worker_status.current_queue_item_completion_blockers if queue_worker_status else [],
        "current_queue_item_validation_status": queue_worker_status.current_queue_item_validation_status if queue_worker_status else None,
        "queue_worker_next_action": queue_worker_status.next_action if queue_worker_status else None,
        "queue_worker_run_count": len(queue_worker_runs),
        "latest_queue_worker_run_id": latest_queue_worker_run.run_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_status": latest_queue_worker_run.status if latest_queue_worker_run else None,
        "latest_queue_worker_run_policy_id": latest_queue_worker_run.policy_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_selected_item": latest_queue_worker_run.selected_queue_item_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_selected_task": latest_queue_worker_run.selected_task_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_worker_run_id": latest_queue_worker_run.selected_worker_run_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_delivery_request_id": latest_queue_worker_run.delivery_request_id if latest_queue_worker_run else None,
        "latest_queue_worker_run_delivery_request_status": latest_queue_worker_run.delivery_request_status if latest_queue_worker_run else None,
        "latest_queue_worker_run_next_action": latest_queue_worker_run.next_action if latest_queue_worker_run else None,
        "handoff_count": len(handoffs),
        "latest_handoff_id": latest_handoff.handoff_id if latest_handoff else None,
        "latest_handoff_type": latest_handoff.handoff_type if latest_handoff else None,
        "latest_handoff_status": latest_handoff.status if latest_handoff else None,
        "latest_handoff_path": latest_handoff.prompt_path if latest_handoff else None,
        "handoff_next_action": handoff_next_action,
        "worker_run_count": len(worker_runs),
        "latest_worker_run_id": latest_worker_run.worker_run_id if latest_worker_run else None,
        "latest_worker_run_status": latest_worker_run.status if latest_worker_run else None,
        "latest_worker_run_next_action": latest_worker_run.next_action if latest_worker_run else None,
        "latest_worker_execution_status": latest_worker_run.status if latest_worker_run and latest_worker_run.execution_exit_code is not None else None,
        "latest_worker_execution_exit_code": latest_worker_run.execution_exit_code if latest_worker_run else None,
        "latest_worker_execution_log_path": latest_worker_run.execution_log_path if latest_worker_run else None,
        "latest_worker_execution_next_action": latest_worker_run.next_action if latest_worker_run and latest_worker_run.execution_exit_code is not None else None,
        "latest_worker_report_status": latest_worker_report.status_reported_by_worker if latest_worker_report else None,
        "latest_worker_report_path": latest_worker_report_run.report_path if latest_worker_report_run else None,
        "latest_worker_report_summary": latest_worker_report.summary if latest_worker_report else None,
        "latest_worker_report_next_action": latest_worker_report_run.next_action if latest_worker_report_run else None,
        "latest_worker_review_id": latest_worker_review.review_id if latest_worker_review else None,
        "latest_worker_review_status": latest_worker_review.review_status if latest_worker_review else None,
        "latest_worker_validation_status": latest_worker_review.validation_evidence.validation_status if latest_worker_review else None,
        "latest_worker_review_reviewer": latest_worker_review.reviewer if latest_worker_review else None,
        "latest_worker_review_decision_note": latest_worker_review.decision_note if latest_worker_review else None,
        "review_next_action": latest_worker_review.next_action if latest_worker_review else None,
        "codex_run_plan_count": len(run_plans),
        "latest_codex_run_plan_id": latest_run_plan.plan_id if latest_run_plan else None,
        "latest_codex_run_plan_status": latest_run_plan.status if latest_run_plan else None,
        "latest_codex_preflight_status": latest_run_plan.preflight_status if latest_run_plan else None,
        "latest_codex_run_plan_next_action": latest_run_plan.next_action if latest_run_plan else None,
        "project_completion_percent": progress.project_completion_percent,
        "backlog_readiness_percent": progress.backlog_readiness_percent,
        "blocked_percent": progress.blocked_percent,
        "batch_completion_percent": progress.batch_completion_percent,
        "progress_next_action": progress.next_action,
        "planning_next_action": next_action,
    }


def _delivery_summary(project_name: str, workspace_root: Path) -> dict[str, object]:
    try:
        checks = list_delivery_checks(project_name, workspace_root=workspace_root)
        plans = list_delivery_plans(project_name, workspace_root=workspace_root)
        reports = list_delivery_reports(project_name, workspace_root=workspace_root)
    except Exception as exc:
        return {
            "delivery_check_count": 0,
            "latest_delivery_id": None,
            "latest_delivery_readiness_status": None,
            "latest_delivery_blocker_count": 0,
            "latest_delivery_warning_count": 0,
            "delivery_next_action": f"Review delivery artifacts: {exc}",
            "delivery_plan_count": 0,
            "latest_delivery_plan_id": None,
            "latest_delivery_plan_status": None,
            "latest_delivery_approval_status": None,
            "latest_delivery_plan_next_action": f"Review delivery artifacts: {exc}",
            "delivery_report_count": 0,
            "latest_delivery_report_id": None,
            "latest_delivery_report_status": None,
            "latest_delivery_commit_ready": False,
            "latest_delivery_push_ready": False,
            "latest_delivery_report_next_action": f"Review delivery artifacts: {exc}",
            "latest_delivery_commit_hash": None,
            "latest_delivery_commit_status": None,
            "latest_delivery_pushed": False,
            "latest_delivery_commit_next_action": f"Review delivery artifacts: {exc}",
            "latest_delivery_push_status": None,
            "latest_delivery_push_remote": None,
            "latest_delivery_push_branch": None,
            "latest_delivery_pushed_at": None,
            "latest_delivery_push_next_action": f"Review delivery artifacts: {exc}",
            "latest_delivery_summary_status": "unknown",
            "latest_delivery_summary_id": None,
            "latest_delivery_summary_kind": None,
            "latest_delivery_summary_next_action": f"Review delivery artifacts: {exc}",
            "current_repo_has_pending_changes": False,
            "current_repo_is_clean": False,
            "latest_meaningful_delivery_id": None,
            "latest_pushed_delivery_id": None,
            "latest_runner_request_id": None,
            "latest_runner_request_status": None,
            "latest_runner_run_id": None,
            "latest_runner_run_status": None,
            "latest_runner_commit_hash": None,
            "latest_runner_pushed": None,
            "latest_runner_next_action": f"Review delivery artifacts: {exc}",
        }
    latest = checks[0] if checks else None
    latest_plan = plans[0] if plans else None
    latest_report = reports[0] if reports else None
    runner_request = None
    runner_run = None
    try:
        runner_requests = list_delivery_runner_requests(project_name, workspace_root=workspace_root)
        runner_request = runner_requests[0] if runner_requests else None
        runner_run = load_delivery_runner_run(project_name, runner_request.request_id, workspace_root=workspace_root) if runner_request else None
    except Exception:
        runner_request = None
        runner_run = None
    try:
        latest_summary = build_delivery_latest_summary(project_name, workspace_root=workspace_root)
    except Exception:
        latest_summary = None
    return {
        "delivery_check_count": len(checks),
        "latest_delivery_id": latest.delivery_id if latest else None,
        "latest_delivery_readiness_status": latest.readiness_status if latest else None,
        "latest_delivery_blocker_count": len(latest.blockers) if latest else 0,
        "latest_delivery_warning_count": len(latest.warnings) if latest else 0,
        "delivery_next_action": latest.next_action if latest else "Run a delivery readiness check when a reviewed queue item is ready.",
        "delivery_plan_count": len(plans),
        "latest_delivery_plan_id": latest_plan.delivery_id if latest_plan else None,
        "latest_delivery_plan_status": latest_plan.delivery_status if latest_plan else None,
        "latest_delivery_approval_status": latest_plan.approval_status if latest_plan else None,
        "latest_delivery_plan_next_action": latest_plan.next_action if latest_plan else "Create a delivery plan from a written readiness check when ready.",
        "delivery_report_count": len(reports),
        "latest_delivery_report_id": latest_report.delivery_id if latest_report else None,
        "latest_delivery_report_status": latest_report.final_status if latest_report else None,
        "latest_delivery_commit_ready": latest_report.commit_ready if latest_report else False,
        "latest_delivery_push_ready": latest_report.push_ready if latest_report else False,
        "latest_delivery_report_next_action": latest_report.next_action if latest_report else "Prepare a delivery report after delivery approval.",
        "latest_delivery_commit_hash": latest_report.commit_hash if latest_report else None,
        "latest_delivery_commit_status": latest_report.final_status if latest_report and latest_report.commit_hash else None,
        "latest_delivery_pushed": latest_report.pushed if latest_report else False,
        "latest_delivery_commit_next_action": latest_report.next_action if latest_report and latest_report.commit_hash else None,
        "latest_delivery_push_status": latest_report.push_status if latest_report else None,
        "latest_delivery_push_remote": latest_report.push_remote if latest_report else None,
        "latest_delivery_push_branch": latest_report.push_branch if latest_report else None,
        "latest_delivery_pushed_at": latest_report.pushed_at.isoformat() if latest_report and latest_report.pushed_at else None,
        "latest_delivery_push_next_action": latest_report.next_action if latest_report and latest_report.push_status else None,
        "latest_delivery_summary_status": _delivery_overview_summary_status(latest_summary),
        "latest_delivery_summary_id": _delivery_overview_summary_id(latest_summary),
        "latest_delivery_summary_kind": _delivery_overview_summary_kind(latest_summary),
        "latest_delivery_summary_next_action": latest_summary.next_action if latest_summary else None,
        "current_repo_has_pending_changes": latest_summary.current_repo_has_pending_changes if latest_summary else False,
        "current_repo_is_clean": latest_summary.current_repo_is_clean if latest_summary else False,
        "latest_meaningful_delivery_id": latest_summary.latest_meaningful_delivery_check_id if latest_summary else None,
        "latest_pushed_delivery_id": latest_summary.latest_pushed_delivery_id if latest_summary else None,
        "latest_runner_request_id": runner_request.request_id if runner_request else None,
        "latest_runner_request_status": runner_request.status if runner_request else None,
        "latest_runner_run_id": runner_run.run_id if runner_run else None,
        "latest_runner_run_status": runner_run.status if runner_run else None,
        "latest_runner_commit_hash": runner_run.commit_hash if runner_run else None,
        "latest_runner_pushed": runner_run.pushed if runner_run else None,
        "latest_runner_next_action": latest_summary.latest_runner_next_action if latest_summary else None,
    }


def _delivery_overview_summary_status(summary: object | None) -> str:
    if not summary:
        return "unknown"
    if getattr(summary, "current_repo_is_clean", False) and "No delivery needed" in getattr(summary, "next_action", ""):
        return "clean"
    check_status = getattr(summary, "latest_delivery_check_status", None)
    if check_status == "blocked":
        return "blocked"
    if getattr(summary, "current_repo_has_pending_changes", False):
        return "pending_changes"
    if getattr(summary, "latest_pushed_delivery_id", None):
        return "pushed"
    return str(check_status or "unknown")


def _delivery_overview_summary_id(summary: object | None) -> str | None:
    if not summary:
        return None
    return getattr(summary, "latest_delivery_check_id", None) or getattr(summary, "latest_pushed_delivery_id", None)


def _delivery_overview_summary_kind(summary: object | None) -> str | None:
    if not summary:
        return None
    if getattr(summary, "latest_delivery_check_id", None):
        return "delivery_check"
    if getattr(summary, "latest_pushed_delivery_id", None):
        return "pushed_delivery"
    return None


def _queue_next_action(project_name: str, queue: object | None) -> str:
    if not queue:
        return f"Create an Execution Queue: devo project queue-create --project {project_name} --batch <batchId>"
    queue_id = getattr(queue, "queue_id", "<queueId>")
    status = getattr(queue, "status", "unknown")
    if status in {"draft", "ready", "paused_usage_limit", "paused_failure", "waiting_review"}:
        return f"Start or resume the Queue: devo project queue-start --project {project_name} --queue {queue_id}"
    if status == "running":
        return f"Inspect the current Queue item: devo project queue-next --project {project_name} --queue {queue_id}"
    if status == "completed":
        return "Queue completed; Codex handoff and review workflow improvements continue in later tasks."
    return f"Review Queue status: devo project queue-show --project {project_name} --queue {queue_id}"


def _handoff_next_action(project_name: str, queue: object | None, handoff: object | None) -> str:
    if queue:
        queue_id = getattr(queue, "queue_id", "<queueId>")
        status = getattr(queue, "status", "unknown")
        if status == "running":
            return f"Generate Codex handoff: devo project handoff-next --project {project_name} --queue {queue_id}"
        if status in {"draft", "ready", "paused_usage_limit", "paused_failure", "waiting_review"}:
            return f"Start or resume queue before handoff: devo project queue-start --project {project_name} --queue {queue_id}"
    if handoff:
        return f"Review latest handoff: devo project handoff-show --project {project_name} --handoff {getattr(handoff, 'handoff_id', '<handoffId>')}"
    return f"Generate manual task handoff: devo project handoff-task --project {project_name} --task <taskId>"


def _latest_validation(project_name: str, run_id: str, workspace_root: Path):
    try:
        records = [record for record in list_validation_history(project_name, workspace_root=workspace_root) if record.run_id == run_id]
    except ValueError:
        return None
    if not records:
        return None
    return sorted(records, key=lambda item: item.started_at, reverse=True)[0]


def _validation_status(record: object | None, fallback: str | None = None) -> str:
    if record:
        exit_code = getattr(record, "exit_code", None)
        suffix = f", exit={exit_code}" if exit_code is not None else ""
        return f"{getattr(record, 'status').value}{suffix}"
    return fallback or "none"


def _visual_reports_for_run(project_name: str, run_id: str, workspace_root: Path) -> list[str]:
    visual_dir = workspace_root / "runs" / project_name / run_id / "artifacts" / "visuals"
    if not visual_dir.exists():
        return []
    return [str(path) for path in sorted(visual_dir.glob("*.md"))]


def _scope_status(package: WorkPackage) -> str:
    if package.approved_files or package.proposed_items or package.allowed_changes:
        return "imported"
    if package.status.value != "draft":
        return "partially available"
    return "draft"


def _delivery_status(package: WorkPackage) -> str:
    if package.commit_hash:
        return f"delivered: {package.commit_hash}"
    if package.delivery_summary:
        return "delivery summary recorded"
    return "not delivered"


def _suggest_project_next_action(onboarding_status: str) -> str:
    if onboarding_status == "READY":
        return "Start or resume a scoped work package."
    if onboarding_status in {"NOT_STARTED", "IN_PROGRESS"}:
        return "Run project onboarding and complete the next setup step."
    return "Review project health before starting work."


def _safe_limit(limit: int) -> int:
    return max(1, min(limit, 100))


def _timed(name: str, timing: dict[str, float], action):
    started = perf_counter()
    result = action()
    timing[name] = _elapsed_ms(started)
    return result


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 1)
