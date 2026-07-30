from __future__ import annotations

from time import perf_counter
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from .doctor import run_doctor
from .projects import get_workspace_root, list_projects
from .read_models import build_project_overview, build_run_overview, build_work_package_overview
from .runs import load_current_selection, load_run
from .scanner import load_registered_project
from .work_history import build_project_activity_summary

APP_NAME = "DevOrchestrator API"
API_ROUTES = (
    "GET /api/health",
    "GET /api/current",
    "GET /api/projects",
    "GET /api/projects/{project}/overview",
    "GET /api/projects/{project}/activity",
    "GET /api/projects/{project}/doctor",
    "GET /api/projects/{project}/runs/{run_id}/overview",
    "GET /api/projects/{project}/runs/{run_id}/work-package",
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
        allow_methods=["GET"],
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
    def project_overview(project: str) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(build_project_overview(project, workspace_root=root))

    @api.get("/api/projects/{project}/activity")
    def project_activity(project: str, limit: int = 10) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(build_project_activity_summary(project, limit=limit, workspace_root=root))

    @api.get("/api/projects/{project}/doctor")
    def project_doctor(project: str) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(run_doctor(project_name=project, workspace_root=root))

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
