from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .context_updates import list_context_updates
from .git_delivery import get_git_repository_status
from .projects import get_workspace_root
from .runs import list_runs, run_path
from .validation_runner import list_validation_history
from .work_packages import WorkPackage, WorkPackageStatus, get_work_package_next_step, load_work_package


class WorkPackageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    run_id: str
    goal: str
    lane: str = "none"
    status: str
    has_work_package: bool = False
    approval_bundle_status: str = "not available"
    latest_validation_status: str = "none"
    latest_validation_run_id: str | None = None
    commit_hash: str | None = None
    delivery_summary: str | None = None
    next_action: str = "unknown"
    updated_at: datetime


class ProjectActivitySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    recent_runs: list[str]
    delivered_work_packages: list[WorkPackageSummary]
    latest_validation_runs: list[str]
    latest_context_updates: list[str]
    latest_reports: list[str]
    current_git_status: str
    suggested_next_action: str


def list_work_package_summaries(
    project_name: str,
    limit: int = 10,
    delivered_first: bool = False,
    workspace_root: Path | None = None,
) -> list[WorkPackageSummary]:
    root = workspace_root or get_workspace_root()
    safe_limit = _safe_limit(limit)
    runs = sorted(list_runs(project_name, workspace_root=root), key=lambda item: item.updated_at, reverse=True)
    validations = _latest_validations_by_run(project_name, root)
    summaries = [_summary_for_run(project_name, run, root, validations) for run in runs]
    if delivered_first:
        summaries = sorted(
            summaries,
            key=lambda item: (
                item.status not in {WorkPackageStatus.DELIVERED.value, WorkPackageStatus.CLOSED.value},
                -item.updated_at.timestamp(),
            ),
        )
    return summaries[:safe_limit]


