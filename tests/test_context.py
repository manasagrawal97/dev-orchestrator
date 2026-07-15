from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.context import DISCOVERY_DRAFT_NAME, REVIEW_ARTIFACT_NAME
from devo.main import app

runner = CliRunner()


def test_imports_project_context_discovery_output(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _registered_scanned_project(tmp_path, monkeypatch)
    output_file = tmp_path / "discovery-output.md"
    output_file.write_text("# Project profile\nDetected facts only.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "ProjectContextDiscoveryAgent", "--project", "sample", "--file", str(output_file)],
    )

    assert result.exit_code == 0
    draft_file = workspace / "projects" / "sample" / "context" / "drafts" / DISCOVERY_DRAFT_NAME
    state_file = workspace / "projects" / "sample" / "context" / "context-state.json"
    assert draft_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["status"] == "CONTEXT_DRAFTED"
    assert state["discovery_artifact"]["agent_name"] == "ProjectContextDiscoveryAgent"
    assert Path(state["discovery_artifact"]["artifact_path"]) == draft_file


def test_generates_project_context_reviewer_prompt(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _registered_scanned_project(tmp_path, monkeypatch)
    _import_discovery_output(tmp_path)

    result = runner.invoke(
        app,
        ["agent", "prompt", "ProjectContextReviewerAgent", "--project", "sample"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "projects" / "sample" / "prompts" / "project-context-reviewer.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "ProjectContextReviewerAgent" in prompt_text
    assert "Did discovery invent facts?" in prompt_text
    assert "approval recommendation: approve / approve_with_notes / revise_required" in prompt_text
    assert "Detected facts only." in prompt_text
    assert '"project_name": "sample"' in prompt_text
    assert str(project_path.resolve()) in prompt_text


def test_imports_project_context_reviewer_output(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _registered_scanned_project(tmp_path, monkeypatch)
    _import_discovery_output(tmp_path)
    review_file = tmp_path / "review-output.md"
    review_file.write_text("# Review\napproval recommendation: approve_with_notes\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "ProjectContextReviewerAgent", "--project", "sample", "--file", str(review_file)],
    )

    assert result.exit_code == 0
    review_artifact = workspace / "projects" / "sample" / "context" / "reviews" / REVIEW_ARTIFACT_NAME
    state = json.loads((workspace / "projects" / "sample" / "context" / "context-state.json").read_text(encoding="utf-8"))
    assert review_artifact.read_text(encoding="utf-8") == review_file.read_text(encoding="utf-8")
    assert state["status"] == "CONTEXT_REVIEWED"
    assert state["review_artifact"]["agent_name"] == "ProjectContextReviewerAgent"


def test_context_status_command_shows_lifecycle_state(tmp_path: Path, monkeypatch) -> None:
    _workspace, _project_path = _registered_scanned_project(tmp_path, monkeypatch)
    _import_discovery_output(tmp_path)

    result = runner.invoke(app, ["project", "context-status", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "sample" in result.output
    assert "Scan status: SCANNED" in result.output
    assert "Context status: CONTEXT_DRAFTED" in result.output
    assert "project-context-discovery" in result.output
    assert "Approval status: none" in result.output


def test_approve_context_requires_discovery_output(tmp_path: Path, monkeypatch) -> None:
    _registered_scanned_project(tmp_path, monkeypatch)

    result = runner.invoke(app, ["project", "approve-context", "sample"])

    assert result.exit_code != 0
    assert "Cannot approve context before importing" in result.output
    assert "ProjectContextDiscoveryAgent output" in result.output


def test_approve_context_requires_review_output(tmp_path: Path, monkeypatch) -> None:
    _registered_scanned_project(tmp_path, monkeypatch)
    _import_discovery_output(tmp_path)

    result = runner.invoke(app, ["project", "approve-context", "sample"])

    assert result.exit_code != 0
    assert "Cannot approve context before importing" in result.output
    assert "ProjectContextReviewerAgent output" in result.output


def test_approve_context_creates_record_and_approved_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _registered_scanned_project(tmp_path, monkeypatch)
    _import_discovery_output(tmp_path)
    _import_review_output(tmp_path)

    result = runner.invoke(app, ["project", "approve-context", "sample"])

    assert result.exit_code == 0
    approval_file = workspace / "projects" / "sample" / "approvals" / "context-approval.json"
    approved_discovery = workspace / "projects" / "sample" / "context" / "approved" / DISCOVERY_DRAFT_NAME
    approved_review = workspace / "projects" / "sample" / "context" / "approved" / REVIEW_ARTIFACT_NAME
    state = json.loads((workspace / "projects" / "sample" / "context" / "context-state.json").read_text(encoding="utf-8"))
    approval = json.loads(approval_file.read_text(encoding="utf-8"))

    assert approval_file.exists()
    assert approved_discovery.exists()
    assert approved_review.exists()
    assert approval["approved_by"] == "user"
    assert state["status"] == "CONTEXT_APPROVED"
    assert state["approved_by"] == "user"


def test_unknown_agent_import_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _registered_scanned_project(tmp_path, monkeypatch)
    output_file = tmp_path / "output.md"
    output_file.write_text("content\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "UnknownAgent", "--project", "sample", "--file", str(output_file)],
    )

    assert result.exit_code != 0
    assert "Unknown agent: UnknownAgent" in result.output


def test_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["project", "context-status", "missing"])

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def _registered_scanned_project(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    add_result = runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    scan_result = runner.invoke(app, ["project", "scan", "sample"])
    assert add_result.exit_code == 0
    assert scan_result.exit_code == 0
    return workspace, project_path


def _import_discovery_output(tmp_path: Path) -> None:
    output_file = tmp_path / "discovery-output.md"
    output_file.write_text("# Project profile\nDetected facts only.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "ProjectContextDiscoveryAgent", "--project", "sample", "--file", str(output_file)],
    )
    assert result.exit_code == 0


def _import_review_output(tmp_path: Path) -> None:
    review_file = tmp_path / "review-output.md"
    review_file.write_text("# Review\napproval recommendation: approve\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "ProjectContextReviewerAgent", "--project", "sample", "--file", str(review_file)],
    )
    assert result.exit_code == 0
