from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.main import app
from devo.runs import load_run
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration, RunStatus
from devo.validation_registry import add_validation_command
from devo.work_packages import WorkPackageStatus, list_lanes, load_work_package, start_work_package

runner = CliRunner()


def test_work_start_creates_run_and_draft_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "start", "--project", "sample", "--lane", "low-risk-ui-maintenance", "--goal", "Polish warning cleanup"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run_id = _only_work_run(workspace)
    package = load_work_package("sample", run_id, workspace_root=workspace)
    paths = _package_paths(workspace, run_id)
    assert package.status == WorkPackageStatus.DRAFT
    assert package.lane == "low-risk-ui-maintenance"
    assert package.validation_commands == ["dotnet-build-personalos"]
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["operator_prompt"].exists()
    assert "devo work import-scope" in result.output


def test_work_import_scope_updates_package_and_tasks_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    scope = _scope_file(tmp_path)

    result = runner.invoke(
        app,
        ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(scope)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    updated = load_work_package("sample", package.run_id, workspace_root=workspace)
    run_state = load_run("sample", package.run_id, workspace_root=workspace)
    tasks_path = workspace / "runs" / "sample" / package.run_id / "artifacts" / "tasks.md"
    assert updated.status == WorkPackageStatus.SCOPE_PROPOSED
    assert updated.proposed_items == ["Convert button titles", "Refresh page labels"]
    assert updated.approved_files == ["src/web/App.razor", "src/web/Nav.razor"]
    assert updated.validation_commands == ["dotnet-build-personalos"]
    assert run_state.status == RunStatus.TASKS_DRAFTED
    assert tasks_path.exists()
    assert "## Task T001" in tasks_path.read_text(encoding="utf-8")


def test_work_status_reports_artifact_paths(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    _scope_file(tmp_path)

    result = runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Work package:" in result.output
    assert "Operator prompt:" in result.output
    assert "work-package.json" in result.output


def test_import_scope_requires_complete_sections(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    scope = tmp_path / "scope.md"
    scope.write_text("# Selected items\n\n- one item\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Scope file is missing required sections"):
        from devo.work_packages import import_work_scope

        import_work_scope("sample", package.run_id, scope, workspace_root=workspace)


def test_lane_registry_exposes_low_risk_ui_maintenance() -> None:
    lanes = {lane.id: lane for lane in list_lanes()}

    assert "low-risk-ui-maintenance" in lanes
    lane = lanes["low-risk-ui-maintenance"]
    assert "DB changes" in lane.forbidden
    assert "dotnet-build-personalos" in lane.default_validation_commands


def test_operator_prompt_contains_stop_conditions_and_delivery_rules(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])

    operator_prompt = _package_paths(workspace, package.run_id)["operator_prompt"].read_text(encoding="utf-8")

    assert "## Stop Conditions" in operator_prompt
    assert "## Final Report Format" in operator_prompt
    assert "Project path:" in operator_prompt
    assert "dotnet-build-personalos" in operator_prompt


def test_work_commands_do_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])
    runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id])

    assert sentinel.read_text(encoding="utf-8") == before


def _workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
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
    run_state = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert run_state.context_state_path == context_path
    add_validation_command(
        "sample",
        "dotnet-build-personalos",
        "Build PersonalOS",
        "dotnet build PersonalOS.slnx",
        "build",
        risk="high",
        approval_required=True,
        enabled=False,
        workspace_root=workspace,
    )
    return workspace, project_path


def _scope_file(tmp_path: Path) -> Path:
    scope = tmp_path / "scope.md"
    scope.write_text(
        "\n".join(
            [
                "# Selected items",
                "- Convert button titles",
                "- Refresh page labels",
                "",
                "# Exact files",
                "- src/web/App.razor",
                "- src/web/Nav.razor",
                "",
                "# Allowed changes",
                "- UI-only Razor markup updates",
                "",
                "# Forbidden changes",
                "- DB, migrations, appsettings, secrets, scripts, backups, user data",
                "",
                "# Validation command",
                "- dotnet-build-personalos",
                "",
                "# Delivery plan",
                "- Run build validation after approval",
                "- Commit and push after validation passes",
            ]
        ),
        encoding="utf-8",
    )
    return scope


def _only_work_run(workspace: Path) -> str:
    run_root = workspace / "runs" / "sample"
    run_ids = [path.name for path in run_root.iterdir() if path.is_dir()]
    assert len(run_ids) == 1
    return run_ids[0]


def _package_paths(workspace: Path, run_id: str) -> dict[str, Path]:
    root = workspace / "runs" / "sample" / run_id / "artifacts" / "work-package"
    return {
        "json": root / "work-package.json",
        "markdown": root / "work-package.md",
        "operator_prompt": root / "operator-prompt.md",
    }
