from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.read_models import build_project_overview, build_project_overview_with_timing, build_run_overview, build_work_package_overview
from devo.runs import create_run, save_current_selection
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration
from devo.validation_registry import add_validation_command
from devo.work_packages import WorkPackageStatus, save_work_package, start_work_package

runner = CliRunner()


def test_project_overview_handles_valid_registered_project(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    add_validation_command("sample", "git-diff-check", "Diff check", "git diff --check", "lint", workspace_root=workspace)
    save_current_selection("sample", workspace_root=workspace)
    package = start_work_package("sample", "docs-only", "Docs package", workspace_root=workspace)

    overview = build_project_overview("sample", workspace_root=workspace)

    assert overview.project_name == "sample"
    assert overview.project_path is not None
    assert overview.is_current_project is True
    assert overview.validation_registry_summary["command_count"] == 1
    assert overview.brief_status == "missing"
    assert overview.backlog_status == "missing"
    assert overview.backlog_refinement_prompt_exists is False
    assert overview.batch_count == 0
    assert overview.approved_batch_count == 0
    assert overview.latest_batch_id is None
    assert overview.latest_batch_approval_status is None
    assert overview.batch_approval_requested_count == 0
    assert overview.batch_approved_count == 0
    assert overview.batch_rejected_count == 0
    assert overview.batch_needs_changes_count == 0
    assert overview.batch_approval_next_action
    assert overview.queue_count == 0
    assert overview.latest_queue_id is None
    assert overview.queue_pending_count == 0
    assert overview.handoff_count == 0
    assert overview.latest_handoff_id is None
    assert overview.handoff_next_action
    assert overview.project_completion_percent == 0.0
    assert overview.backlog_readiness_percent == 0.0
    assert overview.progress_next_action
    assert "brief-create" in overview.planning_next_action
    assert overview.recent_runs[0].run_id == package.run_id
    assert overview.recent_work_packages[0].run_id == package.run_id


def test_project_overview_with_timing_does_not_change_model_shape(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    overview, timing = build_project_overview_with_timing("sample", workspace_root=workspace)

    assert overview.project_name == "sample"
    assert "total_ms" in timing
    assert "doctor_ms" in timing
    assert "_timing" not in overview.model_dump()


def test_project_overview_handles_missing_optional_settings_validation_and_backup(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    monkeypatch.delenv("DEVO_BACKUP_ROOT", raising=False)

    overview = build_project_overview("sample", workspace_root=workspace)

    assert overview.settings_summary["status"] == "missing"
    assert overview.validation_registry_summary["status"] == "missing"
    assert overview.backup_summary["status"] == "SKIP"
    assert overview.recent_runs == []


def test_run_overview_handles_older_run_without_work_package(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run = create_run("sample", "Older workflow run", workspace_root=workspace)

    overview = build_run_overview("sample", run.run_id, workspace_root=workspace)

    assert overview.run_id == run.run_id
    assert overview.goal == "Older workflow run"
    assert overview.work_package_status == "not available"
    assert overview.work_package is None
    assert overview.suggested_next_action == "No work-package artifact found."


def test_work_package_overview_handles_missing_optional_delivery_fields(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Draft package", workspace_root=workspace)

    overview = build_work_package_overview("sample", package.run_id, workspace_root=workspace)

    assert overview.run_id == package.run_id
    assert overview.lane == "low-risk-ui-maintenance"
    assert overview.status == "draft"
    assert overview.approval_status == "not requested"
    assert overview.validation_status == "not available"
    assert overview.delivery_status == "not delivered"
    assert overview.next_phase


def test_json_output_is_valid_for_selected_commands(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    add_validation_command("sample", "git-diff-check", "Diff check", "git diff --check", "lint", workspace_root=workspace)
    package = start_work_package("sample", "docs-only", "JSON package", workspace_root=workspace)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.DELIVERED, "commit_hash": "abc1234"}), workspace_root=workspace)

    activity = runner.invoke(app, ["project", "activity", "--project", "sample", "--json"], terminal_width=240)
    work_status = runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id, "--json"], terminal_width=240)
    doctor = runner.invoke(app, ["doctor", "--project", "sample", "--json"], terminal_width=240)
    overview = runner.invoke(app, ["project", "overview", "--project", "sample", "--json"], terminal_width=240)

    assert activity.exit_code == 0, activity.output
    activity_data = json.loads(activity.output)
    assert activity_data["project_name"] == "sample"
    assert "recent_runs" in activity_data
    assert work_status.exit_code == 0, work_status.output
    work_data = json.loads(work_status.output)
    assert work_data["run_id"] == package.run_id
    assert work_data["delivery_status"] == "delivered: abc1234"
    assert doctor.exit_code == 0, doctor.output
    doctor_data = json.loads(doctor.output)
    assert doctor_data["project"] == "sample"
    assert "overall_status" in doctor_data
    assert overview.exit_code == 0, overview.output
    overview_data = json.loads(overview.output)
    assert overview_data["schema_version"] == "1"
    assert "brief_status" in overview_data
    assert "backlog_task_count" in overview_data
    assert "backlog_refinement_prompt_exists" in overview_data
    assert "batch_count" in overview_data
    assert "approved_batch_count" in overview_data
    assert "latest_batch_approval_status" in overview_data
    assert "batch_approval_requested_count" in overview_data
    assert "batch_approval_next_action" in overview_data
    assert "project_completion_percent" in overview_data
    assert "progress_next_action" in overview_data
    assert "queue_count" in overview_data
    assert "queue_next_action" in overview_data
    assert "handoff_count" in overview_data
    assert "handoff_next_action" in overview_data


def test_project_overview_includes_batch_approval_summary(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Ready."])

    overview = build_project_overview("sample")

    assert overview.batch_count == 1
    assert overview.latest_batch_id == "B001"
    assert overview.latest_batch_approval_status == "requested"
    assert overview.latest_batch_review_status == "not_reviewed"
    assert overview.batch_approval_requested_count == 1
    assert "batch-approval-show" in overview.batch_approval_next_action


def test_human_output_remains_default(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "docs-only", "Human package", workspace_root=workspace)

    result = runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert result.output.lstrip().startswith("Work package:")
    assert not result.output.lstrip().startswith("{")


def test_read_models_do_not_mutate_workspace_or_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")
    before_workspace = sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*"))

    build_project_overview("sample", workspace_root=workspace)
    build_run_overview("sample", "missing-run", workspace_root=workspace)
    build_work_package_overview("sample", "missing-run", workspace_root=workspace)

    after_workspace = sorted(str(path.relative_to(workspace)) for path in workspace.rglob("*"))
    assert sentinel.read_text(encoding="utf-8") == before
    assert after_workspace == before_workspace


def test_project_overview_marks_current_run_when_available(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "docs-only", "Current package", workspace_root=workspace)
    save_current_selection("sample", run_id=package.run_id, workspace_root=workspace)

    overview = build_project_overview("sample", workspace_root=workspace)

    assert overview.is_current_project is True
    assert overview.current_run_id == package.run_id


def _create_backlog(tmp_path: Path) -> None:
    brief_file = tmp_path / "brief.md"
    brief_file.write_text("# Product\n\n## Goals\n- Make planning visible\n", encoding="utf-8")
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-create", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])


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
