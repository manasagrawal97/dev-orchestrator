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
BATCH_APPROVALS_DIR_NAME = "approvals"
QUEUES_DIR_NAME = "queues"
QUEUE_INDEX_JSON = "queue-index.json"
HANDOFFS_DIR_NAME = "handoffs"
HANDOFF_INDEX_JSON = "handoff-index.json"
PLANNING_SCHEMA_VERSION = "1"
ALLOWED_BACKLOG_STATUSES = {"draft", "reviewed", "approved", "superseded"}
ALLOWED_TASK_STATUSES = {"draft", "ready", "approved", "in_progress", "blocked", "completed", "superseded"}
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_BATCH_STATUSES = {"draft", "reviewed", "approved", "in_progress", "completed", "blocked", "superseded"}
ALLOWED_BATCH_APPROVAL_STATUSES = {"not_requested", "requested", "approved", "rejected"}
ALLOWED_BATCH_REVIEW_STATUSES = {"not_reviewed", "reviewed", "needs_changes"}
ALLOWED_QUEUE_STATUSES = {"draft", "ready", "running", "paused_usage_limit", "paused_failure", "waiting_review", "completed", "cancelled", "superseded"}
ALLOWED_QUEUE_ITEM_STATUSES = {"pending", "running", "paused", "blocked", "failed", "completed", "skipped", "superseded"}
PAUSED_QUEUE_STATUSES = {"paused_usage_limit", "paused_failure", "waiting_review"}
ALLOWED_HANDOFF_STATUSES = {"draft", "used", "superseded"}
ALLOWED_HANDOFF_TYPES = {"task", "batch", "queue_next"}
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
    review_status: str = "not_reviewed"
    review_notes: list[str] = Field(default_factory=list)
    task_snapshots: list[BatchTaskSnapshot] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BatchApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    batch_id: str
    approval_status: str = "not_requested"
    review_status: str = "not_reviewed"
    requested_at: datetime | None = None
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    reviewer: str | None = None
    approver: str | None = None
    decision_note: str = ""
    review_notes: list[str] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    risk_summary: dict[str, int] = Field(default_factory=dict)
    lane_summary: dict[str, int] = Field(default_factory=dict)
    task_count: int = 0
    high_risk_task_count: int = 0
    blocked_dependency_count: int = 0
    scope_summary: list[str] = Field(default_factory=list)
    validation_summary: list[str] = Field(default_factory=list)
    next_action: str = ""
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


class PlanningProgressGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str | None = None
    task_count: int = 0
    active_task_count: int = 0
    completed_task_count: int = 0
    blocked_task_count: int = 0
    ready_task_count: int = 0
    approved_task_count: int = 0
    draft_task_count: int = 0
    completion_percent: float = 0.0
    readiness_percent: float = 0.0
    blocked_percent: float = 0.0


class ProjectProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    has_brief: bool = False
    brief_status: str = "missing"
    has_blueprint: bool = False
    blueprint_status: str = "missing"
    has_backlog: bool = False
    backlog_status: str = "missing"
    task_count: int = 0
    completed_task_count: int = 0
    active_task_count: int = 0
    blocked_task_count: int = 0
    approved_task_count: int = 0
    ready_task_count: int = 0
    draft_task_count: int = 0
    project_completion_percent: float = 0.0
    backlog_readiness_percent: float = 0.0
    blocked_percent: float = 0.0
    batch_count: int = 0
    approved_batch_count: int = 0
    completed_batch_count: int = 0
    active_batch_count: int = 0
    batch_completion_percent: float = 0.0
    latest_batch_id: str | None = None
    latest_batch_status: str | None = None
    milestone_progress: list[PlanningProgressGroup] = Field(default_factory=list)
    epic_progress: list[PlanningProgressGroup] = Field(default_factory=list)
    next_action: str = "Create a Project Brief."
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    task_id: str
    title: str
    lane: str
    risk_level: str
    status: str = "pending"
    batch_id: str
    dependencies: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    validation_expectations: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class ExecutionQueue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    queue_id: str
    title: str
    source_batch_id: str
    source_backlog_reference: str
    status: str = "ready"
    items: list[QueueItem] = Field(default_factory=list)
    item_count: int = 0
    pending_count: int = 0
    running_count: int = 0
    completed_count: int = 0
    blocked_count: int = 0
    failed_count: int = 0
    pause_reason: str | None = None
    resume_hint: str | None = None
    current_item_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueueIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_id: str
    title: str
    source_batch_id: str
    status: str
    item_count: int
    pending_count: int
    completed_count: int
    blocked_count: int
    path: str
    updated_at: datetime


class QueueIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    queues: list[QueueIndexEntry] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CodexHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    handoff_id: str
    handoff_type: str
    source_queue_id: str | None = None
    source_batch_id: str | None = None
    source_item_id: str | None = None
    source_task_id: str | None = None
    title: str
    status: str = "draft"
    prompt_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HandoffIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str
    handoff_type: str
    title: str
    status: str
    source_queue_id: str | None = None
    source_batch_id: str | None = None
    source_item_id: str | None = None
    source_task_id: str | None = None
    prompt_path: str
    updated_at: datetime


class HandoffIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PLANNING_SCHEMA_VERSION
    project: str
    handoffs: list[HandoffIndexEntry] = Field(default_factory=list)
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
    backlog_refinement_prompt: Path
    batches_dir: Path
    batch_approvals_dir: Path
    batch_index_json: Path
    queues_dir: Path
    queue_index_json: Path
    handoffs_dir: Path
    handoff_index_json: Path


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
        batch_approvals_dir=planning_dir / BATCHES_DIR_NAME / BATCH_APPROVALS_DIR_NAME,
        batch_index_json=planning_dir / BATCHES_DIR_NAME / BATCH_INDEX_JSON,
        queues_dir=planning_dir / QUEUES_DIR_NAME,
        queue_index_json=planning_dir / QUEUES_DIR_NAME / QUEUE_INDEX_JSON,
        handoffs_dir=planning_dir / HANDOFFS_DIR_NAME,
        handoff_index_json=planning_dir / HANDOFFS_DIR_NAME / HANDOFF_INDEX_JSON,
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


