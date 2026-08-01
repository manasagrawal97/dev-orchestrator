from __future__ import annotations

from time import perf_counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from .doctor import run_doctor_with_timing
from .project_planning import (
    calculate_project_progress,
    get_backlog_task,
    list_project_batches,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
)
from .projects import get_workspace_root, list_projects
from .read_models import build_project_overview_with_timing, build_run_overview, build_work_package_overview
from .runs import load_current_selection, load_run
from .scanner import load_registered_project
from .ui_actions import CURRENT_UI_MODE, UiActionExecuteRequest, execute_ui_action, get_ui_action, list_allowed_ui_actions, list_ui_actions
from .work_history import build_project_activity_summary

APP_NAME = "DevOrchestrator API"
API_ROUTES = (
    "GET /api/health",
    "GET /api/current",
    "GET /api/projects",
    "GET /api/projects/{project}/overview",
    "GET /api/projects/{project}/brief",
    "GET /api/projects/{project}/blueprint",
    "GET /api/projects/{project}/backlog",
    "GET /api/projects/{project}/backlog/prompt",
    "GET /api/projects/{project}/batches",
    "GET /api/projects/{project}/batches/{batch_id}",
    "GET /api/projects/{project}/progress",
    "GET /api/projects/{project}/tasks",
    "GET /api/projects/{project}/tasks/{task_id}",
    "GET /api/projects/{project}/activity",
    "GET /api/projects/{project}/doctor",
    "GET /api/projects/{project}/runs/{run_id}/overview",
    "GET /api/projects/{project}/runs/{run_id}/work-package",
    "GET /api/actions",
    "GET /api/actions/allowed",
    "GET /api/actions/{action_id}",
    "POST /api/actions/execute",
)
LOCAL_API_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOCAL_FRONTEND_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")


