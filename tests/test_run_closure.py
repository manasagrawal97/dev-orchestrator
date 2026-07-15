from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_planning import _approved_project
from tests.test_task_closure import _run_with_closed_task
from tests.test_task_disposition import _mark, _run_with_two_tasks

runner = CliRunner()


def test_closing_run_when_all_tasks_resolved(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "covered_by", "Covered by T002.", covered_by="T002")
    _mark(run_id, "T002", "closed_manually", "Closed manually as ledger reconciliation.")

    result = runner.invoke(app, ["run", "close", "--project", "sample", "--run", run_id], terminal_width=240)

    assert result.exit_code == 0
    assert "Closed run" in result.output
    assert "Status: RUN_CLOSED" in result.output
    state = _run_state(workspace, run_id)
    assert state["status"] == "RUN_CLOSED"
    assert state["run_summary_path"].endswith("run-summary.md")
    assert state["closed_at"]


def test_close_fails_when_task_is_unresolved(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "covered_by", "Covered by T002.", covered_by="T002")

    result = runner.invoke(app, ["run", "close", "--project", "sample", "--run", run_id], terminal_width=240)

    assert result.exit_code != 0
    assert "unresolved tasks" in result.output
    assert "T002" in result.output


def test_close_succeeds_with_mix_of_closure_and_dispositions(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_closed_task(tmp_path, monkeypatch)
    _append_second_task(workspace, run_id)
    _mark(run_id, "T002", "not_needed", "No separate task remains.")

    result = runner.invoke(
        app,
        ["run", "close", "--project", "sample", "--run", run_id, "--note", "All tasks reconciled."],
        terminal_width=240,
    )

    assert result.exit_code == 0
    state = _run_state(workspace, run_id)
    assert state["status"] == "RUN_CLOSED"
    assert state["closure_note"] == "All tasks reconciled."


def test_run_summary_markdown_is_created(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _closed_run(tmp_path, monkeypatch)

    summary_file = workspace / "runs" / "sample" / run_id / "run-summary.md"
    summary_text = summary_file.read_text(encoding="utf-8")

    assert "# run-summary.md" in summary_text
    assert "## Task Resolution" in summary_text
    assert "| T001 |" in summary_text
    assert "## Key Artifacts" in summary_text


def test_run_status_updates_to_run_closed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _closed_run(tmp_path, monkeypatch)

    assert _run_state(workspace, run_id)["status"] == "RUN_CLOSED"


def test_run_summary_command_displays_task_resolution_table(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _closed_run(tmp_path, monkeypatch)

    result = runner.invoke(app, ["run", "summary", "--project", "sample", "--run", run_id], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: RUN_CLOSED" in result.output
    assert "Unresolved tasks: none" in result.output
    assert "Task resolution:" in result.output
    assert "T001" in result.output
    assert "disposition=covered_by" in result.output


def test_run_artifacts_lists_run_summary(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _closed_run(tmp_path, monkeypatch)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "run-summary.md" in result.output


def test_run_close_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["run", "close", "--project", "missing", "--run", "run"], terminal_width=240)

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_run_close_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(app, ["run", "close", "--project", "sample", "--run", "missing-run"], terminal_width=240)

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_run_close(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(app, ["run", "close", "--project", "sample", "--run", "some-run"], terminal_width=240)

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _closed_run(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "covered_by", "Covered by T002.", covered_by="T002")
    _mark(run_id, "T002", "not_needed", "No separate task remains.")
    result = runner.invoke(app, ["run", "close", "--project", "sample", "--run", run_id], terminal_width=240)
    assert result.exit_code == 0
    return workspace, run_id


def _append_second_task(workspace: Path, run_id: str) -> None:
    tasks_file = workspace / "runs" / "sample" / run_id / "artifacts" / "tasks.md"
    with tasks_file.open("a", encoding="utf-8") as file:
        file.write(
            "\n## Task T002\n\n"
            "- task id: `T002`\n"
            "- task title: Follow-up reconciliation task\n"
        )


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
