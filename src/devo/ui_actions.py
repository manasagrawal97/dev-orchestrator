from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .project_onboarding import build_project_onboarding_report
from .project_settings import load_project_settings
from .projects import get_workspace_root
from .runs import load_run
from .scanner import load_registered_project
from .visual_reports import generate_project_activity_visual, generate_work_package_visual
from .work_packages import generate_work_scope_template, start_work_package

UiActionCategory = Literal["read_only", "workspace_safe", "approval_required", "dangerous_deferred"]
UiActionStatus = Literal["available", "read_only", "planned", "deferred", "blocked"]
UiRiskLevel = Literal["none", "low", "medium", "high", "critical"]
UiActionResultStatus = Literal["OK", "WARN", "FAIL", "BLOCKED"]

UI_MODE_READ_ONLY = "read_only"
UI_MODE_CONTROLLED_WORKSPACE = "controlled_workspace"
CURRENT_UI_MODE = UI_MODE_CONTROLLED_WORKSPACE
EXECUTABLE_WORKSPACE_SAFE_ACTIONS = {
    "work.scope_template.generate",
    "visual.work_package.generate",
    "visual.project_activity.generate",
    "onboarding.report.write",
    "work.new.create",
}


@dataclass(frozen=True)
class UiActionMetadata:
    id: str
    label: str
    category: UiActionCategory
    description: str
    allowed_in_ui_v1: bool
    allowed_in_ui_v2_candidate: bool
    mutates_workspace: bool
    mutates_target_project: bool
    requires_approval: bool
    risk_level: UiRiskLevel
    status: UiActionStatus
    reason: str
    required_cli_command: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class UiActionExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    project: str | None = None
    run_id: str | None = None
    goal: str | None = None
    lane: str | None = None
    confirm: bool = False
    no_template: bool = False


class UiActionExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: UiActionResultStatus
    action_id: str
    message: str
    project: str | None = None
    run_id: str | None = None
    lane: str | None = None
    artifact_path: Path | None = None
    suggested_next_command: str | None = None


