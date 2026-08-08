from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from devo.api import create_app, validate_api_host
from devo.main import app
from devo.project_planning import (
    approve_project_backlog,
    create_project_backlog,
    create_project_blueprint,
    create_project_brief,
    create_project_batch,
    create_codex_handoff_for_queue_next,
    create_codex_worker_run_from_handoff,
    create_codex_worker_run_plan,
    import_codex_worker_report,
    create_execution_queue_from_batch,
    generate_backlog_refinement_prompt,
    request_batch_approval,
)
from devo.runs import save_current_selection
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.validation_registry import add_validation_command
from devo.work_packages import start_work_package

runner = CliRunner()


def test_app_factory_creates_app(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    api = create_app(workspace_root=workspace)

    assert api.title == "DevOrchestrator API"


def test_health_returns_read_only_true(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "OK"
    assert response.json()["read_only"] is True


def test_current_works_without_current_context(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/current")

    assert response.status_code == 200
    data = response.json()
    assert data["project"] is None
    assert data["valid"] is True
    assert data["project_exists"] is False


def test_current_works_with_current_context(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "docs-only", "API current", workspace_root=workspace)
    save_current_selection("sample", run_id=package.run_id, workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/current")

    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "sample"
    assert data["run"] == package.run_id
    assert data["project_exists"] is True
    assert data["run_exists"] is True
    assert data["valid"] is True


def test_projects_lists_registered_projects(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["projects"][0]["name"] == "sample"
    assert data["projects"][0]["path"] == str(project_path)
    assert data["projects"][0]["path_exists"] is True


def test_project_overview_returns_json_for_valid_project(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    add_validation_command("sample", "git-diff-check", "Diff check", "git diff --check", "lint", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/overview")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "sample"
    assert data["validation_registry_summary"]["command_count"] == 1
    assert "suggested_next_action" in data
    assert "_timing" not in data


def test_project_brief_and_blueprint_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    brief = client.get("/api/projects/sample/brief")
    blueprint = client.get("/api/projects/sample/blueprint")

    assert brief.status_code == 200
    assert brief.json()["title"] == "Product"
    assert brief.json()["artifact_paths"]["json"].endswith("project-brief.json")
    assert blueprint.status_code == 200
    assert blueprint.json()["title"] == "Product Blueprint"
    assert len(blueprint.json()["milestones"]) == 1
    assert blueprint.json()["artifact_paths"]["markdown"].endswith("blueprint.md")


def test_project_backlog_and_task_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    approve_project_backlog("sample", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    backlog = client.get("/api/projects/sample/backlog")
    tasks = client.get("/api/projects/sample/tasks")
    task = client.get("/api/projects/sample/tasks/T001")

    assert backlog.status_code == 200
    assert backlog.json()["status"] == "approved"
    assert backlog.json()["task_count"] == 2
    assert backlog.json()["artifact_paths"]["json"].endswith("backlog.json")
    assert tasks.status_code == 200
    assert tasks.json()["count"] == 2
    assert tasks.json()["tasks"][0]["id"] == "T001"
    assert task.status_code == 200
    assert task.json()["id"] == "T001"
    assert task.json()["status"] == "ready"


def test_project_backlog_prompt_endpoint_returns_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    before = client.get("/api/projects/sample/backlog/prompt")
    generate_backlog_refinement_prompt("sample", workspace_root=workspace)
    after = client.get("/api/projects/sample/backlog/prompt")

    assert before.status_code == 200
    assert before.json()["exists"] is False
    assert before.json()["path"].endswith("backlog-refinement-prompt.md")
    assert "backlog-prompt" in before.json()["suggested_command"]
    assert after.status_code == 200
    assert after.json()["exists"] is True


def test_project_batch_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    request_batch_approval("sample", "B001", note="Ready for API review.", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    batches = client.get("/api/projects/sample/batches")
    approvals = client.get("/api/projects/sample/batch-approvals")
    batch = client.get("/api/projects/sample/batches/B001")
    approval = client.get("/api/projects/sample/batches/B001/approval")
    missing = client.get("/api/projects/sample/batches/B999")
    missing_approval = client.get("/api/projects/sample/batches/B999/approval")

    assert batches.status_code == 200
    assert batches.json()["count"] == 1
    assert batches.json()["batches"][0]["batch_id"] == "B001"
    assert approvals.status_code == 200
    assert approvals.json()["count"] == 1
    assert approvals.json()["approvals"][0]["approval_status"] == "requested"
    assert batch.status_code == 200
    assert batch.json()["title"] == "API batch"
    assert batch.json()["task_ids"] == ["T001"]
    assert approval.status_code == 200
    assert approval.json()["batch_id"] == "B001"
    assert approval.json()["review_status"] == "not_reviewed"
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "batch_not_found"
    assert missing_approval.status_code == 404
    assert missing_approval.json()["detail"]["error"] == "batch_approval_not_found"


def test_project_progress_endpoint_returns_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "sample"
    assert data["task_count"] == 2
    assert data["batch_count"] == 1
    assert "project_completion_percent" in data
    assert "milestone_progress" in data


def test_project_queue_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    batch, _batch_json, _batch_md = create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    approved = batch.model_copy(update={"status": "approved", "approval_status": "approved"})
    batch_json = workspace / "projects" / "sample" / "planning" / "batches" / "batch-B001.json"
    batch_json.write_text(approved.model_dump_json(indent=2), encoding="utf-8")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    queues = client.get("/api/projects/sample/queues")
    queue = client.get("/api/projects/sample/queues/Q001")
    next_item = client.get("/api/projects/sample/queues/Q001/next")
    missing = client.get("/api/projects/sample/queues/Q999")

    assert queues.status_code == 200
    assert queues.json()["count"] == 1
    assert queues.json()["queues"][0]["queue_id"] == "Q001"
    assert queue.status_code == 200
    assert queue.json()["source_batch_id"] == "B001"
    assert next_item.status_code == 200
    assert next_item.json()["item"]["item_id"] == "QI001"
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "queue_not_found"


def test_project_handoff_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    batch, _batch_json, _batch_md = create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    approved = batch.model_copy(update={"status": "approved", "approval_status": "approved"})
    batch_json = workspace / "projects" / "sample" / "planning" / "batches" / "batch-B001.json"
    batch_json.write_text(approved.model_dump_json(indent=2), encoding="utf-8")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    create_codex_handoff_for_queue_next("sample", "Q001", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    handoffs = client.get("/api/projects/sample/handoffs")
    handoff = client.get("/api/projects/sample/handoffs/H001")
    missing = client.get("/api/projects/sample/handoffs/H999")

    assert handoffs.status_code == 200
    assert handoffs.json()["count"] == 1
    assert handoffs.json()["handoffs"][0]["handoff_id"] == "H001"
    assert handoff.status_code == 200
    assert handoff.json()["handoff_type"] == "queue_next"
    assert handoff.json()["prompt_path"].endswith("handoff-H001.md")
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "handoff_not_found"


def test_project_worker_run_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    batch, _batch_json, _batch_md = create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    approved = batch.model_copy(update={"status": "approved", "approval_status": "approved"})
    batch_json = workspace / "projects" / "sample" / "planning" / "batches" / "batch-B001.json"
    batch_json.write_text(approved.model_dump_json(indent=2), encoding="utf-8")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    create_codex_handoff_for_queue_next("sample", "Q001", workspace_root=workspace)
    create_codex_worker_run_from_handoff("sample", "H001", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    worker_runs = client.get("/api/projects/sample/worker-runs")
    worker_run = client.get("/api/projects/sample/worker-runs/WR001")
    execution = client.get("/api/projects/sample/worker-runs/WR001/execution")
    missing = client.get("/api/projects/sample/worker-runs/WR999")

    assert worker_runs.status_code == 200
    assert worker_runs.json()["count"] == 1
    assert worker_runs.json()["worker_runs"][0]["worker_run_id"] == "WR001"
    assert worker_runs.json()["worker_runs"][0]["source_handoff_id"] == "H001"
    assert worker_run.status_code == 200
    assert worker_run.json()["status"] == "planned"
    assert worker_run.json()["report"]["report_status"] == "missing"
    assert execution.status_code == 200
    assert execution.json()["worker_run_id"] == "WR001"
    assert execution.json()["execution_exit_code"] is None
    assert execution.json()["execution_log_path"].endswith("worker-run-WR001.log")
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "worker_run_not_found"


def test_project_worker_report_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    batch, _batch_json, _batch_md = create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    approved = batch.model_copy(update={"status": "approved", "approval_status": "approved"})
    batch_json = workspace / "projects" / "sample" / "planning" / "batches" / "batch-B001.json"
    batch_json.write_text(approved.model_dump_json(indent=2), encoding="utf-8")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    create_codex_handoff_for_queue_next("sample", "Q001", workspace_root=workspace)
    create_codex_worker_run_from_handoff("sample", "H001", workspace_root=workspace)
    report_file = _worker_report_file(tmp_path, "WR001")
    import_codex_worker_report("sample", "WR001", report_file, workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    reports = client.get("/api/projects/sample/worker-reports")
    report = client.get("/api/projects/sample/worker-runs/WR001/report")
    missing = client.get("/api/projects/sample/worker-runs/WR999/report")

    assert reports.status_code == 200
    assert reports.json()["count"] == 1
    assert reports.json()["reports"][0]["worker_run_id"] == "WR001"
    assert report.status_code == 200
    assert report.json()["status_reported_by_worker"] == "completed"
    assert report.json()["changed_files"] == ["src/example.py"]
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "worker_run_not_found"


def test_project_worker_run_plan_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    batch, _batch_json, _batch_md = create_project_batch("sample", "API batch", ["T001"], workspace_root=workspace)
    approved = batch.model_copy(update={"status": "approved", "approval_status": "approved"})
    batch_json = workspace / "projects" / "sample" / "planning" / "batches" / "batch-B001.json"
    batch_json.write_text(approved.model_dump_json(indent=2), encoding="utf-8")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    create_codex_handoff_for_queue_next("sample", "Q001", workspace_root=workspace)
    create_codex_worker_run_from_handoff("sample", "H001", workspace_root=workspace)
    create_codex_worker_run_plan("sample", "WR001", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    plans = client.get("/api/projects/sample/worker-run-plans")
    plan = client.get("/api/projects/sample/worker-run-plans/RP001")
    missing = client.get("/api/projects/sample/worker-run-plans/RP999")

    assert plans.status_code == 200
    assert plans.json()["count"] == 1
    assert plans.json()["run_plans"][0]["plan_id"] == "RP001"
    assert plan.status_code == 200
    assert plan.json()["worker_run_id"] == "WR001"
    assert "preflight_status" in plan.json()
    assert missing.status_code == 404
    assert missing.json()["detail"]["error"] == "worker_run_plan_not_found"


def test_project_brief_and_blueprint_endpoints_return_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    brief = client.get("/api/projects/sample/brief")
    blueprint = client.get("/api/projects/sample/blueprint")
    backlog = client.get("/api/projects/sample/backlog")
    tasks = client.get("/api/projects/sample/tasks")

    assert brief.status_code == 404
    assert brief.json()["detail"]["error"] == "brief_not_found"
    assert blueprint.status_code == 404
    assert blueprint.json()["detail"]["error"] == "blueprint_not_found"
    assert backlog.status_code == 404
    assert backlog.json()["detail"]["error"] == "backlog_not_found"
    assert tasks.status_code == 404
    assert tasks.json()["detail"]["error"] == "backlog_not_found"


def test_project_task_endpoint_returns_404_for_missing_task(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    create_project_brief("sample", "Product", brief_file, workspace_root=workspace)
    create_project_blueprint("sample", workspace_root=workspace)
    create_project_backlog("sample", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/tasks/T999")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "task_not_found"


def test_project_overview_include_timing_returns_breakdown(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/overview?include_timing=true")

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "sample"
    assert "_timing" in data
    assert "total_ms" in data["_timing"]
    assert "doctor_ms" in data["_timing"]
    assert "activity_ms" in data["_timing"]
    assert "planning_ms" in data["_timing"]


def test_activity_and_doctor_include_timing_returns_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    activity = client.get("/api/projects/sample/activity?include_timing=true")
    doctor = client.get("/api/projects/sample/doctor?include_timing=true")

    assert activity.status_code == 200
    assert activity.json()["_timing"]["activity_ms"] >= 0
    assert doctor.status_code == 200
    assert doctor.json()["_timing"]["total_ms"] >= 0
    assert "backup_ms" in doctor.json()["_timing"]


def test_unknown_project_returns_404(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/missing/overview")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "project_not_found"


def test_run_overview_handles_missing_run_with_404(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/runs/missing-run/overview")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "run_not_found"


def test_work_package_endpoint_tolerates_missing_work_package_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run = start_work_package("sample", "docs-only", "Temporary package", workspace_root=workspace)
    package_path = workspace / "runs" / "sample" / run.run_id / "artifacts" / "work-package" / "work-package.json"
    package_path.unlink()
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get(f"/api/projects/sample/runs/{run.run_id}/work-package")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not available"
    assert data["scope_status"] == "missing work-package artifact"


def test_activity_and_doctor_endpoints_return_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    start_work_package("sample", "docs-only", "API activity", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    activity = client.get("/api/projects/sample/activity")
    doctor = client.get("/api/projects/sample/doctor")

    assert activity.status_code == 200
    assert activity.json()["project"] == "sample"
    assert doctor.status_code == 200
    assert doctor.json()["project"] == "sample"
    assert "overall_status" in doctor.json()
    assert "_timing" not in activity.json()
    assert "_timing" not in doctor.json()


def test_endpoints_do_not_mutate_target_repo_or_workspace(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "docs-only", "Read-only API", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))
    sentinel = project_path / "README.md"
    before_sentinel = sentinel.read_text(encoding="utf-8")
    before_workspace = _workspace_snapshot(workspace)

    client.get("/api/health")
    client.get("/api/current")
    client.get("/api/projects")
    client.get("/api/projects/sample/overview")
    client.get("/api/projects/sample/activity")
    client.get("/api/projects/sample/doctor")
    client.get(f"/api/projects/sample/runs/{package.run_id}/overview")
    client.get(f"/api/projects/sample/runs/{package.run_id}/work-package")

    assert sentinel.read_text(encoding="utf-8") == before_sentinel
    assert _workspace_snapshot(workspace) == before_workspace


def test_non_local_host_is_blocked() -> None:
    try:
        validate_api_host("0.0.0.0")
    except ValueError as exc:
        assert "local-only" in str(exc)
    else:
        raise AssertionError("Expected non-local host to be blocked.")


def test_api_routes_command_lists_read_only_endpoints(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["api", "routes"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "GET /api/health" in result.output
    assert "GET /api/projects/{project}/overview" in result.output
    assert "GET /api/projects/{project}/brief" in result.output
    assert "GET /api/projects/{project}/blueprint" in result.output
    assert "GET /api/projects/{project}/backlog" in result.output
    assert "GET /api/projects/{project}/backlog/prompt" in result.output
    assert "GET /api/projects/{project}/batches" in result.output
    assert "GET /api/projects/{project}/batch-approvals" in result.output
    assert "GET /api/projects/{project}/batches/{batch_id}" in result.output
    assert "GET /api/projects/{project}/batches/{batch_id}/approval" in result.output
    assert "GET /api/projects/{project}/progress" in result.output
    assert "GET /api/projects/{project}/queues" in result.output
    assert "GET /api/projects/{project}/queues/{queue_id}" in result.output
    assert "GET /api/projects/{project}/queues/{queue_id}/next" in result.output
    assert "GET /api/projects/{project}/handoffs" in result.output
    assert "GET /api/projects/{project}/handoffs/{handoff_id}" in result.output
    assert "GET /api/projects/{project}/worker-runs" in result.output
    assert "GET /api/projects/{project}/worker-runs/{worker_run_id}" in result.output
    assert "GET /api/projects/{project}/worker-runs/{worker_run_id}/execution" in result.output
    assert "GET /api/projects/{project}/worker-runs/{worker_run_id}/report" in result.output
    assert "GET /api/projects/{project}/worker-reports" in result.output
    assert "GET /api/projects/{project}/worker-run-plans" in result.output
    assert "GET /api/projects/{project}/worker-run-plans/{plan_id}" in result.output
    assert "GET /api/projects/{project}/tasks" in result.output


def test_api_serve_blocks_non_local_host(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["api", "serve", "--host", "0.0.0.0"], terminal_width=240)

    assert result.exit_code == 1
    assert "local-only" in result.output


def _workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.delenv("DEVO_BACKUP_ROOT", raising=False)
    project_path = tmp_path / "target-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    project_dir = workspace / "projects" / "sample"
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True)
    approvals_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name="sample",
            path=project_path,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    context_path = context_dir / "context-state.json"
    context_path.write_text(
        ContextState(project_name="sample", project_path=project_path, status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    approval_path.write_text("{}", encoding="utf-8")
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path
    return workspace, project_path


def _workspace_snapshot(workspace: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        snapshot[str(path.relative_to(workspace))] = path.read_text(encoding="utf-8")
    return snapshot


def _worker_report_file(tmp_path: Path, worker_run_id: str) -> Path:
    path = tmp_path / f"report-{worker_run_id}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "project": "sample",
                "worker_run_id": worker_run_id,
                "source_handoff_id": "H001",
                "source_queue_id": "Q001",
                "source_queue_item_id": "QI001",
                "source_task_id": "T001",
                "status_reported_by_worker": "completed",
                "summary": "Worker reported completion.",
                "changed_files": ["src/example.py"],
                "validation_attempted": True,
                "validation_results": ["Focused tests passed."],
                "tests_run": ["tests/test_example.py"],
                "commands_run": [],
                "commit_hash": None,
                "safety_warnings": [],
                "blockers": [],
                "follow_up_needed": [],
                "notes": [],
                "reported_at": "2026-07-22T00:00:00Z",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path
