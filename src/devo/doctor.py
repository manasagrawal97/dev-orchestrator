from __future__ import annotations

import os
import platform
import subprocess
import sys
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .backups import list_backup_inventory
from .git_delivery import get_git_repository_status
from .projects import get_workspace_root
from .scanner import load_registered_project
from .validation_registry import list_validation_commands, registry_path
from .validation_runner import list_validation_history
from .work_history import list_work_package_summaries

DEFAULT_BACKUP_ROOT = Path(r"G:\My Drive\Projects\Dev Orchestrator")
SCHEDULED_BACKUP_TASK_NAME = "DevOrchestrator Workspace Backup"


class DoctorStatus(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


class DoctorCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: DoctorStatus
    detail: str


class DoctorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str | None = None
    checks: list[DoctorCheck] = Field(default_factory=list)
    overall_status: DoctorStatus
    suggested_next_action: str


def run_doctor(project_name: str | None = None, workspace_root: Path | None = None) -> DoctorReport:
    root = workspace_root or get_workspace_root()
    checks: list[DoctorCheck] = []
    checks.extend(_devo_checks(root))
    checks.extend(_backup_checks())
    if project_name:
        checks.extend(_project_checks(project_name, root))
    overall = _overall_status(checks)
    return DoctorReport(
        project=project_name,
        checks=checks,
        overall_status=overall,
        suggested_next_action=_suggested_next_action(checks, overall),
    )


def _devo_checks(workspace_root: Path) -> list[DoctorCheck]:
    checks = [
        _path_check("Devo workspace exists", workspace_root, expect_dir=True, missing_status=DoctorStatus.FAIL),
        _path_check("workspace/projects exists", workspace_root / "projects", expect_dir=True, missing_status=DoctorStatus.WARN),
        _path_check("workspace/runs exists", workspace_root / "runs", expect_dir=True, missing_status=DoctorStatus.WARN),
    ]
    current_path = workspace_root / "current.json"
    checks.append(
        DoctorCheck(
            name="current.json",
            status=DoctorStatus.OK if current_path.exists() else DoctorStatus.SKIP,
            detail=str(current_path) if current_path.exists() else "No current selection recorded.",
        )
    )
    checks.append(
        DoctorCheck(
            name="Python environment",
            status=DoctorStatus.OK,
            detail=f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    docs = [Path("README.md"), Path("docs/current-state.md"), Path("docs/roadmap.md"), Path("docs/how-to-use-devo.md")]
    missing_docs = [str(path) for path in docs if not path.exists()]
    checks.append(
        DoctorCheck(
            name="Core docs",
            status=DoctorStatus.OK if not missing_docs else DoctorStatus.WARN,
            detail="All core docs present." if not missing_docs else f"Missing: {', '.join(missing_docs)}",
        )
    )
    return checks


def _project_checks(project_name: str, workspace_root: Path) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    try:
        project = load_registered_project(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return [
            DoctorCheck(
                name="Project registration",
                status=DoctorStatus.FAIL,
                detail=str(exc),
            )
        ]

    checks.append(DoctorCheck(name="Project registration", status=DoctorStatus.OK, detail=f"{project.name}: {project.path}"))
    project_path = Path(project.path)
    checks.append(_path_check("Project path exists", project_path, expect_dir=True, missing_status=DoctorStatus.FAIL))

    try:
        git_status = get_git_repository_status(project_name, workspace_root=workspace_root)
        checks.append(
            DoctorCheck(
                name="Project Git status",
                status=DoctorStatus.OK if git_status.working_tree_clean else DoctorStatus.WARN,
                detail=(
                    f"branch={git_status.current_branch or 'unknown'}, clean={git_status.working_tree_clean}, "
                    f"ahead={git_status.ahead if git_status.ahead is not None else 'unknown'}, "
                    f"behind={git_status.behind if git_status.behind is not None else 'unknown'}"
                ),
            )
        )
    except ValueError as exc:
        checks.append(DoctorCheck(name="Project Git status", status=DoctorStatus.FAIL, detail=str(exc)))

    validation_path = registry_path(project_name, workspace_root=workspace_root)
    try:
        commands = list_validation_commands(project_name, workspace_root=workspace_root)
        build_commands = [command for command in commands if command.category.value == "build"]
        checks.append(
            DoctorCheck(
                name="Validation registry",
                status=DoctorStatus.OK if validation_path.exists() else DoctorStatus.WARN,
                detail=f"{len(commands)} command(s); registry={validation_path}",
            )
        )
        checks.append(
            DoctorCheck(
                name="Build validation command",
                status=DoctorStatus.OK if build_commands else DoctorStatus.SKIP,
                detail=f"{len(build_commands)} build command(s) configured." if build_commands else "No build validation command configured.",
            )
        )
    except ValueError as exc:
        checks.append(DoctorCheck(name="Validation registry", status=DoctorStatus.WARN, detail=str(exc)))

    checks.extend(_work_package_checks(project_name, workspace_root))
    checks.extend(_validation_history_checks(project_name, workspace_root))
    checks.extend(_visual_report_checks(project_name, workspace_root))
    return checks


def _work_package_checks(project_name: str, workspace_root: Path) -> list[DoctorCheck]:
    try:
        summaries = list_work_package_summaries(project_name, limit=10, workspace_root=workspace_root)
    except ValueError as exc:
        return [DoctorCheck(name="Work packages", status=DoctorStatus.WARN, detail=str(exc))]
    packages = [summary for summary in summaries if summary.has_work_package]
    open_count = len([summary for summary in packages if summary.status not in {"delivered", "closed"}])
    delivered_count = len([summary for summary in packages if summary.status in {"delivered", "closed"}])
    status = DoctorStatus.OK if packages else DoctorStatus.SKIP
    return [
        DoctorCheck(
            name="Recent work packages",
            status=status,
            detail=f"{len(packages)} recent package(s); open={open_count}; delivered_or_closed={delivered_count}",
        )
    ]


def _validation_history_checks(project_name: str, workspace_root: Path) -> list[DoctorCheck]:
    try:
        records = list_validation_history(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return [DoctorCheck(name="Latest validation", status=DoctorStatus.WARN, detail=str(exc))]
    if not records:
        return [DoctorCheck(name="Latest validation", status=DoctorStatus.SKIP, detail="No validation runs recorded.")]
    latest = sorted(records, key=lambda record: record.started_at, reverse=True)[0]
    status = DoctorStatus.OK if latest.status.value == "passed" else DoctorStatus.WARN
    return [
        DoctorCheck(
            name="Latest validation",
            status=status,
            detail=f"{latest.validation_run_id}: {latest.command_id} status={latest.status.value} exit={latest.exit_code if latest.exit_code is not None else 'none'}",
        )
    ]


def _visual_report_checks(project_name: str, workspace_root: Path) -> list[DoctorCheck]:
    paths = []
    project_visual = workspace_root / "projects" / project_name / "visuals" / "project-activity.md"
    if project_visual.exists():
        paths.append(project_visual)
    runs_root = workspace_root / "runs" / project_name
    if runs_root.exists():
        paths.extend(sorted(runs_root.glob("*/artifacts/visuals/*.md")))
    if not paths:
        return [DoctorCheck(name="Generated visual reports", status=DoctorStatus.SKIP, detail="No generated visual reports found.")]
    latest = sorted(paths, key=lambda path: path.stat().st_mtime, reverse=True)[0]
    return [DoctorCheck(name="Generated visual reports", status=DoctorStatus.OK, detail=f"{len(paths)} found; latest={latest}")]


def _backup_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    backup_root = _discover_backup_root()
    if not backup_root:
        checks.append(
            DoctorCheck(
                name="Backup root",
                status=DoctorStatus.SKIP,
                detail="No backup root discovered. Set DEVO_BACKUP_ROOT or use the documented Google Drive path.",
            )
        )
    else:
        try:
            inventory = list_backup_inventory(backup_root)
            status = DoctorStatus.WARN if inventory.incomplete_backups or inventory.invalid_backup_folders else DoctorStatus.OK
            checks.append(
                DoctorCheck(
                    name="Backup inventory",
                    status=status,
                    detail=(
                        f"root={inventory.backup_root}; complete={len(inventory.complete_backups)}; "
                        f"normal={len(inventory.normal_backups)}; protected={len(inventory.protected_backups)}; "
                        f"incomplete={len(inventory.incomplete_backups)}; invalid={len(inventory.invalid_backup_folders)}"
                    ),
                )
            )
        except ValueError as exc:
            checks.append(DoctorCheck(name="Backup inventory", status=DoctorStatus.WARN, detail=str(exc)))
    checks.append(_scheduled_task_check())
    return checks


def _discover_backup_root() -> Path | None:
    env_value = os.environ.get("DEVO_BACKUP_ROOT")
    if env_value:
        return Path(env_value)
    if DEFAULT_BACKUP_ROOT.exists():
        return DEFAULT_BACKUP_ROOT
    return None


def _scheduled_task_check() -> DoctorCheck:
    if os.environ.get("DEVO_DOCTOR_SKIP_SCHEDULED_TASK") == "1":
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.SKIP, detail="Scheduled task check skipped by environment.")
    if platform.system().lower() != "windows":
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.SKIP, detail="Scheduled task check is Windows-only.")
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not powershell.exists():
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.SKIP, detail="PowerShell not found.")
    command = (
        f"$task = Get-ScheduledTask -TaskName '{SCHEDULED_BACKUP_TASK_NAME}' -ErrorAction SilentlyContinue; "
        "if ($null -eq $task) { 'missing' } else { "
        "$info = Get-ScheduledTaskInfo -TaskName $task.TaskName; "
        "'present; state=' + $task.State + '; next=' + $info.NextRunTime + '; last=' + $info.LastRunTime + '; result=' + $info.LastTaskResult }"
    )
    try:
        completed = subprocess.run(
            [str(powershell), "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.SKIP, detail=f"Could not inspect scheduled task: {exc}")
    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.SKIP, detail=output or "Scheduled task query failed.")
    if output == "missing":
        return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.WARN, detail=f"Task not found: {SCHEDULED_BACKUP_TASK_NAME}")
    return DoctorCheck(name="Backup scheduled task", status=DoctorStatus.OK, detail=output or "Task present.")


def _path_check(name: str, path: Path, expect_dir: bool, missing_status: DoctorStatus) -> DoctorCheck:
    if not path.exists():
        return DoctorCheck(name=name, status=missing_status, detail=f"Missing: {path}")
    if expect_dir and not path.is_dir():
        return DoctorCheck(name=name, status=DoctorStatus.FAIL, detail=f"Expected directory: {path}")
    if not expect_dir and not path.is_file():
        return DoctorCheck(name=name, status=DoctorStatus.FAIL, detail=f"Expected file: {path}")
    return DoctorCheck(name=name, status=DoctorStatus.OK, detail=str(path))


def _overall_status(checks: list[DoctorCheck]) -> DoctorStatus:
    if any(check.status == DoctorStatus.FAIL for check in checks):
        return DoctorStatus.FAIL
    if any(check.status == DoctorStatus.WARN for check in checks):
        return DoctorStatus.WARN
    return DoctorStatus.OK


def _suggested_next_action(checks: list[DoctorCheck], overall: DoctorStatus) -> str:
    for check in checks:
        if check.status == DoctorStatus.FAIL:
            if "Project path" in check.name:
                return "Update or re-register the project path."
            return f"Fix failed check: {check.name}."
    for check in checks:
        if check.status == DoctorStatus.WARN and "Backup" in check.name and "incomplete=" in check.detail and "incomplete=0" not in check.detail:
            return "Review backup status; incomplete backups usually mean interrupted/failed backup runs."
    for check in checks:
        if check.status == DoctorStatus.WARN:
            if "Validation registry" in check.name:
                return "Register validation commands for the project."
            if "Git" in check.name:
                return "Review project Git status."
            return f"Review warning: {check.name}."
    if overall == DoctorStatus.OK:
        return "No action needed."
    return "Review skipped optional checks if you expected them to be configured."
