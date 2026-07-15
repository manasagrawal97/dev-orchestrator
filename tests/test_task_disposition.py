from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_planning import _approved_project
from tests.test_run_task_decomposer import _run_with_reviewed_plan
from tests.test_task_closure import _run_with_closed_task

runner = CliRunner()


def test_marks_task_as_covered_by(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "task",
            "mark",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--status",
            "covered_by",
            "--covered-by",
            "T002",
            "--note",
            "Covered by the implementation and validation recorded for T002.",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Disposition status: covered_by" in result.output
    assert "Covered by: T002" in result.output
    ledger = _task_ledger(workspace, run_id)
    assert ledger["entries"]["T001"]["disposition_status"] == "covered_by"
    assert ledger["entries"]["T001"]["covered_by_task_id"] == "T002"
    assert _run_state(workspace, run_id)["status"] == "TASKS_DRAFTED"


def test_covered_by_fails_without_covered_by_task_id(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["task", "mark", "--project", "sample", "--run", run_id, "--task", "T001", "--status", "covered_by", "--note", "Covered."],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "covered_by disposition requires --covered-by" in result.output


def test_covered_by_fails_without_note(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["task", "mark", "--project", "sample", "--run", run_id, "--task", "T001", "--status", "covered_by", "--covered-by", "T002"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "covered_by disposition requires --note" in result.output


def test_marks_task_as_superseded(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = _mark(run_id, "T001", "superseded", "T001 is superseded by the reconciled task set.")

    assert result.exit_code == 0
    assert _task_ledger(workspace, run_id)["entries"]["T001"]["disposition_status"] == "superseded"


def test_marks_task_as_not_needed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = _mark(run_id, "T001", "not_needed", "No separate documentation change was needed.")

    assert result.exit_code == 0
    assert _task_ledger(workspace, run_id)["entries"]["T001"]["disposition_status"] == "not_needed"


def test_marks_task_as_closed_manually(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = _mark(run_id, "T001", "closed_manually", "Closed manually as bookkeeping only.")

    assert result.exit_code == 0
    assert _task_ledger(workspace, run_id)["entries"]["T001"]["disposition_status"] == "closed_manually"


def test_open_reset_keeps_implementation_records(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_closed_task(tmp_path, monkeypatch)
    before = _run_state(workspace, run_id)["implementation_records"]
    result = _mark(run_id, "T001", "open", None)

    assert result.exit_code == 0
    state = _run_state(workspace, run_id)
    assert state["status"] == "TASK_CLOSED"
    assert state["implementation_records"] == before
    assert _task_ledger(workspace, run_id)["entries"]["T001"]["disposition_status"] == "open"


def test_task_status_shows_disposition(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "not_needed", "No separate work remains.")

    result = runner.invoke(app, ["task", "status", "--project", "sample", "--run", run_id, "--task", "T001"], terminal_width=240)

    assert result.exit_code == 0
    assert "Disposition status: not_needed" in result.output
    assert "Disposition note: No separate work remains." in result.output


def test_task_list_shows_disposition(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "covered_by", "Covered by T002.", covered_by="T002")

    result = runner.invoke(app, ["task", "list", "--project", "sample", "--run", run_id], terminal_width=240)

    assert result.exit_code == 0
    assert "T001" in result.output
    assert "Disposition status: covered_by" in result.output
    assert "Covered by: T002" in result.output


def test_run_artifacts_lists_task_ledger(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)
    _mark(run_id, "T001", "not_needed", "No separate work remains.")

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "task-ledger.json" in result.output


def test_task_mark_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["task", "mark", "--project", "missing", "--run", "run", "--task", "T001", "--status", "open"], terminal_width=240)

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_task_mark_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(app, ["task", "mark", "--project", "sample", "--run", "missing-run", "--task", "T001", "--status", "open"], terminal_width=240)

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_task_mark_unknown_task_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_two_tasks(tmp_path, monkeypatch)

    result = runner.invoke(app, ["task", "mark", "--project", "sample", "--run", run_id, "--task", "T999", "--status", "open"], terminal_width=240)

    assert result.exit_code != 0
    assert "Task id not found in tasks.md: T999" in result.output


def test_unapproved_project_context_blocks_task_mark(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(app, ["task", "mark", "--project", "sample", "--run", "run", "--task", "T001", "--status", "open"], terminal_width=240)

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _run_with_two_tasks(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)
    output_file = tmp_path / "task-decomposer-output.md"
    output_file.write_text(
        "\n".join(
            [
                "# task-list.md",
                "",
                "## Task T001",
                "",
                "- task id: `T001`",
                "- task title: Inspect scanner solution-file categorization",
                "",
                "## Task T002",
                "",
                "- task id: `T002`",
                "- task title: Add focused `.slnx` scanner regression test",
                "",
            ]
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["agent", "import-output", "TaskDecomposerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
    )
    assert result.exit_code == 0
    return workspace, run_id


def _mark(run_id: str, task_id: str, status: str, note: str | None, covered_by: str | None = None):
    command = ["task", "mark", "--project", "sample", "--run", run_id, "--task", task_id, "--status", status]
    if covered_by:
        command.extend(["--covered-by", covered_by])
    if note:
        command.extend(["--note", note])
    return runner.invoke(app, command, terminal_width=240)


def _task_ledger(workspace: Path, run_id: str) -> dict:
    ledger_file = workspace / "runs" / "sample" / run_id / "artifacts" / "task-ledger.json"
    return json.loads(ledger_file.read_text(encoding="utf-8"))


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
