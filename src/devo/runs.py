from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .context import APPROVAL_RECORD_NAME, CONTEXT_STATE_NAME, load_context_state
from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import (
    ContextSnapshot,
    ContextStatus,
    CurrentSelection,
    ImplementationRecord,
    RunAgentImportRecord,
    RunArtifact,
    RunArtifactType,
    RunState,
    RunStatus,
)

IDEA_ANALYST_AGENT_NAME = "IdeaAnalystAgent"
REQUIREMENTS_AGENT_NAME = "RequirementsAgent"
PLANNER_AGENT_NAME = "PlannerAgent"
PLAN_REVIEWER_AGENT_NAME = "PlanReviewerAgent"
TASK_DECOMPOSER_AGENT_NAME = "TaskDecomposerAgent"
IMPLEMENTATION_COORDINATOR_AGENT_NAME = "ImplementationCoordinatorAgent"
IDEA_ANALYSIS_ARTIFACT_NAME = "idea-analysis.md"
REQUIREMENTS_ARTIFACT_NAME = "requirements.md"
PLAN_ARTIFACT_NAME = "plan.md"
PLAN_REVIEW_ARTIFACT_NAME = "plan-review.md"
TASKS_ARTIFACT_NAME = "tasks.md"
IMPLEMENTATION_BRIEF_ARTIFACT_NAME = "implementation-brief.md"

RUN_STATUS_ORDER = {
    RunStatus.RUN_CREATED: 0,
    RunStatus.IDEA_ANALYSIS_DRAFTED: 1,
    RunStatus.REQUIREMENTS_DRAFTED: 2,
    RunStatus.PLAN_DRAFTED: 3,
    RunStatus.PLAN_REVIEWED: 4,
    RunStatus.TASKS_DRAFTED: 5,
    RunStatus.IMPLEMENTATION_READY: 6,
}

RUN_SUBDIRECTORIES = (
    "artifacts",
    "prompts",
    "validation",
    "reviews",
    "logs",
    "approvals",
)


