from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from pydantic import ValidationError

from .approvals import get_approval_status
from .context_updates import get_project_context_summary, list_context_updates, sanitize_summary_items
from .git_delivery import get_git_repository_status
from .projects import get_workspace_root
from .runs import list_run_tasks, list_runs, load_run, run_path
from .scanner import load_registered_project
from .policy import get_policy_status
from .task_selector import select_next_task
from .validation_runner import list_validation_history
from .workflow import get_workflow_status

REPORTS_DIR = "reports"
REPORT_SCHEMA_VERSION = "1"
MAX_RECENT = 5


def build_project_report(project_name: str, limit: int = MAX_RECENT, workspace_root: Path | None = None) -> dict[str, Any]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    warnings: list[str] = []
    context_summary = _safe_context_summary(project_name, root, warnings, limit)
    git_summary = _safe_git_summary(project_name, root, warnings)
    runs = list_runs(project_name, workspace_root=root)[-limit:]
    validation_runs = _validation_lines(project_name, root, limit=limit)
    approvals = _project_approval_lines(project_name, root, limit=limit)
    context_updates = _context_update_lines(project_name, root, limit=limit)
    git_delivery = _git_delivery_lines(root, project_name, None, limit=limit)
    suggested_actions = _project_suggested_actions(project_name, context_summary, runs)
    return _sanitize_report(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "project",
            "project_name": project_name,
            "project_path": str(registration.path),
            "created_at": datetime.now(UTC).isoformat(),
            "git_repo_summary": git_summary,
            "context_summary": context_summary,
            "validation_run_summary": validation_runs,
            "approval_summary": approvals,
            "recent_context_updates": context_updates,
            "recent_git_delivery_reports": git_delivery,
            "recent_runs": [_run_line(run) for run in runs],
            "warnings": _dedupe([*warnings, *list(context_summary.get("warnings", []))]),
            "suggested_next_actions": suggested_actions,
        }
    )


def build_run_report(project_name: str, run_id: str, limit: int = MAX_RECENT, workspace_root: Path | None = None) -> dict[str, Any]:
    root = workspace_root or get_workspace_root()
    run_state = load_run(project_name, run_id, workspace_root=root)
    warnings: list[str] = []
    workflow = _safe_workflow(project_name, run_id, root, warnings)
    tasks = _safe_tasks(project_name, run_id, root, warnings)
    next_task = _safe_next_task(project_name, run_id, root, warnings)
    policy = _safe_policy(project_name, run_id, root, warnings)
    approvals = _run_approval_lines(project_name, run_id, root, limit=limit)
    validation = _validation_lines(project_name, root, run_id=run_id, limit=limit)
    git_delivery = _git_delivery_lines(root, project_name, run_id, limit=limit)
    context_updates = _context_update_lines(project_name, root, run_id=run_id, limit=limit)
    unresolved = [task for task in tasks if not _task_resolved(task)]
    resolved = [task for task in tasks if _task_resolved(task)]
    return _sanitize_report(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "run",
            "project_name": project_name,
            "project_path": str(run_state.project_path),
            "run_id": run_id,
            "run_goal": run_state.goal,
            "run_status": run_state.status.value,
            "created_at": datetime.now(UTC).isoformat(),
            "workflow_next": workflow,
            "task_candidate_summary": next_task,
            "task_summary": _task_summary(tasks),
            "policy_summary": policy,
            "approval_summary": approvals,
            "validation_evidence_summary": validation,
            "git_delivery_evidence_summary": git_delivery,
            "context_update_summary": context_updates,
            "unresolved_tasks": [_task_line(task) for task in unresolved],
            "resolved_tasks": [_task_line(task) for task in resolved],
            "warnings": _dedupe(warnings),
            "blockers": _blockers_from_workflow(workflow),
            "suggested_next_actions": _run_suggested_actions(project_name, run_id, workflow, unresolved),
        }
    )


