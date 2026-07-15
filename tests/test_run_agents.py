from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app

runner = CliRunner()


def test_generates_idea_analyst_prompt_for_run(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "IdeaAnalystAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "idea-analyst.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "IdeaAnalystAgent" in prompt_text
    assert "goal-analysis.md" in prompt_text
    assert "Add command search" in prompt_text
    assert "Approved Project Context" in prompt_text


def test_imports_idea_analyst_output(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    output_file = tmp_path / "idea-output.md"
    output_file.write_text("# goal-analysis.md\n\nUseful idea analysis.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "IdeaAnalystAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = workspace / "runs" / "sample" / run_id / "artifacts" / "idea-analysis.md"
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")
    assert "IDEA_ANALYSIS_DRAFTED" in result.output


def test_run_status_updates_to_idea_analysis_drafted(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)

    state = _run_state(workspace, run_id)

    assert state["status"] == "IDEA_ANALYSIS_DRAFTED"
    assert state["artifacts"][0]["artifact_type"] == "idea_analysis"


def test_generates_requirements_prompt_after_idea_analysis(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)

    result = runner.invoke(
        app,
        ["agent", "prompt", "RequirementsAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "requirements-agent.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "RequirementsAgent" in prompt_text
    assert "requirements.md" in prompt_text
    assert "acceptance-criteria.md" in prompt_text
    assert "Useful idea analysis." in prompt_text
    assert "Idea Analysis Status" in prompt_text


def test_imports_requirements_output(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)
    output_file = tmp_path / "requirements-output.md"
    output_file.write_text("# requirements.md\n\nRequirement one.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "RequirementsAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = workspace / "runs" / "sample" / run_id / "artifacts" / "requirements.md"
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")


def test_run_status_updates_to_requirements_drafted(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)
    _import_requirements(tmp_path, run_id)

    state = _run_state(workspace, run_id)

    assert state["status"] == "REQUIREMENTS_DRAFTED"
    assert {artifact["artifact_type"] for artifact in state["artifacts"]} == {"idea_analysis", "requirements"}


def test_requirements_import_fails_without_idea_analysis_unless_override(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    output_file = tmp_path / "requirements-output.md"
    output_file.write_text("# requirements.md\n\nRequirement one.\n", encoding="utf-8")

    blocked = runner.invoke(
        app,
        ["agent", "import-output", "RequirementsAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )
    allowed = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "RequirementsAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--file",
            str(output_file),
            "--allow-missing-idea-analysis",
        ],
        terminal_width=240,
    )

    assert blocked.exit_code != 0
    assert "RequirementsAgent import requires" in blocked.output
    assert "allow-missing-idea-analysis" in blocked.output
    assert allowed.exit_code == 0
    assert _run_state(workspace, run_id)["status"] == "REQUIREMENTS_DRAFTED"


def test_run_artifacts_command(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    runner.invoke(app, ["agent", "prompt", "IdeaAnalystAgent", "--project", "sample", "--run", run_id])
    _import_idea_analysis(tmp_path, run_id)
    _import_requirements(tmp_path, run_id)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "goal.md" in result.output
    assert "run-state.json" in result.output
    assert "idea-analysis" in result.output
    assert "requirements" in result.output
    assert "analyst.prompt" in result.output


def test_run_level_prompt_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["agent", "prompt", "IdeaAnalystAgent", "--project", "missing", "--run", "missing-run"],
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_run_level_prompt_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "IdeaAnalystAgent", "--project", "sample", "--run", "missing-run"],
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_run_level_agent_prompts(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        ["agent", "prompt", "IdeaAnalystAgent", "--project", "sample", "--run", "some-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _approved_project_with_run(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace = _approved_project(tmp_path, monkeypatch)
    result = runner.invoke(app, ["run", "create", "--project", "sample", "--goal", "Add command search"])
    assert result.exit_code == 0
    run_dirs = list((workspace / "runs" / "sample").iterdir())
    assert len(run_dirs) == 1
    return workspace, run_dirs[0].name


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


def _import_idea_analysis(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "idea-output.md"
    output_file.write_text("# goal-analysis.md\n\nUseful idea analysis.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "IdeaAnalystAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
    )
    assert result.exit_code == 0


def _import_requirements(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "requirements-output.md"
    output_file.write_text("# requirements.md\n\nRequirement one.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "RequirementsAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
    )
    assert result.exit_code == 0


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))


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
