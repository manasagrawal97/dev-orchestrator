from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_planning import (
    list_codex_run_plans,
    list_codex_worker_runs,
    load_codex_run_plan,
    load_codex_worker_report,
    load_codex_handoff,
    load_codex_worker_run,
    load_execution_queue,
    get_backlog_task,
    load_codex_run_plan_index,
    load_worker_run_index,
    worker_execution_log_paths,
    worker_run_plan_artifact_paths,
    worker_report_artifact_paths,
    worker_report_template_paths,
    worker_run_artifact_paths,
)
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration

runner = CliRunner()


def test_worker_run_create_from_handoff_creates_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_queue_handoff(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["worker", "codex", "run-create", "--project", "sample", "--handoff", "H001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Codex worker run recorded" in result.output
    assert "Devo did not run Codex" in result.output
    json_path, markdown_path = worker_run_artifact_paths("sample", "WR001", workspace_root=workspace)
    assert json_path.exists()
    assert markdown_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["worker_run_id"] == "WR001"
    assert data["worker_type"] == "codex_cli"
    assert data["mode"] == "manual_handoff"
    assert data["source_handoff_id"] == "H001"
    assert data["source_queue_id"] == "Q001"
    assert data["source_queue_item_id"] == "QI001"
    assert data["source_task_id"] == "T001"
    assert data["target_repo_path"] == str(project_path)
    assert data["report"]["report_status"] == "missing"
    assert "workspace-only tracking" in markdown_path.read_text(encoding="utf-8")
    index = load_worker_run_index("sample", workspace_root=workspace)
    assert index.worker_runs[0].worker_run_id == "WR001"
    assert _target_snapshot(project_path) == before_target


def test_worker_run_create_rejects_unknown_handoff(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["worker", "codex", "run-create", "--project", "sample", "--handoff", "H999"], terminal_width=240)

    assert result.exit_code != 0
    assert "Codex handoff not found" in result.output


def test_worker_run_list_and_show(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    listed = runner.invoke(app, ["worker", "codex", "run-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["worker", "codex", "run-show", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "WR001 | planned" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Codex worker run: WR001" in shown.output
    assert "Report status: missing" in shown.output
    assert "Source handoff: H001" in shown.output


def test_worker_run_status_updates_status_and_note(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    result = runner.invoke(
        app,
        [
            "worker",
            "codex",
            "run-status",
            "--project",
            "sample",
            "--run",
            "WR001",
            "--status",
            "waiting_review",
            "--note",
            "Manual worker stopped for review.",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "waiting_review"
    assert worker_run.status_note == "Manual worker stopped for review."
    assert "Review worker evidence manually" in worker_run.next_action


def test_worker_run_status_rejects_invalid_status(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    result = runner.invoke(
        app,
        ["worker", "codex", "run-status", "--project", "sample", "--run", "WR001", "--status", "done-ish"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Invalid worker run status" in result.output


def test_completed_status_does_not_mark_queue_or_task_completed(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    result = runner.invoke(
        app,
        ["worker", "codex", "run-status", "--project", "sample", "--run", "WR001", "--status", "completed", "--note", "Codex stopped."],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "completed"
    assert worker_run.completed_at is not None
    assert "do not automatically complete queue/task state" in worker_run.next_action
    assert queue is not None
    assert queue.status == "running"
    assert queue.items[0].status == "running"


def test_worker_status_guidance_for_usage_limit_and_approval_blocker(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    paused = runner.invoke(
        app,
        ["worker", "codex", "run-status", "--project", "sample", "--run", "WR001", "--status", "paused_usage_limit"],
        terminal_width=240,
    )
    blocked = runner.invoke(
        app,
        ["worker", "codex", "run-status", "--project", "sample", "--run", "WR001", "--status", "blocked_needs_approval"],
        terminal_width=240,
    )

    assert paused.exit_code == 0, paused.output
    assert "queue-pause/queue-resume" in paused.output
    assert blocked.exit_code == 0, blocked.output
    assert "explicit trusted approval" in blocked.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "blocked_needs_approval"


def test_worker_run_mark_used_updates_handoff_only(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)

    result = runner.invoke(app, ["worker", "codex", "run-mark-used", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    handoff = load_codex_handoff("sample", "H001", workspace_root=workspace)
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert handoff is not None
    assert handoff.status == "used"
    assert worker_run is not None
    assert worker_run.status == "planned"
    assert "does not imply worker completion" in worker_run.status_note


def test_worker_run_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    before_target = _target_snapshot(project_path)

    list_codex_worker_runs("sample", workspace_root=workspace)
    runner.invoke(app, ["worker", "codex", "run-list", "--project", "sample"])
    runner.invoke(app, ["worker", "codex", "run-show", "--project", "sample", "--run", "WR001"])
    runner.invoke(app, ["worker", "codex", "run-status", "--project", "sample", "--run", "WR001", "--status", "running"])

    assert _target_snapshot(project_path) == before_target


def test_worker_report_template_creates_template_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["worker", "codex", "report-template", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    json_path, markdown_path = worker_report_template_paths("sample", "WR001", workspace_root=workspace)
    assert json_path.exists()
    assert markdown_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["worker_run_id"] == "WR001"
    assert data["status_reported_by_worker"] == "partial"
    assert "report-validate" in result.output
    assert _target_snapshot(project_path) == before_target


def test_worker_report_validate_accepts_valid_report(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report = _worker_report_file(tmp_path, "WR001")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-validate", "--project", "sample", "--run", "WR001", "--file", str(report)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Valid: True" in result.output
    assert "No queue item, backlog task" in result.output


def test_worker_report_validate_rejects_mismatched_worker_run_id(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report = _worker_report_file(tmp_path, "WR999")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-validate", "--project", "sample", "--run", "WR001", "--file", str(report)],
        terminal_width=240,
    )

    assert result.exit_code == 1
    assert "Report worker_run_id must be WR001" in result.output


def test_worker_report_validate_rejects_invalid_worker_status(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report = _worker_report_file(tmp_path, "WR001", status="done-ish")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-validate", "--project", "sample", "--run", "WR001", "--file", str(report)],
        terminal_width=240,
    )

    assert result.exit_code == 1
    assert "Invalid status_reported_by_worker" in result.output


def test_worker_report_import_stores_report_and_updates_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    before_target = _target_snapshot(project_path)
    report_file = _worker_report_file(tmp_path, "WR001", status="completed")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(report_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    report_json, report_markdown = worker_report_artifact_paths("sample", "WR001", workspace_root=workspace)
    assert report_json.exists()
    assert report_markdown.exists()
    imported_report = load_codex_worker_report("sample", "WR001", workspace_root=workspace)
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert imported_report is not None
    assert imported_report.status_reported_by_worker == "completed"
    assert worker_run is not None
    assert worker_run.report.report_status == "validated"
    assert worker_run.report_path == str(report_markdown)
    assert worker_run.report.reported_changed_files == ["src/example.py"]
    assert worker_run.report.reported_validation == ["Focused tests passed.", "test: tests/test_example.py"]
    assert worker_run.status == "waiting_review"
    assert "queue-complete-item only after review" in worker_run.next_action
    assert _target_snapshot(project_path) == before_target


def test_completed_report_import_does_not_mark_queue_or_task_completed(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report_file = _worker_report_file(tmp_path, "WR001", status="completed")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(report_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "running"
    assert queue.items[0].status == "running"


def test_worker_report_import_maps_usage_limit_to_paused_usage_limit(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report_file = _worker_report_file(tmp_path, "WR001", status="usage_limit")

    result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(report_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "paused_usage_limit"
    assert "usage resets" in worker_run.next_action


def test_worker_report_import_maps_blocked_and_needs_approval_to_approval_blocker(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    blocked = _worker_report_file(tmp_path, "WR001", status="blocked")
    blocked_result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(blocked)],
        terminal_width=240,
    )
    needs_approval = _worker_report_file(tmp_path, "WR001", status="needs_approval")
    approval_result = runner.invoke(
        app,
        ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(needs_approval)],
        terminal_width=240,
    )

    assert blocked_result.exit_code == 0, blocked_result.output
    assert approval_result.exit_code == 0, approval_result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "blocked_needs_approval"
    assert "explicit trusted approval" in worker_run.next_action


def test_worker_report_show_and_list_work(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    report_file = _worker_report_file(tmp_path, "WR001")
    runner.invoke(app, ["worker", "codex", "report-import", "--project", "sample", "--run", "WR001", "--file", str(report_file)])

    shown = runner.invoke(app, ["worker", "codex", "report-show", "--project", "sample", "--run", "WR001"], terminal_width=240)
    listed = runner.invoke(app, ["worker", "codex", "report-list", "--project", "sample"], terminal_width=240)

    assert shown.exit_code == 0, shown.output
    assert "Codex worker report: WR001" in shown.output
    assert "worker-provided evidence only" in shown.output
    assert listed.exit_code == 0, listed.output
    assert "WR001 | completed" in listed.output


def test_codex_preflight_passes_for_valid_worker_run(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["worker", "codex", "preflight", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Status: passed" in result.output
    assert "Devo did not run Codex" in result.output
    assert _target_snapshot(project_path) == before_target
    assert list_codex_run_plans("sample", workspace_root=workspace) == []


def test_codex_preflight_blocks_missing_prompt(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    handoff = load_codex_handoff("sample", "H001")
    assert handoff is not None
    Path(handoff.prompt_path).unlink()

    result = runner.invoke(app, ["worker", "codex", "preflight", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code != 0
    assert "Status: blocked" in result.output
    assert "Prompt file is missing" in result.output


def test_codex_preflight_blocks_missing_target_repo_path(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    worker_run = load_codex_worker_run("sample", "WR001")
    assert worker_run is not None
    target = Path(worker_run.target_repo_path)
    for child in target.iterdir():
        child.unlink()
    target.rmdir()

    result = runner.invoke(app, ["worker", "codex", "preflight", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code != 0
    assert "Status: blocked" in result.output
    assert "Target repo path is missing" in result.output


def test_codex_run_plan_creates_artifacts_and_index(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Codex run plan saved" in result.output
    assert "Supervised Codex execution is future work" in result.output
    json_path, markdown_path = worker_run_plan_artifact_paths("sample", "RP001", workspace_root=workspace)
    assert json_path.exists()
    assert markdown_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["plan_id"] == "RP001"
    assert data["worker_run_id"] == "WR001"
    assert data["status"] == "ready"
    assert data["preflight_status"] == "passed"
    assert "codex <" in data["proposed_command_preview"]
    assert "safe preview only" in markdown_path.read_text(encoding="utf-8")
    index = load_codex_run_plan_index("sample", workspace_root=workspace)
    assert index.run_plans[0].plan_id == "RP001"
    assert _target_snapshot(project_path) == before_target


def test_codex_run_plan_stores_blocked_reasons(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    handoff = load_codex_handoff("sample", "H001", workspace_root=workspace)
    assert handoff is not None
    Path(handoff.prompt_path).unlink()

    result = runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    plan = load_codex_run_plan("sample", "RP001", workspace_root=workspace)
    assert plan is not None
    assert plan.status == "blocked"
    assert plan.preflight_status == "blocked"
    assert any("Prompt file is missing" in reason for reason in plan.blocked_reasons)


def test_codex_run_plan_list_show_and_approve_work(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch)
    runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"])

    listed = runner.invoke(app, ["worker", "codex", "run-plan-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["worker", "codex", "run-plan-show", "--project", "sample", "--plan", "RP001"], terminal_width=240)
    approved = runner.invoke(app, ["worker", "codex", "run-plan-approve", "--project", "sample", "--plan", "RP001", "--note", "Looks safe."], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "RP001 | run=WR001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Codex run plan: RP001" in shown.output
    assert approved.exit_code == 0, approved.output
    assert "planning approval recorded" in approved.output
    plan = load_codex_run_plan("sample", "RP001", workspace_root=workspace)
    assert plan is not None
    assert plan.approval_status == "approved"
    assert plan.approval_note == "Looks safe."
    assert "Looks safe." not in plan.warnings
    assert "Supervised Codex execution is future work" in plan.next_action


def test_codex_run_plan_commands_do_not_mutate_target_repo_or_queue(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    runner.invoke(app, ["worker", "codex", "preflight", "--project", "sample", "--run", "WR001"])
    runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"])
    runner.invoke(app, ["worker", "codex", "run-plan-list", "--project", "sample"])
    runner.invoke(app, ["worker", "codex", "run-plan-show", "--project", "sample", "--plan", "RP001"])

    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    assert queue is not None
    assert queue.status == "running"
    assert queue.items[0].status == "running"
    assert _target_snapshot(project_path) == before_target


def test_codex_execute_preview_works_without_running_executable(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute-preview", "--project", "sample", "--run", "WR001", "--plan", "RP001"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Codex execution preview" in result.output
    assert "Ready: True" in result.output
    log_path, _stderr_log_path = worker_execution_log_paths("sample", "WR001", workspace_root=workspace)
    assert not log_path.exists()
    assert _target_snapshot(project_path) == before_target


def test_codex_execute_refuses_without_confirm_execute(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Refusing to execute Codex without --confirm-execute" in result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "planned"


def test_codex_execute_refuses_unapproved_run_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch)
    runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"])

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "approval status is not_requested" in result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "planned"


def test_codex_execute_refuses_blocked_preflight(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_worker_run(tmp_path)
    handoff = load_codex_handoff("sample", "H001")
    assert handoff is not None
    Path(handoff.prompt_path).unlink()
    runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"])
    runner.invoke(app, ["worker", "codex", "run-plan-approve", "--project", "sample", "--plan", "RP001"])

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run plan preflight is blocked" in result.output


def test_codex_execute_refuses_missing_prompt(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch)
    handoff = load_codex_handoff("sample", "H001")
    assert handoff is not None
    Path(handoff.prompt_path).unlink()

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Prompt file is missing" in result.output


def test_codex_execute_refuses_missing_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch)
    for path in project_path.rglob("*"):
        if path.is_file():
            path.unlink()
    project_path.rmdir()

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Target repo path is missing" in result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "planned"


def test_codex_execute_success_sets_waiting_review_and_writes_logs(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch, stdout="fake codex completed", exit_code=0)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    queue = load_execution_queue("sample", "Q001", workspace_root=workspace)
    task = get_backlog_task("sample", "T001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "waiting_review"
    assert worker_run.mode == "supervised_cli"
    assert worker_run.execution_exit_code == 0
    assert worker_run.execution_log_path is not None
    assert "fake codex completed" in Path(worker_run.execution_log_path).read_text(encoding="utf-8")
    assert queue is not None
    assert queue.items[0].status == "running"
    assert task.status == "ready"
    assert _target_snapshot(project_path) == before_target


def test_codex_execute_failure_sets_failed_and_writes_logs(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch, stderr="fake codex failed", exit_code=7)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "failed"
    assert worker_run.execution_exit_code == 7
    assert worker_run.execution_stderr_log_path is not None
    assert "fake codex failed" in Path(worker_run.execution_stderr_log_path).read_text(encoding="utf-8")


def test_codex_execute_usage_limit_output_sets_paused_usage_limit(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch, stdout="usage limit reached", exit_code=0)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "paused_usage_limit"


def test_codex_execute_safety_output_sets_blocked_needs_approval(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch, stderr="approval required by safety policy", exit_code=1)

    result = runner.invoke(
        app,
        ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    worker_run = load_codex_worker_run("sample", "WR001", workspace_root=workspace)
    assert worker_run is not None
    assert worker_run.status == "blocked_needs_approval"


def test_codex_execute_log_shows_log_tail(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _create_approved_run_plan(tmp_path, monkeypatch, stdout="visible log tail", exit_code=0)
    runner.invoke(app, ["worker", "codex", "execute", "--project", "sample", "--run", "WR001", "--plan", "RP001", "--confirm-execute"])

    result = runner.invoke(app, ["worker", "codex", "execute-log", "--project", "sample", "--run", "WR001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "visible log tail" in result.output
    assert "execution logs" in result.output


def _create_worker_run(tmp_path: Path) -> None:
    _create_queue_handoff(tmp_path)
    result = runner.invoke(app, ["worker", "codex", "run-create", "--project", "sample", "--handoff", "H001"])
    assert result.exit_code == 0, result.output


def _create_approved_run_plan(
    tmp_path: Path,
    monkeypatch,
    *,
    stdout: str = "fake codex ok",
    stderr: str = "",
    exit_code: int = 0,
) -> None:
    _create_worker_run(tmp_path)
    _add_fake_codex_to_path(tmp_path, monkeypatch, stdout=stdout, stderr=stderr, exit_code=exit_code)
    created = runner.invoke(app, ["worker", "codex", "run-plan", "--project", "sample", "--run", "WR001"], terminal_width=240)
    assert created.exit_code == 0, created.output
    approved = runner.invoke(app, ["worker", "codex", "run-plan-approve", "--project", "sample", "--plan", "RP001"], terminal_width=240)
    assert approved.exit_code == 0, approved.output


def _create_queue_handoff(tmp_path: Path) -> None:
    _create_backlog(tmp_path)
    runner.invoke(app, ["project", "batch-create", "--project", "sample", "--title", "First batch", "--tasks", "T001"])
    runner.invoke(app, ["project", "batch-approval-request", "--project", "sample", "--batch", "B001", "--note", "Ready."])
    runner.invoke(app, ["project", "batch-approve", "--project", "sample", "--batch", "B001", "--note", "Approved."])
    runner.invoke(app, ["project", "queue-create", "--project", "sample", "--batch", "B001"])
    runner.invoke(app, ["project", "queue-start", "--project", "sample", "--queue", "Q001"])
    result = runner.invoke(app, ["project", "handoff-next", "--project", "sample", "--queue", "Q001"])
    assert result.exit_code == 0, result.output


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


def _target_snapshot(project_path: Path) -> dict[str, str]:
    return {str(path.relative_to(project_path)): path.read_text(encoding="utf-8") for path in project_path.rglob("*") if path.is_file()}


def _add_fake_codex_to_path(tmp_path: Path, monkeypatch, *, stdout: str = "", stderr: str = "", exit_code: int = 0) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake_codex = bin_dir / "codex.cmd"
    lines = ["@echo off"]
    if stdout:
        lines.append(f"echo {stdout}")
    if stderr:
        lines.append(f"echo {stderr} 1>&2")
    lines.append(f"exit /b {exit_code}")
    fake_codex.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    existing_value = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir};{existing_value}")


def _worker_report_file(tmp_path: Path, worker_run_id: str, status: str = "completed") -> Path:
    path = tmp_path / f"report-{worker_run_id}-{status}.json"
    data = {
        "schema_version": "1",
        "project": "sample",
        "worker_run_id": worker_run_id,
        "source_handoff_id": "H001",
        "source_queue_id": "Q001",
        "source_queue_item_id": "QI001",
        "source_task_id": "T001",
        "status_reported_by_worker": status,
        "summary": f"Worker reported {status}.",
        "changed_files": ["src/example.py"] if status == "completed" else [],
        "validation_attempted": True,
        "validation_results": ["Focused tests passed."],
        "tests_run": ["tests/test_example.py"],
        "commands_run": [],
        "commit_hash": None,
        "safety_warnings": [],
        "blockers": ["Needs approval."] if status in {"blocked", "needs_approval"} else [],
        "follow_up_needed": [],
        "notes": ["Manual report fixture."],
        "reported_at": "2026-07-22T00:00:00Z",
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
