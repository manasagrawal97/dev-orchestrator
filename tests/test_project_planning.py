from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_planning import (
    BacklogTask,
    ProjectBacklog,
    generate_backlog_refinement_prompt,
    list_project_batches,
    load_project_backlog,
    load_project_batch,
    load_project_blueprint,
    load_project_brief,
    planning_artifact_paths,
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
    assert "TASK-DEVO-079" in with_batch.planning_next_action


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