ACTION_REGISTRY: tuple[UiActionMetadata, ...] = (
    UiActionMetadata(
        id="project.overview.view",
        label="View project overview",
        category="read_only",
        description="Inspect project overview read models.",
        allowed_in_ui_v1=True,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="none",
        status="read_only",
        reason="Read-only API endpoint backed by ProjectOverview.",
        required_cli_command="devo project overview --project <project> --json",
    ),
    UiActionMetadata(
        id="project.activity.view",
        label="View project activity",
        category="read_only",
        description="Inspect recent project runs, work packages, validation, and delivery summaries.",
        allowed_in_ui_v1=True,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="none",
        status="read_only",
        reason="Read-only API endpoint backed by project activity summaries.",
        required_cli_command="devo project activity --project <project> --json",
    ),
    UiActionMetadata(
        id="doctor.view",
        label="View doctor health checks",
        category="read_only",
        description="Inspect Devo and project health checks without running target commands.",
        allowed_in_ui_v1=True,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="none",
        status="read_only",
        reason="Doctor is read-only and avoids build, test, backup, restore, and scheduler mutation.",
        required_cli_command="devo doctor --project <project> --json",
    ),
    UiActionMetadata(
        id="command.copy",
        label="Copy CLI command",
        category="read_only",
        description="Copy a suggested Devo CLI command from the dashboard.",
        allowed_in_ui_v1=True,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="none",
        status="available",
        reason="Copying text does not call Devo actions or mutate files.",
    ),
    UiActionMetadata(
        id="work.scope_template.generate",
        label="Generate work scope template",
        category="workspace_safe",
        description="Create a standard work-package scope template under the Devo workspace.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="low",
        status="available",
        reason="Available through the controlled UI action endpoint with confirmation; writes Devo workspace artifacts only.",
        required_cli_command="devo work scope-template --project <project> --run <runId>",
    ),
    UiActionMetadata(
        id="visual.work_package.generate",
        label="Generate work-package visual report",
        category="workspace_safe",
        description="Write a generated Mermaid work-package visual under workspace artifacts.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="low",
        status="available",
        reason="Available through the controlled UI action endpoint with confirmation; writes Devo workspace artifacts only.",
        required_cli_command="devo visual work-package --project <project> --run <runId>",
    ),
    UiActionMetadata(
        id="visual.project_activity.generate",
        label="Generate project activity visual report",
        category="workspace_safe",
        description="Write a generated Mermaid project activity visual under workspace artifacts.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="low",
        status="available",
        reason="Available through the controlled UI action endpoint with confirmation; writes Devo workspace artifacts only.",
        required_cli_command="devo visual project-activity --project <project>",
    ),
    UiActionMetadata(
        id="onboarding.report.write",
        label="Write onboarding report",
        category="workspace_safe",
        description="Write a generated onboarding report under workspace project reports.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="low",
        status="available",
        reason="Available through the controlled UI action endpoint with confirmation; writes Devo workspace artifacts only.",
        required_cli_command="devo project onboard --project <project> --write-suggestions",
    ),
    UiActionMetadata(
        id="work.new.create",
        label="Create work-package draft",
        category="workspace_safe",
        description="Create a Devo run/work-package draft and optional scope template.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=True,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=False,
        risk_level="low",
        status="available",
        reason="Available through the controlled UI action endpoint with confirmation; creates Devo run and work-package artifacts only.",
        required_cli_command='devo work new --project <project> --goal "<goal>" --lane <lane>',
    ),
    UiActionMetadata(
        id="work.approval_bundle.request",
        label="Request approval bundle",
        category="approval_required",
        description="Create approval records for an imported work-package scope.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="medium",
        status="deferred",
        reason="Approval workflows need explicit UX and audit safeguards before UI exposure.",
        required_cli_command="devo work request-approval-bundle --project <project> --run <runId>",
    ),
    UiActionMetadata(
        id="approval.approve",
        label="Approve or reject approval",
        category="approval_required",
        description="Approve or reject an approval request or bundle.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="high",
        status="deferred",
        reason="Human approval actions should stay CLI/manual until UI confirmation and identity model are designed.",
    ),
    UiActionMetadata(
        id="validation.run",
        label="Run validation command",
        category="approval_required",
        description="Run a registered target validation command such as build or test.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="high",
        status="deferred",
        reason="Validation may run target repo commands and must remain approval-gated outside UI v1.",
        required_cli_command="devo validation run --project <project> --run <runId> --task <taskId> --id <validationId>",
    ),
    UiActionMetadata(
        id="git.commit",
        label="Commit target changes",
        category="dangerous_deferred",
        description="Create a Git commit in a Devo or target repository.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=False,
        mutates_target_project=True,
        requires_approval=True,
        risk_level="high",
        status="blocked",
        reason="Delivery mutations remain Codex/CLI-controlled and are not UI actions.",
    ),
    UiActionMetadata(
        id="git.push",
        label="Push target changes",
        category="dangerous_deferred",
        description="Push repository commits to a remote.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=False,
        mutates_target_project=True,
        requires_approval=True,
        risk_level="high",
        status="blocked",
        reason="Remote delivery stays outside UI action scope.",
    ),
    UiActionMetadata(
        id="backup.restore",
        label="Restore backup",
        category="dangerous_deferred",
        description="Restore a workspace backup.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="critical",
        status="blocked",
        reason="Restore is destructive and must not be exposed through dashboard MVP actions.",
    ),
    UiActionMetadata(
        id="backup.delete",
        label="Delete backup",
        category="dangerous_deferred",
        description="Delete backup folders or backup records.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="critical",
        status="blocked",
        reason="Backup deletion is destructive and deferred indefinitely.",
    ),
    UiActionMetadata(
        id="scheduler.modify",
        label="Modify scheduler",
        category="dangerous_deferred",
        description="Create, update, or delete scheduled tasks.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="critical",
        status="blocked",
        reason="Scheduler changes affect the host system and stay outside UI actions.",
    ),
    UiActionMetadata(
        id="target_app.run",
        label="Run target app",
        category="dangerous_deferred",
        description="Start a target application from the UI.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=False,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="high",
        status="blocked",
        reason="Running target apps can touch local services, databases, and external integrations.",
    ),
    UiActionMetadata(
        id="agent.run",
        label="Run model/API agent",
        category="dangerous_deferred",
        description="Call a model adapter or external AI agent.",
        allowed_in_ui_v1=False,
        allowed_in_ui_v2_candidate=False,
        mutates_workspace=True,
        mutates_target_project=False,
        requires_approval=True,
        risk_level="high",
        status="blocked",
        reason="Direct model/API agents are future scope and must include cost and safety controls first.",
    ),
)


