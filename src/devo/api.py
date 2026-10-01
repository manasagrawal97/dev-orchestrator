from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .delivery import (
    list_delivery_approvals,
    list_delivery_checks,
    list_delivery_plans,
    list_delivery_reports,
    load_delivery_commit_result,
    load_delivery_push_result,
    load_delivery_approval,
    load_delivery_check,
    load_delivery_plan,
    load_delivery_report,
)
from .doctor import run_doctor_with_timing
from .project_planning import (
    approve_execution_policy_approval_bundle,
    approve_project_batch,
    build_operator_console_projection,
    calculate_project_progress,
    create_rough_goal_intake_plan_from_text,
    get_codex_queue_worker_status,
    get_codex_worker_flow_summary,
    get_backlog_task,
    get_queue_next_item,
    list_batch_approvals,
    list_codex_handoffs,
    list_codex_run_plans,
    list_codex_worker_reports,
    list_codex_worker_reviews,
    list_codex_worker_runs,
    list_project_batches,
    list_execution_queues,
    list_queue_worker_runs,
    load_execution_queue,
    load_queue_worker_run,
    load_batch_approval,
    load_codex_handoff,
    load_codex_run_plan,
    load_codex_worker_report,
    load_codex_worker_review,
    load_codex_worker_run,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    load_rough_goal_intake_materialization,
    materialize_rough_goal_intake_plan,
    planning_artifact_paths,
    prepare_rough_goal_intake,
    record_queue_worker_review,
    resume_queue_worker_run,
    retry_queue_worker_run,
    supervise_prepared_goal,
    worker_execution_log_paths,
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
    "GET /api/projects/{project}/batch-approvals",
    "GET /api/projects/{project}/batches/{batch_id}",
    "GET /api/projects/{project}/batches/{batch_id}/approval",
    "GET /api/projects/{project}/progress",
    "GET /api/projects/{project}/delivery-checks",
    "GET /api/projects/{project}/delivery-checks/{delivery_id}",
    "GET /api/projects/{project}/delivery-plans",
    "GET /api/projects/{project}/delivery-plans/{delivery_id}",
    "GET /api/projects/{project}/delivery-approvals",
    "GET /api/projects/{project}/delivery-plans/{delivery_id}/approval",
    "GET /api/projects/{project}/delivery-reports",
    "GET /api/projects/{project}/delivery-reports/{delivery_id}",
    "GET /api/projects/{project}/delivery-reports/{delivery_id}/commit",
    "GET /api/projects/{project}/delivery-reports/{delivery_id}/push",
    "GET /api/projects/{project}/queues",
    "GET /api/projects/{project}/queues/{queue_id}",
    "GET /api/projects/{project}/queues/{queue_id}/next",
    "GET /api/projects/{project}/queues/{queue_id}/worker-status",
    "GET /api/projects/{project}/queues/{queue_id}/flow-summary",
    "GET /api/projects/{project}/queue-worker-runs",
    "GET /api/projects/{project}/queue-worker-runs/{run_id}",
    "GET /api/projects/{project}/handoffs",
    "GET /api/projects/{project}/handoffs/{handoff_id}",
    "GET /api/projects/{project}/worker-runs",
    "GET /api/projects/{project}/worker-runs/{worker_run_id}",
    "GET /api/projects/{project}/worker-runs/{worker_run_id}/execution",
    "GET /api/projects/{project}/worker-runs/{worker_run_id}/report",
    "GET /api/projects/{project}/worker-reports",
    "GET /api/projects/{project}/worker-runs/{worker_run_id}/review",
    "GET /api/projects/{project}/worker-reviews",
    "GET /api/projects/{project}/worker-run-plans",
    "GET /api/projects/{project}/worker-run-plans/{plan_id}",
    "GET /api/projects/{project}/tasks",
    "GET /api/projects/{project}/tasks/{task_id}",
    "GET /api/projects/{project}/activity",
    "GET /api/projects/{project}/doctor",
    "GET /api/projects/{project}/runs/{run_id}/overview",
    "GET /api/projects/{project}/runs/{run_id}/work-package",
    "GET /api/projects/{project}/operator-console",
    "POST /api/projects/{project}/operator-console/intakes",
    "POST /api/projects/{project}/operator-console/intakes/{intake_id}/materialize",
    "POST /api/projects/{project}/operator-console/intakes/{intake_id}/approve",
    "POST /api/projects/{project}/operator-console/intakes/{intake_id}/prepare",
    "POST /api/projects/{project}/operator-console/goals/{intake_id}/approve",
    "POST /api/projects/{project}/operator-console/goals/{intake_id}/run",
    "POST /api/projects/{project}/operator-console/runs/{run_id}/review",
    "POST /api/projects/{project}/operator-console/runs/{run_id}/recover",
    "GET /api/actions",
    "GET /api/actions/allowed",
    "GET /api/actions/{action_id}",
    "POST /api/actions/execute",
)
LOCAL_API_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOCAL_API_CLIENT_HOSTS = {*LOCAL_API_HOSTS, "testclient"}
LOCAL_FRONTEND_ORIGINS = ("http://127.0.0.1:5173", "http://localhost:5173")


class OperatorConsoleIntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_markdown: str = Field(min_length=1, max_length=100_000)
    confirm_create: bool = False


class OperatorConsoleMaterializeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_materialize: bool = False


class OperatorConsolePrepareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_prepare: bool = False
    confirm_materialized_plan_reviewed: bool = False
    reviewed_by: str = Field(default="", max_length=200)
    enable_supervised_delivery: bool = False
    confirm_supervised_delivery: bool = False
    supervised_delivery_authorized_by: str = Field(default="", max_length=200)


class OperatorConsolePlanningApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str = Field(min_length=1, max_length=100)
    approver: str = Field(min_length=1, max_length=200)
    note: str = Field(min_length=1, max_length=2_000)
    confirm_approve: bool = False


class OperatorConsoleApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1, max_length=100)
    approver: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=2_000)
    confirm_approve: bool = False


class OperatorConsoleRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1, max_length=100)
    message: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=2_000)
    max_steps: int = Field(default=10, ge=1, le=100)
    poll_interval_seconds: float = Field(default=1.0, gt=0, le=30)
    max_wait_seconds: float = Field(default=30.0, gt=0, le=600)
    confirm_run: bool = False


class OperatorConsoleReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str = Field(min_length=1, max_length=100)
    status: Literal["passed", "needs_changes", "rejected", "blocked"]
    summary: str = Field(min_length=1, max_length=10_000)
    recorded_by: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=2_000)
    confirm_review: bool = False


class OperatorConsoleRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intake_id: str = Field(min_length=1, max_length=100)
    bundle_id: str = Field(min_length=1, max_length=100)
    action: Literal["resume_worker", "retry_worker"]
    operator: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=2_000)
    confirm_recovery: bool = False