def build_handoff_report(
    project_name: str,
    run_id: str | None = None,
    limit: int = MAX_RECENT,
    workspace_root: Path | None = None,
) -> dict[str, Any]:
    root = workspace_root or get_workspace_root()
    project_report = build_project_report(project_name, limit=limit, workspace_root=root)
    run_report = build_run_report(project_name, run_id, limit=limit, workspace_root=root) if run_id else None
    latest_run = _latest_run_line(project_name, root)
    next_action = None
    if run_report:
        next_action = run_report.get("suggested_next_actions", [None])[0]
    else:
        actions = project_report.get("suggested_next_actions", [])
        next_action = actions[0] if actions else None
    return _sanitize_report(
        {
            "schema_version": REPORT_SCHEMA_VERSION,
            "report_type": "handoff",
            "project_name": project_name,
            "project_path": project_report.get("project_path"),
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "current_state": run_report or project_report,
            "last_completed_task_or_run": latest_run,
            "next_planned_task_or_action": next_action or "Inspect project report and workflow status.",
            "safety_constraints": [
                "Do not modify registered target projects unless an explicit implementation task is approved.",
                "Do not execute target build/test/restore commands from report generation.",
                "Do not call AI or fabricate agent outputs inside Devo commands.",
                "Do not expose credentials or local settings values; local-sensitive artifacts are classified only.",
                "Do not bypass Codex/OpenAI/OS/GitHub security policy.",
            ],
            "commands_to_inspect_state": _handoff_commands(project_name, run_id),
            "key_docs_to_read": [
                "README.md",
                "docs/current-state.md",
                "docs/roadmap.md",
                "docs/deferred-scope.md",
                "docs/recovery.md",
            ],
            "what_not_to_do": [
                "Do not stage workspace/, .venv/, .env, caches, backup folders, or target project files accidentally.",
                "Do not push via Devo; use Git delivery reports for explicit human guidance.",
                "Do not treat context update drafts as approved baseline context until reviewed/applied.",
            ],
            "known_deferred_scope": _deferred_scope_summary(),
            "warnings": project_report.get("warnings", []),
        }
    )