def list_ui_actions() -> list[UiActionMetadata]:
    return list(ACTION_REGISTRY)


def get_ui_action(action_id: str) -> UiActionMetadata | None:
    normalized = action_id.strip()
    return next((action for action in ACTION_REGISTRY if action.id == normalized), None)


def is_action_allowed(action: UiActionMetadata, *, ui_mode: str = UI_MODE_READ_ONLY) -> bool:
    if ui_mode == UI_MODE_READ_ONLY:
        return action.allowed_in_ui_v1 and action.category == "read_only" and not action.mutates_workspace and not action.mutates_target_project
    if ui_mode == UI_MODE_CONTROLLED_WORKSPACE:
        read_only_allowed = action.allowed_in_ui_v1 and action.category == "read_only"
        workspace_allowed = action.id in EXECUTABLE_WORKSPACE_SAFE_ACTIONS and action.category == "workspace_safe"
        return (read_only_allowed or workspace_allowed) and not action.mutates_target_project
    return False


def list_allowed_ui_actions(*, ui_mode: str = CURRENT_UI_MODE) -> list[UiActionMetadata]:
    return [action for action in ACTION_REGISTRY if is_action_allowed(action, ui_mode=ui_mode)]


def execute_ui_action(request: UiActionExecuteRequest, *, workspace_root: Path | None = None) -> UiActionExecutionResult:
    root = workspace_root or get_workspace_root()
    action = get_ui_action(request.action_id)
    if not action:
        raise ValueError(f"Unknown UI action: {request.action_id}")

    if action.category == "read_only":
        return UiActionExecutionResult(
            status="BLOCKED",
            action_id=action.id,
            message="Read-only actions do not need execution. Use the matching GET endpoint instead.",
            suggested_next_command=action.required_cli_command,
        )
    if action.category in {"approval_required", "dangerous_deferred"}:
        return UiActionExecutionResult(
            status="BLOCKED",
            action_id=action.id,
            message=f"{action.label} is {action.status}; UI execution is not available for this risk category.",
            suggested_next_command=action.required_cli_command,
        )
    if action.id not in EXECUTABLE_WORKSPACE_SAFE_ACTIONS:
        return UiActionExecutionResult(
            status="BLOCKED",
            action_id=action.id,
            message="This workspace-safe action is not enabled for UI execution yet.",
            suggested_next_command=action.required_cli_command,
        )
    if not request.confirm:
        return UiActionExecutionResult(
            status="BLOCKED",
            action_id=action.id,
            message='confirm=true is required because this action writes Devo workspace artifacts only.',
            suggested_next_command=action.required_cli_command,
        )

    project_name = _require_project_name(request.project)
    load_registered_project(project_name, workspace_root=root)
    run_id = request.run_id.strip() if request.run_id else None
    if action.id in {"work.scope_template.generate", "visual.work_package.generate"}:
        run_id = _require_run_id(run_id, action.id)
        load_run(project_name, run_id, workspace_root=root)

    if action.id == "work.new.create":
        return _execute_work_new(request, project_name, root, action)
    if action.id == "work.scope_template.generate":
        template = generate_work_scope_template(project_name, run_id or "", workspace_root=root)
        return UiActionExecutionResult(
            status="OK",
            action_id=action.id,
            message="Generated work scope template under the Devo workspace.",
            project=project_name,
            run_id=run_id,
            artifact_path=template.template_path,
            suggested_next_command=f"devo work import-scope --project {project_name} --run {run_id} --file {template.template_path}",
        )
    if action.id == "visual.work_package.generate":
        visual = generate_work_package_visual(project_name, run_id or "", workspace_root=root)
        return UiActionExecutionResult(
            status="OK",
            action_id=action.id,
            message="Generated work-package visual report under the Devo workspace.",
            project=project_name,
            run_id=run_id,
            artifact_path=visual.path,
            suggested_next_command=f"devo visual work-package --project {project_name} --run {run_id}",
        )
    if action.id == "visual.project_activity.generate":
        visual = generate_project_activity_visual(project_name, workspace_root=root)
        return UiActionExecutionResult(
            status="OK",
            action_id=action.id,
            message="Generated project activity visual report under the Devo workspace.",
            project=project_name,
            artifact_path=visual.path,
            suggested_next_command=f"devo visual project-activity --project {project_name}",
        )
    if action.id == "onboarding.report.write":
        report = build_project_onboarding_report(
            project_name,
            include_suggested_settings=True,
            write_suggestions=True,
            workspace_root=root,
        )
        return UiActionExecutionResult(
            status="OK",
            action_id=action.id,
            message="Wrote onboarding report under the Devo workspace.",
            project=project_name,
            artifact_path=report.report_path,
            suggested_next_command=f"devo project onboard --project {project_name} --write-suggestions",
        )

    return UiActionExecutionResult(status="FAIL", action_id=action.id, message="No executor is registered for this action.")


