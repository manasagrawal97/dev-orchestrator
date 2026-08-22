from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.delivery import load_delivery_runner_request
from devo.main import app
from devo.project_planning import (
    BacklogTask,
    CodexWorkerReport,
    ProjectBacklog,
    build_project_intake_status,
    calculate_project_progress,
    create_execution_queue_from_batch,
    execution_policy_artifact_paths,
    generate_backlog_refinement_prompt,
    list_execution_policies,
    list_codex_handoffs,
    list_batch_approvals,
    list_execution_queues,
    list_queue_worker_runs,
    load_batch_approval,
    load_codex_handoff,
    load_codex_worker_run,
    list_project_batches,
    load_execution_queue,
    load_execution_policy,
    load_queue_worker_run,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
    project_batch_artifact_paths,
    batch_approval_artifact_paths,
    queue_artifact_paths,
    queue_worker_run_artifact_paths,
    request_queue_worker_delivery,
)
from devo.read_models import build_project_overview
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration

runner = CliRunner()


def test_brief_create_from_file_creates_json_and_markdown_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Project brief saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert paths.brief_json.exists()
    assert paths.brief_markdown.exists()
    data = json.loads(paths.brief_json.read_text(encoding="utf-8"))
    assert data["project"] == "sample"
    assert data["title"] == "Sample Product"
    assert data["status"] == "draft"
    assert data["goals"] == ["Track the work queue", "Show progress clearly"]
    assert "Original Brief Text" in paths.brief_markdown.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_brief_create_handles_utf8_bom_input_without_storing_bom(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = tmp_path / "bom-brief.md"
    brief_file.write_text("\ufeff# BOM Brief\n\nBuild reliable planning guidance.\n", encoding="utf-8")

    created = runner.invoke(
        app,
        ["project", "brief-create", "--project", "sample", "--title", "\ufeffBOM Product", "--file", str(brief_file)],
        terminal_width=240,
    )
    shown = runner.invoke(app, ["project", "brief-show", "--project", "sample"], terminal_width=240)

    assert created.exit_code == 0, created.output
    assert shown.exit_code == 0, shown.output
    brief = load_project_brief("sample", workspace_root=workspace)
    assert brief is not None
    assert brief.title == "BOM Product"
    assert "\ufeff" not in brief.summary
    assert "\ufeff" not in shown.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert "\ufeff" not in paths.brief_markdown.read_text(encoding="utf-8")


def test_brief_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "brief-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project brief: sample" in result.output
    assert "Status: draft" in result.output


def test_brief_approve_marks_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "brief-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project brief approved" in result.output
    brief = load_project_brief("sample", workspace_root=workspace)
    assert brief is not None
    assert brief.status == "approved"


def test_blueprint_create_creates_deterministic_draft_from_brief(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "blueprint-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert paths.blueprint_json.exists()
    assert paths.blueprint_markdown.exists()
    blueprint = load_project_blueprint("sample", workspace_root=workspace)
    assert blueprint is not None
    assert blueprint.status == "draft"
    assert len(blueprint.milestones) == 2
    assert len(blueprint.epics) == 2
    assert "no AI or Codex automation" in "\n".join(blueprint.architecture_notes)


def test_blueprint_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])

    result = runner.invoke(app, ["project", "blueprint-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint: sample" in result.output
    assert "Milestones: 2" in result.output
    assert "Epics: 2" in result.output


def test_blueprint_approve_marks_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])

    result = runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint approved" in result.output
    assert "backlog-create" in result.output
    blueprint = load_project_blueprint("sample", workspace_root=workspace)
    assert blueprint is not None
    assert blueprint.status == "approved"