def batch_approval_artifact_paths(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_batch_id(batch_id)
    return paths.batch_approvals_dir / f"batch-{safe_id}-approval.json", paths.batch_approvals_dir / f"batch-{safe_id}-approval.md"


def load_batch_approval(project_name: str, batch_id: str, workspace_root: Path | None = None) -> BatchApproval | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = batch_approval_artifact_paths(project_name, batch_id, workspace_root=root)
    if not json_path.exists():
        return None
    return BatchApproval.model_validate_json(json_path.read_text(encoding="utf-8"))


def list_batch_approvals(project_name: str, workspace_root: Path | None = None) -> list[BatchApproval]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.batch_approvals_dir.exists():
        return []
    approvals: list[BatchApproval] = []
    for path in sorted(paths.batch_approvals_dir.glob("batch-*-approval.json")):
        try:
            approvals.append(BatchApproval.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(approvals, key=lambda approval: approval.updated_at, reverse=True)


def request_batch_approval(
    project_name: str,
    batch_id: str,
    note: str = "",
    reviewer: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    review_notes = list(existing.review_notes if existing else [])
    cleaned = note.strip()
    if cleaned:
        review_notes.append(f"{now.isoformat()}: request: {cleaned}")
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="requested",
        review_status=existing.review_status if existing else "not_reviewed",
        review_notes=review_notes,
        requested_at=now,
        reviewer=reviewer or (existing.reviewer if existing else None),
        now=now,
    )
    updated_batch = batch.model_copy(update={"approval_status": "requested", "updated_at": now})
    _write_project_batch(project_name, updated_batch, workspace_root=root)
    return _write_batch_approval(project_name, approval, workspace_root=root)


def approve_project_batch(
    project_name: str,
    batch_id: str,
    note: str = "",
    approver: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval, Path, Path, bool]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    direct_approval = existing is None or existing.approval_status != "requested"
    review_notes = list(existing.review_notes if existing else [])
    cleaned = note.strip()
    if cleaned:
        review_notes.append(f"{now.isoformat()}: approval: {cleaned}")
    review_status = existing.review_status if existing else batch.review_status
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="approved",
        review_status=review_status if review_status != "not_reviewed" else "reviewed",
        review_notes=review_notes,
        approved_at=now,
        approver=approver or (existing.approver if existing else None),
        decision_note=cleaned or (existing.decision_note if existing else ""),
        now=now,
    )
    updated = batch.model_copy(update={"status": "approved", "approval_status": "approved", "review_status": approval.review_status, "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md, direct_approval


def reject_project_batch(
    project_name: str,
    batch_id: str,
    note: str,
    approver: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    cleaned = note.strip()
    if not cleaned:
        msg = "Decision note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    review_notes = list(existing.review_notes if existing else [])
    review_notes.append(f"{now.isoformat()}: rejection: {cleaned}")
    approval = _build_batch_approval(
        batch,
        existing=existing,
        approval_status="rejected",
        review_status="needs_changes",
        review_notes=review_notes,
        rejected_at=now,
        approver=approver or (existing.approver if existing else None),
        decision_note=cleaned,
        now=now,
    )
    updated = batch.model_copy(update={"approval_status": "rejected", "review_status": "needs_changes", "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md


def review_project_batch(
    project_name: str,
    batch_id: str,
    note: str,
    needs_changes: bool = False,
    reviewer: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[ProjectBatch, Path, Path, BatchApproval | None, Path | None, Path | None]:
    root = workspace_root or get_workspace_root()
    batch = _require_batch(project_name, batch_id, root)
    cleaned = note.strip()
    if not cleaned:
        msg = "Review note must not be empty."
        raise ValueError(msg)
    now = datetime.now(UTC)
    notes = [*batch.review_notes, f"{now.isoformat()}: {cleaned}"]
    review_status = "needs_changes" if needs_changes else "reviewed"
    status = "reviewed" if batch.status == "draft" and not needs_changes else batch.status
    updated = batch.model_copy(update={"status": status, "review_status": review_status, "review_notes": notes, "updated_at": now})
    json_path, markdown_path = _write_project_batch(project_name, updated, workspace_root=root)
    existing = load_batch_approval(project_name, batch.batch_id, workspace_root=root)
    if not existing:
        return updated, json_path, markdown_path, None, None, None
    approval = _build_batch_approval(
        updated,
        existing=existing,
        approval_status=existing.approval_status,
        review_status=review_status,
        review_notes=notes,
        reviewed_at=now,
        reviewer=reviewer or existing.reviewer,
        now=now,
    )
    approval, approval_json, approval_md = _write_batch_approval(project_name, approval, workspace_root=root)
    return updated, json_path, markdown_path, approval, approval_json, approval_md


def project_batch_artifact_paths(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_batch_id(batch_id)
    return paths.batches_dir / f"batch-{safe_id}.json", paths.batches_dir / f"batch-{safe_id}.md"


def calculate_project_progress(project_name: str, workspace_root: Path | None = None) -> ProjectProgress:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    brief = load_project_brief(project_name, workspace_root=root)
    blueprint = load_project_blueprint(project_name, workspace_root=root)
    backlog = load_project_backlog(project_name, workspace_root=root)
    batches = list_project_batches(project_name, workspace_root=root)
    tasks = backlog.tasks if backlog else []
    active_tasks = [task for task in tasks if task.status != "superseded"]
    active_task_count = len(active_tasks)
    completed_task_count = sum(1 for task in active_tasks if task.status == "completed")
    blocked_task_count = sum(1 for task in active_tasks if task.status == "blocked")
    approved_task_count = sum(1 for task in active_tasks if task.status == "approved")
    ready_task_count = sum(1 for task in active_tasks if task.status == "ready")
    draft_task_count = sum(1 for task in active_tasks if task.status == "draft")
    ready_like_count = sum(1 for task in active_tasks if task.status in {"ready", "approved", "completed"})
    active_batches = [batch for batch in batches if batch.status != "superseded"]
    latest_batch = batches[0] if batches else None
    warnings = _progress_warnings(brief, blueprint, backlog, active_tasks, batches)
    return ProjectProgress(
        project=project_name,
        has_brief=brief is not None,
        brief_status=brief.status if brief else "missing",
        has_blueprint=blueprint is not None,
        blueprint_status=blueprint.status if blueprint else "missing",
        has_backlog=backlog is not None,
        backlog_status=backlog.status if backlog else "missing",
        task_count=len(tasks),
        completed_task_count=completed_task_count,
        active_task_count=active_task_count,
        blocked_task_count=blocked_task_count,
        approved_task_count=approved_task_count,
        ready_task_count=ready_task_count,
        draft_task_count=draft_task_count,
        project_completion_percent=_percent(completed_task_count, active_task_count),
        backlog_readiness_percent=_percent(ready_like_count, active_task_count),
        blocked_percent=_percent(blocked_task_count, active_task_count),
        batch_count=len(batches),
        approved_batch_count=sum(1 for batch in active_batches if batch.approval_status == "approved"),
        completed_batch_count=sum(1 for batch in active_batches if batch.status == "completed"),
        active_batch_count=len(active_batches),
        batch_completion_percent=_percent(sum(1 for batch in active_batches if batch.status == "completed"), len(active_batches)),
        latest_batch_id=latest_batch.batch_id if latest_batch else None,
        latest_batch_status=latest_batch.status if latest_batch else None,
        milestone_progress=_aggregate_progress_groups(active_tasks, blueprint.milestones if blueprint else [], "milestone_id"),
        epic_progress=_aggregate_progress_groups(active_tasks, blueprint.epics if blueprint else [], "epic_id"),
        next_action=_progress_next_action(project_name, brief, blueprint, backlog, batches),
        warnings=warnings,
        generated_at=datetime.now(UTC),
    )


def render_project_progress_markdown(progress: ProjectProgress) -> str:
    lines = [
        f"# Project Progress: {progress.project}",
        "",
        f"- Generated: `{progress.generated_at.isoformat()}`",
        f"- Brief: `{progress.brief_status}`",
        f"- Blueprint: `{progress.blueprint_status}`",
        f"- Backlog: `{progress.backlog_status}`",
        f"- Tasks: `{progress.task_count}`",
        f"- Active tasks: `{progress.active_task_count}`",
        f"- Completed tasks: `{progress.completed_task_count}`",
        f"- Blocked tasks: `{progress.blocked_task_count}`",
        f"- Project completion: `{progress.project_completion_percent:.1f}%`",
        f"- Backlog readiness: `{progress.backlog_readiness_percent:.1f}%`",
        f"- Blocked: `{progress.blocked_percent:.1f}%`",
        f"- Batches: `{progress.batch_count}`",
        f"- Approved batches: `{progress.approved_batch_count}`",
        f"- Completed batches: `{progress.completed_batch_count}`",
        f"- Batch completion: `{progress.batch_completion_percent:.1f}%`",
        f"- Latest batch: `{progress.latest_batch_id or 'none'}`",
        f"- Latest batch status: `{progress.latest_batch_status or 'none'}`",
        "",
        "## Next Action",
        "",
        progress.next_action,
        "",
    ]
    _append_list_section(lines, "Warnings", progress.warnings)
    lines.extend(["## Milestone Progress", ""])
    _append_progress_groups(lines, progress.milestone_progress)
    lines.extend(["## Epic Progress", ""])
    _append_progress_groups(lines, progress.epic_progress)
    return "\n".join(lines).rstrip() + "\n"


def create_execution_queue_from_batch(
    project_name: str,
    batch_id: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    if batch.approval_status != "approved" or batch.status not in {"approved", "in_progress", "completed"}:
        msg = f"Project batch must be approved before queue creation: {batch.batch_id}"
        raise ValueError(msg)
    queue_id = _next_queue_id(project_name, workspace_root=root)
    now = datetime.now(UTC)
    items = [
        QueueItem(
            item_id=f"QI{index:03d}",
            task_id=task.task_id,
            title=task.title,
            lane=task.lane,
            risk_level=task.risk_level,
            status="pending",
            batch_id=batch.batch_id,
            dependencies=task.dependencies,
            acceptance_criteria=[task.acceptance_criteria_summary] if task.acceptance_criteria_summary else [],
            validation_expectations=[task.validation_expectations_summary] if task.validation_expectations_summary else [],
        )
        for index, task in enumerate(batch.task_snapshots, start=1)
    ]
    queue = _with_queue_counts(
        ExecutionQueue(
            project=project_name,
            queue_id=queue_id,
            title=f"Execution queue for {batch.title}",
            source_batch_id=batch.batch_id,
            source_backlog_reference=batch.source_backlog_reference,
            status="ready",
            items=items,
            pause_reason=None,
            resume_hint="Start the queue when ready, then generate a Codex handoff prompt with devo project handoff-next.",
            current_item_id=None,
            created_at=now,
            updated_at=now,
        )
    )
    return _write_execution_queue(project_name, queue, workspace_root=root)


def list_execution_queues(project_name: str, workspace_root: Path | None = None) -> list[ExecutionQueue]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    paths = planning_artifact_paths(project_name, workspace_root=root)
    if not paths.queues_dir.exists():
        return []
    queues: list[ExecutionQueue] = []
    for path in sorted(paths.queues_dir.glob("queue-*.json")):
        if path.name == QUEUE_INDEX_JSON:
            continue
        try:
            queues.append(ExecutionQueue.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    return sorted(queues, key=lambda queue: queue.updated_at, reverse=True)


def load_queue_index(project_name: str, workspace_root: Path | None = None) -> QueueIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.queue_index_json.exists():
        return QueueIndex(project=project_name)
    return QueueIndex.model_validate_json(paths.queue_index_json.read_text(encoding="utf-8"))


def load_handoff_index(project_name: str, workspace_root: Path | None = None) -> HandoffIndex:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    if not paths.handoff_index_json.exists():
        return HandoffIndex(project=project_name)
    return HandoffIndex.model_validate_json(paths.handoff_index_json.read_text(encoding="utf-8"))


def load_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> ExecutionQueue | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _markdown_path = queue_artifact_paths(project_name, queue_id, workspace_root=root)
    if not json_path.exists():
        return None
    return ExecutionQueue.model_validate_json(json_path.read_text(encoding="utf-8"))


def load_codex_handoff(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> CodexHandoff | None:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    json_path, _prompt_path = handoff_artifact_paths(project_name, handoff_id, workspace_root=root)
    if not json_path.exists():
        return None
    return CodexHandoff.model_validate_json(json_path.read_text(encoding="utf-8"))


def start_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    if queue.status not in {"draft", "ready", *PAUSED_QUEUE_STATUSES}:
        msg = f"Queue cannot be started from status: {queue.status}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [item.model_copy() for item in queue.items]
    current_item_id = queue.current_item_id if _find_queue_item(items, queue.current_item_id) else None
    running_item = next((item for item in items if item.status == "running"), None)
    if running_item:
        current_item_id = running_item.item_id
    elif current_item_id:
        current = _find_queue_item(items, current_item_id)
        if current and current.status in {"pending", "paused", "blocked"}:
            replacement = current.model_copy(update={"status": "running", "started_at": current.started_at or now})
            _replace_queue_item(items, replacement)
            current_item_id = replacement.item_id
    elif not current_item_id:
        next_item = next((item for item in items if item.status == "pending"), None)
        if next_item:
            replacement = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, replacement)
            current_item_id = replacement.item_id
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": "running" if current_item_id else "completed",
                "items": items,
                "pause_reason": None,
                "resume_hint": "Queue is running. Generate a Codex handoff prompt with devo project handoff-next.",
                "current_item_id": current_item_id,
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def get_queue_next_item(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, QueueItem | None]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    current = _find_queue_item(queue.items, queue.current_item_id)
    if current and current.status == "running":
        return queue, current
    pending = next((item for item in queue.items if item.status == "pending"), None)
    return queue, pending


def complete_queue_item(
    project_name: str,
    queue_id: str,
    item_id: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    now = datetime.now(UTC)
    item = _require_queue_item(queue, item_id)
    notes = _append_note(item.notes, note, now)
    completed = item.model_copy(update={"status": "completed", "completed_at": now, "notes": notes})
    items = [entry.model_copy() for entry in queue.items]
    _replace_queue_item(items, completed)
    current_item_id: str | None = None
    status = queue.status
    if status == "running":
        next_item = next((entry for entry in items if entry.status == "pending"), None)
        if next_item:
            running = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, running)
            current_item_id = running.item_id
        else:
            status = "completed"
    elif all(entry.status in {"completed", "skipped", "superseded"} for entry in items):
        status = "completed"
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "current_item_id": current_item_id,
                "pause_reason": None if status == "completed" else queue.pause_reason,
                "resume_hint": "Queue completed." if status == "completed" else queue.resume_hint,
                "updated_at": now,
            }
        )
    )
    _update_backlog_task_status(project_name, item.task_id, "completed", workspace_root=root)
    return _write_execution_queue(project_name, updated, workspace_root=root)


def block_queue_item(
    project_name: str,
    queue_id: str,
    item_id: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    now = datetime.now(UTC)
    item = _require_queue_item(queue, item_id)
    notes = _append_note(item.notes, note, now)
    blocked = item.model_copy(update={"status": "blocked", "notes": notes})
    items = [entry.model_copy() for entry in queue.items]
    _replace_queue_item(items, blocked)
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": "waiting_review",
                "items": items,
                "pause_reason": "blocked_item",
                "resume_hint": f"Review blocked item {blocked.item_id}; generate a new handoff only after the blocker is resolved.",
                "current_item_id": blocked.item_id,
                "updated_at": now,
            }
        )
    )
    _update_backlog_task_status(project_name, item.task_id, "blocked", workspace_root=root)
    return _write_execution_queue(project_name, updated, workspace_root=root)


def pause_execution_queue(
    project_name: str,
    queue_id: str,
    reason: str,
    note: str,
    workspace_root: Path | None = None,
) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    normalized_reason = reason.strip().lower()
    if normalized_reason == "usage_limit":
        status = "paused_usage_limit"
    elif normalized_reason == "failure":
        status = "paused_failure"
    elif normalized_reason in {"review", "manual"}:
        status = "waiting_review"
    else:
        msg = "Pause reason must be one of: usage_limit, failure, review, manual."
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [entry.model_copy() for entry in queue.items]
    current = _find_queue_item(items, queue.current_item_id)
    if current and current.status == "running":
        _replace_queue_item(items, current.model_copy(update={"status": "paused"}))
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "pause_reason": normalized_reason,
                "resume_hint": note.strip() or f"Resume when {normalized_reason} is resolved.",
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def resume_execution_queue(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue = _require_queue(project_name, queue_id, root)
    if queue.status not in PAUSED_QUEUE_STATUSES:
        msg = f"Queue cannot be resumed from status: {queue.status}"
        raise ValueError(msg)
    now = datetime.now(UTC)
    items = [entry.model_copy() for entry in queue.items]
    current_item_id = queue.current_item_id
    current = _find_queue_item(items, current_item_id)
    if current and current.status in {"paused", "blocked"}:
        running = current.model_copy(update={"status": "running", "started_at": current.started_at or now})
        _replace_queue_item(items, running)
        current_item_id = running.item_id
    elif not current_item_id:
        next_item = next((entry for entry in items if entry.status == "pending"), None)
        if next_item:
            running = next_item.model_copy(update={"status": "running", "started_at": next_item.started_at or now})
            _replace_queue_item(items, running)
            current_item_id = running.item_id
    status = "running" if current_item_id else "completed"
    updated = _with_queue_counts(
        queue.model_copy(
            update={
                "status": status,
                "items": items,
                "pause_reason": None,
                "resume_hint": "Queue resumed. Generate a Codex handoff prompt with devo project handoff-next.",
                "current_item_id": current_item_id,
                "updated_at": now,
            }
        )
    )
    return _write_execution_queue(project_name, updated, workspace_root=root)


def queue_artifact_paths(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_queue_id(queue_id)
    return paths.queues_dir / f"queue-{safe_id}.json", paths.queues_dir / f"queue-{safe_id}.md"


def handoff_artifact_paths(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    paths = planning_artifact_paths(project_name, workspace_root=workspace_root)
    safe_id = _normalize_handoff_id(handoff_id)
    return paths.handoffs_dir / f"handoff-{safe_id}.json", paths.handoffs_dir / f"handoff-{safe_id}.md"


def create_codex_handoff_for_queue_next(project_name: str, queue_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    queue, item = get_queue_next_item(project_name, queue_id, workspace_root=root)
    if queue.status == "completed":
        msg = f"Execution queue is completed: {queue.queue_id}"
        raise ValueError(msg)
    if not item:
        msg = f"Execution queue has no running or pending item: {queue.queue_id}"
        raise ValueError(msg)
    task = _try_get_backlog_task(project_name, item.task_id, root)
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        queue=queue,
        queue_item=item,
        task=task,
        batch=load_project_batch(project_name, queue.source_batch_id, workspace_root=root),
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="queue_next",
        title=f"{item.task_id}: {item.title}",
        prompt=prompt,
        source_queue_id=queue.queue_id,
        source_batch_id=queue.source_batch_id,
        source_item_id=item.item_id,
        source_task_id=item.task_id,
        workspace_root=root,
    )


def create_codex_handoff_for_task(project_name: str, task_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    task = get_backlog_task(project_name, task_id, workspace_root=root)
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="task",
        title=f"{task.id}: {task.title}",
        task=task,
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="task",
        title=f"{task.id}: {task.title}",
        prompt=prompt,
        source_task_id=task.id,
        workspace_root=root,
    )


def create_codex_handoff_for_batch(project_name: str, batch_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    batch = load_project_batch(project_name, batch_id, workspace_root=root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    tasks = [_try_get_backlog_task(project_name, task_id, root) for task_id in batch.task_ids]
    prompt = render_codex_handoff_prompt(
        project_name,
        handoff_type="batch",
        title=f"{batch.batch_id}: {batch.title}",
        batch=batch,
        tasks=[task for task in tasks if task],
        workspace_root=root,
    )
    return _write_codex_handoff(
        project_name,
        handoff_type="batch",
        title=f"{batch.batch_id}: {batch.title}",
        prompt=prompt,
        source_batch_id=batch.batch_id,
        workspace_root=root,
    )


def list_codex_handoffs(project_name: str, workspace_root: Path | None = None) -> list[CodexHandoff]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    index = load_handoff_index(project_name, workspace_root=root)
    handoffs: list[CodexHandoff] = []
    for entry in index.handoffs:
        handoff = load_codex_handoff(project_name, entry.handoff_id, workspace_root=root)
        if handoff:
            handoffs.append(handoff)
    return sorted(handoffs, key=lambda item: item.updated_at, reverse=True)


def mark_codex_handoff_used(project_name: str, handoff_id: str, workspace_root: Path | None = None) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    handoff = load_codex_handoff(project_name, handoff_id, workspace_root=root)
    if not handoff:
        msg = f"Codex handoff not found: {handoff_id}"
        raise ValueError(msg)
    updated = handoff.model_copy(update={"status": "used", "updated_at": datetime.now(UTC)})
    return _write_codex_handoff_model(project_name, updated, workspace_root=root)


def render_codex_handoff_prompt(
    project_name: str,
    *,
    handoff_type: str,
    title: str,
    workspace_root: Path | None = None,
    queue: ExecutionQueue | None = None,
    queue_item: QueueItem | None = None,
    task: BacklogTask | None = None,
    batch: ProjectBatch | None = None,
    tasks: list[BacklogTask] | None = None,
) -> str:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    selected_tasks = tasks or ([task] if task else [])
    lane = queue_item.lane if queue_item else (task.lane if task else _summarize_batch_dict(batch.lane_summary if batch else {}, "unknown"))
    risk = queue_item.risk_level if queue_item else (task.risk_level if task else _summarize_batch_dict(batch.risk_summary if batch else {}, "unknown"))
    dependencies = queue_item.dependencies if queue_item else (task.dependencies if task else (batch.dependencies if batch else []))
    acceptance = queue_item.acceptance_criteria if queue_item else (task.acceptance_criteria if task else _batch_acceptance(batch, selected_tasks))
    validation = queue_item.validation_expectations if queue_item else (task.validation_expectations if task else _batch_validation(batch, selected_tasks))
    allowed_scope = task.allowed_scope if task else _collect_task_scope(selected_tasks, "allowed")
    forbidden_scope = task.forbidden_scope if task else _collect_task_scope(selected_tasks, "forbidden")
    lines = [
        f"# Codex Handoff: {title}",
        "",
        "Continue DevOrchestrator-managed project work using this generated Devo handoff prompt.",
        "",
        "## Project",
        "",
        f"- Project: `{project_name}`",
        f"- Target repo path: `{registration.path}`",
        f"- Handoff type: `{handoff_type}`",
        f"- Lane: `{lane}`",
        f"- Risk level: `{risk}`",
        "",
        "## Devo Context",
        "",
        "- Devo is the workflow controller for planning, scope, queue state, validation records, and delivery reports.",
        "- This prompt is a handoff artifact only. Devo is not invoking Codex or an AI API automatically.",
        "- Execute only the selected task or approved batch scope described below.",
        "",
    ]
    if queue:
        lines.extend(
            [
                "## Source Queue",
                "",
                f"- Queue id: `{queue.queue_id}`",
                f"- Queue status: `{queue.status}`",
                f"- Source batch: `{queue.source_batch_id}`",
                f"- Current item: `{queue.current_item_id or 'none'}`",
                "",
            ]
        )
    if queue_item:
        lines.extend(
            [
                "## Queue Item",
                "",
                f"- Item id: `{queue_item.item_id}`",
                f"- Task id: `{queue_item.task_id}`",
                f"- Title: {queue_item.title}",
                f"- Status: `{queue_item.status}`",
                "",
            ]
        )
    if batch:
        lines.extend(
            [
                "## Source Batch",
                "",
                f"- Batch id: `{batch.batch_id}`",
                f"- Title: {batch.title}",
                f"- Status: `{batch.status}`",
                f"- Approval status: `{batch.approval_status}`",
                f"- Task count: `{batch.task_count}`",
                "",
            ]
        )
        if batch.task_snapshots:
            lines.extend(["### Batch Tasks", ""])
            for snapshot in batch.task_snapshots:
                lines.append(f"- `{snapshot.task_id}` {snapshot.title} ({snapshot.lane}, {snapshot.risk_level})")
            lines.append("")
    if task:
        lines.extend(_task_prompt_section(task))
    elif selected_tasks:
        for selected in selected_tasks:
            lines.extend(_task_prompt_section(selected))
    lines.extend(
        [
            "## Dependencies",
            "",
            *_bullet_lines(dependencies, "No dependencies recorded."),
            "",
            "## Acceptance Criteria",
            "",
            *_bullet_lines(acceptance, "No acceptance criteria recorded."),
            "",
            "## Validation Expectations",
            "",
            *_bullet_lines(validation, "No validation expectations recorded. Use the project's approved validation method only."),
            "",
            "## Allowed Scope",
            "",
            *_bullet_lines(allowed_scope, "Only the task or batch scope described in this handoff."),
            "",
            "## Forbidden Scope",
            "",
            *_bullet_lines(
                forbidden_scope,
                "Do not modify unrelated files, generated artifacts, secrets, local settings, backups, database files, migrations, or scripts.",
            ),
            "",
            "## Safety Boundaries",
            "",
            "- Do not exceed this task/batch scope.",
            "- Do not touch PersonalOS unless the selected project is PersonalOS and the task explicitly says so.",
            "- Do not commit generated workspace artifacts.",
            "- Do not stage workspace/, ui/node_modules/, ui/dist/, .venv/, .env, .pytest_cache/, or pt-* folders.",
            "- Do not run backup/restore, scheduler modification, destructive commands, or target project commands unless explicitly approved for this handoff.",
            "- Do not add AI API/model integration or invoke Codex CLI automation automatically.",
            "- Ask for explicit trusted approval if a safety gate blocks the edit.",
            "",
            "## Required Validation Instructions",
            "",
            "- Run only validation that is approved for this task/batch.",
            "- Record skipped validation honestly when approval is absent or unsafe.",
            "- Run diff checks before staging if source files change.",
            "- Do not fabricate validation, review, audit, commit, or push evidence.",
            "",
            "## Expected Final Report",
            "",
            "- Changed files",
            "- Implementation summary",
            "- Validation performed and results",
            "- Devo artifacts generated or updated",
            "- Commit hash and push result, if delivery is approved",
            "- Final source repo status",
            "- Confirmation generated workspace artifacts were not committed",
            "",
        ]
    )
    return "\n".join(lines)


def render_execution_queue_markdown(queue: ExecutionQueue) -> str:
    lines = [
        f"# {queue.title}",
        "",
        f"- Project: `{queue.project}`",
        f"- Queue id: `{queue.queue_id}`",
        f"- Source batch: `{queue.source_batch_id}`",
        f"- Status: `{queue.status}`",
        f"- Current item: `{queue.current_item_id or 'none'}`",
        f"- Items: `{queue.item_count}`",
        f"- Pending: `{queue.pending_count}`",
        f"- Running: `{queue.running_count}`",
        f"- Completed: `{queue.completed_count}`",
        f"- Blocked: `{queue.blocked_count}`",
        f"- Failed: `{queue.failed_count}`",
        f"- Pause reason: `{queue.pause_reason or 'none'}`",
        f"- Resume hint: {queue.resume_hint or 'none'}",
        f"- Created: `{queue.created_at.isoformat()}`",
        f"- Updated: `{queue.updated_at.isoformat()}`",
        "",
        "## Items",
        "",
    ]
    if not queue.items:
        lines.extend(["No queue items recorded.", ""])
    for item in queue.items:
        lines.extend(
            [
                f"### {item.item_id}: {item.title}",
                "",
                f"- Task: `{item.task_id}`",
                f"- Status: `{item.status}`",
                f"- Lane: `{item.lane}`",
                f"- Risk: `{item.risk_level}`",
                f"- Dependencies: `{', '.join(item.dependencies) if item.dependencies else 'none'}`",
                f"- Started: `{item.started_at.isoformat() if item.started_at else 'none'}`",
                f"- Completed: `{item.completed_at.isoformat() if item.completed_at else 'none'}`",
                "",
            ]
        )
        _append_list_section(lines, "Acceptance Criteria", item.acceptance_criteria)
        _append_list_section(lines, "Validation Expectations", item.validation_expectations)
        _append_list_section(lines, "Notes", item.notes)
    lines.extend(
        [
            "## Safety Note",
            "",
            "Execution queue state is tracking only. Devo does not run Codex, run validation, commit, push, or modify target repositories from this queue.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_project_batch_markdown(batch: ProjectBatch) -> str:
    lines = [
        f"# {batch.title}",
        "",
        f"- Project: `{batch.project}`",
        f"- Batch id: `{batch.batch_id}`",
        f"- Status: `{batch.status}`",
        f"- Approval status: `{batch.approval_status}`",
        f"- Review status: `{batch.review_status}`",
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


def render_batch_approval_markdown(approval: BatchApproval) -> str:
    lines = [
        f"# Batch Approval: {approval.batch_id}",
        "",
        f"- Project: `{approval.project}`",
        f"- Batch id: `{approval.batch_id}`",
        f"- Approval status: `{approval.approval_status}`",
        f"- Review status: `{approval.review_status}`",
        f"- Requested at: `{approval.requested_at.isoformat() if approval.requested_at else 'none'}`",
        f"- Reviewed at: `{approval.reviewed_at.isoformat() if approval.reviewed_at else 'none'}`",
        f"- Approved at: `{approval.approved_at.isoformat() if approval.approved_at else 'none'}`",
        f"- Rejected at: `{approval.rejected_at.isoformat() if approval.rejected_at else 'none'}`",
        f"- Reviewer: `{approval.reviewer or 'none'}`",
        f"- Approver: `{approval.approver or 'none'}`",
        f"- Task count: `{approval.task_count}`",
        f"- High-risk tasks: `{approval.high_risk_task_count}`",
        f"- Blocked dependencies: `{approval.blocked_dependency_count}`",
        f"- Updated: `{approval.updated_at.isoformat()}`",
        "",
        "## Decision Note",
        "",
        approval.decision_note or "No decision note recorded.",
        "",
    ]
    _append_mapping_section(lines, "Risk Summary", approval.risk_summary)
    _append_mapping_section(lines, "Lane Summary", approval.lane_summary)
    _append_list_section(lines, "Scope Summary", approval.scope_summary)
    _append_list_section(lines, "Validation Summary", approval.validation_summary)
    _append_list_section(lines, "Dependency Warnings", approval.dependency_warnings)
    _append_list_section(lines, "Review Notes", approval.review_notes)
    lines.extend(
        [
            "## Next Action",
            "",
            approval.next_action or "No next action recorded.",
            "",
            "## Safety Note",
            "",
            "Batch approval is planning approval only. It does not create a queue, run Codex, execute target commands, run validation, commit, push, restore backups, or modify target repositories.",
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


def _normalize_queue_id(queue_id: str) -> str:
    cleaned = queue_id.strip()
    if cleaned.lower().startswith("queue-"):
        cleaned = cleaned[6:]
    return cleaned.upper()


def _normalize_handoff_id(handoff_id: str) -> str:
    cleaned = handoff_id.strip()
    if cleaned.lower().startswith("handoff-"):
        cleaned = cleaned[8:]
    return cleaned.upper()


def _next_batch_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_batch_id(batch.batch_id) for batch in list_project_batches(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"B{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_queue_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_queue_id(queue.queue_id) for queue in list_execution_queues(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"Q{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1


def _next_handoff_id(project_name: str, workspace_root: Path | None = None) -> str:
    existing = {_normalize_handoff_id(handoff.handoff_id) for handoff in list_codex_handoffs(project_name, workspace_root=workspace_root)}
    index = 1
    while True:
        candidate = f"H{index:03d}"
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


def _write_batch_approval(project_name: str, approval: BatchApproval, workspace_root: Path | None = None) -> tuple[BatchApproval, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.batch_approvals_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = batch_approval_artifact_paths(project_name, approval.batch_id, workspace_root=root)
    _write_model(json_path, approval)
    markdown_path.write_text(render_batch_approval_markdown(approval), encoding="utf-8")
    return approval, json_path, markdown_path


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


def _write_execution_queue(project_name: str, queue: ExecutionQueue, workspace_root: Path | None = None) -> tuple[ExecutionQueue, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queues_dir.mkdir(parents=True, exist_ok=True)
    queue = _with_queue_counts(queue)
    json_path, markdown_path = queue_artifact_paths(project_name, queue.queue_id, workspace_root=root)
    _write_model(json_path, queue)
    markdown_path.write_text(render_execution_queue_markdown(queue), encoding="utf-8")
    _write_queue_index(project_name, workspace_root=root)
    return queue, json_path, markdown_path


def _write_queue_index(project_name: str, workspace_root: Path | None = None) -> QueueIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.queues_dir.mkdir(parents=True, exist_ok=True)
    queues = list_execution_queues(project_name, workspace_root=root)
    entries = [
        QueueIndexEntry(
            queue_id=queue.queue_id,
            title=queue.title,
            source_batch_id=queue.source_batch_id,
            status=queue.status,
            item_count=queue.item_count,
            pending_count=queue.pending_count,
            completed_count=queue.completed_count,
            blocked_count=queue.blocked_count,
            path=str(queue_artifact_paths(project_name, queue.queue_id, workspace_root=root)[0]),
            updated_at=queue.updated_at,
        )
        for queue in queues
    ]
    index = QueueIndex(project=project_name, queues=entries, updated_at=datetime.now(UTC))
    _write_model(paths.queue_index_json, index)
    return index


def _write_codex_handoff(
    project_name: str,
    *,
    handoff_type: str,
    title: str,
    prompt: str,
    workspace_root: Path | None = None,
    source_queue_id: str | None = None,
    source_batch_id: str | None = None,
    source_item_id: str | None = None,
    source_task_id: str | None = None,
) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    _require_project(project_name, root)
    normalized_type = handoff_type.strip().lower()
    if normalized_type not in ALLOWED_HANDOFF_TYPES:
        msg = f"Invalid handoff type: {handoff_type}"
        raise ValueError(msg)
    handoff_id = _next_handoff_id(project_name, workspace_root=root)
    _json_path, prompt_path = handoff_artifact_paths(project_name, handoff_id, workspace_root=root)
    now = datetime.now(UTC)
    handoff = CodexHandoff(
        project=project_name,
        handoff_id=handoff_id,
        handoff_type=normalized_type,
        source_queue_id=source_queue_id,
        source_batch_id=source_batch_id,
        source_item_id=source_item_id,
        source_task_id=source_task_id,
        title=title,
        status="draft",
        prompt_path=str(prompt_path),
        created_at=now,
        updated_at=now,
    )
    return _write_codex_handoff_model(project_name, handoff, prompt=prompt, workspace_root=root)


def _write_codex_handoff_model(
    project_name: str,
    handoff: CodexHandoff,
    *,
    prompt: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[CodexHandoff, Path, Path]:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)
    if handoff.status not in ALLOWED_HANDOFF_STATUSES:
        msg = f"Invalid handoff status: {handoff.status}"
        raise ValueError(msg)
    json_path, prompt_path = handoff_artifact_paths(project_name, handoff.handoff_id, workspace_root=root)
    updated = handoff.model_copy(update={"prompt_path": str(prompt_path), "updated_at": handoff.updated_at})
    _write_model(json_path, updated)
    if prompt is not None:
        prompt_path.write_text(prompt, encoding="utf-8")
    elif not prompt_path.exists():
        prompt_path.write_text(f"# Codex Handoff: {updated.title}\n\nPrompt content is unavailable.\n", encoding="utf-8")
    _write_handoff_index(project_name, workspace_root=root)
    return updated, json_path, prompt_path


def _write_handoff_index(project_name: str, workspace_root: Path | None = None) -> HandoffIndex:
    root = workspace_root or get_workspace_root()
    paths = planning_artifact_paths(project_name, workspace_root=root)
    paths.handoffs_dir.mkdir(parents=True, exist_ok=True)
    handoffs = []
    for path in sorted(paths.handoffs_dir.glob("handoff-*.json")):
        if path.name == HANDOFF_INDEX_JSON:
            continue
        try:
            handoffs.append(CodexHandoff.model_validate_json(path.read_text(encoding="utf-8")))
        except (ValueError, ValidationError):
            continue
    handoffs = sorted(handoffs, key=lambda item: item.updated_at, reverse=True)
    entries = [
        HandoffIndexEntry(
            handoff_id=handoff.handoff_id,
            handoff_type=handoff.handoff_type,
            title=handoff.title,
            status=handoff.status,
            source_queue_id=handoff.source_queue_id,
            source_batch_id=handoff.source_batch_id,
            source_item_id=handoff.source_item_id,
            source_task_id=handoff.source_task_id,
            prompt_path=handoff.prompt_path,
            updated_at=handoff.updated_at,
        )
        for handoff in handoffs
    ]
    index = HandoffIndex(project=project_name, handoffs=entries, updated_at=datetime.now(UTC))
    _write_model(paths.handoff_index_json, index)
    return index


def _with_queue_counts(queue: ExecutionQueue) -> ExecutionQueue:
    items = queue.items
    return queue.model_copy(
        update={
            "item_count": len(items),
            "pending_count": sum(1 for item in items if item.status == "pending"),
            "running_count": sum(1 for item in items if item.status == "running"),
            "completed_count": sum(1 for item in items if item.status == "completed"),
            "blocked_count": sum(1 for item in items if item.status == "blocked"),
            "failed_count": sum(1 for item in items if item.status == "failed"),
        }
    )


def _require_queue(project_name: str, queue_id: str, workspace_root: Path) -> ExecutionQueue:
    queue = load_execution_queue(project_name, queue_id, workspace_root=workspace_root)
    if not queue:
        msg = f"Execution queue not found: {queue_id}"
        raise ValueError(msg)
    return queue


def _require_queue_item(queue: ExecutionQueue, item_id: str) -> QueueItem:
    normalized = item_id.strip().upper()
    for item in queue.items:
        if item.item_id.upper() == normalized:
            return item
    msg = f"Queue item not found: {item_id}"
    raise ValueError(msg)


def _find_queue_item(items: list[QueueItem], item_id: str | None) -> QueueItem | None:
    if not item_id:
        return None
    normalized = item_id.strip().upper()
    return next((item for item in items if item.item_id.upper() == normalized), None)


def _replace_queue_item(items: list[QueueItem], replacement: QueueItem) -> None:
    for index, item in enumerate(items):
        if item.item_id.upper() == replacement.item_id.upper():
            items[index] = replacement
            return


def _append_note(notes: list[str], note: str, timestamp: datetime) -> list[str]:
    cleaned = note.strip()
    if not cleaned:
        cleaned = "No note provided."
    return [*notes, f"{timestamp.isoformat()}: {cleaned}"]


def _update_backlog_task_status(project_name: str, task_id: str, status: str, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    backlog = load_project_backlog(project_name, workspace_root=root)
    if not backlog:
        return
    now = datetime.now(UTC)
    updated_tasks: list[BacklogTask] = []
    changed = False
    normalized = task_id.strip().upper()
    for task in backlog.tasks:
        if task.id.strip().upper() == normalized:
            updated_tasks.append(task.model_copy(update={"status": status, "updated_at": now}))
            changed = True
        else:
            updated_tasks.append(task)
    if not changed:
        return
    updated = _with_backlog_counts(backlog.model_copy(update={"tasks": updated_tasks, "updated_at": now}))
    paths = planning_artifact_paths(project_name, workspace_root=root)
    _write_model(paths.backlog_json, updated)
    paths.backlog_markdown.write_text(render_project_backlog_markdown(updated), encoding="utf-8")


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


def _require_batch(project_name: str, batch_id: str, workspace_root: Path) -> ProjectBatch:
    batch = load_project_batch(project_name, batch_id, workspace_root=workspace_root)
    if not batch:
        msg = f"Project batch not found: {batch_id}"
        raise ValueError(msg)
    return batch


def _build_batch_approval(
    batch: ProjectBatch,
    *,
    existing: BatchApproval | None = None,
    approval_status: str,
    review_status: str,
    review_notes: list[str],
    requested_at: datetime | None = None,
    reviewed_at: datetime | None = None,
    approved_at: datetime | None = None,
    rejected_at: datetime | None = None,
    reviewer: str | None = None,
    approver: str | None = None,
    decision_note: str = "",
    now: datetime,
) -> BatchApproval:
    created_at = existing.created_at if existing else now
    return BatchApproval(
        project=batch.project,
        batch_id=batch.batch_id,
        approval_status=approval_status,
        review_status=review_status,
        requested_at=requested_at or (existing.requested_at if existing else None),
        reviewed_at=reviewed_at or (existing.reviewed_at if existing else None),
        approved_at=approved_at or (existing.approved_at if existing else None),
        rejected_at=rejected_at or (existing.rejected_at if existing else None),
        reviewer=reviewer or (existing.reviewer if existing else None),
        approver=approver or (existing.approver if existing else None),
        decision_note=decision_note or (existing.decision_note if existing else ""),
        review_notes=review_notes,
        dependency_warnings=batch.dependency_warnings,
        risk_summary=batch.risk_summary,
        lane_summary=batch.lane_summary,
        task_count=batch.task_count,
        high_risk_task_count=sum(batch.risk_summary.get(risk, 0) for risk in ("high", "critical")),
        blocked_dependency_count=len(batch.dependency_warnings),
        scope_summary=_batch_scope_summary(batch),
        validation_summary=_batch_validation_summary(batch),
        next_action=_batch_approval_next_action(batch.project, batch.batch_id, approval_status, review_status),
        created_at=created_at,
        updated_at=now,
    )


def _batch_scope_summary(batch: ProjectBatch) -> list[str]:
    items = [
        f"{batch.task_count} task(s): {', '.join(batch.task_ids) if batch.task_ids else 'none'}",
        f"Lanes: {_format_count_summary(batch.lane_summary)}",
        f"Risks: {_format_count_summary(batch.risk_summary)}",
    ]
    if batch.dependencies:
        items.append(f"External dependencies: {', '.join(batch.dependencies)}")
    return items


def _batch_validation_summary(batch: ProjectBatch) -> list[str]:
    summaries = [snapshot.validation_expectations_summary for snapshot in batch.task_snapshots if snapshot.validation_expectations_summary]
    if not summaries:
        return ["No validation expectations recorded."]
    return sorted(set(summaries))


def _batch_approval_next_action(project_name: str, batch_id: str, approval_status: str, review_status: str) -> str:
    if approval_status == "approved":
        return f"Create execution queue: devo project queue-create --project {project_name} --batch {batch_id}"
    if approval_status == "rejected" or review_status == "needs_changes":
        return "Revise backlog/batch manually or create a new batch."
    if approval_status == "requested":
        return f"Review or approve batch: devo project batch-approval-show --project {project_name} --batch {batch_id}"
    return f"Request batch approval: devo project batch-approval-request --project {project_name} --batch {batch_id} --note \"<note>\""


def _format_count_summary(summary: dict[str, int]) -> str:
    if not summary:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(summary.items()))


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


def _progress_next_action(
    project_name: str,
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint | None,
    backlog: ProjectBacklog | None,
    batches: list[ProjectBatch],
) -> str:
    if not brief:
        return f"Create a Project Brief: devo project brief-create --project {project_name} --title \"<title>\" --file <brief.md>"
    if brief.status != "approved":
        return f"Approve the Project Brief: devo project brief-approve --project {project_name}"
    if not blueprint:
        return f"Create a Blueprint: devo project blueprint-create --project {project_name}"
    if blueprint.status != "approved":
        return f"Approve the Blueprint: devo project blueprint-approve --project {project_name}"
    if not backlog:
        return f"Create a Backlog: devo project backlog-create --project {project_name}"
    if backlog.status != "approved":
        return f"Approve the Backlog: devo project backlog-approve --project {project_name}"
    if not batches:
        return f"Create or suggest a Batch: devo project batch-suggest --project {project_name}"
    latest_batch = batches[0]
    if not any(batch.approval_status == "approved" for batch in batches):
        return f"Review and approve a Batch: devo project batch-show --project {project_name} --batch {latest_batch.batch_id}"
    return "Approved planning batch is ready; create an execution queue or generate a batch handoff."


def _progress_warnings(
    brief: ProjectBrief | None,
    blueprint: ProjectBlueprint | None,
    backlog: ProjectBacklog | None,
    active_tasks: list[BacklogTask],
    batches: list[ProjectBatch],
) -> list[str]:
    warnings: list[str] = []
    if not brief:
        warnings.append("Project Brief is missing.")
    if not blueprint:
        warnings.append("Blueprint is missing.")
    if not backlog:
        warnings.append("Backlog is missing.")
    if backlog and not active_tasks:
        warnings.append("Backlog has no active tasks.")
    blocked = [task.id for task in active_tasks if task.status == "blocked"]
    if blocked:
        warnings.append(f"Blocked tasks: {', '.join(blocked)}.")
    if batches and not any(batch.approval_status == "approved" for batch in batches):
        warnings.append("No planning batch is approved.")
    return warnings


def _aggregate_progress_groups(
    tasks: list[BacklogTask],
    groups: list[BlueprintMilestone] | list[BlueprintEpic],
    field_name: str,
) -> list[PlanningProgressGroup]:
    title_by_id = {group.id: group.title for group in groups}
    group_ids = set(title_by_id)
    for task in tasks:
        group_id = getattr(task, field_name) or "unassigned"
        group_ids.add(group_id)
    results: list[PlanningProgressGroup] = []
    for group_id in sorted(group_ids):
        group_tasks = [task for task in tasks if (getattr(task, field_name) or "unassigned") == group_id]
        active_count = len(group_tasks)
        completed = sum(1 for task in group_tasks if task.status == "completed")
        blocked = sum(1 for task in group_tasks if task.status == "blocked")
        ready = sum(1 for task in group_tasks if task.status == "ready")
        approved = sum(1 for task in group_tasks if task.status == "approved")
        draft = sum(1 for task in group_tasks if task.status == "draft")
        ready_like = sum(1 for task in group_tasks if task.status in {"ready", "approved", "completed"})
        results.append(
            PlanningProgressGroup(
                id=group_id,
                title=title_by_id.get(group_id),
                task_count=active_count,
                active_task_count=active_count,
                completed_task_count=completed,
                blocked_task_count=blocked,
                ready_task_count=ready,
                approved_task_count=approved,
                draft_task_count=draft,
                completion_percent=_percent(completed, active_count),
                readiness_percent=_percent(ready_like, active_count),
                blocked_percent=_percent(blocked, active_count),
            )
        )
    return results


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


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


def _try_get_backlog_task(project_name: str, task_id: str, workspace_root: Path) -> BacklogTask | None:
    try:
        return get_backlog_task(project_name, task_id, workspace_root=workspace_root)
    except ValueError:
        return None


def _task_prompt_section(task: BacklogTask) -> list[str]:
    return [
        "## Task",
        "",
        f"- Task id: `{task.id}`",
        f"- Title: {task.title}",
        f"- Status: `{task.status}`",
        f"- Lane: `{task.lane}`",
        f"- Risk level: `{task.risk_level}`",
        f"- Milestone: `{task.milestone_id or 'none'}`",
        f"- Epic: `{task.epic_id or 'none'}`",
        "",
        "### Summary",
        "",
        task.summary or "No summary recorded.",
        "",
    ]


def _bullet_lines(values: list[str], fallback: str) -> list[str]:
    if not values:
        return [f"- {fallback}"]
    return [f"- {value}" for value in values]


def _summarize_batch_dict(values: dict[str, int], fallback: str) -> str:
    if not values:
        return fallback
    return ", ".join(f"{key} ({value})" for key, value in sorted(values.items()))


def _batch_acceptance(batch: ProjectBatch | None, tasks: list[BacklogTask]) -> list[str]:
    values: list[str] = []
    for task in tasks:
        values.extend(f"{task.id}: {item}" for item in task.acceptance_criteria)
    if values:
        return values
    if not batch:
        return []
    return [f"{snapshot.task_id}: {snapshot.acceptance_criteria_summary}" for snapshot in batch.task_snapshots if snapshot.acceptance_criteria_summary]


def _batch_validation(batch: ProjectBatch | None, tasks: list[BacklogTask]) -> list[str]:
    values: list[str] = []
    for task in tasks:
        values.extend(f"{task.id}: {item}" for item in task.validation_expectations)
    if values:
        return values
    if not batch:
        return []
    return [
        f"{snapshot.task_id}: {snapshot.validation_expectations_summary}"
        for snapshot in batch.task_snapshots
        if snapshot.validation_expectations_summary
    ]


def _collect_task_scope(tasks: list[BacklogTask], kind: str) -> list[str]:
    values: list[str] = []
    for task in tasks:
        source = task.allowed_scope if kind == "allowed" else task.forbidden_scope
        values.extend(f"{task.id}: {item}" for item in source)
    return values


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


def _append_progress_groups(lines: list[str], groups: list[PlanningProgressGroup]) -> None:
    if not groups:
        lines.extend(["No progress groups recorded.", ""])
        return
    for group in groups:
        label = f"{group.id}: {group.title}" if group.title else group.id
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Tasks: `{group.task_count}`",
                f"- Completed: `{group.completed_task_count}`",
                f"- Blocked: `{group.blocked_task_count}`",
                f"- Completion: `{group.completion_percent:.1f}%`",
                f"- Readiness: `{group.readiness_percent:.1f}%`",
                "",
            ]
        )


def _write_model(path: Path, model: BaseModel) -> None:
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")


def _require_project(project_name: str, workspace_root: Path) -> None:
    load_registered_project(project_name, workspace_root=workspace_root)
