from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .backups import create_backup, list_backups, restore_backup, verify_backup

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
from .projects import get_workspace_root, list_projects, register_project
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

app = typer.Typer(help="DevOrchestrator local development CLI.")
project_app = typer.Typer(help="Manage registered projects.")
agent_app = typer.Typer(help="Inspect agent definitions and generate prompts.")
run_app = typer.Typer(help="Manage development runs.")
implementation_app = typer.Typer(help="Record implementation completion evidence.")
validation_app = typer.Typer(help="Inspect validation review evidence.")
review_app = typer.Typer(help="Inspect code review evidence.")
audit_app = typer.Typer(help="Inspect final audit evidence.")
task_app = typer.Typer(help="Manage run tasks.")
backup_app = typer.Typer(help="Backup, verify, list, and restore workspace state.")
app.add_typer(project_app, name="project")
app.add_typer(agent_app, name="agent")
app.add_typer(run_app, name="run")
app.add_typer(implementation_app, name="implementation")
app.add_typer(validation_app, name="validation")
app.add_typer(review_app, name="review")
app.add_typer(audit_app, name="audit")
app.add_typer(task_app, name="task")
app.add_typer(backup_app, name="backup")

console = Console()


def _named_path(path: object | None) -> str:
    if not path:
        return "none"
    path_text = str(path)
    return f"{Path(path_text).name} ({path_text})"


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


@backup_app.command("create")
def create_workspace_backup(
    dest: Path = typer.Option(..., "--dest", help="Backup root directory."),
    label: str | None = typer.Option(None, "--label", help="Optional backup label."),
) -> None:
    """Create a timestamped backup of DevOrchestrator workspace state."""
    try:
        manifest = create_backup(dest=dest, label=label)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--dest") from exc

    console.print(f"[green]Created backup[/green] {manifest.backup_path}")
    console.print(f"Manifest: {manifest.backup_path / 'backup-manifest.json'}")
    console.print(f"Files: {manifest.file_count}")
    console.print(f"Total bytes: {manifest.total_bytes}")
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
    backups = list_backups(dest)
    if not backups:
        console.print("[yellow]No backups found.[/yellow]")
        return

    for manifest in backups:
        console.print(f"[bold]{manifest.backup_path.name}[/bold]")
        console.print(f"  Path: {manifest.backup_path}")
        console.print(f"  Created at: {manifest.created_at.isoformat()}")
        console.print(f"  Label: {manifest.label or 'none'}")
        console.print(f"  Files: {manifest.file_count}")
        console.print(f"  Total bytes: {manifest.total_bytes}")
        console.print(f"  Git: {manifest.git_branch} {manifest.git_commit_hash}")
