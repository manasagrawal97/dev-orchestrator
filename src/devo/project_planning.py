from __future__ import annotations

import re
from datetime import UTC, datetime
from pydantic import ValidationError
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .projects import get_workspace_root
from .scanner import load_registered_project
from .work_packages import BUILT_IN_LANES

PLANNING_DIR_NAME = "planning"
PROJECT_BRIEF_JSON = "project-brief.json"
PROJECT_BRIEF_MD = "project-brief.md"
BLUEPRINT_JSON = "blueprint.json"
BLUEPRINT_MD = "blueprint.md"
BACKLOG_JSON = "backlog.json"
BACKLOG_MD = "backlog.md"
BACKLOG_REFINEMENT_PROMPT_MD = "backlog-refinement-prompt.md"
BATCHES_DIR_NAME = "batches"
BATCH_INDEX_JSON = "batch-index.json"
PLANNING_SCHEMA_VERSION = "1"
ALLOWED_BACKLOG_STATUSES = {"draft", "reviewed", "approved", "superseded"}
ALLOWED_TASK_STATUSES = {"draft", "ready", "approved", "in_progress", "blocked", "completed", "superseded"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_BATCH_STATUSES = {"draft", "reviewed", "approved", "in_progress", "completed", "blocked", "superseded"}
SELECTABLE_TASK_STATUSES = {"draft", "ready", "approved"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


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


class BacklogValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    task_count: int = 0


class BatchTaskSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria_summary: str = ""
    validation_expectations_summary: str = ""


class ProjectBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batch_id: str
    title: str
    summary: str
    source_backlog_reference: str
    status: str = "draft"
    task_ids: list[str] = Field(default_factory=list)
    task_count: int = 0
    completed_task_count: int = 0
    blocked_task_count: int = 0
    risk_summary: dict[str, int] = Field(default_factory=dict)
    lane_summary: dict[str, int] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    approval_status: str = "not_requested"
    review_notes: list[str] = Field(default_factory=list)
    task_snapshots: list[BatchTaskSnapshot] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    title: str
    status: str
    task_count: int
    approval_status: str
    path: str
    updated_at: datetime


class BatchIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batches: list[BatchIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str
    reason: str


class BatchSuggestionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    suggested_tasks: list[BatchSuggestion] = Field(default_factory=list)
    skipped_tasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PlanningArtifactPaths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planning_dir: Path
    brief_json: Path
    brief_markdown: Path
    blueprint_json: Path
    blueprint_markdown: Path
    backlog_json: Path
    backlog_markdown: Path
    backlog_refinement_prompt: Path
    batches_dir: Path
    batch_index_json: Path


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
        backlog_refinement_prompt=planning_dir / BACKLOG_REFINEMENT_PROMPT_MD,
        batches_dir=planning_dir / BATCHES_DIR_NAME,
        batch_index_json=planning_dir / BATCHES_DIR_NAME / BATCH_INDEX_JSON,
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


def generate_backlog_refinement_prompt(project_name: str, workspace_root: Path | None = None) -> tuple[Path, str]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not blueprint:
        msg = f"Project blueprint not found for project: {project_name}"
        raise ValueError(msg)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    prompt = render_backlog_refinement_prompt(project_name, brief, blueprint, backlog)
    paths.backlog_refinement_prompt.write_text(prompt, encoding="utf-8")
    return paths.backlog_refinement_prompt, prompt


def validate_refined_backlog_file(
    project_name: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> tuple[BacklogValidationResult, ProjectBacklog | None]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Refined backlog file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Refined backlog path must be a file: {source_path}"
        raise ValueError(msg)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        backlog = ProjectBacklog.model_validate_json(source_path.read_text(encoding="utf-8"))
    except (ValueError, ValidationError) as exc:
        return BacklogValidationResult(valid=False, errors=[f"Invalid backlog JSON: {exc}"]), None

    if backlog.project != project_name:
        errors.append(f"Backlog project must be {project_name}, got {backlog.project}.")
    if backlog.status not in ALLOWED_BACKLOG_STATUSES:
        errors.append(f"Invalid backlog status: {backlog.status}.")
    seen: set[str] = set()
    all_task_ids = {task.id.strip().upper() for task in backlog.tasks}
    known_lanes = set(BUILT_IN_LANES)
    for task in backlog.tasks:
        normalized_id = task.id.strip().upper()
        if normalized_id in seen:
            errors.append(f"Duplicate task id: {task.id}.")
        seen.add(normalized_id)
        if task.status not in ALLOWED_TASK_STATUSES:
            errors.append(f"Invalid status for {task.id}: {task.status}.")
        if task.risk_level not in ALLOWED_RISK_LEVELS:
            errors.append(f"Invalid risk level for {task.id}: {task.risk_level}.")
        if task.lane not in known_lanes:
            errors.append(f"Unknown lane for {task.id}: {task.lane}.")
        for dependency in task.dependencies:
            if dependency.strip().upper() not in all_task_ids:
                warnings.append(f"Task {task.id} depends on unknown task id: {dependency}.")
    result = BacklogValidationResult(valid=not errors, errors=errors, warnings=warnings, task_count=len(backlog.tasks))
    return result, backlog if result.valid else None


def import_refined_backlog(
    project_name: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> tuple[ProjectBacklog, PlanningArtifactPaths, BacklogValidationResult]:
    root = workspace_root or get_workspace_root()
    result, backlog = validate_refined_backlog_file(project_name, source_file, workspace_root=root)
    if not result.valid or not backlog:
        msg = "Refined backlog validation failed: " + "; ".join(result.errors)
        raise ValueError(msg)
    now = datetime.now(UTC)
    safe_tasks = [task.model_copy(update={"status": _safe_import_task_status(task.status), "updated_at": now}) for task in backlog.tasks]
    imported = _with_backlog_counts(backlog.model_copy(update={"status": "draft", "tasks": safe_tasks, "updated_at": now}))
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.planning_dir.mkdir(parents=True, exist_ok=True)
    _write_model(paths.backlog_json, imported)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(imported), encoding="utf-8")
    return imported, paths, result


def create_project_batch(
    project_name: str,
    title: str,
    task_ids: list[str],
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    normalized_ids = _normalize_task_ids(task_ids)
    if not normalized_ids:
        msg = "At least one task id is required."
        raise ValueError(msg)
    if len(set(normalized_ids)) != len(normalized_ids):
        msg = "Duplicate task ids are not allowed."
        raise ValueError(msg)
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    missing = [task_id for task_id in normalized_ids if task_id not in task_by_id]
    if missing:
        msg = f"Backlog task id not found: {', '.join(missing)}"
        raise ValueError(msg)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    batch_id = _next_batch_id(project_name, workspace_root=root)
    tasks = [task_by_id[task_id] for task_id in normalized_ids]
    now = datetime.now(UTC)
    batch = _build_batch_from_tasks(
        project_name=project_name,
        batch_id=batch_id,
        title=title.strip() or f"Planning Batch {batch_id}",
        tasks=tasks,
        backlog=backlog,
        source_backlog_reference=str(paths.backlog_json),
        now=now,
    )
    json_path, markdown_path = _write_project_batch(project_name, batch, workspace_root=root)
    return batch, json_path, markdown_path


def suggest_project_batch(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> BatchSuggestionResult:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        msg = f"Project backlog not found for project: {project_name}"
        raise ValueError(msg)
    safe_limit = max(1, limit)
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    completed = {task_id for task_id, task in task_by_id.items() if task.status == "completed"}
    selected: list[BacklogTask] = []
    skipped: list[str] = []
    warnings: list[str] = []
    candidates = sorted(
        [task for task in backlog.tasks if task.status in SELECTABLE_TASK_STATUSES],
        key=lambda task: (RISK_ORDER.get(task.risk_level, 99), task.lane, task.id),
    )
    for task in candidates:
        if len(selected) >= safe_limit:
            break
        selected_ids = {item.id.strip().upper() for item in selected}
        dependencies = [dependency.strip().upper() for dependency in task.dependencies]
        missing_dependencies = [dependency for dependency in dependencies if dependency not in task_by_id]
        unresolved = [dependency for dependency in dependencies if dependency not in completed and dependency not in selected_ids]
        if missing_dependencies:
            skipped.append(f"{task.id}: missing dependency {', '.join(missing_dependencies)}")
            continue
        if unresolved:
            skipped.append(f"{task.id}: unresolved dependency {', '.join(unresolved)}")
            continue
        selected.append(task)
    if not selected:
        warnings.append("No ready batch candidates found.")
    suggestions = [
        BatchSuggestion(
            task_id=task.id,
            title=task.title,
            lane=task.lane,
            risk_level=task.risk_level,
            status=task.status,
            reason=_suggestion_reason(task),
        )
        for task in selected
    ]
    return BatchSuggestionResult(project=project_name, suggested_tasks=suggestions, skipped_tasks=skipped, warnings=warnings)


def create_suggested_project_batch(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchSuggestionResult]:
    root = workspace_root or get_workspace_root()
    suggestion = suggest_project_batch(project_name, limit=limit, workspace_root=root)
    task_ids = [task.task_id for task in suggestion.suggested_tasks]
    if not task_ids:
        msg = "No suggested tasks are available for a batch."
        raise ValueError(msg)
    batch, json_path, markdown_path = create_project_batch(
        project_name,
        title="Suggested planning batch",
        task_ids=task_ids,
        workspace_root=root,
    )
    return batch, json_path, markdown_path, suggestion


def load_batch_index(project_name: str, workspace_root: Path | None = None) -> BatchIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.batch_index_json.exists():
        return BatchIndex(project=project_name)
    return BatchIndex.model_validate_json(paths.batch_index_json.read_text(encoding="utf-8"))


def list_project_batches(project_name: str, workspace_root: Path | None = None) -> list[ProjectBatch]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.batches_dir.exists():
        return []
    batches: list[ProjectBatch] = []
    for path in sorted(paths.batches_dir.glob("batch-*.json")):
        if path.name == BATCH_INDEX_JSON:
            continue
        try:
            batches.append(ProjectBatch.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(batches, key=lambda batch: batch.updated_at, reverse=True)


def load_project_batch(project_name: str, batch_id: str, workspace_root: Path | None = None) -> ProjectBatch | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = project_batch_artifact_paths(project_name, batch_id, workspace_root=root)
    if not json_path.exists():
        return None
    return ProjectBatch.model_validate_json(json_path.read_text(encoding="utf-8"))


def approve_project_batch(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[ProjectBatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    updated = batch.model_copy(update={"status": "approved", "approval_status": "approved", "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    return updated, json_path, markdown_path


def review_project_batch(project_name: str, batch_id: str, note: str, workspace_root: Path | None = None) -> tuple[ProjectBatch, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    cleaned = note.strip()
    if not cleaned:
        msg = "Review note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = [*batch.review_notes, f"{now.isoformat()}: {cleaned}"]
    status = "reviewed" if batch.status == "draft" else batch.status
    updated = batch.model_copy(update={"status": status, "review_notes": notes, "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    return updated, json_path, markdown_path


def project_batch_artifact_paths(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_batch_id(batch_id)
    return paths.batches_dir / f"batch-{safe_id}.json", paths.batches_dir / f"batch-{safe_id}.md"


def render_project_batch_markdown(batch: ProjectBatch) -> str:
    lines = [
        f"# {batch.title}",
        "",
        f"- Project: `{batch.project}`",
        f"- Batch id: `{batch.batch_id}`",
        f"- Status: `{batch.status}`",
        f"- Approval status: `{batch.approval_status}`",
        f"- Source backlog: `{batch.source_backlog_reference}`",
        f"- Task count: `{batch.task_count}`",
        f"- Completed tasks: `{batch.completed_task_count}`",
        f"- Blocked tasks: `{batch.blocked_task_count}`",
        f"- Created: `{batch.created_at.isoformat()}`",
        f"- Updated: `{batch.updated_at.isoformat()}`",
        "",
        "## Summary",
        "",
        batch.summary or "No summary recorded.",
        "",
    ]
    _append_mapping_section(lines, "Risk Summary", batch.risk_summary)
    _append_mapping_section(lines, "Lane Summary", batch.lane_summary)
    _append_list_section(lines, "Dependencies", batch.dependencies)
    _append_list_section(lines, "Dependency Warnings", batch.dependency_warnings)
    _append_list_section(lines, "Review Notes", batch.review_notes)
    lines.extend(["## Task Snapshots", ""])
    if not batch.task_snapshots:
        lines.extend(["No tasks recorded.", ""])
    for task in batch.task_snapshots:
        lines.extend(
            [
                f"### {task.task_id}: {task.title}",
                "",
                f"- Status: `{task.status}`",
                f"- Lane: `{task.lane}`",
                f"- Risk: `{task.risk_level}`",
                f"- Dependencies: `{', '.join(task.dependencies) if task.dependencies else 'none'}`",
                f"- Acceptance criteria: {task.acceptance_criteria_summary or 'none'}",
                f"- Validation: {task.validation_expectations_summary or 'none'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Safety Note",
            "",
            "Planning approval only: batch approval does not approve implementation execution. Execution queue, Codex automation, implementation approval, validation, commit, and push are future workflow steps.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_backlog_refinement_prompt(
    project_name: str,
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint,
    backlog: ProjectBacklog,
) -> str:
    example = _with_backlog_counts(
        ProjectBacklog(
            project=project_name,
            title="Refined implementation backlog",
            blueprint_reference=backlog.blueprint_reference,
            status="draft",
            tasks=[
                BacklogTask(
                    id="T001",
                    title="Small implementation task",
                    summary="One implementation-ready task description.",
                    milestone_id=blueprint.milestones[0].id if blueprint.milestones else None,
                    epic_id=blueprint.epics[0].id if blueprint.epics else None,
                    lane="small-feature",
                    risk_level="medium",
                    status="draft",
                    dependencies=[],
                    acceptance_criteria=["Concrete user-visible or technical acceptance criterion."],
                    validation_expectations=["Registered validation command or manual validation evidence needed."],
                    allowed_scope=["Specific files or areas allowed for this task."],
                    forbidden_scope=["DB/migrations/secrets/scripts/backups unless explicitly approved."],
                    notes=["Planning only; not approved for implementation."],
                    source="codex-refinement",
                )
            ],
        )
    )
    return "\n".join(
        [
            f"# Backlog Refinement Handoff: {project_name}",
            "",
            "You are Codex acting as a planning worker. This is planning only.",
            "",
            "## Hard Rules",
            "",
            "- Do not modify source code.",
            "- Do not run build, test, restore, backup, migration, database, scheduler, app, or external API commands.",
            "- Do not call AI/model APIs.",
            "- Preserve Devo's safety model, approvals, validation evidence, and target repository boundaries.",
            "- Do not suggest unapproved risky work as ordinary low-risk tasks.",
            "- Refine the backlog into small implementation-ready tasks suitable for later work packages/batches.",
            "",
            "## Project Brief Summary",
            "",
            brief.summary if brief else "No Project Brief artifact is available.",
            "",
            "## Blueprint",
            "",
            render_project_blueprint_markdown(blueprint).strip(),
            "",
            "## Current Backlog",
            "",
            render_project_backlog_markdown(backlog).strip(),
            "",
            "## Lane Guidance",
            "",
            _lane_summary(),
            "",
            "## Risk Guidance",
            "",
            "- low: docs, display-only UI, tests, tiny scoped cleanup",
            "- medium: ordinary source changes with bounded behavior impact",
            "- high: build/test/run, config, scripts, target repo validation, or broader source behavior",
            "- critical: destructive, secrets, DB migrations/data, restore/delete, scheduler, deployment, or unbounded execution",
            "",
            "## Required Output",
            "",
            "Return only a Devo-compatible refined backlog JSON object. Do not wrap it in Markdown.",
            "",
            "Required task fields: id, title, summary, milestone_id, epic_id, lane, risk_level, status, dependencies, acceptance_criteria, validation_expectations, allowed_scope, forbidden_scope, notes, source, created_at, updated_at.",
            "",
            "Use task statuses from: draft, ready, approved, in_progress, blocked, completed, superseded.",
            "Use backlog status draft unless a human explicitly asks for reviewed/approved.",
            "",
            "## Output JSON Example",
            "",
            "```json",
            example.model_dump_json(indent=2),
            "```",
            "",
        ]
    )


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


def _safe_import_task_status(status: str) -> str:
    if status in {"completed", "superseded"}:
        return status
    return "draft"


def _normalize_task_ids(task_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in task_ids:
        for item in raw.split(","):
            cleaned = item.strip().upper()
            if cleaned:
                normalized.append(cleaned)
    return normalized


def _normalize_batch_id(batch_id: str) -> str:
    cleaned = batch_id.strip()
    if cleaned.lower().startswith("batch-"):
        cleaned = cleaned[6:]
    return cleaned.upper()


def _next_batch_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_batch_id(batch.batch_id) for batch in list_project_batches(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"B{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _build_batch_from_tasks(
    *,
    project_name: str,
    batch_id: str,
    title: str,
    tasks: list[BacklogTask],
    backlog: ProjectBacklog,
    source_backlog_reference: str,
    now: datetime,
) -> ProjectBatch:
    task_ids = [task.id for task in tasks]
    dependency_warnings = _batch_dependency_warnings(tasks, backlog)
    return ProjectBatch(
        project=project_name,
        batch_id=batch_id,
        title=title,
        summary=_batch_summary(tasks),
        source_backlog_reference=source_backlog_reference,
        status="draft",
        task_ids=task_ids,
        task_count=len(tasks),
        completed_task_count=sum(1 for task in tasks if task.status == "completed"),
        blocked_task_count=sum(1 for task in tasks if task.status == "blocked"),
        risk_summary=_count_by(tasks, "risk_level"),
        lane_summary=_count_by(tasks, "lane"),
        dependencies=_batch_dependencies(tasks),
        approval_status="not_requested",
        review_notes=[],
        task_snapshots=[_task_snapshot(task) for task in tasks],
        dependency_warnings=dependency_warnings,
        created_at=now,
        updated_at=now,
    )


def _write_project_batch(project_name: str, batch: ProjectBatch, workspace_root: Path | None = None) -> tuple[Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = project_batch_artifact_paths(project_name, batch.batch_id, workspace_root=root)
    _write_model(json_path, batch)
    markdown_path.write_text(render_project_batch_markdown(batch), encoding="utf-8")
    _write_batch_index(project_name, workspace_root=root)
    return json_path, markdown_path


def _write_batch_index(project_name: str, workspace_root: Path | None = None) -> BatchIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batches_dir.mkdir(parents=True, exist_ok=True)
    batches = list_project_batches(project_name, workspace_root=root)
    entries = [
        BatchIndexEntry(
            batch_id=batch.batch_id,
            title=batch.title,
            status=batch.status,
            task_count=batch.task_count,
            approval_status=batch.approval_status,
            path=str(project_batch_artifact_paths(project_name, batch.batch_id, workspace_root=root)[0]),
            updated_at=batch.updated_at,
        )
        for batch in batches
    ]
    index = BatchIndex(project=project_name, batches=entries, updated_at=datetime.now(UTC))
    _write_model(paths.batch_index_json, index)
    return index


def _task_snapshot(task: BacklogTask) -> BatchTaskSnapshot:
    return BatchTaskSnapshot(
        task_id=task.id,
        title=task.title,
        lane=task.lane,
        risk_level=task.risk_level,
        status=task.status,
        dependencies=task.dependencies,
        acceptance_criteria_summary=_summary_list(task.acceptance_criteria),
        validation_expectations_summary=_summary_list(task.validation_expectations),
    )


def _batch_summary(tasks: list[BacklogTask]) -> str:
    if not tasks:
        return "No tasks selected."
    lanes = ", ".join(sorted({task.lane for task in tasks}))
    risks = ", ".join(sorted({task.risk_level for task in tasks}, key=lambda risk: RISK_ORDER.get(risk, 99)))
    return f"Planning batch with {len(tasks)} task(s), lanes: {lanes}, risks: {risks}."


def _count_by(tasks: list[BacklogTask], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(getattr(task, field_name))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _batch_dependencies(tasks: list[BacklogTask]) -> list[str]:
    selected = {task.id.strip().upper() for task in tasks}
    dependencies: set[str] = set()
    for task in tasks:
        for dependency in task.dependencies:
            normalized = dependency.strip().upper()
            if normalized and normalized not in selected:
                dependencies.add(normalized)
    return sorted(dependencies)


def _batch_dependency_warnings(tasks: list[BacklogTask], backlog: ProjectBacklog) -> list[str]:
    selected = {task.id.strip().upper() for task in tasks}
    task_by_id = {task.id.strip().upper(): task for task in backlog.tasks}
    warnings: list[str] = []
    for task in tasks:
        for dependency in task.dependencies:
            normalized = dependency.strip().upper()
            dependency_task = task_by_id.get(normalized)
            if not dependency_task:
                warnings.append(f"{task.id} depends on unknown task {dependency}.")
            elif normalized not in selected:
                warnings.append(f"{task.id} depends on {dependency_task.id}, which is not included in this batch.")
            elif dependency_task.status != "completed" and dependency_task.id != task.id:
                warnings.append(f"{task.id} depends on {dependency_task.id}, which is included but not completed.")
    return warnings


def _suggestion_reason(task: BacklogTask) -> str:
    dependency_text = "dependencies satisfied" if not task.dependencies else "dependencies completed or included"
    return f"{task.status} task, {task.risk_level} risk, {dependency_text}."


def _summary_list(values: list[str]) -> str:
    if not values:
        return ""
    text = "; ".join(values[:3])
    if len(values) > 3:
        text += f"; +{len(values) - 3} more"
    return text


def _lane_summary() -> str:
    lines: list[str] = []
    for lane_id, lane in sorted(BUILT_IN_LANES.items()):
        lines.append(f"- {lane_id}: {lane.name}")
        if lane.default_validation_commands:
            lines.append(f"  - default validation: {', '.join(lane.default_validation_commands)}")
        if lane.notes:
            lines.append(f"  - note: {lane.notes[0]}")
    return "\n".join(lines)


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


def _append_mapping_section(lines: list[str], title: str, values: dict[str, int]) -> None:
    lines.extend([f"## {title}", ""])
    if values:
        for key, value in sorted(values.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("No items recorded.")
    lines.append("")


def _write_model(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _require_project(project_name: str, workspace_root: Path) -> None:
    load_registered_project(project_name, workspace_root=workspace_root)