def create_run(project_name: str, goal: str, workspace_root: Path | None = None) -> RunState:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    require_context_approved(project_name, workspace_root=root)

    created_at = datetime.now(UTC)
    run_id = _unique_run_id(root, project_name, goal, created_at)
    run_dir = _run_dir(root, project_name, run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    for subdirectory in RUN_SUBDIRECTORIES:
        (run_dir / subdirectory).mkdir(parents=True, exist_ok=True)

    run_state = RunState(
        project_name=project_name,
        project_path=registration.path,
        run_id=run_id,
        goal=goal,
        status=RunStatus.RUN_CREATED,
        created_at=created_at,
        context_snapshot=_build_context_snapshot(root, project_name),
    )

    (run_dir / "goal.md").write_text(_render_goal_markdown(run_state), encoding="utf-8")
    (run_dir / "run-state.json").write_text(run_state.model_dump_json(indent=2), encoding="utf-8")
    return run_state


def list_runs(project_name: str, workspace_root: Path | None = None) -> list[RunState]:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    runs_root = root / "runs" / project_name
    if not runs_root.exists():
        return []

    runs: list[RunState] = []
    for state_file in sorted(runs_root.glob("*/run-state.json")):
        data = json.loads(state_file.read_text(encoding="utf-8"))
        runs.append(RunState.model_validate(data))
    return runs


def load_run(project_name: str, run_id: str, workspace_root: Path | None = None) -> RunState:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    state_file = _run_dir(root, project_name, run_id) / "run-state.json"
    if not state_file.exists():
        msg = f"Run not found: {run_id}"
        raise ValueError(msg)

    data = json.loads(state_file.read_text(encoding="utf-8"))
    return RunState.model_validate(data)


def save_run_state(run_state: RunState, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    state_file = _run_dir(root, run_state.project_name, run_state.run_id) / "run-state.json"
    state_file.write_text(run_state.model_dump_json(indent=2), encoding="utf-8")


def import_run_agent_output(
    agent_name: str,
    project_name: str,
    run_id: str,
    source_file: Path,
    task_id: str | None = None,
    allow_missing_idea_analysis: bool = False,
    workspace_root: Path | None = None,
) -> RunAgentImportRecord:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Import file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Import path must be a file: {source_path}"
        raise ValueError(msg)

    if agent_name == IDEA_ANALYST_AGENT_NAME:
        artifact_type = RunArtifactType.IDEA_ANALYSIS
        artifact_name = IDEA_ANALYSIS_ARTIFACT_NAME
        next_status = RunStatus.IDEA_ANALYSIS_DRAFTED
    elif agent_name == REQUIREMENTS_AGENT_NAME:
        if not find_run_artifact(run_state, RunArtifactType.IDEA_ANALYSIS) and not allow_missing_idea_analysis:
            msg = "RequirementsAgent import requires IdeaAnalystAgent output. Use --allow-missing-idea-analysis to override."
            raise ValueError(msg)
        artifact_type = RunArtifactType.REQUIREMENTS
        artifact_name = REQUIREMENTS_ARTIFACT_NAME
        next_status = RunStatus.REQUIREMENTS_DRAFTED
    elif agent_name == PLANNER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.REQUIREMENTS_DRAFTED,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.REQUIREMENTS,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        artifact_type = RunArtifactType.PLAN
        artifact_name = PLAN_ARTIFACT_NAME
        next_status = RunStatus.PLAN_DRAFTED
    elif agent_name == PLAN_REVIEWER_AGENT_NAME:
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "PlanReviewerAgent requires PlannerAgent output before review.",
        )
        artifact_type = RunArtifactType.PLAN_REVIEW
        artifact_name = PLAN_REVIEW_ARTIFACT_NAME
        next_status = RunStatus.PLAN_REVIEWED
    elif agent_name == TASK_DECOMPOSER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.PLAN_REVIEWED,
            "TaskDecomposerAgent requires a reviewed plan before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "TaskDecomposerAgent requires PlannerAgent output before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN_REVIEW,
            "TaskDecomposerAgent requires PlanReviewerAgent output before task decomposition.",
        )
        artifact_type = RunArtifactType.TASKS
        artifact_name = TASKS_ARTIFACT_NAME
        next_status = RunStatus.TASKS_DRAFTED
    elif agent_name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.TASKS_DRAFTED,
            "ImplementationCoordinatorAgent requires drafted tasks before implementation coordination.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.TASKS,
            "ImplementationCoordinatorAgent requires TaskDecomposerAgent output before implementation coordination.",
        )
        require_task_excerpt(run_state, normalized_task_id)
        artifact_type = RunArtifactType.IMPLEMENTATION_BRIEF
        artifact_name = IMPLEMENTATION_BRIEF_ARTIFACT_NAME
        next_status = RunStatus.IMPLEMENTATION_READY
    else:
        msg = f"Run-level import is not supported for agent: {agent_name}"
        raise ValueError(msg)

    if agent_name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        artifact_path = _implementation_artifact_dir(root, project_name, run_id, normalized_task_id) / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        artifact_path = _run_dir(root, project_name, run_id) / "artifacts" / artifact_name
    shutil.copyfile(source_path, artifact_path)
    artifact = RunArtifact(
        artifact_type=artifact_type,
        agent_name=agent_name,
        source_file_path=source_path,
        artifact_path=artifact_path,
    )
    if agent_name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        run_state.artifacts = [
            existing
            for existing in run_state.artifacts
            if not (
                existing.artifact_type == artifact_type
                and existing.artifact_path.parent.name == normalized_task_id
            )
        ]
        imported_at = datetime.now(UTC)
        run_state.implementation_records = [
            existing for existing in run_state.implementation_records if existing.task_id != normalized_task_id
        ]
        run_state.implementation_records.append(
            ImplementationRecord(
                task_id=normalized_task_id,
                agent_name=agent_name,
                source_file_path=source_path,
                implementation_brief_path=artifact_path,
                imported_at=imported_at,
            )
        )
        run_state.current_task_id = normalized_task_id
        run_state.implementation_brief_path = artifact_path
        run_state.implementation_ready_at = imported_at
    else:
        run_state.artifacts = [
            existing for existing in run_state.artifacts if existing.artifact_type != artifact_type
        ]
    run_state.artifacts.append(artifact)
    run_state.status = next_status
    run_state.updated_at = datetime.now(UTC)
    save_run_state(run_state, workspace_root=root)

    return RunAgentImportRecord(
        project_name=project_name,
        run_id=run_id,
        agent_name=agent_name,
        artifact=artifact,
        status_after_import=next_status,
    )


def save_current_selection(
    project_name: str,
    run_id: str | None = None,
    workspace_root: Path | None = None,
) -> CurrentSelection:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    run_path = None
    if run_id:
        load_run(project_name, run_id, workspace_root=root)
        run_path = _run_dir(root, project_name, run_id)

    selection = CurrentSelection(
        project_name=project_name,
        project_path=registration.path,
        run_id=run_id,
        run_path=run_path,
    )
    current_file = root / "current.json"
    current_file.parent.mkdir(parents=True, exist_ok=True)
    current_file.write_text(selection.model_dump_json(indent=2), encoding="utf-8")
    return selection


