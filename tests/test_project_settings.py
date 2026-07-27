from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.validation_registry import add_validation_command

runner = CliRunner()


def test_settings_show_works_with_no_settings(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["project", "settings-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project settings: sample" in result.output
    assert "Default lane: none" in result.output
    assert "settings.json" in result.output


def test_settings_set_writes_settings(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    add_validation_command(
        "sample",
        "dotnet-build-sample",
        "Build Sample",
        "dotnet build Sample.slnx",
        "build",
        workspace_root=workspace,
    )

    result = runner.invoke(
        app,
        [
            "project",
            "settings-set",
            "--project",
            "sample",
            "--default-lane",
            "low-risk-ui-maintenance",
            "--default-validation-command",
            "dotnet-build-sample",
            "--default-branch",
            "main",
            "--delivery-mode",
            "approved_commit_push",
            "--notes",
            "Use careful batches.",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    settings = json.loads((workspace / "projects" / "sample" / "settings.json").read_text(encoding="utf-8"))
    assert settings["default_lane"] == "low-risk-ui-maintenance"
    assert settings["default_validation_command"] == "dotnet-build-sample"
    assert settings["default_branch"] == "main"
    assert settings["delivery_mode"] == "approved_commit_push"
    assert settings["notes"] == "Use careful batches."


def test_settings_set_invalid_lane_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["project", "settings-set", "--project", "sample", "--default-lane", "not-a-lane"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Unknown work lane" in result.output


def test_settings_set_invalid_validation_command_fails_when_registry_exists(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    add_validation_command(
        "sample",
        "known-command",
        "Known",
        "git diff --check",
        "lint",
        workspace_root=workspace,
    )

    result = runner.invoke(
        app,
        ["project", "settings-set", "--project", "sample", "--default-validation-command", "missing-command"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Configured default validation command is not registered: missing-command" in result.output


def test_settings_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_root, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    result = runner.invoke(
        app,
        ["project", "settings-set", "--project", "sample", "--default-lane", "docs-only"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
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
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path
    return workspace, project_path
