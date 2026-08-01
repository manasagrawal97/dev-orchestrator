from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_planning import (
    list_codex_worker_runs,
    load_codex_handoff,
    load_codex_worker_run,
    load_execution_queue,
    load_worker_run_index,
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


def _create_worker_run(tmp_path: Path) -> None:
    _create_queue_handoff(tmp_path)
    result = runner.invoke(app, ["worker", "codex", "run-create", "--project", "sample", "--handoff", "H001"])
    assert result.exit_code == 0, result.output


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
