from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_planning import (
    _approved_project,
    _approved_project_with_run,
    _import_idea_analysis,
    _import_plan,
    _import_plan_review,
    _import_requirements,
    _run_with_plan,
    _run_with_requirements,
)

runner = CliRunner()


def test_generates_task_decomposer_prompt_after_plan_review(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code == 0
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "task-decomposer.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "TaskDecomposerAgent" in prompt_text
    assert "task-list.md" in prompt_text
    assert "task-dependency-map.md" in prompt_text
    assert "first-safe-task.md" in prompt_text
    assert "Safe plan." in prompt_text
    assert "approve_with_notes" in prompt_text


def test_task_decomposer_prompt_fails_without_plan(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_requirements(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "TaskDecomposerAgent requires a reviewed plan" in result.output
    assert "before task decomposition" in result.output


def test_task_decomposer_prompt_fails_without_plan_review(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_plan(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "TaskDecomposerAgent requires a reviewed plan" in result.output
    assert "before task decomposition" in result.output


def test_imports_task_decomposer_output(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)
    output_file = tmp_path / "task-decomposer-output.md"
    output_file.write_text("# task-list.md\n\n- Task ID: T001\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "TaskDecomposerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = workspace / "runs" / "sample" / run_id / "artifacts" / "tasks.md"
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")


def test_run_status_updates_to_tasks_drafted(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)
    _import_tasks(tmp_path, run_id)

    state = _run_state(workspace, run_id)

    assert state["status"] == "TASKS_DRAFTED"
    assert "tasks" in {artifact["artifact_type"] for artifact in state["artifacts"]}


def test_run_artifacts_lists_tasks(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)
    runner.invoke(app, ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", run_id])
    _import_tasks(tmp_path, run_id)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "tasks:" in result.output
    assert "tasks.md" in result.output
    assert "task-decomposer.prompt.md" in result.output


def test_task_decomposer_prompt_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "missing", "--run", "missing-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_task_decomposer_prompt_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", "missing-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Run not found: missing-run" in result.output


def test_unapproved_project_context_blocks_task_decomposition(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])

    result = runner.invoke(
        app,
        ["agent", "prompt", "TaskDecomposerAgent", "--project", "sample", "--run", "some-run"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Project context must be approved before" in result.output


def test_task_decomposer_import_blocked_before_plan_reviewed(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_plan(tmp_path, monkeypatch)
    output_file = tmp_path / "task-decomposer-output.md"
    output_file.write_text("# task-list.md\n\n- Task ID: T001\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["agent", "import-output", "TaskDecomposerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "TaskDecomposerAgent requires a reviewed plan" in result.output
    assert "before task decomposition" in result.output


def _run_with_reviewed_plan(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _approved_project_with_run(tmp_path, monkeypatch)
    _import_idea_analysis(tmp_path, run_id)
    _import_requirements(tmp_path, run_id)
    _import_plan(tmp_path, run_id)
    _import_plan_review(tmp_path, run_id)
    return workspace, run_id


def _import_tasks(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "task-decomposer-output.md"
    output_file.write_text("# task-list.md\n\n- Task ID: T001\n", encoding="utf-8")
    result = runner.invoke(
        app,
        ["agent", "import-output", "TaskDecomposerAgent", "--project", "sample", "--run", run_id, "--file", str(output_file)],
    )
    assert result.exit_code == 0


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
