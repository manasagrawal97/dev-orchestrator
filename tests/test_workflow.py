from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.workflow import WorkflowAction, run_workflow_batch
from devo.schemas import (
    ContextSnapshot,
    ContextState,
    ContextStatus,
    ImplementationRecord,
    ProjectRegistration,
    RunArtifact,
    RunArtifactType,
    RunState,
    RunStatus,
    TaskDispositionStatus,
    TaskLedger,
    TaskLedgerEntry,
)

runner = CliRunner()


def test_workflow_status_works_for_run_created(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    result = runner.invoke(app, ["workflow", "status", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Run status: RUN_CREATED" in result.output
    assert "Lifecycle stage: requirements_definition" in result.output
    assert "IdeaAnalystAgent" in result.output
    assert (workspace / "runs" / "sample" / "run-1" / "run-state.json").exists()


def test_workflow_next_maps_run_created_to_idea_analyst(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    result = _next()

    assert result.exit_code == 0
    assert "Action type: generate_agent_prompt" in result.output
    assert "Agent: IdeaAnalystAgent" in result.output
    assert "devo agent prompt IdeaAnalystAgent" in result.output


def test_workflow_next_maps_idea_analysis_to_requirements(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.IDEA_ANALYSIS_DRAFTED, artifacts=[RunArtifactType.IDEA_ANALYSIS])

    result = _next()

    assert result.exit_code == 0
    assert "Agent: RequirementsAgent" in result.output
    assert "Next status: REQUIREMENTS_DRAFTED" in result.output


def test_workflow_next_maps_requirements_to_planner(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.REQUIREMENTS_DRAFTED,
        artifacts=[RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Agent: PlannerAgent" in result.output
    assert "Next status: PLAN_DRAFTED" in result.output


def test_workflow_next_maps_plan_drafted_to_plan_reviewer(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.PLAN_DRAFTED, artifacts=_planning_artifacts(include_plan_review=False))

    result = _next()

    assert result.exit_code == 0
    assert "Agent: PlanReviewerAgent" in result.output
    assert "Next status: PLAN_REVIEWED" in result.output


def test_workflow_next_maps_plan_reviewed_to_task_decomposer(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.PLAN_REVIEWED, artifacts=_planning_artifacts())

    result = _next()

    assert result.exit_code == 0
    assert "Agent: TaskDecomposerAgent" in result.output
    assert "Next status: TASKS_DRAFTED" in result.output


def test_workflow_next_for_tasks_drafted_selects_first_unresolved_task(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])

    result = _next()

    assert result.exit_code == 0
    assert "Agent: ImplementationCoordinatorAgent" in result.output
    assert "Task: T001" in result.output
    assert "--task T001" in result.output


def test_workflow_next_skips_covered_superseded_not_needed_and_closed_tasks(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        dispositions={
            "T001": TaskDispositionStatus.COVERED_BY,
            "T002": TaskDispositionStatus.SUPERSEDED,
            "T003": TaskDispositionStatus.NOT_NEEDED,
        },
        closed_tasks=["T004"],
        tasks=("T001", "T002", "T003", "T004", "T005"),
    )

    result = _next()

    assert result.exit_code == 0
    assert "Task: T005" in result.output
    assert "--task T005" in result.output


def test_workflow_next_for_implementation_ready_shows_report_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.IMPLEMENTATION_READY,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001")],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Action type: wait_for_input" in result.output
    assert "devo implementation report" in result.output
    assert "--task T001" in result.output
    assert "<completionReportFile>" in result.output


def test_workflow_next_maps_implementation_reported_to_validator(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.IMPLEMENTATION_REPORTED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True)],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Agent: ValidatorAgent" in result.output
    assert "--task T001" in result.output


def test_workflow_next_maps_validation_reviewed_to_code_reviewer(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.VALIDATION_REVIEWED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True, validation=True)],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Agent: CodeReviewerAgent" in result.output


def test_workflow_next_maps_code_reviewed_to_final_auditor(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.CODE_REVIEWED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True, validation=True, review=True)],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Agent: FinalAuditorAgent" in result.output


def test_workflow_next_for_final_audited_suggests_task_close_when_allowed(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.FINAL_AUDITED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[
            _implementation_record(tmp_path, "T001", completion=True, validation=True, review=True, audit=True, final_decision="close_with_notes")
        ],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Action type: close_task" in result.output
    assert "devo task close --project sample --run run-1 --task T001" in result.output


def test_workflow_next_for_final_audited_blocks_when_decision_not_closable(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.FINAL_AUDITED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[
            _implementation_record(tmp_path, "T001", completion=True, validation=True, review=True, audit=True, final_decision="blocked")
        ],
    )

    result = _next()

    assert result.exit_code == 0
    assert "Action type: blocked" in result.output
    assert "Final decision is blocked" in result.output


def test_workflow_next_after_task_closed_suggests_next_open_task(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASK_CLOSED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        tasks=("T001", "T002"),
    )

    result = _next()

    assert result.exit_code == 0
    assert "Agent: ImplementationCoordinatorAgent" in result.output
    assert "Task: T002" in result.output


def test_workflow_next_after_task_closed_suggests_run_close_when_all_resolved(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASK_CLOSED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        dispositions={"T002": TaskDispositionStatus.NOT_NEEDED},
        tasks=("T001", "T002"),
    )

    result = _next()

    assert result.exit_code == 0
    assert "Action type: close_run" in result.output
    assert "devo run close --project sample --run run-1" in result.output


def test_workflow_next_for_run_closed_reports_no_action(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CLOSED, artifacts=[RunArtifactType.TASKS], closed_tasks=["T001"], tasks=("T001",))

    result = _next()

    assert result.exit_code == 0
    assert "Action type: none" in result.output
    assert "Run is already closed" in result.output


def test_workflow_advance_does_not_fake_missing_ai_outputs(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)
    before = (workspace / "runs" / "sample" / "run-1" / "run-state.json").read_text(encoding="utf-8")

    result = runner.invoke(app, ["workflow", "advance", "--project", "sample", "--run", "run-1"], terminal_width=240)

    after = (workspace / "runs" / "sample" / "run-1" / "run-state.json").read_text(encoding="utf-8")
    assert result.exit_code == 0
    assert "workflow advance is non-mutating" in result.output
    assert "devo agent prompt IdeaAnalystAgent" in result.output
    assert after == before


def test_workflow_status_shows_warnings_for_inconsistent_missing_artifacts(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.REQUIREMENTS_DRAFTED, artifacts=[])

    result = runner.invoke(app, ["workflow", "status", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Warnings:" in result.output
    assert "Missing expected artifact" in result.output


def test_unknown_project_and_run_fail_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    project_result = runner.invoke(app, ["workflow", "next", "--project", "missing", "--run", "run-1"])
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)
    run_result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "missing"])

    assert project_result.exit_code != 0
    assert "Registered project not found: missing" in project_result.output
    assert run_result.exit_code != 0
    assert "Run not found: missing" in run_result.output


def test_workflow_commands_do_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])
    project_path = Path(json.loads((workspace / "projects" / "sample" / "project.json").read_text(encoding="utf-8"))["path"])
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    assert _next().exit_code == 0
    assert runner.invoke(app, ["workflow", "status", "--project", "sample", "--run", "run-1"]).exit_code == 0

    assert sentinel.read_text(encoding="utf-8") == before



