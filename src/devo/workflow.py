from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .approvals import find_matching_approved_approval
from .context import load_context_state
from .policy import PolicyCheckResult, check_policy
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
from .task_selector import select_next_task

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


@dataclass
class WorkflowBatchStep:
    step_number: int
    action: WorkflowAction


@dataclass
class WorkflowBatchReport:
    project_name: str
    run_id: str
    run_goal: str
    starting_status: str
    ending_status: str
    steps_inspected: int
    actions_recommended: list[WorkflowAction]
    commands_to_run: list[str]
    artifacts_expected: list[str]
    stop_reason: str
    warnings: list[str]
    mutation_occurred: bool
    next_human_action: str
    report_path: Path | None = None
    json_report_path: Path | None = None


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
        if warnings and not task:
            return _inconsistent_action(run_state, warnings)
        if not task:
            return _run_close_action(run_state, warnings=warnings)
        policy_action = _policy_gate_action(run_state, str(task["task_id"]), root, warnings)
        if policy_action:
            return policy_action
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
        if warnings and not task:
            return _inconsistent_action(run_state, warnings)
        if task:
            policy_action = _policy_gate_action(run_state, str(task["task_id"]), root, warnings)
            if policy_action:
                return policy_action
            return _implementation_prompt_action(run_state, str(task["task_id"]), warnings=warnings)
        return _run_close_action(run_state, warnings=warnings)

    if status == RunStatus.RUN_CLOSED:
        return WorkflowAction(
            action_type="none",
            current_status=status.value,
            reason=f"Run is already closed; no next workflow action is available. Consider `devo project context-refresh --project {run_state.project_name} --run {run_state.run_id} --write-draft` if this run changed durable project context.",
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



def run_workflow_batch(
    project_name: str,
    run_id: str,
    max_steps: int = 20,
    dry_run: bool = True,
    apply: bool = False,
    workspace_root: Path | None = None,
) -> WorkflowBatchReport:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    starting_status = run_state.status.value
    actions: list[WorkflowAction] = []
    warnings: list[str] = []
    stop_reason = "MAX_STEPS_REACHED"

    if apply:
        warnings.append("--apply is deferred; workflow batch remains non-mutating and reports recommended commands only.")
    if max_steps <= 0:
        warnings.append("max_steps was zero; no workflow actions were inspected.")
    else:
        for _index in range(max_steps):
            action = get_next_workflow_action(project_name, run_id, workspace_root=root)
            if apply:
                action.warnings.append("--apply is deferred for this action; run the recommended command explicitly.")
            actions.append(action)
            warnings.extend(action.warnings)
            stop_reason = _batch_stop_reason(action)
            break

    ending_status = load_run(project_name, run_id, workspace_root=root).status.value
    report = WorkflowBatchReport(
        project_name=project_name,
        run_id=run_id,
        run_goal=run_state.goal,
        starting_status=starting_status,
        ending_status=ending_status,
        steps_inspected=len(actions),
        actions_recommended=actions,
        commands_to_run=[action.command_to_run for action in actions if action.command_to_run],
        artifacts_expected=[action.expected_output_artifact for action in actions if action.expected_output_artifact],
        stop_reason=stop_reason,
        warnings=_dedupe(warnings),
        mutation_occurred=False,
        next_human_action=_next_human_action(stop_reason, actions[-1] if actions else None),
    )
    report_path, json_path = _write_batch_report(report, root)
    report.report_path = report_path
    report.json_report_path = json_path
    return report


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




def _policy_gate_action(run_state: RunState, task_id: str, root: Path, warnings: list[str]) -> WorkflowAction | None:
    policy = _safe_policy_check(run_state, task_id, root, warnings)
    if not policy:
        return None
    policy_warning = (
        f"Policy risk for task {task_id}: {policy.risk_level}; "
        f"approval_required={policy.approval_required}; blocked={policy.blocked}."
    )
    if policy.risk_level in {"medium", "high", "critical"}:
        warnings.append(policy_warning)
    if policy.blocked:
        return WorkflowAction(
            action_type="blocked",
            current_status=run_state.status.value,
            task_id=task_id,
            command_to_run=f"devo approval request --project {run_state.project_name} --run {run_state.run_id} --task {task_id} --action implementation_prompt",
            reason=f"Policy gate blocked critical risk task {task_id}; approval override is not implemented.",
            blockers=["Task is blocked by current policy."],
            warnings=warnings,
        )
    if not policy.approval_required:
        return None

    approval = find_matching_approved_approval(
        run_state.project_name,
        run_state.run_id,
        task_id,
        "implementation_prompt",
        workspace_root=root,
    )
    if approval:
        warnings.append(f"Policy approval {approval.approval_id} matches task {task_id} scope.")
        return None

    return WorkflowAction(
        action_type="approval_required",
        current_status=run_state.status.value,
        task_id=task_id,
        command_to_run=f"devo approval request --project {run_state.project_name} --run {run_state.run_id} --task {task_id} --action implementation_prompt",
        reason=f"Task {task_id} is high risk and needs a matching Devo approval before implementation prompt generation.",
        blockers=[policy.required_approval_note or f"Approval required for task {task_id}."],
        warnings=warnings,
    )


def _safe_policy_check(run_state: RunState, task_id: str, root: Path, warnings: list[str]) -> PolicyCheckResult | None:
    try:
        return check_policy(
            run_state.project_name,
            run_state.run_id,
            task_id,
            action_type="implementation_prompt",
            workspace_root=root,
        )
    except ValueError as exc:
        warnings.append(f"Policy check failed for task {task_id}: {exc}")
        return None
def _inconsistent_action(run_state: RunState, warnings: list[str]) -> WorkflowAction:
    return WorkflowAction(
        action_type="blocked",
        current_status=run_state.status.value,
        reason="Run state is inconsistent; resolve warnings before advancing workflow.",
        blockers=list(warnings),
        warnings=warnings,
    )


def _batch_stop_reason(action: WorkflowAction) -> str:
    if action.action_type == "none":
        return "RUN_CLOSED"
    if action.action_type == "unknown_status":
        return "UNKNOWN_STATUS"
    if action.action_type == "blocked" or action.blockers:
        return "INCONSISTENT_STATE"
    if action.action_type == "close_task":
        return "WAITING_FOR_TASK_CLOSE"
    if action.action_type == "close_run":
        return "WAITING_FOR_RUN_CLOSE"
    if action.action_type == "wait_for_input":
        return "WAITING_FOR_IMPLEMENTATION_REPORT"
    if action.agent_name == VALIDATOR_AGENT_NAME:
        return "WAITING_FOR_VALIDATION_REPORT"
    if action.agent_name == CODE_REVIEWER_AGENT_NAME:
        return "WAITING_FOR_CODE_REVIEW"
    if action.agent_name == FINAL_AUDITOR_AGENT_NAME:
        return "WAITING_FOR_FINAL_AUDIT"
    if action.action_type == "generate_agent_prompt":
        return "WAITING_FOR_AGENT_OUTPUT"
    return "UNKNOWN_STATUS"


def _next_human_action(stop_reason: str, action: WorkflowAction | None) -> str:
    if action and action.command_to_run:
        if stop_reason == "WAITING_FOR_AGENT_OUTPUT":
            return "Run the prompt command, produce the requested output, then import it with the shown import command."
        if stop_reason == "WAITING_FOR_IMPLEMENTATION_REPORT":
            return "Complete implementation outside DevOrchestrator, then import the completion report with the shown command."
        if stop_reason in {"WAITING_FOR_VALIDATION_REPORT", "WAITING_FOR_CODE_REVIEW", "WAITING_FOR_FINAL_AUDIT"}:
            return "Run the prompt command, produce the review artifact, then import it with the shown import command."
        if stop_reason in {"WAITING_FOR_TASK_CLOSE", "WAITING_FOR_RUN_CLOSE"}:
            return "Review the recommendation and run the shown closure command when ready."
    if stop_reason == "RUN_CLOSED":
        return "No action needed; the run is closed."
    if stop_reason == "MAX_STEPS_REACHED":
        return "Increase --max-steps and rerun workflow batch if more inspection is needed."
    if stop_reason in {"INCONSISTENT_STATE", "UNKNOWN_STATUS"}:
        return "Resolve blockers or inconsistent state before continuing."
    return "Inspect workflow status and choose the next safe command."


def _write_batch_report(report: WorkflowBatchReport, root: Path) -> tuple[Path, Path]:
    report_dir = run_path(report.project_name, report.run_id, workspace_root=root) / "artifacts" / "workflow"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    md_path = report_dir / f"batch-report-{timestamp}.md"
    json_path = report_dir / f"batch-report-{timestamp}.json"
    md_path.write_text(_render_batch_report_markdown(report), encoding="utf-8")
    data = asdict(report)
    data["report_path"] = str(md_path)
    data["json_report_path"] = str(json_path)
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return md_path, json_path


def _render_batch_report_markdown(report: WorkflowBatchReport) -> str:
    lines = [
        "# Workflow batch report",
        "",
        f"Project: {report.project_name}",
        f"Run: {report.run_id}",
        f"Goal: {report.run_goal}",
        f"Starting status: {report.starting_status}",
        f"Ending status: {report.ending_status}",
        f"Steps inspected: {report.steps_inspected}",
        f"Stop reason: {report.stop_reason}",
        f"Mutation occurred: {report.mutation_occurred}",
        "",
        "## Steps",
        "",
    ]
    if not report.actions_recommended:
        lines.append("- none")
    for index, action in enumerate(report.actions_recommended, start=1):
        lines.extend(
            [
                f"### Step {index}",
                "",
                f"- action_type: {action.action_type}",
                f"- current_status: {action.current_status}",
                f"- next_status: {action.next_status or 'none'}",
                f"- agent_name: {action.agent_name or 'none'}",
                f"- task_id: {action.task_id or 'none'}",
                f"- expected_output_artifact: {action.expected_output_artifact or 'none'}",
                f"- reason: {action.reason or 'none'}",
                "",
                "Command:",
                "",
                f"    {action.command_to_run or 'none'}",
                "",
                "Import command:",
                "",
                f"    {action.import_command or 'none'}",
                "",
            ]
        )
    lines.extend(["## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Next human action", "", report.next_human_action, ""])
    return "\n".join(lines)


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _current_task_id(run_state: RunState) -> str | None:
    if run_state.current_task_id:
        return run_state.current_task_id
    if run_state.implementation_records:
        return run_state.implementation_records[-1].task_id
    return None


def _agent_is_task_specific(agent_name: str) -> bool:
    return agent_name in {VALIDATOR_AGENT_NAME, CODE_REVIEWER_AGENT_NAME, FINAL_AUDITOR_AGENT_NAME}


def _next_unresolved_task(run_state: RunState, root: Path, warnings: list[str]) -> dict[str, Any] | None:
    selection = select_next_task(run_state.project_name, run_state.run_id, workspace_root=root)
    warnings.extend(selection.warnings)
    warnings.extend(selection.blockers)
    if selection.selected:
        return {"task_id": selection.selected.task_id, "task_title": selection.selected.title}
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
