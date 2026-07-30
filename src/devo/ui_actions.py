from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

UiActionCategory = Literal["read_only", "workspace_safe", "approval_required", "dangerous_deferred"]
UiActionStatus = Literal["available", "read_only", "planned", "deferred", "blocked"]
UiRiskLevel = Literal["none", "low", "medium", "high", "critical"]

UI_MODE_READ_ONLY = "read_only"


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
        status="planned",
        reason="Useful UI v2 candidate, but UI v1 remains read-only.",
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
        status="planned",
        reason="Workspace-only generated report; deferred until UI v2 action execution exists.",
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
        status="planned",
        reason="Workspace-only generated report; deferred until UI v2 action execution exists.",
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
        status="planned",
        reason="Workspace-only report write; deferred until UI v2 action execution exists.",
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
        status="planned",
        reason="Creates Devo workspace artifacts only, but is intentionally outside UI v1.",
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
    if ui_mode != UI_MODE_READ_ONLY:
        return False
    return action.allowed_in_ui_v1 and action.category == "read_only" and not action.mutates_workspace and not action.mutates_target_project


def list_allowed_ui_actions(*, ui_mode: str = UI_MODE_READ_ONLY) -> list[UiActionMetadata]:
    return [action for action in ACTION_REGISTRY if is_action_allowed(action, ui_mode=ui_mode)]
