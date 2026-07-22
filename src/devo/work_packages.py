from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .projects import get_workspace_root
from .runs import create_run, load_run, run_path, save_run_state
from .scanner import load_registered_project
from .schemas import RunArtifact, RunArtifactType, RunStatus
from .validation_registry import get_validation_command, list_validation_commands

WORK_PACKAGE_SCHEMA_VERSION = "1"
WORK_PACKAGE_DIR = "work-package"
WORK_PACKAGE_JSON = "work-package.json"
WORK_PACKAGE_MD = "work-package.md"
OPERATOR_PROMPT_MD = "operator-prompt.md"


class WorkPackageStatus(StrEnum):
    DRAFT = "draft"
    SCOPE_PROPOSED = "scope_proposed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    VALIDATED = "validated"
    DELIVERED = "delivered"
    CLOSED = "closed"


class WorkLane(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    allowed: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    default_validation_commands: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class WorkPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = WORK_PACKAGE_SCHEMA_VERSION
    project: str
    run_id: str
    goal: str
    lane: str
    status: WorkPackageStatus
    proposed_items: list[str] = Field(default_factory=list)
    approved_files: list[str] = Field(default_factory=list)
    allowed_changes: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    delivery_plan: list[str] = Field(default_factory=list)
    approval_bundle_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScopeImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: WorkPackage
    scope_file: Path
    missing_sections: list[str] = Field(default_factory=list)


BUILT_IN_LANES: dict[str, WorkLane] = {
    "low-risk-ui-maintenance": WorkLane(
        id="low-risk-ui-maintenance",
        name="Low-risk UI maintenance",
        allowed=[
            "Razor UI files",
            "UI help text",
            "empty states",
            "mechanical analyzer/warning fixes",
            "small display-only prompts using already-loaded data",
            "dotnet build validation",
        ],
        forbidden=[
            "DB changes",
            "migrations",
            "appsettings",
            "secrets",
            "local settings",
            "scripts",
            "backups",
            "generated files",
            "user data",
            "app run",
            "external API calls",
            "behavior-heavy refactors",
        ],
        default_validation_commands=["dotnet-build-personalos"],
        notes=[
            "Prefer project validation command dotnet-build-personalos when present.",
            "If that command is not registered, import-scope must provide a validation command.",
        ],
    )
}

REQUIRED_SCOPE_SECTIONS = {
    "selected items": "proposed_items",
    "exact files": "approved_files",
    "allowed changes": "allowed_changes",
    "forbidden changes": "forbidden_changes",
    "validation command": "validation_commands",
    "delivery plan": "delivery_plan",
}


def list_lanes() -> list[WorkLane]:
    return list(BUILT_IN_LANES.values())


def get_lane(lane_id: str) -> WorkLane:
    normalized = lane_id.strip()
    lane = BUILT_IN_LANES.get(normalized)
    if not lane:
        allowed = ", ".join(sorted(BUILT_IN_LANES))
        msg = f"Unknown work lane: {lane_id}. Available lanes: {allowed}"
        raise ValueError(msg)
    return lane


def start_work_package(
    project_name: str,
    lane_id: str,
    goal: str,
    workspace_root: Path | None = None,
) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    lane = get_lane(lane_id)
    run_state = create_run(project_name, goal, workspace_root=root)
    validation_commands = _default_validation_commands(project_name, lane, root)
    package = WorkPackage(
        project=project_name,
        run_id=run_state.run_id,
        goal=goal,
        lane=lane.id,
        status=WorkPackageStatus.DRAFT,
        allowed_changes=list(lane.allowed),
        forbidden_changes=list(lane.forbidden),
        validation_commands=validation_commands,
    )
    save_work_package(package, workspace_root=root)
    return package


def import_work_scope(
    project_name: str,
    run_id: str,
    scope_file: Path,
    workspace_root: Path | None = None,
) -> ScopeImportResult:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    source_path = scope_file.expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        msg = f"Scope import file does not exist: {source_path}"
        raise ValueError(msg)
    text = source_path.read_text(encoding="utf-8")
    sections = _extract_sections(text)
    missing = [section for section in REQUIRED_SCOPE_SECTIONS if not sections.get(section)]
    if missing:
        msg = f"Scope file is missing required sections: {', '.join(missing)}"
        raise ValueError(msg)

    updated = package.model_copy(
        update={
            "status": WorkPackageStatus.SCOPE_PROPOSED,
            "proposed_items": _section_items(sections["selected items"]),
            "approved_files": _section_items(sections["exact files"]),
            "allowed_changes": _section_items(sections["allowed changes"]),
            "forbidden_changes": _section_items(sections["forbidden changes"]),
            "validation_commands": _normalize_validation_commands(_section_items(sections["validation command"])),
            "delivery_plan": _section_items(sections["delivery plan"]),
            "updated_at": datetime.now(UTC),
        }
    )
    save_work_package(updated, workspace_root=root)
    _write_task_artifact(updated, workspace_root=root)
    return ScopeImportResult(package=updated, scope_file=source_path)


def load_work_package(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    load_run(project_name, run_id, workspace_root=root)
    path = work_package_path(project_name, run_id, workspace_root=root)
    if not path.exists():
        msg = f"Work package not found for run: {run_id}"
        raise ValueError(msg)
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkPackage.model_validate(data)


def save_work_package(package: WorkPackage, workspace_root: Path | None = None) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    package = package.model_copy(update={"updated_at": datetime.now(UTC)})
    directory = _work_package_dir(root, package.project, package.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / WORK_PACKAGE_JSON).write_text(package.model_dump_json(indent=2), encoding="utf-8")
    (directory / WORK_PACKAGE_MD).write_text(render_work_package_markdown(package), encoding="utf-8")
    (directory / OPERATOR_PROMPT_MD).write_text(render_operator_prompt(package, workspace_root=root), encoding="utf-8")
    return package


def set_work_package_approval_bundle(
    project_name: str,
    run_id: str,
    bundle_id: str,
    workspace_root: Path | None = None,
) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    updated = package.model_copy(
        update={
            "approval_bundle_id": bundle_id,
            "status": WorkPackageStatus.APPROVAL_REQUESTED,
            "updated_at": datetime.now(UTC),
        }
    )
    return save_work_package(updated, workspace_root=root)


def work_package_path(project_name: str, run_id: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return _work_package_dir(root, project_name, run_id) / WORK_PACKAGE_JSON


def work_package_artifact_paths(package: WorkPackage, workspace_root: Path | None = None) -> dict[str, Path]:
    root = workspace_root or get_workspace_root()
    directory = _work_package_dir(root, package.project, package.run_id)
    return {
        "json": directory / WORK_PACKAGE_JSON,
        "markdown": directory / WORK_PACKAGE_MD,
        "operator_prompt": directory / OPERATOR_PROMPT_MD,
    }


def render_work_package_markdown(package: WorkPackage) -> str:
    lines = [
        f"# Work Package: {package.goal}",
        "",
        f"- schema_version: {package.schema_version}",
        f"- project: {package.project}",
        f"- run_id: {package.run_id}",
        f"- lane: {package.lane}",
        f"- status: {package.status.value}",
        f"- approval_bundle_id: {package.approval_bundle_id or 'none'}",
        f"- created_at: {package.created_at.isoformat()}",
        f"- updated_at: {package.updated_at.isoformat()}",
        "",
        "## Proposed Items",
        "",
    ]
    lines.extend(_bullets(package.proposed_items))
    lines.extend(["", "## Approved Files", ""])
    lines.extend(_bullets(package.approved_files))
    lines.extend(["", "## Allowed Changes", ""])
    lines.extend(_bullets(package.allowed_changes))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(package.forbidden_changes))
    lines.extend(["", "## Validation Commands", ""])
    lines.extend(_bullets(package.validation_commands))
    lines.extend(["", "## Delivery Plan", ""])
    lines.extend(_bullets(package.delivery_plan))
    lines.append("")
    return "\n".join(lines)


def render_operator_prompt(package: WorkPackage, workspace_root: Path | None = None) -> str:
    root = workspace_root or get_workspace_root()
    project = load_registered_project(package.project, workspace_root=root)
    lines = [
        f"# Codex Operator Prompt: {package.goal}",
        "",
        f"Project: {package.project}",
        f"Project path: {project.path}",
        f"Run id: {package.run_id}",
        f"Lane: {package.lane}",
        f"Status: {package.status.value}",
        "",
        "## Goal",
        "",
        package.goal,
        "",
        "## Allowed Changes",
        "",
    ]
    lines.extend(_bullets(package.allowed_changes))
    lines.extend(["", "## Approved Files Or Areas", ""])
    lines.extend(_bullets(package.approved_files))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(package.forbidden_changes))
    lines.extend(
        [
            "",
            "## Approval Rules",
            "",
            "- Do not edit target project files until the approval bundle is approved.",
            "- Child approvals remain normal Devo approvals.",
            "- A bundle does not bypass Codex, OS, GitHub, shell, or external-service approval policy.",
            "- Stop if scope changes or a child approval is rejected/blocked.",
            "",
            "## Validation Command",
            "",
        ]
    )
    lines.extend(_bullets(package.validation_commands))
    lines.extend(
        [
            "",
            "## Delivery Rules",
            "",
        ]
    )
    lines.extend(_bullets(package.delivery_plan))
    lines.extend(
        [
            "",
            "## Stop Conditions",
            "",
            "- DB, migrations, appsettings, secrets, local settings, scripts, backups, generated files, user data, app run, or external API calls are needed.",
            "- A file outside the approved scope is needed.",
            "- The fix requires a behavior-heavy refactor.",
            "- Validation fails.",
            "- Git is dirty in an unexpected way.",
            "",
            "## Final Report Format",
            "",
            "- changed files",
            "- exact behavior changed",
            "- validation result",
            "- Devo artifacts",
            "- commit hash",
            "- push result",
            "- final Git status",
            "",
        ]
    )
    return "\n".join(lines)


def _write_task_artifact(package: WorkPackage, workspace_root: Path) -> None:
    run_state = load_run(package.project, package.run_id, workspace_root=workspace_root)
    artifacts_dir = run_path(package.project, package.run_id, workspace_root=workspace_root) / "artifacts"
    tasks_path = artifacts_dir / "tasks.md"
    task_text = _render_task_artifact(package)
    tasks_path.write_text(task_text, encoding="utf-8")
    artifact = RunArtifact(
        artifact_type=RunArtifactType.TASKS,
        agent_name="WorkPackage",
        source_file_path=work_package_artifact_paths(package, workspace_root=workspace_root)["markdown"],
        artifact_path=tasks_path,
    )
    run_state.artifacts = [item for item in run_state.artifacts if item.artifact_type != RunArtifactType.TASKS]
    run_state.artifacts.append(artifact)
    run_state.status = RunStatus.TASKS_DRAFTED
    run_state.updated_at = datetime.now(UTC)
    save_run_state(run_state, workspace_root=workspace_root)


def _render_task_artifact(package: WorkPackage) -> str:
    return "\n".join(
        [
            "# task-list.md",
            "",
            "## Task T001",
            "",
            "- task id: T001",
            f"- task title: {package.goal}",
            f"- objective: {package.goal}",
            f"- scope: Work package lane {package.lane}; files {', '.join(package.approved_files) or 'none specified'}.",
            f"- out-of-scope: {', '.join(package.forbidden_changes) or 'none specified'}.",
            f"- likely files or areas: {', '.join(package.approved_files) or 'none specified'}.",
            f"- validation required: {', '.join(package.validation_commands) or 'none specified'}.",
            "- risk level: high",
            "- dependencies: Approval bundle before source edit and build validation.",
            "- recommended executor: Codex after bundled approval.",
            "",
            "# task-dependency-map.md",
            "",
            "- T001 has no implementation dependencies other than approval.",
            "",
            "# first-safe-task.md",
            "",
            "T001 is the selected work package task after approval.",
            "",
        ]
    )


def _extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(r"(?ims)^#{1,6}\s+(.+?)\s*$\n?(.*?)(?=^#{1,6}\s+.+?\s*$|\Z)")
    for match in pattern.finditer(text):
        title = _normalize_heading(match.group(1))
        body = match.group(2).strip()
        if title in REQUIRED_SCOPE_SECTIONS:
            sections[title] = body
    return sections


def _normalize_heading(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
    normalized = " ".join(normalized.split())
    aliases = {
        "validation commands": "validation command",
    }
    return aliases.get(normalized, normalized)


def _section_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        if stripped:
            items.append(stripped.strip("`"))
    if not items and text.strip():
        items.append(" ".join(text.strip().split()))
    return items


def _normalize_validation_commands(items: list[str]) -> list[str]:
    commands: list[str] = []
    for item in items:
        value = item.strip()
        if not value:
            continue
        match = re.search(r"\b[A-Za-z0-9._-]+\b", value)
        commands.append(match.group(0) if match else value)
    return commands


def _default_validation_commands(project_name: str, lane: WorkLane, workspace_root: Path) -> list[str]:
    registered = {command.id for command in list_validation_commands(project_name, workspace_root=workspace_root)}
    defaults = [command_id for command_id in lane.default_validation_commands if command_id in registered]
    return defaults


def _work_package_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / WORK_PACKAGE_DIR


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def bundle_id_for_package(project_name: str, run_id: str, task_id: str, created_at: datetime) -> str:
    seed = f"{project_name}|{run_id}|{task_id}|{created_at.isoformat()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def validation_command_details(project_name: str, command_id: str, workspace_root: Path | None = None) -> tuple[str, str]:
    command = get_validation_command(project_name, command_id, workspace_root=workspace_root)
    return command.id, command.command
