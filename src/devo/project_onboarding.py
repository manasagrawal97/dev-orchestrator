from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .context import get_context_status
from .doctor import run_doctor
from .git_delivery import get_git_repository_status
from .projects import get_workspace_root
from .project_settings import load_project_settings, project_settings_path
from .scanner import load_registered_project
from .schemas import ProjectScanResult
from .validation_registry import list_validation_commands, registry_path


class OnboardingStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"


class OnboardingCheckStatus(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


class OnboardingCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: OnboardingCheckStatus
    detail: str


class SuggestedProjectSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str
    notes: list[str] = Field(default_factory=list)


class ProjectOnboardingReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    overall_status: OnboardingStatus
    checks: list[OnboardingCheck] = Field(default_factory=list)
    suggested_next_command: str
    suggested_settings: SuggestedProjectSettings | None = None
    report_path: Path | None = None


def build_project_onboarding_report(
    project_name: str,
    *,
    include_suggested_settings: bool = False,
    include_doctor: bool = True,
    write_suggestions: bool = False,
    workspace_root: Path | None = None,
) -> ProjectOnboardingReport:
    root = workspace_root or get_workspace_root()
    checks: list[OnboardingCheck] = []
    project_dir = root / "projects" / project_name
    project_file = project_dir / "project.json"

    if not project_file.exists():
        checks.append(
            OnboardingCheck(
                name="Project registration",
                status=OnboardingCheckStatus.FAIL,
                detail=f"Registered project not found: {project_name}",
            )
        )
        report = ProjectOnboardingReport(
            project_name=project_name,
            overall_status=OnboardingStatus.NOT_STARTED,
            checks=checks,
            suggested_next_command=f"devo project add --name {project_name} --path <projectPath>",
        )
        return _maybe_write_report(report, root, write_suggestions)

    try:
        registration = load_registered_project(project_name, workspace_root=root)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        checks.append(OnboardingCheck(name="Project registration", status=OnboardingCheckStatus.FAIL, detail=str(exc)))
        report = ProjectOnboardingReport(
            project_name=project_name,
            overall_status=OnboardingStatus.NEEDS_ATTENTION,
            checks=checks,
            suggested_next_command=f"Repair or re-register project metadata for {project_name}.",
        )
        return _maybe_write_report(report, root, write_suggestions)

    checks.append(OnboardingCheck(name="Project registration", status=OnboardingCheckStatus.OK, detail=str(project_file)))
    path_exists = Path(registration.path).exists()
    checks.append(
        OnboardingCheck(
            name="Project path",
            status=OnboardingCheckStatus.OK if path_exists else OnboardingCheckStatus.FAIL,
            detail=str(registration.path) if path_exists else f"Path does not exist: {registration.path}",
        )
    )

    scan_exists, scan_detail, scan_categories = _scan_status(project_name, root)
    checks.append(
        OnboardingCheck(
            name="Project scan",
            status=OnboardingCheckStatus.OK if scan_exists else OnboardingCheckStatus.WARN,
            detail=scan_detail,
        )
    )

    context_value, context_detail = _context_status(project_name, root)
    checks.append(
        OnboardingCheck(
            name="Project context",
            status=OnboardingCheckStatus.OK if context_value == "CONTEXT_APPROVED" else OnboardingCheckStatus.WARN,
            detail=context_detail,
        )
    )

    validation_exists, validation_count, validation_detail, validation_ids = _validation_status(project_name, root)
    checks.append(
        OnboardingCheck(
            name="Validation registry",
            status=OnboardingCheckStatus.OK if validation_exists and validation_count > 0 else OnboardingCheckStatus.WARN,
            detail=validation_detail,
        )
    )

    settings_exists, settings_has_lane, settings_detail = _settings_status(project_name, root)
    checks.append(
        OnboardingCheck(
            name="Project settings",
            status=OnboardingCheckStatus.OK if settings_exists and settings_has_lane else OnboardingCheckStatus.WARN,
            detail=settings_detail,
        )
    )

    if include_doctor:
        doctor_detail = _doctor_status(project_name, root)
        checks.append(
            OnboardingCheck(
                name="Doctor",
                status=OnboardingCheckStatus.OK if doctor_detail.startswith("OK") else OnboardingCheckStatus.WARN,
                detail=doctor_detail,
            )
        )

    suggested_settings = (
        suggest_project_settings(project_name, scan_categories=scan_categories, validation_ids=validation_ids, workspace_root=root)
        if include_suggested_settings
        else None
    )
    overall = _overall_status(checks, context_value=context_value, validation_count=validation_count, settings_has_lane=settings_has_lane)
    report = ProjectOnboardingReport(
        project_name=project_name,
        overall_status=overall,
        checks=checks,
        suggested_next_command=_suggest_next_command(
            project_name,
            scan_exists=scan_exists,
            context_value=context_value,
            validation_exists=validation_exists,
            validation_count=validation_count,
            settings_exists=settings_exists,
            settings_has_lane=settings_has_lane,
            suggested_settings=suggested_settings,
        ),
        suggested_settings=suggested_settings,
    )
    return _maybe_write_report(report, root, write_suggestions)


def render_project_onboarding_markdown(report: ProjectOnboardingReport) -> str:
    lines = [
        f"# Project Onboarding: {report.project_name}",
        "",
        f"- Onboarding overall status: {report.overall_status.value}",
        f"- Suggested next command: `{report.suggested_next_command}`",
        "",
        "## Checklist",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.status.value} {check.name}: {check.detail}")
    if report.suggested_settings:
        lines.extend(
            [
                "",
                "## Suggested Settings",
                "",
                f"```powershell\n{report.suggested_settings.command}\n```",
            ]
        )
        if report.suggested_settings.notes:
            lines.append("")
            lines.append("Notes:")
            for note in report.suggested_settings.notes:
                lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def suggest_project_settings(
    project_name: str,
    *,
    scan_categories: dict[str, list[str]] | None = None,
    validation_ids: set[str] | None = None,
    workspace_root: Path | None = None,
) -> SuggestedProjectSettings:
    root = workspace_root or get_workspace_root()
    validation_ids = validation_ids or set()
    branch = _current_branch(project_name, root)
    notes: list[str] = []

    if project_name == "DevOrchestrator":
        branch_part = f" --default-branch {branch or 'main'}"
        return SuggestedProjectSettings(
            command=(
                "devo project settings-set --project DevOrchestrator "
                f"--default-lane devo-internal-source{branch_part} "
                "--allow-auto-scope-template --delivery-mode approved_commit_push"
            ),
            notes=["DevOrchestrator uses the internal source lane for Devo source/docs/tests work."],
        )

    is_dotnet = _scan_has_dotnet(scan_categories or {})
    if project_name == "PersonalOS" or is_dotnet:
        branch_part = f" --default-branch {branch or 'master'}"
        validation_part = " --default-validation-command dotnet-build-personalos" if "dotnet-build-personalos" in validation_ids else ""
        if not validation_part:
            notes.append("Register or choose a .NET build validation command before setting a validation default.")
        return SuggestedProjectSettings(
            command=(
                f"devo project settings-set --project {project_name} "
                " --default-lane low-risk-ui-maintenance"
                f"{validation_part}{branch_part} --allow-auto-scope-template --delivery-mode approved_commit_push"
            ).replace("  ", " "),
            notes=notes or ["Use low-risk-ui-maintenance for UI-only PersonalOS-style maintenance batches."],
        )

    return SuggestedProjectSettings(
        command=f"devo project settings-set --project {project_name} --default-lane <lane> --default-branch <branch>",
        notes=["No project-specific default lane inferred; choose a lane with `devo work lanes`."],
    )


def _scan_status(project_name: str, workspace_root: Path) -> tuple[bool, str, dict[str, list[str]]]:
    path = workspace_root / "projects" / project_name / "scan-result.json"
    if not path.exists():
        return False, "No scan-result.json found.", {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        scan = ProjectScanResult.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        return False, f"Scan result is malformed: {exc}", {}
    categories = {
        "solution_files": scan.categories.solution_files,
        "project_files": scan.categories.project_files,
        "package_dependency_files": scan.categories.package_dependency_files,
    }
    scanned_at = scan.scanned_at.isoformat() if isinstance(scan.scanned_at, datetime) else str(scan.scanned_at)
    return True, f"Scanned at {scanned_at}; files={scan.file_tree.scanned_file_count}.", categories


def _context_status(project_name: str, workspace_root: Path) -> tuple[str, str]:
    try:
        status = get_context_status(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return "UNKNOWN", str(exc)
    context_value = str(status.get("context_status") or "UNKNOWN")
    approval = status.get("approval_status") or "not approved"
    return context_value, f"{context_value}; approval={approval}"


def _validation_status(project_name: str, workspace_root: Path) -> tuple[bool, int, str, set[str]]:
    path = registry_path(project_name, workspace_root=workspace_root)
    try:
        commands = list_validation_commands(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return path.exists(), 0, str(exc), set()
    ids = {command.id for command in commands}
    if not path.exists():
        return False, len(commands), f"No validation registry found at {path}.", ids
    return True, len(commands), f"{len(commands)} command(s); registry={path}", ids


def _settings_status(project_name: str, workspace_root: Path) -> tuple[bool, bool, str]:
    try:
        path = project_settings_path(project_name, workspace_root=workspace_root)
        settings = load_project_settings(project_name, workspace_root=workspace_root)
    except ValueError as exc:
        return False, False, str(exc)
    exists = path.exists()
    lane = settings.default_lane or "none"
    branch = settings.default_branch or "none"
    validation = settings.default_validation_command or "none"
    detail = f"default_lane={lane}; default_branch={branch}; default_validation={validation}"
    if not exists:
        detail = f"No settings.json yet; {detail}"
    return exists, bool(settings.default_lane), detail


def _doctor_status(project_name: str, workspace_root: Path) -> str:
    try:
        report = run_doctor(project_name=project_name, workspace_root=workspace_root)
    except Exception as exc:  # doctor must not break onboarding guidance
        return f"WARN doctor unavailable: {exc}"
    return f"{report.overall_status.value}; {report.suggested_next_action}"


def _overall_status(
    checks: list[OnboardingCheck],
    *,
    context_value: str,
    validation_count: int,
    settings_has_lane: bool,
) -> OnboardingStatus:
    if any(check.status == OnboardingCheckStatus.FAIL for check in checks):
        return OnboardingStatus.NEEDS_ATTENTION
    required_ready = context_value == "CONTEXT_APPROVED" and validation_count > 0 and settings_has_lane
    if required_ready:
        return OnboardingStatus.READY
    return OnboardingStatus.IN_PROGRESS


def _suggest_next_command(
    project_name: str,
    *,
    scan_exists: bool,
    context_value: str,
    validation_exists: bool,
    validation_count: int,
    settings_exists: bool,
    settings_has_lane: bool,
    suggested_settings: SuggestedProjectSettings | None,
) -> str:
    if not scan_exists:
        return f"devo project scan {project_name}"
    if context_value != "CONTEXT_APPROVED":
        if context_value == "CONTEXT_REVIEWED":
            return f"devo project approve-context {project_name}"
        return f"devo agent prompt ProjectContextDiscoveryAgent --project {project_name}"
    if not validation_exists or validation_count == 0:
        return f"devo validation suggest --project {project_name} --write"
    if not settings_exists or not settings_has_lane:
        return suggested_settings.command if suggested_settings else f"devo project settings-set --project {project_name} --default-lane <lane>"
    return f"devo work new --project {project_name} --goal \"<goal>\""


def _maybe_write_report(report: ProjectOnboardingReport, workspace_root: Path, write: bool) -> ProjectOnboardingReport:
    if not write:
        return report
    report_dir = workspace_root / "projects" / report.project_name / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "onboarding-report.md"
    report = report.model_copy(update={"report_path": path})
    path.write_text(render_project_onboarding_markdown(report), encoding="utf-8")
    return report


def _current_branch(project_name: str, workspace_root: Path) -> str | None:
    try:
        return get_git_repository_status(project_name, workspace_root=workspace_root).current_branch
    except ValueError:
        return None


def _scan_has_dotnet(categories: dict[str, list[str]]) -> bool:
    paths = categories.get("solution_files", []) + categories.get("project_files", [])
    return any(Path(path).suffix.lower() in {".sln", ".slnx", ".csproj"} for path in paths)
