from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app

runner = CliRunner()


def test_generates_planner_prompt_after_requirements(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "planner.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "PlannerAgent" in prompt_text
    assert "plan-summary.md" in prompt_text
    assert "recommended-first-task.md" in prompt_text
    assert "Requirement one." in prompt_text


def test_planner_prompt_fails_without_requirements(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "PlannerAgent requires RequirementsAgent output" in result.output
    assert "before planning" in result.output


def test_planner_prompt_fails_after_idea_analysis_without_requirements(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "PlannerAgent requires RequirementsAgent output" in result.output
    assert "before planning" in result.output


def test_imports_planner_output_and_updates_status(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)
    output_file = tmp_path / "planner-output.md"
    output_file.write_text("# plan-summary.md\n\nSafe plan.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "PlannerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = workspace / "runs" / "sample" / run_id / "artifacts" / "plan.md"
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")
    state = _run_state(workspace, run_id)
    assert state["status"] == "PLAN_DRAFTED"
    assert "plan" in {artifact["artifact_type"] for artifact in state["artifacts"]}


def test_planner_import_fails_without_requirements(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    output_file = tmp_path / "planner-output.md"
    output_file.write_text("# plan-summary.md\n\nSafe plan.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "PlannerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "PlannerAgent requires RequirementsAgent output" in result.output
    assert "before planning" in result.output


def test_generates_plan_reviewer_prompt_after_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_plan(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlanReviewerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "plan-reviewer.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "PlanReviewerAgent" in prompt_text
    assert "review-summary.md" in prompt_text
    assert "approval-recommendation.md" in prompt_text
    assert "Safe plan." in prompt_text


def test_plan_reviewer_prompt_fails_without_plan(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlanReviewerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "PlanReviewerAgent requires PlannerAgent output" in result.output
    assert "before review" in result.output


def test_imports_plan_reviewer_output_and_updates_status(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_plan(tmp_path, monkeypatch)
    output_file = tmp_path / "plan-review-output.md"
    output_file.write_text("# approval-recommendation.md\n\napprove_with_notes\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "PlanReviewerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = workspace / "runs" / "sample" / run_id / "artifacts" / "plan-review.md"
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")
    state = _run_state(workspace, run_id)
    assert state["status"] == "PLAN_REVIEWED"
    assert "plan_review" in {artifact["artifact_type"] for artifact in state["artifacts"]}


def test_plan_reviewer_import_fails_without_plan(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)
    output_file = tmp_path / "plan-review-output.md"
    output_file.write_text("# approval-recommendation.md\n\napprove\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "PlanReviewerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "PlanReviewerAgent requires PlannerAgent output" in result.output
    assert "before review" in result.output


def test_run_artifacts_includes_plan_artifacts_and_prompts(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_plan(tmp_path, monkeypatch)
    runner.invoke(app, ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", run_id])
    runner.invoke(app, ["agent", "prompt", "PlanReviewerAgent", "--project", "sample", "--run", run_id])
    _import_plan_review(tmp_path, run_id)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "plan:" in result.output
    assert "plan-review:" in result.output
    assert "planner.prompt.md" in result.output
    assert "plan-reviewer.prompt.md" in result.output


def test_planner_prompt_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "missing", "--run", "missing-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_planner_prompt_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", "missing-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_planner_prompt(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        ["agent", "prompt", "PlannerAgent", "--project", "sample", "--run", "some-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def _run_with_plan(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)
    _import_plan(tmp_path, run_id)
    return workspace, run_id


def _run_with_requirements(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)
    _import_requirements(tmp_path, run_id)
    return workspace, run_id


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


def _import_plan(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "planner-output.md"
    output_file.write_text("# plan-summary.md\n\nSafe plan.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "PlannerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
    )
    assert result.exit_code == 0


def _import_plan_review(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "plan-review-output.md"
    output_file.write_text("# approval-recommendation.md\n\napprove_with_notes\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "PlanReviewerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
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