def test_workflow_batch_on_run_created_stops_at_idea_prompt(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_AGENT_OUTPUT" in result.output
    assert "IdeaAnalystAgent" in result.output
    assert "devo agent prompt IdeaAnalystAgent" in result.output


def test_workflow_batch_does_not_mutate_state_by_default(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)
    state_path = workspace / "runs" / "sample" / "run-1" / "run-state.json"
    before = state_path.read_text(encoding="utf-8")

    result = _batch()

    assert result.exit_code == 0
    assert "Mutation occurred: False" in result.output
    assert state_path.read_text(encoding="utf-8") == before


def test_workflow_batch_writes_batch_report_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    result = _batch()

    report_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "workflow"
    assert result.exit_code == 0
    assert list(report_dir.glob("batch-report-*.md"))
    assert list(report_dir.glob("batch-report-*.json"))
    assert "Report:" in result.output


def test_workflow_batch_includes_stop_reason_in_report_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    assert _batch().exit_code == 0
    md_path, json_path = _latest_batch_reports(workspace)
    data = json.loads(json_path.read_text(encoding="utf-8"))

    assert data["project_name"] == "sample"
    assert data["run_id"] == "run-1"
    assert data["starting_status"] == "RUN_CREATED"
    assert data["stop_reason"] == "WAITING_FOR_AGENT_OUTPUT"
    assert "Stop reason: WAITING_FOR_AGENT_OUTPUT" in md_path.read_text(encoding="utf-8")


def test_workflow_batch_respects_max_steps(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    result = _batch(max_steps=0)

    assert result.exit_code == 0
    assert "Steps inspected: 0" in result.output
    assert "Stop reason: MAX_STEPS_REACHED" in result.output


def test_workflow_batch_on_run_closed_reports_no_action(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.RUN_CLOSED, artifacts=[RunArtifactType.TASKS], closed_tasks=["T001"], tasks=("T001",))

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: RUN_CLOSED" in result.output
    assert "Actions recommended:" in result.output
    assert "Step 1: none" in result.output


def test_workflow_batch_unknown_status_stops_safely(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.RUN_CREATED)

    def fake_next(project_name: str, run_id: str, workspace_root=None):
        return WorkflowAction(action_type="unknown_status", current_status="ALIEN", reason="unknown")

    monkeypatch.setattr("devo.workflow.get_next_workflow_action", fake_next)
    report = run_workflow_batch("sample", "run-1", workspace_root=workspace)

    assert report.stop_reason == "UNKNOWN_STATUS"
    assert report.actions_recommended[0].current_status == "ALIEN"


def test_workflow_batch_for_tasks_drafted_selects_first_unresolved_task(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_AGENT_OUTPUT" in result.output
    assert "ImplementationCoordinatorAgent" in result.output
    assert "--task T001" in result.output


def test_workflow_batch_skips_resolved_tasks(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASKS_DRAFTED,
        artifacts=[RunArtifactType.TASKS],
        dispositions={
            "T001": TaskDispositionStatus.COVERED_BY,
            "T002": TaskDispositionStatus.SUPERSEDED,
            "T003": TaskDispositionStatus.NOT_NEEDED,
        },
        closed_tasks=["T004"],
        tasks=("T001", "T002", "T003", "T004", "T005"),
    )

    result = _batch()

    assert result.exit_code == 0
    assert "--task T005" in result.output


def test_workflow_batch_stops_at_implementation_ready(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.IMPLEMENTATION_READY,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001")],
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_IMPLEMENTATION_REPORT" in result.output
    assert "devo implementation report" in result.output


def test_workflow_batch_stops_at_implementation_reported_with_validator(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.IMPLEMENTATION_REPORTED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True)],
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_VALIDATION_REPORT" in result.output
    assert "ValidatorAgent" in result.output


def test_workflow_batch_stops_at_validation_reviewed_with_code_reviewer(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.VALIDATION_REVIEWED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True, validation=True)],
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_CODE_REVIEW" in result.output
    assert "CodeReviewerAgent" in result.output


def test_workflow_batch_stops_at_code_reviewed_with_final_auditor(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.CODE_REVIEWED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[_implementation_record(tmp_path, "T001", completion=True, validation=True, review=True)],
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_FINAL_AUDIT" in result.output
    assert "FinalAuditorAgent" in result.output


def test_workflow_batch_stops_at_final_audited_with_task_close(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.FINAL_AUDITED,
        artifacts=[RunArtifactType.TASKS],
        current_task_id="T001",
        implementation_records=[
            _implementation_record(tmp_path, "T001", completion=True, validation=True, review=True, audit=True, final_decision="close_task")
        ],
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_TASK_CLOSE" in result.output
    assert "devo task close" in result.output


def test_workflow_batch_after_task_closed_with_unresolved_task_recommends_next_task(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASK_CLOSED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        tasks=("T001", "T002"),
    )

    result = _batch()

    assert result.exit_code == 0
    assert "ImplementationCoordinatorAgent" in result.output
    assert "--task T002" in result.output


def test_workflow_batch_after_task_closed_all_resolved_recommends_run_close(tmp_path: Path, monkeypatch) -> None:
    _workspace(
        tmp_path,
        monkeypatch,
        RunStatus.TASK_CLOSED,
        artifacts=[RunArtifactType.TASKS],
        closed_tasks=["T001"],
        dispositions={"T002": TaskDispositionStatus.NOT_NEEDED},
        tasks=("T001", "T002"),
    )

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: WAITING_FOR_RUN_CLOSE" in result.output
    assert "devo run close" in result.output


def test_workflow_batch_does_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS])
    project_path = Path(json.loads((workspace / "projects" / "sample" / "project.json").read_text(encoding="utf-8"))["path"])
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    assert _batch().exit_code == 0

    assert sentinel.read_text(encoding="utf-8") == before


def test_workflow_batch_handles_missing_task_artifact_gracefully(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[])

    result = _batch()

    assert result.exit_code == 0
    assert "Stop reason: INCONSISTENT_STATE" in result.output
    assert "tasks.md" in result.output


def test_workflow_batch_command_appears_in_readme() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo workflow batch" in readme


def _next():
    return runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)


def _batch(max_steps: int = 20):
    return runner.invoke(
        app,
        ["workflow", "batch", "--project", "sample", "--run", "run-1", "--max-steps", str(max_steps)],
        terminal_width=240,
    )


def _latest_batch_reports(workspace: Path) -> tuple[Path, Path]:
    report_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "workflow"
    md_reports = sorted(report_dir.glob("batch-report-*.md"))
    json_reports = sorted(report_dir.glob("batch-report-*.json"))
    assert md_reports
    assert json_reports
    return md_reports[-1], json_reports[-1]


def _planning_artifacts(include_plan_review: bool = True) -> list[RunArtifactType]:
    artifacts = [RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS, RunArtifactType.PLAN]
    if include_plan_review:
        artifacts.append(RunArtifactType.PLAN_REVIEW)
    return artifacts


def _workspace(
    tmp_path: Path,
    monkeypatch,
    status: RunStatus,
    artifacts: list[RunArtifactType] | None = None,
    current_task_id: str | None = None,
    implementation_records: list[ImplementationRecord] | None = None,
    dispositions: dict[str, TaskDispositionStatus] | None = None,
    closed_tasks: list[str] | None = None,
    tasks: tuple[str, ...] = ("T001", "T002", "T003"),
) -> Path:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "target-project"
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "README.md").write_text("# Target\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    project_dir = workspace / "projects" / "sample"
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name="sample",
            path=project_path.resolve(),
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    context_state_path = context_dir / "context-state.json"
    context_state_path.write_text(
        ContextState(project_name="sample", project_path=project_path.resolve(), status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    approval_path.write_text('{"project_name":"sample"}', encoding="utf-8")

    run_dir = workspace / "runs" / "sample" / "run-1"
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "prompts").mkdir(parents=True, exist_ok=True)
    run_artifacts = _create_artifacts(run_dir, artifacts or [], tasks)
    records = list(implementation_records or [])
    for task_id in closed_tasks or []:
        records.append(_implementation_record(tmp_path, task_id, completion=True, validation=True, review=True, audit=True, closed=True))

    run_state = RunState(
        project_name="sample",
        project_path=project_path.resolve(),
        run_id="run-1",
        goal="Do the next safe thing",
        status=status,
        context_snapshot=ContextSnapshot(
            context_state_path=context_state_path,
            approval_record_path=approval_path,
            approved_artifact_paths=[],
        ),
        artifacts=run_artifacts,
        current_task_id=current_task_id,
        implementation_records=records,
    )
    if dispositions:
        ledger = TaskLedger(project_name="sample", run_id="run-1")
        for task_id, disposition in dispositions.items():
            ledger.entries[task_id] = TaskLedgerEntry(
                task_id=task_id,
                disposition_status=disposition,
                covered_by_task_id="T001" if disposition == TaskDispositionStatus.COVERED_BY else None,
                disposition_note="resolved by test",
            )
        ledger_path = run_dir / "artifacts" / "task-ledger.json"
        ledger_path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
        run_state.task_ledger_path = ledger_path

    (run_dir / "goal.md").write_text("# run-1\n\nDo the next safe thing\n", encoding="utf-8")
    (run_dir / "run-state.json").write_text(run_state.model_dump_json(indent=2), encoding="utf-8")
    return workspace


def _create_artifacts(run_dir: Path, artifact_types: list[RunArtifactType], tasks: tuple[str, ...]) -> list[RunArtifact]:
    names = {
        RunArtifactType.IDEA_ANALYSIS: ("idea-analysis.md", "IdeaAnalystAgent"),
        RunArtifactType.REQUIREMENTS: ("requirements.md", "RequirementsAgent"),
        RunArtifactType.PLAN: ("plan.md", "PlannerAgent"),
        RunArtifactType.PLAN_REVIEW: ("plan-review.md", "PlanReviewerAgent"),
        RunArtifactType.TASKS: ("tasks.md", "TaskDecomposerAgent"),
    }
    artifacts: list[RunArtifact] = []
    for artifact_type in artifact_types:
        filename, agent_name = names[artifact_type]
        path = run_dir / "artifacts" / filename
        if artifact_type == RunArtifactType.TASKS:
            path.write_text(_tasks_text(tasks), encoding="utf-8")
        else:
            path.write_text(f"# {filename}\n", encoding="utf-8")
        artifacts.append(RunArtifact(artifact_type=artifact_type, agent_name=agent_name, source_file_path=path, artifact_path=path))
    return artifacts


def _tasks_text(tasks: tuple[str, ...]) -> str:
    sections = []
    for task_id in tasks:
        sections.append(f"## Task {task_id}\n\n- task title: Task {task_id} title\n")
    return "\n".join(sections)


def _implementation_record(
    tmp_path: Path,
    task_id: str,
    completion: bool = False,
    validation: bool = False,
    review: bool = False,
    audit: bool = False,
    closed: bool = False,
    final_decision: str = "close_task",
) -> ImplementationRecord:
    root = tmp_path / "implementation" / task_id
    root.mkdir(parents=True, exist_ok=True)
    brief = root / "implementation-brief.md"
    brief.write_text("brief", encoding="utf-8")
    completion_path = root / "completion-report.md" if completion else None
    validation_path = root / "validation-report.md" if validation else None
    review_path = root / "code-review.md" if review else None
    audit_path = root / "final-audit.md" if audit else None
    closure_path = root / "closure-record.md" if closed else None
    for path in (completion_path, validation_path, review_path, audit_path, closure_path):
        if path:
            path.write_text(path.name, encoding="utf-8")
    return ImplementationRecord(
        task_id=task_id,
        agent_name="ImplementationCoordinatorAgent",
        source_file_path=brief,
        implementation_brief_path=brief,
        completion_report_path=completion_path,
        validation_report_path=validation_path,
        code_review_path=review_path,
        final_audit_path=audit_path,
        final_decision=final_decision if audit else "unknown",
        closure_record_path=closure_path,
        closure_status="closed" if closed else None,
    )
