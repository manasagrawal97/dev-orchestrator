from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from .approvals import (
    DevoApprovalRecord,
    approval_bundle_artifact_paths,
    approval_artifact_paths,
    approve_approval_bundle,
    approve_approval,
    create_approval_bundle,
    create_approval_request,
    get_approval_bundle,
    get_approval_status,
    reject_approval,
)
from .backups import cleanup_backups, create_backup, list_backup_inventory, restore_backup, verify_backup
from .environment import (
    create_environment_snapshot,
    generate_environment_bootstrap_plan,
    verify_environment_snapshot,
)
from .git_delivery import (
    create_delivery_report,
    get_git_repository_status,
    run_delivery_check,
)
from .agents import (
    DISCOVERY_AGENT_NAME,
    REVIEWER_AGENT_NAME,
    generate_run_agent_prompt,
    generate_project_context_discovery_prompt,
    generate_project_context_reviewer_prompt,
    list_agent_definitions,
    load_agent_definition,
    render_agent_definition,
)
from .context import approve_context, get_context_status, import_agent_output
from .context_updates import (
    apply_context_update,
    get_project_context_summary,
    list_context_updates,
    refresh_project_context,
    render_context_update_markdown,
)
from .doctor import DoctorReport, run_doctor
from .reports import (
    build_handoff_report,
    build_project_report,
    build_run_report,
    render_report_markdown,
    write_report_artifacts,
)
from .projects import get_workspace_root, list_projects, register_project
from .project_onboarding import ProjectOnboardingReport, build_project_onboarding_report
from .project_planning import (
    BacklogTask,
    BacklogValidationResult,
    BatchApproval,
    BatchSuggestionResult,
    CodexHandoff,
    ExecutionQueue,
    QueueItem,
    ProjectProgress,
    ProjectBacklog,
    ProjectBatch,
    ProjectBlueprint,
    ProjectBrief,
    CodexExecutionPreview,
    CodexExecutionResult,
    CodexQueueWorkerStatus,
    CodexPreflightResult,
    CodexRunPlan,
    CodexWorkerReport,
    QueueItemCompletionReadiness,
    WorkerReview,
    WorkerReportValidationResult,
    WorkerRun,
    approve_codex_run_plan,
    approve_project_batch,
    approve_project_backlog,
    approve_project_blueprint,
    approve_project_brief,
    block_queue_item,
    calculate_project_progress,
    create_project_batch,
    create_project_backlog,
    create_project_blueprint,
    create_project_brief,
    create_codex_handoff_for_batch,
    create_codex_handoff_for_queue_next,
    create_codex_handoff_for_task,
    create_codex_worker_run_from_handoff,
    create_codex_worker_run_plan,
    create_codex_worker_report_template,
    create_codex_worker_review_template,
    create_execution_queue_from_batch,
    create_suggested_project_batch,
    execute_codex_worker_run,
    complete_queue_item,
    generate_backlog_refinement_prompt,
    get_backlog_task,
    get_codex_queue_worker_status,
    get_queue_item_completion_readiness,
    get_queue_next_item,
    import_refined_backlog,
    attach_codex_worker_review_evidence,
    list_execution_queues,
    list_batch_approvals,
    list_codex_handoffs,
    list_codex_run_plans,
    list_codex_worker_reports,
    list_codex_worker_reviews,
    list_codex_worker_runs,
    list_project_batches,
    load_execution_queue,
    load_batch_approval,
    load_codex_handoff,
    load_codex_run_plan,
    load_codex_worker_report,
    load_codex_worker_review,
    load_codex_worker_run,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
    pause_execution_queue,
    mark_codex_handoff_used,
    mark_codex_worker_run_handoff_used,
    prepare_codex_worker_for_queue_next,
    preview_codex_worker_execution,
    reject_project_batch,
    request_batch_approval,
    review_project_batch,
    record_codex_worker_review,
    resume_execution_queue,
    suggest_project_batch,
    start_execution_queue,
    run_codex_worker_preflight,
    update_codex_worker_run_status,
    validate_refined_backlog_file,
    validate_codex_worker_report_file,
    import_codex_worker_report,
    worker_report_artifact_paths,
    worker_review_artifact_paths,
    worker_execution_log_paths,
    worker_run_plan_artifact_paths,
    worker_run_artifact_paths,
)
from .project_settings import ProjectSettings, load_project_settings, project_settings_path, update_project_settings
from .read_models import (
    ProjectOverview,
    build_project_overview,
    build_work_package_overview,
)
from .policy import (
    PolicyCheckResult,
    PolicyClassification,
    PolicyStatus,
    check_policy,
    classify_task,
    get_policy_status,
)
from .runs import (
    CODE_REVIEWER_AGENT_NAME,
    close_run,
    FINAL_AUDITOR_AGENT_NAME,
    IDEA_ANALYST_AGENT_NAME,
    IMPLEMENTATION_COORDINATOR_AGENT_NAME,
    PLANNER_AGENT_NAME,
    PLAN_REVIEWER_AGENT_NAME,
    REQUIREMENTS_AGENT_NAME,
    TASK_DECOMPOSER_AGENT_NAME,
    VALIDATOR_AGENT_NAME,
    close_task,
    create_run,
    get_audit_status,
    get_implementation_status,
    get_review_status,
    get_run_artifacts_summary,
    get_run_summary,
    get_task_status,
    get_validation_status,
    import_implementation_completion_report,
    import_run_agent_output,
    load_current_selection,
    list_run_tasks,
    mark_task_disposition,
    list_runs,
    load_run,
    run_path,
    save_current_selection,
)
from .scanner import load_registered_project, scan_registered_project
from .task_selector import DEFAULT_STRATEGY, TaskSelection, list_task_candidates, select_next_task
from .ui_helpers import check_ui_status, open_ui_if_reachable, ui_urls
from .validation_registry import (
    add_validation_command,
    check_validation_command,
    get_validation_command,
    list_validation_commands,
    registry_path,
    suggest_validation_commands,
)
from .validation_runner import list_validation_history, run_validation_command, terminal_excerpt
from .work_packages import (
    build_work_package_resume,
    complete_work_package,
    generate_work_package_phase_prompt,
    generate_work_scope_template,
    get_lane,
    get_work_package_next_step,
    import_work_scope,
    list_lanes,
    load_work_package,
    render_work_scope_example,
    start_work_package,
    work_package_artifact_paths,
    work_package_next_action,
)
from .work_history import ProjectActivitySummary, WorkPackageSummary, build_project_activity_summary, list_work_package_summaries
from .visual_reports import generate_project_activity_visual, generate_work_package_visual
from .workflow import WorkflowAction, advance_workflow, get_next_workflow_action, get_workflow_status, run_workflow_batch

app = typer.Typer(help="DevOrchestrator local development CLI.")
project_app = typer.Typer(help="Manage registered projects.")
agent_app = typer.Typer(help="Inspect agent definitions and generate prompts.")
run_app = typer.Typer(help="Manage development runs.")
implementation_app = typer.Typer(help="Record implementation completion evidence.")
validation_app = typer.Typer(help="Manage validation command metadata and review evidence.")
review_app = typer.Typer(help="Inspect code review evidence.")
audit_app = typer.Typer(help="Inspect final audit evidence.")
task_app = typer.Typer(help='Manage run tasks.')
policy_app = typer.Typer(help='Classify task risk and check policy gates.')
approval_app = typer.Typer(help='Record and inspect Devo approval requests.')
work_app = typer.Typer(help="Create and inspect scoped work packages.")
backup_app = typer.Typer(help="Backup, verify, list, and restore workspace state.")
env_app = typer.Typer(help="Capture and verify environment snapshots.")
workflow_app = typer.Typer(help="Inspect run workflow status and next actions.")
git_app = typer.Typer(help="Inspect Git delivery readiness without mutating repositories.")
report_app = typer.Typer(help="Generate deterministic project, run, and handoff reports.")
visual_app = typer.Typer(help="Generate Mermaid visual report artifacts.")
api_app = typer.Typer(help="Serve the local read-only Devo API.")
ui_app = typer.Typer(help="Inspect and open the local read-only Devo UI.")
worker_app = typer.Typer(help="Track local worker runs.")
worker_codex_app = typer.Typer(help="Track Codex worker runs without invoking Codex.")
app.add_typer(project_app, name="project")
app.add_typer(agent_app, name="agent")
app.add_typer(run_app, name="run")
app.add_typer(implementation_app, name="implementation")
app.add_typer(validation_app, name="validation")
app.add_typer(review_app, name="review")
app.add_typer(audit_app, name="audit")
app.add_typer(task_app, name='task')
app.add_typer(policy_app, name='policy')
app.add_typer(approval_app, name='approval')
app.add_typer(work_app, name="work")
app.add_typer(backup_app, name="backup")
app.add_typer(env_app, name="env")
app.add_typer(workflow_app, name="workflow")
app.add_typer(git_app, name="git")
app.add_typer(report_app, name="report")
app.add_typer(visual_app, name="visual")
app.add_typer(api_app, name="api")
app.add_typer(ui_app, name="ui")
app.add_typer(worker_app, name="worker")
worker_app.add_typer(worker_codex_app, name="codex")
console = Console()


def _print_doctor_report(report: DoctorReport) -> None:
    title = "Devo doctor"
    if report.project:
        title = f"{title}: {report.project}"
    console.print(f"[bold]{title}[/bold]")
    for check in report.checks:
        console.print(f"{check.status.value:<4} {check.name}: {check.detail}", soft_wrap=True)
    console.print(f"Overall status: {report.overall_status.value}")
    console.print(f"Suggested next action: {report.suggested_next_action}", soft_wrap=True)


def _print_project_settings(settings: ProjectSettings, path: Path) -> None:
    console.print(f"[bold]Project settings: {settings.project_name}[/bold]")
    console.print(f"  Path: {_named_path(path)}")
    console.print(f"  Default lane: {settings.default_lane or 'none'}")
    console.print(f"  Default validation command: {settings.default_validation_command or 'none'}")
    console.print(f"  Default full test command: {settings.default_full_test_command or 'none'}")
    console.print(f"  Default branch: {settings.default_branch or 'none'}")
    console.print(f"  Auto scope template: {settings.allow_auto_scope_template}")
    console.print(f"  Delivery mode: {settings.delivery_mode.value}")
    console.print(f"  Notes: {settings.notes or 'none'}", soft_wrap=True)
    console.print(f"  Updated at: {settings.updated_at.isoformat()}")


def _print_project_onboarding(report: ProjectOnboardingReport) -> None:
    console.print(f"[bold]Project onboarding: {report.project_name}[/bold]")
    console.print(f"Onboarding overall status: {report.overall_status.value}")
    console.print("Checklist:")
    for check in report.checks:
        console.print(f"  {check.status.value:<4} {check.name}: {check.detail}", soft_wrap=True)
    if report.suggested_settings:
        console.print("Suggested settings:")
        console.print(f"  {report.suggested_settings.command}", soft_wrap=True)
        for note in report.suggested_settings.notes:
            console.print(f"  Note: {note}", soft_wrap=True)
    console.print(f"Suggested next command: {report.suggested_next_command}", soft_wrap=True)
    if report.report_path:
        console.print(f"Report: {_named_path(report.report_path)}")


def _print_project_overview(overview: ProjectOverview) -> None:
    console.print(f"[bold]Project overview: {overview.project_name}[/bold]")
    console.print(f"Project path: {overview.project_path or 'unknown'}", soft_wrap=True)
    console.print(f"Current project: {overview.is_current_project}")
    console.print(f"Current run: {overview.current_run_id or 'none'}")
    console.print(f"Onboarding: {overview.onboarding_status}")
    console.print(f"Doctor: {overview.doctor_overall_status}")
    console.print(f"Default lane: {overview.settings_summary.get('default_lane') or 'none'}")
    console.print(f"Git: {overview.git_summary.get('status', 'unknown')} branch={overview.git_summary.get('branch', 'unknown')}")
    console.print(f"Validation commands: {overview.validation_registry_summary.get('command_count', 0)}")
    console.print(f"Brief: {overview.brief_status}")
    console.print(f"Blueprint: {overview.blueprint_status} milestones={overview.blueprint_milestone_count} epics={overview.blueprint_epic_count}")
    console.print(f"Batches: {overview.batch_count} approved={overview.approved_batch_count} latest={overview.latest_batch_id or 'none'}")
    console.print(f"Queues: {overview.queue_count} latest={overview.latest_queue_id or 'none'} status={overview.latest_queue_status or 'none'}")
    console.print(
        f"Handoffs: {overview.handoff_count} latest={overview.latest_handoff_id or 'none'} "
        f"type={overview.latest_handoff_type or 'none'} status={overview.latest_handoff_status or 'none'}",
        soft_wrap=True,
    )
    console.print(f"Project completion: {overview.project_completion_percent:.1f}%")
    console.print(f"Backlog readiness: {overview.backlog_readiness_percent:.1f}%")
    console.print(f"Planning next action: {overview.planning_next_action}", soft_wrap=True)
    console.print(f"Handoff next action: {overview.handoff_next_action}", soft_wrap=True)
    console.print(f"Recent runs: {len(overview.recent_runs)}")
    console.print(f"Recent work packages: {len(overview.recent_work_packages)}")
    console.print(f"Suggested next action: {overview.suggested_next_action}", soft_wrap=True)


def _print_project_brief(brief: ProjectBrief | None, project_name: str) -> None:
    paths = planning_artifact_paths(project_name)
    if not brief:
        console.print(f"[yellow]Project brief not found for {project_name}.[/yellow]")
        console.print(f"Suggested next command: devo project brief-create --project {project_name} --title \"<title>\" --file <brief.md>")
        return
    console.print(f"[bold]Project brief: {project_name}[/bold]")
    console.print(f"Title: {brief.title}")
    console.print(f"Status: {brief.status}")
    console.print(f"Summary: {brief.summary}", soft_wrap=True)
    console.print(f"JSON: {_named_path(paths.brief_json)}")
    console.print(f"Markdown: {_named_path(paths.brief_markdown)}")


def _print_project_blueprint(blueprint: ProjectBlueprint | None, project_name: str) -> None:
    paths = planning_artifact_paths(project_name)
    if not blueprint:
        console.print(f"[yellow]Project blueprint not found for {project_name}.[/yellow]")
        console.print(f"Suggested next command: devo project blueprint-create --project {project_name}")
        return
    console.print(f"[bold]Project blueprint: {project_name}[/bold]")
    console.print(f"Title: {blueprint.title}")
    console.print(f"Status: {blueprint.status}")
    console.print(f"Milestones: {len(blueprint.milestones)}")
    console.print(f"Epics: {len(blueprint.epics)}")
    console.print(f"JSON: {_named_path(paths.blueprint_json)}")
    console.print(f"Markdown: {_named_path(paths.blueprint_markdown)}")


def _print_project_backlog(backlog: ProjectBacklog | None, project_name: str) -> None:
    paths = planning_artifact_paths(project_name)
    if not backlog:
        console.print(f"[yellow]Project backlog not found for {project_name}.[/yellow]")
        console.print(f"Suggested next command: devo project backlog-create --project {project_name}")
        return
    console.print(f"[bold]Project backlog: {project_name}[/bold]")
    console.print(f"Title: {backlog.title}")
    console.print(f"Status: {backlog.status}")
    console.print(f"Tasks: {backlog.task_count}")
    console.print(f"Ready: {backlog.ready_task_count}")
    console.print(f"Blocked: {backlog.blocked_task_count}")
    console.print(f"Completed: {backlog.completed_task_count}")
    console.print(f"JSON: {_named_path(paths.backlog_json)}")
    console.print(f"Markdown: {_named_path(paths.backlog_markdown)}")
    console.print("Starter backlog guidance:")
    console.print("  - This deterministic starter backlog is not implementation-ready by default.", soft_wrap=True)
    console.print(f"  - Refine it with: devo project backlog-prompt --project {project_name}", soft_wrap=True)
    console.print(f"  - Import refined JSON with: devo project backlog-import --project {project_name} --file <refined-backlog.json>", soft_wrap=True)
    console.print("  - Review and approve the refined backlog before batch creation.", soft_wrap=True)


def _print_backlog_task(task: BacklogTask) -> None:
    console.print(f"[bold]Backlog task: {task.id}[/bold]")
    console.print(f"Title: {task.title}")
    console.print(f"Status: {task.status}")
    console.print(f"Lane: {task.lane}")
    console.print(f"Risk: {task.risk_level}")
    console.print(f"Milestone: {task.milestone_id or 'none'}")
    console.print(f"Epic: {task.epic_id or 'none'}")
    console.print(f"Summary: {task.summary}", soft_wrap=True)
    console.print("Dependencies:")
    for dependency in task.dependencies or ["none"]:
        console.print(f"  - {dependency}")
    console.print("Acceptance criteria:")
    for item in task.acceptance_criteria or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Validation expectations:")
    for item in task.validation_expectations or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Allowed scope:")
    for item in task.allowed_scope or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Forbidden scope:")
    for item in task.forbidden_scope or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Notes:")
    for item in task.notes or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)


def _print_backlog_validation_result(result: BacklogValidationResult) -> None:
    console.print(f"Valid: {result.valid}")
    console.print(f"Tasks: {result.task_count}")
    console.print("Errors:")
    for item in result.errors or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Warnings:")
    for item in result.warnings or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)


