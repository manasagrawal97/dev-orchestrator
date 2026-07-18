from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import ImplementationRecord, RunArtifactType, RunStatus, TaskDispositionStatus
from devo.task_selector import list_task_candidates, select_next_task
from tests.test_workflow import _implementation_record, _workspace

runner = CliRunner()


def test_task_next_selects_first_open_task_from_task_ledger(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])
    _write_ledger(workspace, {"T001": {"disposition_status": "open"}})

    result = runner.invoke(app, ["task", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Selected task: T001 Task T001 title" in result.output
    assert "Suggested next command: devo agent prompt ImplementationCoordinatorAgent" in result.output


def test_task_next_skips_closed_task(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        tasks=("T001", "T002"),
    )

    selection = select_next_task("sample", "run-1")

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert selection.skipped[0].skip_reason == "formal closure status is closed"


def test_task_next_skips_covered_by(tmp_path: Path, monkeypatch) -> None:
    selection = _selection_with_disposition(tmp_path, monkeypatch, TaskDispositionStatus.COVERED_BY)

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert "covered_by" in selection.skipped[0].skip_reason


def test_task_next_skips_superseded(tmp_path: Path, monkeypatch) -> None:
    selection = _selection_with_disposition(tmp_path, monkeypatch, TaskDispositionStatus.SUPERSEDED)

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert "superseded" in selection.skipped[0].skip_reason


def test_task_next_skips_not_needed(tmp_path: Path, monkeypatch) -> None:
    selection = _selection_with_disposition(tmp_path, monkeypatch, TaskDispositionStatus.NOT_NEEDED)

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert "not_needed" in selection.skipped[0].skip_reason


def test_task_next_skips_closed_manually(tmp_path: Path, monkeypatch) -> None:
    selection = _selection_with_disposition(tmp_path, monkeypatch, TaskDispositionStatus.CLOSED_MANUALLY)

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert "closed_manually" in selection.skipped[0].skip_reason


def test_task_next_preserves_task_order_when_equal(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T003", "T001", "T002"))
    _write_tasks(workspace, ("T003", "T001", "T002"))

    selection = select_next_task("sample", "run-1")

    assert selection.selected
    assert selection.selected.task_id == "T003"


def test_task_next_reports_no_actionable_tasks_when_all_resolved(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASK_CLOSED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        dispositions={"T002": TaskDispositionStatus.NOT_NEEDED},
        tasks=("T001", "T002"),
    )

    result = runner.invoke(app, ["task", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Selected task: none" in result.output
    assert "Run may be ready for closure: True" in result.output


def test_task_next_warns_on_unknown_status(tmp_path: Path, monkeypatch) -> None:
    record = _implementation_record_with_closure(tmp_path, "T001", "mystery")
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        implementation_records=[record],
        tasks=("T001", "T002"),
    )

    selection = select_next_task("sample", "run-1")

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert "unknown closure status" in selection.warnings[0]


def test_task_next_falls_back_to_tasks_md_when_ledger_missing(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001",))

    selection = select_next_task("sample", "run-1")

    assert selection.selected
    assert selection.selected.task_id == "T001"
    assert selection.source_artifact.endswith("tasks.md")


def test_task_candidates_lists_selectable_and_skipped(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        dispositions={"T001": TaskDispositionStatus.NOT_NEEDED},
        tasks=("T001", "T002"),
    )

    result = runner.invoke(app, ["task", "candidates", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "T001: Task T001 title" in result.output
    assert "selection status: skipped_resolved" in result.output
    assert "T002: Task T002 title" in result.output
    assert "selection status: selectable" in result.output


def test_task_candidates_includes_skip_reasons(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        dispositions={"T001": TaskDispositionStatus.NOT_NEEDED},
        tasks=("T001", "T002"),
    )

    candidates = list_task_candidates("sample", "run-1")

    assert candidates.skipped[0].skip_reason == "disposition is not_needed"


def test_safest_strategy_prefers_low_risk_when_available(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001", "T002"))
    _write_tasks(workspace, ("T001", "T002"), risks={"T001": "high", "T002": "low"})

    selection = select_next_task("sample", "run-1", strategy="safest")

    assert selection.selected
    assert selection.selected.task_id == "T002"
    assert selection.selected.risk == "low"


def test_selector_does_not_invent_risk_or_priority_when_missing(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001",))

    selection = select_next_task("sample", "run-1")

    assert selection.selected
    assert selection.selected.risk is None
    assert selection.selected.priority is None


def test_task_next_json_output_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001",))

    result = runner.invoke(app, ["task", "next", "--project", "sample", "--run", "run-1", "--format", "json"], terminal_width=240)
    data = json.loads(result.output)

    assert result.exit_code == 0
    assert data["selected"]["task_id"] == "T001"
    assert data["suggested_command"].endswith("--task T001")


def test_workflow_next_reuses_task_selector_for_tasks_drafted(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001", "T002"))
    _write_tasks(workspace, ("T001", "T002"), risks={"T001": "high", "T002": "low"})

    result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "--task T002" in result.output


def test_workflow_batch_reuses_task_selector(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=("T001", "T002"))
    _write_tasks(workspace, ("T001", "T002"), risks={"T001": "high", "T002": "low"})

    result = runner.invoke(app, ["workflow", "batch", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "--task T002" in result.output


def test_task_selector_does_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])
    project_path = Path(json.loads((workspace / "projects" / "sample" / "project.json").read_text(encoding="utf-8"))["path"])
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    assert runner.invoke(app, ["task", "next", "--project", "sample", "--run", "run-1"]).exit_code == 0
    assert runner.invoke(app, ["task", "candidates", "--project", "sample", "--run", "run-1"]).exit_code == 0

    assert sentinel.read_text(encoding="utf-8") == before


def test_task_selector_unknown_project_and_run_fail_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    project_result = runner.invoke(app, ["task", "next", "--project", "missing", "--run", "run-1"])
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])
    run_result = runner.invoke(app, ["task", "candidates", "--project", "sample", "--run", "missing"])

    assert project_result.exit_code != 0
    assert "Registered project not found: missing" in project_result.output
    assert run_result.exit_code != 0
    assert "Run not found: missing" in run_result.output


def test_task_selection_commands_are_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo task next" in readme
    assert "devo task candidates" in readme


def _selection_with_disposition(tmp_path: Path, monkeypatch, disposition: TaskDispositionStatus):
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        dispositions={"T001": disposition},
        tasks=("T001", "T002"),
    )
    return select_next_task("sample", "run-1")


def _write_tasks(workspace: Path, task_ids: tuple[str, ...], risks: dict[str, str] | None = None) -> None:
    risks = risks or {}
    sections = []
    for task_id in task_ids:
        lines = [f"## Task {task_id}", "", f"- task title: Task {task_id} title"]
        if task_id in risks:
            lines.append(f"- risk level: {risks[task_id]}")
        sections.append("\n".join(lines) + "\n")
    (workspace / "runs" / "sample" / "run-1" / "artifacts" / "tasks.md").write_text("\n".join(sections), encoding="utf-8")


def _write_ledger(workspace: Path, entries: dict[str, dict[str, str]]) -> None:
    path = workspace / "runs" / "sample" / "run-1" / "artifacts" / "task-ledger.json"
    normalized_entries = {task_id: {"task_id": task_id, **entry} for task_id, entry in entries.items()}
    data = {"project_name": "sample", "run_id": "run-1", "entries": normalized_entries}
    path.write_text(json.dumps(data), encoding="utf-8")


def _implementation_record_with_closure(tmp_path: Path, task_id: str, closure_status: str) -> ImplementationRecord:
    record = _implementation_record(tmp_path, task_id, completion=True, validation=True, review=True, audit=True)
    closure_path = tmp_path / "implementation" / task_id / "closure-record.md"
    closure_path.write_text("closure", encoding="utf-8")
    return record.model_copy(update={"closure_status": closure_status, "closure_record_path": closure_path})

