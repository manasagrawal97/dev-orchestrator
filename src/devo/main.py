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
    list_run_tasks,
    mark_task_disposition,
    list_runs,
    load_run,
    run_path,
    save_current_selection,
)
from .scanner import scan_registered_project
from .task_selector import DEFAULT_STRATEGY, TaskSelection, list_task_candidates, select_next_task
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


@app.command("doctor")
def doctor(
    project_name: str | None = typer.Option(None, "--project", help="Registered project name to include in health checks."),
) -> None:
    """Run read-only Devo and optional project health checks."""
    report = run_doctor(project_name=project_name)
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


@project_app.command("activity")
def show_project_activity(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Show compact project activity across runs, work packages, validation, reports, and Git."""
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

    console.print(f"[green]Selected project[/green] {selection.project_name}")
    if selection.run_id:
        console.print(f"Run: {selection.run_id}")
        console.print(f"Run path: {selection.run_path}")
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
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """List recent work packages and project runs."""
    try:
        summaries = list_work_package_summaries(project_name=project_name, limit=limit)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_work_summary_list(summaries, f"Recent work for {project_name}")


@work_app.command("history")
def show_work_history(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Show delivery-focused work package history."""
    try:
        summaries = list_work_package_summaries(project_name=project_name, limit=limit, delivered_first=True)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--project") from exc
    _print_work_summary_list(summaries, f"Work history for {project_name}", include_delivery=True)


@work_app.command("new")
def new_work(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    goal: str = typer.Option(..., "--goal", help="Work package goal."),
    lane_id: str = typer.Option(..., "--lane", help="Work lane ID."),
    no_template: bool = typer.Option(False, "--no-template", help="Skip scope template generation."),
    print_resume: bool = typer.Option(False, "--print-resume", help="Print the full resume guidance after creation."),
) -> None:
    """Create a run, draft work package, optional scope template, and resume guidance."""
    try:
        package = start_work_package(project_name=project_name, lane_id=lane_id, goal=goal)
    except ValueError as exc:
        hint = "--lane" if "Unknown work lane" in str(exc) else "--project"
        raise typer.BadParameter(str(exc), param_hint=hint) from exc

    template_path = None
    if not no_template:
        template = generate_work_scope_template(project_name=project_name, run_id=package.run_id)
        template_path = template.template_path
    resume = build_work_package_resume(project_name=project_name, run_id=package.run_id)
    next_step = get_work_package_next_step(package)

    console.print("[green]Created work package.[/green]")
    console.print(f"Run: {package.run_id}")
    console.print(f"Lane: {package.lane}")
    console.print(f"Scope template: {_named_path(template_path) if template_path else 'skipped'}")
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
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Write a fill-in scope markdown template for a draft work package."""
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
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show work package status and artifact paths."""
    try:
        package = load_work_package(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_work_package(package)


@work_app.command("next")
def show_work_next(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show the next work-package action without mutating project files."""
    try:
        package = load_work_package(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    _print_work_next(package)


@work_app.command("resume")
def show_work_resume(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Show a compact operator plan for resuming a work package."""
    try:
        resume = build_work_package_resume(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc

    console.print(resume.resume_text)


@work_app.command("prompt")
def write_work_prompt(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    phase: str = typer.Option(..., "--phase", help="Prompt phase: scope, implement, validate, deliver, or complete."),
) -> None:
    """Write a phase-specific Codex operator prompt for a work package."""
    try:
        result = generate_work_package_phase_prompt(project_name=project_name, run_id=run_id, phase=phase)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--phase") from exc

    console.print(f"Phase: {result.phase}")
    console.print(f"Prompt: {_named_path(result.prompt_path)}")


@work_app.command("complete")
def complete_work(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    commit_hash: str = typer.Option(..., "--commit", help="Delivered Git commit hash."),
    message: str = typer.Option(..., "--message", help="Short delivery summary."),
) -> None:
    """Mark a work package delivered after validation, commit, and push."""
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
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
    task_id: str = typer.Option(..., "--task", help="Task ID."),
) -> None:
    """Request the source-edit and validation approvals for a work package."""
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
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    run_id: str = typer.Option(..., "--run", help="Run ID."),
) -> None:
    """Write a Mermaid work-package lifecycle visual artifact."""
    try:
        result = generate_work_package_visual(project_name=project_name, run_id=run_id)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--run") from exc
    console.print(f"Visual report: {_named_path(result.path)}")


@visual_app.command("project-activity")
def write_project_activity_visual(
    project_name: str = typer.Option(..., "--project", help="Registered project name."),
    limit: int = typer.Option(10, "--limit", min=1, help="Recent item limit."),
) -> None:
    """Write a compact Mermaid project activity visual artifact."""
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
