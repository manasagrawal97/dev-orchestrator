from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .projects import get_workspace_root
from .runs import (
    IMPLEMENTATION_COORDINATOR_AGENT_NAME,
    find_run_artifact,
    get_run_artifact_text,
    list_run_tasks,
    load_run,
)
from .schemas import RunArtifactType, TaskDispositionStatus

DEFAULT_STRATEGY = "first-open-safe"
VALID_STRATEGIES = {"first-open-safe", "first-open", "safest", "priority"}

RESOLVED_DISPOSITIONS = {
    TaskDispositionStatus.COVERED_BY.value,
    TaskDispositionStatus.SUPERSEDED.value,
    TaskDispositionStatus.NOT_NEEDED.value,
    TaskDispositionStatus.CLOSED_MANUALLY.value,
}
CLOSED_STATUSES = {"closed", "closed_with_notes"}
KNOWN_CLOSURE_STATUSES = {"open", *CLOSED_STATUSES}
KNOWN_DISPOSITION_STATUSES = {status.value for status in TaskDispositionStatus}
RISK_ORDER = {"safe": 0, "low": 0, "medium": 1, "high": 2}


@dataclass
class TaskCandidate:
    task_id: str
    title: str
    closure_status: str
    disposition_status: str
    priority: str | None = None
    risk: str | None = None
    safety: str | None = None
    blocked: bool = False
    source_artifact: str | None = None
    original_order: int = 0
    selection_status: str = "selectable"
    skip_reason: str | None = None
    selection_rank: int | None = None
    covered_by_task_id: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskSelection:
    project_name: str
    run_id: str
    strategy: str
    source_artifact: str | None
    selected: TaskCandidate | None
    candidates: list[TaskCandidate]
    skipped: list[TaskCandidate]
    reason: str
    suggested_command: str | None = None
    all_resolved: bool = False
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def select_next_task(
    project_name: str,
    run_id: str,
    strategy: str = DEFAULT_STRATEGY,
    workspace_root: Path | None = None,
) -> TaskSelection:
    selection = list_task_candidates(
        project_name=project_name,
        run_id=run_id,
        strategy=strategy,
        workspace_root=workspace_root,
    )
    selectable = [candidate for candidate in selection.candidates if candidate.selection_status == "selectable"]
    ranked = _rank_selectable(selectable, selection.strategy)
    for rank, candidate in enumerate(ranked, start=1):
        candidate.selection_rank = rank
    selected = ranked[0] if ranked else None
    reason = _selection_reason(selected, selection)
    suggested_command = (
        f"devo agent prompt {IMPLEMENTATION_COORDINATOR_AGENT_NAME} "
        f"--project {project_name} --run {run_id} --task {selected.task_id}"
        if selected
        else None
    )
    return TaskSelection(
        project_name=selection.project_name,
        run_id=selection.run_id,
        strategy=selection.strategy,
        source_artifact=selection.source_artifact,
        selected=selected,
        candidates=selection.candidates,
        skipped=selection.skipped,
        reason=reason,
        suggested_command=suggested_command,
        all_resolved=selection.all_resolved,
        warnings=selection.warnings,
        blockers=selection.blockers,
    )