def _print_project_batch(batch: ProjectBatch, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Project batch: {batch.batch_id}[/bold]")
    console.print(f"Title: {batch.title}")
    console.print(f"Status: {batch.status}")
    console.print(f"Approval status: {batch.approval_status}")
    console.print(f"Tasks: {batch.task_count}")
    console.print(f"Completed: {batch.completed_task_count}")
    console.print(f"Blocked: {batch.blocked_task_count}")
    console.print(f"Summary: {batch.summary}", soft_wrap=True)
    if batch.dependency_warnings:
        console.print("Dependency warnings:")
        for warning in batch.dependency_warnings:
            console.print(f"  - {warning}", soft_wrap=True)
    console.print("Included tasks:")
    for task in batch.task_snapshots:
        console.print(f"  - {task.task_id} | {task.status} | lane={task.lane} | risk={task.risk_level} | {task.title}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")


def _print_batch_approval(approval: BatchApproval, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Batch approval: {approval.batch_id}[/bold]")
    console.print(f"Approval status: {approval.approval_status}")
    console.print(f"Review status: {approval.review_status}")
    console.print(f"Tasks: {approval.task_count}")
    console.print(f"High-risk tasks: {approval.high_risk_task_count}")
    console.print(f"Blocked dependencies: {approval.blocked_dependency_count}")
    console.print(f"Reviewer: {approval.reviewer or 'none'}")
    console.print(f"Approver: {approval.approver or 'none'}")
    console.print(f"Decision note: {approval.decision_note or 'none'}", soft_wrap=True)
    console.print(f"Next action: {approval.next_action}", soft_wrap=True)
    if approval.dependency_warnings:
        console.print("Dependency warnings:")
        for warning in approval.dependency_warnings:
            console.print(f"  - {warning}", soft_wrap=True)
    if approval.scope_summary:
        console.print("Scope summary:")
        for item in approval.scope_summary:
            console.print(f"  - {item}", soft_wrap=True)
    if approval.validation_summary:
        console.print("Validation summary:")
        for item in approval.validation_summary:
            console.print(f"  - {item}", soft_wrap=True)
    if approval.review_notes:
        console.print("Review notes:")
        for note in approval.review_notes:
            console.print(f"  - {note}", soft_wrap=True)
    if json_path:
        console.print(f"Approval JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Approval Markdown: {_named_path(markdown_path)}")


def _print_batch_suggestion(result: BatchSuggestionResult) -> None:
    console.print(f"[bold]Batch suggestion: {result.project}[/bold]")
    if not result.suggested_tasks:
        console.print("[yellow]No suggested tasks.[/yellow]")
    for task in result.suggested_tasks:
        console.print(f"{task.task_id} | {task.status} | lane={task.lane} | risk={task.risk_level} | {task.title}", soft_wrap=True)
        console.print(f"  Reason: {task.reason}", soft_wrap=True)
    if result.skipped_tasks:
        console.print("Skipped:")
        for item in result.skipped_tasks:
            console.print(f"  - {item}", soft_wrap=True)
    if result.warnings:
        console.print("Warnings:")
        for item in result.warnings:
            console.print(f"  - {item}", soft_wrap=True)


def _print_project_progress(progress: ProjectProgress) -> None:
    console.print(f"[bold]Project progress: {progress.project}[/bold]")
    console.print(f"Brief: {progress.brief_status}")
    console.print(f"Blueprint: {progress.blueprint_status}")
    console.print(f"Backlog: {progress.backlog_status}")
    console.print(
        f"Tasks: total={progress.task_count} active={progress.active_task_count} "
        f"completed={progress.completed_task_count} ready={progress.ready_task_count} "
        f"approved={progress.approved_task_count} draft={progress.draft_task_count} blocked={progress.blocked_task_count}",
        soft_wrap=True,
    )
    console.print(f"Project completion: {progress.project_completion_percent:.1f}%")
    console.print(f"Backlog readiness: {progress.backlog_readiness_percent:.1f}%")
    console.print(f"Blocked: {progress.blocked_percent:.1f}%")
    console.print(
        f"Batches: total={progress.batch_count} active={progress.active_batch_count} "
        f"approved={progress.approved_batch_count} completed={progress.completed_batch_count}",
        soft_wrap=True,
    )
    console.print(f"Batch completion: {progress.batch_completion_percent:.1f}%")
    console.print(f"Latest batch: {progress.latest_batch_id or 'none'} status={progress.latest_batch_status or 'none'}")
    console.print(f"Next action: {progress.next_action}", soft_wrap=True)
    if progress.warnings:
        console.print("Warnings:")
        for warning in progress.warnings:
            console.print(f"  - {warning}", soft_wrap=True)
    console.print("Milestones:")
    for item in progress.milestone_progress or []:
        console.print(
            f"  - {item.id} | tasks={item.task_count} completed={item.completed_task_count} "
            f"blocked={item.blocked_task_count} completion={item.completion_percent:.1f}% {item.title or ''}",
            soft_wrap=True,
        )
    console.print("Epics:")
    for item in progress.epic_progress or []:
        console.print(
            f"  - {item.id} | tasks={item.task_count} completed={item.completed_task_count} "
            f"blocked={item.blocked_task_count} completion={item.completion_percent:.1f}% {item.title or ''}",
            soft_wrap=True,
        )


def _print_execution_queue(queue: ExecutionQueue, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Execution queue: {queue.queue_id}[/bold]")
    console.print(f"Title: {queue.title}")
    console.print(f"Source batch: {queue.source_batch_id}")
    console.print(f"Status: {queue.status}")
    console.print(f"Current item: {queue.current_item_id or 'none'}")
    console.print(
        f"Items: total={queue.item_count} pending={queue.pending_count} running={queue.running_count} "
        f"completed={queue.completed_count} blocked={queue.blocked_count} failed={queue.failed_count}",
        soft_wrap=True,
    )
    console.print(f"Pause reason: {queue.pause_reason or 'none'}")
    console.print(f"Resume hint: {queue.resume_hint or 'none'}", soft_wrap=True)
    console.print("Queue items:")
    for item in queue.items:
        console.print(f"  - {item.item_id} | task={item.task_id} | {item.status} | lane={item.lane} | risk={item.risk_level} | {item.title}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")


def _print_queue_item(item: QueueItem | None, project_name: str | None = None, queue_id: str | None = None) -> None:
    if not item:
        console.print("[yellow]No current or pending queue item.[/yellow]")
        return
    console.print(f"[bold]Queue item: {item.item_id}[/bold]")
    console.print(f"Task: {item.task_id}")
    console.print(f"Status: {item.status}")
    console.print(f"Lane: {item.lane}")
    console.print(f"Risk: {item.risk_level}")
    console.print(f"Title: {item.title}", soft_wrap=True)
    console.print("Dependencies:")
    for dependency in item.dependencies or ["none"]:
        console.print(f"  - {dependency}")
    console.print("Acceptance criteria:")
    for criterion in item.acceptance_criteria or ["none"]:
        console.print(f"  - {criterion}", soft_wrap=True)
    console.print("Validation expectations:")
    for expectation in item.validation_expectations or ["none"]:
        console.print(f"  - {expectation}", soft_wrap=True)
    if project_name and queue_id:
        typer.echo(f"Suggested handoff command: devo project handoff-next --project {project_name} --queue {queue_id}")
        typer.echo(f"Optional task handoff command: devo project handoff-task --project {project_name} --task {item.task_id}")
    else:
        console.print("Suggested handoff command: devo project handoff-next --project <project> --queue <queueId>")


def _print_queue_item_completion_readiness(readiness: QueueItemCompletionReadiness | None) -> None:
    if not readiness:
        return
    console.print(f"Completion ready: {'yes' if readiness.completion_ready else 'no'}")
    console.print(f"Linked worker run: {readiness.linked_worker_run_id or 'none'}")
    console.print(f"Worker review status: {readiness.review_status or 'none'}")
    console.print(f"Validation evidence status: {readiness.validation_status or 'none'}")
    if readiness.blockers:
        console.print("Completion blockers:")
        for blocker in readiness.blockers:
            console.print(f"  - {blocker}", soft_wrap=True)
    console.print(f"Completion next action: {readiness.next_action}", soft_wrap=True)


def _print_codex_handoff(handoff: CodexHandoff, json_path: Path | None = None, prompt_path: Path | None = None) -> None:
    console.print(f"[bold]Codex handoff: {handoff.handoff_id}[/bold]")
    console.print(f"Type: {handoff.handoff_type}")
    console.print(f"Title: {handoff.title}", soft_wrap=True)
    console.print(f"Status: {handoff.status}")
    console.print(f"Source queue: {handoff.source_queue_id or 'none'}")
    console.print(f"Source batch: {handoff.source_batch_id or 'none'}")
    console.print(f"Source item: {handoff.source_item_id or 'none'}")
    console.print(f"Source task: {handoff.source_task_id or 'none'}")
    console.print(f"Prompt: {_named_path(prompt_path or Path(handoff.prompt_path))}")
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    console.print("Suggested user action: paste this prompt into Codex.")
    console.print("Devo does not run Codex or target project commands automatically.")


def _print_worker_run(worker_run: WorkerRun, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Codex worker run: {worker_run.worker_run_id}[/bold]")
    console.print(f"Project: {worker_run.project}")
    console.print(f"Worker type: {worker_run.worker_type}")
    console.print(f"Mode: {worker_run.mode}")
    console.print(f"Status: {worker_run.status}")
    console.print(f"Title: {worker_run.title}", soft_wrap=True)
    console.print(f"Source handoff: {worker_run.source_handoff_id or 'none'}")
    console.print(f"Source queue: {worker_run.source_queue_id or 'none'}")
    console.print(f"Source item: {worker_run.source_queue_item_id or 'none'}")
    console.print(f"Source batch: {worker_run.source_batch_id or 'none'}")
    console.print(f"Source task: {worker_run.source_task_id or 'none'}")
    console.print(f"Prompt: {_named_path(Path(worker_run.prompt_path))}")
    console.print(f"Target repo: {worker_run.target_repo_path}", soft_wrap=True)
    console.print(f"Report status: {worker_run.report.report_status}")
    console.print(f"Reported commit: {worker_run.report.reported_commit_hash or 'none'}")
    console.print(f"Status note: {worker_run.status_note or 'none'}", soft_wrap=True)
    console.print(f"Next action: {worker_run.next_action}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")
    console.print("Safety: this is workspace-only tracking. Devo did not run Codex, execute target commands, or mark implementation complete.")


def _print_worker_report_validation(result: WorkerReportValidationResult) -> None:
    console.print(f"Valid: {result.valid}")
    console.print("Errors:")
    for item in result.errors or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Warnings:")
    for item in result.warnings or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    if result.report:
        console.print(f"Worker reported status: {result.report.status_reported_by_worker}")
        console.print(f"Changed files: {len(result.report.changed_files)}")
        console.print(f"Validation results: {len(result.report.validation_results)}")


def _print_worker_report(report: CodexWorkerReport, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Codex worker report: {report.worker_run_id}[/bold]")
    console.print(f"Project: {report.project}")
    console.print(f"Worker reported status: {report.status_reported_by_worker}")
    console.print(f"Source handoff: {report.source_handoff_id or 'none'}")
    console.print(f"Source queue: {report.source_queue_id or 'none'}")
    console.print(f"Source item: {report.source_queue_item_id or 'none'}")
    console.print(f"Source task: {report.source_task_id or 'none'}")
    console.print(f"Summary: {report.summary}", soft_wrap=True)
    console.print(f"Changed files: {len(report.changed_files)}")
    console.print(f"Validation attempted: {report.validation_attempted}")
    console.print(f"Validation results: {len(report.validation_results)}")
    console.print(f"Commit hash: {report.commit_hash or 'none'}")
    if report.safety_warnings:
        console.print("Safety warnings:")
        for warning in report.safety_warnings:
            console.print(f"  - {warning}", soft_wrap=True)
    if report.blockers:
        console.print("Blockers:")
        for blocker in report.blockers:
            console.print(f"  - {blocker}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")
    console.print("Safety: imported reports are worker-provided evidence only; queue/task completion remains explicit.")


def _print_worker_review(review: WorkerReview, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Codex worker review: {review.worker_run_id}[/bold]")
    console.print(f"Project: {review.project}")
    console.print(f"Review id: {review.review_id}")
    console.print(f"Review status: {review.review_status}")
    console.print(f"Reviewer: {review.reviewer or 'none'}")
    console.print(f"Source handoff: {review.source_handoff_id or 'none'}")
    console.print(f"Source queue: {review.source_queue_id or 'none'}")
    console.print(f"Source item: {review.source_queue_item_id or 'none'}")
    console.print(f"Source task: {review.source_task_id or 'none'}")
    console.print(f"Source report path: {review.source_report_path or 'none'}", soft_wrap=True)
    console.print(f"Validation status: {review.validation_evidence.validation_status}")
    console.print(f"Validation summary: {review.validation_evidence.validation_summary or 'none'}", soft_wrap=True)
    console.print(f"Decision note: {review.decision_note or 'none'}", soft_wrap=True)
    console.print(f"Changed files reviewed: {len(review.changed_files_review)}")
    console.print(f"Acceptance criteria reviewed: {len(review.acceptance_criteria_review)}")
    console.print(f"Safety review items: {len(review.safety_review)}")
    console.print(f"Follow-up items: {len(review.follow_up_items)}")
    console.print(f"Next action: {review.next_action}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")
    console.print("Safety: reviews are evidence only. Devo did not run validation, complete queue/task state, commit, push, or modify target source.")


def _print_codex_preflight(result: CodexPreflightResult) -> None:
    console.print(f"[bold]Codex worker preflight: {result.worker_run_id}[/bold]")
    console.print(f"Project: {result.project}")
    console.print(f"Status: {result.status}")
    console.print("Checks:")
    for check in result.checks:
        console.print(f"  - {check.status} {check.name}: {check.detail}", soft_wrap=True)
    console.print("Blocked reasons:")
    for item in result.blocked_reasons or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Warnings:")
    for item in result.warnings or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print(f"Next action: {result.next_action}", soft_wrap=True)
    console.print("Safety: preflight is read-only. Devo did not run Codex or target repo commands.")


def _print_codex_run_plan(plan: CodexRunPlan, json_path: Path | None = None, markdown_path: Path | None = None) -> None:
    console.print(f"[bold]Codex run plan: {plan.plan_id}[/bold]")
    console.print(f"Project: {plan.project}")
    console.print(f"Worker run: {plan.worker_run_id}")
    console.print(f"Handoff: {plan.handoff_id or 'none'}")
    console.print(f"Queue: {plan.queue_id or 'none'}")
    console.print(f"Queue item: {plan.queue_item_id or 'none'}")
    console.print(f"Task: {plan.task_id or 'none'}")
    console.print(f"Status: {plan.status}")
    console.print(f"Approval status: {plan.approval_status}")
    console.print(f"Preflight status: {plan.preflight_status}")
    console.print(f"Proposed working directory: {plan.proposed_working_directory}", soft_wrap=True)
    console.print(f"Proposed command preview: {plan.proposed_command_preview}", soft_wrap=True)
    console.print(f"Blocked reasons: {len(plan.blocked_reasons)}")
    console.print(f"Warnings: {len(plan.warnings)}")
    console.print(f"Next action: {plan.next_action}", soft_wrap=True)
    if json_path:
        console.print(f"JSON: {_named_path(json_path)}")
    if markdown_path:
        console.print(f"Markdown: {_named_path(markdown_path)}")
    console.print("Safety: this is a preview artifact only. Devo did not run Codex, execute target commands, or modify target source.")


def _print_codex_execution_preview(preview: CodexExecutionPreview) -> None:
    console.print(f"[bold]Codex execution preview: {preview.worker_run_id} / {preview.plan_id}[/bold]")
    console.print(f"Project: {preview.project}")
    console.print(f"Ready: {preview.ready}")
    console.print(f"Executable: {preview.executable_path or 'not found'}")
    console.print(f"Command label: {preview.command_label}")
    console.print(f"Working directory: {preview.proposed_working_directory}", soft_wrap=True)
    console.print(f"Prompt path: {preview.prompt_path}", soft_wrap=True)
    console.print(f"Log path: {preview.log_path}", soft_wrap=True)
    console.print(f"Stderr log path: {preview.stderr_log_path}", soft_wrap=True)
    console.print(f"Approval status: {preview.approval_status}")
    console.print(f"Preflight status: {preview.preflight_status}")
    console.print("Blocked reasons:")
    for item in preview.blocked_reasons or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Warnings:")
    for item in preview.warnings or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print("Safety boundaries:")
    for item in preview.safety_boundaries or ["none"]:
        console.print(f"  - {item}", soft_wrap=True)
    console.print(f"Next action: {preview.next_action}", soft_wrap=True)
    console.print("Safety: preview is read-only. Devo did not run Codex or target repo commands.")


def _print_codex_execution_result(result: CodexExecutionResult) -> None:
    console.print(f"[bold]Codex execution result: {result.worker_run_id} / {result.plan_id}[/bold]")
    console.print(f"Project: {result.project}")
    console.print(f"Status: {result.status}")
    console.print(f"Exit code: {result.exit_code}")
    console.print(f"Log path: {result.log_path}", soft_wrap=True)
    console.print(f"Stderr log path: {result.stderr_log_path}", soft_wrap=True)
    console.print(f"Started: {result.started_at.isoformat()}")
    console.print(f"Completed: {result.completed_at.isoformat()}")
    console.print(f"Next action: {result.next_action}", soft_wrap=True)
    console.print("Safety: Codex output is evidence only. Devo did not validate, commit, push, or complete queue/task state.")


def _print_codex_queue_worker_status(status: CodexQueueWorkerStatus) -> None:
    console.print(f"[bold]Codex queue worker status: {status.queue_id}[/bold]")
    console.print(f"Project: {status.project}")
    console.print(f"Queue status: {status.queue_status}")
    console.print(f"Current item: {status.current_item_id or 'none'}")
    console.print(f"Current item status: {status.current_item_status or 'none'}")
    console.print(f"Current task: {status.current_task_id or 'none'}")
    console.print(f"Linked worker run: {status.linked_worker_run_id or 'none'}")
    console.print(f"Linked worker status: {status.linked_worker_run_status or 'none'}")
    console.print(f"Linked run plan: {status.linked_run_plan_id or 'none'}")
    console.print(f"Linked run plan status: {status.linked_run_plan_status or 'none'}")
    console.print(f"Latest execution status: {status.latest_worker_execution_status or 'none'}")
    console.print(f"Latest execution exit code: {status.latest_worker_execution_exit_code if status.latest_worker_execution_exit_code is not None else 'none'}")
    console.print(f"Latest execution log path: {status.latest_worker_execution_log_path or 'none'}", soft_wrap=True)
    console.print(f"Latest review: {status.latest_worker_review_id or 'none'}")
    console.print(f"Latest review status: {status.latest_worker_review_status or 'none'}")
    console.print(f"Latest validation status: {status.latest_worker_validation_status or 'none'}")
    console.print(f"Completion ready: {'yes' if status.current_queue_item_completion_ready else 'no'}")
    console.print(f"Current item review status: {status.current_queue_item_review_status or 'none'}")
    console.print(f"Current item validation status: {status.current_queue_item_validation_status or 'none'}")
    if status.current_queue_item_completion_blockers:
        console.print("Completion blockers:")
        for blocker in status.current_queue_item_completion_blockers:
            console.print(f"  - {blocker}", soft_wrap=True)
    console.print(f"Next action: {status.next_action}", soft_wrap=True)
    console.print("Safety: queue worker status is read-only. Queue item completion remains explicit.")


def _print_json_model(model: object) -> None:
    if hasattr(model, "model_dump_json"):
        typer.echo(model.model_dump_json(indent=2))
        return
    typer.echo(json.dumps(model, indent=2, default=str))


@api_app.command("routes")
def show_api_routes() -> None:
    """Print available read-only API endpoints."""
    from .api import API_ROUTES

    console.print("[bold]Devo read-only API routes[/bold]")
    for route in API_ROUTES:
        console.print(f"  - {route}")


@api_app.command("serve")
def serve_api(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host. MVP allows only 127.0.0.1 or localhost."),
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="Bind port."),
    reload: bool = typer.Option(False, "--reload", help="Enable uvicorn reload for local development."),
) -> None:
    """Start the local read-only API server."""
    from .api import create_app, validate_api_host

    try:
        bind_host = validate_api_host(host)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]", soft_wrap=True)
        raise typer.Exit(1) from exc

    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        console.print("[red]uvicorn is not installed. Reinstall Devo dependencies first.[/red]")
        raise typer.Exit(1) from exc

    url_host = "127.0.0.1" if bind_host == "localhost" else bind_host
    console.print("[bold]Starting Devo read-only API[/bold]")
    console.print("Read-only: true")
    console.print(f"URL: http://{url_host}:{port}")
    if reload:
        uvicorn.run("devo.api:create_app", host=bind_host, port=port, reload=True, factory=True)
        return
    uvicorn.run(create_app(), host=bind_host, port=port)


@ui_app.command("info")
def show_ui_info() -> None:
    """Print local Devo UI/API URLs and manual start commands."""
    urls = ui_urls()
    console.print("[bold]Devo UI[/bold]")
    console.print(f"API: {urls['api']}")
    console.print(f"API health: {urls['api_health']}")
    console.print(f"UI: {urls['ui']}")
    console.print("")
    console.print("Start commands:")
    console.print("  devo api serve")
    console.print("  cd ui")
    console.print("  npm run dev")
    console.print("")
    console.print("UI v1 is read-only.")
    console.print("No approval, build, test, commit, push, restore, scheduler, target app, or model-agent actions exist in UI v1.")


@ui_app.command("urls")
def show_ui_urls() -> None:
    """Print only local Devo UI/API URLs."""
    urls = ui_urls()
    console.print(f"API: {urls['api']}")
    console.print(f"UI: {urls['ui']}")


@ui_app.command("status")
def show_ui_status() -> None:
    """Check whether the local API and UI dev server are reachable without starting them."""
    console.print("[bold]Devo UI status[/bold]")
    for endpoint in check_ui_status():
        console.print(f"{endpoint.status:<4} {endpoint.name}: {endpoint.url} - {endpoint.detail}", soft_wrap=True)
    console.print("Read-only: true")
    console.print("This command does not start servers or mutate workspace state.")


@ui_app.command("open")
def open_ui() -> None:
    """Open the local read-only UI if the UI dev server is already reachable."""
    opened, message = open_ui_if_reachable()
    if not opened:
        console.print(f"[yellow]{message}[/yellow]", soft_wrap=True)
        raise typer.Exit(1)
    console.print(message)


def _resolve_project(project_name: str | None, *, announce: bool = True) -> str:
    if project_name:
        return project_name
    selection = load_current_selection()
    if not selection or not selection.project_name:
        msg = "No project provided and no current project selected. Run: devo use --project <project>"
        typer.echo(msg)
        raise typer.BadParameter(msg, param_hint="--project")
    if announce:
        console.print(f"Using current project: {selection.project_name}")
    return selection.project_name


def _resolve_project_run(project_name: str | None, run_id: str | None, *, announce: bool = True) -> tuple[str, str]:
    selection = load_current_selection()
    resolved_project = project_name or (selection.project_name if selection else None)
    if not resolved_project:
        msg = "No project provided and no current project selected. Run: devo use --project <project>"
        typer.echo(msg)
        raise typer.BadParameter(msg, param_hint="--project")
    if not project_name and announce:
        console.print(f"Using current project: {resolved_project}")

    resolved_run = run_id or (selection.run_id if selection and selection.project_name == resolved_project else None)
    if not resolved_run:
        msg = "No run provided and no current run selected. Run: devo use --project <project> --run <runId>"
        typer.echo(msg)
        raise typer.BadParameter(msg, param_hint="--run")
    if not run_id and announce:
        console.print(f"Using current run: {resolved_run}")
    return resolved_project, resolved_run


@app.command("doctor")
def doctor(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name to include in health checks."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Run read-only Devo and optional project health checks."""
    if project_name is None:
        selection = load_current_selection()
        if selection and selection.project_name:
            project_name = selection.project_name
            if not json_output:
                console.print(f"Using current project: {project_name}")
    report = run_doctor(project_name=project_name)
    if json_output:
        _print_json_model(report)
        return
    _print_doctor_report(report)



def _print_task_selection(
    selection: TaskSelection,
    include_skipped: bool,
    output_format: str,
    candidates_only: bool = False,
) -> None:
    normalized_format = output_format.strip().lower()
    if normalized_format == "json":
        typer.echo(json.dumps(selection.to_dict(), indent=2, default=str))
        return
    if normalized_format != "text":
        raise typer.BadParameter("Unsupported format. Use text or json.", param_hint="--format")

    console.print(f"Project: {selection.project_name}")
    console.print(f"Run: {selection.run_id}")
    console.print(f"Strategy: {selection.strategy}")
    console.print(f"Source artifact: {selection.source_artifact or 'none'}")
    if selection.selected and not candidates_only:
        task = selection.selected
        console.print(f"Selected task: {task.task_id} {task.title}")
        console.print(f"Status: {task.closure_status}")
        console.print(f"Disposition: {task.disposition_status}")
        console.print(f"Reason: {selection.reason}")
        console.print(f"Suggested next command: {selection.suggested_command}")
    elif not candidates_only:
        console.print("Selected task: none")
        console.print(f"Reason: {selection.reason}")
        console.print(f"Run may be ready for closure: {selection.all_resolved}")

    shown = selection.candidates if include_skipped else [item for item in selection.candidates if item.selection_status == "selectable"]
    console.print("Candidates:")
    if not shown:
        console.print("  none")
    for item in shown:
        console.print(f"  - {item.task_id}: {item.title}")
        console.print(f"    status: {item.closure_status}")
        console.print(f"    disposition: {item.disposition_status}")
        console.print(f"    priority: {item.priority or 'unknown'}")
        console.print(f"    risk: {item.risk or 'unknown'}")
        console.print(f"    safety: {item.safety or 'unknown'}")
        console.print(f"    blocked: {item.blocked}")
        console.print(f"    selection rank: {item.selection_rank or 'none'}")
        console.print(f"    selection status: {item.selection_status}")
        console.print(f"    skip reason: {item.skip_reason or 'none'}")
    if selection.warnings:
        console.print("Warnings:")
        for warning in selection.warnings:
            console.print(f"  - {warning}")
    if selection.blockers:
        console.print("Blockers:")
        for blocker in selection.blockers:
            console.print(f"  - {blocker}")


def _print_approval(record: DevoApprovalRecord) -> None:
    paths = approval_artifact_paths(record)
    console.print(f"Approval ID: {record.approval_id}")
    console.print(f"Project: {record.project_name}")
    console.print(f"Run: {record.run_id}")
    console.print(f"Task: {record.task_id}")
    console.print(f"Title: {record.task_title}")
    console.print(f"Action: {record.action_type}")
    console.print(f"Risk level: {record.risk_level}")
    console.print(f"Approval required: {record.approval_required}")
    console.print(f"Blocked: {record.blocked}")
    console.print(f"Status: {record.status.value}")
    console.print(f"Requested at: {record.requested_at.isoformat()}")
    console.print(f"Reason: {record.requested_reason or 'none'}")
    console.print(f"Scope fingerprint: {record.scope_fingerprint}")
    console.print(f"Approved at: {record.approved_at.isoformat() if record.approved_at else 'none'}")
    console.print(f"Approved by: {record.approved_by or 'none'}")
    console.print(f"Approval note: {record.approval_note or 'none'}")
    console.print(f"Rejected at: {record.rejected_at.isoformat() if record.rejected_at else 'none'}")
    console.print(f"Rejected by: {record.rejected_by or 'none'}")
    console.print(f"Rejection note: {record.rejection_note or 'none'}")
    console.print(f"Ledger: {_named_path(paths['ledger'])}")
    console.print(f"JSON: {_named_path(paths['json'])}")
    console.print(f"Markdown: {_named_path(paths['markdown'])}")
    console.print("Policy reasons:")
    for reason in record.policy_reasons or ["none"]:
        console.print(f"  - {reason}")
    console.print("Matched signals:")
    for signal in record.matched_signals or ["none"]:
        console.print(f"  - {signal}")
    console.print("Safety exclusions:")
    for signal in record.safety_exclusion_signals or ["none"]:
        console.print(f"  - {signal}")


def _print_approval_list(records: list[DevoApprovalRecord]) -> None:
    if not records:
        console.print("[yellow]No approvals found.[/yellow]")
        return
    for record in records:
        console.print(f"[bold]{record.approval_id}[/bold]")
        console.print(f"  Task: {record.task_id} {record.task_title}")
        console.print(f"  Action: {record.action_type}")
        console.print(f"  Risk level: {record.risk_level}")
        console.print(f"  Status: {record.status.value}")
        console.print(f"  Requested at: {record.requested_at.isoformat()}")
        console.print(f"  Scope fingerprint: {record.scope_fingerprint}")


def _print_work_package(package: object) -> None:
    paths = work_package_artifact_paths(package)
    next_step = get_work_package_next_step(package)
    console.print(f"Work package: {getattr(package, 'run_id')}")
    console.print(f"Project: {getattr(package, 'project')}")
    console.print(f"Goal: {getattr(package, 'goal')}")
    console.print(f"Lane: {getattr(package, 'lane')}")
    console.print(f"Status: {getattr(package, 'status').value}")
    console.print(f"Approval bundle: {getattr(package, 'approval_bundle_id') or 'none'}")
    console.print(f"Approval bundle status: {getattr(package, 'approval_bundle_status') or 'none'}")
    validation = getattr(package, "validation_run_id") or "none"
    validation_status = getattr(package, "validation_status") or "none"
    console.print(f"Validation: {validation} ({validation_status})")
    console.print(f"Delivery commit: {getattr(package, 'commit_hash') or 'none'}")
    console.print(f"Delivery summary: {getattr(package, 'delivery_summary') or 'none'}")
    delivered_at = getattr(package, "delivered_at") or None
    console.print(f"Delivered at: {delivered_at.isoformat() if delivered_at else 'none'}")
    console.print(f"Final git status: {getattr(package, 'final_git_status') or 'none'}")
    console.print(f"Next action: {work_package_next_action(package)}")
    console.print(f"Suggested next command: {next_step.suggested_prompt_command or next_step.required_command or 'none'}")
    console.print("Proposed items:")
    for item in getattr(package, "proposed_items") or ["none"]:
        console.print(f"  - {item}")
    console.print("Approved files:")
    for file_path in getattr(package, "approved_files") or ["none"]:
        console.print(f"  - {file_path}")
    console.print("Validation commands:")
    for command_id in getattr(package, "validation_commands") or ["none"]:
        console.print(f"  - {command_id}")
    console.print(f"JSON: {_named_path(paths['json'])}")
    console.print(f"Markdown: {_named_path(paths['markdown'])}")
    console.print(f"Operator prompt: {_named_path(paths['operator_prompt'])}")
    console.print(f"Scope template: {_named_path(paths['scope_template'])}")


def _print_work_next(package: object) -> None:
    next_step = get_work_package_next_step(package)
    console.print(f"Project: {getattr(package, 'project')}")
    console.print(f"Run: {getattr(package, 'run_id')}")
    console.print(f"Current status: {next_step.current_status.value}")
    console.print(f"Next action: {next_step.next_action}")
    console.print(f"Required command: {next_step.required_command or 'none'}")
    console.print(f"Suggested prompt command: {next_step.suggested_prompt_command or 'none'}")
    console.print(f"User approval needed: {next_step.user_approval_needed}")
    console.print("Stop conditions:")
    for condition in next_step.stop_conditions or ["none"]:
        console.print(f"  - {condition}")


def _print_work_lane(lane: object) -> None:
    console.print(f"[bold]{getattr(lane, 'id')}[/bold]")
    console.print(f"  Name: {getattr(lane, 'name')}")
    console.print("  Allowed changes:")
    for item in getattr(lane, "allowed") or ["none"]:
        console.print(f"    - {item}")
    console.print("  Forbidden changes:")
    for item in getattr(lane, "forbidden") or ["none"]:
        console.print(f"    - {item}")
    console.print("  Default validation commands:")
    for command_id in getattr(lane, "default_validation_commands") or ["none"]:
        console.print(f"    - {command_id}")
    console.print("  Default validation categories:")
    for category in getattr(lane, "default_validation_categories") or ["none"]:
        console.print(f"    - {category}")
    console.print(f"  Requires registered validation command: {getattr(lane, 'require_registered_validation_command')}")
    console.print("  Notes:")
    for note in getattr(lane, "notes") or ["none"]:
        console.print(f"    - {note}")


def _print_work_summary_list(summaries: list[WorkPackageSummary], title: str, include_delivery: bool = False) -> None:
    if not summaries:
        console.print("[yellow]No runs found.[/yellow]")
        return
    console.print(f"[bold]{title}[/bold]")
    for summary in summaries:
        console.print(f"[bold]Run: {summary.run_id}[/bold]")
        console.print(f"  Goal: {summary.goal}", soft_wrap=True)
        console.print(f"  Lane: {summary.lane}")
        console.print(f"  Status: {summary.status}")
        console.print(f"  Has work package: {summary.has_work_package}")
        console.print(f"  Approval bundle status: {summary.approval_bundle_status}")
        console.print(f"  Latest validation: {summary.latest_validation_status}")
        console.print(f"  Commit: {summary.commit_hash or 'none'}")
        if include_delivery:
            console.print(f"  Delivery summary: {summary.delivery_summary or 'none'}", soft_wrap=True)
        console.print(f"  Next action: {summary.next_action}", soft_wrap=True)


def _print_project_activity(summary: ProjectActivitySummary) -> None:
    console.print(f"[bold]Project activity: {summary.project}[/bold]")
    console.print(f"Current Git status: {summary.current_git_status}", soft_wrap=True)
    console.print(f"Suggested next action: {summary.suggested_next_action}", soft_wrap=True)
    console.print("Recent runs:")
    for line in summary.recent_runs or ["none"]:
        console.print(f"  - {line}", soft_wrap=True)
    console.print("Delivered work packages:")
    if summary.delivered_work_packages:
        for item in summary.delivered_work_packages:
            console.print(f"  - {item.run_id}: {item.delivery_summary or item.goal} ({item.commit_hash or 'no commit'})", soft_wrap=True)
    else:
        console.print("  - none")
    console.print("Latest validation runs:")
    for line in summary.latest_validation_runs or ["none"]:
        console.print(f"  - {line}", soft_wrap=True)
    console.print("Latest context updates:")
    for line in summary.latest_context_updates or ["none"]:
        console.print(f"  - {line}", soft_wrap=True)
    console.print("Latest reports:")
    for line in summary.latest_reports or ["none"]:
        console.print(f"  - {line}", soft_wrap=True)


def _print_approval_bundle(bundle: object) -> None:
    paths = approval_bundle_artifact_paths(bundle)
    console.print(f"Approval bundle: {getattr(bundle, 'bundle_id')}")
    console.print(f"Project: {getattr(bundle, 'project_name')}")
    console.print(f"Run: {getattr(bundle, 'run_id')}")
    console.print(f"Task: {getattr(bundle, 'task_id')}")
    console.print(f"Status: {getattr(bundle, 'status').value}")
    console.print("Child approvals:")
    for approval_id in getattr(bundle, "child_approval_ids") or ["none"]:
        console.print(f"  - {approval_id}")
    console.print(f"Approved at: {getattr(bundle, 'approved_at').isoformat() if getattr(bundle, 'approved_at') else 'none'}")
    console.print(f"Approved by: {getattr(bundle, 'approved_by') or 'none'}")
    console.print(f"Approval note: {getattr(bundle, 'approval_note') or 'none'}")
    console.print(f"JSON: {_named_path(paths['json'])}")
    console.print(f"Markdown: {_named_path(paths['markdown'])}")
def _print_policy_classification(classification: PolicyClassification) -> None:
    console.print(f"Project: {classification.project_name}")
    console.print(f"Run: {classification.run_id}")
    console.print(f"Task: {classification.task_id}")
    console.print(f"Title: {classification.task_title}")
    console.print(f"Risk level: {classification.risk_level}")
    console.print(f"Approval required: {classification.approval_required}")
    console.print(f"Blocked: {classification.blocked}")
    console.print(f"Closure status: {classification.closure_status}")
    console.print(f"Disposition status: {classification.disposition_status}")
    console.print("Reasons:")
    for reason in classification.reasons or ["none"]:
        console.print(f"  - {reason}")
    console.print("Matched risk signals:")
    for signal in classification.matched_risk_signals or ["none"]:
        console.print(f"  - {signal}")
    console.print("Safety exclusions:")
    for signal in classification.safety_exclusion_signals or ["none"]:
        console.print(f"  - {signal}")
    console.print(f"Safe action categories: {', '.join(classification.safe_action_categories) or 'none'}")
    console.print(f"Unsafe action categories: {', '.join(classification.unsafe_action_categories) or 'none'}")
    console.print(f"Recommended next command/action: {classification.recommended_next_command or 'none'}")


def _print_policy_check(result: PolicyCheckResult) -> None:
    console.print(f"Project: {result.project_name}")
    console.print(f"Run: {result.run_id}")
    console.print(f"Task: {result.task_id}")
    console.print(f"Action: {result.action_type}")
    console.print(f"Allowed: {result.allowed}")
    console.print(f"Approval required: {result.approval_required}")
    console.print(f"Blocked: {result.blocked}")
    console.print(f"Risk level: {result.risk_level}")
    console.print(f"Required approval note: {result.required_approval_note or 'none'}")
    console.print(f"Suggested safer alternative: {result.suggested_safer_alternative or 'none'}")
    console.print("Reasons:")
    for reason in result.reasons or ["none"]:
        console.print(f"  - {reason}")
    console.print("Matched risk signals:")
    for signal in result.matched_risk_signals or ["none"]:
        console.print(f"  - {signal}")
    console.print("Safety exclusions:")
    for signal in result.safety_exclusion_signals or ["none"]:
        console.print(f"  - {signal}")


def _print_policy_status(status: PolicyStatus) -> None:
    console.print(f"Project: {status.project_name}")
    console.print(f"Run: {status.run_id}")
    console.print("Tasks:")
    if not status.tasks:
        console.print("  none")
    for task in status.tasks:
        summary = task.reasons[0] if task.reasons else "none"
        console.print(f"  - {task.task_id}: {task.task_title}")
        console.print(f"    status: {task.closure_status}")
        console.print(f"    disposition: {task.disposition_status}")
        console.print(f"    risk level: {task.risk_level}")
        console.print(f"    approval required: {task.approval_required}")
        console.print(f"    blocked: {task.blocked}")
        console.print(f"    reason summary: {summary}")

def _named_path(path: object | None) -> str:
    if not path:
        return "none"
    path_text = str(path)
    return f"{Path(path_text).name} ({path_text})"


def _print_git_repository_status(status: object) -> None:
    console.print(f"[bold]{status.project_name}[/bold]")
    console.print(f"  Repo path: {status.repo_path}", soft_wrap=True)
    console.print(f"  Branch: {status.current_branch or 'unknown'}")
    console.print(f"  HEAD: {status.head_commit or 'unknown'}")
    console.print(f"  Upstream: {status.upstream_branch or 'none'}")
    console.print(f"  Ahead: {status.ahead if status.ahead is not None else 'unknown'}")
    console.print(f"  Behind: {status.behind if status.behind is not None else 'unknown'}")
    console.print(f"  Remote detected: {status.remote_detected}")
    console.print(f"  Working tree clean: {status.working_tree_clean}")
    _print_git_file_group("Staged files", status.staged_files)
    _print_git_file_group("Unstaged files", status.unstaged_files)
    _print_git_file_group("Untracked files", status.untracked_files)
    if status.warnings:
        console.print("  Warnings:")
        for warning in status.warnings:
            console.print(f"    - {warning}", soft_wrap=True)


def _print_git_file_group(label: str, files: object) -> None:
    console.print(f"  {label}:")
    if not files:
        console.print("    none")
        return
    for item in files:
        console.print(f"    - {item.path} ({item.status})", soft_wrap=True)


def _print_git_delivery_check(check: object) -> None:
    _print_git_repository_status(check.status)
    console.print(f"  Delivery readiness: {check.readiness.value}")
    console.print("  Checks performed:")
    for item in check.checks_performed:
        console.print(f"    - {item}", soft_wrap=True)
    console.print("  Blockers:")
    if check.blockers:
        for blocker in check.blockers:
            console.print(f"    - {blocker}", soft_wrap=True)
    else:
        console.print("    none")
    console.print("  Warnings:")
    if check.warnings:
        for warning in check.warnings:
            console.print(f"    - {warning}", soft_wrap=True)
    else:
        console.print("    none")
    console.print("  Secret signals:")
    if check.secret_signals:
        for signal in check.secret_signals:
            console.print(f"    - {signal.path}: {signal.signal_type}", soft_wrap=True)
    else:
        console.print("    none")
    console.print("  Validation evidence:")
    if check.validation_evidence:
        for evidence in check.validation_evidence:
            console.print(f"    - {evidence}", soft_wrap=True)
    else:
        console.print("    none")
    console.print("  Approval evidence:")
    if check.approval_evidence:
        for evidence in check.approval_evidence:
            console.print(f"    - {evidence}", soft_wrap=True)
    else:
        console.print("    none")
    console.print(f"  Suggested commit command: {check.suggested_commit_command or 'none'}", soft_wrap=True)
    console.print(f"  Suggested push command: {check.suggested_push_command or 'none'}", soft_wrap=True)
    console.print(f"  Next human action: {check.next_human_action}", soft_wrap=True)


@git_app.command("status")
def show_git_status(project_name: str = typer.Option(..., "--project", help="Registered project name.")) -> None:
    """Show read-only Git status for a registered project."""
    try:
        status = get_git_repository_status(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_git_repository_status(status)


@git_app.command("delivery-check")
def check_git_delivery(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run ID for validation/approval evidence."),
    task_id: str | None = typer.Option(None, "--task", help="Optional task ID for validation/approval evidence."),
) -> None:
    """Run non-mutating Git delivery readiness checks."""
    try:
        check = run_delivery_check(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_git_delivery_check(check)


@git_app.command("delivery-report")
def write_git_delivery_report(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run ID."),
    task_id: str | None = typer.Option(None, "--task", help="Optional task ID."),
    message: str | None = typer.Option(None, "--message", help="Optional suggested commit message."),
) -> None:
    """Write a Git delivery report artifact without committing or pushing."""
    try:
        report = create_delivery_report(project_name=project_name, run_id=run_id, task_id=task_id, commit_message=message)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Created Git delivery report[/green] for {report.project_name}")
    console.print(f"Readiness: {report.delivery_check.readiness.value}")
    console.print(f"Markdown: {_named_path(report.markdown_path)}")
    console.print(f"JSON: {_named_path(report.json_path)}")
    console.print(f"Next human action: {report.delivery_check.next_human_action}", soft_wrap=True)


def _print_report(report: dict[str, object], output_format: str, write: bool, project_name: str, run_id: str | None = None) -> None:
    normalized = output_format.strip().lower()
    if normalized == "json":
        typer.echo(json.dumps(report, indent=2, default=str))
    elif normalized == "text":
        console.print(render_report_markdown(report), markup=False)
    else:
        raise typer.BadParameter("Unsupported format. Use text or json.", param_hint="--format")
    if write:
        md_path, json_path = write_report_artifacts(report, project_name=project_name, run_id=run_id)
        console.print(f"[green]Wrote report[/green] {Path(md_path).name}")
        console.print(f"Markdown: {_named_path(md_path)}")
        console.print(f"JSON: {_named_path(json_path)}")


@report_app.command("project")
def report_project(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    write: bool = typer.Option(False, "--write", help="Write Markdown and JSON report artifacts."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
    limit: int = typer.Option(5, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Generate a deterministic project-level report."""
    try:
        report = build_project_report(project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_report(report, output_format=output_format, write=write, project_name=project_name)


@report_app.command("run")
def report_run(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    write: bool = typer.Option(False, "--write", help="Write Markdown and JSON report artifacts."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
    limit: int = typer.Option(5, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Generate a deterministic run-level report."""
    try:
        report = build_run_report(project_name, run_id, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    _print_report(report, output_format=output_format, write=write, project_name=project_name, run_id=run_id)


@report_app.command("handoff")
def report_handoff(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run ID."),
    write: bool = typer.Option(False, "--write", help="Write Markdown and JSON handoff artifacts."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
    limit: int = typer.Option(5, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Generate a concise handoff report for context recovery."""
    try:
        report = build_handoff_report(project_name, run_id=run_id, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_report(report, output_format=output_format, write=write, project_name=project_name)


@app.callback()
def main() -> None:
    """DevOrchestrator CLI."""


@project_app.command("add")
def add_project(
    name: str = typer.Option(..., "--name", help="Project name to register."),
    path: Path = typer.Option(..., "--path", help="Existing local project path."),
) -> None:
    """Register a local project path."""
    try:
        registration = register_project(name=name, path=path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--path") from exc

    marker_text = ", ".join(registration.detected_markers) or "none"
    console.print(f"[green]Registered[/green] {registration.name}")
    console.print(f"Path: {registration.path}")
    console.print(f"Looks like software project: {registration.looks_like_software_project}")
    console.print(f"Detected markers: {marker_text}")
    console.print(f"Stored in: {get_workspace_root() / 'projects' / name / 'project.json'}")


@project_app.command("list")
def list_registered_projects() -> None:
    """List registered projects."""
    projects = list_projects()
    if not projects:
        console.print("[yellow]No projects registered.[/yellow]")
        return

    for project in projects:
        marker_text = ", ".join(project.detected_markers) or "none"
        console.print(f"[bold]{project.name}[/bold]")
        console.print(f"  Path: {project.path}", soft_wrap=True)
        console.print(f"  Looks like software project: {project.looks_like_software_project}")
        console.print(f"  Markers: {marker_text}")


@project_app.command("onboard")
def onboard_project(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name to inspect."),
    write_suggestions: bool = typer.Option(False, "--write-suggestions", help="Write workspace onboarding report Markdown."),
    suggest_settings: bool = typer.Option(False, "--suggest-settings", help="Print suggested project settings without writing them."),
) -> None:
    """Show read-only project onboarding progress and the next setup action."""
    project_name = _resolve_project(project_name)
    report = build_project_onboarding_report(
        project_name,
        include_suggested_settings=suggest_settings,
        write_suggestions=write_suggestions,
    )
    _print_project_onboarding(report)


@project_app.command("settings-show")
def show_project_settings(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Show workflow defaults for a registered project."""
    project_name = _resolve_project(project_name)
    try:
        settings = load_project_settings(project_name)
        path = project_settings_path(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_project_settings(settings, path)


@project_app.command("settings-set")
def set_project_settings(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    default_lane: str | None = typer.Option(None, "--default-lane", help="Default work lane for devo work new."),
    default_validation_command: str | None = typer.Option(None, "--default-validation-command", help="Default validation command ID."),
    default_full_test_command: str | None = typer.Option(None, "--default-full-test-command", help="Default full test command ID."),
    default_branch: str | None = typer.Option(None, "--default-branch", help="Expected delivery branch."),
    allow_auto_scope_template: bool | None = typer.Option(
        None,
        "--allow-auto-scope-template/--no-auto-scope-template",
        help="Enable or disable automatic scope-template generation in devo work new.",
    ),
    delivery_mode: str | None = typer.Option(None, "--delivery-mode", help="Delivery mode: manual_commit_push or approved_commit_push."),
    notes: str | None = typer.Option(None, "--notes", help="Free-form project workflow note."),
) -> None:
    """Set workflow defaults for a registered project."""
    if default_lane is not None:
        try:
            get_lane(default_lane)
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--default-lane") from exc
    try:
        result = update_project_settings(
            project_name,
            default_lane=default_lane,
            default_validation_command=default_validation_command,
            default_full_test_command=default_full_test_command,
            default_branch=default_branch,
            allow_auto_scope_template=allow_auto_scope_template,
            delivery_mode=delivery_mode,
            notes=notes,
        )
    except ValueError as exc:
        console.print(str(exc), soft_wrap=True)
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Updated project settings[/green] {project_name}")
    _print_project_settings(result.settings, result.path)
    for warning in result.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}", soft_wrap=True)


@project_app.command("overview")
def show_project_overview(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Show a UI-ready read model overview for one project."""
    project_name = _resolve_project(project_name, announce=not json_output)
    overview = build_project_overview(project_name=project_name, limit=limit)
    if json_output:
        _print_json_model(overview)
        return
    _print_project_overview(overview)


@project_app.command("brief-create")
def create_brief_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    title: str = typer.Option(..., "--title", help="Project brief title."),
    brief_file: Path = typer.Option(..., "--file", help="Markdown or text file containing the final project brief."),
) -> None:
    """Create or update the draft Project Brief artifact from a local text file."""
    project_name = _resolve_project(project_name)
    try:
        brief, paths = create_project_brief(project_name, title, brief_file)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.print(f"[green]Project brief saved[/green] {project_name}")
    console.print(f"Title: {brief.title}")
    console.print(f"Status: {brief.status}")
    console.print(f"JSON: {_named_path(paths.brief_json)}")
    console.print(f"Markdown: {_named_path(paths.brief_markdown)}")
    console.print(f"Suggested next command: devo project brief-approve --project {project_name}")


@project_app.command("brief-show")
def show_brief_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Show the current Project Brief summary without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        load_registered_project(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_project_brief(load_project_brief(project_name), project_name)


@project_app.command("brief-approve")
def approve_brief_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Mark the current Project Brief approved without approving implementation work."""
    project_name = _resolve_project(project_name)
    try:
        brief, paths = approve_project_brief(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Project brief approved[/green] {project_name}")
    console.print(f"Title: {brief.title}")
    console.print(f"JSON: {_named_path(paths.brief_json)}")
    console.print(f"Markdown: {_named_path(paths.brief_markdown)}")
    console.print(f"Suggested next command: devo project blueprint-create --project {project_name}")


@project_app.command("blueprint-create")
def create_blueprint_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Create or update a deterministic draft Blueprint from the current Project Brief."""
    project_name = _resolve_project(project_name)
    try:
        blueprint, paths = create_project_blueprint(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Project blueprint saved[/green] {project_name}")
    console.print(f"Title: {blueprint.title}")
    console.print(f"Status: {blueprint.status}")
    console.print(f"Milestones: {len(blueprint.milestones)}")
    console.print(f"Epics: {len(blueprint.epics)}")
    console.print(f"JSON: {_named_path(paths.blueprint_json)}")
    console.print(f"Markdown: {_named_path(paths.blueprint_markdown)}")
    console.print(f"Suggested next command: devo project blueprint-approve --project {project_name}")


@project_app.command("blueprint-show")
def show_blueprint_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Show the current Blueprint summary without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        load_registered_project(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_project_blueprint(load_project_blueprint(project_name), project_name)


@project_app.command("blueprint-approve")
def approve_blueprint_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Mark the current Blueprint approved without approving implementation work."""
    project_name = _resolve_project(project_name)
    try:
        blueprint, paths = approve_project_blueprint(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Project blueprint approved[/green] {project_name}")
    console.print(f"Title: {blueprint.title}")
    console.print(f"JSON: {_named_path(paths.blueprint_json)}")
    console.print(f"Markdown: {_named_path(paths.blueprint_markdown)}")
    console.print(f"Suggested next command: devo project backlog-create --project {project_name}")


@project_app.command("backlog-create")
def create_backlog_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Create or update a deterministic draft Backlog from the current Blueprint."""
    project_name = _resolve_project(project_name)
    try:
        backlog, paths = create_project_backlog(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Project backlog saved[/green] {project_name}")
    console.print(f"Title: {backlog.title}")
    console.print(f"Status: {backlog.status}")
    console.print(f"Tasks: {backlog.task_count}")
    console.print(f"Ready: {backlog.ready_task_count}")
    console.print(f"Blocked: {backlog.blocked_task_count}")
    console.print(f"Completed: {backlog.completed_task_count}")
    console.print(f"JSON: {_named_path(paths.backlog_json)}")
    console.print(f"Markdown: {_named_path(paths.backlog_markdown)}")
    console.print("Starter backlog guidance:")
    console.print("  - This deterministic starter backlog is not implementation-ready by default.", soft_wrap=True)
    console.print(f"  - Refine it with: devo project backlog-prompt --project {project_name}", soft_wrap=True)
    console.print(f"  - Import refined JSON with: devo project backlog-import --project {project_name} --file <refined-backlog.json>", soft_wrap=True)
    console.print("  - Review and approve the refined backlog before batch creation.", soft_wrap=True)
    console.print(f"Suggested next command: devo project backlog-prompt --project {project_name}")


@project_app.command("backlog-show")
def show_backlog_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Show the current Backlog summary without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        load_registered_project(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_project_backlog(load_project_backlog(project_name), project_name)


@project_app.command("backlog-approve")
def approve_backlog_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Mark the current Backlog approved without approving implementation work."""
    project_name = _resolve_project(project_name)
    try:
        backlog, paths = approve_project_backlog(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Project backlog approved[/green] {project_name}")
    console.print(f"Title: {backlog.title}")
    console.print(f"Tasks: {backlog.task_count}")
    console.print(f"Ready: {backlog.ready_task_count}")
    console.print(f"JSON: {_named_path(paths.backlog_json)}")
    console.print(f"Markdown: {_named_path(paths.backlog_markdown)}")
    typer.echo(f"Suggested next command: devo project batch-suggest --project {project_name} --limit 10")
    typer.echo(f"Suggested write command: devo project batch-suggest --project {project_name} --limit 10 --write")


@project_app.command("task-list")
def list_backlog_tasks_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List tasks from the current Backlog without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        backlog = load_project_backlog(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    if not backlog:
        console.print(f"[yellow]Project backlog not found for {project_name}.[/yellow]")
        console.print(f"Suggested next command: devo project backlog-create --project {project_name}")
        return
    console.print(f"[bold]Backlog tasks: {project_name}[/bold]")
    if not backlog.tasks:
        console.print("[yellow]No tasks recorded.[/yellow]")
        return
    for task in backlog.tasks:
        console.print(
            f"{task.id} | {task.status} | lane={task.lane} | risk={task.risk_level} | "
            f"milestone={task.milestone_id or 'none'} | epic={task.epic_id or 'none'} | {task.title}",
            soft_wrap=True,
        )


@project_app.command("task-show")
def show_backlog_task_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    task_id: str = typer.Option(..., "--task", help="Backlog task id."),
) -> None:
    """Show one Backlog task without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        task = get_backlog_task(project_name, task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc
    _print_backlog_task(task)


@project_app.command("backlog-prompt")
def create_backlog_refinement_prompt_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Write a Codex-ready planning prompt for refining the current Backlog."""
    project_name = _resolve_project(project_name)
    try:
        path, _prompt = generate_backlog_refinement_prompt(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[green]Backlog refinement prompt written[/green] {project_name}")
    console.print(f"Prompt: {_named_path(path)}")
    console.print("Next suggested step: paste this prompt into Codex/manual planning, then import the refined backlog JSON.")
    console.print(f"Suggested import command: devo project backlog-import --project {project_name} --file <refined-backlog.json>")


@project_app.command("backlog-validate")
def validate_backlog_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    refined_file: Path = typer.Option(..., "--file", help="Refined backlog JSON file to validate."),
) -> None:
    """Validate a refined Backlog JSON file without importing it."""
    project_name = _resolve_project(project_name)
    try:
        result, _backlog = validate_refined_backlog_file(project_name, refined_file)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--file") from exc
    _print_backlog_validation_result(result)
    if not result.valid:
        raise typer.Exit(1)


@project_app.command("backlog-import")
def import_backlog_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    refined_file: Path = typer.Option(..., "--file", help="Refined backlog JSON file to import."),
) -> None:
    """Import a validated refined Backlog JSON file as a draft Backlog."""
    project_name = _resolve_project(project_name)
    try:
        backlog, paths, result = import_refined_backlog(project_name, refined_file)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--file") from exc
    console.print(f"[green]Refined backlog imported[/green] {project_name}")
    console.print(f"Status: {backlog.status}")
    console.print(f"Tasks: {backlog.task_count}")
    console.print(f"Ready: {backlog.ready_task_count}")
    console.print(f"Blocked: {backlog.blocked_task_count}")
    console.print(f"Completed: {backlog.completed_task_count}")
    if result.warnings:
        console.print("Warnings:")
        for warning in result.warnings:
            console.print(f"  - {warning}", soft_wrap=True)
    console.print(f"JSON: {_named_path(paths.backlog_json)}")
    console.print(f"Markdown: {_named_path(paths.backlog_markdown)}")
    console.print(f"Suggested next command: devo project backlog-show --project {project_name}")


@project_app.command("batch-create")
def create_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    title: str = typer.Option(..., "--title", help="Batch title."),
    tasks: str = typer.Option(..., "--tasks", help="Comma-separated backlog task ids."),
) -> None:
    """Create a draft planning Batch from explicit backlog task ids."""
    project_name = _resolve_project(project_name)
    try:
        batch, json_path, markdown_path = create_project_batch(project_name, title=title, task_ids=[tasks])
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--tasks") from exc
    console.print(f"[green]Project batch saved[/green] {project_name}")
    _print_project_batch(batch, json_path=json_path, markdown_path=markdown_path)
    console.print(f"Suggested next command: devo project batch-show --project {project_name} --batch {batch.batch_id}")
    console.print(f"Suggested next command: devo project queue-create --project {project_name} --batch {batch.batch_id}")


@project_app.command("batch-suggest")
def suggest_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Maximum task count to suggest."),
    write: bool = typer.Option(False, "--write", help="Write the suggestion as a draft batch."),
) -> None:
    """Suggest ready backlog tasks for a planning Batch without writing unless requested."""
    project_name = _resolve_project(project_name)
    try:
        if write:
            batch, json_path, markdown_path, suggestion = create_suggested_project_batch(project_name, limit=limit)
            _print_batch_suggestion(suggestion)
            console.print(f"[green]Suggested project batch saved[/green] {project_name}")
            _print_project_batch(batch, json_path=json_path, markdown_path=markdown_path)
            console.print(f"Suggested next command: devo project batch-review --project {project_name} --batch {batch.batch_id} --note \"<review note>\"")
            return
        suggestion = suggest_project_batch(project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_batch_suggestion(suggestion)
    if suggestion.suggested_tasks:
        task_ids = ",".join(task.task_id for task in suggestion.suggested_tasks)
        console.print(f"Suggested write command: devo project batch-create --project {project_name} --title \"<batch title>\" --tasks {task_ids}")


@project_app.command("batch-list")
def list_batches_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List planning Batches for a project."""
    project_name = _resolve_project(project_name)
    try:
        batches = list_project_batches(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Project batches: {project_name}[/bold]")
    if not batches:
        console.print("[yellow]No batches recorded.[/yellow]")
        console.print(f"Suggested next command: devo project batch-suggest --project {project_name}")
        return
    for batch in batches:
        console.print(
            f"{batch.batch_id} | {batch.status} | approval={batch.approval_status} | tasks={batch.task_count} | {batch.title}",
            soft_wrap=True,
        )


@project_app.command("batch-show")
def show_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
) -> None:
    """Show a planning Batch without mutating it."""
    project_name = _resolve_project(project_name)
    try:
        batch = load_project_batch(project_name, batch_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    if not batch:
        console.print(f"[yellow]Project batch not found: {batch_id}[/yellow]")
        console.print(f"Suggested next command: devo project batch-list --project {project_name}")
        return
    _print_project_batch(batch)
    approval = load_batch_approval(project_name, batch.batch_id)
    if approval:
        _print_batch_approval(approval)
    else:
        console.print(f"Suggested next command: devo project batch-approval-request --project {project_name} --batch {batch.batch_id} --note \"<note>\"")


@project_app.command("batch-approval-request")
def request_batch_approval_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
    note: str = typer.Option("", "--note", help="Request note."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name to record."),
) -> None:
    """Create or update a workspace-only Batch approval request artifact."""
    project_name = _resolve_project(project_name)
    try:
        approval, json_path, markdown_path = request_batch_approval(project_name, batch_id, note=note, reviewer=reviewer)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[green]Batch approval requested[/green] {project_name}")
    _print_batch_approval(approval, json_path=json_path, markdown_path=markdown_path)
    console.print(f"Suggested next command: devo project batch-review --project {project_name} --batch {approval.batch_id} --note \"<review note>\"")


@project_app.command("batch-approval-show")
def show_batch_approval_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
) -> None:
    """Show a workspace-only Batch approval request artifact."""
    project_name = _resolve_project(project_name)
    try:
        approval = load_batch_approval(project_name, batch_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    if not approval:
        console.print(f"[yellow]Batch approval artifact not found: {batch_id}[/yellow]")
        console.print(f"Suggested next command: devo project batch-approval-request --project {project_name} --batch {batch_id} --note \"<note>\"")
        return
    _print_batch_approval(approval)


@project_app.command("batch-approval-list")
def list_batch_approvals_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List workspace-only Batch approval artifacts for a project."""
    project_name = _resolve_project(project_name)
    try:
        approvals = list_batch_approvals(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Batch approvals: {project_name}[/bold]")
    if not approvals:
        console.print("[yellow]No batch approval artifacts recorded.[/yellow]")
        return
    for approval in approvals:
        console.print(
            f"{approval.batch_id} | approval={approval.approval_status} | review={approval.review_status} | tasks={approval.task_count} | next={approval.next_action}",
            soft_wrap=True,
        )


@project_app.command("batch-approve")
def approve_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
    note: str = typer.Option("", "--note", help="Decision note."),
    approver: str | None = typer.Option(None, "--approver", help="Approver name to record."),
) -> None:
    """Mark a planning Batch approved without approving implementation execution."""
    project_name = _resolve_project(project_name)
    try:
        batch, json_path, markdown_path, approval, approval_json, approval_md, direct = approve_project_batch(
            project_name,
            batch_id,
            note=note,
            approver=approver,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[green]Project batch approved[/green] {project_name}")
    if direct:
        console.print("[yellow]Approval was recorded without a prior requested approval artifact.[/yellow]")
    _print_project_batch(batch, json_path=json_path, markdown_path=markdown_path)
    _print_batch_approval(approval, json_path=approval_json, markdown_path=approval_md)
    console.print("Planning approval only. No queue was created and no target commands were run.")
    console.print(f"Suggested next command: devo project queue-create --project {project_name} --batch {batch.batch_id}")


@project_app.command("batch-review")
def review_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
    note: str = typer.Option(..., "--note", help="Review note to append."),
    needs_changes: bool = typer.Option(False, "--needs-changes", help="Mark the approval review as needing changes."),
    reviewer: str | None = typer.Option(None, "--reviewer", help="Reviewer name to record."),
) -> None:
    """Append a review note to a planning Batch."""
    project_name = _resolve_project(project_name)
    try:
        batch, json_path, markdown_path, approval, approval_json, approval_md = review_project_batch(
            project_name,
            batch_id,
            note,
            needs_changes=needs_changes,
            reviewer=reviewer,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[green]Project batch reviewed[/green] {project_name}")
    _print_project_batch(batch, json_path=json_path, markdown_path=markdown_path)
    if approval:
        _print_batch_approval(approval, json_path=approval_json, markdown_path=approval_md)
    next_command = (
        f"devo project batch-show --project {project_name} --batch {batch.batch_id}"
        if needs_changes
        else f"devo project batch-approve --project {project_name} --batch {batch.batch_id} --note \"<decision note>\""
    )
    console.print(f"Suggested next command: {next_command}")


@project_app.command("batch-reject")
def reject_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
    note: str = typer.Option(..., "--note", help="Decision note."),
    approver: str | None = typer.Option(None, "--approver", help="Approver name to record."),
) -> None:
    """Reject a planning Batch without deleting it or mutating target repositories."""
    project_name = _resolve_project(project_name)
    try:
        batch, json_path, markdown_path, approval, approval_json, approval_md = reject_project_batch(
            project_name,
            batch_id,
            note=note,
            approver=approver,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[yellow]Project batch rejected[/yellow] {project_name}")
    _print_project_batch(batch, json_path=json_path, markdown_path=markdown_path)
    _print_batch_approval(approval, json_path=approval_json, markdown_path=approval_md)
    console.print("No batch was deleted and no target project files were modified.")


@project_app.command("progress")
def show_project_progress_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Compute deterministic planning progress from brief, blueprint, backlog, and batches."""
    project_name = _resolve_project(project_name, announce=not json_output)
    try:
        progress = calculate_project_progress(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    if json_output:
        _print_json_model(progress)
        return
    _print_project_progress(progress)


@project_app.command("queue-create")
def create_queue_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Approved planning batch id."),
) -> None:
    """Create an execution queue from an approved planning Batch without executing it."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = create_execution_queue_from_batch(project_name, batch_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[green]Execution queue saved[/green] {project_name}")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)
    console.print(f"Suggested next command: devo project queue-start --project {project_name} --queue {queue.queue_id}")
    console.print(f"Suggested handoff command: devo project handoff-next --project {project_name} --queue {queue.queue_id}")


@project_app.command("queue-list")
def list_queues_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List execution queues for a project."""
    project_name = _resolve_project(project_name)
    try:
        queues = list_execution_queues(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Execution queues: {project_name}[/bold]")
    if not queues:
        console.print("[yellow]No queues recorded.[/yellow]")
        console.print(f"Suggested next command: devo project queue-create --project {project_name} --batch <batchId>")
        return
    for queue in queues:
        console.print(
            f"{queue.queue_id} | batch={queue.source_batch_id} | {queue.status} | "
            f"pending={queue.pending_count} completed={queue.completed_count} blocked={queue.blocked_count} | {queue.title}",
            soft_wrap=True,
        )


@project_app.command("queue-show")
def show_queue_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Show execution queue details without mutating them."""
    project_name = _resolve_project(project_name)
    try:
        queue = load_execution_queue(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    if not queue:
        console.print(f"[yellow]Execution queue not found: {queue_id}[/yellow]")
        console.print(f"Suggested next command: devo project queue-list --project {project_name}")
        return
    _print_execution_queue(queue)
    item = next((entry for entry in queue.items if entry.item_id == queue.current_item_id), None)
    if item:
        _print_queue_item_completion_readiness(get_queue_item_completion_readiness(project_name, queue.queue_id, item.item_id))
    console.print(f"Suggested handoff command: devo project handoff-next --project {project_name} --queue {queue.queue_id}")


@project_app.command("queue-start")
def start_queue_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Move a queue to running and mark the first pending item running without executing it."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = start_execution_queue(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    console.print(f"[green]Execution queue started[/green] {project_name}")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)
    current = next((item for item in queue.items if item.item_id == queue.current_item_id), None)
    _print_queue_item(current, project_name=project_name, queue_id=queue.queue_id)


@project_app.command("queue-next")
def next_queue_item_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Show the current running or next pending queue item without generating prompts."""
    project_name = _resolve_project(project_name)
    try:
        queue, item = get_queue_next_item(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    console.print(f"[bold]Execution queue next: {queue.queue_id}[/bold]")
    console.print(f"Queue status: {queue.status}")
    _print_queue_item(item, project_name=project_name, queue_id=queue.queue_id)
    if item:
        _print_queue_item_completion_readiness(get_queue_item_completion_readiness(project_name, queue.queue_id, item.item_id))


@project_app.command("queue-complete-item")
def complete_queue_item_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
    item_id: str = typer.Option(..., "--item", help="Queue item id."),
    note: str = typer.Option(..., "--note", help="Completion note."),
    confirm_without_review: bool = typer.Option(False, "--confirm-without-review", help="Emergency/manual override for completing without reviewed_passed worker review evidence."),
) -> None:
    """Mark one queue item completed and advance queue state without executing commands."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = complete_queue_item(project_name, queue_id, item_id, note, confirm_without_review=confirm_without_review)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--item") from exc
    console.print(f"[green]Queue item completed[/green] {project_name}")
    if confirm_without_review:
        console.print("[yellow]Completed with --confirm-without-review. This bypass is discouraged and was recorded in queue item notes.[/yellow]")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)


@project_app.command("queue-block-item")
def block_queue_item_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
    item_id: str = typer.Option(..., "--item", help="Queue item id."),
    note: str = typer.Option(..., "--note", help="Blocker note."),
) -> None:
    """Mark one queue item blocked and pause the queue for review."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = block_queue_item(project_name, queue_id, item_id, note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--item") from exc
    console.print(f"[yellow]Queue item blocked[/yellow] {project_name}")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)


@project_app.command("queue-pause")
def pause_queue_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
    reason: str = typer.Option(..., "--reason", help="Pause reason: usage_limit, failure, review, manual."),
    note: str = typer.Option(..., "--note", help="Pause note/resume hint."),
) -> None:
    """Pause queue state without executing or stopping external processes."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = pause_execution_queue(project_name, queue_id, reason, note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--reason") from exc
    console.print(f"[yellow]Execution queue paused[/yellow] {project_name}")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)


@project_app.command("queue-resume")
def resume_queue_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Resume a paused execution queue without executing it."""
    project_name = _resolve_project(project_name)
    try:
        queue, json_path, markdown_path = resume_execution_queue(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    console.print(f"[green]Execution queue resumed[/green] {project_name}")
    _print_execution_queue(queue, json_path=json_path, markdown_path=markdown_path)


@project_app.command("handoff-next")
def create_handoff_next_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Generate a Codex-ready handoff prompt for the current or next queue item."""
    project_name = _resolve_project(project_name)
    try:
        handoff, json_path, prompt_path = create_codex_handoff_for_queue_next(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    console.print(f"[green]Codex handoff prompt saved[/green] {project_name}")
    _print_codex_handoff(handoff, json_path=json_path, prompt_path=prompt_path)


@project_app.command("handoff-task")
def create_handoff_task_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    task_id: str = typer.Option(..., "--task", help="Backlog task id."),
) -> None:
    """Generate a Codex-ready handoff prompt for a single backlog task."""
    project_name = _resolve_project(project_name)
    try:
        handoff, json_path, prompt_path = create_codex_handoff_for_task(project_name, task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc
    console.print(f"[green]Codex handoff prompt saved[/green] {project_name}")
    _print_codex_handoff(handoff, json_path=json_path, prompt_path=prompt_path)


@project_app.command("handoff-batch")
def create_handoff_batch_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    batch_id: str = typer.Option(..., "--batch", help="Planning batch id."),
) -> None:
    """Generate a Codex-ready handoff prompt for an approved batch scope."""
    project_name = _resolve_project(project_name)
    try:
        handoff, json_path, prompt_path = create_codex_handoff_for_batch(project_name, batch_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--batch") from exc
    console.print(f"[green]Codex handoff prompt saved[/green] {project_name}")
    _print_codex_handoff(handoff, json_path=json_path, prompt_path=prompt_path)
    console.print("Batch handoff must stay within the approved batch scope.")


@project_app.command("handoff-list")
def list_handoffs_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List generated Codex handoff prompts for a project."""
    project_name = _resolve_project(project_name)
    try:
        handoffs = list_codex_handoffs(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Codex handoffs: {project_name}[/bold]")
    if not handoffs:
        console.print("[yellow]No handoffs recorded.[/yellow]")
        console.print(f"Suggested next command: devo project handoff-task --project {project_name} --task <taskId>")
        return
    for handoff in handoffs:
        console.print(
            f"{handoff.handoff_id} | {handoff.handoff_type} | {handoff.status} | "
            f"task={handoff.source_task_id or 'none'} batch={handoff.source_batch_id or 'none'} queue={handoff.source_queue_id or 'none'} | {handoff.title}",
            soft_wrap=True,
        )


@project_app.command("handoff-show")
def show_handoff_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    handoff_id: str = typer.Option(..., "--handoff", help="Codex handoff id."),
    print_prompt: bool = typer.Option(False, "--print", help="Print prompt content."),
) -> None:
    """Show Codex handoff metadata and prompt path without mutating anything."""
    project_name = _resolve_project(project_name)
    try:
        handoff = load_codex_handoff(project_name, handoff_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--handoff") from exc
    if not handoff:
        console.print(f"[yellow]Codex handoff not found: {handoff_id}[/yellow]")
        console.print(f"Suggested next command: devo project handoff-list --project {project_name}")
        return
    _print_codex_handoff(handoff)
    if print_prompt:
        prompt_path = Path(handoff.prompt_path)
        if prompt_path.exists():
            console.print("")
            console.print(prompt_path.read_text(encoding="utf-8"), soft_wrap=True)


@project_app.command("handoff-mark-used")
def mark_handoff_used_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    handoff_id: str = typer.Option(..., "--handoff", help="Codex handoff id."),
) -> None:
    """Mark a handoff prompt used as a workspace-only planning artifact."""
    project_name = _resolve_project(project_name)
    try:
        handoff, json_path, prompt_path = mark_codex_handoff_used(project_name, handoff_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--handoff") from exc
    console.print(f"[green]Codex handoff marked used[/green] {project_name}")
    _print_codex_handoff(handoff, json_path=json_path, prompt_path=prompt_path)


@worker_codex_app.command("run-create")
def create_codex_worker_run_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    handoff_id: str = typer.Option(..., "--handoff", help="Codex handoff id."),
) -> None:
    """Create a planned Codex worker run record from an existing handoff without running Codex."""
    project_name = _resolve_project(project_name)
    try:
        worker_run, json_path, markdown_path = create_codex_worker_run_from_handoff(project_name, handoff_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--handoff") from exc
    console.print(f"[green]Codex worker run recorded[/green] {project_name}")
    _print_worker_run(worker_run, json_path=json_path, markdown_path=markdown_path)
    console.print(f"Manual action: paste the handoff prompt into Codex from {_named_path(Path(worker_run.prompt_path))}.", soft_wrap=True)
    console.print("Future TASK-DEVO-089 will import/review worker reports. This command does not trust or complete worker output.")


@worker_codex_app.command("run-list")
def list_codex_worker_runs_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List Codex worker run records for a project."""
    project_name = _resolve_project(project_name)
    try:
        worker_runs = list_codex_worker_runs(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Codex worker runs: {project_name}[/bold]")
    if not worker_runs:
        console.print("[yellow]No Codex worker runs recorded.[/yellow]")
        console.print(f"Suggested next command: devo worker codex run-create --project {project_name} --handoff <handoffId>")
        return
    for worker_run in worker_runs:
        console.print(
            f"{worker_run.worker_run_id} | {worker_run.status} | handoff={worker_run.source_handoff_id or 'none'} "
            f"task={worker_run.source_task_id or 'none'} report={worker_run.report.report_status} | {worker_run.title}",
            soft_wrap=True,
        )


@worker_codex_app.command("run-show")
def show_codex_worker_run_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Show Codex worker run metadata without mutating anything."""
    project_name = _resolve_project(project_name)
    try:
        worker_run = load_codex_worker_run(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    if not worker_run:
        console.print(f"[yellow]Codex worker run not found: {worker_run_id}[/yellow]")
        console.print(f"Suggested next command: devo worker codex run-list --project {project_name}")
        return
    json_path, markdown_path = worker_run_artifact_paths(project_name, worker_run.worker_run_id)
    _print_worker_run(worker_run, json_path=json_path, markdown_path=markdown_path)


@worker_codex_app.command("run-status")
def update_codex_worker_run_status_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    status: str = typer.Option(..., "--status", help="New worker run status."),
    note: str = typer.Option("", "--note", help="Status note."),
) -> None:
    """Update a Codex worker run status as a workspace-only tracking artifact."""
    project_name = _resolve_project(project_name)
    try:
        worker_run, json_path, markdown_path = update_codex_worker_run_status(project_name, worker_run_id, status, note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--status") from exc
    console.print(f"[green]Codex worker run status updated[/green] {project_name}")
    _print_worker_run(worker_run, json_path=json_path, markdown_path=markdown_path)
    console.print("No queue item, backlog task, validation, commit, or push state was updated automatically.")


@worker_codex_app.command("run-mark-used")
def mark_codex_worker_run_used_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Mark the linked Codex handoff used without implying worker completion."""
    project_name = _resolve_project(project_name)
    try:
        worker_run, json_path, markdown_path = mark_codex_worker_run_handoff_used(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"[green]Linked handoff marked used[/green] {project_name}")
    _print_worker_run(worker_run, json_path=json_path, markdown_path=markdown_path)
    console.print("This does not imply worker completion or queue/task completion.")


@worker_codex_app.command("report-template")
def create_codex_worker_report_template_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Create a JSON/Markdown template for a manual Codex worker report."""
    project_name = _resolve_project(project_name)
    try:
        json_path, markdown_path, _template = create_codex_worker_report_template(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"[green]Codex worker report template saved[/green] {project_name}")
    console.print(f"JSON template: {_named_path(json_path)}")
    console.print(f"Markdown template: {_named_path(markdown_path)}")
    console.print("Paste Codex's final report into the JSON structure, then run:")
    console.print(f"  devo worker codex report-validate --project {project_name} --run {worker_run_id} --file {_named_path(json_path)}", soft_wrap=True)
    console.print(f"  devo worker codex report-import --project {project_name} --run {worker_run_id} --file <filledReportFile>", soft_wrap=True)
    console.print("This command does not import the report or modify the target project.")


@worker_codex_app.command("report-validate")
def validate_codex_worker_report_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    report_file: Path = typer.Option(..., "--file", help="Codex worker report JSON file."),
) -> None:
    """Validate a manual Codex worker report without importing it."""
    project_name = _resolve_project(project_name)
    result = validate_codex_worker_report_file(project_name, worker_run_id, report_file)
    _print_worker_report_validation(result)
    console.print("No queue item, backlog task, validation, Git, commit, push, or target repository state was modified.")
    if not result.valid:
        raise typer.Exit(1)


@worker_codex_app.command("report-import")
def import_codex_worker_report_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    report_file: Path = typer.Option(..., "--file", help="Codex worker report JSON file."),
) -> None:
    """Import a validated manual Codex worker report as workspace-only evidence."""
    project_name = _resolve_project(project_name)
    try:
        worker_run, report, validation, report_json, report_markdown, worker_json, worker_markdown = import_codex_worker_report(
            project_name,
            worker_run_id,
            report_file,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--file") from exc
    console.print(f"[green]Codex worker report imported[/green] {project_name}")
    _print_worker_report_validation(validation)
    _print_worker_report(report, json_path=report_json, markdown_path=report_markdown)
    _print_worker_run(worker_run, json_path=worker_json, markdown_path=worker_markdown)
    console.print("Next suggested command:")
    console.print(f"  devo worker codex report-show --project {project_name} --run {worker_run.worker_run_id}", soft_wrap=True)
    console.print("Review report manually, verify validation independently, then use queue-complete-item only after review.")


@worker_codex_app.command("report-show")
def show_codex_worker_report_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Show imported Codex worker report metadata without mutating anything."""
    project_name = _resolve_project(project_name)
    try:
        worker_run = load_codex_worker_run(project_name, worker_run_id)
        report = load_codex_worker_report(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    if not worker_run:
        console.print(f"[yellow]Codex worker run not found: {worker_run_id}[/yellow]")
        return
    if not report:
        console.print(f"[yellow]Codex worker report not found for run: {worker_run_id}[/yellow]")
        console.print(f"Suggested next command: devo worker codex report-template --project {project_name} --run {worker_run.worker_run_id}")
        return
    report_json, report_markdown = worker_report_artifact_paths(project_name, worker_run.worker_run_id)
    _print_worker_report(report, json_path=report_json, markdown_path=report_markdown)
    console.print(f"Worker run next action: {worker_run.next_action}", soft_wrap=True)


@worker_codex_app.command("report-list")
def list_codex_worker_reports_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List imported Codex worker reports for a project."""
    project_name = _resolve_project(project_name)
    try:
        reports = list_codex_worker_reports(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Codex worker reports: {project_name}[/bold]")
    if not reports:
        console.print("[yellow]No Codex worker reports imported.[/yellow]")
        console.print(f"Suggested next command: devo worker codex report-template --project {project_name} --run <workerRunId>")
        return
    for report in reports:
        console.print(
            f"{report.worker_run_id} | {report.status_reported_by_worker} | changed={len(report.changed_files)} "
            f"validation={len(report.validation_results)} | {report.summary}",
            soft_wrap=True,
        )


@worker_codex_app.command("review-template")
def create_codex_worker_review_template_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Create a JSON/Markdown review template for worker evidence without completing queue state."""
    project_name = _resolve_project(project_name)
    try:
        review, json_path, markdown_path = create_codex_worker_review_template(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"[green]Codex worker review template saved[/green] {project_name}")
    _print_worker_review(review, json_path=json_path, markdown_path=markdown_path)
    console.print("Next suggested commands:")
    console.print(f"  devo worker codex review-attach-evidence --project {project_name} --run {review.worker_run_id} --status provided --summary \"<validation summary>\"", soft_wrap=True)
    console.print(f"  devo worker codex review-record --project {project_name} --run {review.worker_run_id} --status reviewed_passed --reviewer \"<name>\" --note \"<note>\"", soft_wrap=True)


@worker_codex_app.command("review-show")
def show_codex_worker_review_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Show worker review evidence without mutating anything."""
    project_name = _resolve_project(project_name)
    try:
        review = load_codex_worker_review(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    if not review:
        console.print(f"[yellow]Codex worker review not found for run: {worker_run_id}[/yellow]")
        console.print(f"Suggested next command: devo worker codex review-template --project {project_name} --run {worker_run_id}")
        return
    json_path, markdown_path = worker_review_artifact_paths(project_name, review.worker_run_id)
    _print_worker_review(review, json_path=json_path, markdown_path=markdown_path)


@worker_codex_app.command("review-list")
def list_codex_worker_reviews_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List Codex worker review artifacts for a project."""
    project_name = _resolve_project(project_name)
    try:
        reviews = list_codex_worker_reviews(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Codex worker reviews: {project_name}[/bold]")
    if not reviews:
        console.print("[yellow]No Codex worker reviews recorded.[/yellow]")
        console.print(f"Suggested next command: devo worker codex review-template --project {project_name} --run <workerRunId>")
        return
    for review in reviews:
        console.print(
            f"{review.worker_run_id} | {review.review_status} | validation={review.validation_evidence.validation_status} "
            f"reviewer={review.reviewer or 'none'} | {review.next_action}",
            soft_wrap=True,
        )


@worker_codex_app.command("review-record")
def record_codex_worker_review_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    status: str = typer.Option(..., "--status", help="Review decision: reviewed_passed, reviewed_needs_changes, or rejected."),
    reviewer: str = typer.Option(..., "--reviewer", help="Reviewer name."),
    note: str = typer.Option(..., "--note", help="Review decision note."),
) -> None:
    """Record a worker review decision without completing queue/task state."""
    project_name = _resolve_project(project_name)
    try:
        review, worker_run, review_json, review_markdown, worker_json, worker_markdown = record_codex_worker_review(
            project_name,
            worker_run_id,
            status,
            reviewer,
            note,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--status") from exc
    console.print(f"[green]Codex worker review recorded[/green] {project_name}")
    _print_worker_review(review, json_path=review_json, markdown_path=review_markdown)
    _print_worker_run(worker_run, json_path=worker_json, markdown_path=worker_markdown)
    console.print("No queue item, backlog task, validation, Git, commit, push, or target repository state was completed automatically.")
    if review.review_status == "reviewed_passed" and review.source_queue_id and review.source_queue_item_id:
        console.print("Next suggested queue completion command after independent review:")
        console.print(
            f"  devo project queue-complete-item --project {project_name} --queue {review.source_queue_id} "
            f"--item {review.source_queue_item_id} --note \"<reviewed result>\"",
            soft_wrap=True,
        )


@worker_codex_app.command("review-attach-evidence")
def attach_codex_worker_review_evidence_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    status: str = typer.Option(..., "--status", help="Evidence status: provided, passed, failed, or partial."),
    summary: str = typer.Option(..., "--summary", help="Validation evidence summary."),
) -> None:
    """Attach manually recorded validation evidence to a worker review artifact."""
    project_name = _resolve_project(project_name)
    try:
        review, json_path, markdown_path = attach_codex_worker_review_evidence(project_name, worker_run_id, status, summary)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--status") from exc
    console.print(f"[green]Codex worker review evidence attached[/green] {project_name}")
    _print_worker_review(review, json_path=json_path, markdown_path=markdown_path)
    console.print("Evidence was recorded manually. Devo did not run validation automatically.")


@worker_codex_app.command("prepare-next")
def prepare_codex_worker_for_queue_next_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Prepare handoff, worker run, and run plan for one queue item without approval or execution."""
    project_name = _resolve_project(project_name)
    try:
        handoff, worker_run, plan, preflight, plan_json, plan_markdown = prepare_codex_worker_for_queue_next(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    console.print(f"[green]Codex queue worker prepared[/green] {project_name}")
    console.print(f"Handoff: {handoff.handoff_id}")
    _print_worker_run(worker_run)
    _print_codex_preflight(preflight)
    _print_codex_run_plan(plan, json_path=plan_json, markdown_path=plan_markdown)
    console.print("Next commands:")
    console.print(f"  devo worker codex run-plan-show --project {project_name} --plan {plan.plan_id}")
    console.print(f"  devo worker codex run-plan-approve --project {project_name} --plan {plan.plan_id} --note \"<review note>\"")
    console.print(f"  devo worker codex execute-preview --project {project_name} --run {worker_run.worker_run_id} --plan {plan.plan_id}")
    console.print(f"  devo worker codex execute --project {project_name} --run {worker_run.worker_run_id} --plan {plan.plan_id} --confirm-execute")
    console.print("Safety: prepare-next does not approve the plan, execute Codex, run validation, commit, push, or complete queue/task state.")


@worker_codex_app.command("queue-status")
def codex_queue_worker_status_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    queue_id: str = typer.Option(..., "--queue", help="Execution queue id."),
) -> None:
    """Show queue worker linkage and next safe command without mutating state."""
    project_name = _resolve_project(project_name)
    try:
        status = get_codex_queue_worker_status(project_name, queue_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--queue") from exc
    _print_codex_queue_worker_status(status)


@worker_codex_app.command("preflight")
def preflight_codex_worker_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    write: bool = typer.Option(False, "--write", help="Create a run-plan artifact if preflight is not blocked."),
) -> None:
    """Run read-only preflight checks for a future supervised Codex run."""
    project_name = _resolve_project(project_name)
    result = run_codex_worker_preflight(project_name, worker_run_id)
    _print_codex_preflight(result)
    if write:
        if result.status == "blocked":
            console.print("[yellow]Run plan not written because preflight is blocked.[/yellow]")
            raise typer.Exit(1)
        plan, preflight, json_path, markdown_path = create_codex_worker_run_plan(project_name, worker_run_id)
        console.print("[green]Codex run plan written from preflight[/green]")
        _print_codex_preflight(preflight)
        _print_codex_run_plan(plan, json_path=json_path, markdown_path=markdown_path)
    if result.status == "blocked":
        raise typer.Exit(1)


@worker_codex_app.command("run-plan")
def create_codex_worker_run_plan_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
) -> None:
    """Create a safe preview run-plan artifact for supervised Codex execution."""
    project_name = _resolve_project(project_name)
    try:
        plan, preflight, json_path, markdown_path = create_codex_worker_run_plan(project_name, worker_run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"[green]Codex run plan saved[/green] {project_name}")
    _print_codex_preflight(preflight)
    _print_codex_run_plan(plan, json_path=json_path, markdown_path=markdown_path)
    console.print("Use execute-preview first; guarded execution still requires approval and --confirm-execute.")


@worker_codex_app.command("run-plan-list")
def list_codex_worker_run_plans_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """List Codex worker run plans for a project."""
    project_name = _resolve_project(project_name)
    plans = list_codex_run_plans(project_name)
    console.print(f"[bold]Codex run plans: {project_name}[/bold]")
    if not plans:
        console.print("[yellow]No Codex run plans found.[/yellow]")
        console.print(f"Suggested next command: devo worker codex run-plan --project {project_name} --run <workerRunId>")
        return
    for plan in plans:
        console.print(
            f"{plan.plan_id} | run={plan.worker_run_id} | {plan.status} | preflight={plan.preflight_status} | approval={plan.approval_status} | {plan.next_action}",
            soft_wrap=True,
        )


@worker_codex_app.command("run-plan-show")
def show_codex_worker_run_plan_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    plan_id: str = typer.Option(..., "--plan", help="Codex run plan id."),
) -> None:
    """Show one Codex worker run-plan artifact without mutating anything."""
    project_name = _resolve_project(project_name)
    plan = load_codex_run_plan(project_name, plan_id)
    if not plan:
        console.print(f"[yellow]Codex run plan not found: {plan_id}[/yellow]")
        return
    json_path, markdown_path = worker_run_plan_artifact_paths(project_name, plan.plan_id)
    _print_codex_run_plan(plan, json_path=json_path, markdown_path=markdown_path)


@worker_codex_app.command("run-plan-approve")
def approve_codex_worker_run_plan_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    plan_id: str = typer.Option(..., "--plan", help="Codex run plan id."),
    note: str = typer.Option("", "--note", help="Planning approval note."),
) -> None:
    """Approve a run plan as planning-only evidence without running Codex."""
    project_name = _resolve_project(project_name)
    try:
        plan, json_path, markdown_path = approve_codex_run_plan(project_name, plan_id, note=note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--plan") from exc
    console.print(f"[green]Codex run plan planning approval recorded[/green] {project_name}")
    _print_codex_run_plan(plan, json_path=json_path, markdown_path=markdown_path)
    console.print("This approval is planning-only. It does not execute Codex or authorize future execution by itself.")


@worker_codex_app.command("execute-preview")
def preview_codex_worker_execution_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    plan_id: str = typer.Option(..., "--plan", help="Approved Codex run plan id."),
) -> None:
    """Preview one supervised Codex execution without running anything."""
    project_name = _resolve_project(project_name)
    try:
        preview = preview_codex_worker_execution(project_name, worker_run_id, plan_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--plan") from exc
    _print_codex_execution_preview(preview)


@worker_codex_app.command("execute")
def execute_codex_worker_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    plan_id: str = typer.Option(..., "--plan", help="Approved Codex run plan id."),
    confirm_execute: bool = typer.Option(False, "--confirm-execute", help="Required explicit confirmation to launch Codex CLI."),
    started_by: str = typer.Option("operator", "--started-by", help="Operator label recorded in the worker run."),
) -> None:
    """Launch Codex once for an approved run plan and capture logs."""
    project_name = _resolve_project(project_name)
    if not confirm_execute:
        console.print("[red]Refusing to execute Codex without --confirm-execute.[/red]")
        console.print(f"Preview first: devo worker codex execute-preview --project {project_name} --run {worker_run_id} --plan {plan_id}")
        raise typer.Exit(1)
    try:
        preview = preview_codex_worker_execution(project_name, worker_run_id, plan_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--plan") from exc
    _print_codex_execution_preview(preview)
    if preview.blocked_reasons:
        console.print("[red]Execution blocked. Resolve blockers before running Codex.[/red]")
        raise typer.Exit(1)
    console.print("[yellow]Launching Codex CLI once for this approved run plan.[/yellow]")
    console.print("[yellow]Devo will capture logs and move the worker run to review/failure state only; it will not validate, commit, push, or complete queue/task state.[/yellow]")
    try:
        result, _worker_run, _log_path, _stderr_path = execute_codex_worker_run(project_name, worker_run_id, plan_id, started_by=started_by)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--plan") from exc
    _print_codex_execution_result(result)
    console.print(f"Suggested next command: devo worker codex report-template --project {project_name} --run {result.worker_run_id}")


@worker_codex_app.command("execute-log")
def show_codex_worker_execution_log_command(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    worker_run_id: str = typer.Option(..., "--run", help="Codex worker run id."),
    tail_chars: int = typer.Option(4000, "--tail-chars", min=200, max=20000, help="Characters to show from the end of stdout/stderr logs."),
) -> None:
    """Show stored supervised execution log paths and a small safe tail."""
    project_name = _resolve_project(project_name)
    worker_run = load_codex_worker_run(project_name, worker_run_id)
    if not worker_run:
        console.print(f"[yellow]Codex worker run not found: {worker_run_id}[/yellow]")
        raise typer.Exit(1)
    log_path = Path(worker_run.execution_log_path) if worker_run.execution_log_path else worker_execution_log_paths(project_name, worker_run.worker_run_id)[0]
    stderr_log_path = Path(worker_run.execution_stderr_log_path) if worker_run.execution_stderr_log_path else worker_execution_log_paths(project_name, worker_run.worker_run_id)[1]
    console.print(f"[bold]Codex execution logs: {worker_run.worker_run_id}[/bold]")
    console.print(f"Status: {worker_run.status}")
    console.print(f"Exit code: {worker_run.execution_exit_code if worker_run.execution_exit_code is not None else 'none'}")
    console.print(f"Log path: {_named_path(log_path)}")
    console.print(f"Stderr log path: {_named_path(stderr_log_path)}")
    for label, path in [("stdout/log", log_path), ("stderr", stderr_log_path)]:
        console.print(f"[bold]{label} tail[/bold]")
        if not path.exists():
            console.print("  - log not found")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        console.print(text[-tail_chars:] if text else "  - empty", soft_wrap=True)
    console.print("Safety: logs are evidence only. Review/import a worker report before queue/task or delivery updates.")


@project_app.command("activity")
def show_project_activity(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Show compact project activity across runs, work packages, validation, reports, and Git."""
    project_name = _resolve_project(project_name, announce=not json_output)
    if json_output:
        _print_json_model(build_project_overview(project_name=project_name, limit=limit))
        return
    try:
        activity = build_project_activity_summary(project_name=project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_project_activity(activity)


@project_app.command("scan")
def scan_project(project_name: str = typer.Argument(..., help="Registered project name to scan.")) -> None:
    """Scan a registered project without reading source contents."""
    try:
        result = scan_registered_project(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="projectName") from exc

    output_file = get_workspace_root() / "projects" / project_name / "scan-result.json"
    console.print(f"[green]Scanned[/green] {result.project_name}")
    console.print(f"Path: {result.project_path}")
    console.print(f"Files scanned: {result.file_tree.scanned_file_count}")
    console.print(f"Directories scanned: {result.file_tree.scanned_directory_count}")
    console.print(f"Ignored files: {result.file_tree.ignored_file_count}")
    console.print(f"Ignored directories: {result.file_tree.ignored_directory_count}")
    console.print(f"Git repo: {result.git.is_git_repo}")
    console.print(f"Stored in: {output_file}")


@project_app.command("context-status")
def show_context_status(project_name: str = typer.Argument(..., help="Registered project name.")) -> None:
    """Show scan, context, and approval status for a project."""
    try:
        status = get_context_status(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="projectName") from exc

    console.print(f"[bold]{status['project_name']}[/bold]")
    console.print(f"  Project path: {status['project_path']}")
    console.print(f"  Scan status: {status['scan_status']}")
    console.print(f"  Context status: {status['context_status']}")
    console.print(f"  Discovery artifact: {status['discovery_artifact_path'] or 'none'}")
    console.print(f"  Review artifact: {status['review_artifact_path'] or 'none'}")
    console.print(f"  Approval status: {status['approval_status'] or 'none'}")



@project_app.command("context-summary")
def show_project_context_summary(
    project_name: str = typer.Argument(None, help="Registered project name."),
    project_option: str | None = typer.Option(None, "--project", help="Registered project name."),
) -> None:
    """Show current known context state for a registered project."""
    name = project_option or project_name
    if not name:
        raise typer.BadParameter("Project name is required as an argument or --project.", param_hint="projectName")
    try:
        summary = get_project_context_summary(name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_context_summary(summary)


@project_app.command("context-refresh")
def refresh_project_context_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Optional source run ID."),
    write_draft: bool = typer.Option(False, "--write-draft", help="Write context update draft artifacts."),
) -> None:
    """Build a deterministic context refresh summary from Devo workspace artifacts."""
    try:
        update, md_path, json_path = refresh_project_context(project_name, run_id=run_id, write_draft=write_draft)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    if write_draft:
        console.print(f"[green]Wrote context update draft[/green] {update.update_id}")
        console.print(f"Markdown: {_named_path(md_path)}")
        console.print(f"JSON: {_named_path(json_path)}")
    else:
        console.print(render_context_update_markdown(update))


@project_app.command("context-apply")
def apply_project_context_update(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    file_path: Path = typer.Option(..., "--file", help="Generated context update JSON file."),
) -> None:
    """Apply a reviewed generated context update into Devo workspace metadata."""
    try:
        update = apply_context_update(project_name, file_path)
    except ValueError as exc:
        console.print(f"[red]Context update apply failed:[/red] {exc}", soft_wrap=True)
        raise typer.Exit(1) from exc
    console.print(f"[green]Applied context update[/green] {update.update_id}")
    console.print(f"Project: {update.project_name}")
    console.print(f"Status: {update.status.value}")
    console.print(f"Applied at: {update.applied_at.isoformat() if update.applied_at else 'none'}")
    console.print(f"JSON: {_named_path(update.json_path)}")
    if update.warnings:
        console.print("Warnings:")
        for warning in update.warnings:
            console.print(f"  - {warning}", soft_wrap=True)


@project_app.command("context-history")
def show_project_context_history(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
) -> None:
    """List generated and applied context updates for a project."""
    try:
        ledger = list_context_updates(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"[bold]Context updates for {ledger.project_name}[/bold]")
    if not ledger.updates:
        console.print("  none")
        return
    for update in ledger.updates:
        summary = update.facts_added[0] if update.facts_added else "none"
        console.print(f"[bold]{update.update_id}[/bold]")
        console.print(f"  Created at: {update.created_at.isoformat()}")
        console.print(f"  Source run: {update.source_run_id or 'none'}")
        console.print(f"  Status: {update.status.value}")
        console.print(f"  Path: {_named_path(update.json_path or update.markdown_path)}")
        console.print(f"  Summary: {summary}", soft_wrap=True)
        console.print(f"  Warnings: {'; '.join(update.warnings) if update.warnings else 'none'}", soft_wrap=True)


def _print_context_summary(summary: dict[str, object]) -> None:
    console.print(f"[bold]{summary['project_name']}[/bold]")
    console.print(f"  Project path: {summary['project_path']}", soft_wrap=True)
    console.print(f"  Context status: {summary['context_status']}")
    console.print("  Approved context paths:")
    for path in summary["approved_context_paths"] or ["none"]:
        console.print(f"    - {path}", soft_wrap=True)
    console.print("  Last scan result:")
    for item in summary["last_scan_result"] or ["none"]:
        console.print(f"    - {item}", soft_wrap=True)
    console.print("  Environment snapshot:")
    for item in summary["environment_snapshot"] or ["none"]:
        console.print(f"    - {item}", soft_wrap=True)
    console.print("  Validation registry:")
    for item in summary["validation_registry"] or ["none"]:
        console.print(f"    - {item}", soft_wrap=True)
    console.print("  Recent runs:")
    for item in summary["recent_runs"] or ["none"]:
        console.print(f"    - {item}", soft_wrap=True)
    console.print(f"  Latest context update: {summary['latest_context_update_file'] or 'none'}")
    console.print("  Warnings:")
    for warning in summary["warnings"] or ["none"]:
        console.print(f"    - {warning}", soft_wrap=True)
    console.print(f"  Suggested next context action: {summary['suggested_next_context_action']}", soft_wrap=True)
@project_app.command("approve-context")
def approve_project_context(project_name: str = typer.Argument(..., help="Registered project name.")) -> None:
    """Approve imported project context after discovery and review."""
    try:
        approval = approve_context(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="projectName") from exc

    console.print(f"[green]Approved context[/green] for {approval.project_name}")
    console.print(f"Approved by: {approval.approved_by}")
    console.print(f"Approved at: {approval.approved_at.isoformat()}")
    for artifact_path in approval.approved_artifact_paths:
        console.print(f"Stored approved artifact: {artifact_path}")


@agent_app.command("list")
def list_agents() -> None:
    """List available prompt-only agents."""
    agents = list_agent_definitions()
    if not agents:
        console.print("[yellow]No agents found.[/yellow]")
        return

    console.print("[bold]Available Agents[/bold]")
    for agent in agents:
        console.print(f"[bold]{agent.name}[/bold]")
        console.print(f"  Purpose: {agent.purpose}", soft_wrap=True)
        console.print(f"  Mode: {agent.mode.value}")
        console.print(f"  Requires approval: {agent.requires_approval}")


@agent_app.command("show")
def show_agent(agent_name: str = typer.Argument(..., help="Agent definition name.")) -> None:
    """Show full details for an agent definition."""
    try:
        agent = load_agent_definition(agent_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="agentName") from exc

    console.print(render_agent_definition(agent))


@agent_app.command("prompt")
def generate_agent_prompt(
    agent_name: str = typer.Argument(..., help="Agent name to generate a prompt for."),
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID for run-level agents."),
    task_id: str | None = typer.Option(None, "--task", help="Task ID for implementation coordination."),
) -> None:
    """Generate a ready-to-paste prompt for a supported agent."""
    try:
        agent = load_agent_definition(agent_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="agentName") from exc

    if agent.name == DISCOVERY_AGENT_NAME:
        generator = generate_project_context_discovery_prompt
    elif agent.name == REVIEWER_AGENT_NAME:
        generator = generate_project_context_reviewer_prompt
    elif agent.name in {
        IDEA_ANALYST_AGENT_NAME,
        REQUIREMENTS_AGENT_NAME,
        PLANNER_AGENT_NAME,
        PLAN_REVIEWER_AGENT_NAME,
        TASK_DECOMPOSER_AGENT_NAME,
        IMPLEMENTATION_COORDINATOR_AGENT_NAME,
        VALIDATOR_AGENT_NAME,
        CODE_REVIEWER_AGENT_NAME,
    close_run,
        FINAL_AUDITOR_AGENT_NAME,
    }:
        if not run_id:
            raise typer.BadParameter(f"{agent.name} prompt generation requires --run.", param_hint="--run")
        try:
            metadata = generate_run_agent_prompt(
                agent_name=agent.name,
                project_name=project_name,
                run_id=run_id,
                task_id=task_id,
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc), param_hint="--run") from exc

        console.print(f"[green]Generated prompt[/green] for {metadata.agent_name}")
        console.print(f"Project: {metadata.project_name}")
        console.print(f"Run: {run_id}")
        console.print(f"Stored in: {metadata.prompt_path}")
        return
    else:
        raise typer.BadParameter(
            (
                "Prompt generation is only supported for "
                f"{DISCOVERY_AGENT_NAME}, {REVIEWER_AGENT_NAME}, "
                f"{IDEA_ANALYST_AGENT_NAME}, {REQUIREMENTS_AGENT_NAME}, "
                f"{PLANNER_AGENT_NAME}, {PLAN_REVIEWER_AGENT_NAME}, "
                f"{TASK_DECOMPOSER_AGENT_NAME}, {IMPLEMENTATION_COORDINATOR_AGENT_NAME}, "
                f"{VALIDATOR_AGENT_NAME}, {CODE_REVIEWER_AGENT_NAME}, and {FINAL_AUDITOR_AGENT_NAME}."
            ),
            param_hint="agentName",
        )

    try:
        metadata = generator(project_name=project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    console.print(f"[green]Generated prompt[/green] for {metadata.agent_name}")
    console.print(f"Project: {metadata.project_name}")
    console.print(f"Stored in: {metadata.prompt_path}")


@agent_app.command("import-output")
def import_output(
    agent_name: str = typer.Argument(..., help="Agent name that produced the output."),
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID for run-level agent output."),
    task_id: str | None = typer.Option(None, "--task", help="Task ID for implementation coordination output."),
    file_path: Path = typer.Option(..., "--file", help="Markdown output file to import."),
    allow_missing_idea_analysis: bool = typer.Option(
        False,
        "--allow-missing-idea-analysis",
        help="Allow RequirementsAgent import without IdeaAnalystAgent output.",
    ),
) -> None:
    """Import manual prompt output for a supported agent."""
    try:
        agent = load_agent_definition(agent_name)
        if agent.name in {
            IDEA_ANALYST_AGENT_NAME,
            REQUIREMENTS_AGENT_NAME,
            PLANNER_AGENT_NAME,
            PLAN_REVIEWER_AGENT_NAME,
            TASK_DECOMPOSER_AGENT_NAME,
            IMPLEMENTATION_COORDINATOR_AGENT_NAME,
            VALIDATOR_AGENT_NAME,
            CODE_REVIEWER_AGENT_NAME,
    close_run,
            FINAL_AUDITOR_AGENT_NAME,
        }:
            if not run_id:
                raise ValueError(f"{agent.name} import requires --run.")
            record = import_run_agent_output(
                agent_name=agent.name,
                project_name=project_name,
                run_id=run_id,
                source_file=file_path,
                task_id=task_id,
                allow_missing_idea_analysis=allow_missing_idea_analysis,
            )
            console.print(f"[green]Imported output[/green] for {record.agent_name}")
            console.print(f"Project: {project_name}")
            console.print(f"Run: {run_id}")
            if task_id:
                console.print(f"Task: {task_id}")
            console.print(f"Status: {record.status_after_import.value}")
            console.print(f"Source: {record.artifact.source_file_path}")
            console.print(f"Stored in: {record.artifact.artifact_path}")
            return

        artifact = import_agent_output(agent_name=agent.name, project_name=project_name, source_file=file_path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="agentName") from exc

    console.print(f"[green]Imported output[/green] for {artifact.agent_name}")
    console.print(f"Project: {project_name}")
    console.print(f"Source: {artifact.source_file_path}")
    console.print(f"Stored in: {artifact.artifact_path}")


@run_app.command("create")
def create_development_run(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    goal: str = typer.Option(..., "--goal", help="Feature, bugfix, refactor, or project goal."),
) -> None:
    """Create a development run for an approved project context."""
    try:
        run_state = create_run(project_name=project_name, goal=goal)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    output_dir = run_path(project_name, run_state.run_id)
    console.print(f"[green]Created run[/green] {run_state.run_id}")
    console.print(f"Project: {run_state.project_name}")
    console.print(f"Status: {run_state.status.value}")
    console.print(f"Goal: {run_state.goal}")
    console.print(f"Stored in: {output_dir}")


@run_app.command("list")
def list_development_runs(project_name: str = typer.Option(..., "--project", help="Registered project name.")) -> None:
    """List development runs for a project."""
    try:
        runs = list_runs(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    if not runs:
        console.print("[yellow]No runs found.[/yellow]")
        return

    for run_state in runs:
        console.print(f"[bold]{run_state.run_id}[/bold]")
        console.print(f"  Status: {run_state.status.value}")
        console.print(f"  Goal: {run_state.goal}")
        console.print(f"  Created at: {run_state.created_at.isoformat()}")


@run_app.command("status")
def show_run_status(
    run_id: str = typer.Argument(..., help="Run ID."),
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
) -> None:
    """Show run status and state summary."""
    try:
        run_state = load_run(project_name, run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="runId") from exc

    console.print(f"[bold]{run_state.run_id}[/bold]")
    console.print(f"  Project: {run_state.project_name}")
    console.print(f"  Project path: {run_state.project_path}")
    console.print(f"  Status: {run_state.status.value}")
    console.print(f"  Goal: {run_state.goal}")
    console.print(f"  Created at: {run_state.created_at.isoformat()}")
    console.print(f"  Closed at: {run_state.closed_at.isoformat() if run_state.closed_at else 'none'}")
    console.print(f"  Run summary: {_named_path(run_state.run_summary_path)}")
    console.print(f"  Closure note: {run_state.closure_note or 'none'}")
    console.print(f"  Context state: {_named_path(run_state.context_snapshot.context_state_path)}")
    console.print(f"  Approval record: {_named_path(run_state.context_snapshot.approval_record_path)}")


@run_app.command("close")
def close_development_run(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    note: str | None = typer.Option(None, "--note", help="Optional run closure note."),
) -> None:
    """Close a run when every task is resolved."""
    try:
        run_state = close_run(project_name=project_name, run_id=run_id, note=note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(f"[green]Closed run[/green] {run_state.run_id}")
    console.print(f"Project: {run_state.project_name}")
    console.print(f"Status: {run_state.status.value}")
    console.print(f"Closed at: {run_state.closed_at.isoformat() if run_state.closed_at else 'none'}")
    console.print(f"Summary: {_named_path(run_state.run_summary_path)}")
    console.print(f"Note: {run_state.closure_note or 'none'}")


@run_app.command("summary")
def show_run_summary(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show run closure summary and task resolution."""
    try:
        summary = get_run_summary(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(f"[bold]{summary['run_id']}[/bold]")
    console.print(f"  Project: {summary['project_name']}")
    console.print(f"  Status: {summary['status']}")
    console.print(f"  Goal: {summary['goal']}")
    console.print(f"  Closed at: {summary['closed_at'] or 'none'}")
    console.print(f"  Closure note: {summary['closure_note'] or 'none'}")
    console.print(f"  Run summary: {_named_path(summary['run_summary_path'])}")
    unresolved = summary["unresolved_task_ids"]
    console.print(f"  Unresolved tasks: {', '.join(unresolved) if unresolved else 'none'}")
    console.print("  Task resolution:")
    for task in summary["tasks"]:
        console.print(
            "    - "
            f"{task['task_id']} {task['task_title']} | "
            f"closure={task['closure_status']} | "
            f"disposition={task['disposition_status']} | "
            f"covered_by={task['covered_by_task_id'] or 'none'} | "
            f"final={task['final_decision']}"
        )


@run_app.command("artifacts")
def show_run_artifacts(
    run_id: str = typer.Argument(..., help="Run ID."),
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
) -> None:
    """Show run artifact and prompt paths."""
    try:
        summary = get_run_artifacts_summary(project_name, run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="runId") from exc

    console.print(f"[bold]{run_id}[/bold]")
    console.print(f"  goal.md: {_named_path(summary['goal_path'])}")
    console.print(f"  run-state.json: {_named_path(summary['run_state_path'])}")
    console.print(f"  idea-analysis: {_named_path(summary['idea_analysis_artifact_path'])}")
    console.print(f"  requirements: {_named_path(summary['requirements_artifact_path'])}")
    console.print(f"  plan: {_named_path(summary['plan_artifact_path'])}")
    console.print(f"  plan-review: {_named_path(summary['plan_review_artifact_path'])}")
    console.print(f"  tasks: {_named_path(summary['tasks_artifact_path'])}")
    console.print(f"  task-ledger.json: {_named_path(summary['task_ledger_path'])}")
    console.print(f"  run-summary.md: {_named_path(summary['run_summary_path'])}")
    implementation_paths = summary["implementation_artifact_paths"]
    if implementation_paths:
        console.print("  implementation:")
        for record in implementation_paths:
            console.print(f"    - {record['task_id']}: {_named_path(record['implementation_brief_path'])}")
            if record["completion_report_path"]:
                console.print(f"      completion: {_named_path(record['completion_report_path'])}")
            if record["validation_report_path"]:
                console.print(f"      validation: {_named_path(record['validation_report_path'])}")
            if record["code_review_path"]:
                console.print(f"      code review: {_named_path(record['code_review_path'])}")
            if record["final_audit_path"]:
                console.print(f"      final audit: {_named_path(record['final_audit_path'])}")
            if record["closure_record_path"]:
                console.print(f"      closure: {_named_path(record['closure_record_path'])}")
    else:
        console.print("  implementation: none")
    prompt_paths = summary["prompt_paths"]
    if prompt_paths:
        console.print("  prompts:")
        for prompt_path in prompt_paths:
            console.print(f"    - {_named_path(prompt_path)}")
    else:
        console.print("  prompts: none")


@app.command("use")
def use_project_or_run(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run ID to select."),
) -> None:
    """Save the active project and optional run selection."""
    try:
        selection = save_current_selection(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    console.print("[green]Current context updated.[/green]")
    console.print(f"Current project: {selection.project_name}")
    console.print(f"Project path: {selection.project_path}")
    console.print(f"Current run: {selection.run_id or 'none'}")
    if selection.run_path:
        console.print(f"Run path: {selection.run_path}")
    console.print(f"Stored in: {get_workspace_root() / 'current.json'}")


@app.command("current")
def show_current_context() -> None:
    """Show saved current project/run context and whether it still exists."""
    selection = load_current_selection()
    if not selection:
        console.print("Current project: none")
        console.print("Current run: none")
        console.print("Next command: devo use --project <project>")
        return
    console.print(f"Current project: {selection.project_name}")
    try:
        load_registered_project(selection.project_name)
        console.print(f"Project exists: yes")
    except ValueError:
        console.print("Project exists: no")
    console.print(f"Project path: {selection.project_path}")
    console.print(f"Current run: {selection.run_id or 'none'}")
    if selection.run_id:
        try:
            load_run(selection.project_name, selection.run_id)
            console.print("Run exists: yes")
        except ValueError:
            console.print("Run exists: no")
    else:
        console.print("Run exists: n/a")
    console.print(f"Stored in: {get_workspace_root() / 'current.json'}")


@implementation_app.command("report")
def report_implementation_completion(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
    file_path: Path = typer.Option(..., "--file", help="Markdown completion report file."),
) -> None:
    """Import an implementation completion report for a selected task."""
    try:
        record = import_implementation_completion_report(
            project_name=project_name,
            run_id=run_id,
            task_id=task_id,
            source_file=file_path,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[green]Imported implementation report[/green] for {record.task_id}")
    console.print(f"Project: {project_name}")
    console.print(f"Run: {run_id}")
    console.print(f"Report: {_named_path(record.completion_report_path)}")
    console.print(f"Validation summary: {record.validation_summary}")
    console.print(f"Commit hash: {record.commit_hash}")


@implementation_app.command("status")
def show_implementation_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Show implementation readiness and completion evidence for a selected task."""
    try:
        status = get_implementation_status(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[bold]{status['task_id']}[/bold]")
    console.print(f"  Project: {status['project_name']}")
    console.print(f"  Run: {status['run_id']}")
    console.print(f"  Run status: {status['run_status']}")
    console.print(f"  Implementation brief: {_named_path(status['implementation_brief_path'])}")
    console.print(f"  Completion report: {_named_path(status['completion_report_path'])}")
    console.print(f"  Reported at: {status['reported_at'] or 'none'}")
    console.print(f"  Validation summary: {status['validation_summary']}")
    console.print(f"  Commit hash: {status['commit_hash']}")



def _print_validation_command(command: object) -> None:
    console.print(f"[bold]{command.id}[/bold]")
    console.print(f"  Name: {command.name}")
    console.print(f"  Command: {command.command}", soft_wrap=True)
    console.print(f"  Working directory: {command.working_dir or 'none'}", soft_wrap=True)
    console.print(f"  Category: {command.category.value}")
    console.print(f"  Risk level: {command.risk_level.value}")
    console.print(f"  Approval required: {command.approval_required}")
    console.print(f"  Enabled: {command.enabled}")
    console.print(f"  Source: {command.source}")
    console.print(f"  Notes: {'; '.join(command.notes) if command.notes else 'none'}", soft_wrap=True)
    console.print(f"  Created at: {command.created_at.isoformat()}")
    console.print(f"  Updated at: {command.updated_at.isoformat()}")


def _print_validation_check(result: object) -> None:
    console.print(f"Project: {result.project_name}")
    console.print(f"Command ID: {result.command_id}")
    console.print(f"Allowed: {result.allowed}")
    console.print(f"Approval required: {result.approval_required}")
    console.print(f"Blocked: {result.blocked}")
    console.print(f"Risk level: {result.risk_level.value}")
    console.print("Reasons:")
    for reason in result.reasons or ["none"]:
        console.print(f"  - {reason}")
    console.print(f"Suggested approval request command: {result.suggested_approval_request_command or 'none'}")


@validation_app.command("list")
def list_project_validation_commands(project_name: str = typer.Option(..., "--project", help="Registered project name.")) -> None:
    """List registered validation commands for a project without executing them."""
    try:
        commands = list_validation_commands(project_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    if not commands:
        console.print("[yellow]No validation commands registered.[/yellow]")
        console.print(f"Registry: {registry_path(project_name)}")
        return
    console.print(f"[bold]Validation commands for {project_name}[/bold]")
    for command in commands:
        _print_validation_command(command)


@validation_app.command("add")
def add_project_validation_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str = typer.Option(..., "--id", help="Validation command id."),
    name: str = typer.Option(..., "--name", help="Display name."),
    command: str = typer.Option(..., "--command", help="Command text to record, not execute."),
    category: str = typer.Option(..., "--category", help="Category: restore/build/test/lint/compile/run/script/backup/other."),
    working_dir: Path | None = typer.Option(None, "--working-dir", help="Working directory for future execution."),
    risk: str | None = typer.Option(None, "--risk", help="Risk level: low/medium/high/critical."),
    approval_required: bool | None = typer.Option(None, "--approval-required/--no-approval-required", help="Whether future execution requires approval."),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Whether the command is enabled for future selection."),
    source: str = typer.Option("manual", "--source", help="Metadata source."),
    note: str | None = typer.Option(None, "--note", help="Optional note."),
    replace: bool = typer.Option(False, "--replace", help="Replace an existing command with the same id."),
) -> None:
    """Add a validation command to the registry without executing it."""
    try:
        validation_command = add_validation_command(
            project_name=project_name,
            command_id=command_id,
            name=name,
            command=command,
            category=category,
            working_dir=working_dir,
            risk=risk,
            approval_required=approval_required,
            enabled=enabled,
            source=source,
            note=note,
            replace=replace,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--id") from exc

    console.print(f"[green]Registered validation command[/green] {validation_command.id}")
    console.print(f"Registry: {registry_path(project_name)}")
    _print_validation_command(validation_command)


@validation_app.command("show")
def show_project_validation_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str = typer.Option(..., "--id", help="Validation command id."),
) -> None:
    """Show one validation command with full metadata."""
    try:
        command = get_validation_command(project_name, command_id)
        result = check_validation_command(project_name, command_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--id") from exc

    _print_validation_command(command)
    console.print("Policy classification:")
    _print_validation_check(result)


@validation_app.command("check")
def check_project_validation_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str = typer.Option(..., "--id", help="Validation command id."),
) -> None:
    """Run Devo policy classification on validation command metadata without executing it."""
    try:
        result = check_validation_command(project_name, command_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--id") from exc

    _print_validation_check(result)


@validation_app.command("suggest")
def suggest_project_validation_commands(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    write: bool = typer.Option(False, "--write", help="Write suggestions to the registry without executing them."),
) -> None:
    """Suggest likely validation commands from project metadata without executing them."""
    try:
        commands = suggest_validation_commands(project_name, write=write)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc

    if not commands:
        console.print("[yellow]No validation command suggestions found.[/yellow]")
        return
    console.print(f"[bold]Suggested validation commands for {project_name}[/bold]")
    console.print(f"Write mode: {write}")
    for command in commands:
        _print_validation_command(command)
    if write:
        console.print(f"[green]Wrote suggestions[/green] to {registry_path(project_name)}")
    else:
        console.print("No registry changes made. Re-run with --write to save suggestions.")


def _print_validation_run_result(result: object) -> None:
    record = result.record
    status_label = record.status.value.upper()
    console.print(f"[bold]{status_label}[/bold] validation run {record.validation_run_id}")
    console.print(f"Project: {record.project_name}")
    console.print(f"Run: {record.run_id or 'none'}")
    console.print(f"Task: {record.task_id or 'none'}")
    console.print(f"Command ID: {record.command_id}")
    console.print(f"Command: {record.command}", soft_wrap=True)
    console.print(f"Working directory: {record.working_dir}", soft_wrap=True)
    console.print(f"Risk level: {record.risk_level.value}")
    console.print(f"Approval required: {record.approval_required}")
    console.print(f"Approval ID: {record.approval_id or 'none'}")
    console.print(f"Status: {record.status.value}")
    console.print(f"Exit code: {record.exit_code if record.exit_code is not None else 'none'}")
    console.print(f"Duration seconds: {record.duration_seconds}")
    console.print(f"Blocked reason: {record.blocked_reason or 'none'}", soft_wrap=True)
    console.print(f"Report: {record.report_path or 'none'}")
    console.print("Policy reasons:")
    for reason in record.policy_reasons or ["none"]:
        console.print(f"  - {reason}", soft_wrap=True)
    if result.stdout_text:
        console.print("Stdout excerpt:")
        console.print(terminal_excerpt(result.stdout_text), soft_wrap=True)
    if result.stderr_text:
        console.print("Stderr excerpt:")
        console.print(terminal_excerpt(result.stderr_text), soft_wrap=True)


@validation_app.command("run")
def run_project_validation_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str = typer.Option(..., "--id", help="Registered validation command id."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run id for linked artifacts and approvals."),
    task_id: str | None = typer.Option(None, "--task", help="Optional task id for linked approvals."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not execute; show what would happen."),
    timeout_seconds: int = typer.Option(300, "--timeout-seconds", help="Maximum execution time in seconds."),
    allow_disabled: bool = typer.Option(False, "--allow-disabled", help="Allow disabled commands if policy and approval also allow."),
    require_approval: bool | None = typer.Option(None, "--require-approval/--no-require-approval", help="Override approval requirement for this run."),
    write_report: bool = typer.Option(True, "--write-report/--no-write-report", help="Write validation run artifacts."),
) -> None:
    """Safely run one registered validation command with policy and approval gates."""
    try:
        result = run_validation_command(
            project_name=project_name,
            command_id=command_id,
            run_id=run_id,
            task_id=task_id,
            dry_run=dry_run,
            timeout_seconds=timeout_seconds,
            allow_disabled=allow_disabled,
            require_approval=require_approval,
            write_report=write_report,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--id") from exc
    _print_validation_run_result(result)


@validation_app.command("dry-run")
def dry_run_project_validation_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str = typer.Option(..., "--id", help="Registered validation command id."),
    run_id: str | None = typer.Option(None, "--run", help="Optional run id for linked artifacts and approvals."),
    task_id: str | None = typer.Option(None, "--task", help="Optional task id for linked approvals."),
    timeout_seconds: int = typer.Option(300, "--timeout-seconds", help="Maximum execution time in seconds."),
    allow_disabled: bool = typer.Option(False, "--allow-disabled", help="Show disabled command details without execution."),
    require_approval: bool | None = typer.Option(None, "--require-approval/--no-require-approval", help="Override approval requirement for this dry run."),
    write_report: bool = typer.Option(True, "--write-report/--no-write-report", help="Write dry-run artifacts."),
) -> None:
    """Alias for validation run --dry-run."""
    try:
        result = run_validation_command(
            project_name=project_name,
            command_id=command_id,
            run_id=run_id,
            task_id=task_id,
            dry_run=True,
            timeout_seconds=timeout_seconds,
            allow_disabled=allow_disabled,
            require_approval=require_approval,
            write_report=write_report,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--id") from exc
    _print_validation_run_result(result)


@validation_app.command("history")
def show_validation_history(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    command_id: str | None = typer.Option(None, "--id", help="Optional validation command id filter."),
) -> None:
    """Show previous validation command run records."""
    try:
        records = list_validation_history(project_name=project_name, command_id=command_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    if not records:
        console.print("[yellow]No validation runs found.[/yellow]")
        return
    console.print(f"[bold]Validation history for {project_name}[/bold]")
    for record in records:
        console.print(f"[bold]{record.validation_run_id}[/bold]")
        console.print(f"  Command ID: {record.command_id}")
        console.print(f"  Status: {record.status.value}")
        console.print(f"  Exit code: {record.exit_code if record.exit_code is not None else 'none'}")
        console.print(f"  Started at: {record.started_at.isoformat()}")
        console.print(f"  Finished at: {record.finished_at.isoformat() if record.finished_at else 'none'}")
        console.print(f"  Duration seconds: {record.duration_seconds}")
        console.print(f"  Report: {record.report_path or 'none'}")
        console.print(f"  Run: {record.run_id or 'none'}")
        console.print(f"  Task: {record.task_id or 'none'}")
@validation_app.command("status")
def show_validation_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Show validation review evidence for a selected task."""
    try:
        status = get_validation_status(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[bold]{status['task_id']}[/bold]")
    console.print(f"  Project: {status['project_name']}")
    console.print(f"  Run: {status['run_id']}")
    console.print(f"  Run status: {status['run_status']}")
    console.print(f"  Implementation brief: {_named_path(status['implementation_brief_path'])}")
    console.print(f"  Completion report: {_named_path(status['completion_report_path'])}")
    console.print(f"  Validation report: {_named_path(status['validation_report_path'])}")
    console.print(f"  Validated at: {status['validated_at'] or 'none'}")
    console.print(f"  Validation decision: {status['validation_decision']}")


@review_app.command("status")
def show_review_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Show code review evidence for a selected task."""
    try:
        status = get_review_status(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[bold]{status['task_id']}[/bold]")
    console.print(f"  Project: {status['project_name']}")
    console.print(f"  Run: {status['run_id']}")
    console.print(f"  Run status: {status['run_status']}")
    console.print(f"  Implementation brief: {_named_path(status['implementation_brief_path'])}")
    console.print(f"  Completion report: {_named_path(status['completion_report_path'])}")
    console.print(f"  Validation report: {_named_path(status['validation_report_path'])}")
    console.print(f"  Code review: {_named_path(status['code_review_path'])}")
    console.print(f"  Reviewed at: {status['reviewed_at'] or 'none'}")
    console.print(f"  Review decision: {status['review_decision']}")


@audit_app.command("status")
def show_audit_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Show final audit evidence for a selected task."""
    try:
        status = get_audit_status(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[bold]{status['task_id']}[/bold]")
    console.print(f"  Project: {status['project_name']}")
    console.print(f"  Run: {status['run_id']}")
    console.print(f"  Run status: {status['run_status']}")
    console.print(f"  Implementation brief: {_named_path(status['implementation_brief_path'])}")
    console.print(f"  Completion report: {_named_path(status['completion_report_path'])}")
    console.print(f"  Validation report: {_named_path(status['validation_report_path'])}")
    console.print(f"  Code review: {_named_path(status['code_review_path'])}")
    console.print(f"  Final audit: {_named_path(status['final_audit_path'])}")
    console.print(f"  Audited at: {status['audited_at'] or 'none'}")
    console.print(f"  Final decision: {status['final_decision']}")


@task_app.command("mark")
def mark_run_task(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
    status: str = typer.Option(..., "--status", help="Disposition status."),
    note: str | None = typer.Option(None, "--note", help="Disposition note."),
    covered_by_task_id: str | None = typer.Option(None, "--covered-by", help="Task ID that covers this task."),
) -> None:
    """Mark task disposition in the run ledger."""
    try:
        entry = mark_task_disposition(
            project_name=project_name,
            run_id=run_id,
            task_id=task_id,
            status=status,
            note=note,
            covered_by_task_id=covered_by_task_id,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[green]Marked task[/green] {entry.task_id}")
    console.print(f"Project: {project_name}")
    console.print(f"Run: {run_id}")
    console.print(f"Disposition status: {entry.disposition_status.value}")
    console.print(f"Covered by: {entry.covered_by_task_id or 'none'}")
    console.print(f"Note: {entry.disposition_note or 'none'}")
    console.print(f"Updated at: {entry.updated_at.isoformat()}")


@task_app.command("close")
def close_run_task(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
    note: str | None = typer.Option(None, "--note", help="Optional closure note."),
) -> None:
    """Close a final-audited task."""
    try:
        record = close_task(project_name=project_name, run_id=run_id, task_id=task_id, note=note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[green]Closed task[/green] {record.task_id}")
    console.print(f"Project: {project_name}")
    console.print(f"Run: {run_id}")
    console.print(f"Closure status: {record.closure_status}")
    console.print(f"Final decision: {record.final_decision}")
    if record.closure_note:
        console.print(f"Note: {record.closure_note}")
    console.print(f"Stored in: {_named_path(record.closure_record_path)}")


@task_app.command("status")
def show_task_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Show task closure status."""
    try:
        status = get_task_status(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    console.print(f"[bold]{status['task_id']}[/bold]")
    console.print(f"  Project: {status['project_name']}")
    console.print(f"  Run: {status['run_id']}")
    console.print(f"  Run status: {status['run_status']}")
    console.print(f"  Closure status: {status['closure_status']}")
    console.print(f"  Disposition status: {status['disposition_status']}")
    console.print(f"  Covered by: {status['covered_by_task_id'] or 'none'}")
    console.print(f"  Disposition note: {status['disposition_note'] or 'none'}")
    console.print(f"  Disposition updated at: {status['disposition_updated_at'] or 'none'}")
    console.print(f"  Closure record: {_named_path(status['closure_record_path'])}")
    console.print(f"  Closed at: {status['closed_at'] or 'none'}")
    console.print(f"  Closure note: {status['closure_note'] or 'none'}")
    console.print(f"  Final decision: {status['final_decision']}")
    console.print(f"  Final audit: {_named_path(status['final_audit_path'])}")


@task_app.command("list")
def list_tasks_for_run(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """List tasks in a run with closure status."""
    try:
        tasks = list_run_tasks(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    for task in tasks:
        console.print(f"[bold]{task['task_id']}[/bold] {task['task_title']}")
        console.print(f"  Closure status: {task['closure_status']}")
        console.print(f"  Disposition status: {task['disposition_status']}")
        console.print(f"  Covered by: {task['covered_by_task_id'] or 'none'}")
        console.print(f"  Final decision: {task['final_decision']}")
        if task["disposition_note"]:
            console.print(f"  Disposition note: {task['disposition_note']}")
        if task["closure_record_path"]:
            console.print(f"  Closure record: {_named_path(task['closure_record_path'])}")



@task_app.command("next")
def show_next_task(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    strategy: str = typer.Option(DEFAULT_STRATEGY, "--strategy", help="Selection strategy."),
    include_skipped: bool = typer.Option(False, "--include-skipped", help="Show skipped tasks and reasons."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
) -> None:
    """Select the next actionable task deterministically."""
    try:
        selection = select_next_task(project_name=project_name, run_id=run_id, strategy=strategy)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_task_selection(selection, include_skipped=include_skipped, output_format=output_format)


@task_app.command("candidates")
def show_task_candidates(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    strategy: str = typer.Option(DEFAULT_STRATEGY, "--strategy", help="Selection strategy."),
    include_skipped: bool = typer.Option(True, "--include-skipped/--hide-skipped", help="Show skipped tasks and reasons."),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json."),
) -> None:
    """List task-selection candidates with skip reasons."""
    try:
        selection = list_task_candidates(project_name=project_name, run_id=run_id, strategy=strategy)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_task_selection(selection, include_skipped=include_skipped, output_format=output_format, candidates_only=True)


@work_app.command("lanes")
def list_work_package_lanes() -> None:
    """List built-in work package lanes."""
    for lane in list_lanes():
        _print_work_lane(lane)


@work_app.command("lane-show")
def show_work_package_lane(
    lane_id: str = typer.Option(..., "--lane", help="Work lane ID."),
) -> None:
    """Show one built-in work package lane."""
    try:
        lane = get_lane(lane_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--lane") from exc

    _print_work_lane(lane)


@work_app.command("list")
def list_work_packages(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """List recent work packages and project runs."""
    project_name = _resolve_project(project_name)
    try:
        summaries = list_work_package_summaries(project_name=project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_work_summary_list(summaries, f"Recent work for {project_name}")


@work_app.command("history")
def show_work_history(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Show delivery-focused work package history."""
    project_name = _resolve_project(project_name)
    try:
        summaries = list_work_package_summaries(project_name=project_name, limit=limit, delivered_first=True)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_work_summary_list(summaries, f"Work history for {project_name}", include_delivery=True)


@work_app.command("new")
def new_work(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    goal: str = typer.Option(..., "--goal", help="Work package goal."),
    lane_id: str | None = typer.Option(None, "--lane", help="Work lane ID. Uses project default lane when omitted."),
    no_template: bool = typer.Option(False, "--no-template", help="Skip scope template generation."),
    force_template: bool = typer.Option(False, "--template", help="Generate a scope template even when project settings disable automatic templates."),
    print_resume: bool = typer.Option(False, "--print-resume", help="Print the full resume guidance after creation."),
) -> None:
    """Create a run, draft work package, optional scope template, and resume guidance."""
    if no_template and force_template:
        raise typer.BadParameter("Use either --template or --no-template, not both.", param_hint="--template")
    project_name = _resolve_project(project_name)
    try:
        settings = load_project_settings(project_name)
        selected_lane = lane_id or settings.default_lane
        if not selected_lane:
            raise ValueError("No lane provided and no project default lane configured.")
        package = start_work_package(project_name=project_name, lane_id=selected_lane, goal=goal)
    except ValueError as exc:
        hint = "--lane" if "lane" in str(exc).lower() else "--project"
        console.print(str(exc), soft_wrap=True)
        raise typer.BadParameter(str(exc), param_hint=hint) from exc

    template_path = None
    template_skipped_reason = "skipped"
    should_generate_template = not no_template and (force_template or settings.allow_auto_scope_template)
    if should_generate_template:
        template = generate_work_scope_template(project_name=project_name, run_id=package.run_id)
        template_path = template.template_path
    elif not no_template and not settings.allow_auto_scope_template:
        template_skipped_reason = "skipped by project settings"
    resume = build_work_package_resume(project_name=project_name, run_id=package.run_id)
    next_step = get_work_package_next_step(package)

    console.print("[green]Created work package.[/green]")
    console.print(f"Run: {package.run_id}")
    console.print(f"Lane: {package.lane}")
    console.print(f"Scope template: {_named_path(template_path) if template_path else template_skipped_reason}")
    console.print(f"Next action: {next_step.next_action}")
    console.print(f"Suggested command: devo work resume --project {project_name} --run {package.run_id}")
    if print_resume:
        console.print("")
        console.print(resume.resume_text)


@work_app.command("start")
def start_work(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    lane_id: str = typer.Option(..., "--lane", help="Work lane ID."),
    goal: str = typer.Option(..., "--goal", help="Work package goal."),
) -> None:
    """Create a run and draft work package."""
    try:
        package = start_work_package(project_name=project_name, lane_id=lane_id, goal=goal)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--lane") from exc

    _print_work_package(package)
    console.print(
        "Next command: "
        f"devo work scope-template --project {project_name} --run {package.run_id}"
    )


@work_app.command("scope-template")
def write_work_scope_template(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
) -> None:
    """Write a fill-in scope markdown template for a draft work package."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        result = generate_work_scope_template(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(f"Scope template: {_named_path(result.template_path)}")
    console.print(
        "Next command: "
        f"devo work import-scope --project {project_name} --run {run_id} --file {result.template_path}"
    )


@work_app.command("scope-example")
def show_work_scope_example(
    lane_id: str = typer.Option(..., "--lane", help="Work lane ID."),
) -> None:
    """Print an example filled work-package scope for a lane."""
    try:
        example = render_work_scope_example(lane_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--lane") from exc

    console.print(example)


@work_app.command("import-scope")
def import_scope(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    scope_file: Path = typer.Option(..., "--file", exists=True, file_okay=True, dir_okay=False, readable=True, help="Scope markdown file."),
) -> None:
    """Import a reviewed markdown scope into a work package."""
    try:
        result = import_work_scope(project_name=project_name, run_id=run_id, scope_file=scope_file)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--file") from exc

    console.print("Imported scope into work package.")
    _print_work_package(result.package)
    console.print(
        "Next command: "
        f"devo work request-approval-bundle --project {project_name} --run {run_id} --task T001"
    )


@work_app.command("status")
def show_work_status(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Show work package status and artifact paths."""
    project_name, run_id = _resolve_project_run(project_name, run_id, announce=not json_output)
    if json_output:
        _print_json_model(build_work_package_overview(project_name=project_name, run_id=run_id))
        return
    try:
        package = load_work_package(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_work_package(package)


@work_app.command("next")
def show_work_next(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
) -> None:
    """Show the next work-package action without mutating project files."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        package = load_work_package(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_work_next(package)


@work_app.command("resume")
def show_work_resume(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
) -> None:
    """Show a compact operator plan for resuming a work package."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        resume = build_work_package_resume(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(resume.resume_text)


@work_app.command("prompt")
def write_work_prompt(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
    phase: str = typer.Option(..., "--phase", help="Prompt phase: scope, implement, validate, deliver, or complete."),
) -> None:
    """Write a phase-specific Codex operator prompt for a work package."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        result = generate_work_package_phase_prompt(project_name=project_name, run_id=run_id, phase=phase)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--phase") from exc

    console.print(f"Phase: {result.phase}")
    console.print(f"Prompt: {_named_path(result.prompt_path)}")


@work_app.command("complete")
def complete_work(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
    commit_hash: str = typer.Option(..., "--commit", help="Delivered Git commit hash."),
    message: str = typer.Option(..., "--message", help="Short delivery summary."),
) -> None:
    """Mark a work package delivered after validation, commit, and push."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        package = complete_work_package(
            project_name=project_name,
            run_id=run_id,
            commit_hash=commit_hash,
            delivery_summary=message,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print("[green]Completed work package.[/green]")
    _print_work_package(package)


@work_app.command("request-approval-bundle")
def request_work_approval_bundle(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Request the source-edit and validation approvals for a work package."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        bundle = create_approval_bundle(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    _print_approval_bundle(bundle)
    if bundle.status.value == "pending":
        console.print(
            "Next command: "
            f"devo approval bundle-approve --project {project_name} --run {run_id} --bundle {bundle.bundle_id} --by <name>"
        )
    else:
        console.print("Next command: none; at least one child approval is blocked or rejected.")


@visual_app.command("work-package")
def write_work_package_visual(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    run_id: str | None = typer.Option(None, "--run", help="Run ID."),
) -> None:
    """Write a Mermaid work-package lifecycle visual artifact."""
    project_name, run_id = _resolve_project_run(project_name, run_id)
    try:
        result = generate_work_package_visual(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"Visual report: {_named_path(result.path)}")


@visual_app.command("project-activity")
def write_project_activity_visual(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Write a compact Mermaid project activity visual artifact."""
    project_name = _resolve_project(project_name)
    try:
        result = generate_project_activity_visual(project_name=project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    console.print(f"Visual report: {_named_path(result.path)}")


@approval_app.command("request")
def request_approval(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
    action_type: str = typer.Option(..., "--action", help="Action type to approve."),
    reason: str | None = typer.Option(None, "--reason", help="Reason for requesting approval."),
) -> None:
    """Create a Devo approval request for a task/action scope."""
    try:
        record = create_approval_request(project_name=project_name, run_id=run_id, task_id=task_id, action_type=action_type, reason=reason)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    _print_approval(record)
    if record.status.value == "pending":
        console.print(
            "Next command: "
            f"devo approval approve --project {project_name} --run {run_id} --approval {record.approval_id} --by <name>"
        )
    else:
        console.print("Next command: none; this request is blocked by policy.")


@approval_app.command("approve")
def approve_requested_approval(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    approval_id: str = typer.Option(..., "--approval", help="Approval request ID."),
    approved_by: str = typer.Option(..., "--by", help="Approver name."),
    note: str | None = typer.Option(None, "--note", help="Optional approval note."),
) -> None:
    """Approve a pending Devo approval request without executing anything."""
    try:
        record = approve_approval(project_name=project_name, run_id=run_id, approval_id=approval_id, approved_by=approved_by, note=note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--approval") from exc

    _print_approval(record)


@approval_app.command("reject")
def reject_requested_approval(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    approval_id: str = typer.Option(..., "--approval", help="Approval request ID."),
    rejected_by: str = typer.Option(..., "--by", help="Rejector name."),
    note: str | None = typer.Option(None, "--note", help="Optional rejection note."),
) -> None:
    """Reject a pending Devo approval request without executing anything."""
    try:
        record = reject_approval(project_name=project_name, run_id=run_id, approval_id=approval_id, rejected_by=rejected_by, note=note)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--approval") from exc

    _print_approval(record)


@approval_app.command("status")
def show_approval_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    approval_id: str | None = typer.Option(None, "--approval", help="Approval request ID."),
) -> None:
    """Show one approval request or all approvals for a run."""
    try:
        records = get_approval_status(project_name=project_name, run_id=run_id, approval_id=approval_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--approval") from exc

    if approval_id and records:
        _print_approval(records[0])
    else:
        _print_approval_list(records)


@approval_app.command("list")
def list_approvals(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """List approvals for a run."""
    try:
        records = get_approval_status(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_approval_list(records)


@approval_app.command("bundle-status")
def show_approval_bundle_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    bundle_id: str = typer.Option(..., "--bundle", help="Approval bundle ID."),
) -> None:
    """Show a work package approval bundle and child approval IDs."""
    try:
        bundle = get_approval_bundle(project_name=project_name, run_id=run_id, bundle_id=bundle_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--bundle") from exc

    _print_approval_bundle(bundle)


@approval_app.command("bundle-approve")
def approve_requested_approval_bundle(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    bundle_id: str = typer.Option(..., "--bundle", help="Approval bundle ID."),
    approved_by: str = typer.Option(..., "--by", help="Approver name."),
    note: str | None = typer.Option(None, "--note", help="Optional approval note."),
) -> None:
    """Approve every pending child approval in a work package bundle."""
    try:
        bundle = approve_approval_bundle(
            project_name=project_name,
            run_id=run_id,
            bundle_id=bundle_id,
            approved_by=approved_by,
            note=note,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--bundle") from exc

    _print_approval_bundle(bundle)
@policy_app.command("classify")
def classify_policy_task(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Classify a run task with deterministic risk rules."""
    try:
        classification = classify_task(project_name=project_name, run_id=run_id, task_id=task_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--task") from exc

    _print_policy_classification(classification)


@policy_app.command("check")
def check_policy_task(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
    action_type: str = typer.Option("unknown", "--action", help="Action type to check."),
) -> None:
    """Check whether a proposed task/action can proceed under policy."""
    try:
        result = check_policy(project_name=project_name, run_id=run_id, task_id=task_id, action_type=action_type)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--action") from exc

    _print_policy_check(result)


@policy_app.command("status")
def show_policy_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show policy risk status for all tasks in a run."""
    try:
        status = get_policy_status(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_policy_status(status)
@backup_app.command("create")
def create_workspace_backup(
    dest: Path = typer.Option(..., "--dest", help="Backup root directory."),
    label: str | None = typer.Option(None, "--label", help="Optional backup label."),
    protect: bool = typer.Option(False, "--protect", help="Mark backup as protected from cleanup."),
) -> None:
    """Create a timestamped backup of DevOrchestrator workspace state."""
    try:
        manifest = create_backup(dest=dest, label=label, protect=protect)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    console.print(f"[green]Created backup[/green] {manifest.backup_path}")
    console.print(f"Manifest: {manifest.backup_path / 'backup-manifest.json'}")
    console.print(f"Files: {manifest.file_count}")
    console.print(f"Total bytes: {manifest.total_bytes}")
    console.print(f"Protected: {manifest.protected}")
    if manifest.warnings:
        console.print("Warnings:")
        for warning in manifest.warnings:
            console.print(f"  - {warning}")


@backup_app.command("verify")
def verify_workspace_backup(path: Path = typer.Option(..., "--path", help="Backup folder to verify.")) -> None:
    """Verify a workspace backup manifest, file set, byte count, and hashes."""
    try:
        manifest = verify_backup(path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--path") from exc

    console.print(f"[green]Verified backup[/green] {manifest.backup_path}")
    console.print(f"Manifest: {manifest.backup_path / 'backup-manifest.json'}")
    console.print(f"Files: {manifest.file_count}")
    console.print(f"Total bytes: {manifest.total_bytes}")


@backup_app.command("restore")
def restore_workspace_backup(
    backup: Path = typer.Option(..., "--backup", help="Backup folder to restore."),
    dest: Path = typer.Option(..., "--dest", help="Empty destination workspace folder."),
) -> None:
    """Restore a verified backup into an empty workspace destination."""
    try:
        manifest = restore_backup(backup=backup, dest=dest)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    console.print(f"[green]Restored backup[/green] {manifest.backup_path}")
    console.print(f"Destination: {dest.expanduser().resolve()}")
    console.print(f"Files: {manifest.file_count}")
    console.print(f"Total bytes: {manifest.total_bytes}")


@backup_app.command("list")
def list_workspace_backups(dest: Path = typer.Option(..., "--dest", help="Backup root directory.")) -> None:
    """List DevOrchestrator workspace backups under a backup root."""
    try:
        inventory = list_backup_inventory(dest)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    _print_backup_inventory(inventory, latest=0)


@backup_app.command("status")
def show_workspace_backup_status(
    dest: Path = typer.Option(..., "--dest", help="Backup root directory."),
    latest: int = typer.Option(5, "--latest", help="Number of latest complete/incomplete folders to show."),
) -> None:
    """Summarize backup health without creating, restoring, deleting, or scheduling anything."""
    try:
        inventory = list_backup_inventory(dest)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    _print_backup_inventory(inventory, latest=latest)


def _print_backup_inventory(inventory: object, latest: int = 0) -> None:
    complete_backups = list(getattr(inventory, "complete_backups"))
    normal_backups = list(getattr(inventory, "normal_backups"))
    protected_backups = list(getattr(inventory, "protected_backups"))
    incomplete_backups = list(getattr(inventory, "incomplete_backups"))
    invalid_backup_folders = list(getattr(inventory, "invalid_backup_folders"))

    if not complete_backups and not incomplete_backups and not invalid_backup_folders:
        console.print("[yellow]No backups found.[/yellow]")
        return

    console.print(f"Backup root: {getattr(inventory, 'backup_root')}")
    console.print(f"Complete backups: {len(complete_backups)}")
    console.print(f"Normal backups: {len(normal_backups)}")
    console.print(f"Protected backups: {len(protected_backups)}")
    console.print(f"Incomplete backups: {len(incomplete_backups)}")
    if incomplete_backups:
        console.print(
            "[yellow]Incomplete backups usually mean the backup was interrupted or the PowerShell process was closed before completion.[/yellow]"
        )

    complete_to_print = sorted(complete_backups, key=lambda item: item.created_at, reverse=True)
    incomplete_to_print = sorted(incomplete_backups, key=lambda item: item.last_modified_at, reverse=True)
    if latest > 0:
        complete_to_print = complete_to_print[:latest]
        incomplete_to_print = incomplete_to_print[:latest]

    if complete_to_print:
        console.print("Complete backup folders:")
    for manifest in complete_to_print:
        console.print(f"[bold]{manifest.backup_path.name}[/bold]")
        console.print(f"  Path: {manifest.backup_path}")
        console.print(f"  Created at: {manifest.created_at.isoformat()}")
        console.print(f"  Label: {manifest.label or 'none'}")
        console.print(f"  Protected: {manifest.protected}")
        console.print(f"  Files: {manifest.file_count}")
        console.print(f"  Total bytes: {manifest.total_bytes}")
        console.print(f"  Git: {manifest.git_branch} {manifest.git_commit_hash}")
    if incomplete_to_print:
        console.print("Incomplete backup folders:")
    for incomplete in incomplete_to_print:
        console.print(f"[bold yellow]{incomplete.backup_path.name}[/bold yellow]")
        console.print(f"  Path: {incomplete.backup_path}")
        console.print(f"  Last modified: {incomplete.last_modified_at.isoformat()}")
        console.print(f"  Stale: {incomplete.stale}")
        console.print(f"  Likely interrupted: {incomplete.likely_interrupted}")
        console.print(f"  Reason: {incomplete.reason}")
        if incomplete.marker_text:
            console.print(f"  Marker: {incomplete.marker_text}")
    if invalid_backup_folders:
        console.print("Invalid backup folders:")
        for item in invalid_backup_folders:
            console.print(f"  - {item}")


@backup_app.command("cleanup")
def cleanup_workspace_backups(
    dest: Path = typer.Option(..., "--dest", help="Backup root directory."),
    keep: int = typer.Option(3, "--keep", help="Number of latest unprotected backups to retain."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Report cleanup actions without deleting backups."),
) -> None:
    """Delete old unprotected backups after successful create and verify."""
    try:
        result = cleanup_backups(dest=dest, keep=keep, dry_run=dry_run)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    action = "Would delete" if dry_run else "Deleted"
    console.print(f"[green]Backup cleanup complete[/green] {result.backup_root}")
    console.print(f"Keep latest unprotected backups: {result.keep}")
    console.print(f"Dry run: {result.dry_run}")
    if result.deleted_backups:
        console.print(f"{action} backups:")
        for path in result.deleted_backups:
            console.print(f"  - {path}")
    else:
        console.print("Deleted backups: none")
    if result.skipped_protected_backups:
        console.print("Skipped protected backups:")
        for path in result.skipped_protected_backups:
            console.print(f"  - {path}")
    if result.skipped_incomplete_backups:
        console.print("Skipped incomplete backups:")
        for path in result.skipped_incomplete_backups:
            console.print(f"  - {path}")
        console.print("Incomplete backups are not counted as successful backups and are never retention candidates.")
    if result.skipped_invalid_backups:
        console.print("Skipped invalid or unknown folders:")
        for item in result.skipped_invalid_backups:
            console.print(f"  - {item}")

@env_app.command("snapshot")
def create_env_snapshot(
    name: str = typer.Option(..., "--name", help="Snapshot name used under workspace/environment."),
    path: Path = typer.Option(..., "--path", help="Project path to inspect in read-only mode."),
) -> None:
    """Create a bounded environment snapshot and bootstrap plan."""
    try:
        snapshot, snapshot_file, plan_file = create_environment_snapshot(name=name, project_path=path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--path") from exc

    console.print(f"[green]Created environment snapshot[/green] {snapshot.name}")
    console.print(f"Project path: {snapshot.project_path}")
    console.print(f"Snapshot: {snapshot_file}")
    console.print(f"Bootstrap plan: {plan_file}")
    console.print(f"Dependency files found: {len(snapshot.dependency_files_found)}")
    console.print(f"Solution files: {len(snapshot.detected_solution_files)}")
    console.print(f"Project files: {len(snapshot.detected_project_files)}")
    console.print(f"Warnings: {len(snapshot.warnings)}")
    for warning in snapshot.warnings[:5]:
        console.print(f"  - {warning}")
    if len(snapshot.warnings) > 5:
        console.print(f"  - ... {len(snapshot.warnings) - 5} more warnings omitted")


@env_app.command("verify")
def verify_env_snapshot(
    snapshot: Path = typer.Option(..., "--snapshot", help="environment-snapshot.json to verify."),
) -> None:
    """Verify an environment snapshot schema and version."""
    try:
        result = verify_environment_snapshot(snapshot)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--snapshot") from exc

    console.print(f"[green]Verified environment snapshot[/green] {result.name}")
    console.print(f"Project path: {result.project_path}")
    console.print(f"Created at: {result.created_at.isoformat()}")
    console.print(f"Dependency files found: {len(result.dependency_files_found)}")
    console.print(f"Solutions: {len(result.detected_solution_files)}")
    console.print(f"Projects: {len(result.detected_project_files)}")
    console.print(f"Warnings: {len(result.warnings)}")


@env_app.command("bootstrap-plan")
def show_env_bootstrap_plan(
    snapshot: Path = typer.Option(..., "--snapshot", help="environment-snapshot.json to render into a bootstrap plan."),
) -> None:
    """Render and display a recovery bootstrap plan from a snapshot."""
    try:
        result, plan_file, plan_text = generate_environment_bootstrap_plan(snapshot)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--snapshot") from exc

    console.print(f"[green]Generated bootstrap plan[/green] {result.name}")
    console.print(f"Plan: {plan_file}")
    console.print("")
    console.print(plan_text)


def _print_workflow_action(action: WorkflowAction) -> None:
    console.print(f"Action type: {action.action_type}")
    console.print(f"Current status: {action.current_status}")
    console.print(f"Next status: {action.next_status or 'none'}")
    console.print(f"Agent: {action.agent_name or 'none'}")
    console.print(f"Task: {action.task_id or 'none'}")
    console.print(f"Command: {action.command_to_run or 'none'}")
    console.print(f"Expected output: {action.expected_output_artifact or 'none'}")
    console.print(f"Import command: {action.import_command or 'none'}")
    console.print(f"Reason: {action.reason or 'none'}")
    if action.blockers:
        console.print("Blockers:")
        for blocker in action.blockers:
            console.print(f"  - {blocker}")
    if action.warnings:
        console.print("Warnings:")
        for warning in action.warnings:
            console.print(f"  - {warning}")


@workflow_app.command("status")
def show_workflow_status(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show current run workflow state and next action."""
    try:
        status = get_workflow_status(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(f"[bold]{status.project_name}[/bold]")
    console.print(f"Run: {status.run_id}")
    console.print(f"Goal: {status.run_goal}")
    console.print(f"Run status: {status.run_status}")
    console.print(f"Context status: {status.context_status or 'unknown'}")
    console.print(f"Lifecycle stage: {status.lifecycle_stage}")
    console.print(f"Artifacts present: {', '.join(status.artifacts_present) or 'none'}")
    console.print(f"Artifacts missing: {', '.join(status.artifacts_missing) or 'none'}")
    console.print("Task ledger summary:")
    for key, value in status.task_ledger_summary.items():
        console.print(f"  {key}: {value}")
    console.print("Open tasks:")
    if status.open_tasks:
        for task in status.open_tasks:
            console.print(f"  - {task['task_id']}: {task['task_title']}")
    else:
        console.print("  none")
    console.print("Closed/resolved tasks:")
    resolved = {task['task_id']: task for task in status.closed_resolved_tasks}
    for task in status.dispositioned_tasks:
        resolved.setdefault(task['task_id'], task)
    if resolved:
        for task in resolved.values():
            console.print(
                f"  - {task['task_id']}: closure={task['closure_status']} disposition={task['disposition_status']}"
            )
    else:
        console.print("  none")
    console.print(f"Can close run: {status.can_close_run}")
    if status.warnings:
        console.print("Warnings:")
        for warning in status.warnings:
            console.print(f"  - {warning}")
    console.print("Next recommended action:")
    _print_workflow_action(status.next_action)


@workflow_app.command("next")
def show_workflow_next(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show the single next recommended workflow action without mutating state."""
    try:
        action = get_next_workflow_action(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    _print_workflow_action(action)


@workflow_app.command("advance")
def advance_workflow_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Explain deterministic next workflow advancement without fabricating outputs."""
    try:
        action = advance_workflow(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    _print_workflow_action(action)

@workflow_app.command("batch")
def run_workflow_batch_command(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    max_steps: int = typer.Option(20, "--max-steps", help="Maximum workflow decisions to inspect."),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Inspect and report without applying workflow mutations."),
    apply: bool = typer.Option(False, "--apply", help="Reserved for future deterministic internal mutations."),
) -> None:
    """Run bounded workflow guidance until a safe stop condition."""
    try:
        report = run_workflow_batch(
            project_name=project_name,
            run_id=run_id,
            max_steps=max_steps,
            dry_run=dry_run,
            apply=apply,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print("[bold]Workflow batch report[/bold]")
    console.print(f"Project: {report.project_name}")
    console.print(f"Run: {report.run_id}")
    console.print(f"Starting status: {report.starting_status}")
    console.print(f"Ending status: {report.ending_status}")
    console.print(f"Steps inspected: {report.steps_inspected}")
    console.print(f"Stop reason: {report.stop_reason}")
    console.print(f"Mutation occurred: {report.mutation_occurred}")
    console.print(f"Report: {report.report_path}")
    console.print(f"JSON report: {report.json_report_path}")
    if report.actions_recommended:
        console.print("Actions recommended:")
        for index, action in enumerate(report.actions_recommended, start=1):
            console.print(f"  Step {index}: {action.action_type}")
            console.print(f"    Agent: {action.agent_name or 'none'}")
            console.print(f"    Task: {action.task_id or 'none'}")
            console.print(f"    Command: {action.command_to_run or 'none'}")
    else:
        console.print("Actions recommended: none")
    if report.warnings:
        console.print("Warnings:")
        for warning in report.warnings:
            console.print(f"  - {warning}")
    console.print("Next human action:")
    console.print(f"  {report.next_human_action}")