def write_report_artifacts(
    report: dict[str, Any],
    project_name: str,
    run_id: str | None = None,
    workspace_root: Path | None = None,
) -> tuple[Path, Path]:
    root = workspace_root or get_workspace_root()
    report_type = str(report["report_type"])
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    if report_type == "run":
        output_dir = run_path(project_name, str(run_id), workspace_root=root) / "artifacts" / REPORTS_DIR
        stem = f"run-report-{timestamp}"
    elif report_type == "handoff":
        output_dir = root / "projects" / project_name / REPORTS_DIR
        stem = f"handoff-report-{timestamp}"
    else:
        output_dir = root / "projects" / project_name / REPORTS_DIR
        stem = f"project-report-{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}.md"
    json_path = output_dir / f"{stem}.json"
    report_with_paths = {**report, "markdown_path": str(md_path), "json_path": str(json_path)}
    json_path.write_text(json.dumps(report_with_paths, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_report_markdown(report_with_paths), encoding="utf-8")
    return md_path, json_path


def render_report_markdown(report: dict[str, Any]) -> str:
    title = {
        "project": "Project Report",
        "run": "Run Report",
        "handoff": "Handoff Report",
    }.get(str(report.get("report_type")), "Report")
    lines = [f"# {title}", ""]
    for key, value in report.items():
        if key in {"schema_version", "markdown_path", "json_path"}:
            continue
        lines.extend(_render_value(key, value, 0))
    return "\n".join(lines).rstrip() + "\n"


def _safe_context_summary(project_name: str, root: Path, warnings: list[str], limit: int) -> dict[str, Any]:
    try:
        return _limit_context_summary(get_project_context_summary(project_name, workspace_root=root), limit)
    except ValueError as exc:
        warnings.append(f"Context summary unavailable: {exc}")
        return {}


def _limit_context_summary(summary: dict[str, Any], limit: int) -> dict[str, Any]:
    bounded = dict(summary)
    for key in ("approved_context_paths", "recent_runs", "latest_run_statuses", "warnings"):
        value = bounded.get(key)
        if isinstance(value, list):
            bounded[key] = value[-limit:]
    for key in ("validation_registry", "environment_snapshot"):
        value = bounded.get(key)
        if isinstance(value, list):
            bounded[key] = value[:limit]
    scan = bounded.get("last_scan_result")
    if isinstance(scan, dict):
        bounded["last_scan_result"] = {
            item_key: item_value[-limit:] if isinstance(item_value, list) else item_value
            for item_key, item_value in scan.items()
        }
    return bounded


def _safe_git_summary(project_name: str, root: Path, warnings: list[str]) -> list[str]:
    try:
        status = get_git_repository_status(project_name, workspace_root=root)
    except ValueError as exc:
        warnings.append(f"Git status unavailable: {exc}")
        return []
    return [
        f"branch={status.current_branch or 'unknown'}",
        f"head={status.head_commit or 'unknown'}",
        f"upstream={status.upstream_branch or 'none'}",
        f"ahead={status.ahead if status.ahead is not None else 'unknown'}",
        f"behind={status.behind if status.behind is not None else 'unknown'}",
        f"clean={status.working_tree_clean}",
    ]


def _safe_workflow(project_name: str, run_id: str, root: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        status = get_workflow_status(project_name, run_id, workspace_root=root)
    except ValueError as exc:
        warnings.append(f"Workflow status unavailable: {exc}")
        return {}
    action = status.next_action
    return {
        "run_status": status.run_status,
        "lifecycle_stage": status.lifecycle_stage,
        "can_close_run": status.can_close_run,
        "next_action_type": action.action_type,
        "next_action_reason": action.reason,
        "next_action_command": action.command_to_run,
        "next_action_task": action.task_id,
        "warnings": [*status.warnings, *action.warnings],
        "blockers": action.blockers,
    }


def _safe_tasks(project_name: str, run_id: str, root: Path, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        return list_run_tasks(project_name, run_id, workspace_root=root)
    except ValueError as exc:
        warnings.append(f"Task summary unavailable: {exc}")
        return []


def _safe_next_task(project_name: str, run_id: str, root: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        selection = select_next_task(project_name, run_id, workspace_root=root)
    except ValueError as exc:
        warnings.append(f"Task selection unavailable: {exc}")
        return {}
    selected = selection.selected
    return {
        "strategy": selection.strategy,
        "selected_task": f"{selected.task_id}: {selected.title}" if selected else None,
        "reason": selection.reason,
        "all_resolved": selection.all_resolved,
        "warnings": selection.warnings,
        "blockers": selection.blockers,
    }


def _safe_policy(project_name: str, run_id: str, root: Path, warnings: list[str]) -> list[str]:
    try:
        status = get_policy_status(project_name, run_id, workspace_root=root)
    except ValueError as exc:
        warnings.append(f"Policy summary unavailable: {exc}")
        return []
    return [
        f"{task.task_id}: risk={task.risk_level}, approval_required={task.approval_required}, blocked={task.blocked}, disposition={task.disposition_status}, closure={task.closure_status}"
        for task in status.tasks
    ]


def _validation_lines(project_name: str, root: Path, run_id: str | None = None, limit: int = MAX_RECENT) -> list[str]:
    try:
        records = list_validation_history(project_name, workspace_root=root)
    except (ValueError, OSError, ValidationError):
        return []
    if run_id:
        records = [record for record in records if record.run_id == run_id]
    return [
        f"{record.validation_run_id}: run={record.run_id or 'none'}, task={record.task_id or 'none'}, command={record.command_id}, status={record.status.value}, exit={record.exit_code if record.exit_code is not None else 'none'}"
        for record in records[-limit:]
    ]


def _project_approval_lines(project_name: str, root: Path, limit: int = MAX_RECENT) -> list[str]:
    lines: list[str] = []
    for run in list_runs(project_name, workspace_root=root)[-limit:]:
        lines.extend(_run_approval_lines(project_name, run.run_id, root, limit=limit))
    return lines[-limit:]


def _run_approval_lines(project_name: str, run_id: str, root: Path, limit: int = MAX_RECENT) -> list[str]:
    try:
        approvals = get_approval_status(project_name, run_id, workspace_root=root)
    except ValueError:
        return []
    return [
        f"{approval.approval_id}: task={approval.task_id}, action={approval.action_type}, status={approval.status.value}, risk={approval.risk_level}"
        for approval in approvals[-limit:]
    ]


def _context_update_lines(project_name: str, root: Path, run_id: str | None = None, limit: int = MAX_RECENT) -> list[str]:
    try:
        ledger = list_context_updates(project_name, workspace_root=root)
    except ValueError:
        return []
    updates = ledger.updates
    if run_id:
        updates = [update for update in updates if update.source_run_id == run_id]
    return [
        f"{update.update_id}: status={update.status.value}, source_run={update.source_run_id or 'none'}, warnings={len(update.warnings)}"
        for update in updates[-limit:]
    ]


def _git_delivery_lines(root: Path, project_name: str, run_id: str | None, limit: int = MAX_RECENT) -> list[str]:
    paths: list[Path] = []
    if run_id:
        paths.extend(sorted((run_path(project_name, run_id, workspace_root=root) / "artifacts" / "git-delivery").glob("git-delivery-report-*.json")))
    else:
        paths.extend(sorted((root / "projects" / project_name / "git-delivery").glob("git-delivery-report-*.json")))
        for run in list_runs(project_name, workspace_root=root)[-limit:]:
            paths.extend(sorted((run_path(project_name, run.run_id, workspace_root=root) / "artifacts" / "git-delivery").glob("git-delivery-report-*.json")))
    lines: list[str] = []
    for path in paths[-limit:]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            lines.append(f"{path.name}: invalid json")
            continue
        check = data.get("delivery_check", {}) if isinstance(data, dict) else {}
        status = check.get("status", {}) if isinstance(check, dict) else {}
        lines.append(
            f"{path.name}: readiness={check.get('readiness', 'unknown')}, branch={status.get('current_branch', 'unknown')}, ahead={status.get('ahead', 'unknown')}, behind={status.get('behind', 'unknown')}"
        )
    return lines


def _task_summary(tasks: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"total": len(tasks), "resolved": 0, "unresolved": 0, "closed": 0, "dispositioned": 0}
    for task in tasks:
        if _task_resolved(task):
            summary["resolved"] += 1
        else:
            summary["unresolved"] += 1
        if task.get("closure_status") not in {None, "open"}:
            summary["closed"] += 1
        if task.get("disposition_status") not in {None, "open"}:
            summary["dispositioned"] += 1
    return summary


def _task_resolved(task: dict[str, Any]) -> bool:
    return bool(task.get("closure_record_path")) or task.get("disposition_status") in {"covered_by", "superseded", "not_needed", "closed_manually"}


def _task_line(task: dict[str, Any]) -> str:
    return (
        f"{task.get('task_id')}: {task.get('task_title')} | "
        f"closure={task.get('closure_status', 'open')} | disposition={task.get('disposition_status', 'open')} | "
        f"covered_by={task.get('covered_by_task_id') or 'none'}"
    )


def _run_line(run: Any) -> str:
    return f"{run.run_id}: status={run.status.value}, goal={run.goal}, updated_at={run.updated_at.isoformat()}"


def _latest_run_line(project_name: str, root: Path) -> str | None:
    runs = list_runs(project_name, workspace_root=root)
    if not runs:
        return None
    return _run_line(runs[-1])


def _blockers_from_workflow(workflow: dict[str, Any]) -> list[str]:
    blockers = workflow.get("blockers", []) if workflow else []
    return list(blockers) if isinstance(blockers, list) else []


def _project_suggested_actions(project_name: str, context_summary: dict[str, Any], runs: list[Any]) -> list[str]:
    actions: list[str] = []
    suggested = context_summary.get("suggested_next_context_action") if context_summary else None
    if suggested:
        actions.append(str(suggested))
    if runs:
        actions.append(f"Run `devo report run --project {project_name} --run {runs[-1].run_id}` for the latest run.")
    else:
        actions.append(f"Create a run with `devo run create --project {project_name} --goal <goal>` after context is approved.")
    return actions


def _run_suggested_actions(project_name: str, run_id: str, workflow: dict[str, Any], unresolved: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    command = workflow.get("next_action_command") if workflow else None
    reason = workflow.get("next_action_reason") if workflow else None
    if command:
        actions.append(str(command))
    elif reason:
        actions.append(str(reason))
    if not unresolved:
        actions.append(f"Consider `devo project context-refresh --project {project_name} --run {run_id} --write-draft` if this run changed durable project context.")
    return actions or ["Inspect workflow status before continuing."]


def _handoff_commands(project_name: str, run_id: str | None) -> list[str]:
    commands = [
        f"devo project context-summary {project_name}",
        f"devo report project --project {project_name}",
        f"devo project context-history --project {project_name}",
    ]
    if run_id:
        commands.extend(
            [
                f"devo run status {run_id} --project {project_name}",
                f"devo workflow status --project {project_name} --run {run_id}",
                f"devo task next --project {project_name} --run {run_id}",
                f"devo report run --project {project_name} --run {run_id}",
            ]
        )
    return commands


def _deferred_scope_summary() -> list[str]:
    path = Path("docs/deferred-scope.md")
    if not path.exists():
        return ["No docs/deferred-scope.md file found."]
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("-") or stripped.startswith("#"):
            lines.append(stripped)
        if len(lines) >= 12:
            break
    return lines or ["docs/deferred-scope.md exists but has no summary headings or bullets."]


def _render_value(key: str, value: Any, indent: int) -> list[str]:
    prefix = "  " * indent
    label = key.replace("_", " ").title()
    if isinstance(value, dict):
        lines = [f"{prefix}## {label}" if indent == 0 else f"{prefix}- {label}:"]
        for child_key, child_value in value.items():
            lines.extend(_render_value(child_key, child_value, indent + 1))
        return lines
    if isinstance(value, list):
        lines = [f"{prefix}## {label}" if indent == 0 else f"{prefix}- {label}:"]
        if not value:
            lines.append(f"{prefix}  - none")
        else:
            for item in value:
                if isinstance(item, (dict, list)):
                    lines.extend(_render_value("item", item, indent + 1))
                else:
                    lines.append(f"{prefix}  - {item}")
        return lines
    return [f"{prefix}- {label}: {value if value is not None else 'none'}"]


def _sanitize_report(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_report(item) for key, item in value.items()}
    if isinstance(value, list):
        sanitized = sanitize_summary_items(str(item) if not isinstance(item, (dict, list)) else json.dumps(_sanitize_report(item), default=str) for item in value)
        return sanitized
    if isinstance(value, str):
        return sanitize_summary_items([value])[0]
    return value


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