def _execute_work_new(
    request: UiActionExecuteRequest,
    project_name: str,
    workspace_root: Path,
    action: UiActionMetadata,
) -> UiActionExecutionResult:
    goal = _clean_required(request.goal, "goal")
    settings = load_project_settings(project_name, workspace_root=workspace_root)
    selected_lane = _clean_optional(request.lane) or settings.default_lane
    if not selected_lane:
        return UiActionExecutionResult(
            status="FAIL",
            action_id=action.id,
            message="No lane provided and no project default lane configured.",
            project=project_name,
            suggested_next_command=f"devo project settings-set --project {project_name} --default-lane <lane>",
        )

    package = start_work_package(project_name=project_name, lane_id=selected_lane, goal=goal, workspace_root=workspace_root)
    artifact_path = None
    if not request.no_template:
        template = generate_work_scope_template(project_name=project_name, run_id=package.run_id, workspace_root=workspace_root)
        artifact_path = template.template_path
    return UiActionExecutionResult(
        status="OK",
        action_id=action.id,
        message="Created Devo run and work-package draft under the Devo workspace.",
        project=project_name,
        run_id=package.run_id,
        lane=package.lane,
        artifact_path=artifact_path,
        suggested_next_command=f"devo work resume --project {project_name} --run {package.run_id}",
    )


def _require_project_name(project_name: str | None) -> str:
    if not project_name or not project_name.strip():
        raise ValueError("project is required for this UI action.")
    return project_name.strip()


def _require_run_id(run_id: str | None, action_id: str) -> str:
    if not run_id or not run_id.strip():
        raise ValueError(f"run_id is required for {action_id}.")
    return run_id.strip()


def _clean_required(value: str | None, field_name: str) -> str:
    cleaned = _clean_optional(value)
    if not cleaned:
        raise ValueError(f"{field_name} is required for this UI action.")
    return cleaned


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
