from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .context import APPROVAL_RECORD_NAME, CONTEXT_STATE_NAME, load_context_state
from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import (
    ContextSnapshot,
    ContextStatus,
    CurrentSelection,
    ImplementationRecord,
    RunAgentImportRecord,
    RunArtifact,
    RunArtifactType,
    RunState,
    RunStatus,
    TaskDispositionStatus,
    TaskLedger,
    TaskLedgerEntry,
)

IDEA_ANALYST_AGENT_NAME = "IdeaAnalystAgent"
REQUIREMENTS_AGENT_NAME = "RequirementsAgent"
PLANNER_AGENT_NAME = "PlannerAgent"
PLAN_REVIEWER_AGENT_NAME = "PlanReviewerAgent"
TASK_DECOMPOSER_AGENT_NAME = "TaskDecomposerAgent"
IMPLEMENTATION_COORDINATOR_AGENT_NAME = "ImplementationCoordinatorAgent"
VALIDATOR_AGENT_NAME = "ValidatorAgent"
CODE_REVIEWER_AGENT_NAME = "CodeReviewerAgent"
FINAL_AUDITOR_AGENT_NAME = "FinalAuditorAgent"
IDEA_ANALYSIS_ARTIFACT_NAME = "idea-analysis.md"
REQUIREMENTS_ARTIFACT_NAME = "requirements.md"
PLAN_ARTIFACT_NAME = "plan.md"
PLAN_REVIEW_ARTIFACT_NAME = "plan-review.md"
TASKS_ARTIFACT_NAME = "tasks.md"
IMPLEMENTATION_BRIEF_ARTIFACT_NAME = "implementation-brief.md"
COMPLETION_REPORT_ARTIFACT_NAME = "completion-report.md"
VALIDATION_REPORT_ARTIFACT_NAME = "validation-report.md"
CODE_REVIEW_ARTIFACT_NAME = "code-review.md"
FINAL_AUDIT_ARTIFACT_NAME = "final-audit.md"
CLOSURE_RECORD_ARTIFACT_NAME = "closure-record.md"
TASK_LEDGER_ARTIFACT_NAME = "task-ledger.json"

RUN_STATUS_ORDER = {
    RunStatus.RUN_CREATED: 0,
    RunStatus.IDEA_ANALYSIS_DRAFTED: 1,
    RunStatus.REQUIREMENTS_DRAFTED: 2,
    RunStatus.PLAN_DRAFTED: 3,
    RunStatus.PLAN_REVIEWED: 4,
    RunStatus.TASKS_DRAFTED: 5,
    RunStatus.IMPLEMENTATION_READY: 6,
    RunStatus.IMPLEMENTATION_REPORTED: 7,
    RunStatus.VALIDATION_REVIEWED: 8,
    RunStatus.CODE_REVIEWED: 9,
    RunStatus.FINAL_AUDITED: 10,
    RunStatus.TASK_CLOSED: 11,
}

TASK_CLOSING_FINAL_DECISIONS = {
    "close_task": "closed",
    "close_with_notes": "closed_with_notes",
}

RUN_SUBDIRECTORIES = (
    "artifacts",
    "prompts",
    "validation",
    "reviews",
    "logs",
    "approvals",
)