def create_app(workspace_root: Path | None = None) -> FastAPI:
    """Create the local Devo projection and guarded-control API without starting a server."""
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
            "read_only": False,
            "capabilities": {
                "read_projections": True,
                "guarded_mutations": True,
                "localhost_mutations_only": True,
                "arbitrary_commands": False,
                "automatic_retry": False,
            },
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

    @api.get("/api/projects/{project}/batch-approvals")
    def project_batch_approvals(project: str) -> dict[str, object]:
        _require_project(project, root)
        approvals = list_batch_approvals(project, workspace_root=root)
        return {"project": project, "count": len(approvals), "approvals": [_model_dump(approval) for approval in approvals]}

    @api.get("/api/projects/{project}/batches/{batch_id}")
    def project_batch(project: str, batch_id: str) -> dict[str, object]:
        _require_project(project, root)
        batch = load_project_batch(project, batch_id, workspace_root=root)
        if not batch:
            raise HTTPException(status_code=404, detail={"error": "batch_not_found", "message": f"Project batch not found: {batch_id}"})
        return _model_dump(batch)

    @api.get("/api/projects/{project}/batches/{batch_id}/approval")
    def project_batch_approval(project: str, batch_id: str) -> dict[str, object]:
        _require_project(project, root)
        approval = load_batch_approval(project, batch_id, workspace_root=root)
        if not approval:
            raise HTTPException(status_code=404, detail={"error": "batch_approval_not_found", "message": f"Batch approval not found: {batch_id}"})
        return _model_dump(approval)

    @api.get("/api/projects/{project}/progress")
    def project_progress(project: str) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(calculate_project_progress(project, workspace_root=root))

    @api.get("/api/projects/{project}/delivery-checks")
    def project_delivery_checks(project: str) -> dict[str, object]:
        _require_project(project, root)
        checks = list_delivery_checks(project, workspace_root=root)
        return {"project": project, "count": len(checks), "delivery_checks": [_model_dump(check) for check in checks]}

    @api.get("/api/projects/{project}/delivery-checks/{delivery_id}")
    def project_delivery_check(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        check = load_delivery_check(project, delivery_id, workspace_root=root)
        if not check:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_check_not_found", "message": f"Delivery check not found: {delivery_id}"},
            )
        return _model_dump(check)

    @api.get("/api/projects/{project}/delivery-plans")
    def project_delivery_plans(project: str) -> dict[str, object]:
        _require_project(project, root)
        plans = list_delivery_plans(project, workspace_root=root)
        return {"project": project, "count": len(plans), "delivery_plans": [_model_dump(plan) for plan in plans]}

    @api.get("/api/projects/{project}/delivery-plans/{delivery_id}")
    def project_delivery_plan(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        plan = load_delivery_plan(project, delivery_id, workspace_root=root)
        if not plan:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_plan_not_found", "message": f"Delivery plan not found: {delivery_id}"},
            )
        return _model_dump(plan)

    @api.get("/api/projects/{project}/delivery-approvals")
    def project_delivery_approvals(project: str) -> dict[str, object]:
        _require_project(project, root)
        approvals = list_delivery_approvals(project, workspace_root=root)
        return {"project": project, "count": len(approvals), "delivery_approvals": [_model_dump(approval) for approval in approvals]}

    @api.get("/api/projects/{project}/delivery-plans/{delivery_id}/approval")
    def project_delivery_approval(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        approval = load_delivery_approval(project, delivery_id, workspace_root=root)
        if not approval:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_approval_not_found", "message": f"Delivery approval not found: {delivery_id}"},
            )
        return _model_dump(approval)

    @api.get("/api/projects/{project}/delivery-reports")
    def project_delivery_reports(project: str) -> dict[str, object]:
        _require_project(project, root)
        reports = list_delivery_reports(project, workspace_root=root)
        return {"project": project, "count": len(reports), "delivery_reports": [_model_dump(report) for report in reports]}

    @api.get("/api/projects/{project}/delivery-reports/{delivery_id}")
    def project_delivery_report(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        report = load_delivery_report(project, delivery_id, workspace_root=root)
        if not report:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_report_not_found", "message": f"Delivery report not found: {delivery_id}"},
            )
        return _model_dump(report)

    @api.get("/api/projects/{project}/delivery-reports/{delivery_id}/commit")
    def project_delivery_commit_result(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        result = load_delivery_commit_result(project, delivery_id, workspace_root=root)
        if not result:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_commit_not_found", "message": f"Delivery commit result not found: {delivery_id}"},
            )
        return _model_dump(result)

    @api.get("/api/projects/{project}/delivery-reports/{delivery_id}/push")
    def project_delivery_push_result(project: str, delivery_id: str) -> dict[str, object]:
        _require_project(project, root)
        result = load_delivery_push_result(project, delivery_id, workspace_root=root)
        if not result:
            raise HTTPException(
                status_code=404,
                detail={"error": "delivery_push_not_found", "message": f"Delivery push result not found: {delivery_id}"},
            )
        return _model_dump(result)

    @api.get("/api/projects/{project}/queues")
    def project_queues(project: str) -> dict[str, object]:
        _require_project(project, root)
        queues = list_execution_queues(project, workspace_root=root)
        return {"project": project, "count": len(queues), "queues": [_model_dump(queue) for queue in queues]}

    @api.get("/api/projects/{project}/queues/{queue_id}")
    def project_queue(project: str, queue_id: str) -> dict[str, object]:
        _require_project(project, root)
        queue = load_execution_queue(project, queue_id, workspace_root=root)
        if not queue:
            raise HTTPException(status_code=404, detail={"error": "queue_not_found", "message": f"Execution queue not found: {queue_id}"})
        return _model_dump(queue)

    @api.get("/api/projects/{project}/queues/{queue_id}/next")
    def project_queue_next(project: str, queue_id: str) -> dict[str, object]:
        _require_project(project, root)
        try:
            queue, item = get_queue_next_item(project, queue_id, workspace_root=root)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail={"error": "queue_not_found", "message": str(exc)}) from exc
        return {"project": project, "queue_id": queue.queue_id, "queue_status": queue.status, "item": _model_dump(item) if item else None}

    @api.get("/api/projects/{project}/queues/{queue_id}/worker-status")
    def project_queue_worker_status(project: str, queue_id: str, item_id: str | None = None) -> dict[str, object]:
        _require_project(project, root)
        try:
            status = get_codex_queue_worker_status(project, queue_id, item_id=item_id, workspace_root=root)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail={"error": "queue_not_found", "message": str(exc)}) from exc
        return _model_dump(status)

    @api.get("/api/projects/{project}/queues/{queue_id}/flow-summary")
    def project_queue_worker_flow_summary(project: str, queue_id: str, item_id: str | None = None) -> dict[str, object]:
        _require_project(project, root)
        try:
            summary = get_codex_worker_flow_summary(project, queue_id, item_id=item_id, workspace_root=root)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail={"error": "queue_not_found", "message": str(exc)}) from exc
        return _model_dump(summary)

    @api.get("/api/projects/{project}/queue-worker-runs")
    def project_queue_worker_runs(project: str) -> dict[str, object]:
        _require_project(project, root)
        runs = list_queue_worker_runs(project, workspace_root=root)
        return {"project": project, "count": len(runs), "queue_worker_runs": [_model_dump(run) for run in runs]}

    @api.get("/api/projects/{project}/queue-worker-runs/{run_id}")
    def project_queue_worker_run(project: str, run_id: str) -> dict[str, object]:
        _require_project(project, root)
        run = load_queue_worker_run(project, run_id, workspace_root=root)
        if not run:
            raise HTTPException(
                status_code=404,
                detail={"error": "queue_worker_run_not_found", "message": f"Queue worker run not found: {run_id}"},
            )
        return _model_dump(run)

    @api.get("/api/projects/{project}/handoffs")
    def project_handoffs(project: str) -> dict[str, object]:
        _require_project(project, root)
        handoffs = list_codex_handoffs(project, workspace_root=root)
        return {"project": project, "count": len(handoffs), "handoffs": [_model_dump(handoff) for handoff in handoffs]}

    @api.get("/api/projects/{project}/handoffs/{handoff_id}")
    def project_handoff(project: str, handoff_id: str) -> dict[str, object]:
        _require_project(project, root)
        handoff = load_codex_handoff(project, handoff_id, workspace_root=root)
        if not handoff:
            raise HTTPException(status_code=404, detail={"error": "handoff_not_found", "message": f"Codex handoff not found: {handoff_id}"})
        return _model_dump(handoff)

    @api.get("/api/projects/{project}/worker-runs")
    def project_worker_runs(project: str) -> dict[str, object]:
        _require_project(project, root)
        worker_runs = list_codex_worker_runs(project, workspace_root=root)
        return {"project": project, "count": len(worker_runs), "worker_runs": [_model_dump(worker_run) for worker_run in worker_runs]}

    @api.get("/api/projects/{project}/worker-runs/{worker_run_id}")
    def project_worker_run(project: str, worker_run_id: str) -> dict[str, object]:
        _require_project(project, root)
        worker_run = load_codex_worker_run(project, worker_run_id, workspace_root=root)
        if not worker_run:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_run_not_found", "message": f"Codex worker run not found: {worker_run_id}"},
            )
        return _model_dump(worker_run)

    @api.get("/api/projects/{project}/worker-runs/{worker_run_id}/execution")
    def project_worker_run_execution(project: str, worker_run_id: str) -> dict[str, object]:
        _require_project(project, root)
        worker_run = load_codex_worker_run(project, worker_run_id, workspace_root=root)
        if not worker_run:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_run_not_found", "message": f"Codex worker run not found: {worker_run_id}"},
            )
        log_path, stderr_log_path = worker_execution_log_paths(project, worker_run.worker_run_id, workspace_root=root)
        return {
            "project": project,
            "worker_run_id": worker_run.worker_run_id,
            "status": worker_run.status,
            "execution_exit_code": worker_run.execution_exit_code,
            "execution_command_label": worker_run.execution_command_label,
            "execution_started_by": worker_run.execution_started_by,
            "execution_log_path": worker_run.execution_log_path or str(log_path),
            "execution_stderr_log_path": worker_run.execution_stderr_log_path or str(stderr_log_path),
            "next_action": worker_run.next_action,
            "status_note": worker_run.status_note,
        }

    @api.get("/api/projects/{project}/worker-runs/{worker_run_id}/report")
    def project_worker_run_report(project: str, worker_run_id: str) -> dict[str, object]:
        _require_project(project, root)
        worker_run = load_codex_worker_run(project, worker_run_id, workspace_root=root)
        if not worker_run:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_run_not_found", "message": f"Codex worker run not found: {worker_run_id}"},
            )
        report = load_codex_worker_report(project, worker_run.worker_run_id, workspace_root=root)
        if not report:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_report_not_found", "message": f"Codex worker report not found: {worker_run_id}"},
            )
        return _model_dump(report)

    @api.get("/api/projects/{project}/worker-reports")
    def project_worker_reports(project: str) -> dict[str, object]:
        _require_project(project, root)
        reports = list_codex_worker_reports(project, workspace_root=root)
        return {"project": project, "count": len(reports), "reports": [_model_dump(report) for report in reports]}

    @api.get("/api/projects/{project}/worker-runs/{worker_run_id}/review")
    def project_worker_run_review(project: str, worker_run_id: str) -> dict[str, object]:
        _require_project(project, root)
        worker_run = load_codex_worker_run(project, worker_run_id, workspace_root=root)
        if not worker_run:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_run_not_found", "message": f"Codex worker run not found: {worker_run_id}"},
            )
        review = load_codex_worker_review(project, worker_run.worker_run_id, workspace_root=root)
        if not review:
            raise HTTPException(
                status_code=404,
                detail={"error": "worker_review_not_found", "message": f"Codex worker review not found: {worker_run_id}"},
            )
        return _model_dump(review)

    @api.get("/api/projects/{project}/worker-reviews")
    def project_worker_reviews(project: str) -> dict[str, object]:
        _require_project(project, root)
        reviews = list_codex_worker_reviews(project, workspace_root=root)
        return {"project": project, "count": len(reviews), "reviews": [_model_dump(review) for review in reviews]}

    @api.get("/api/projects/{project}/worker-run-plans")
    def project_worker_run_plans(project: str) -> dict[str, object]:
        _require_project(project, root)
        plans = list_codex_run_plans(project, workspace_root=root)
        return {"project": project, "count": len(plans), "run_plans": [_model_dump(plan) for plan in plans]}

    @api.get("/api/projects/{project}/worker-run-plans/{plan_id}")
    def project_worker_run_plan(project: str, plan_id: str) -> dict[str, object]:
        _require_project(project, root)
        plan = load_codex_run_plan(project, plan_id, workspace_root=root)
        if not plan:
            raise HTTPException(status_code=404, detail={"error": "worker_run_plan_not_found", "message": f"Codex run plan not found: {plan_id}"})
        return _model_dump(plan)

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

    @api.get("/api/projects/{project}/operator-console")
    def operator_console(project: str) -> dict[str, object]:
        _require_project(project, root)
        return _model_dump(build_operator_console_projection(project, workspace_root=root))

    @api.post("/api/projects/{project}/operator-console/intakes")
    def operator_console_create_intake(
        project: str,
        body: OperatorConsoleIntakeRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_create, "confirm_create")
        try:
            plan, json_path, markdown_path = create_rough_goal_intake_plan_from_text(
                project,
                body.goal_markdown,
                confirm_create=True,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "intake": _model_dump(plan),
            "artifact_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        }

    @api.post("/api/projects/{project}/operator-console/intakes/{intake_id}/materialize")
    def operator_console_materialize_intake(
        project: str,
        intake_id: str,
        body: OperatorConsoleMaterializeRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_materialize, "confirm_materialize")
        try:
            materialization, backlog, batch, queue, policy, json_path, markdown_path = materialize_rough_goal_intake_plan(
                project,
                intake_id,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "materialization": _model_dump(materialization),
            "review": {
                "backlog_tasks": [_model_dump(task) for task in backlog.tasks if task.id in materialization.created_task_ids],
                "batch": _model_dump(batch),
                "queue": _model_dump(queue),
                "source_policy": _model_dump(policy),
            },
            "artifact_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        }

    @api.post("/api/projects/{project}/operator-console/intakes/{intake_id}/prepare")
    def operator_console_prepare_intake(
        project: str,
        intake_id: str,
        body: OperatorConsolePrepareRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_prepare, "confirm_prepare")
        _require_confirmation(body.confirm_materialized_plan_reviewed, "confirm_materialized_plan_reviewed")
        if not body.reviewed_by.strip():
            raise _operator_console_request_error("reviewed_by is required to record who reviewed the materialized draft.")
        if body.confirm_supervised_delivery and not body.enable_supervised_delivery:
            raise _operator_console_request_error(
                "confirm_supervised_delivery requires enable_supervised_delivery."
            )
        if body.enable_supervised_delivery and not body.confirm_supervised_delivery:
            raise _operator_console_request_error(
                "Supervised delivery remains disabled without confirm_supervised_delivery."
            )
        if body.enable_supervised_delivery and not body.supervised_delivery_authorized_by.strip():
            raise _operator_console_request_error(
                "supervised_delivery_authorized_by is required for the audited opt-in."
            )
        if not body.enable_supervised_delivery and body.supervised_delivery_authorized_by.strip():
            raise _operator_console_request_error(
                "supervised_delivery_authorized_by is accepted only with the explicit supervised-delivery opt-in."
            )
        materialization = load_rough_goal_intake_materialization(project, intake_id, workspace_root=root)
        if not materialization:
            raise HTTPException(
                status_code=404,
                detail={"error": "materialization_not_found", "message": f"Rough goal materialization not found: {intake_id}"},
            )
        try:
            preparation, json_path, markdown_path = prepare_rough_goal_intake(
                project,
                intake_id,
                materialized_plan_reviewed_by=body.reviewed_by.strip(),
                supervised_delivery_authorized_by=(
                    body.supervised_delivery_authorized_by.strip() if body.enable_supervised_delivery else None
                ),
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "preparation": _model_dump(preparation),
            "materialization": _model_dump(materialization),
            "console": _model_dump(build_operator_console_projection(project, workspace_root=root)),
            "artifact_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        }

    @api.post("/api/projects/{project}/operator-console/intakes/{intake_id}/approve")
    def operator_console_approve_materialized_plan(
        project: str,
        intake_id: str,
        body: OperatorConsolePlanningApprovalRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_approve, "confirm_approve")
        approver = body.approver.strip()
        if not approver:
            raise _operator_console_request_error("approver is required to record planning authority.")
        note = body.note.strip()
        if not note:
            raise _operator_console_request_error("note is required to record the materialized-plan review.")
        materialization = load_rough_goal_intake_materialization(project, intake_id, workspace_root=root)
        if not materialization:
            raise HTTPException(
                status_code=404,
                detail={"error": "materialization_not_found", "message": f"Rough goal materialization not found: {intake_id}"},
            )
        if materialization.project != project or materialization.intake_id != intake_id:
            raise _operator_console_conflict("The materialization does not belong to the requested project and intake.")
        if body.batch_id != materialization.batch_id:
            raise _operator_console_conflict(
                f"Stale batch id {body.batch_id}; intake {intake_id} owns {materialization.batch_id}."
            )
        projection = build_operator_console_projection(project, workspace_root=root)
        if projection.active_goal and projection.active_goal.intake_id != intake_id:
            raise _operator_console_conflict(
                f"Prepared goal {projection.active_goal.intake_id} is active; planning approval for {intake_id} is not current."
            )
        batch = load_project_batch(project, materialization.batch_id, workspace_root=root)
        if not batch:
            raise _operator_console_conflict(f"Materialized batch is missing: {materialization.batch_id}.")
        if (
            batch.project != project
            or batch.batch_id != materialization.batch_id
            or batch.task_ids != materialization.created_task_ids
        ):
            raise _operator_console_conflict("The materialized batch authority has drifted from the active intake.")
        try:
            batch, batch_json, batch_markdown, approval, approval_json, approval_markdown, direct = approve_project_batch(
                project,
                materialization.batch_id,
                approver=approver,
                note=note,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "materialization": _model_dump(materialization),
            "batch": _model_dump(batch),
            "approval": _model_dump(approval),
            "direct_approval": direct,
            "artifact_paths": {
                "batch_json": str(batch_json),
                "batch_markdown": str(batch_markdown),
                "approval_json": str(approval_json),
                "approval_markdown": str(approval_markdown),
            },
        }

    @api.post("/api/projects/{project}/operator-console/goals/{intake_id}/approve")
    def operator_console_approve_goal(
        project: str,
        intake_id: str,
        body: OperatorConsoleApprovalRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_approve, "confirm_approve")
        approver = _require_operator_identity(body.approver, "approver")
        goal = _require_operator_console_action(
            project,
            intake_id,
            "approve_plan",
            workspace_root=root,
        )
        if body.bundle_id != goal.bundle_id:
            raise _operator_console_conflict(
                f"Stale bundle id {body.bundle_id}; the active reviewed goal requires {goal.bundle_id}."
            )
        try:
            bundle, json_path, markdown_path = approve_execution_policy_approval_bundle(
                project,
                goal.bundle_id,
                approver=approver,
                note=body.note,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "bundle": _model_dump(bundle),
            "console": _model_dump(build_operator_console_projection(project, workspace_root=root)),
            "artifact_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        }

    @api.post("/api/projects/{project}/operator-console/goals/{intake_id}/run")
    def operator_console_run_goal(
        project: str,
        intake_id: str,
        body: OperatorConsoleRunRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_run, "confirm_run")
        goal = _require_operator_console_action(
            project,
            intake_id,
            {"start_goal", "resume_goal", "record_validation"},
            workspace_root=root,
        )
        if body.bundle_id != goal.bundle_id:
            raise _operator_console_conflict(
                f"Stale bundle id {body.bundle_id}; the active reviewed goal requires {goal.bundle_id}."
            )
        try:
            preparation, result = supervise_prepared_goal(
                project,
                intake_id,
                message=body.message,
                note=body.note,
                max_steps=body.max_steps,
                poll_interval_seconds=body.poll_interval_seconds,
                max_wait_seconds=body.max_wait_seconds,
                dry_run=False,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "preparation": _model_dump(preparation),
            "result": _model_dump(result),
            "console": _model_dump(build_operator_console_projection(project, workspace_root=root)),
        }

    @api.post("/api/projects/{project}/operator-console/runs/{run_id}/review")
    def operator_console_review_worker(
        project: str,
        run_id: str,
        body: OperatorConsoleReviewRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_review, "confirm_review")
        recorded_by = _require_operator_identity(body.recorded_by, "recorded_by")
        _goal, _run = _require_operator_console_worker_action(
            project,
            run_id,
            body.bundle_id,
            "review_worker",
            workspace_root=root,
        )
        try:
            result = record_queue_worker_review(
                project,
                run_id,
                status=body.status,
                summary=body.summary,
                recorded_by=recorded_by,
                note=body.note,
                workspace_root=root,
            )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "review": _model_dump(result),
            "console": _model_dump(build_operator_console_projection(project, workspace_root=root)),
        }

    @api.post("/api/projects/{project}/operator-console/runs/{run_id}/recover")
    def operator_console_recover_worker(
        project: str,
        run_id: str,
        body: OperatorConsoleRecoveryRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_local_request(request)
        _require_project(project, root)
        _require_confirmation(body.confirm_recovery, "confirm_recovery")
        operator = body.operator.strip()
        reason = body.reason.strip()
        if not operator:
            raise _operator_console_request_error("operator is required to record recovery authority.")
        if not reason:
            raise _operator_console_request_error("reason is required for guarded recovery.")
        goal, _run = _require_operator_console_worker_action(
            project,
            run_id,
            body.bundle_id,
            body.action,
            workspace_root=root,
        )
        if goal.intake_id != body.intake_id:
            raise _operator_console_conflict(
                f"Prepared goal {body.intake_id} is not the active owner of queue-worker run {run_id}."
            )
        try:
            if body.action == "resume_worker":
                recovered, json_path, markdown_path = resume_queue_worker_run(
                    project,
                    run_id,
                    operator=operator,
                    reason=reason,
                    workspace_root=root,
                )
            else:
                recovered, json_path, markdown_path = retry_queue_worker_run(
                    project,
                    run_id,
                    operator=operator,
                    reason=reason,
                    workspace_root=root,
                )
        except ValueError as exc:
            raise _operator_console_domain_error(exc) from exc
        return {
            "action": body.action,
            "run": _model_dump(recovered),
            "console": _model_dump(build_operator_console_projection(project, workspace_root=root)),
            "artifact_paths": {"json": str(json_path), "markdown": str(markdown_path)},
        }

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


def _require_local_request(request: Request) -> None:
    client_host = request.client.host.strip().lower() if request.client and request.client.host else ""
    if client_host not in LOCAL_API_CLIENT_HOSTS:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "local_request_required",
                "message": "Operator-console mutations are available only to a localhost client.",
            },
        )


def _require_confirmation(confirmed: bool, field_name: str) -> None:
    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "confirmation_required",
                "message": f"Explicit {field_name}=true is required.",
            },
        )


