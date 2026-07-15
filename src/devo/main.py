from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .projects import get_workspace_root, list_projects, register_project
from .scanner import scan_registered_project

app = typer.Typer(help="DevOrchestrator local development CLI.")
project_app = typer.Typer(help="Manage registered projects.")
app.add_typer(project_app, name="project")

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