def create_run(project_name: str, goal: str, workspace_root: Path | None = None) -> RunState:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    require_context_approved(project_name, workspace_root=root)

    created_at = datetime.now(UTC)
    run_id = _unique_run_id(root, project_name, goal, created_at)
    run_dir = _run_dir(root, project_name, run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    for subdirectory in RUN_SUBDIRECTORIES:
        (run_dir / subdirectory).mkdir(parents=True, exist_ok=True)

    run_state = RunState(
        project_name=project_name,
        project_path=registration.path,
        run_id=run_id,
        goal=goal,
        status=RunStatus.RUN_CREATED,
        created_at=created_at,
        context_snapshot=_build_context_snapshot(root, project_name),
    )

    (run_dir / "goal.md").write_text(_render_goal_markdown(run_state), encoding="utf-8")
    (run_dir / "run-state.json").write_text(run_state.model_dump_json(indent=2), encoding="utf-8")
    return run_state


def list_runs(project_name: str, workspace_root: Path | None = None) -> list[RunState]:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    runs_root = root / "runs" / project_name
    if not runs_root.exists():
        return []

    runs: list[RunState] = []
    for state_file in sorted(runs_root.glob("*/run-state.json")):
        data = json.loads(state_file.read_text(encoding="utf-8"))
        runs.append(RunState.model_validate(data))
    return runs


def load_run(project_name: str, run_id: str, workspace_root: Path | None = None) -> RunState:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    state_file = _run_dir(root, project_name, run_id) / "run-state.json"
    if not state_file.exists():
        msg = f"Run not found: {run_id}"
        raise ValueError(msg)

    data = json.loads(state_file.read_text(encoding="utf-8"))
    return RunState.model_validate(data)


def save_run_state(run_state: RunState, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    state_file = _run_dir(root, run_state.project_name, run_state.run_id) / "run-state.json"
    state_file.write_text(run_state.model_dump_json(indent=2), encoding="utf-8")


def import_run_agent_output(
    agent_name: str,
    project_name: str,
    run_id: str,
    source_file: Path,
    task_id: str | None = None,
    allow_missing_idea_analysis: bool = False,
    workspace_root: Path | None = None,
) -> RunAgentImportRecord:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Import file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Import path must be a file: {source_path}"
        raise ValueError(msg)

    if agent_name == IDEA_ANALYST_AGENT_NAME:
        artifact_type = RunArtifactType.IDEA_ANALYSIS
        artifact_name = IDEA_ANALYSIS_ARTIFACT_NAME
        next_status = RunStatus.IDEA_ANALYSIS_DRAFTED
    elif agent_name == REQUIREMENTS_AGENT_NAME:
        if not find_run_artifact(run_state, RunArtifactType.IDEA_ANALYSIS) and not allow_missing_idea_analysis:
            msg = "RequirementsAgent import requires IdeaAnalystAgent output. Use --allow-missing-idea-analysis to override."
            raise ValueError(msg)
        artifact_type = RunArtifactType.REQUIREMENTS
        artifact_name = REQUIREMENTS_ARTIFACT_NAME
        next_status = RunStatus.REQUIREMENTS_DRAFTED
    elif agent_name == PLANNER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.REQUIREMENTS_DRAFTED,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.REQUIREMENTS,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        artifact_type = RunArtifactType.PLAN
        artifact_name = PLAN_ARTIFACT_NAME
        next_status = RunStatus.PLAN_DRAFTED
    elif agent_name == PLAN_REVIEWER_AGENT_NAME:
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "PlanReviewerAgent requires PlannerAgent output before review.",
        )
        artifact_type = RunArtifactType.PLAN_REVIEW
        artifact_name = PLAN_REVIEW_ARTIFACT_NAME
        next_status = RunStatus.PLAN_REVIEWED
    elif agent_name == TASK_DECOMPOSER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.PLAN_REVIEWED,
            "TaskDecomposerAgent requires a reviewed plan before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "TaskDecomposerAgent requires PlannerAgent output before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN_REVIEW,
            "TaskDecomposerAgent requires PlanReviewerAgent output before task decomposition.",
        )
        artifact_type = RunArtifactType.TASKS
        artifact_name = TASKS_ARTIFACT_NAME
        next_status = RunStatus.TASKS_DRAFTED
    elif agent_name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.TASKS_DRAFTED,
            "ImplementationCoordinatorAgent requires drafted tasks before implementation coordination.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.TASKS,
            "ImplementationCoordinatorAgent requires TaskDecomposerAgent output before implementation coordination.",
        )
        require_task_excerpt(run_state, normalized_task_id)
        artifact_type = RunArtifactType.IMPLEMENTATION_BRIEF
        artifact_name = IMPLEMENTATION_BRIEF_ARTIFACT_NAME
        next_status = RunStatus.IMPLEMENTATION_READY
    elif agent_name == VALIDATOR_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.IMPLEMENTATION_REPORTED,
            "ValidatorAgent requires reported implementation completion before validation review.",
        )
        require_implementation_completion(run_state, normalized_task_id)
        artifact_type = RunArtifactType.VALIDATION_REPORT
        artifact_name = VALIDATION_REPORT_ARTIFACT_NAME
        next_status = RunStatus.VALIDATION_REVIEWED
    elif agent_name == CODE_REVIEWER_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.VALIDATION_REVIEWED,
            "CodeReviewerAgent requires reviewed validation evidence before code review.",
        )
        require_validation_review(run_state, normalized_task_id)
        artifact_type = RunArtifactType.CODE_REVIEW
        artifact_name = CODE_REVIEW_ARTIFACT_NAME
        next_status = RunStatus.CODE_REVIEWED
    elif agent_name == FINAL_AUDITOR_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.CODE_REVIEWED,
            "FinalAuditorAgent requires code review evidence before final audit.",
        )
        require_code_review(run_state, normalized_task_id)
        artifact_type = RunArtifactType.FINAL_AUDIT
        artifact_name = FINAL_AUDIT_ARTIFACT_NAME
        next_status = RunStatus.FINAL_AUDITED
    else:
        msg = f"Run-level import is not supported for agent: {agent_name}"
        raise ValueError(msg)

    if agent_name in {
        IMPLEMENTATION_COORDINATOR_AGENT_NAME,
        VALIDATOR_AGENT_NAME,
        CODE_REVIEWER_AGENT_NAME,
        FINAL_AUDITOR_AGENT_NAME,
    }:
        artifact_path = _implementation_artifact_dir(root, project_name, run_id, normalized_task_id) / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        artifact_path = _run_dir(root, project_name, run_id) / "artifacts" / artifact_name
    shutil.copyfile(source_path, artifact_path)
    artifact = RunArtifact(
        artifact_type=artifact_type,
        agent_name=agent_name,
        source_file_path=source_path,
        artifact_path=artifact_path,
    )
    if agent_name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        run_state.artifacts = [
            existing
            for existing in run_state.artifacts
            if not (
                existing.artifact_type == artifact_type
                and existing.artifact_path.parent.name == normalized_task_id
            )
        ]
        imported_at = datetime.now(UTC)
        run_state.implementation_records = [
            existing for existing in run_state.implementation_records if existing.task_id != normalized_task_id
        ]
        run_state.implementation_records.append(
            ImplementationRecord(
                task_id=normalized_task_id,
                agent_name=agent_name,
                source_file_path=source_path,
                implementation_brief_path=artifact_path,
                imported_at=imported_at,
            )
        )
        run_state.current_task_id = normalized_task_id
        run_state.implementation_brief_path = artifact_path
        run_state.implementation_ready_at = imported_at
    elif agent_name == VALIDATOR_AGENT_NAME:
        run_state.artifacts = [
            existing
            for existing in run_state.artifacts
            if not (
                existing.artifact_type == artifact_type
                and existing.artifact_path.parent.name == normalized_task_id
            )
        ]
        validated_at = datetime.now(UTC)
        report_text = source_path.read_text(encoding="utf-8")
        run_state.implementation_records = [
            existing.model_copy(
                update={
                    "validation_report_path": artifact_path,
                    "validated_at": validated_at,
                    "validation_decision": _extract_validation_decision(report_text),
                }
            )
            if existing.task_id == normalized_task_id
            else existing
            for existing in run_state.implementation_records
        ]
    elif agent_name == CODE_REVIEWER_AGENT_NAME:
        run_state.artifacts = [
            existing
            for existing in run_state.artifacts
            if not (
                existing.artifact_type == artifact_type
                and existing.artifact_path.parent.name == normalized_task_id
            )
        ]
        reviewed_at = datetime.now(UTC)
        review_text = source_path.read_text(encoding="utf-8")
        run_state.implementation_records = [
            existing.model_copy(
                update={
                    "code_review_path": artifact_path,
                    "reviewed_at": reviewed_at,
                    "review_decision": _extract_review_decision(review_text),
                }
            )
            if existing.task_id == normalized_task_id
            else existing
            for existing in run_state.implementation_records
        ]
    elif agent_name == FINAL_AUDITOR_AGENT_NAME:
        run_state.artifacts = [
            existing
            for existing in run_state.artifacts
            if not (
                existing.artifact_type == artifact_type
                and existing.artifact_path.parent.name == normalized_task_id
            )
        ]
        audited_at = datetime.now(UTC)
        audit_text = source_path.read_text(encoding="utf-8")
        run_state.implementation_records = [
            existing.model_copy(
                update={
                    "final_audit_path": artifact_path,
                    "audited_at": audited_at,
                    "final_decision": _extract_final_decision(audit_text),
                }
            )
            if existing.task_id == normalized_task_id
            else existing
            for existing in run_state.implementation_records
        ]
    else:
        run_state.artifacts = [
            existing for existing in run_state.artifacts if existing.artifact_type != artifact_type
        ]
    run_state.artifacts.append(artifact)
    run_state.status = next_status
    run_state.updated_at = datetime.now(UTC)
    save_run_state(run_state, workspace_root=root)

    return RunAgentImportRecord(
        project_name=project_name,
        run_id=run_id,
        agent_name=agent_name,
        artifact=artifact,
        status_after_import=next_status,
    )