def require_context_approved(project_name: str, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    state = load_context_state(project_name, workspace_root=root)
    if state.status != ContextStatus.CONTEXT_APPROVED:
        msg = "Project context must be approved before creating development runs."
        raise ValueError(msg)


def find_run_artifact(run_state: RunState, artifact_type: RunArtifactType) -> RunArtifact | None:
    for artifact in run_state.artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def require_run_artifact(run_state: RunState, artifact_type: RunArtifactType, message: str) -> RunArtifact:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact:
        raise ValueError(message)
    return artifact


def require_run_status_at_least(run_state: RunState, minimum_status: RunStatus, message: str) -> None:
    if RUN_STATUS_ORDER[run_state.status] < RUN_STATUS_ORDER[minimum_status]:
        raise ValueError(message)


def require_task_id(task_id: str | None) -> str:
    normalized = (task_id or "").strip()
    if not normalized:
        msg = "ImplementationCoordinatorAgent requires --task."
        raise ValueError(msg)
    return normalized


def require_task_excerpt(run_state: RunState, task_id: str) -> str:
    tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS)
    if not tasks_text:
        msg = "ImplementationCoordinatorAgent requires TaskDecomposerAgent output before implementation coordination."
        raise ValueError(msg)
    excerpt = extract_task_excerpt(tasks_text, task_id)
    if not excerpt:
        msg = f"Task id not found in tasks.md: {task_id}"
        raise ValueError(msg)
    return excerpt


def extract_task_excerpt(tasks_text: str, task_id: str) -> str | None:
    pattern = re.compile(
        rf"(?ims)^##\s+Task\s+{re.escape(task_id)}\b.*?(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)"
    )
    match = pattern.search(tasks_text)
    if match:
        return match.group(0).strip()

    fallback = re.compile(
        rf"(?ims)^.*(?:task id:\s*`?{re.escape(task_id)}`?).*?(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)"
    )
    match = fallback.search(tasks_text)
    if match:
        return match.group(0).strip()
    return None


def get_run_artifact_text(run_state: RunState, artifact_type: RunArtifactType, max_chars: int = 20_000) -> str | None:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact or not artifact.artifact_path.exists():
        return None
    return artifact.artifact_path.read_text(encoding="utf-8")[:max_chars]


def get_run_artifacts_summary(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    directory = _run_dir(root, project_name, run_id)
    return {
        "goal_path": str(directory / "goal.md"),
        "run_state_path": str(directory / "run-state.json"),
        "idea_analysis_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.IDEA_ANALYSIS),
        "requirements_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.REQUIREMENTS),
        "plan_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.PLAN),
        "plan_review_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.PLAN_REVIEW),
        "tasks_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.TASKS),
        "implementation_artifact_paths": [
            {
                "task_id": record.task_id,
                "implementation_brief_path": str(record.implementation_brief_path),
            }
            for record in run_state.implementation_records
        ],
        "prompt_paths": [str(path) for path in sorted((directory / "prompts").glob("*.md"))],
    }


def run_path(project_name: str, run_id: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return _run_dir(root, project_name, run_id)


def _build_context_snapshot(workspace_root: Path, project_name: str) -> ContextSnapshot:
    context_root = workspace_root / "projects" / project_name / "context"
    approval_file = workspace_root / "projects" / project_name / "approvals" / APPROVAL_RECORD_NAME
    if not approval_file.exists():
        msg = "Project context must be approved before creating development runs."
        raise ValueError(msg)

    approval_data = json.loads(approval_file.read_text(encoding="utf-8"))
    approved_artifact_paths = [Path(path) for path in approval_data.get("approved_artifact_paths", [])]
    return ContextSnapshot(
        context_state_path=context_root / CONTEXT_STATE_NAME,
        approval_record_path=approval_file,
        approved_artifact_paths=approved_artifact_paths,
    )


def _artifact_path_or_none(run_state: RunState, artifact_type: RunArtifactType) -> str | None:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact:
        return None
    return str(artifact.artifact_path)


def _render_goal_markdown(run_state: RunState) -> str:
    return "\n".join(
        [
            f"# {run_state.run_id}",
            "",
            f"- Project: {run_state.project_name}",
            f"- Run ID: {run_state.run_id}",
            f"- Created at: {run_state.created_at.isoformat()}",
            f"- Initial status: {run_state.status.value}",
            "",
            "## Goal",
            "",
            run_state.goal,
            "",
        ]
    )


def _unique_run_id(workspace_root: Path, project_name: str, goal: str, created_at: datetime) -> str:
    base = f"{created_at:%Y-%m-%d-%H%M%S}-{_slugify(goal)}"
    candidate = base
    suffix = 2
    while _run_dir(workspace_root, project_name, candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:60] or "run"


def _run_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return workspace_root / "runs" / project_name / run_id


def _implementation_artifact_dir(workspace_root: Path, project_name: str, run_id: str, task_id: str) -> Path:
    return _run_dir(workspace_root, project_name, run_id) / "artifacts" / "implementation" / task_id
