from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .context import APPROVAL_RECORD_NAME, CONTEXT_STATE_NAME, load_context_state
from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import ContextSnapshot, ContextStatus, CurrentSelection, RunState, RunStatus

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
    state = load_context_state(project_name, workspace_root=root)
    if state.status != ContextStatus.CONTEXT_APPROVED:
        msg = "Project context must be approved before creating development runs."
        raise ValueError(msg)

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
