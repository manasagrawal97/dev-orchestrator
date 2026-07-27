from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from devo.api import create_app, validate_api_host
from devo.main import app
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
