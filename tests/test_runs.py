from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app

runner = CliRunner()


def test_create_run_for_approved_project_context(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["run", "create", "--project", "sample", "--goal", "Add command search"],
        terminal_width=240,
    )

    assert result.exit_code == 0
    run_id = _only_run_id(workspace)
    assert re.match(r"\d{4}-\d{2}-\d{2}-\d{6}-add-command-search", run_id)
    assert "Created run" in result.output
    assert run_id in result.output


def test_create_run_fails_when_context_is_not_approved(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        ["run", "create", "--project", "sample", "--goal", "Add command search"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output
    assert "creating development runs." in result.output


def test_run_folder_structure_is_created(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)

    runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])

    run_dir = _only_run_dir(workspace)
    for subdirectory in ("artifacts", "prompts", "validation", "reviews", "logs", "approvals"):
        assert (run_dir / subdirectory).is_dir()


def test_goal_markdown_is_created(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)

    runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])

    run_dir = _only_run_dir(workspace)
    goal_text = (run_dir / "goal.md").read_text(encoding="utf-8")
    assert "Project: sample" in goal_text
    assert "Run ID:" in goal_text
    assert "Add command search" in goal_text
    assert "Initial status: RUN_CREATED" in goal_text


def test_run_state_json_is_created(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)

    runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])

    run_dir = _only_run_dir(workspace)
    data = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
    assert data["project_name"] == "sample"
    assert data["goal"] == "Add command search"
    assert data["status"] == "RUN_CREATED"
    assert data["context_snapshot"]["approval_record_path"].endswith("context-approval.json")
    assert data["context_snapshot"]["approved_artifact_paths"]


def test_list_runs(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)
    create_result = runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])

    result = runner.invoke(app, ["run", "list", "--project", "sample"], terminal_width=240)

    assert create_result.exit_code == 0
    assert result.exit_code == 0
    assert "RUN_CREATED" in result.output
    assert "Add command search" in result.output


def test_run_status(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)
    runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])
    run_id = _only_run_id(workspace)

    result = runner.invoke(app, ["run", "status", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert run_id in result.output
    assert "Project: sample" in result.output
    assert "Status: RUN_CREATED" in result.output
    assert "Add command search" in result.output
    assert "context-approval.json" in result.output


def test_use_project(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(app, ["use", "--project", "sample"])

    assert result.exit_code == 0
    data = json.loads((workspace / "current.json").read_text(encoding="utf-8"))
    assert data["project_name"] == "sample"
    assert data["run_id"] is None


def test_use_project_and_run(tmp_path: Path, monkeypatch) -> None:
    workspace = _approved_project(tmp_path, monkeypatch)
    runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])
    run_id = _only_run_id(workspace)

    result = runner.invoke(app, ["use", "--project", "sample", "--run", run_id])

    assert result.exit_code == 0
    data = json.loads((workspace / "current.json").read_text(encoding="utf-8"))
    assert data["project_name"] == "sample"
    assert data["run_id"] == run_id
    assert data["run_path"].endswith(run_id)


def test_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["run", "create", "--project", "missing", "--goal", "Add command search"])

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(app, ["run", "status", "missing-run", "--project", "sample"])

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def _approved_project(tmp_path: Path, monkeypatch) -> Path:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    discovery_file = tmp_path / "discovery.md"
    discovery_file.write_text(_discovery_output(), encoding="utf-8")
    review_file = tmp_path / "review.md"
    review_file.write_text("# Review\napproval recommendation: approve_with_notes\n", encoding="utf-8")

    assert runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)]).exit_code == 0
    assert runner.invoke(app, ["project", "scan", "sample"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["agent", "import-output", "ProjectContextDiscoveryAgent", "--project", "sample", "--file", str(discovery_file)],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            ["agent", "import-output", "ProjectContextReviewerAgent", "--project", "sample", "--file", str(review_file)],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["project", "approve-context", "sample"]).exit_code == 0
    return workspace


def _only_run_dir(workspace: Path) -> Path:
    run_dirs = list((workspace / "runs" / "sample").iterdir())
    assert len(run_dirs) == 1
    return run_dirs[0]


def _only_run_id(workspace: Path) -> str:
    return _only_run_dir(workspace).name


def _discovery_output() -> str:
    sections = [
        "# project-profile.md\n\nDetected facts only.\n",
        "# architecture-map.md\n\nDetected architecture.\n",
        "# module-map.md\n\nDetected modules.\n",
        "# data-model-summary.md\n\nDetected data model.\n",
        "# validation-profile.md\n\nDetected validation.\n",
        (
            "# risk-profile.md\n\n"
            "Future planning agents should treat these areas as requiring extra care:\n\n"
            "- Database migrations.\n"
        ),
        "# unknowns.md\n\nUnknowns are clearly marked.\n",
    ]
    return "\n---\n\n".join(sections)