def list_task_candidates(
    project_name: str,
    run_id: str,
    strategy: str = DEFAULT_STRATEGY,
    workspace_root: Path | None = None,
) -> TaskSelection:
    normalized_strategy = _normalize_strategy(strategy)
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    tasks_artifact = find_run_artifact(run_state, RunArtifactType.TASKS)
    source_artifact = str(tasks_artifact.artifact_path) if tasks_artifact else None
    warnings: list[str] = []
    blockers: list[str] = []

    if not tasks_artifact or not tasks_artifact.artifact_path.exists():
        warnings.append("tasks.md artifact is missing; task selection cannot continue.")
        return TaskSelection(
            project_name=project_name,
            run_id=run_id,
            strategy=normalized_strategy,
            source_artifact=source_artifact,
            selected=None,
            candidates=[],
            skipped=[],
            reason="No task artifact is available.",
            warnings=warnings,
            blockers=warnings.copy(),
        )

    tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS) or ""
    task_metadata = _extract_task_metadata(tasks_text)
    tasks = list_run_tasks(project_name, run_id, workspace_root=root)
    candidates = [
        _candidate_from_task(task, task_metadata, source_artifact, index, warnings)
        for index, task in enumerate(tasks, start=1)
    ]
    candidates.sort(key=lambda item: item.original_order)
    skipped = [candidate for candidate in candidates if candidate.selection_status != "selectable"]
    selectable = [candidate for candidate in candidates if candidate.selection_status == "selectable"]
    ranked = _rank_selectable(selectable, normalized_strategy)
    for rank, candidate in enumerate(ranked, start=1):
        candidate.selection_rank = rank

    all_resolved = bool(candidates) and not selectable and all(
        candidate.selection_status == "skipped_resolved" for candidate in skipped
    )
    reason = "Task candidates loaded."
    if not candidates:
        reason = "No tasks were found in tasks.md."
    elif not selectable and all_resolved:
        reason = "No actionable tasks remain; all tasks appear resolved and the run may be ready for closure."
    elif not selectable:
        reason = "No actionable tasks remain after conservative filtering."

    return TaskSelection(
        project_name=project_name,
        run_id=run_id,
        strategy=normalized_strategy,
        source_artifact=source_artifact,
        selected=ranked[0] if ranked else None,
        candidates=candidates,
        skipped=skipped,
        reason=reason,
        suggested_command=(
            f"devo agent prompt {IMPLEMENTATION_COORDINATOR_AGENT_NAME} "
            f"--project {project_name} --run {run_id} --task {ranked[0].task_id}"
            if ranked
            else None
        ),
        all_resolved=all_resolved,
        warnings=_dedupe(warnings),
        blockers=blockers,
    )


def _candidate_from_task(
    task: dict[str, object],
    task_metadata: dict[str, dict[str, str | int | bool | None]],
    source_artifact: str | None,
    fallback_order: int,
    warnings: list[str],
) -> TaskCandidate:
    task_id = str(task.get("task_id") or "").strip()
    metadata = task_metadata.get(task_id, {})
    closure_status = str(task.get("closure_status") or "open")
    disposition_status = str(task.get("disposition_status") or TaskDispositionStatus.OPEN.value)
    risk = _normalize_risk(metadata.get("risk"))
    safety = _clean_optional(metadata.get("safety"))
    priority = _clean_optional(metadata.get("priority"))
    candidate = TaskCandidate(
        task_id=task_id,
        title=str(task.get("task_title") or metadata.get("title") or "unknown"),
        closure_status=closure_status,
        disposition_status=disposition_status,
        priority=priority,
        risk=risk,
        safety=safety,
        blocked=bool(metadata.get("blocked")),
        source_artifact=source_artifact,
        original_order=int(metadata.get("order") or fallback_order),
        covered_by_task_id=_clean_optional(task.get("covered_by_task_id")),
    )

    if closure_status not in KNOWN_CLOSURE_STATUSES:
        candidate.selection_status = "skipped_unknown_status"
        candidate.skip_reason = f"unknown closure status: {closure_status}"
        warning = f"Task {task_id} has unknown closure status: {closure_status}"
        candidate.warnings.append(warning)
        warnings.append(warning)
    elif disposition_status not in KNOWN_DISPOSITION_STATUSES:
        candidate.selection_status = "skipped_unknown_status"
        candidate.skip_reason = f"unknown disposition status: {disposition_status}"
        warning = f"Task {task_id} has unknown disposition status: {disposition_status}"
        candidate.warnings.append(warning)
        warnings.append(warning)
    elif _has_formal_closure(task):
        candidate.selection_status = "skipped_resolved"
        candidate.skip_reason = f"formal closure status is {closure_status}"
    elif disposition_status in RESOLVED_DISPOSITIONS:
        candidate.selection_status = "skipped_resolved"
        detail = f" by {candidate.covered_by_task_id}" if candidate.covered_by_task_id else ""
        candidate.skip_reason = f"disposition is {disposition_status}{detail}"
    elif candidate.blocked:
        candidate.selection_status = "skipped_blocked"
        candidate.skip_reason = "task is marked blocked in tasks.md"
    return candidate


