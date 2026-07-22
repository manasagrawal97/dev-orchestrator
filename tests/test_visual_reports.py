from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.runs import create_run
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.work_packages import WorkPackageStatus, save_work_package, start_work_package

runner = CliRunner()


def test_visual_work_package_creates_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Polish dashboard help", workspace_root=workspace)
    save_work_package(
        package.model_copy(
            update={
                "status": WorkPackageStatus.DELIVERED,
                "approval_bundle_status": "approved",
                "validation_status": "passed",
                "commit_hash": "abc123456789",
            }
        ),
        workspace_root=workspace,
    )

    result = runner.invoke(app, ["visual", "work-package", "--project", "sample", "--run", package.run_id], terminal_width=240)

    artifact = workspace / "runs" / "sample" / package.run_id / "artifacts" / "visuals" / "work-package-flow.md"
    text = artifact.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "work-package-flow.md" in result.output
    assert artifact.exists()
    assert "```mermaid" in text
    assert "current_status: delivered" in text
    assert "approval_bundle_status: approved" in text
    assert "latest_validation_status: passed" in text
    assert "delivered_commit: abc123456789" in text
    assert "class delivered current" in text


def test_visual_work_package_handles_missing_optional_fields(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Draft package", workspace_root=workspace)
    package_path = workspace / "runs" / "sample" / package.run_id / "artifacts" / "work-package" / "work-package.json"
    data = json.loads(package_path.read_text(encoding="utf-8"))
    data.pop("approval_bundle_status", None)
    data.pop("validation_status", None)
    data.pop("commit_hash", None)
    package_path.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["visual", "work-package", "--project", "sample", "--run", package.run_id], terminal_width=240)

    artifact = workspace / "runs" / "sample" / package.run_id / "artifacts" / "visuals" / "work-package-flow.md"
    text = artifact.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "approval_bundle_status: not available" in text
    assert "delivered_commit: not available" in text


def test_visual_project_activity_creates_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Improve empty states", workspace_root=workspace)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.DELIVERED, "commit_hash": "def5678"}), workspace_root=workspace)

    result = runner.invoke(app, ["visual", "project-activity", "--project", "sample"], terminal_width=240)

    artifact = workspace / "projects" / "sample" / "visuals" / "project-activity.md"
    text = artifact.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "project-activity.md" in result.output
    assert "```mermaid" in text
    assert "Project Activity Visual: sample" in text
    assert "Improve empty states" in text
    assert "status: delivered" in text
    assert "commit: def5678" in text


def test_visual_project_activity_respects_limit(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    start_work_package("sample", "low-risk-ui-maintenance", "First package", workspace_root=workspace)
    start_work_package("sample", "low-risk-ui-maintenance", "Second package", workspace_root=workspace)
    start_work_package("sample", "low-risk-ui-maintenance", "Third package", workspace_root=workspace)

    result = runner.invoke(app, ["visual", "project-activity", "--project", "sample", "--limit", "2"], terminal_width=240)

    artifact = workspace / "projects" / "sample" / "visuals" / "project-activity.md"
    text = artifact.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "items_rendered: 2" in text
    assert text.count('["') == 2


def test_visual_project_activity_handles_old_runs_without_work_package(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run = create_run("sample", "Old planning run", workspace_root=workspace)

    result = runner.invoke(app, ["visual", "project-activity", "--project", "sample"], terminal_width=240)

    artifact = workspace / "projects" / "sample" / "visuals" / "project-activity.md"
    text = artifact.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert run.run_id in text or "Old planning run" in text
    assert "status: run:" in text


def test_visual_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")
    package = start_work_package("sample", "low-risk-ui-maintenance", "Polish help states", workspace_root=workspace)

    work_result = runner.invoke(app, ["visual", "work-package", "--project", "sample", "--run", package.run_id])
    activity_result = runner.invoke(app, ["visual", "project-activity", "--project", "sample"])

    assert work_result.exit_code == 0, work_result.output
    assert activity_result.exit_code == 0, activity_result.output
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