def create_app(workspace_root: Path | None = None) -> FastAPI:
    """Create the local read-only Devo API app without starting a server."""
    root = workspace_root or get_workspace_root()
    api = FastAPI(title=APP_NAME, version="0.1.0")
    api.add_middleware(
        CORSMiddleware,
        allow_origins=list(LOCAL_FRONTEND_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @api.middleware("http")
    async def add_elapsed_header(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = perf_counter()
        response = await call_next(request)
        response.headers["X-Devo-Elapsed-Ms"] = f"{(perf_counter() - started) * 1000:.1f}"
        return response

    @api.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "OK",
            "app": APP_NAME,
            "read_only": True,
        }

    @api.get("/api/current")
    def current() -> dict[str, object]:
        return _current_context(root)

    @api.get("/api/projects")
    def projects() -> dict[str, object]:
        registrations = list_projects(workspace_root=root)
        return {
            "projects": [
                {
                    "name": project.name,
                    "path": str(project.path),
                    "path_exists": Path(project.path).exists(),
                }
                for project in registrations
            ],
            "count": len(registrations),
        }

    @api.get("/api/projects/{project}/overview")
    def project_overview(project: str, include_timing: bool = False) -> dict[str, object]:
        _require_project(project, root)
        overview, timing = build_project_overview_with_timing(project, workspace_root=root)
        return _with_optional_timing(_model_dump(overview), timing, include_timing)

    @api.get("/api/projects/{project}/brief")
    def project_brief(project: str) -> dict[str, object]:
        _require_project(project, root)
        brief = load_project_brief(project, workspace_root=root)
        if not brief:
            raise HTTPException(status_code=404, detail={"error": "brief_not_found", "message": f"Project brief not found: {project}"})
        paths = planning_artifact_paths(project, workspace_root=root)
        data = _model_dump(brief)
        data["artifact_paths"] = {"json": str(paths.brief_json), "markdown": str(paths.brief_markdown)}
        return data

    @api.get("/api/projects/{project}/blueprint")
    def project_blueprint(project: str) -> dict[str, object]:
        _require_project(project, root)
        blueprint = load_project_blueprint(project, workspace_root=root)
        if not blueprint:
            raise HTTPException(status_code=404, detail={"error": "blueprint_not_found", "message": f"Project blueprint not found: {project}"})
        paths = planning_artifact_paths(project, workspace_root=root)
        data = _model_dump(blueprint)
        data["artifact_paths"] = {"json": str(paths.blueprint_json), "markdown": str(paths.blueprint_markdown)}
        return data

    @api.get("/api/projects/{project}/backlog")
    def project_backlog(project: str) -> dict[str, object]:
        _require_project(project, root)
        backlog = load_project_backlog(project, workspace_root=root)
        if not backlog:
            raise HTTPException(status_code=404, detail={"error": "backlog_not_found", "message": f"Project backlog not found: {project}"})
        paths = planning_artifact_paths(project, workspace_root=root)
        data = _model_dump(backlog)
        data["artifact_paths"] = {"json": str(paths.backlog_json), "markdown": str(paths.backlog_markdown)}
        return data

    @api.get("/api/projects/{project}/backlog/prompt")
    def project_backlog_prompt(project: str) -> dict[str, object]:
        _require_project(project, root)
        paths = planning_artifact_paths(project, workspace_root=root)
        return {
            "project": project,
            "exists": paths.backlog_refinement_prompt.exists(),
            "path": str(paths.backlog_refinement_prompt),
            "suggested_command": f"devo project backlog-prompt --project {project}",
        }

    @api.get("/api/projects/{project}/batches")
    def project_batches(project: str) -> dict[str, object]:
        _require_project(project, root)
        batches = list_project_batches(project, workspace_root=root)
        return {"project": project, "count": len(batches), "batches": [_model_dump(batch) for batch in batches]}

    @api.get("/api/projects/{project}/batches/{batch_id}")
    def project_batch(project: str, batch_id: str) -> dict[str, object]:
        _require_project(project, root)
        batch = load_project_batch(project, batch_id, workspace_root=root)
        if not batch:
            raise HTTPException(status_code=404, detail={"error": "batch_not_found", "message": f"Project batch not found: {batch_id}"})
        return _model_dump(batch)

    @api.get("/api/projects/{project}/progress")
    def project_progress(project: str) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(calculate_project_progress(project, workspace_root=root))

    @api.get("/api/projects/{project}/tasks")
    def project_tasks(project: str) -> dict[str, object]:
        _require_project(project, root)
        backlog = load_project_backlog(project, workspace_root=root)
        if not backlog:
            raise HTTPException(status_code=404, detail={"error": "backlog_not_found", "message": f"Project backlog not found: {project}"})
        return {"project": project, "count": backlog.task_count, "tasks": [_model_dump(task) for task in backlog.tasks]}

    @api.get("/api/projects/{project}/tasks/{task_id}")
    def project_task(project: str, task_id: str) -> dict[str, object]:
        _require_project(project, root)
        try:
            task = get_backlog_task(project, task_id, workspace_root=root)
        except ValueError as exc:
            error = "task_not_found" if str(exc).startswith("Backlog task not found:") else "backlog_not_found"
            raise HTTPException(status_code=404, detail={"error": error, "message": str(exc)}) from exc
        return _model_dump(task)

    @api.get("/api/projects/{project}/activity")
    def project_activity(project: str, limit: int = 10, include_timing: bool = False) -> dict[str, object]:
        _require_project(project, root)
        activity, timing = _timed_model("activity_ms", lambda: build_project_activity_summary(project, limit=limit, workspace_root=root))
        return _with_optional_timing(_model_dump(activity), timing, include_timing)

    @api.get("/api/projects/{project}/doctor")
    def project_doctor(project: str, include_timing: bool = False) -> dict[str, object]:
        _require_project(project, root)
        report, timing = run_doctor_with_timing(project_name=project, workspace_root=root)
        return _with_optional_timing(_model_dump(report), timing, include_timing)

    @api.get("/api/projects/{project}/runs/{run_id}/overview")
    def run_overview(project: str, run_id: str) -> dict[str, object]:
        _require_project(project, root)
        _require_run(project, run_id, root)
        return _model_dump(build_run_overview(project, run_id, workspace_root=root))

    @api.get("/api/projects/{project}/runs/{run_id}/work-package")
    def work_package_overview(project: str, run_id: str) -> dict[str, object]:
        _require_project(project, root)
        _require_run(project, run_id, root)
        return _model_dump(build_work_package_overview(project, run_id, workspace_root=root))

    @api.get("/api/actions")
    def ui_actions() -> dict[str, object]:
        actions = [action.to_dict() for action in list_ui_actions()]
        return {"ui_mode": CURRENT_UI_MODE, "count": len(actions), "actions": actions}

    @api.get("/api/actions/allowed")
    def allowed_ui_actions() -> dict[str, object]:
        actions = [action.to_dict() for action in list_allowed_ui_actions(ui_mode=CURRENT_UI_MODE)]
        return {"ui_mode": CURRENT_UI_MODE, "count": len(actions), "actions": actions}

    @api.get("/api/actions/{action_id}")
    def ui_action(action_id: str) -> dict[str, object]:
        action = get_ui_action(action_id)
        if not action:
            raise HTTPException(status_code=404, detail={"error": "action_not_found", "message": f"Unknown UI action: {action_id}"})
        return action.to_dict()

    @api.post("/api/actions/execute")
    def execute_action(request: UiActionExecuteRequest) -> dict[str, object]:
        try:
            result = execute_ui_action(request, workspace_root=root)
        except ValueError as exc:
            if str(exc).startswith("Unknown UI action:"):
                raise HTTPException(status_code=404, detail={"error": "action_not_found", "message": str(exc)}) from exc
            raise HTTPException(status_code=400, detail={"error": "action_invalid", "message": str(exc)}) from exc
        return _model_dump(result)

    return api


def validate_api_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized not in LOCAL_API_HOSTS:
        msg = "Devo API v1 is local-only. Use --host 127.0.0.1 or --host localhost."
        raise ValueError(msg)
    return host


def _current_context(workspace_root: Path) -> dict[str, object]:
    try:
        selection = load_current_selection(workspace_root=workspace_root)
    except Exception as exc:
        return {
            "project": None,
            "run": None,
            "project_exists": False,
            "run_exists": False,
            "valid": False,
            "detail": f"Current context is unreadable: {exc}",
        }
    if not selection:
        return {
            "project": None,
            "run": None,
            "project_exists": False,
            "run_exists": False,
            "valid": True,
            "detail": "No current context selected.",
        }

    project_exists = _project_exists(selection.project_name, workspace_root)
    run_exists = False
    if project_exists and selection.run_id:
        try:
            load_run(selection.project_name, selection.run_id, workspace_root=workspace_root)
        except ValueError:
            run_exists = False
        else:
            run_exists = True
    return {
        "project": selection.project_name,
        "run": selection.run_id,
        "project_exists": project_exists,
        "run_exists": run_exists,
        "valid": project_exists and (not selection.run_id or run_exists),
        "detail": "Current context loaded.",
    }


def _require_project(project_name: str, workspace_root: Path) -> None:
    try:
        load_registered_project(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": "project_not_found", "message": str(exc)}) from exc


def _require_run(project_name: str, run_id: str, workspace_root: Path) -> None:
    try:
        load_run(project_name, run_id, workspace_root=workspace_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": "run_not_found", "message": str(exc)}) from exc


def _project_exists(project_name: str, workspace_root: Path) -> bool:
    try:
        load_registered_project(project_name, workspace_root=workspace_root)
    except ValueError:
        return False
    return True


def _model_dump(model: object) -> dict[str, object]:
    if hasattr(model, "model_dump"):
        return jsonable_encoder(model)
    return jsonable_encoder(model)


def _with_optional_timing(data: dict[str, object], timing: dict[str, float], include_timing: bool) -> dict[str, object]:
    if include_timing:
        data["_timing"] = timing
    return data


def _timed_model(name: str, action):
    started = perf_counter()
    model = action()
    elapsed = round((perf_counter() - started) * 1000, 1)
    return model, {name: elapsed, "total_ms": elapsed}
