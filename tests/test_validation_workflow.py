from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_implementation_reporting import _import_completion_report, _run_with_implementation_brief
from tests.test_run_implementation_coordinator import _run_with_tasks
from tests.test_run_planning import _approved_project

runner = CliRunner()


def test_generates_validator_prompt_after_implementation_reported(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "validator-T001.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "ValidatorAgent" in prompt_text
    assert "validation-summary.md" in prompt_text
    assert "validation-decision.md" in prompt_text
    assert "Implement T001 safely." in prompt_text
    assert "73 passed" in prompt_text
    assert "894f3ddbb8b3f014fc0db99fdb3cb4ebdbeb501f" in prompt_text


def test_validator_prompt_fails_without_completion_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "ValidatorAgent requires reported" in result.output
    assert "validation review" in result.output


def test_imports_validator_output_and_copies_validation_report(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    validation_file = _validation_report(tmp_path, "passed_with_notes")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(validation_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Imported output" in result.output
    assert "Status: VALIDATION_REVIEWED" in result.output
    artifact_file = _validation_report_artifact(workspace, run_id)
    assert artifact_file.read_text(encoding="utf-8") == validation_file.read_text(encoding="utf-8")


def test_run_status_updates_to_validation_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    _import_validation_report(tmp_path, run_id, "passed")

    state = _run_state(workspace, run_id)

    assert state["status"] == "VALIDATION_REVIEWED"
    record = state["implementation_records"][0]
    assert record["validation_report_path"].endswith("artifacts\\implementation\\T001\\validation-report.md")
    assert record["validated_at"] is not None
    assert record["validation_decision"] == "passed"


def test_validation_status_shows_report_and_decision(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    _import_validation_report(tmp_path, run_id, "needs_more_evidence")

    result = runner.invoke(
        app,
        ["validation", "status", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Run status: VALIDATION_REVIEWED" in result.output
    assert "validation-report.md" in result.output
    assert "Validation decision: needs_more_evidence" in result.output


def test_run_artifacts_lists_validation_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    _import_validation_report(tmp_path, run_id, "passed_with_notes")

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "implementation:" in result.output
    assert "completion-report.md" in result.output
    assert "validation-report.md" in result.output


def test_validator_import_fails_without_completion_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    validation_file = _validation_report(tmp_path, "passed")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(validation_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "ValidatorAgent requires reported" in result.output
    assert "validation review" in result.output


def test_validator_prompt_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ValidatorAgent",
            "--project",
            "missing",
            "--run",
            "missing-run",
            "--task",
            "T001",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_validator_prompt_missing_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            "missing-run",
            "--task",
            "T001",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_validation_review(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            "some-run",
            "--task",
            "T001",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _run_with_reported_implementation(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_implementation_brief(tmp_path, monkeypatch)
    _import_completion_report(tmp_path, run_id)
    return workspace, run_id


def _validation_report(tmp_path: Path, decision: str) -> Path:
    output_file = tmp_path / f"validation-{decision}.md"
    output_file.write_text(
        "\n".join(
            [
                "# validation-summary.md",
                "",
                "Reported validation evidence covers the selected task with notes.",
                "",
                "# validation-evidence.md",
                "",
                "- Reported test result: 73 passed",
                "",
                "# commands-reviewed.md",
                "",
                "- pytest",
                "",
                "# scope-coverage.md",
                "",
                "The report stays within T001 scope.",
                "",
                "# gaps-or-concerns.md",
                "",
                "No blocking gaps identified.",
                "",
                "# validation-decision.md",
                "",
                decision,
                "",
                "# recommended-next-step.md",
                "",
                "Proceed to code review.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_file


def _import_validation_report(tmp_path: Path, run_id: str, decision: str) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "ValidatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(_validation_report(tmp_path, decision)),
        ],
    )
    assert result.exit_code == 0


def _validation_report_artifact(workspace: Path, run_id: str) -> Path:
    return (
        workspace
        / "runs"
        / "sample"
        / run_id
        / "artifacts"
        / "implementation"
        / "T001"
        / "validation-report.md"
    )


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