def test_backlog_create_from_blueprint_creates_json_and_markdown_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_blueprint(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "backlog-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project backlog saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert paths.backlog_json.exists()
    assert paths.backlog_markdown.exists()
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    assert backlog.status == "draft"
    assert backlog.task_count == 2
    assert backlog.ready_task_count == 0
    assert [task.id for task in backlog.tasks] == ["T001", "T002"]
    assert backlog.tasks[0].epic_id == "E001"
    assert "Deterministic starter task" in paths.backlog_markdown.read_text(encoding="utf-8")
    assert "This is a deterministic starter backlog" in paths.backlog_markdown.read_text(encoding="utf-8")
    assert "backlog-prompt --project sample" in paths.backlog_markdown.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_backlog_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "backlog-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project backlog: sample" in result.output
    assert "Status: draft" in result.output
    assert "Tasks: 2" in result.output
    assert "not implementation-ready" in result.output
    assert "backlog-prompt --project sample" in result.output


def test_backlog_approve_marks_approved_and_tasks_ready(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "backlog-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project backlog approved" in result.output
    assert "batch-suggest --project sample --limit 10" in result.output
    assert "batch-suggest --project sample --limit 10 --write" in result.output
    assert "TASK-DEVO-077" not in result.output
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    assert backlog.status == "approved"
    assert backlog.ready_task_count == 2
    assert {task.status for task in backlog.tasks} == {"ready"}


def test_task_list_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "task-list", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Backlog tasks: sample" in result.output
    assert "T001" in result.output
    assert "lane=small-feature" in result.output


def test_task_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "task-show", "--project", "sample", "--task", "T001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Backlog task: T001" in result.output
    assert "Planning Foundation" in result.output
    assert "Validation expectations" in result.output


def test_backlog_prompt_creates_prompt_artifact_with_context_and_schema(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "backlog-prompt", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Backlog refinement prompt written" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    prompt = paths.backlog_refinement_prompt.read_text(encoding="utf-8")
    assert "Project Brief Summary" in prompt
    assert "Blueprint" in prompt
    assert "Current Backlog" in prompt
    assert "Required task fields" in prompt
    assert "Do not modify source code" in prompt
    assert "small-feature" in prompt
    assert _target_snapshot(project_path) == before_target


def test_backlog_prompt_fails_when_blueprint_or_backlog_missing(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    missing_blueprint = runner.invoke(app, ["project", "backlog-prompt", "--project", "sample"], terminal_width=240)
    assert missing_blueprint.exit_code != 0
    assert "Project blueprint not found" in missing_blueprint.output

    _create_blueprint(tmp_path)
    missing_backlog = runner.invoke(app, ["project", "backlog-prompt", "--project", "sample"], terminal_width=240)
    assert missing_backlog.exit_code != 0
    assert "Project backlog not found" in missing_backlog.output


def test_backlog_import_imports_valid_refined_backlog_as_draft(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    refined = _refined_backlog_file(tmp_path, workspace, status="approved", task_status="approved")
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "backlog-import", "--project", "sample", "--file", str(refined)], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Refined backlog imported" in result.output
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    assert backlog.status == "draft"
    assert backlog.task_count == 2
    assert backlog.ready_task_count == 0
    assert {task.status for task in backlog.tasks} == {"draft"}
    assert backlog.tasks[0].title == "Refined planning task"
    assert _target_snapshot(project_path) == before_target


def test_backlog_validate_accepts_valid_refined_backlog(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    refined = _refined_backlog_file(tmp_path, workspace)

    result = runner.invoke(app, ["project", "backlog-validate", "--project", "sample", "--file", str(refined)], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Valid: True" in result.output
    assert "Tasks: 2" in result.output


def test_backlog_import_rejects_duplicate_task_ids(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    refined = _refined_backlog_file(tmp_path, workspace, duplicate=True)

    result = runner.invoke(app, ["project", "backlog-import", "--project", "sample", "--file", str(refined)], terminal_width=240)
    validation = runner.invoke(app, ["project", "backlog-validate", "--project", "sample", "--file", str(refined)], terminal_width=240)

    assert result.exit_code != 0
    assert validation.exit_code != 0
    assert "Duplicate task id" in validation.output


def test_backlog_import_rejects_invalid_status_and_risk(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    refined = _refined_backlog_file(tmp_path, workspace, task_status="mystery", risk_level="spicy")

    result = runner.invoke(app, ["project", "backlog-import", "--project", "sample", "--file", str(refined)], terminal_width=240)

    assert result.exit_code != 0
    assert "Invalid status" in result.output
    assert "Invalid risk level" in result.output


def test_backlog_import_fails_for_unknown_project(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    refined = _refined_backlog_file(tmp_path, workspace, project="missing")

    result = runner.invoke(app, ["project", "backlog-import", "--project", "missing", "--file", str(refined)], terminal_width=240)

    assert result.exit_code != 0
    assert "Registered project not found" in result.output


def test_batch_create_creates_json_and_markdown_from_explicit_task_ids(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001,T002"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Project batch saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    batch_json = paths.batches_dir / "batch-B001.json"
    batch_md = paths.batches_dir / "batch-B001.md"
    assert batch_json.exists()
    assert batch_md.exists()
    assert paths.batch_index_json.exists()
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert batch.status == "draft"
    assert batch.approval_status == "not_requested"
    assert batch.task_ids == ["T001", "T002"]
    assert batch.task_count == 2
    assert batch.risk_summary == {"medium": 2}
    assert "Planning approval only" in batch_md.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_batch_create_rejects_unknown_task_ids(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(
        app,
        ["project", "batch-create", "--project", "sample", "--title", "Bad batch", "--tasks", "T999"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Backlog task id not found" in result.output


def test_batch_create_rejects_duplicate_task_ids(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(
        app,
        ["project", "batch-create", "--project", "sample", "--title", "Bad batch", "--tasks", "T001,T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Duplicate task ids" in result.output


def test_batch_suggest_suggests_ready_tasks(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])

    result = runner.invoke(app, ["project", "batch-suggest", "--project", "sample", "--limit", "1"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Batch suggestion: sample" in result.output
    assert "T001" in result.output
    assert "Suggested write command" in result.output


def test_batch_suggest_write_creates_draft_batch(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])

    result = runner.invoke(app, ["project", "batch-suggest", "--project", "sample", "--limit", "2", "--write"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Suggested project batch saved" in result.output
    batches = list_project_batches("sample", workspace_root=workspace)
    assert len(batches) == 1
    assert batches[0].batch_id == "B001"
    assert batches[0].task_count == 2


def test_batch_list_and_show_work(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])

    listed = runner.invoke(app, ["project", "batch-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["project", "batch-show", "--project", "sample", "--batch", "B001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "B001" in listed.output
    assert "First batch" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Project batch: B001" in shown.output
    assert "Included tasks" in shown.output


def test_batch_approve_marks_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])

    result = runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project batch approved" in result.output
    assert "Planning approval only" in result.output
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert batch.status == "approved"
    assert batch.approval_status == "approved"
    approval = load_batch_approval("sample", "B001", workspace_root=workspace)
    assert approval is not None
    assert approval.approval_status == "approved"
    assert "queue-create" in approval.next_action
    approval_json, approval_md = batch_approval_artifact_paths("sample", "B001", workspace_root=workspace)
    assert approval_json.exists()
    assert approval_md.exists()


def test_batch_approval_request_creates_artifacts_and_show_works(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])

    result = runner.invoke(
        app,
        ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Ready for review."],
        terminal_width=240,
    )
    shown = runner.invoke(app, ["project", "batch-approval-show", "--project", "sample", "--batch", "B001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Batch approval requested" in result.output
    assert shown.exit_code == 0, shown.output
    assert "Approval status: requested" in shown.output
    approval = load_batch_approval("sample", "B001", workspace_root=workspace)
    assert approval is not None
    assert approval.approval_status == "requested"
    assert approval.task_count == 1
    assert any("Ready for review." in note for note in approval.review_notes)
    approval_json, approval_md = batch_approval_artifact_paths("sample", "B001", workspace_root=workspace)
    assert approval_json.exists()
    assert "Safety Note" in approval_md.read_text(encoding="utf-8")


def test_batch_review_adds_note_and_marks_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])

    result = runner.invoke(app, ["project", "batch-review", "--project", "sample", "--batch", "B001", "--note", "Looks scoped."], terminal_width=240)

    assert result.exit_code == 0, result.output
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert batch.status == "reviewed"
    assert batch.review_status == "reviewed"
    assert any("Looks scoped." in note for note in batch.review_notes)


def test_batch_review_updates_approval_artifact_and_needs_changes(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Please review."])

    result = runner.invoke(
        app,
        ["project", "batch-review", "--project", "sample", "--batch", "B001", "--note", "Needs a smaller scope.", "--needs-changes"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    approval = load_batch_approval("sample", "B001", workspace_root=workspace)
    assert approval is not None
    assert approval.review_status == "needs_changes"
    assert any("Needs a smaller scope." in note for note in approval.review_notes)
    listed = runner.invoke(app, ["project", "batch-approval-list", "--project", "sample"], terminal_width=240)
    assert listed.exit_code == 0, listed.output
    assert "needs_changes" in listed.output


def test_batch_reject_marks_rejected_without_deleting_batch(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Please review."])

    result = runner.invoke(
        app,
        ["project", "batch-reject", "--project", "sample", "--batch", "B001", "--note", "Needs a safer split."],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Project batch rejected" in result.output
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    approval = load_batch_approval("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert approval is not None
    assert batch.approval_status == "rejected"
    assert approval.approval_status == "rejected"
    assert approval.review_status == "needs_changes"
    assert "Revise backlog/batch" in approval.next_action


def test_batch_create_includes_dependency_warnings(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    refined = _refined_backlog_file(tmp_path, workspace)
    runner.invoke(app, ["project", "backlog-import", "--project", "sample", "--file", str(refined)])

    result = runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "Dependent batch", "--tasks", "T102"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Dependency warnings" in result.output
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert batch.dependencies == ["T101"]
    assert batch.dependency_warnings


def test_batch_commands_fail_for_unknown_project_and_missing_backlog(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    unknown = runner.invoke(app, ["project", "batch-list", "--project", "missing"], terminal_width=240)
    missing_backlog = runner.invoke(app, ["project", "batch-suggest", "--project", "sample"], terminal_width=240)

    assert unknown.exit_code != 0
    assert "Registered project not found" in unknown.output
    assert missing_backlog.exit_code != 0
    assert "Project backlog not found" in missing_backlog.output


def test_progress_command_works_with_no_planning_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "progress", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project progress: sample" in result.output
    assert "Brief: missing" in result.output
    progress = calculate_project_progress("sample", workspace_root=workspace)
    assert progress.has_brief is False
    assert progress.project_completion_percent == 0.0
    assert "Project Brief is missing" in "\n".join(progress.warnings)
    assert _target_snapshot(project_path) == before_target


def test_progress_command_works_with_brief_and_blueprint_only(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_blueprint(tmp_path)

    progress = calculate_project_progress("sample", workspace_root=workspace)

    assert progress.has_brief is True
    assert progress.brief_status == "approved"
    assert progress.has_blueprint is True
    assert progress.blueprint_status == "approved"
    assert progress.has_backlog is False
    assert progress.task_count == 0
    assert "backlog-create" in progress.next_action


def test_progress_calculates_task_counts_and_percentages(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    _write_backlog_statuses(workspace, ["completed", "blocked", "approved", "ready", "draft", "superseded"])

    result = runner.invoke(app, ["project", "progress", "--project", "sample", "--json"], terminal_width=240)
    progress = calculate_project_progress("sample", workspace_root=workspace)
    data = json.loads(result.output)

    assert result.exit_code == 0, result.output
    assert progress.task_count == 6
    assert progress.active_task_count == 5
    assert progress.completed_task_count == 1
    assert progress.blocked_task_count == 1
    assert progress.approved_task_count == 1
    assert progress.ready_task_count == 1
    assert progress.draft_task_count == 1
    assert progress.project_completion_percent == 20.0
    assert progress.backlog_readiness_percent == 60.0
    assert progress.blocked_percent == 20.0
    assert data["project_completion_percent"] == 20.0


def test_progress_percent_handles_zero_active_tasks(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    _write_backlog_statuses(workspace, ["superseded", "superseded"])

    progress = calculate_project_progress("sample", workspace_root=workspace)

    assert progress.active_task_count == 0
    assert progress.project_completion_percent == 0.0
    assert progress.backlog_readiness_percent == 0.0
    assert progress.blocked_percent == 0.0


def test_progress_aggregates_milestone_and_epic_progress(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    _write_backlog_statuses(workspace, ["completed", "blocked"])

    progress = calculate_project_progress("sample", workspace_root=workspace)

    milestone = next(item for item in progress.milestone_progress if item.id == "M001")
    epic_1 = next(item for item in progress.epic_progress if item.id == "E001")
    epic_2 = next(item for item in progress.epic_progress if item.id == "E002")
    assert milestone.task_count == 2
    assert milestone.completed_task_count == 1
    assert milestone.blocked_task_count == 1
    assert milestone.completion_percent == 50.0
    assert epic_1.completed_task_count == 1
    assert epic_2.blocked_task_count == 1


def test_progress_aggregates_batch_progress(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "Second batch", "--tasks", "T002"])
    _write_batch_status(workspace, "B001", status="completed", approval_status="approved")
    _write_batch_status(workspace, "B002", status="approved", approval_status="approved")

    progress = calculate_project_progress("sample", workspace_root=workspace)

    assert progress.batch_count == 2
    assert progress.active_batch_count == 2
    assert progress.approved_batch_count == 2
    assert progress.completed_batch_count == 1
    assert progress.batch_completion_percent == 50.0


def test_intake_status_and_next_start_with_brief_guidance(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    status = runner.invoke(app, ["project", "intake-status", "--project", "sample"], terminal_width=240)
    next_result = runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240)
    model = build_project_intake_status("sample", workspace_root=workspace)

    assert status.exit_code == 0, status.output
    assert next_result.exit_code == 0, next_result.output
    assert "Project intake: sample" in status.output
    assert "Brief: missing" in status.output
    assert "Create a project brief" in next_result.output
    assert "brief-create" in next_result.output
    assert model.brief_status == "missing"
    assert model.next_command.startswith("devo project brief-create")
    assert _target_snapshot(project_path) == before_target


def test_intake_next_walks_operator_through_planning_pipeline(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)

    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    assert "brief-approve" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    assert "blueprint-create" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    assert "blueprint-approve" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])
    assert "backlog-create" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "backlog-create", "--project", "sample"])
    assert "backlog-approve" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])
    assert "batch-suggest" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    assert "batch-approval-request" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Ready."])
    assert "batch-approval-show" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"])
    assert "queue-create" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])
    assert "handoff-next" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output

    runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"])
    assert "worker codex run-create" in runner.invoke(app, ["project", "intake-next", "--project", "sample"], terminal_width=240).output


def test_intake_status_json_summarizes_existing_pipeline_state(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"])

    result = runner.invoke(app, ["project", "intake-status", "--project", "sample", "--json"], terminal_width=240)
    data = json.loads(result.output)

    assert result.exit_code == 0, result.output
    assert data["brief_status"] == "approved"
    assert data["blueprint_status"] == "approved"
    assert data["backlog_status"] == "approved"
    assert data["task_count"] == 2
    assert data["batch_count"] == 1
    assert data["latest_batch_id"] == "B001"
    assert data["latest_batch_approval_status"] == "approved"
    assert data["queue_count"] == 1
    assert data["latest_queue_id"] == "Q001"
    assert data["handoff_count"] == 1
    assert data["latest_handoff_id"] == "H001"
    assert "worker codex run-create" in data["next_command"]


def test_intake_template_prints_and_writes_workspace_artifact_only(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    shown = runner.invoke(app, ["project", "intake-template", "--project", "sample"], terminal_width=240)
    written = runner.invoke(app, ["project", "intake-template", "--project", "sample", "--write"], terminal_width=240)

    assert shown.exit_code == 0, shown.output
    assert "## Problem / Goal" in shown.output
    assert "## Validation Expectations" in shown.output
    assert written.exit_code == 0, written.output
    path = planning_artifact_paths("sample", workspace_root=workspace).planning_dir / "intake-template.md"
    assert path.exists()
    assert "## Delivery Expectations" in path.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_intake_prompt_prints_idea_and_writes_workspace_artifact_only(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    shown = runner.invoke(
        app,
        ["project", "intake-prompt", "--project", "sample", "--idea", "Improve vision intake."],
        terminal_width=240,
    )
    written = runner.invoke(
        app,
        ["project", "intake-prompt", "--project", "sample", "--idea", "Improve vision intake.", "--write"],
        terminal_width=240,
    )

    assert shown.exit_code == 0, shown.output
    assert "Improve vision intake." in shown.output
    assert "Project brief draft" in shown.output
    assert "Batch suggestion" in shown.output
    assert "Phase 1 is not autonomous" in shown.output
    assert written.exit_code == 0, written.output
    path = planning_artifact_paths("sample", workspace_root=workspace).planning_dir / "intake-prompt.md"
    assert path.exists()
    assert "Current Suggested Next Devo Action" in path.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_queue_create_from_approved_batch_creates_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Execution queue saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    queue_json = paths.queues_dir / "queue-Q001.json"
    queue_md = paths.queues_dir / "queue-Q001.md"
    assert queue_json.exists()
    assert queue_md.exists()
    assert paths.queue_index_json.exists()
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "ready"
    assert queue.item_count == 2
    assert queue.pending_count == 2
    assert queue.items[0].task_id == "T001"
    assert "state is tracking only" in queue_md.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_execution_policy_create_creates_draft_policy_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        [
            "project",
            "execution-policy-create",
            "--project",
            "sample",
            "--batch",
            "B001",
            "--title",
            "Safe policy",
            "--allowed-task",
            "T001",
            "--allowed-file",
            "docs/**",
            "--forbidden-file",
            ".env",
            "--max-tasks",
            "1",
            "--max-tasks-per-run",
            "1",
            "--max-changed-files-per-task",
            "20",
            "--validation-command",
            "git diff --check",
            "--note",
            "Create draft only.",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Execution policy saved" in result.output
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    assert policy.status == "draft"
    assert policy.batch_id == "B001"
    assert policy.allowed_task_ids == ["T001"]
    assert policy.allowed_file_patterns == ["docs/**"]
    assert policy.forbidden_file_patterns == [".env"]
    assert policy.max_tasks == 1
    assert policy.validation_commands == ["git diff --check"]
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    assert json_path.exists()
    assert markdown_path.exists()
    assert "bounded approval contract" in markdown_path.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_execution_policy_create_validates_batch_and_records_queue(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    missing = runner.invoke(
        app,
        ["project", "execution-policy-create", "--project", "sample", "--batch", "B999", "--title", "Missing"],
        terminal_width=240,
    )
    created = runner.invoke(
        app,
        [
            "project",
            "execution-policy-create",
            "--project",
            "sample",
            "--batch",
            "B001",
            "--queue",
            "Q001",
            "--title",
            "Queued policy",
            "--allowed-task",
            "T001",
        ],
        terminal_width=240,
    )

    assert missing.exit_code != 0
    assert "Project batch not found" in missing.output
    assert created.exit_code == 0, created.output
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    assert policy.queue_id == "Q001"
    assert policy.allowed_queue_item_ids == ["QI001"]


def test_execution_policy_request_approve_reject_list_show_and_check(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(
        app,
        [
            "project",
            "execution-policy-create",
            "--project",
            "sample",
            "--batch",
            "B001",
            "--queue",
            "Q001",
            "--title",
            "Approval policy",
            "--allowed-task",
            "T001",
            "--allowed-file",
            "src/**",
            "--forbidden-file",
            ".env",
            "--validation-command",
            "pytest",
        ],
    )

    requested = runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", "POL-0001", "--note", "Ready."], terminal_width=240)
    approved = runner.invoke(
        app,
        ["project", "execution-policy-approve", "--project", "sample", "--policy", "POL-0001", "--approver", "Manas", "--note", "Approved bounds."],
        terminal_width=240,
    )
    listed = runner.invoke(app, ["project", "execution-policy-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["project", "execution-policy-show", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)
    checked = runner.invoke(app, ["project", "execution-policy-check", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert requested.exit_code == 0, requested.output
    assert approved.exit_code == 0, approved.output
    assert "Execution policy approved" in approved.output
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    assert policy.status == "approved"
    assert policy.approver == "Manas"
    assert "TASK-DEVO-129" in policy.next_action
    assert listed.exit_code == 0, listed.output
    assert "POL-0001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Approval policy" in shown.output
    assert checked.exit_code == 0, checked.output
    assert "Usable: True" in checked.output

    runner.invoke(app, ["project", "execution-policy-create", "--project", "sample", "--batch", "B001", "--title", "Rejected policy", "--allowed-task", "T001"])
    runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", "POL-0002"])
    rejected = runner.invoke(
        app,
        ["project", "execution-policy-reject", "--project", "sample", "--policy", "POL-0002", "--reviewer", "Manas", "--note", "Too broad."],
        terminal_width=240,
    )
    assert rejected.exit_code == 0, rejected.output
    rejected_policy = load_execution_policy("sample", "POL-0002", workspace_root=workspace)
    assert rejected_policy is not None
    assert rejected_policy.status == "rejected"
    assert len(list_execution_policies("sample", workspace_root=workspace)) == 2


def test_execution_policy_request_refuses_empty_allowed_scope(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path, task_ids="")

    runner.invoke(app, ["project", "execution-policy-create", "--project", "sample", "--batch", "B001", "--title", "Empty policy"], terminal_width=240)
    result = runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", "POL-0001", "--note", "Ready."], terminal_width=240)

    assert result.exit_code != 0
    assert "must include allowed tasks" in result.output
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    assert policy.status == "draft"


def test_execution_policy_check_blocks_expired_missing_refs_and_auto_push_without_delivery(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(
        app,
        [
            "project",
            "execution-policy-create",
            "--project",
            "sample",
            "--batch",
            "B001",
            "--queue",
            "Q001",
            "--title",
            "Broken policy",
            "--allowed-task",
            "T001",
            "--no-auto-delivery",
            "--expires-at",
            "2000-01-01T00:00:00+00:00",
        ],
    )
    runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", "POL-0001"])
    runner.invoke(app, ["project", "execution-policy-approve", "--project", "sample", "--policy", "POL-0001", "--approver", "Manas"])
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    broken = policy.model_copy(update={"batch_id": "B999", "queue_id": "Q999", "allowed_task_ids": ["T999"], "allowed_queue_item_ids": ["QI999"]})
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    json_path.write_text(broken.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("broken test policy\n", encoding="utf-8")

    result = runner.invoke(app, ["project", "execution-policy-check", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "Policy expired" in result.output
    assert "Referenced batch not found" in result.output
    assert "Referenced queue not found" in result.output
    assert "auto_push_allowed requires auto_delivery_allowed" in result.output


def test_execution_policy_check_blocks_missing_allowed_task(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(
        app,
        [
            "project",
            "execution-policy-create",
            "--project",
            "sample",
            "--batch",
            "B001",
            "--queue",
            "Q001",
            "--title",
            "Stale policy",
            "--allowed-task",
            "T001",
        ],
    )
    runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", "POL-0001"])
    runner.invoke(app, ["project", "execution-policy-approve", "--project", "sample", "--policy", "POL-0001", "--approver", "Manas"])
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    stale = policy.model_copy(update={"allowed_task_ids": ["T999"]})
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    json_path.write_text(stale.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("stale test policy\n", encoding="utf-8")

    result = runner.invoke(app, ["project", "execution-policy-check", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "Allowed tasks missing from batch B001: T999" in result.output


def test_queue_worker_plan_blocks_missing_and_draft_policy(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    missing = runner.invoke(app, ["project", "queue-worker-plan", "--project", "sample", "--policy", "POL-999"], terminal_width=240)
    _create_execution_policy(tmp_path, allowed_task="T001", request=False, approve=False)
    draft = runner.invoke(app, ["project", "queue-worker-plan", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert missing.exit_code != 0
    assert "Execution policy not found" in missing.output
    assert draft.exit_code != 0
    assert "Policy status is draft" in draft.output
    assert "Usable: False" in draft.output


def test_queue_worker_plan_shows_usable_approved_policy(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")

    result = runner.invoke(app, ["project", "queue-worker-plan", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Queue worker plan: POL-0001" in result.output
    assert "Usable: True" in result.output
    assert "Selected item: QI001" in result.output
    assert "Selected task: T001" in result.output
    assert "queue-worker-run --project sample --policy POL-0001 --once --confirm-queue-worker" in result.output


def test_queue_worker_run_requires_confirmation_and_blocks_unapproved_or_expired_policy(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001", request=False, approve=False)

    missing_confirm = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once"],
        terminal_width=240,
    )
    draft = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )

    assert missing_confirm.exit_code != 0
    assert "requires --confirm-queue-worker" in missing_confirm.output
    assert draft.exit_code != 0
    assert "Queue worker run: QWR-0001" in draft.output
    assert "Policy status is draft" in draft.output
    assert load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace) is not None

    _create_execution_policy(tmp_path, allowed_task="T001", expires_at="2000-01-01T00:00:00+00:00")
    expired = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0002", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )

    assert expired.exit_code != 0
    assert "Policy expired" in expired.output


def test_queue_worker_run_creates_artifacts_handoff_and_worker_without_completing_item(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker", "--approver", "Manas"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Queue worker run: QWR-0001" in result.output
    assert "Status: waiting_worker" in result.output
    assert "No real Codex CLI was executed" in result.output
    queue_worker_run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert queue_worker_run is not None
    assert queue_worker_run.selected_queue_item_id == "QI001"
    assert queue_worker_run.selected_task_id == "T001"
    assert queue_worker_run.selected_handoff_id == "H001"
    assert queue_worker_run.selected_worker_run_id == "WR001"
    json_path, markdown_path = queue_worker_run_artifact_paths("sample", "QWR-0001", workspace_root=workspace)
    assert json_path.exists()
    assert markdown_path.exists()
    handoff = load_codex_handoff("sample", "H001", workspace_root=workspace)
    worker = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert handoff is not None
    assert handoff.source_queue_id == "Q001"
    assert handoff.source_item_id == "QI001"
    assert worker is not None
    assert worker.mode == "manual_handoff"
    assert worker.status == "planned"
    assert worker.source_queue_item_id == "QI001"
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.items[0].status == "pending"
    assert _target_snapshot(project_path) == before_target


def test_queue_worker_run_selects_next_allowed_item_and_processes_only_one(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T002")

    result = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    queue_worker_run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert queue_worker_run is not None
    assert queue_worker_run.selected_queue_item_id == "QI002"
    assert queue_worker_run.selected_task_id == "T002"
    assert queue_worker_run.selected_worker_run_id == "WR001"
    assert len(list_queue_worker_runs("sample", workspace_root=workspace)) == 1
    assert len(list_codex_handoffs("sample", workspace_root=workspace)) == 1
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert [item.status for item in queue.items] == ["pending", "pending"]


def test_queue_worker_run_ignores_terminal_items_and_reports_no_ready_item(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001,T002")
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    updated_items = [
        queue.items[0].model_copy(update={"status": "completed"}),
        queue.items[1].model_copy(update={"status": "blocked"}),
    ]
    updated = queue.model_copy(update={"items": updated_items})
    json_path, _markdown_path = queue_artifact_paths("sample", "Q001", workspace_root=workspace)
    json_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Status: no_ready_item" in result.output
    assert "QI001: item status is completed" in result.output
    assert "QI002: item status blocked requires review or manual recovery" in result.output
    assert list_codex_handoffs("sample", workspace_root=workspace) == []


def test_queue_worker_run_blocks_missing_policy_references(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    broken = policy.model_copy(update={"batch_id": "B999", "queue_id": "Q999", "allowed_task_ids": ["T999"], "allowed_queue_item_ids": ["QI999"]})
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    json_path.write_text(broken.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("broken queue worker policy\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Referenced batch not found: B999" in result.output
    assert "Referenced queue not found: Q999" in result.output


def test_queue_worker_list_show_latest_work(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])

    listed = runner.invoke(app, ["project", "queue-worker-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["project", "queue-worker-show", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)
    latest = runner.invoke(app, ["project", "queue-worker-latest", "--project", "sample"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "QWR-0001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Queue worker run: QWR-0001" in shown.output
    assert latest.exit_code == 0, latest.output
    assert "Queue worker run: QWR-0001" in latest.output


def test_queue_worker_status_handles_no_runs_without_mutating_target(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "queue-worker-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest run: none" in result.output
    assert "queue-worker-plan --project sample --policy <POL-ID>" in result.output
    assert _target_snapshot(project_path) == before_target


def test_queue_worker_status_shows_waiting_worker_missing_evidence(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])

    result = runner.invoke(app, ["project", "queue-worker-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest run: QWR-0001" in result.output
    assert "Status: waiting_worker" in result.output
    assert "Worker result/report not imported." in result.output
    assert "Worker review not recorded." not in result.output
    assert "report-import --project sample --run WR001" in result.output


def test_queue_worker_pause_records_paused_state_and_reason(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])

    result = runner.invoke(
        app,
        ["project", "queue-worker-pause", "--project", "sample", "--run", "QWR-0001", "--reason", "operator review"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "paused"
    assert run.pause_reason == "operator review"
    assert run.paused_at is not None
    assert "queue-worker-resume --project sample --run QWR-0001 --confirm-resume" in run.next_action


def test_queue_worker_resume_requires_confirmation_and_rechecks_policy(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])
    runner.invoke(app, ["project", "queue-worker-pause", "--project", "sample", "--run", "QWR-0001", "--reason", "pause"])

    missing_confirm = runner.invoke(app, ["project", "queue-worker-resume", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)
    assert missing_confirm.exit_code != 0
    assert "requires --confirm-resume" in missing_confirm.output

    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    stale = policy.model_copy(update={"status": "draft"})
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    json_path.write_text(stale.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("draft test policy\n", encoding="utf-8")

    resumed = runner.invoke(
        app,
        ["project", "queue-worker-resume", "--project", "sample", "--run", "QWR-0001", "--confirm-resume"],
        terminal_width=240,
    )

    assert resumed.exit_code != 0
    assert "Status: blocked" in resumed.output
    assert "Policy status is draft" in resumed.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "blocked"


def test_queue_worker_fail_records_failed_state_and_reason(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])

    result = runner.invoke(
        app,
        ["project", "queue-worker-fail", "--project", "sample", "--run", "QWR-0001", "--reason", "worker output unclear"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "failed"
    assert run.failure_reason == "worker output unclear"
    assert run.failed_at is not None
    assert "queue-worker-retry --project sample --run QWR-0001 --confirm-retry" in run.next_action


def test_queue_worker_retry_requires_confirmation_and_creates_linked_attempt(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])
    runner.invoke(app, ["project", "queue-worker-fail", "--project", "sample", "--run", "QWR-0001", "--reason", "retry test"])

    missing_confirm = runner.invoke(app, ["project", "queue-worker-retry", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)
    assert missing_confirm.exit_code != 0
    assert "requires --confirm-retry" in missing_confirm.output

    result = runner.invoke(
        app,
        ["project", "queue-worker-retry", "--project", "sample", "--run", "QWR-0001", "--confirm-retry"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    retry = load_queue_worker_run("sample", "QWR-0002", workspace_root=workspace)
    original = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert retry is not None
    assert original is not None
    assert original.status == "failed"
    assert retry.retry_of == "QWR-0001"
    assert retry.selected_queue_item_id == "QI001"
    assert retry.selected_worker_run_id is None
    assert "run-create --project sample --handoff H001" in retry.next_action


def test_queue_worker_retry_blocks_when_selected_item_no_longer_valid(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    runner.invoke(app, ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"])
    runner.invoke(app, ["project", "queue-worker-fail", "--project", "sample", "--run", "QWR-0001", "--reason", "retry test"])
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    stale = queue.model_copy(update={"items": [queue.items[0].model_copy(update={"status": "completed"}), queue.items[1]]})
    json_path, markdown_path = queue_artifact_paths("sample", "Q001", workspace_root=workspace)
    json_path.write_text(stale.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("stale queue\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["project", "queue-worker-retry", "--project", "sample", "--run", "QWR-0001", "--confirm-retry"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "item status is completed" in result.output
    assert load_queue_worker_run("sample", "QWR-0002", workspace_root=workspace) is None


def test_queue_worker_evidence_shows_missing_report_without_mutating_target(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    _create_queue_worker_run(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["project", "queue-worker-evidence", "--project", "sample", "--run", "QWR-0001"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Queue worker evidence: QWR-0001" in result.output
    assert "Worker report exists: False" in result.output
    assert "Worker result/report not imported." in result.output
    assert "evidence inspection is read-only" in result.output
    assert _target_snapshot(project_path) == before_target


def test_queue_worker_continue_requires_confirmation(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_queue_worker_run(tmp_path)

    result = runner.invoke(app, ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "requires --confirm-continue" in result.output


def test_queue_worker_continue_blocks_failed_worker_report(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue_worker_run(tmp_path)
    _import_worker_report(tmp_path, status="failed")

    result = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Status: failed" in result.output
    assert "Worker report says failed." in result.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "failed"
    assert "queue-worker-retry" in run.next_action


def test_queue_worker_continue_advances_review_validation_and_delivery_readiness(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue_worker_run(tmp_path)
    _import_worker_report(tmp_path)

    waiting_review = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    _record_worker_review(status="reviewed_passed")
    waiting_validation = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    _attach_validation(status="passed")
    ready = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )

    assert waiting_review.exit_code == 0
    assert "Status: waiting_review" in waiting_review.output
    assert waiting_validation.exit_code == 0
    assert "Status: waiting_validation" in waiting_validation.output
    assert ready.exit_code == 0, ready.output
    assert "Status: ready_for_delivery_request" in ready.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "ready_for_delivery_request"
    assert "queue-worker-request-delivery" in run.next_action


def test_queue_worker_request_delivery_requires_confirmation_and_ready_state(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_queue_worker_run(tmp_path)

    missing_confirm = runner.invoke(
        app,
        ["project", "queue-worker-request-delivery", "--project", "sample", "--run", "QWR-0001"],
        terminal_width=240,
    )
    not_ready = runner.invoke(
        app,
        [
            "project",
            "queue-worker-request-delivery",
            "--project",
            "sample",
            "--run",
            "QWR-0001",
            "--confirm-delivery-request",
        ],
        terminal_width=240,
    )

    assert missing_confirm.exit_code != 0
    assert "requires --confirm-delivery-request" in missing_confirm.output
    assert not_ready.exit_code != 0
    assert "waiting_worker" in not_ready.output


def test_queue_worker_request_delivery_rechecks_policy_before_request(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_ready_queue_worker_run(tmp_path)
    policy = load_execution_policy("sample", "POL-0001", workspace_root=workspace)
    assert policy is not None
    json_path, markdown_path = execution_policy_artifact_paths("sample", "POL-0001", workspace_root=workspace)
    json_path.write_text(policy.model_copy(update={"status": "draft"}).model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text("draft policy\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Policy status is draft"):
        request_queue_worker_delivery("sample", "QWR-0001", workspace_root=workspace)


def test_queue_worker_request_delivery_creates_runner_request_without_commit_or_push(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _init_git_repo(project_path)
    _create_ready_queue_worker_run(tmp_path)
    (project_path / "src").mkdir()
    (project_path / "src" / "feature.py").write_text("print('safe')\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "project",
            "queue-worker-request-delivery",
            "--project",
            "sample",
            "--run",
            "QWR-0001",
            "--message",
            "feat: complete queue worker task",
            "--note",
            "TASK-DEVO-131 test request.",
            "--confirm-delivery-request",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Runner request: REQ-0001" in result.output
    assert "No runner-watch, guarded commit, guarded push, or queue completion was run." in result.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert request is not None
    assert run.status == "delivery_requested"
    assert run.delivery_request_id == "REQ-0001"
    assert run.delivery_request_status == "requested"
    assert request.status == "requested"
    assert request.intended_commit_message == "feat: complete queue worker task"
    assert request.expected_changed_files == ["src/feature.py"]
    assert _git(project_path, "status", "--short", capture=True).stdout == "?? src/\n"
    assert _git(project_path, "log", "--oneline", "-n", "1", capture=True).stdout.strip().endswith("initial")


def test_queue_worker_assisted_e2e_flow(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _init_git_repo(project_path)

    _create_queue_worker_run(tmp_path)
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "waiting_worker"

    _import_worker_report(tmp_path)
    waiting_review = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    assert waiting_review.exit_code == 0, waiting_review.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "waiting_review"

    _record_worker_review(status="reviewed_passed")
    waiting_validation = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    assert waiting_validation.exit_code == 0, waiting_validation.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "waiting_validation"

    _attach_validation(status="passed")
    ready = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    assert ready.exit_code == 0, ready.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "ready_for_delivery_request"

    (project_path / "src").mkdir()
    (project_path / "src" / "feature.py").write_text("print('assisted dogfood')\n", encoding="utf-8")
    requested = runner.invoke(
        app,
        [
            "project",
            "queue-worker-request-delivery",
            "--project",
            "sample",
            "--run",
            "QWR-0001",
            "--message",
            "feat: assisted queue worker dogfood",
            "--note",
            "TASK-DEVO-132 sandbox dogfood.",
            "--confirm-delivery-request",
        ],
        terminal_width=240,
    )

    assert requested.exit_code == 0, requested.output
    run = load_queue_worker_run("sample", "QWR-0001", workspace_root=workspace)
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert request is not None
    assert run.status == "delivery_requested"
    assert run.delivery_request_id == "REQ-0001"
    assert request.status == "requested"
    assert request.expected_changed_files == ["src/feature.py"]
    shown = runner.invoke(app, ["project", "queue-worker-show", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)
    latest = runner.invoke(app, ["project", "queue-worker-latest", "--project", "sample"], terminal_width=240)
    status = runner.invoke(app, ["project", "queue-worker-status", "--project", "sample"], terminal_width=240)
    evidence = runner.invoke(app, ["project", "queue-worker-evidence", "--project", "sample", "--run", "QWR-0001"], terminal_width=240)
    for result in (shown, latest, status, evidence):
        assert result.exit_code == 0, result.output
        assert "REQ-0001" in result.output
        assert "requested" in result.output
    assert _git(project_path, "log", "--oneline", "-n", "1", capture=True).stdout.strip().endswith("initial")


def test_queue_worker_plan_read_only_does_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    _create_execution_policy(tmp_path, allowed_task="T001")
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["project", "queue-worker-plan", "--project", "sample", "--policy", "POL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert _target_snapshot(project_path) == before_target


def test_queue_create_rejects_unapproved_and_unknown_batch(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "Draft batch", "--tasks", "T001"])

    unapproved = runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"], terminal_width=240)
    unknown = runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B999"], terminal_width=240)

    assert unapproved.exit_code != 0
    assert "must be approved" in unapproved.output
    assert unknown.exit_code != 0
    assert "Project batch not found" in unknown.output


def test_queue_list_and_show_work(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    listed = runner.invoke(app, ["project", "queue-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["project", "queue-show", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "Q001" in listed.output
    assert "batch=B001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Execution queue: Q001" in shown.output
    assert "QI001" in shown.output


def test_queue_start_moves_to_running_and_marks_first_item(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    result = runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "running"
    assert queue.current_item_id == "QI001"
    assert queue.items[0].status == "running"
    assert queue.running_count == 1


def test_queue_next_shows_current_or_next_item(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    before_start = runner.invoke(app, ["project", "queue-next", "--project", "sample", "--queue", "Q001"], terminal_width=240)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])
    after_start = runner.invoke(app, ["project", "queue-next", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert before_start.exit_code == 0, before_start.output
    assert "QI001" in before_start.output
    assert after_start.exit_code == 0, after_start.output
    assert "Status: running" in after_start.output
    assert "devo project handoff-next --project sample --queue Q001" in after_start.output
    assert "devo project handoff-task --project sample --task T001" in after_start.output
    assert "<queueId>" not in after_start.output
    assert "<project>" not in after_start.output


def test_queue_complete_item_marks_completed_and_advances(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    result = runner.invoke(
        app,
        ["project", "queue-complete-item", "--project", "sample", "--queue", "Q001", "--item", "QI001", "--note", "Done."],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "running"
    assert queue.current_item_id == "QI002"
    assert queue.items[0].status == "completed"
    assert queue.items[1].status == "running"
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    assert backlog.tasks[0].status == "completed"


def test_queue_complete_item_completes_queue_when_all_done(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])
    runner.invoke(app, ["project", "queue-complete-item", "--project", "sample", "--queue", "Q001", "--item", "QI001", "--note", "Done."])

    result = runner.invoke(app, ["project", "queue-complete-item", "--project", "sample", "--queue", "Q001", "--item", "QI002", "--note", "Done."], terminal_width=240)

    assert result.exit_code == 0, result.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "completed"
    assert queue.current_item_id is None
    assert queue.completed_count == 2


def test_queue_block_item_marks_blocked_and_waiting_review(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    result = runner.invoke(app, ["project", "queue-block-item", "--project", "sample", "--queue", "Q001", "--item", "QI001", "--note", "Needs review."], terminal_width=240)

    assert result.exit_code == 0, result.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "waiting_review"
    assert queue.items[0].status == "blocked"
    assert queue.blocked_count == 1
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    assert backlog.tasks[0].status == "blocked"


def test_queue_pause_usage_limit_and_resume(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    paused = runner.invoke(app, ["project", "queue-pause", "--project", "sample", "--queue", "Q001", "--reason", "usage_limit", "--note", "Resume when usage resets."], terminal_width=240)
    resumed = runner.invoke(app, ["project", "queue-resume", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert paused.exit_code == 0, paused.output
    assert resumed.exit_code == 0, resumed.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "running"
    assert queue.current_item_id == "QI001"
    assert queue.items[0].status == "running"


def test_empty_queue_edge_case_starts_as_completed(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path, task_ids="")
    queue, _json_path, _markdown_path = create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)

    started = runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", queue.queue_id], terminal_width=240)

    assert started.exit_code == 0, started.output
    loaded = load_execution_queue("sample", queue.queue_id, workspace_root=workspace)
    assert loaded is not None
    assert loaded.status == "completed"
    assert loaded.item_count == 0


def test_handoff_next_creates_prompt_from_running_queue_item(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)
    _create_queue(tmp_path)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    result = runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Codex handoff prompt saved" in result.output
    assert "paste this prompt into Codex" in result.output
    handoffs = list_codex_handoffs("sample", workspace_root=workspace)
    assert len(handoffs) == 1
    handoff = handoffs[0]
    assert handoff.handoff_type == "queue_next"
    assert handoff.source_queue_id == "Q001"
    assert handoff.source_item_id == "QI001"
    prompt = Path(handoff.prompt_path).read_text(encoding="utf-8")
    assert "Do not exceed this task/batch scope." in prompt
    assert "Do not touch PersonalOS unless the selected project is PersonalOS and the task explicitly says so." in prompt
    assert "Acceptance Criteria" in prompt
    assert "Validation Expectations" in prompt
    assert str(project_path) in prompt
    assert _target_snapshot(project_path) == before_target


def test_handoff_next_creates_prompt_from_pending_item_if_none_running(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_queue(tmp_path)

    result = runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    handoff = list_codex_handoffs("sample", workspace_root=workspace)[0]
    assert handoff.source_item_id == "QI001"
    assert handoff.source_task_id == "T001"


def test_handoff_next_fails_for_missing_empty_and_completed_queue(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path, task_ids="")
    create_execution_queue_from_batch("sample", "B001", workspace_root=workspace)
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    missing = runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q999"], terminal_width=240)
    completed = runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"], terminal_width=240)

    assert missing.exit_code != 0
    assert "Execution queue not found" in missing.output
    assert completed.exit_code != 0
    assert "Execution queue is completed" in completed.output


def test_handoff_task_creates_prompt_and_unknown_task_fails(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "handoff-task", "--project", "sample", "--task", "T001"], terminal_width=240)
    missing = runner.invoke(app, ["project", "handoff-task", "--project", "sample", "--task", "T999"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert missing.exit_code != 0
    assert "Backlog task not found" in missing.output
    handoff = list_codex_handoffs("sample", workspace_root=workspace)[0]
    assert handoff.handoff_type == "task"
    assert handoff.source_task_id == "T001"
    prompt = Path(handoff.prompt_path).read_text(encoding="utf-8")
    assert "Allowed Scope" in prompt
    assert "Forbidden Scope" in prompt


def test_handoff_batch_creates_prompt_and_unknown_batch_fails(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_batch(tmp_path)

    result = runner.invoke(app, ["project", "handoff-batch", "--project", "sample", "--batch", "B001"], terminal_width=240)
    missing = runner.invoke(app, ["project", "handoff-batch", "--project", "sample", "--batch", "B999"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "approved batch scope" in result.output
    assert missing.exit_code != 0
    assert "Project batch not found" in missing.output
    handoff = list_codex_handoffs("sample", workspace_root=workspace)[0]
    assert handoff.handoff_type == "batch"
    assert handoff.source_batch_id == "B001"
    prompt = Path(handoff.prompt_path).read_text(encoding="utf-8")
    assert "Batch Tasks" in prompt
    assert "Do not commit generated workspace artifacts." in prompt


def test_handoff_list_show_and_mark_used(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "handoff-task", "--project", "sample", "--task", "T001"])

    listed = runner.invoke(app, ["project", "handoff-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["project", "handoff-show", "--project", "sample", "--handoff", "H001"], terminal_width=240)
    marked = runner.invoke(app, ["project", "handoff-mark-used", "--project", "sample", "--handoff", "H001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "H001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Codex handoff: H001" in shown.output
    assert marked.exit_code == 0, marked.output
    handoff = load_codex_handoff("sample", "H001", workspace_root=workspace)
    assert handoff is not None
    assert handoff.status == "used"


def test_unknown_project_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)

    result = runner.invoke(
        app,
        ["project", "brief-create", "--project", "missing", "--title", "Missing", "--file", str(brief_file)],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found" in result.output


def test_blueprint_create_without_brief_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["project", "blueprint-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code != 0
    assert "Project brief not found" in result.output


def test_backlog_create_without_blueprint_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["project", "backlog-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code != 0
    assert "Project blueprint not found" in result.output


def test_task_show_unknown_task_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "task-show", "--project", "sample", "--task", "T999"], terminal_width=240)

    assert result.exit_code != 0
    assert "Backlog task not found" in result.output


def test_read_models_include_planning_summary(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)

    missing = build_project_overview("sample", workspace_root=workspace)
    assert missing.brief_status == "missing"
    assert "brief-create" in missing.planning_next_action

    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])

    overview = build_project_overview("sample", workspace_root=workspace)
    assert overview.brief_status == "approved"
    assert overview.blueprint_status == "approved"
    assert overview.blueprint_milestone_count == 2
    assert overview.blueprint_epic_count == 2
    assert overview.backlog_status == "missing"
    assert "backlog-create" in overview.planning_next_action

    runner.invoke(app, ["project", "backlog-create", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])
    generate_backlog_refinement_prompt("sample", workspace_root=workspace)

    with_backlog = build_project_overview("sample", workspace_root=workspace)
    assert with_backlog.backlog_status == "approved"
    assert with_backlog.backlog_task_count == 2
    assert with_backlog.backlog_ready_count == 2
    assert with_backlog.backlog_refinement_prompt_exists is True
    assert with_backlog.backlog_refinement_prompt_path is not None
    assert with_backlog.batch_count == 0
    assert "batch-suggest" in with_backlog.planning_next_action

    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"])

    with_batch = build_project_overview("sample", workspace_root=workspace)
    assert with_batch.batch_count == 1
    assert with_batch.approved_batch_count == 1
    assert with_batch.latest_batch_id == "B001"
    assert with_batch.latest_batch_status == "approved"
    assert "queue-create" in with_batch.planning_next_action

    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])

    with_queue = build_project_overview("sample", workspace_root=workspace)
    assert with_queue.queue_count == 1
    assert with_queue.latest_queue_id == "Q001"
    assert with_queue.latest_queue_status == "running"
    assert with_queue.current_queue_item == "QI001"
    assert with_queue.queue_pending_count == 0
    assert with_queue.queue_next_action.endswith("--queue Q001")
    assert "handoff-next" in with_queue.handoff_next_action

    runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"])

    with_handoff = build_project_overview("sample", workspace_root=workspace)
    assert with_handoff.handoff_count == 1
    assert with_handoff.latest_handoff_id == "H001"
    assert with_handoff.latest_handoff_type == "queue_next"
    assert with_handoff.latest_handoff_status == "draft"
    assert with_handoff.latest_handoff_path is not None


def test_planning_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    before_target = _target_snapshot(project_path)

    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-create", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-prompt", "--project", "sample"])
    runner.invoke(app, ["project", "backlog-approve", "--project", "sample"])
    refined = _refined_backlog_file(tmp_path, _workspace_path)
    runner.invoke(app, ["project", "backlog-validate", "--project", "sample", "--file", str(refined)])
    runner.invoke(app, ["project", "batch-suggest", "--project", "sample"])
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "Safe planning batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-review", "--project", "sample", "--batch", "B001", "--note", "Planning review only."])
    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])
    runner.invoke(app, ["project", "queue-next", "--project", "sample", "--queue", "Q001"])
    runner.invoke(app, ["project", "queue-pause", "--project", "sample", "--queue", "Q001", "--reason", "usage_limit", "--note", "Pause only."])
    runner.invoke(app, ["project", "queue-resume", "--project", "sample", "--queue", "Q001"])
    runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"])
    runner.invoke(app, ["project", "handoff-task", "--project", "sample", "--task", "T001"])
    runner.invoke(app, ["project", "handoff-batch", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "handoff-list", "--project", "sample"])
    runner.invoke(app, ["project", "handoff-show", "--project", "sample", "--handoff", "H001"])
    runner.invoke(app, ["project", "handoff-mark-used", "--project", "sample", "--handoff", "H001"])
    runner.invoke(app, ["project", "queue-complete-item", "--project", "sample", "--queue", "Q001", "--item", "QI001", "--note", "Done."])

    assert _target_snapshot(project_path) == before_target


def _refined_backlog_file(
    tmp_path: Path,
    workspace: Path,
    *,
    project: str = "sample",
    status: str = "draft",
    task_status: str = "draft",
    risk_level: str = "medium",
    duplicate: bool = False,
) -> Path:
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    task_ids = ["T101", "T101" if duplicate else "T102"]
    backlog = ProjectBacklog(
        project=project,
        title="Refined Sample Backlog",
        blueprint_reference=str(paths.blueprint_json),
        status=status,
        task_count=2,
        ready_task_count=0,
        blocked_task_count=0,
        completed_task_count=0,
        tasks=[
            BacklogTask(
                id=task_ids[0],
                title="Refined planning task",
                summary="Make the starter task implementation-ready.",
                milestone_id="M001",
                epic_id="E001",
                lane="small-feature",
                risk_level=risk_level,
                status=task_status,
                dependencies=[],
                acceptance_criteria=["The task has clear acceptance criteria."],
                validation_expectations=["Run focused tests."],
                allowed_scope=["Planning artifacts only."],
                forbidden_scope=["No target repo mutation."],
                notes=["Created by test refined backlog."],
                source="test-refinement",
            ),
            BacklogTask(
                id=task_ids[1],
                title="Second refined planning task",
                summary="A second implementation-ready placeholder.",
                milestone_id="M001",
                epic_id="E002",
                lane="docs-only",
                risk_level="low",
                status="draft",
                dependencies=[task_ids[0]],
                acceptance_criteria=["The task is separately executable."],
                validation_expectations=["Run docs checks."],
                allowed_scope=["Docs only."],
                forbidden_scope=["No source behavior changes."],
                notes=[],
                source="test-refinement",
            ),
        ],
    )
    path = tmp_path / "refined-backlog.json"
    path.write_text(backlog.model_dump_json(indent=2), encoding="utf-8")
    return path


def _write_backlog_statuses(workspace: Path, statuses: list[str]) -> None:
    backlog = load_project_backlog("sample", workspace_root=workspace)
    assert backlog is not None
    template = backlog.tasks[0]
    tasks: list[BacklogTask] = []
    for index, status in enumerate(statuses, start=1):
        base = backlog.tasks[index - 1] if index <= len(backlog.tasks) else template
        epic_id = "E001" if index % 2 else "E002"
        tasks.append(
            base.model_copy(
                update={
                    "id": f"T{index:03d}",
                    "title": f"Progress task {index}",
                    "status": status,
                    "milestone_id": "M001",
                    "epic_id": epic_id,
                }
            )
        )
    updated = backlog.model_copy(update={"tasks": tasks, "task_count": len(tasks)})
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    paths.backlog_json.write_text(updated.model_dump_json(indent=2), encoding="utf-8")


def _write_batch_status(workspace: Path, batch_id: str, *, status: str, approval_status: str) -> None:
    batch = load_project_batch("sample", batch_id, workspace_root=workspace)
    assert batch is not None
    updated = batch.model_copy(update={"status": status, "approval_status": approval_status})
    json_path, _markdown_path = project_batch_artifact_paths("sample", batch_id, workspace_root=workspace)
    json_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")


def _create_approved_batch(tmp_path: Path, task_ids: str = "T001,T002") -> None:
    _create_backlog(tmp_path)
    if task_ids:
        runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "Approved batch", "--tasks", task_ids])
    else:
        from devo.project_planning import ProjectBatch

        paths = planning_artifact_paths("sample")
        batch = ProjectBatch(
            project="sample",
            batch_id="B001",
            title="Empty approved batch",
            summary="Empty test batch.",
            source_backlog_reference=str(paths.backlog_json),
            status="approved",
            task_ids=[],
            task_count=0,
            approval_status="approved",
        )
        paths.batches_dir.mkdir(parents=True, exist_ok=True)
        json_path, markdown_path = project_batch_artifact_paths("sample", "B001")
        json_path.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
        markdown_path.write_text("# Empty approved batch\n", encoding="utf-8")
        return
    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001"])


def _ensure_queue(tmp_path: Path) -> None:
    if load_execution_queue("sample", "Q001") is not None:
        return
    _create_queue(tmp_path)


def _create_execution_policy(
    tmp_path: Path,
    *,
    allowed_task: str = "T001",
    request: bool = True,
    approve: bool = True,
    expires_at: str | None = None,
) -> None:
    _ensure_queue(tmp_path)
    args = [
        "project",
        "execution-policy-create",
        "--project",
        "sample",
        "--batch",
        "B001",
        "--queue",
        "Q001",
        "--title",
        "Queue worker policy",
        "--allowed-file",
        "src/**",
        "--forbidden-file",
        ".env",
        "--validation-command",
        "pytest",
        "--max-tasks",
        "5",
        "--max-tasks-per-run",
        "1",
    ]
    for task_id in [value.strip() for value in allowed_task.split(",") if value.strip()]:
        args.extend(["--allowed-task", task_id])
    if expires_at:
        args.extend(["--expires-at", expires_at])
    created = runner.invoke(app, args, terminal_width=240)
    assert created.exit_code == 0, created.output
    policy_id = list_execution_policies("sample")[0].policy_id
    if request:
        requested = runner.invoke(app, ["project", "execution-policy-request", "--project", "sample", "--policy", policy_id], terminal_width=240)
        assert requested.exit_code == 0, requested.output
    if approve:
        approved = runner.invoke(app, ["project", "execution-policy-approve", "--project", "sample", "--policy", policy_id, "--approver", "Manas"], terminal_width=240)
        assert approved.exit_code == 0, approved.output


def _create_queue_worker_run(tmp_path: Path) -> None:
    _create_execution_policy(tmp_path, allowed_task="T001")
    result = runner.invoke(
        app,
        ["project", "queue-worker-run", "--project", "sample", "--policy", "POL-0001", "--once", "--confirm-queue-worker"],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output


def _create_ready_queue_worker_run(tmp_path: Path) -> None:
    _create_queue_worker_run(tmp_path)
    _import_worker_report(tmp_path)
    _continue_queue_worker_run()
    _record_worker_review(status="reviewed_passed")
    _continue_queue_worker_run()
    _attach_validation(status="passed")
    _continue_queue_worker_run()


def _import_worker_report(tmp_path: Path, *, status: str = "completed") -> None:
    report = CodexWorkerReport(
        project="sample",
        worker_run_id="WR001",
        source_handoff_id="H001",
        source_queue_id="Q001",
        source_queue_item_id="QI001",
        source_task_id="T001",
        status_reported_by_worker=status,
        summary="Worker completed the small task." if status == "completed" else "Worker could not complete the task.",
        changed_files=["src/feature.py"] if status == "completed" else [],
        validation_attempted=status == "completed",
        validation_results=["Focused validation passed."] if status == "completed" else [],
        tests_run=["pytest tests/test_sample.py"] if status == "completed" else [],
        commands_run=["pytest tests/test_sample.py"] if status == "completed" else [],
    )
    report_file = tmp_path / f"worker-report-{status}.json"
    report_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(report_file)],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output


def _record_worker_review(*, status: str = "reviewed_passed") -> None:
    result = runner.invoke(
        app,
        [
            "worker",
            "codex",
            "review-record",
            "--project",
            "sample",
            "--run",
            "WR001",
            "--status",
            status,
            "--reviewer",
            "Manas",
            "--note",
            "Reviewed safe worker output.",
        ],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output


def _attach_validation(*, status: str = "passed") -> None:
    result = runner.invoke(
        app,
        [
            "worker",
            "codex",
            "review-attach-evidence",
            "--project",
            "sample",
            "--run",
            "WR001",
            "--status",
            status,
            "--summary",
            "Validation evidence passed.",
        ],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output


def _continue_queue_worker_run() -> None:
    result = runner.invoke(
        app,
        ["project", "queue-worker-continue", "--project", "sample", "--run", "QWR-0001", "--confirm-continue"],
        terminal_width=240,
    )
    assert result.exit_code == 0 or "Status: waiting_" in result.output, result.output


def _init_git_repo(project_path: Path) -> None:
    _git(project_path, "init")
    _git(project_path, "config", "user.email", "devo@example.test")
    _git(project_path, "config", "user.name", "Devo Test")
    _git(project_path, "add", "README.md")
    _git(project_path, "commit", "-m", "initial")


def _git(cwd: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=capture, text=True)


def _create_queue(tmp_path: Path) -> None:
    _create_approved_batch(tmp_path)
    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])


def _create_blueprint(tmp_path: Path) -> None:
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])


def _create_backlog(tmp_path: Path) -> None:
    _create_blueprint(tmp_path)
    runner.invoke(app, ["project", "backlog-create", "--project", "sample"])


def _brief_file(tmp_path: Path) -> Path:
    path = tmp_path / "brief.md"
    path.write_text(
        """# Sample Brief

Build a local planning dashboard for controlled work.

## Goals
- Track the work queue
- Show progress clearly

## Non-Goals
- Run builds from the UI

## Target Users
- Solo developer

## Constraints
- Local-only
- No AI API calls

## Risks
- Scope drift

## Tech Stack
- Python
- React

## Validation
- Run focused tests
""",
        encoding="utf-8",
    )
    return path


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


def _target_snapshot(project_path: Path) -> dict[str, str]:
    return {str(path.relative_to(project_path)): path.read_text(encoding="utf-8") for path in project_path.rglob("*") if path.is_file()}
