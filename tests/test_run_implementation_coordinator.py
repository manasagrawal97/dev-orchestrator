from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from tests.test_run_planning import _approved_project
from tests.test_run_task_decomposer import _run_with_reviewed_plan

runner = CliRunner()


def test_generates_implementation_coordinator_prompt_after_tasks_drafted(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ImplementationCoordinatorAgent",
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
    prompt_file = workspace / "runs" / "sample" / run_id / "prompts" / "implementation-coordinator-T001.prompt.md"
    prompt_text = prompt_file.read_text(encoding="utf-8")
    assert "ImplementationCoordinatorAgent" in prompt_text
    assert "implementation-brief.md" in prompt_text
    assert "codex-execution-prompt.md" in prompt_text
    assert "Selected task id" in prompt_text
    assert "T001" in prompt_text
    assert "Inspect scanner solution-file categorization" in prompt_text


def test_implementation_prompt_fails_if_task_id_is_missing(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["agent", "prompt", "ImplementationCoordinatorAgent", "--project", "sample", "--run", run_id],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "ImplementationCoordinatorAgent requires --task" in result.output


def test_implementation_prompt_fails_if_task_id_is_not_found(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ImplementationCoordinatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T999",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Task id not found in tasks.md: T999" in result.output


def test_implementation_prompt_fails_before_tasks_drafted(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ImplementationCoordinatorAgent",
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
    assert "ImplementationCoordinatorAgent requires drafted" in result.output
    assert "tasks" in result.output


def test_imports_implementation_coordinator_output(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)
    output_file = tmp_path / "implementation-output.md"
    output_file.write_text("# implementation-brief.md\n\nImplement T001 safely.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "ImplementationCoordinatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(output_file),
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0
    artifact_file = (
        workspace
        / "runs"
        / "sample"
        / run_id
        / "artifacts"
        / "implementation"
        / "T001"
        / "implementation-brief.md"
    )
    assert artifact_file.read_text(encoding="utf-8") == output_file.read_text(encoding="utf-8")


def test_run_status_updates_to_implementation_ready(tmp_path: Path, monkeypatch) -> None:
    workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)
    _import_implementation_brief(tmp_path, run_id)

    state = _run_state(workspace, run_id)

    assert state["status"] == "IMPLEMENTATION_READY"
    assert state["current_task_id"] == "T001"
    assert state["implementation_brief_path"].endswith("artifacts\\implementation\\T001\\implementation-brief.md")
    assert state["implementation_ready_at"] is not None
    assert state["implementation_records"][0]["task_id"] == "T001"


def test_run_artifacts_lists_implementation_brief(tmp_path: Path, monkeypatch) -> None:
    _workspace, run_id = _run_with_tasks(tmp_path, monkeypatch)
    _import_implementation_brief(tmp_path, run_id)

    result = runner.invoke(app, ["run", "artifacts", run_id, "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "implementation:" in result.output
    assert "T001" in result.output
    assert "implementation-brief.md" in result.output


def test_implementation_prompt_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ImplementationCoordinatorAgent",
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


def test_implementation_prompt_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _approved_project(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "agent",
            "prompt",
            "ImplementationCoordinatorAgent",
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


def test_unapproved_project_context_blocks_implementation_coordination(tmp_path: Path, monkeypatch) -> None:
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
            "ImplementationCoordinatorAgent",
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


def _run_with_tasks(tmp_path: Path, monkeypatch) -> tuple[Path, str]:
    workspace, run_id = _run_with_reviewed_plan(tmp_path, monkeypatch)
    _import_tasks(tmp_path, run_id)
    return workspace, run_id


def _import_tasks(tmp_path: Path, run_id: str) -> None:
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
                "- objective: Identify scanner logic before implementation.",
                "- scope: DevOrchestrator scanner only.",
                "- out-of-scope: PersonalOS changes.",
                "- files/areas likely involved, if known: `src/devo/scanner.py`",
                "- validation required: pytest",
                "- risk level: low",
                "- dependency on previous tasks, if any: none",
                "- recommended executor: Codex",
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


def _import_implementation_brief(tmp_path: Path, run_id: str) -> None:
    output_file = tmp_path / "implementation-output.md"
    output_file.write_text("# implementation-brief.md\n\nImplement T001 safely.\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "agent",
            "import-output",
            "ImplementationCoordinatorAgent",
            "--project",
            "sample",
            "--run",
            run_id,
            "--task",
            "T001",
            "--file",
            str(output_file),
        ],
    )
    assert result.exit_code == 0


def _run_state(workspace: Path, run_id: str) -> dict:
    state_file = workspace / "runs" / "sample" / run_id / "run-state.json"
    return json.loads(state_file.read_text(encoding="utf-8"))