def build_project_activity_summary(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> ProjectActivitySummary:
    root = workspace_root or get_workspace_root()
    safe_limit = _safe_limit(limit)
    runs = sorted(list_runs(project_name, workspace_root=root), key=lambda item: item.updated_at, reverse=True)
    validations = _latest_validations_by_run(project_name, root)
    work_summaries = [_summary_for_run(project_name, run, root, validations) for run in runs]
    work_summaries = sorted(
        work_summaries,
        key=lambda item: (
            item.status not in {WorkPackageStatus.DELIVERED.value, WorkPackageStatus.CLOSED.value},
            -item.updated_at.timestamp(),
        ),
    )[: max(safe_limit, 25)]
    delivered = [item for item in work_summaries if item.status in {WorkPackageStatus.DELIVERED.value, WorkPackageStatus.CLOSED.value}]
    open_packages = [
        item
        for item in work_summaries
        if item.has_work_package and item.status not in {WorkPackageStatus.DELIVERED.value, WorkPackageStatus.CLOSED.value}
    ]
    return ProjectActivitySummary(
        project=project_name,
        recent_runs=[
            f"{run.run_id}: status={run.status.value}, goal={run.goal}"
            for run in runs[:safe_limit]
        ],
        delivered_work_packages=delivered[:safe_limit],
        latest_validation_runs=_validation_lines(project_name, root, safe_limit),
        latest_context_updates=_context_update_lines(project_name, root, safe_limit),
        latest_reports=_report_lines(project_name, root, safe_limit),
        current_git_status=_git_status_line(project_name, root),
        suggested_next_action=_suggested_next_action(open_packages, delivered),
    )


def _summary_for_run(project_name: str, run_state, workspace_root: Path, validations_by_run: dict[str, object | None]) -> WorkPackageSummary:
    validation = validations_by_run.get(run_state.run_id)
    try:
        package = load_work_package(project_name, run_state.run_id, workspace_root=workspace_root)
    except ValueError:
        return WorkPackageSummary(
            project=project_name,
            run_id=run_state.run_id,
            goal=run_state.goal,
            status=f"run:{run_state.status.value}",
            has_work_package=False,
            latest_validation_status=_validation_status_text(validation),
            latest_validation_run_id=validation.validation_run_id if validation else None,
            next_action="No work-package artifact found.",
            updated_at=run_state.updated_at,
        )
    return _summary_for_package(package, validation, workspace_root)


def _summary_for_package(package: WorkPackage, validation: object | None, workspace_root: Path) -> WorkPackageSummary:
    approval_status = package.approval_bundle_status or _approval_bundle_status(package, workspace_root) or "not available"
    return WorkPackageSummary(
        project=package.project,
        run_id=package.run_id,
        goal=package.goal,
        lane=package.lane,
        status=package.status.value,
        has_work_package=True,
        approval_bundle_status=approval_status,
        latest_validation_status=_validation_status_text(validation),
        latest_validation_run_id=getattr(validation, "validation_run_id", None),
        commit_hash=package.commit_hash,
        delivery_summary=package.delivery_summary,
        next_action=get_work_package_next_step(package).next_action,
        updated_at=package.updated_at,
    )


def _latest_validation_for_run(project_name: str, run_id: str, workspace_root: Path):
    records = [record for record in list_validation_history(project_name, workspace_root=workspace_root) if record.run_id == run_id]
    if not records:
        return None
    return sorted(records, key=lambda item: item.started_at, reverse=True)[0]


def _latest_validations_by_run(project_name: str, workspace_root: Path) -> dict[str, object]:
    try:
        records = list_validation_history(project_name, workspace_root=workspace_root)
    except ValueError:
        return {}
    latest: dict[str, object] = {}
    for record in sorted(records, key=lambda item: item.started_at, reverse=True):
        if record.run_id and record.run_id not in latest:
            latest[record.run_id] = record
    return latest


def _validation_status_text(record: object | None) -> str:
    if not record:
        return "none"
    exit_code = getattr(record, "exit_code", None)
    suffix = f", exit={exit_code}" if exit_code is not None else ""
    return f"{getattr(record, 'status').value}{suffix}"


def _approval_bundle_status(package: WorkPackage, workspace_root: Path) -> str | None:
    if not package.approval_bundle_id:
        return None
    path = (
        run_path(package.project, package.run_id, workspace_root=workspace_root)
        / "artifacts"
        / "approval-bundles"
        / f"approval-bundle-{package.approval_bundle_id}.json"
    )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("status")
    return str(value) if value else None


def _validation_lines(project_name: str, workspace_root: Path, limit: int) -> list[str]:
    try:
        records = list_validation_history(project_name, workspace_root=workspace_root)
    except ValueError:
        return []
    lines = [
        f"{record.validation_run_id}: run={record.run_id or 'none'}, command={record.command_id}, status={record.status.value}, exit={record.exit_code if record.exit_code is not None else 'none'}"
        for record in sorted(records, key=lambda item: item.started_at, reverse=True)
    ]
    return lines[:limit]


def _context_update_lines(project_name: str, workspace_root: Path, limit: int) -> list[str]:
    try:
        ledger = list_context_updates(project_name, workspace_root=workspace_root)
    except ValueError:
        return []
    updates = sorted(ledger.updates, key=lambda item: item.created_at, reverse=True)
    return [
        f"{update.update_id}: status={update.status.value}, source_run={update.source_run_id or 'none'}"
        for update in updates[:limit]
    ]


def _report_lines(project_name: str, workspace_root: Path, limit: int) -> list[str]:
    paths: list[Path] = []
    paths.extend((workspace_root / "projects" / project_name / "reports").glob("*.json"))
    runs_root = workspace_root / "runs" / project_name
    if runs_root.exists():
        for run_dir in runs_root.iterdir():
            if run_dir.is_dir():
                paths.extend((run_dir / "artifacts" / "reports").glob("*.json"))
    ordered = sorted(paths, key=lambda item: item.stat().st_mtime if item.exists() else 0, reverse=True)
    return [f"{path.name}: {path}" for path in ordered[:limit]]


def _git_status_line(project_name: str, workspace_root: Path) -> str:
    try:
        status = get_git_repository_status(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return f"unavailable: {exc}"
    return (
        f"branch={status.current_branch or 'unknown'}, head={status.head_commit or 'unknown'}, "
        f"clean={status.working_tree_clean}, ahead={status.ahead if status.ahead is not None else 'unknown'}, "
        f"behind={status.behind if status.behind is not None else 'unknown'}"
    )


def _suggested_next_action(open_packages: list[WorkPackageSummary], delivered: list[WorkPackageSummary]) -> str:
    if open_packages:
        package = open_packages[0]
        return f"Continue {package.run_id}: {package.next_action}"
    if delivered:
        return "No open work packages. Pick or start the next scoped work package."
    return "No work-package history yet. Start a work package when ready."


def _safe_limit(limit: int) -> int:
    return max(1, min(limit, 100))
