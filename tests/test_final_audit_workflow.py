from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_code_review_workflow import _import_code_review, _run_with_validation_review
from tests.test_run_planning import _approved_project

runner = CliRunner()


def test_generates_final_auditor_prompt_after_code_reviewed(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "FinalAuditorAgent",
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
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "final-auditor-T001.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "FinalAuditorAgent" in prompt_text
    assert "audit-summary.md" in prompt_text
    assert "final-decision.md" in prompt_text
    assert "Implement T001 safely." in prompt_text
    assert "73 passed" in prompt_text
    assert "validation-decision.md" in prompt_text
    assert "review-decision.md" in prompt_text


def test_final_auditor_prompt_fails_without_code_review_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "FinalAuditorAgent",
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
    assert "FinalAuditorAgent requires code review" in result.output
    assert "before final audit" in result.output


def test_imports_final_auditor_output_and_copies_report(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)
    audit_file = _final_audit_report(tmp_path, "close_with_notes")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "FinalAuditorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(audit_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Imported output" in result.output
    assert "Status: FINAL_AUDITED" in result.output
    artifact_file = _final_audit_artifact(workspace, run_id)
    assert artifact_file.read_text(encoding="utf-8") == audit_file.read_text(encoding="utf-8")


def test_run_status_updates_to_final_audited(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)
    _import_final_audit(tmp_path, run_id, "close_task")

    state = _run_state(workspace, run_id)

    assert state["status"] == "FINAL_AUDITED"
    record = state["implementation_records"][0]
    assert record["final_audit_path"].endswith("artifacts\\implementation\\T001\\final-audit.md")
    assert record["audited_at"] is not None
    assert record["final_decision"] == "close_task"


def test_audit_status_shows_report_and_decision(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)
    _import_final_audit(tmp_path, run_id, "needs_follow_up")

    result = runner.invoke(
        app,
        ["audit", "status", "--project", "sample", "--run", run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "Run status: FINAL_AUDITED" in result.output
    assert "final-audit.md" in result.output
    assert "Final decision: needs_follow_up" in result.output


def test_run_artifacts_lists_final_audit_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_code_review(tmp_path, monkeypatch)
    _import_final_audit(tmp_path, run_id, "close_with_notes")

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "implementation:" in result.output
    assert "code-review.md" in result.output
    assert "final-audit.md" in result.output


def test_final_auditor_import_fails_without_code_review_report(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    audit_file = _final_audit_report(tmp_path, "close_task")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "FinalAuditorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(audit_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "FinalAuditorAgent requires code review" in result.output
    assert "before final audit" in result.output


def test_final_auditor_prompt_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "FinalAuditorAgent",
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


def test_final_auditor_prompt_missing_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "FinalAuditorAgent",
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


def test_unapproved_project_context_blocks_final_audit(tmp_path: Path, monkeypatch) -> None:
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
            "FinalAuditorAgent",
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


def _run_with_code_review(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_validation_review(tmp_path, monkeypatch)
    _import_code_review(tmp_path, run_id, "approve_with_notes")
    return workspace, run_id


def _final_audit_report(tmp_path: Path, decision: str) -> Path:
    output_file = tmp_path / f"final-audit-{decision}.md"
    output_file.write_text(
        "\n".join(
            [
                "# audit-summary.md",
                "",
                "The selected task has implementation, validation, and code review evidence.",
                "",
                "# lifecycle-check.md",
                "",
                "Implementation, validation, and code review reports are present.",
                "",
                "# evidence-check.md",
                "",
                "Evidence supports final audit with notes.",
                "",
                "# decision-check.md",
                "",
                "Validation and code review decisions support closure with notes.",
                "",
                "# unresolved-notes.md",
                "",
                "Evidence is bounded to recorded reports.",
                "",
                "# final-decision.md",
                "",
                decision,
                "",
                "# recommended-next-step.md",
                "",
                "Proceed according to the final decision.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output_file


def _import_final_audit(tmp_path: Path, run_id: str, decision: str) -> None:
    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "FinalAuditorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(_final_audit_report(tmp_path, decision)),
        ],
    )
    assert result.exit_code == 0


def _final_audit_artifact(workspace: Path, run_id: str) -> Path:
    return workspace / "runs" / "sample" / run_id / "artifacts" / "implementation" / "T001" / "final-audit.md"


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