def _extract_task_metadata(tasks_text: str) -> dict[str, dict[str, str | int | bool | None]]:
    metadata: dict[str, dict[str, str | int | bool | None]] = {}
    pattern = re.compile(r"(?ims)^##\s+Task\s+(\S+)\b(.*?)(?=^##\s+Task\s+\S+\b|^---\s*$|\Z)")
    for order, match in enumerate(pattern.finditer(tasks_text), start=1):
        task_id = match.group(1).strip("`")
        body = match.group(2)
        metadata[task_id] = {
            "order": order,
            "title": _extract_field(body, "task title", "title"),
            "risk": _extract_field(body, "risk level", "risk"),
            "priority": _extract_field(body, "priority"),
            "safety": _extract_field(body, "safety", "safety level"),
            "blocked": _is_blocked(body),
        }

    fallback = re.compile(r"(?im)^\s*-\s*task id:\s*`?([A-Za-z0-9_.-]+)`?")
    next_order = len(metadata) + 1
    for match in fallback.finditer(tasks_text):
        task_id = match.group(1)
        if task_id not in metadata:
            metadata[task_id] = {"order": next_order, "blocked": False}
            next_order += 1
    return metadata


def _extract_field(body: str, *names: str) -> str | None:
    for name in names:
        pattern = re.compile(
            rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?{re.escape(name)}(?:\*\*)?\s*:\s*(.+?)\s*$"
        )
        match = pattern.search(body)
        if match:
            return match.group(1).strip().strip("`")
    return None


def _is_blocked(body: str) -> bool:
    blocked_value = _extract_field(body, "blocked")
    if blocked_value and blocked_value.strip().lower() in {"yes", "true", "blocked"}:
        return True
    blockers = _extract_field(body, "blocker", "blockers")
    if not blockers:
        return False
    return blockers.strip().lower() not in {"none", "no", "n/a", "not blocked"}


def _rank_selectable(candidates: list[TaskCandidate], strategy: str) -> list[TaskCandidate]:
    if strategy == "first-open":
        return sorted(candidates, key=lambda item: item.original_order)
    if strategy == "priority":
        return sorted(candidates, key=lambda item: (_priority_rank(item.priority), _risk_rank(item), item.original_order))
    return sorted(candidates, key=lambda item: (_risk_rank(item), item.original_order))


def _priority_rank(priority: str | None) -> tuple[int, str]:
    if not priority:
        return (10_000, "")
    number = re.search(r"\d+", priority)
    if number:
        return (int(number.group(0)), priority)
    normalized = priority.lower()
    ranks = {"high": 0, "medium": 1, "low": 2}
    return (ranks.get(normalized, 10_000), priority)


def _risk_rank(candidate: TaskCandidate) -> int:
    if candidate.risk in RISK_ORDER:
        return RISK_ORDER[candidate.risk]
    if candidate.safety and candidate.safety.lower() in {"safe", "low", "low-risk"}:
        return 0
    return 1


def _normalize_risk(value: object | None) -> str | None:
    cleaned = _clean_optional(value)
    if not cleaned:
        return None
    lowered = cleaned.lower()
    for risk in ("safe", "low", "medium", "high"):
        if re.search(rf"\b{risk}\b", lowered):
            return risk
    return cleaned


def _clean_optional(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_formal_closure(task: dict[str, object]) -> bool:
    return task.get("closure_status") in CLOSED_STATUSES and bool(task.get("closure_record_path"))


def _normalize_strategy(strategy: str) -> str:
    normalized = strategy.strip().lower()
    if normalized not in VALID_STRATEGIES:
        allowed = ", ".join(sorted(VALID_STRATEGIES))
        msg = f"Invalid task selection strategy: {strategy}. Allowed: {allowed}"
        raise ValueError(msg)
    return normalized


def _selection_reason(selected: TaskCandidate | None, selection: TaskSelection) -> str:
    if selected:
        return f"Selected {selected.task_id} using {selection.strategy} from {selection.source_artifact or 'tasks.md'}."
    return selection.reason


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
