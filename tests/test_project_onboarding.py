from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import (
    ContextSnapshot,
    ContextState,
    ContextStatus,
    FileTreeSummary,
    GitInfo,
    ProjectRegistration,
    ProjectScanResult,
    ScanCategories,
    ScanLimits,
)
from devo.validation_registry import add_validation_command

runner = CliRunner()


def test_onboard_reports_unknown_project_clearly(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["project", "onboard", "--project", "missing"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Onboarding overall status: NOT_STARTED" in result.output
    assert "Registered project not found: missing" in result.output
    assert "devo project add --name missing --path <projectPath>" in result.output


def test_onboard_reports_registered_project_missing_scan_context_and_settings(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Onboarding overall status: IN_PROGRESS" in result.output
    assert "OK   Project registration" in result.output
    assert "WARN Project scan" in result.output
    assert "WARN Project context" in result.output
    assert "WARN Project settings" in result.output
    assert "Suggested next command: devo project scan sample" in result.output


def test_onboard_reports_ready_project(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    _write_scan(workspace, "sample")
    _write_context(workspace, "sample", ContextStatus.CONTEXT_APPROVED)
    add_validation_command(
        "sample",
        "dotnet-build-personalos",
        "Build",
        "dotnet build PersonalOS.slnx",
        "build",
        workspace_root=workspace,
    )
    _write_settings(workspace, "sample", default_lane="low-risk-ui-maintenance")

    result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Onboarding overall status: READY" in result.output
    assert "OK   Project scan" in result.output
    assert "OK   Project context" in result.output
    assert "OK   Validation registry" in result.output
    assert "OK   Project settings" in result.output
    assert 'Suggested next command: devo work new --project sample --goal "<goal>"' in result.output


def test_onboard_suggested_next_action_moves_from_context_to_validation_to_settings(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    _write_scan(workspace, "sample")

    context_result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)
    assert context_result.exit_code == 0, context_result.output
    assert "devo agent prompt ProjectContextDiscoveryAgent --project sample" in context_result.output

    _write_context(workspace, "sample", ContextStatus.CONTEXT_REVIEWED)
    approve_result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)
    assert approve_result.exit_code == 0, approve_result.output
    assert "devo project approve-context sample" in approve_result.output

    _write_context(workspace, "sample", ContextStatus.CONTEXT_APPROVED)
    validation_result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)
    assert validation_result.exit_code == 0, validation_result.output
    assert "devo validation suggest --project sample --write" in validation_result.output

    add_validation_command(
        "sample",
        "dotnet-build-personalos",
        "Build",
        "dotnet build PersonalOS.slnx",
        "build",
        workspace_root=workspace,
    )
    settings_result = runner.invoke(app, ["project", "onboard", "--project", "sample", "--suggest-settings"], terminal_width=240)
    assert settings_result.exit_code == 0, settings_result.output
    assert "devo project settings-set --project sample" in settings_result.output


def test_onboard_write_suggestions_creates_report(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["project", "onboard", "--project", "sample", "--write-suggestions"], terminal_width=240)

    report_path = workspace / "projects" / "sample" / "reports" / "onboarding-report.md"
    assert result.exit_code == 0, result.output
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "# Project Onboarding: sample" in text
    assert "Onboarding overall status:" in text


def test_onboard_suggest_settings_prints_without_writing_settings(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch, name="PersonalOS")
    _quiet_optional_checks(monkeypatch, tmp_path)
    _write_scan(workspace, "PersonalOS", dotnet=True)
    add_validation_command(
        "PersonalOS",
        "dotnet-build-personalos",
        "Build",
        "dotnet build PersonalOS.slnx",
        "build",
        workspace_root=workspace,
    )

    result = runner.invoke(app, ["project", "onboard", "--project", "PersonalOS", "--suggest-settings"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Suggested settings:" in result.output
    assert "--default-lane low-risk-ui-maintenance" in result.output
    assert "--default-validation-command dotnet-build-personalos" in result.output
    assert not (workspace / "projects" / "PersonalOS" / "settings.json").exists()


def test_onboard_does_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_root, project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    result = runner.invoke(app, ["project", "onboard", "--project", "sample", "--suggest-settings"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert sentinel.read_text(encoding="utf-8") == before


def test_onboard_handles_older_settings_missing_optional_fields(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    _write_scan(workspace, "sample")
    _write_context(workspace, "sample", ContextStatus.CONTEXT_APPROVED)
    add_validation_command("sample", "known-command", "Known", "git diff --check", "lint", workspace_root=workspace)
    settings_path = workspace / "projects" / "sample" / "settings.json"
    settings_path.write_text(
        json.dumps({"schema_version": "1", "project_name": "sample", "default_lane": "docs-only"}),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["project", "onboard", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Onboarding overall status: READY" in result.output


def _workspace(tmp_path: Path, monkeypatch, name: str = "sample") -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project_path = tmp_path / f"{name}-target"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    project_dir = workspace / "projects" / name
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True)
    approvals_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name=name,
            path=project_path,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    return workspace, project_path


def _quiet_optional_checks(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.setenv("DEVO_BACKUP_ROOT", str(tmp_path / "backup-root"))


def _write_scan(workspace: Path, project_name: str, dotnet: bool = False) -> None:
    project_file = workspace / "projects" / project_name / "project.json"
    registration = ProjectRegistration.model_validate_json(project_file.read_text(encoding="utf-8"))
    result = ProjectScanResult(
        project_name=project_name,
        project_path=registration.path,
        limits=ScanLimits(max_file_size_bytes=1_000_000, max_recorded_paths_per_category=100, max_tree_entries=250),
        file_tree=FileTreeSummary(scanned_file_count=3, scanned_directory_count=1),
        categories=ScanCategories(
            solution_files=["PersonalOS.slnx"] if dotnet else [],
            project_files=["src/App.csproj"] if dotnet else [],
            readme_docs_files=["README.md"],
        ),
        git=GitInfo(is_git_repo=True, current_branch="master" if project_name == "PersonalOS" else "main"),
    )
    (workspace / "projects" / project_name / "scan-result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")


def _write_context(workspace: Path, project_name: str, status: ContextStatus) -> None:
    project_file = workspace / "projects" / project_name / "project.json"
    registration = ProjectRegistration.model_validate_json(project_file.read_text(encoding="utf-8"))
    context_dir = workspace / "projects" / project_name / "context"
    approvals_dir = workspace / "projects" / project_name / "approvals"
    context_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    context_path = context_dir / "context-state.json"
    context_path.write_text(
        ContextState(project_name=project_name, project_path=registration.path, status=status).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    if status == ContextStatus.CONTEXT_APPROVED:
        approval_path.write_text("{}", encoding="utf-8")
    elif approval_path.exists():
        approval_path.unlink()
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path


def _write_settings(workspace: Path, project_name: str, default_lane: str) -> None:
    (workspace / "projects" / project_name / "settings.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "project_name": project_name,
                "default_lane": default_lane,
                "allow_auto_scope_template": True,
                "delivery_mode": "approved_commit_push",
            }
        ),
        encoding="utf-8",
    )
