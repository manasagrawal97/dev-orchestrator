from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.validation_registry import add_validation_command
from devo.work_packages import WorkPackageStatus, save_work_package, start_work_package

runner = CliRunner()


def test_devo_doctor_succeeds_with_minimal_workspace(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["doctor"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Devo doctor" in result.output
    assert "Devo workspace exists" in result.output
    assert "Overall status:" in result.output
    assert "Suggested next action:" in result.output


def test_project_doctor_reports_ok_for_valid_registered_project(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    _init_git_repo(project_path)
    add_validation_command(
        "sample",
        "dotnet-build-sample",
        "Build Sample",
        "dotnet build Sample.slnx",
        "build",
        workspace_root=workspace,
        approval_required=True,
        enabled=False,
    )
    package = start_work_package("sample", "low-risk-ui-maintenance", "Delivered package", workspace_root=workspace)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.DELIVERED, "commit_hash": "abc1234"}), workspace_root=workspace)

    result = runner.invoke(app, ["doctor", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Devo doctor: sample" in result.output
    assert "OK   Project registration" in result.output
    assert "OK   Project Git status" in result.output
    assert "Validation registry" in result.output
    assert "1 command(s)" in result.output
    assert "Recent work packages" in result.output


def test_project_doctor_reports_fail_for_missing_project_path(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, project_path=tmp_path / "missing-project")
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["doctor", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "FAIL Project path exists" in result.output
    assert "Overall status: FAIL" in result.output
    assert "Suggested next action: Update or re-register the project path." in result.output


def test_project_doctor_handles_missing_validation_registry(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)

    result = runner.invoke(app, ["doctor", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "WARN Validation registry" in result.output
    assert "0 command(s)" in result.output
    assert "Overall status:" in result.output


def test_doctor_reports_incomplete_backup_folders_as_warn(tmp_path: Path, monkeypatch) -> None:
    backup_root = tmp_path / "backups"
    incomplete = backup_root / "devo-workspace-backup-20260723-010000.incomplete"
    incomplete.mkdir(parents=True)
    _quiet_optional_checks(monkeypatch, tmp_path, backup_root=backup_root)

    result = runner.invoke(app, ["doctor"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "WARN Backup inventory" in result.output
    assert "incomplete=1" in result.output
    assert "Overall status: WARN" in result.output
    assert "incomplete backups usually mean interrupted/failed backup runs" in result.output


def test_doctor_handles_missing_optional_backup_config_without_crashing(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.delenv("DEVO_BACKUP_ROOT", raising=False)
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.setattr("devo.doctor.DEFAULT_BACKUP_ROOT", tmp_path / "missing-backup-root")

    result = runner.invoke(app, ["doctor"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "SKIP Backup root" in result.output
    assert "Overall status:" in result.output


def test_doctor_does_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_root, project_path = _workspace(tmp_path, monkeypatch)
    _quiet_optional_checks(monkeypatch, tmp_path)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert sentinel.read_text(encoding="utf-8") == before


def test_doctor_overall_status_reflects_warn_and_fail(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, project_path=tmp_path / "missing-project")
    backup_root = tmp_path / "backups"
    (backup_root / "devo-workspace-backup-20260723-010000.incomplete").mkdir(parents=True)
    _quiet_optional_checks(monkeypatch, tmp_path, backup_root=backup_root)

    result = runner.invoke(app, ["doctor", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "WARN Backup inventory" in result.output
    assert "FAIL Project path exists" in result.output
    assert "Overall status: FAIL" in result.output


def _workspace(tmp_path: Path, monkeypatch, project_path: Path | None = None) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    target = project_path or tmp_path / "target-project"
    if project_path is None:
        target.mkdir()
        (target / "README.md").write_text("# Sample\n", encoding="utf-8")

    project_dir = workspace / "projects" / "sample"
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True)
    approvals_dir.mkdir(parents=True)
    (workspace / "runs").mkdir(parents=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name="sample",
            path=target,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    context_path = context_dir / "context-state.json"
    context_path.write_text(
        ContextState(project_name="sample", project_path=target, status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    approval_path.write_text("{}", encoding="utf-8")
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path
    return workspace, target


def _quiet_optional_checks(monkeypatch, tmp_path: Path, backup_root: Path | None = None) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.setenv("DEVO_BACKUP_ROOT", str(backup_root or tmp_path / "backup-root"))


def _init_git_repo(project_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=project_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=project_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=project_path, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=project_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project_path, check=True, capture_output=True, text=True)
