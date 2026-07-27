from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_settings import update_project_settings
from devo.runs import load_current_selection
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.validation_registry import add_validation_command
from devo.work_packages import load_work_package, start_work_package

runner = CliRunner()


def test_current_prints_empty_state_when_no_current_context_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["current"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Current project: none" in result.output
    assert "Current run: none" in result.output
    assert "devo use --project <project>" in result.output


def test_use_sets_current_project_and_run(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Context work", workspace_root=workspace)

    result = runner.invoke(app, ["use", "--project", "sample", "--run", package.run_id], terminal_width=240)
    current_result = runner.invoke(app, ["current"], terminal_width=240)

    selection = load_current_selection(workspace_root=workspace)
    assert result.exit_code == 0, result.output
    assert "Current context updated." in result.output
    assert "Current project: sample" in result.output
    assert f"Current run: {package.run_id}" in result.output
    assert selection is not None
    assert selection.project_name == "sample"
    assert selection.run_id == package.run_id
    assert current_result.exit_code == 0, current_result.output
    assert "Project exists: yes" in current_result.output
    assert "Run exists: yes" in current_result.output


def test_work_resume_status_and_next_use_current_project_and_run(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Resume from current", workspace_root=workspace)
    runner.invoke(app, ["use", "--project", "sample", "--run", package.run_id], terminal_width=240)

    resume_result = runner.invoke(app, ["work", "resume"], terminal_width=240)
    status_result = runner.invoke(app, ["work", "status"], terminal_width=240)
    next_result = runner.invoke(app, ["work", "next"], terminal_width=240)

    assert resume_result.exit_code == 0, resume_result.output
    assert "Using current project: sample" in resume_result.output
    assert f"Using current run: {package.run_id}" in resume_result.output
    assert "# Work Resume:" in resume_result.output
    assert status_result.exit_code == 0, status_result.output
    assert "Work package:" in status_result.output
    assert next_result.exit_code == 0, next_result.output
    assert "Next action:" in next_result.output


def test_work_new_uses_current_project_when_project_omitted(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    update_project_settings("sample", default_lane="low-risk-ui-maintenance", workspace_root=workspace)
    runner.invoke(app, ["use", "--project", "sample"], terminal_width=240)

    result = runner.invoke(app, ["work", "new", "--goal", "Use current project"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Using current project: sample" in result.output
    run_ids = [path.name for path in (workspace / "runs" / "sample").iterdir() if path.is_dir()]
    assert len(run_ids) == 1
    package = load_work_package("sample", run_ids[0], workspace_root=workspace)
    assert package.project == "sample"


def test_doctor_uses_current_project_when_project_omitted(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    runner.invoke(app, ["use", "--project", "sample"], terminal_width=240)

    result = runner.invoke(app, ["doctor"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Using current project: sample" in result.output
    assert "Devo doctor: sample" in result.output


def test_project_activity_uses_current_project_when_project_omitted(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    runner.invoke(app, ["use", "--project", "sample"], terminal_width=240)

    result = runner.invoke(app, ["project", "activity"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Using current project: sample" in result.output
    assert "Project activity: sample" in result.output


def test_visual_work_package_uses_current_project_and_run(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Visual current", workspace_root=workspace)
    runner.invoke(app, ["use", "--project", "sample", "--run", package.run_id], terminal_width=240)

    result = runner.invoke(app, ["visual", "work-package"], terminal_width=240)

    artifact = workspace / "runs" / "sample" / package.run_id / "artifacts" / "visuals" / "work-package-flow.md"
    assert result.exit_code == 0, result.output
    assert "Using current project: sample" in result.output
    assert f"Using current run: {package.run_id}" in result.output
    assert artifact.exists()


def test_missing_current_project_fails_clearly_for_project_shortcut(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["work", "new", "--goal", "No project"], terminal_width=240)

    assert result.exit_code != 0
    assert "No project provided and no current project selected. Run: devo use --project <project>" in result.output


def test_missing_current_run_fails_clearly_for_run_shortcut(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    runner.invoke(app, ["use", "--project", "sample"], terminal_width=240)

    result = runner.invoke(app, ["work", "resume"], terminal_width=240)

    assert result.exit_code != 0
    assert "No run provided and no current run selected. Run: devo use --project <project> --run <runId>" in result.output


def test_explicit_project_and_run_override_current_context(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    other_workspace, _other_path = _workspace(tmp_path, monkeypatch, name="other")
    assert other_workspace == workspace
    sample_package = start_work_package("sample", "low-risk-ui-maintenance", "Sample work", workspace_root=workspace)
    other_package = start_work_package("other", "low-risk-ui-maintenance", "Other work", workspace_root=workspace)
    runner.invoke(app, ["use", "--project", "sample", "--run", sample_package.run_id], terminal_width=240)

    result = runner.invoke(
        app,
        ["work", "status", "--project", "other", "--run", other_package.run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Using current project" not in result.output
    assert "Using current run" not in result.output
    assert "Project: other" in result.output
    assert f"Work package: {other_package.run_id}" in result.output


def test_shortcut_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Read current", workspace_root=workspace)
    runner.invoke(app, ["use", "--project", "sample", "--run", package.run_id], terminal_width=240)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    runner.invoke(app, ["work", "status"], terminal_width=240)
    runner.invoke(app, ["work", "next"], terminal_width=240)
    runner.invoke(app, ["doctor"], terminal_width=240)

    assert sentinel.read_text(encoding="utf-8") == before


def _workspace(tmp_path: Path, monkeypatch, name: str = "sample") -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.setenv("DEVO_BACKUP_ROOT", str(tmp_path / "backup-root"))
    project_path = tmp_path / f"{name}-target-project"
    project_path.mkdir(exist_ok=True)
    (project_path / "README.md").write_text(f"# {name}\n", encoding="utf-8")

    project_dir = workspace / "projects" / name
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name=name,
            path=project_path,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    context_path = context_dir / "context-state.json"
    context_path.write_text(
        ContextState(project_name=name, project_path=project_path, status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    approval_path.write_text("{}", encoding="utf-8")
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path
    add_validation_command(
        name,
        "dotnet-build-personalos",
        "Build",
        "dotnet build PersonalOS.slnx",
        "build",
        workspace_root=workspace,
        approval_required=True,
        enabled=False,
    )
    return workspace, project_path
