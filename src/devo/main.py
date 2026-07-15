from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .agents import (
    DISCOVERY_AGENT_NAME,
    REVIEWER_AGENT_NAME,
    generate_project_context_discovery_prompt,
    generate_project_context_reviewer_prompt,
    list_agent_definitions,
    load_agent_definition,
    render_agent_definition,
)
from .context import approve_context, get_context_status, import_agent_output
from .projects import get_workspace_root, list_projects, register_project
from .scanner import scan_registered_project

app = typer.Typer(help="DevOrchestrator local development CLI.")
project_app = typer.Typer(help="Manage registered projects.")
agent_app = typer.Typer(help="Inspect agent definitions and generate prompts.")
app.add_typer(project_app, name="project")
app.add_typer(agent_app, name="agent")

console = Console()


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
    else:
        raise typer.BadParameter(
            f"Prompt generation is only supported for {DISCOVERY_AGENT_NAME} and {REVIEWER_AGENT_NAME}.",
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
    file_path: Path = typer.Option(..., "--file", help="Markdown output file to import."),
) -> None:
    """Import manual prompt output for a supported agent."""
    try:
        load_agent_definition(agent_name)
        artifact = import_agent_output(agent_name=agent_name, project_name=project_name, source_file=file_path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="agentName") from exc

    console.print(f"[green]Imported output[/green] for {artifact.agent_name}")
    console.print(f"Project: {project_name}")
    console.print(f"Source: {artifact.source_file_path}")
    console.print(f"Stored in: {artifact.artifact_path}")
