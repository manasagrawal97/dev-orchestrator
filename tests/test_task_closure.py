from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_final_audit_workflow import _import_final_audit, _run_with_code_review
from tests.test_run_planning import _approved_project

runner = CliRunner()


def test_closes_task_after_final_audit_close_task(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_final_audit(tmp_path, monkeypatch, "close_task")

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Closed task" in result.output
    assert "Closure status: closed" in result.output
    state = _run_state(workspace, run_id)
    record = state["implementation_records"][0]
    assert state["status"] == "TASK_CLOSED"
    assert record["closure_status"] == "closed"
    assert record["closure_record_path"].endswith("artifacts\\implementation\\T001\\closure-record.md")


def test_closes_task_after_final_audit_close_with_notes(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_final_audit(tmp_path, monkeypatch, "close_with_notes")

    result = runner.invoke(
        app,
        [
            "task",
            "close",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--note",
            "Evidence-only review accepted.",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Closure status: closed_with_notes" in result.output
    assert "Evidence-only review accepted." in result.output
    record = _run_state(workspace, run_id)["implementation_records"][0]
    assert record["closure_status"] == "closed_with_notes"
    assert record["closure_note"] == "Evidence-only review accepted."


def test_close_fails_without_final_audit(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Task closure requires final audit evidence" in result.output


def test_close_fails_when_final_decision_needs_follow_up(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_final_audit(tmp_path, monkeypatch, "needs_follow_up")

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Task cannot be closed with final decision" in result.output
    assert "needs_follow_up" in result.output


def test_close_fails_when_final_decision_blocked(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_final_audit(tmp_path, monkeypatch, "blocked")

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Task cannot be closed with final decision" in result.output
    assert "blocked" in result.output


def test_task_status_shows_closure_info(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_closed_task(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["task", "status", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Run status: TASK_CLOSED" in result.output
    assert "Closure status: closed_with_notes" in result.output
    assert "closure-record.md" in result.output
    assert "Final decision: close_with_notes" in result.output


def test_task_list_shows_closed_task(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_closed_task(tmp_path, monkeypatch)

    result = runner.invoke(app, ["task", "list", "--project", "sample", "--run", run_id], terminal_width=240)

    assert result.exit_code == 0
    assert "T001" in result.output
    assert "Inspect scanner solution-file categorization" in result.output
    assert "Closure status: closed_with_notes" in result.output


def test_run_artifacts_lists_closure_record(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_closed_task(tmp_path, monkeypatch)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "final-audit.md" in result.output
    assert "closure-record.md" in result.output


def test_task_close_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["task", "close", "--project", "missing", "--run", "missing-run", "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_task_close_missing_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", "missing-run", "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_task_close(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        ["task", "close", "--project", "sample", "--run", "some-run", "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _run_with_final_audit(tmp_path: Path, monkeypatch, decision: str) -> tuple[Path, str]:
    workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)
    _import_final_audit(tmp_path, run_id, decision)
    return workspace, run_id


def _run_with_closed_task(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_final_audit(tmp_path, monkeypatch, "close_with_notes")
    result = runner.invoke(
        app,
        [
            "task",
            "close",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--note",
            "Close with evidence notes.",
        ],
    )
    assert result.exit_code == 0
    return workspace, run_id


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