def _require_operator_identity(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise _operator_console_request_error(
            f"{field_name} is required and must identify the human operator."
        )
    return normalized


def _operator_console_request_error(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error": "operator_console_request_invalid", "message": message})


def _operator_console_conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"error": "operator_console_state_conflict", "message": message})


def _operator_console_domain_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    if "not found" in message.casefold():
        return HTTPException(status_code=404, detail={"error": "operator_console_not_found", "message": message})
    return _operator_console_conflict(message)


def _require_operator_console_action(
    project_name: str,
    intake_id: str,
    action_ids: str | set[str],
    *,
    workspace_root: Path,
):
    projection = build_operator_console_projection(project_name, workspace_root=workspace_root)
    goal = projection.active_goal
    if not goal or goal.intake_id != intake_id:
        raise _operator_console_conflict(
            f"Prepared goal {intake_id} is not the active operator-console goal. Refresh console state."
        )
    expected = {action_ids} if isinstance(action_ids, str) else action_ids
    supported = {action.action_id for action in projection.supported_actions}
    if not expected & supported:
        raise _operator_console_conflict(
            "Requested action is not supported in the current goal state. Refresh console state and resolve blockers."
        )
    return goal


def _require_operator_console_worker_action(
    project_name: str,
    run_id: str,
    bundle_id: str,
    action_id: str,
    *,
    workspace_root: Path,
):
    projection = build_operator_console_projection(project_name, workspace_root=workspace_root)
    goal = projection.active_goal
    if not goal:
        raise _operator_console_conflict("No active prepared goal owns the requested queue-worker run.")
    if bundle_id != goal.bundle_id:
        raise _operator_console_conflict(
            f"Stale bundle id {bundle_id}; the active prepared goal requires {goal.bundle_id}."
        )
    if goal.current_queue_worker_run_id != run_id:
        raise _operator_console_conflict(
            f"Queue-worker run {run_id} is not the current run for the active prepared goal."
        )
    supported = {action.action_id for action in projection.supported_actions}
    if action_id not in supported:
        raise _operator_console_conflict(
            f"Action {action_id} is not supported for queue-worker run {run_id} in its current state."
        )
    run = load_queue_worker_run(project_name, run_id, workspace_root=workspace_root)
    if not run:
        raise _operator_console_conflict(f"Current queue-worker run is missing: {run_id}.")
    if not goal.current_policy_id or run.policy_id != goal.current_policy_id:
        raise _operator_console_conflict(
            f"Queue-worker run {run_id} is not bound to the active goal policy {goal.current_policy_id or 'none'}."
        )
    return goal, run


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
