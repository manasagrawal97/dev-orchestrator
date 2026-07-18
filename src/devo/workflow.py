from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .context import load_context_state
from .projects import get_workspace_root
from .runs import (
    CODE_REVIEWER_AGENT_NAME,
    FINAL_AUDITOR_AGENT_NAME,
    IDEA_ANALYST_AGENT_NAME,
    IMPLEMENTATION_COORDINATOR_AGENT_NAME,
    PLANNER_AGENT_NAME,
    PLAN_REVIEWER_AGENT_NAME,
    REQUIREMENTS_AGENT_NAME,
    TASK_DECOMPOSER_AGENT_NAME,
    VALIDATOR_AGENT_NAME,
    find_implementation_record,
    find_run_artifact,
    get_run_artifacts_summary,
    list_run_tasks,
    load_run,
    run_path,
)
from .schemas import RunArtifactType, RunState, RunStatus, TaskDispositionStatus

RESOLVED_DISPOSITIONS = {
    TaskDispositionStatus.COVERED_BY.value,
    TaskDispositionStatus.SUPERSEDED.value,
    TaskDispositionStatus.NOT_NEEDED.value,
    TaskDispositionStatus.CLOSED_MANUALLY.value,
}
CLOSED_STATUSES = {"closed", "closed_with_notes"}
CLOSABLE_FINAL_DECISIONS = {"close_task", "close_with_notes"}


@dataclass
class WorkflowAction:
    action_type: str
    current_status: str
    next_status: str | None = None
    agent_name: str | None = None
    task_id: str | None = None
    command_to_run: str | None = None
    expected_output_artifact: str | None = None
    import_command: str | None = None
    reason: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class WorkflowStatus:
    project_name: str
    run_id: str
    run_goal: str
    run_status: str
    context_status: str | None
    lifecycle_stage: str
    artifacts_present: list[str]
    artifacts_missing: list[str]
    task_ledger_summary: dict[str, int]
    open_tasks: list[dict[str, Any]]
    closed_resolved_tasks: list[dict[str, Any]]
    dispositioned_tasks: list[dict[str, Any]]
    next_action: WorkflowAction
    can_close_run: bool
    warnings: list[str]


