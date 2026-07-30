from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from devo.api import create_app
from devo.project_settings import update_project_settings
from devo.schemas import ContextState, ContextStatus, ProjectRegistration
from devo.ui_actions import get_ui_action, is_action_allowed, list_allowed_ui_actions, list_ui_actions
from devo.work_packages import load_work_package, start_work_package


def test_action_registry_loads() -> None:
    actions = list_ui_actions()

    assert actions
    assert get_ui_action("project.overview.view") is not None
    assert get_ui_action("git.push") is not None


def test_dangerous_actions_are_blocked_or_deferred() -> None:
    dangerous = [action for action in list_ui_actions() if action.category == "dangerous_deferred"]

    assert dangerous
    assert all(action.status in {"blocked", "deferred"} for action in dangerous)
    assert all(not action.allowed_in_ui_v1 for action in dangerous)
    assert all(action.requires_approval for action in dangerous)


def test_read_only_actions_are_allowed_in_read_only_mode() -> None:
    overview = get_ui_action("project.overview.view")
    doctor = get_ui_action("doctor.view")

    assert overview is not None
    assert doctor is not None
    assert is_action_allowed(overview)
    assert is_action_allowed(doctor)


def test_workspace_safe_actions_are_not_allowed_in_ui_v1() -> None:
    template = get_ui_action("work.scope_template.generate")

    assert template is not None
    assert template.category == "workspace_safe"
    assert template.mutates_workspace is True
    assert not template.allowed_in_ui_v1
    assert not is_action_allowed(template)


def test_actions_endpoint_returns_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/actions")

    assert response.status_code == 200
    data = response.json()
    assert data["ui_mode"] == "controlled_workspace"
    assert data["count"] >= 10
    assert any(action["id"] == "validation.run" for action in data["actions"])


