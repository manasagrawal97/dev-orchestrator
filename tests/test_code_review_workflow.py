from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_planning import _approved_project
from tests.test_validation_workflow import _import_validation_report, _run_with_reported_implementation

runner = CliRunner()


def test_generates_code_reviewer_prompt_after_validation_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "CodeReviewerAgent",
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
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "code-reviewer-T001.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "CodeReviewerAgent" in prompt_text
    assert "review-summary.md" in prompt_text
    assert "review-decision.md" in prompt_text
    assert "Do not pretend to have reviewed source code" in prompt_text
    assert "Implement T001 safely." in prompt_text
    assert "73 passed" in prompt_text
    assert "validation-decision.md" in prompt_text


def test_code_reviewer_prompt_fails_without_validation_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "CodeReviewerAgent",
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
    assert "CodeReviewerAgent requires reviewed validation" in result.output
    assert "before code review" in result.output


def test_imports_code_reviewer_output_and_copies_report(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    review_file = _code_review_report(tmp_path, "approve_with_notes")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "CodeReviewerAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(review_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Imported output" in result.output
    assert "Status: CODE_REVIEWED" in result.output
    artifact_file = _code_review_artifact(workspace, run_id)
    assert artifact_file.read_text(encoding="utf-8") == review_file.read_text(encoding="utf-8")


def test_run_status_updates_to_code_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    _import_code_review(tmp_path, run_id, "approve")

    state = _run_state(workspace, run_id)

    assert state["status"] == "CODE_REVIEWED"
    record = state["implementation_records"][0]
    assert record["code_review_path"].endswith("artifacts\\implementation\\T001\\code-review.md")
    assert record["reviewed_at"] is not None
    assert record["review_decision"] == "approve"


def test_review_status_shows_report_and_decision(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    _import_code_review(tmp_path, run_id, "changes_requested")

    result = runner.invoke(
        app,
        ["review", "status", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Run status: CODE_REVIEWED" in result.output
    assert "code-review.md" in result.output
    assert "Review decision: changes_requested" in result.output


def test_run_artifacts_lists_code_review_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    _import_code_review(tmp_path, run_id, "approve_with_notes")

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "implementation:" in result.output
    assert "validation-report.md" in result.output
    assert "code-review.md" in result.output


def test_code_reviewer_import_fails_without_validation_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    review_file = _code_review_report(tmp_path, "approve")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "CodeReviewerAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(review_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "CodeReviewerAgent requires reviewed validation" in result.output
    assert "before code review" in result.output


def test_code_reviewer_prompt_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "CodeReviewerAgent",
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


def test_code_reviewer_prompt_missing_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "CodeReviewerAgent",
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


def test_unapproved_project_context_blocks_code_review(tmp_path: Path, monkeypatch) -> None:
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
            "CodeReviewerAgent",
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


def _run_with_validation_review(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_reported_implementation(tmp_path, monkeypatch)
    _import_validation_report(tmp_path, run_id, "passed_with_notes")
    return workspace, run_id


def _code_review_report(tmp_path: Path, decision: str) -> Path:
    output_file = tmp_path / f"code-review-{decision}.md"
    output_file.write_text(
        "\n".join(
            [
                "# review-summary.md",
                "",
                "Reviewed completion and validation evidence only; no source diff was provided.",
                "",
                "# scope-review.md",
                "",
                "The reported work stays within T001 scope.",
                "",
                "# changed-files-review.md",
                "",
                "Changed files were reviewed from completion evidence only.",
                "",
                "# quality-review.md",
                "",
                "No quality issue is supported by provided evidence.",
                "",
                "# risk-review.md",
                "",
                "Residual risk is evidence-limited because no diff was provided.",
                "",
                "# test-review.md",
                "",
                "Reported validation included 73 passed.",
                "",
                "# findings.md",
                "",
                "none supported by provided evidence",
                "",
                "# review-decision.md",
                "",
                decision,
                "",
                "# recommended-next-step.md",
                "",
                "Proceed to the next workflow step.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_file


def _import_code_review(tmp_path: Path, run_id: str, decision: str) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "CodeReviewerAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(_code_review_report(tmp_path, decision)),
        ],
    )
    assert result.exit_code == 0


def _code_review_artifact(workspace: Path, run_id: str) -> Path:
    return workspace / "runs" / "sample" / run_id / "artifacts" / "implementation" / "T001" / "code-review.md"


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
