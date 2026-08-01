from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_planning import (
    BacklogTask,
    ProjectBacklog,
    calculate_project_progress,
    create_execution_queue_from_batch,
    generate_backlog_refinement_prompt,
    list_execution_queues,
    list_project_batches,
    load_execution_queue,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
    project_batch_artifact_paths,
    queue_artifact_paths,
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
    assert _target_snapshot(project_path) == before_target


def test_backlog_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "backlog-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project backlog: sample" in result.output
    assert "Status: draft" in result.output
    assert "Tasks: 2" in result.output


def test_backlog_approve_marks_approved_and_tasks_ready(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)

    result = runner.invoke(app, ["project", "backlog-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project backlog approved" in result.output
    assert "TASK-DEVO-077" in result.output
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


def test_batch_review_adds_note_and_marks_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])

    result = runner.invoke(app, ["project", "batch-review", "--project", "sample", "--batch", "B001", "--note", "Looks scoped."], terminal_width=240)

    assert result.exit_code == 0, result.output
    batch = load_project_batch("sample", "B001", workspace_root=workspace)
    assert batch is not None
    assert batch.status == "reviewed"
    assert any("Looks scoped." in note for note in batch.review_notes)


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
    assert "TASK-DEVO-080" in after_start.output


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