def import_implementation_completion_report(
    project_name: str,
    run_id: str,
    task_id: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> ImplementationRecord:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Completion report file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Completion report path must be a file: {source_path}"
        raise ValueError(msg)

    record = find_implementation_record(run_state, normalized_task_id)
    if not record or not record.implementation_brief_path.exists():
        msg = f"Implementation brief not found for task: {normalized_task_id}"
        raise ValueError(msg)

    report_path = record.implementation_brief_path.parent / COMPLETION_REPORT_ARTIFACT_NAME
    shutil.copyfile(source_path, report_path)
    report_text = source_path.read_text(encoding="utf-8")
    reported_at = datetime.now(UTC)

    updated_record = record.model_copy(
        update={
            "completion_report_path": report_path,
            "reported_at": reported_at,
            "validation_summary": _extract_validation_summary(report_text),
            "commit_hash": _extract_commit_hash(report_text),
        }
    )
    run_state.implementation_records = [
        updated_record if existing.task_id == normalized_task_id else existing
        for existing in run_state.implementation_records
    ]
    run_state.status = RunStatus.IMPLEMENTATION_REPORTED
    run_state.updated_at = reported_at
    save_run_state(run_state, workspace_root=root)
    return updated_record


def get_implementation_status(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    record = find_implementation_record(run_state, normalized_task_id)
    if not record or not record.implementation_brief_path.exists():
        msg = f"Implementation brief not found for task: {normalized_task_id}"
        raise ValueError(msg)

    return {
        "project_name": project_name,
        "run_id": run_id,
        "task_id": normalized_task_id,
        "run_status": run_state.status.value,
        "implementation_brief_path": str(record.implementation_brief_path),
        "completion_report_path": str(record.completion_report_path) if record.completion_report_path else None,
        "reported_at": record.reported_at.isoformat() if record.reported_at else None,
        "validation_summary": record.validation_summary,
        "commit_hash": record.commit_hash,
    }


def get_validation_status(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    record = require_implementation_completion(run_state, normalized_task_id)

    return {
        "project_name": project_name,
        "run_id": run_id,
        "task_id": normalized_task_id,
        "run_status": run_state.status.value,
        "implementation_brief_path": str(record.implementation_brief_path),
        "completion_report_path": str(record.completion_report_path),
        "validation_report_path": str(record.validation_report_path) if record.validation_report_path else None,
        "validated_at": record.validated_at.isoformat() if record.validated_at else None,
        "validation_decision": record.validation_decision,
    }


def get_review_status(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    record = require_validation_review(run_state, normalized_task_id)

    return {
        "project_name": project_name,
        "run_id": run_id,
        "task_id": normalized_task_id,
        "run_status": run_state.status.value,
        "implementation_brief_path": str(record.implementation_brief_path),
        "completion_report_path": str(record.completion_report_path),
        "validation_report_path": str(record.validation_report_path),
        "code_review_path": str(record.code_review_path) if record.code_review_path else None,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "review_decision": record.review_decision,
    }


def get_audit_status(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    record = require_code_review(run_state, normalized_task_id)

    return {
        "project_name": project_name,
        "run_id": run_id,
        "task_id": normalized_task_id,
        "run_status": run_state.status.value,
        "implementation_brief_path": str(record.implementation_brief_path),
        "completion_report_path": str(record.completion_report_path),
        "validation_report_path": str(record.validation_report_path),
        "code_review_path": str(record.code_review_path),
        "final_audit_path": str(record.final_audit_path) if record.final_audit_path else None,
        "audited_at": record.audited_at.isoformat() if record.audited_at else None,
        "final_decision": record.final_decision,
    }


def close_task(
    project_name: str,
    run_id: str,
    task_id: str,
    note: str | None = None,
    workspace_root: Path | None = None,
) -> ImplementationRecord:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    require_run_status_at_least(
        run_state,
        RunStatus.FINAL_AUDITED,
        "Task closure requires final audit evidence before closing.",
    )
    record = require_final_audit(run_state, normalized_task_id)
    final_decision = record.final_decision
    closure_status = TASK_CLOSING_FINAL_DECISIONS.get(final_decision)
    if not closure_status:
        msg = f"Task cannot be closed with final decision: {final_decision}"
        raise ValueError(msg)

    closed_at = datetime.now(UTC)
    closure_record_path = record.implementation_brief_path.parent / CLOSURE_RECORD_ARTIFACT_NAME
    closure_record_path.write_text(
        _render_closure_record(record, closed_at=closed_at, closure_status=closure_status, note=note),
        encoding="utf-8",
    )
    updated_record = record.model_copy(
        update={
            "closure_record_path": closure_record_path,
            "closed_at": closed_at,
            "closure_status": closure_status,
            "closure_note": note,
        }
    )
    run_state.implementation_records = [
        updated_record if existing.task_id == normalized_task_id else existing
        for existing in run_state.implementation_records
    ]
    run_state.status = RunStatus.TASK_CLOSED
    run_state.updated_at = closed_at
    save_run_state(run_state, workspace_root=root)
    return updated_record


def mark_task_disposition(
    project_name: str,
    run_id: str,
    task_id: str,
    status: str,
    note: str | None = None,
    covered_by_task_id: str | None = None,
    workspace_root: Path | None = None,
) -> TaskLedgerEntry:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    tasks_by_id = _extract_tasks_from_artifact(run_state)
    _require_task_in_task_list(tasks_by_id, normalized_task_id)

    disposition_status = _parse_task_disposition_status(status)
    normalized_covered_by = covered_by_task_id.strip() if covered_by_task_id else None
    note_text = note.strip() if note else None

    if disposition_status == TaskDispositionStatus.COVERED_BY:
        if not normalized_covered_by:
            msg = "covered_by disposition requires --covered-by."
            raise ValueError(msg)
        _require_task_in_task_list(tasks_by_id, normalized_covered_by)
    elif normalized_covered_by:
        msg = "--covered-by can only be used with covered_by disposition."
        raise ValueError(msg)

    if disposition_status != TaskDispositionStatus.OPEN and not note_text:
        msg = f"{disposition_status.value} disposition requires --note."
        raise ValueError(msg)

    updated_at = datetime.now(UTC)
    entry = TaskLedgerEntry(
        task_id=normalized_task_id,
        disposition_status=disposition_status,
        covered_by_task_id=normalized_covered_by if disposition_status == TaskDispositionStatus.COVERED_BY else None,
        disposition_note=note_text,
        updated_at=updated_at,
    )
    ledger = load_task_ledger(run_state, workspace_root=root)
    ledger.entries[normalized_task_id] = entry
    ledger.updated_at = updated_at
    ledger_path = save_task_ledger(run_state, ledger, workspace_root=root)
    run_state.task_ledger_path = ledger_path
    run_state.updated_at = updated_at
    save_run_state(run_state, workspace_root=root)
    return entry


def get_task_status(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    normalized_task_id = require_task_id(task_id)
    tasks_by_id = _extract_tasks_from_artifact(run_state)
    task = _require_task_in_task_list(tasks_by_id, normalized_task_id)
    record = find_implementation_record(run_state, normalized_task_id)
    ledger_entry = load_task_ledger(run_state, workspace_root=root).entries.get(normalized_task_id)

    return {
        "project_name": project_name,
        "run_id": run_id,
        "task_id": normalized_task_id,
        "task_title": task["task_title"],
        "run_status": run_state.status.value,
        "closure_status": record.closure_status if record and record.closure_status else "open",
        "closure_record_path": str(record.closure_record_path) if record and record.closure_record_path else None,
        "closed_at": record.closed_at.isoformat() if record and record.closed_at else None,
        "closure_note": record.closure_note if record else None,
        "final_decision": record.final_decision if record else "unknown",
        "final_audit_path": str(record.final_audit_path) if record and record.final_audit_path else None,
        "disposition_status": ledger_entry.disposition_status.value if ledger_entry else TaskDispositionStatus.OPEN.value,
        "covered_by_task_id": ledger_entry.covered_by_task_id if ledger_entry else None,
        "disposition_note": ledger_entry.disposition_note if ledger_entry else None,
        "disposition_updated_at": ledger_entry.updated_at.isoformat() if ledger_entry else None,
    }


def list_run_tasks(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> list[dict[str, object]]:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    tasks_by_id = _extract_tasks_from_artifact(run_state)
    ledger = load_task_ledger(run_state, workspace_root=root)

    for record in run_state.implementation_records:
        task = tasks_by_id.setdefault(
            record.task_id,
            {
                "task_id": record.task_id,
                "task_title": "unknown",
            },
        )
        task.update(
            {
                "closure_status": record.closure_status or "open",
                "final_decision": record.final_decision,
                "closure_record_path": str(record.closure_record_path) if record.closure_record_path else None,
                "closed_at": record.closed_at.isoformat() if record.closed_at else None,
            }
        )

    for task_id, entry in ledger.entries.items():
        task = tasks_by_id.setdefault(task_id, {"task_id": task_id, "task_title": "unknown"})
        task.update(
            {
                "disposition_status": entry.disposition_status.value,
                "covered_by_task_id": entry.covered_by_task_id,
                "disposition_note": entry.disposition_note,
                "disposition_updated_at": entry.updated_at.isoformat(),
            }
        )

    for task in tasks_by_id.values():
        task.setdefault("closure_status", "open")
        task.setdefault("final_decision", "unknown")
        task.setdefault("closure_record_path", None)
        task.setdefault("closed_at", None)
        task.setdefault("disposition_status", TaskDispositionStatus.OPEN.value)
        task.setdefault("covered_by_task_id", None)
        task.setdefault("disposition_note", None)
        task.setdefault("disposition_updated_at", None)

    return [tasks_by_id[task_id] for task_id in sorted(tasks_by_id)]


def save_current_selection(
    project_name: str,
    run_id: str | None = None,
    workspace_root: Path | None = None,
) -> CurrentSelection:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    run_path = None
    if run_id:
        load_run(project_name, run_id, workspace_root=root)
        run_path = _run_dir(root, project_name, run_id)

    selection = CurrentSelection(
        project_name=project_name,
        project_path=registration.path,
        run_id=run_id,
        run_path=run_path,
    )
    current_file = root / "current.json"
    current_file.parent.mkdir(parents=True, exist_ok=True)
    current_file.write_text(selection.model_dump_json(indent=2), encoding="utf-8")
    return selection


def require_context_approved(project_name: str, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    state = load_context_state(project_name, workspace_root=root)
    if state.status != ContextStatus.CONTEXT_APPROVED:
        msg = "Project context must be approved before creating development runs."
        raise ValueError(msg)


def find_run_artifact(run_state: RunState, artifact_type: RunArtifactType) -> RunArtifact | None:
    for artifact in run_state.artifacts:
        if artifact.artifact_type == artifact_type:
            return artifact
    return None


def find_implementation_record(run_state: RunState, task_id: str) -> ImplementationRecord | None:
    for record in run_state.implementation_records:
        if record.task_id == task_id:
            return record
    return None


def require_run_artifact(run_state: RunState, artifact_type: RunArtifactType, message: str) -> RunArtifact:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact:
        raise ValueError(message)
    return artifact


def require_run_status_at_least(run_state: RunState, minimum_status: RunStatus, message: str) -> None:
    if RUN_STATUS_ORDER[run_state.status] < RUN_STATUS_ORDER[minimum_status]:
        raise ValueError(message)


def require_task_id(task_id: str | None) -> str:
    normalized = (task_id or "").strip()
    if not normalized:
        msg = "ImplementationCoordinatorAgent requires --task."
        raise ValueError(msg)
    return normalized


def require_task_excerpt(run_state: RunState, task_id: str) -> str:
    tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS)
    if not tasks_text:
        msg = "ImplementationCoordinatorAgent requires TaskDecomposerAgent output before implementation coordination."
        raise ValueError(msg)
    excerpt = extract_task_excerpt(tasks_text, task_id)
    if not excerpt:
        msg = f"Task id not found in tasks.md: {task_id}"
        raise ValueError(msg)
    return excerpt


def require_implementation_completion(run_state: RunState, task_id: str) -> ImplementationRecord:
    record = find_implementation_record(run_state, task_id)
    if not record or not record.implementation_brief_path.exists():
        msg = f"Implementation brief not found for task: {task_id}"
        raise ValueError(msg)
    if not record.completion_report_path or not record.completion_report_path.exists():
        msg = f"Completion report not found for task: {task_id}"
        raise ValueError(msg)
    return record


def require_validation_review(run_state: RunState, task_id: str) -> ImplementationRecord:
    record = require_implementation_completion(run_state, task_id)
    if not record.validation_report_path or not record.validation_report_path.exists():
        msg = f"Validation report not found for task: {task_id}"
        raise ValueError(msg)
    return record


def require_code_review(run_state: RunState, task_id: str) -> ImplementationRecord:
    record = require_validation_review(run_state, task_id)
    if not record.code_review_path or not record.code_review_path.exists():
        msg = f"Code review report not found for task: {task_id}"
        raise ValueError(msg)
    return record


def require_final_audit(run_state: RunState, task_id: str) -> ImplementationRecord:
    record = require_code_review(run_state, task_id)
    if not record.final_audit_path or not record.final_audit_path.exists():
        msg = f"Final audit report not found for task: {task_id}"
        raise ValueError(msg)
    return record


def extract_task_excerpt(tasks_text: str, task_id: str) -> str | None:
    pattern = re.compile(
        rf"(?ims)^##\s+Task\s+{re.escape(task_id)}\b.*?(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)"
    )
    match = pattern.search(tasks_text)
    if match:
        return match.group(0).strip()

    fallback = re.compile(
        rf"(?ims)^.*(?:task id:\s*`?{re.escape(task_id)}`?).*?(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)"
    )
    match = fallback.search(tasks_text)
    if match:
        return match.group(0).strip()
    return None


def get_run_artifact_text(run_state: RunState, artifact_type: RunArtifactType, max_chars: int = 20_000) -> str | None:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact or not artifact.artifact_path.exists():
        return None
    return artifact.artifact_path.read_text(encoding="utf-8")[:max_chars]


def get_run_artifacts_summary(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> dict[str, object]:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    directory = _run_dir(root, project_name, run_id)
    return {
        "goal_path": str(directory / "goal.md"),
        "run_state_path": str(directory / "run-state.json"),
        "idea_analysis_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.IDEA_ANALYSIS),
        "requirements_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.REQUIREMENTS),
        "plan_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.PLAN),
        "plan_review_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.PLAN_REVIEW),
        "tasks_artifact_path": _artifact_path_or_none(run_state, RunArtifactType.TASKS),
        "task_ledger_path": str(_task_ledger_path(root, project_name, run_id)) if _task_ledger_path(root, project_name, run_id).exists() else None,
        "implementation_artifact_paths": [
            {
                "task_id": record.task_id,
                "implementation_brief_path": str(record.implementation_brief_path),
                "completion_report_path": str(record.completion_report_path) if record.completion_report_path else None,
                "validation_report_path": str(record.validation_report_path) if record.validation_report_path else None,
                "code_review_path": str(record.code_review_path) if record.code_review_path else None,
                "final_audit_path": str(record.final_audit_path) if record.final_audit_path else None,
                "closure_record_path": str(record.closure_record_path) if record.closure_record_path else None,
            }
            for record in run_state.implementation_records
        ],
        "prompt_paths": [str(path) for path in sorted((directory / "prompts").glob("*.md"))],
    }


def run_path(project_name: str, run_id: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return _run_dir(root, project_name, run_id)


def _build_context_snapshot(workspace_root: Path, project_name: str) -> ContextSnapshot:
    context_root = workspace_root / "projects" / project_name / "context"
    approval_file = workspace_root / "projects" / project_name / "approvals" / APPROVAL_RECORD_NAME
    if not approval_file.exists():
        msg = "Project context must be approved before creating development runs."
        raise ValueError(msg)

    approval_data = json.loads(approval_file.read_text(encoding="utf-8"))
    approved_artifact_paths = [Path(path) for path in approval_data.get("approved_artifact_paths", [])]
    return ContextSnapshot(
        context_state_path=context_root / CONTEXT_STATE_NAME,
        approval_record_path=approval_file,
        approved_artifact_paths=approved_artifact_paths,
    )


def _artifact_path_or_none(run_state: RunState, artifact_type: RunArtifactType) -> str | None:
    artifact = find_run_artifact(run_state, artifact_type)
    if not artifact:
        return None
    return str(artifact.artifact_path)


def _render_goal_markdown(run_state: RunState) -> str:
    return "\n".join(
        [
            f"# {run_state.run_id}",
            "",
            f"- Project: {run_state.project_name}",
            f"- Run ID: {run_state.run_id}",
            f"- Created at: {run_state.created_at.isoformat()}",
            f"- Initial status: {run_state.status.value}",
            "",
            "## Goal",
            "",
            run_state.goal,
            "",
        ]
    )


def _render_closure_record(
    record: ImplementationRecord,
    closed_at: datetime,
    closure_status: str,
    note: str | None,
) -> str:
    lines = [
        "# closure-record.md",
        "",
        f"- task id: {record.task_id}",
        f"- closed_at: {closed_at.isoformat()}",
        f"- final decision: {record.final_decision}",
        f"- closure status: {closure_status}",
    ]
    if note:
        lines.append(f"- note: {note}")
    lines.extend(
        [
            "",
            "## References",
            "",
            f"- implementation brief: {record.implementation_brief_path}",
            f"- completion report: {record.completion_report_path}",
            f"- validation report: {record.validation_report_path}",
            f"- code review: {record.code_review_path}",
            f"- final audit: {record.final_audit_path}",
            "",
        ]
    )
    return "\n".join(lines)


def _unique_run_id(workspace_root: Path, project_name: str, goal: str, created_at: datetime) -> str:
    base = f"{created_at:%Y-%m-%d-%H%M%S}-{_slugify(goal)}"
    candidate = base
    suffix = 2
    while _run_dir(workspace_root, project_name, candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug[:60] or "run"


def _run_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return workspace_root / "runs" / project_name / run_id


def _implementation_artifact_dir(workspace_root: Path, project_name: str, run_id: str, task_id: str) -> Path:
    return _run_dir(workspace_root, project_name, run_id) / "artifacts" / "implementation" / task_id


def load_task_ledger(run_state: RunState, workspace_root: Path | None = None) -> TaskLedger:
    root = workspace_root or get_workspace_root()
    ledger_path = _task_ledger_path(root, run_state.project_name, run_state.run_id)
    if not ledger_path.exists():
        return TaskLedger(project_name=run_state.project_name, run_id=run_state.run_id)
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    return TaskLedger.model_validate(data)


def save_task_ledger(run_state: RunState, ledger: TaskLedger, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    ledger_path = _task_ledger_path(root, run_state.project_name, run_state.run_id)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    return ledger_path


def _parse_task_disposition_status(status: str) -> TaskDispositionStatus:
    try:
        return TaskDispositionStatus(status)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in TaskDispositionStatus)
        msg = f"Invalid task disposition status: {status}. Allowed: {allowed}"
        raise ValueError(msg) from exc


def _require_task_in_task_list(tasks_by_id: dict[str, dict[str, object]], task_id: str) -> dict[str, object]:
    task = tasks_by_id.get(task_id)
    if not task:
        msg = f"Task id not found in tasks.md: {task_id}"
        raise ValueError(msg)
    return task


def _task_ledger_path(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return _run_dir(workspace_root, project_name, run_id) / "artifacts" / TASK_LEDGER_ARTIFACT_NAME


def _extract_tasks_from_artifact(run_state: RunState) -> dict[str, dict[str, object]]:
    tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS) or ""
    tasks: dict[str, dict[str, object]] = {}
    pattern = re.compile(r"(?ims)^##\s+Task\s+(\S+)\b(.*?)(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)")
    for match in pattern.finditer(tasks_text):
        task_id = match.group(1).strip("`")
        body = match.group(2)
        title_match = re.search(r"(?im)^\s*-\s*task title:\s*(.+)$", body)
        tasks[task_id] = {
            "task_id": task_id,
            "task_title": title_match.group(1).strip().strip("`") if title_match else "unknown",
        }

    fallback = re.compile(r"(?im)^\s*-\s*task id:\s*`?([A-Za-z0-9_.-]+)`?")
    for match in fallback.finditer(tasks_text):
        task_id = match.group(1)
        tasks.setdefault(task_id, {"task_id": task_id, "task_title": "unknown"})
    return tasks


def _extract_validation_summary(report_text: str) -> str:
    patterns = (
        r"(?im)^\s*(?:[-*]\s*)?(?:validation result|test results)\s*:\s*(.+)$",
        r"(?ims)^#+\s*(?:validation|test results)\s*\n+(.+?)(?=^#+\s|\Z)",
    )
    for pattern in patterns:
        match = re.search(pattern, report_text)
        if match:
            summary = " ".join(match.group(1).strip().split())
            return summary[:500] or "unknown"
    return "unknown"


def _extract_commit_hash(report_text: str) -> str:
    explicit = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:git commit hash|commit hash|commit)\s*:\s*`?([0-9a-f]{7,40})`?\s*$", report_text)
    if explicit:
        return explicit.group(1)
    any_hash = re.search(r"\b[0-9a-f]{40}\b", report_text, flags=re.IGNORECASE)
    if any_hash:
        return any_hash.group(0)
    return "unknown"


def _extract_validation_decision(report_text: str) -> str:
    allowed = ("passed_with_notes", "needs_more_evidence", "passed", "failed")
    section = re.search(r"(?ims)^#+\s*validation-decision\.md\s*\n+(.+?)(?=^#+\s|\Z)", report_text)
    candidates = [section.group(1)] if section else []
    inline = re.search(r"(?im)^\s*(?:[-*]\s*)?validation decision\s*:\s*(.+)$", report_text)
    if inline:
        candidates.append(inline.group(1))
    candidates.append(report_text)

    for candidate in candidates:
        normalized = candidate.strip().lower()
        for decision in allowed:
            if re.search(rf"\b{re.escape(decision)}\b", normalized):
                return decision
    return "unknown"


def _extract_review_decision(review_text: str) -> str:
    allowed = ("approve_with_notes", "changes_requested", "approve", "blocked")
    section = re.search(r"(?ims)^#+\s*review-decision\.md\s*\n+(.+?)(?=^#+\s|\Z)", review_text)
    candidates = [section.group(1)] if section else []
    inline = re.search(r"(?im)^\s*(?:[-*]\s*)?review decision\s*:\s*(.+)$", review_text)
    if inline:
        candidates.append(inline.group(1))
    candidates.append(review_text)

    for candidate in candidates:
        normalized = candidate.strip().lower()
        for decision in allowed:
            if re.search(rf"\b{re.escape(decision)}\b", normalized):
                return decision
    return "unknown"


def _extract_final_decision(audit_text: str) -> str:
    allowed = ("close_with_notes", "needs_follow_up", "close_task", "blocked")
    section = re.search(r"(?ims)^#+\s*final-decision\.md\s*\n+(.+?)(?=^#+\s|\Z)", audit_text)
    candidates = [section.group(1)] if section else []
    inline = re.search(r"(?im)^\s*(?:[-*]\s*)?final decision\s*:\s*(.+)$", audit_text)
    if inline:
        candidates.append(inline.group(1))
    candidates.append(audit_text)

    for candidate in candidates:
        normalized = candidate.strip().lower()
        for decision in allowed:
            if re.search(rf"\b{re.escape(decision)}\b", normalized):
                return decision
    return "unknown"
