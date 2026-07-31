from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .projects import get_workspace_root
from .scanner import load_registered_project

PLANNING_DIR_NAME = "planning"
PROJECT_BRIEF_JSON = "project-brief.json"
PROJECT_BRIEF_MD = "project-brief.md"
BLUEPRINT_JSON = "blueprint.json"
BLUEPRINT_MD = "blueprint.md"
BACKLOG_JSON = "backlog.json"
BACKLOG_MD = "backlog.md"
PLANNING_SCHEMA_VERSION = "1"


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


class PlanningArtifactPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_dir: Path
    brief_json: Path
    brief_markdown: Path
    blueprint_json: Path
    blueprint_markdown: Path
    backlog_json: Path
    backlog_markdown: Path


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
    )


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

    text = source_path.read_text(encoding="utf-8")
    now = datetime.now(UTC)
    existing = load_project_brief(project_name, workspace_root=root)
    created_at = existing.created_at if existing else now
    brief = ProjectBrief(
        project=project_name,
        title=title.strip(),
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


def _extract_section(text: str, headings: tuple[str, ...]) -> str:
    items = _extract_list_section(text, headings)
    return " ".join(items).strip()


def _extract_list_section(text: str, headings: tuple[str, ...]) -> list[str]:
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


def _write_model(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _require_project(project_name: str, workspace_root: Path) -> None:
    load_registered_project(project_name, workspace_root=workspace_root)
