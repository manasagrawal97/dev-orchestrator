from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from .backups import list_backup_inventory
from .doctor import run_doctor_with_timing
from .git_delivery import get_git_repository_status
from .project_onboarding import build_project_onboarding_report
from .project_planning import (
    calculate_project_progress,
    list_project_batches,
    list_execution_queues,
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
    queue_count: int = 0
    latest_queue_id: str | None = None
    latest_queue_status: str | None = None
    current_queue_item: str | None = None
    queue_pending_count: int = 0
    queue_completed_count: int = 0
    queue_blocked_count: int = 0
    queue_next_action: str = "Create a Project Brief."
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
            queue_count=int(planning["queue_count"]),
            latest_queue_id=str(planning["latest_queue_id"]) if planning["latest_queue_id"] else None,
            latest_queue_status=str(planning["latest_queue_status"]) if planning["latest_queue_status"] else None,
            current_queue_item=str(planning["current_queue_item"]) if planning["current_queue_item"] else None,
            queue_pending_count=int(planning["queue_pending_count"]),
            queue_completed_count=int(planning["queue_completed_count"]),
            queue_blocked_count=int(planning["queue_blocked_count"]),
            queue_next_action=str(planning["queue_next_action"]),
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
        queues = list_execution_queues(project_name, workspace_root=workspace_root)
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
            "queue_count": 0,
            "latest_queue_id": None,
            "latest_queue_status": None,
            "current_queue_item": None,
            "queue_pending_count": 0,
            "queue_completed_count": 0,
            "queue_blocked_count": 0,
            "queue_next_action": f"Review planning artifacts: {exc}",
            "project_completion_percent": 0.0,
            "backlog_readiness_percent": 0.0,
            "blocked_percent": 0.0,
            "batch_completion_percent": 0.0,
            "progress_next_action": f"Review planning artifacts: {exc}",
            "planning_next_action": f"Review planning artifacts: {exc}",
        }
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    latest_batch = batches[0] if batches else None
    latest_queue = queues[0] if queues else None
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
        next_action = f"Create or suggest a Batch: devo project batch-suggest --project {project_name}"
    elif not any(batch.approval_status == "approved" for batch in batches):
        next_action = f"Review and approve a Batch: devo project batch-show --project {project_name} --batch {latest_batch.batch_id if latest_batch else '<batchId>'}"
    elif not queues:
        next_action = f"Create an Execution Queue: devo project queue-create --project {project_name} --batch {latest_batch.batch_id if latest_batch else '<batchId>'}"
    else:
        next_action = f"Continue the Execution Queue: devo project queue-next --project {project_name} --queue {latest_queue.queue_id if latest_queue else '<queueId>'}"
    queue_next_action = _queue_next_action(project_name, latest_queue)
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
        "queue_count": len(queues),
        "latest_queue_id": latest_queue.queue_id if latest_queue else None,
        "latest_queue_status": latest_queue.status if latest_queue else None,
        "current_queue_item": latest_queue.current_item_id if latest_queue else None,
        "queue_pending_count": latest_queue.pending_count if latest_queue else 0,
        "queue_completed_count": latest_queue.completed_count if latest_queue else 0,
        "queue_blocked_count": latest_queue.blocked_count if latest_queue else 0,
        "queue_next_action": queue_next_action,
        "project_completion_percent": progress.project_completion_percent,
        "backlog_readiness_percent": progress.backlog_readiness_percent,
        "blocked_percent": progress.blocked_percent,
        "batch_completion_percent": progress.batch_completion_percent,
        "progress_next_action": progress.next_action,
        "planning_next_action": next_action,
    }


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