def test_action_detail_endpoint_returns_one_action(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/actions/work.scope_template.generate")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "work.scope_template.generate"
    assert data["category"] == "workspace_safe"
    assert data["allowed_in_ui_v1"] is False


def test_unknown_action_returns_404(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/actions/missing.action")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "action_not_found"


def test_allowed_actions_include_controlled_workspace_safe_but_exclude_dangerous(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/actions/allowed")

    assert response.status_code == 200
    data = response.json()
    action_ids = {action["id"] for action in data["actions"]}
    assert "project.overview.view" in action_ids
    assert "doctor.view" in action_ids
    assert "work.scope_template.generate" in action_ids
    assert "visual.project_activity.generate" in action_ids
    assert "work.new.create" in action_ids
    assert "git.push" not in action_ids
    assert all(not action["mutates_target_project"] for action in data["actions"])


def test_list_allowed_ui_actions_matches_read_only_boundary() -> None:
    allowed = list_allowed_ui_actions(ui_mode="read_only")

    assert allowed
    assert all(action.category == "read_only" for action in allowed)
    assert all(action.allowed_in_ui_v1 for action in allowed)
    assert all(not action.mutates_workspace for action in allowed)
    assert all(not action.mutates_target_project for action in allowed)


def test_execute_endpoint_requires_confirm_true(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.scope_template.generate", "project": "sample", "run_id": package.run_id, "confirm": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert "confirm=true" in data["message"]


def test_execute_allowed_workspace_safe_action_generates_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, target, package = _registered_workspace(tmp_path, monkeypatch)
    sentinel = target / "README.md"
    before_target = sentinel.read_text(encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.scope_template.generate", "project": "sample", "run_id": package.run_id, "confirm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["artifact_path"].endswith("scope-template.md")
    assert Path(data["artifact_path"]).exists()
    assert sentinel.read_text(encoding="utf-8") == before_target


def test_execute_work_new_requires_confirm_true(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.new.create", "project": "sample", "goal": "New package", "lane": "docs-only", "confirm": False},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED"
    assert "confirm=true" in response.json()["message"]


def test_execute_work_new_creates_run_and_package_with_explicit_lane(tmp_path: Path, monkeypatch) -> None:
    workspace, target, _package = _registered_workspace(tmp_path, monkeypatch)
    sentinel = target / "README.md"
    before_target = sentinel.read_text(encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={
            "action_id": "work.new.create",
            "project": "sample",
            "goal": "Create from UI",
            "lane": "low-risk-ui-maintenance",
            "confirm": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["project"] == "sample"
    assert data["lane"] == "low-risk-ui-maintenance"
    assert data["run_id"]
    assert data["artifact_path"].endswith("scope-template.md")
    assert "devo work resume --project sample --run" in data["suggested_next_command"]
    package = load_work_package("sample", data["run_id"], workspace_root=workspace)
    assert package.goal == "Create from UI"
    assert package.lane == "low-risk-ui-maintenance"
    assert Path(data["artifact_path"]).exists()
    assert sentinel.read_text(encoding="utf-8") == before_target


def test_execute_work_new_uses_project_default_lane_when_lane_omitted(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    update_project_settings("sample", default_lane="docs-only", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.new.create", "project": "sample", "goal": "Default lane package", "confirm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["lane"] == "docs-only"
    package = load_work_package("sample", data["run_id"], workspace_root=workspace)
    assert package.lane == "docs-only"


def test_execute_work_new_missing_goal_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.new.create", "project": "sample", "lane": "docs-only", "confirm": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "action_invalid"
    assert "goal is required" in response.json()["detail"]["message"]


def test_execute_work_new_missing_lane_and_default_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.new.create", "project": "sample", "goal": "Missing lane", "confirm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "FAIL"
    assert "No lane provided" in data["message"]
    assert "devo project settings-set --project sample --default-lane <lane>" == data["suggested_next_command"]


def test_execute_work_new_unknown_project_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "work.new.create", "project": "missing", "goal": "Unknown project", "lane": "docs-only", "confirm": True},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "action_invalid"
    assert "Registered project not found" in response.json()["detail"]["message"]


def test_execute_work_new_no_template_skips_scope_template(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={
            "action_id": "work.new.create",
            "project": "sample",
            "goal": "No template package",
            "lane": "docs-only",
            "confirm": True,
            "no_template": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["artifact_path"] is None
    assert not (workspace / "runs" / "sample" / data["run_id"] / "artifacts" / "work-package" / "scope-template.md").exists()


def test_execute_project_activity_visual_returns_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "visual.project_activity.generate", "project": "sample", "confirm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OK"
    assert data["artifact_path"].endswith("project-activity.md")
    assert Path(data["artifact_path"]).exists()


def test_execute_missing_project_or_run_returns_clear_error(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    missing_project = client.post(
        "/api/actions/execute",
        json={"action_id": "visual.project_activity.generate", "confirm": True},
    )
    missing_run = client.post(
        "/api/actions/execute",
        json={"action_id": "visual.work_package.generate", "project": "sample", "confirm": True},
    )

    assert missing_project.status_code == 400
    assert missing_project.json()["detail"]["error"] == "action_invalid"
    assert "project is required" in missing_project.json()["detail"]["message"]
    assert missing_run.status_code == 400
    assert "run_id is required" in missing_run.json()["detail"]["message"]


def test_execute_approval_required_action_is_blocked(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "validation.run", "project": "sample", "run_id": package.run_id, "confirm": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert "not available" in data["message"]


def test_execute_dangerous_action_is_blocked(tmp_path: Path, monkeypatch) -> None:
    workspace, _target, _package = _registered_workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "git.push", "project": "sample", "confirm": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "BLOCKED"


def test_execute_unknown_action_returns_404(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.post(
        "/api/actions/execute",
        json={"action_id": "missing.action", "project": "sample", "confirm": True},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "action_not_found"


def test_action_endpoints_do_not_mutate_workspace_or_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "README.md"
    sentinel.write_text("# Target\n", encoding="utf-8")
    before_workspace = _workspace_snapshot(workspace)
    before_target = sentinel.read_text(encoding="utf-8")
    client = TestClient(create_app(workspace_root=workspace))

    client.get("/api/actions")
    client.get("/api/actions/allowed")
    client.get("/api/actions/project.overview.view")
    client.get("/api/actions/git.push")

    assert _workspace_snapshot(workspace) == before_workspace
    assert sentinel.read_text(encoding="utf-8") == before_target


def _workspace(tmp_path: Path, monkeypatch) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    return workspace


def _registered_workspace(tmp_path: Path, monkeypatch):
    workspace = _workspace(tmp_path, monkeypatch)
    target = tmp_path / "target-project"
    target.mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    project_dir = workspace / "projects" / "sample"
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True)
    approvals_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name="sample",
            path=target,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (context_dir / "context-state.json").write_text(
        ContextState(project_name="sample", project_path=target, status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (approvals_dir / "context-approval.json").write_text("{}", encoding="utf-8")
    package = start_work_package("sample", "docs-only", "Generate workspace artifact", workspace_root=workspace)
    return workspace, target, package


def _workspace_snapshot(workspace: Path) -> dict[str, str]:
    return {str(path.relative_to(workspace)): path.read_text(encoding="utf-8") for path in workspace.rglob("*") if path.is_file()}