def get_workflow_status(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkflowStatus:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    context_status = _context_status(project_name, root)
    artifact_state = _artifact_state(run_state)
    warnings = _state_warnings(run_state, root, artifact_state)
    tasks = _safe_tasks(run_state, root, warnings)
    open_tasks = [task for task in tasks if not _task_is_resolved(task)]
    closed_resolved_tasks = [task for task in tasks if _task_has_formal_closure(task)]
    dispositioned_tasks = [task for task in tasks if task.get("disposition_status") != TaskDispositionStatus.OPEN.value]
    next_action = get_next_workflow_action(project_name, run_id, workspace_root=root)
    can_close_run = bool(tasks) and not open_tasks

    return WorkflowStatus(
        project_name=project_name,
        run_id=run_id,
        run_goal=run_state.goal,
        run_status=run_state.status.value,
        context_status=context_status,
        lifecycle_stage=_lifecycle_stage(run_state.status),
        artifacts_present=artifact_state["present"],
        artifacts_missing=artifact_state["missing"],
        task_ledger_summary=_task_ledger_summary(tasks),
        open_tasks=open_tasks,
        closed_resolved_tasks=closed_resolved_tasks,
        dispositioned_tasks=dispositioned_tasks,
        next_action=next_action,
        can_close_run=can_close_run,
        warnings=warnings,
    )


def get_next_workflow_action(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkflowAction:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    status = run_state.status
    warnings: list[str] = []

    mapping = {
        RunStatus.RUN_CREATED: (IDEA_ANALYST_AGENT_NAME, RunStatus.IDEA_ANALYSIS_DRAFTED, "artifacts/idea-analysis.md"),
        RunStatus.IDEA_ANALYSIS_DRAFTED: (REQUIREMENTS_AGENT_NAME, RunStatus.REQUIREMENTS_DRAFTED, "artifacts/requirements.md"),
        RunStatus.REQUIREMENTS_DRAFTED: (PLANNER_AGENT_NAME, RunStatus.PLAN_DRAFTED, "artifacts/plan.md"),
        RunStatus.PLAN_DRAFTED: (PLAN_REVIEWER_AGENT_NAME, RunStatus.PLAN_REVIEWED, "artifacts/plan-review.md"),
        RunStatus.PLAN_REVIEWED: (TASK_DECOMPOSER_AGENT_NAME, RunStatus.TASKS_DRAFTED, "artifacts/tasks.md"),
        RunStatus.IMPLEMENTATION_REPORTED: (VALIDATOR_AGENT_NAME, RunStatus.VALIDATION_REVIEWED, "artifacts/implementation/<taskId>/validation-report.md"),
        RunStatus.VALIDATION_REVIEWED: (CODE_REVIEWER_AGENT_NAME, RunStatus.CODE_REVIEWED, "artifacts/implementation/<taskId>/code-review.md"),
        RunStatus.CODE_REVIEWED: (FINAL_AUDITOR_AGENT_NAME, RunStatus.FINAL_AUDITED, "artifacts/implementation/<taskId>/final-audit.md"),
    }

    if status in mapping:
        agent_name, next_status, expected = mapping[status]
        task_id = _current_task_id(run_state) if _agent_is_task_specific(agent_name) else None
        blockers: list[str] = []
        if _agent_is_task_specific(agent_name) and not task_id:
            blockers.append("No current task id is recorded in run-state.json.")
        return _agent_prompt_action(
            run_state=run_state,
            agent_name=agent_name,
            next_status=next_status,
            expected_output_artifact=expected,
            task_id=task_id,
            reason=f"Run status {status.value} is ready for {agent_name} prompt generation.",
            blockers=blockers,
        )

    if status == RunStatus.TASKS_DRAFTED:
        task = _next_unresolved_task(run_state, root, warnings)
        if not task:
            return _run_close_action(run_state, warnings=warnings)
        return _implementation_prompt_action(run_state, str(task["task_id"]), warnings=warnings)

    if status == RunStatus.IMPLEMENTATION_READY:
        task_id = _current_task_id(run_state)
        blockers = [] if task_id else ["No current task id is recorded in run-state.json."]
        return WorkflowAction(
            action_type="wait_for_input",
            current_status=status.value,
            next_status=RunStatus.IMPLEMENTATION_REPORTED.value,
            task_id=task_id,
            command_to_run=_implementation_report_command(run_state, task_id or "<taskId>", "<completionReportFile>"),
            expected_output_artifact="artifacts/implementation/<taskId>/completion-report.md",
            reason="Implementation must be performed outside DevOrchestrator and reported with evidence.",
            blockers=blockers,
            warnings=warnings,
        )

    if status == RunStatus.FINAL_AUDITED:
        task_id = _current_task_id(run_state)
        record = find_implementation_record(run_state, task_id) if task_id else None
        if not task_id or not record:
            return WorkflowAction(
                action_type="blocked",
                current_status=status.value,
                task_id=task_id,
                reason="Final audit exists in status, but no current implementation record was found.",
                blockers=["No current task implementation record was found."],
                warnings=warnings,
            )
        if record.final_decision not in CLOSABLE_FINAL_DECISIONS:
            return WorkflowAction(
                action_type="blocked",
                current_status=status.value,
                task_id=task_id,
                reason=f"Task cannot be closed with final decision: {record.final_decision}.",
                blockers=[f"Final decision is {record.final_decision}."],
                warnings=warnings,
            )
        return WorkflowAction(
            action_type="close_task",
            current_status=status.value,
            next_status=RunStatus.TASK_CLOSED.value,
            task_id=task_id,
            command_to_run=f"devo task close --project {run_state.project_name} --run {run_state.run_id} --task {task_id}",
            expected_output_artifact=f"artifacts/implementation/{task_id}/closure-record.md",
            reason=f"Final decision {record.final_decision} allows formal task closure.",
            warnings=warnings,
        )

    if status == RunStatus.TASK_CLOSED:
        task = _next_unresolved_task(run_state, root, warnings)
        if task:
            return _implementation_prompt_action(run_state, str(task["task_id"]), warnings=warnings)
        return _run_close_action(run_state, warnings=warnings)

    if status == RunStatus.RUN_CLOSED:
        return WorkflowAction(
            action_type="none",
            current_status=status.value,
            reason="Run is already closed; no next workflow action is available.",
            warnings=warnings,
        )

    return WorkflowAction(
        action_type="unknown_status",
        current_status=status.value,
        reason=f"No workflow mapping exists for status {status.value}.",
        blockers=[f"Unknown workflow status: {status.value}"],
        warnings=warnings,
    )


def advance_workflow(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkflowAction:
    action = get_next_workflow_action(project_name, run_id, workspace_root=workspace_root)
    action.warnings.append("workflow advance is non-mutating for this step; run the recommended command explicitly.")
    return action


def _agent_prompt_action(
    run_state: RunState,
    agent_name: str,
    next_status: RunStatus,
    expected_output_artifact: str,
    task_id: str | None = None,
    reason: str = "",
    blockers: list[str] | None = None,
) -> WorkflowAction:
    command = f"devo agent prompt {agent_name} --project {run_state.project_name} --run {run_state.run_id}"
    if task_id:
        command = f"{command} --task {task_id}"
    import_command = (
        f"devo agent import-output {agent_name} --project {run_state.project_name} --run {run_state.run_id} --file <agentOutputFile>"
    )
    if task_id:
        import_command = f"{import_command} --task {task_id}"
    return WorkflowAction(
        action_type="generate_agent_prompt",
        current_status=run_state.status.value,
        next_status=next_status.value,
        agent_name=agent_name,
        task_id=task_id,
        command_to_run=command,
        expected_output_artifact=expected_output_artifact,
        import_command=import_command,
        reason=reason,
        blockers=blockers or [],
    )


def _implementation_prompt_action(run_state: RunState, task_id: str, warnings: list[str] | None = None) -> WorkflowAction:
    action = _agent_prompt_action(
        run_state=run_state,
        agent_name=IMPLEMENTATION_COORDINATOR_AGENT_NAME,
        next_status=RunStatus.IMPLEMENTATION_READY,
        expected_output_artifact=f"artifacts/implementation/{task_id}/implementation-brief.md",
        task_id=task_id,
        reason=f"Task {task_id} is the first unresolved task and is ready for implementation coordination.",
        blockers=[],
    )
    action.warnings = warnings or []
    return action


def _run_close_action(run_state: RunState, warnings: list[str] | None = None) -> WorkflowAction:
    return WorkflowAction(
        action_type="close_run",
        current_status=run_state.status.value,
        next_status=RunStatus.RUN_CLOSED.value,
        command_to_run=f'devo run close --project {run_state.project_name} --run {run_state.run_id} --note "Run completed."',
        expected_output_artifact="run-summary.md",
        reason="All tasks appear resolved, so the run can be closed.",
        warnings=warnings or [],
    )


def _current_task_id(run_state: RunState) -> str | None:
    if run_state.current_task_id:
        return run_state.current_task_id
    if run_state.implementation_records:
        return run_state.implementation_records[-1].task_id
    return None


def _agent_is_task_specific(agent_name: str) -> bool:
    return agent_name in {VALIDATOR_AGENT_NAME, CODE_REVIEWER_AGENT_NAME, FINAL_AUDITOR_AGENT_NAME}


def _next_unresolved_task(run_state: RunState, root: Path, warnings: list[str]) -> dict[str, Any] | None:
    tasks = _safe_tasks(run_state, root, warnings)
    for task in tasks:
        if not _task_is_resolved(task):
            return task
    return None


def _safe_tasks(run_state: RunState, root: Path, warnings: list[str]) -> list[dict[str, Any]]:
    if not find_run_artifact(run_state, RunArtifactType.TASKS):
        if run_state.status in {RunStatus.TASKS_DRAFTED, RunStatus.TASK_CLOSED}:
            warnings.append("Run status expects tasks.md, but no tasks artifact is recorded.")
        return []
    try:
        return list_run_tasks(run_state.project_name, run_state.run_id, workspace_root=root)
    except ValueError as exc:
        warnings.append(str(exc))
        return []


def _task_is_resolved(task: dict[str, Any]) -> bool:
    return _task_has_formal_closure(task) or task.get("disposition_status") in RESOLVED_DISPOSITIONS


def _task_has_formal_closure(task: dict[str, Any]) -> bool:
    return task.get("closure_status") in CLOSED_STATUSES and bool(task.get("closure_record_path"))


def _task_ledger_summary(tasks: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"open": 0, "closed": 0, "dispositioned": 0, "resolved": 0}
    for task in tasks:
        if _task_has_formal_closure(task):
            summary["closed"] += 1
        if task.get("disposition_status") != TaskDispositionStatus.OPEN.value:
            summary["dispositioned"] += 1
        if _task_is_resolved(task):
            summary["resolved"] += 1
        else:
            summary["open"] += 1
    return summary


def _artifact_state(run_state: RunState) -> dict[str, list[str]]:
    expected_by_status = {
        RunStatus.IDEA_ANALYSIS_DRAFTED: [RunArtifactType.IDEA_ANALYSIS],
        RunStatus.REQUIREMENTS_DRAFTED: [RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS],
        RunStatus.PLAN_DRAFTED: [RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS, RunArtifactType.PLAN],
        RunStatus.PLAN_REVIEWED: [RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS, RunArtifactType.PLAN, RunArtifactType.PLAN_REVIEW],
        RunStatus.TASKS_DRAFTED: [RunArtifactType.IDEA_ANALYSIS, RunArtifactType.REQUIREMENTS, RunArtifactType.PLAN, RunArtifactType.PLAN_REVIEW, RunArtifactType.TASKS],
        RunStatus.IMPLEMENTATION_READY: [RunArtifactType.TASKS],
        RunStatus.IMPLEMENTATION_REPORTED: [RunArtifactType.TASKS],
        RunStatus.VALIDATION_REVIEWED: [RunArtifactType.TASKS],
        RunStatus.CODE_REVIEWED: [RunArtifactType.TASKS],
        RunStatus.FINAL_AUDITED: [RunArtifactType.TASKS],
        RunStatus.TASK_CLOSED: [RunArtifactType.TASKS],
        RunStatus.RUN_CLOSED: [RunArtifactType.TASKS],
    }
    present = [artifact.artifact_type.value for artifact in run_state.artifacts if artifact.artifact_path.exists()]
    missing = [artifact.value for artifact in expected_by_status.get(run_state.status, []) if not find_run_artifact(run_state, artifact)]
    return {"present": sorted(set(present)), "missing": missing}


def _state_warnings(run_state: RunState, root: Path, artifact_state: dict[str, list[str]]) -> list[str]:
    warnings = list(artifact_state["missing"])
    if warnings:
        warnings = [f"Missing expected artifact: {item}" for item in warnings]
    directory = run_path(run_state.project_name, run_state.run_id, workspace_root=root)
    for required in ("goal.md", "run-state.json"):
        if not (directory / required).exists():
            warnings.append(f"Missing run file: {required}")
    if run_state.status == RunStatus.RUN_CLOSED and not run_state.run_summary_path:
        warnings.append("Run is closed but run_summary_path is not recorded.")
    return warnings


def _context_status(project_name: str, root: Path) -> str | None:
    try:
        return load_context_state(project_name, workspace_root=root).status.value
    except ValueError:
        return None


def _lifecycle_stage(status: RunStatus) -> str:
    if status in {RunStatus.RUN_CREATED, RunStatus.IDEA_ANALYSIS_DRAFTED, RunStatus.REQUIREMENTS_DRAFTED}:
        return "requirements_definition"
    if status in {RunStatus.PLAN_DRAFTED, RunStatus.PLAN_REVIEWED, RunStatus.TASKS_DRAFTED}:
        return "planning"
    if status in {RunStatus.IMPLEMENTATION_READY, RunStatus.IMPLEMENTATION_REPORTED}:
        return "implementation"
    if status in {RunStatus.VALIDATION_REVIEWED, RunStatus.CODE_REVIEWED, RunStatus.FINAL_AUDITED}:
        return "review_and_audit"
    if status in {RunStatus.TASK_CLOSED, RunStatus.RUN_CLOSED}:
        return "closure"
    return "unknown"


def _implementation_report_command(run_state: RunState, task_id: str, file_hint: str) -> str:
    return f"devo implementation report --project {run_state.project_name} --run {run_state.run_id} --task {task_id} --file {file_hint}"


