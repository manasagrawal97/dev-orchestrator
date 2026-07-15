from __future__ import annotations

import json
import os
from pathlib import Path

from .schemas import ProjectRegistration

SOFTWARE_PROJECT_MARKERS = (
    ".git",
    ".sln",
    ".csproj",
    "package.json",
    "pyproject.toml",
    "README.md",
)


def get_workspace_root() -> Path:
    override = os.getenv("DEVO_WORKSPACE")
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd() / "workspace"


def detect_project_markers(project_path: Path) -> list[str]:
    found: list[str] = []
    for marker in SOFTWARE_PROJECT_MARKERS:
        if marker.startswith(".") and marker not in {".git"}:
            matches = list(project_path.glob(f"*{marker}"))
            if matches:
                found.append(marker)
            continue

        if (project_path / marker).exists():
            found.append(marker)

    return found


def register_project(name: str, path: Path, workspace_root: Path | None = None) -> ProjectRegistration:
    project_path = path.expanduser().resolve()
    if not project_path.exists():
        msg = f"Project path does not exist: {project_path}"
        raise ValueError(msg)
    if not project_path.is_dir():
        msg = f"Project path must be a directory: {project_path}"
        raise ValueError(msg)

    detected_markers = detect_project_markers(project_path)
    registration = ProjectRegistration(
        name=name,
        path=project_path,
        looks_like_software_project=bool(detected_markers),
        detected_markers=detected_markers,
    )

    root = workspace_root or get_workspace_root()
    project_dir = root / "projects" / name
    project_dir.mkdir(parents=True, exist_ok=True)
    for lifecycle_dir in (
        project_dir / "context",
        project_dir / "context" / "drafts",
        project_dir / "context" / "reviews",
        project_dir / "context" / "approved",
        project_dir / "approvals",
    ):
        lifecycle_dir.mkdir(parents=True, exist_ok=True)
    project_file = project_dir / "project.json"
    project_file.write_text(
        registration.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return registration


def list_projects(workspace_root: Path | None = None) -> list[ProjectRegistration]:
    root = workspace_root or get_workspace_root()
    projects_dir = root / "projects"
    if not projects_dir.exists():
        return []

    registrations: list[ProjectRegistration] = []
    for project_file in sorted(projects_dir.glob("*/project.json")):
        data = json.loads(project_file.read_text(encoding="utf-8"))
        registrations.append(ProjectRegistration.model_validate(data))
    return registrations
