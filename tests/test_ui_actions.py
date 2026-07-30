from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from devo.api import create_app
from devo.ui_actions import get_ui_action, is_action_allowed, list_allowed_ui_actions, list_ui_actions


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
    assert data["ui_mode"] == "read_only"
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


def test_allowed_actions_exclude_dangerous_and_workspace_safe(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/actions/allowed")

    assert response.status_code == 200
    data = response.json()
    action_ids = {action["id"] for action in data["actions"]}
    assert "project.overview.view" in action_ids
    assert "doctor.view" in action_ids
    assert "work.scope_template.generate" not in action_ids
    assert "git.push" not in action_ids
    assert all(not action["mutates_workspace"] for action in data["actions"])
    assert all(not action["mutates_target_project"] for action in data["actions"])


def test_list_allowed_ui_actions_matches_read_only_boundary() -> None:
    allowed = list_allowed_ui_actions()

    assert allowed
    assert all(action.category == "read_only" for action in allowed)
    assert all(action.allowed_in_ui_v1 for action in allowed)
    assert all(not action.mutates_workspace for action in allowed)
    assert all(not action.mutates_target_project for action in allowed)


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


def _workspace_snapshot(workspace: Path) -> dict[str, str]:
    return {str(path.relative_to(workspace)): path.read_text(encoding="utf-8") for path in workspace.rglob("*") if path.is_file()}
