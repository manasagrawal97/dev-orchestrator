from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_implementation_coordinator import _import_implementation_brief, _run_with_tasks
from tests.test_run_planning import _approved_project

runner = CliRunner()


def test_imports_completion_report_after_implementation_ready(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    report_file = _completion_report(tmp_path)

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(report_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Imported implementation report" in result.output
    assert "73 passed" in result.output
    report_artifact = _completion_report_artifact(workspace, run_id)
    assert report_artifact.read_text(encoding="utf-8") == report_file.read_text(encoding="utf-8")


def test_run_status_updates_to_implementation_reported(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    _import_completion_report(tmp_path, run_id)

    state = _run_state(workspace, run_id)

    assert state["status"] == "IMPLEMENTATION_REPORTED"
    record = state["implementation_records"][0]
    assert record["completion_report_path"].endswith("artifacts\\implementation\\T001\\completion-report.md")
    assert record["reported_at"] is not None
    assert record["validation_summary"] == "73 passed"
    assert record["commit_hash"] == "894f3ddbb8b3f014fc0db99fdb3cb4ebdbeb501f"


def test_implementation_status_shows_report_path(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    _import_completion_report(tmp_path, run_id)

    result = runner.invoke(
        app,
        ["implementation", "status", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Run status: IMPLEMENTATION_REPORTED" in result.output
    assert "completion-report.md" in result.output
    assert "73 passed" in result.output
    assert "894f3ddbb8b3f014fc0db99fdb3cb4ebdbeb501f" in result.output


def test_run_artifacts_lists_completion_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    _import_completion_report(tmp_path, run_id)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "implementation:" in result.output
    assert "implementation-brief.md" in result.output
    assert "completion-report.md" in result.output


def test_completion_report_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    report_file = _completion_report(tmp_path)

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "missing",
            "--run",
            "missing-run",
            "--task",
            "T001",
            "--file",
            str(report_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_completion_report_missing_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)
    report_file = _completion_report(tmp_path)

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            "missing-run",
            "--task",
            "T001",
            "--file",
            str(report_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_completion_report_missing_implementation_brief_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)
    report_file = _completion_report(tmp_path)

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(report_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Implementation brief not found for task: T001" in result.output


def test_completion_report_missing_report_file_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    missing_file = tmp_path / "missing-report.md"

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(missing_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Completion report file does not exist" in result.output


def test_unapproved_project_context_blocks_completion_report(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    report_file = _completion_report(tmp_path)

    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            "some-run",
            "--task",
            "T001",
            "--file",
            str(report_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _run_with_implementation_brief(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)
    _import_implementation_brief(tmp_path, run_id)
    return workspace, run_id


def _completion_report(tmp_path: Path) -> Path:
    report_file = tmp_path / "completion-report.md"
    report_file.write_text(
        "\n".join(
            [
                "# Completion Report",
                "",
                "- task id: T001",
                "- task title: Inspect scanner solution-file categorization",
                "- summary: Added focused regression coverage.",
                "- changed files: tests/test_scanner.py",
                "- commands run: pytest",
                "- test results: 73 passed",
                "- validation result: pass",
                "- git commit hash: 894f3ddbb8b3f014fc0db99fdb3cb4ebdbeb501f",
                "- push result: pushed to main",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report_file


def _import_completion_report(tmp_path: Path, run_id: str) -> None:
    result = runner.invoke(
        app,
        [
            "implementation",
            "report",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(_completion_report(tmp_path)),
        ],
    )
    assert result.exit_code == 0


def _completion_report_artifact(workspace: Path, run_id: str) -> Path:
    return (
        workspace
        / "runs"
        / "sample"
        / run_id
        / "artifacts"
        / "implementation"
        / "T001"
        / "completion-report.md"
    )


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
