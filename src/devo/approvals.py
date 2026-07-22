from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .policy import PolicyCheckResult, check_policy
from .projects import get_workspace_root
from .runs import load_run, run_path
from .work_packages import (
    WorkPackageStatus,
    bundle_id_for_package,
    load_work_package,
    save_work_package,
    validation_command_details,
)

APPROVAL_SCHEMA_VERSION = "1"
APPROVAL_LEDGER_NAME = "approvals-ledger.json"
APPROVAL_BUNDLE_SCHEMA_VERSION = "1"


class DevoApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class DevoApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = APPROVAL_SCHEMA_VERSION
    approval_id: str
    project_name: str
    run_id: str
    task_id: str
    task_title: str
    action_type: str
    risk_level: str
    approval_required: bool
    blocked: bool
    status: DevoApprovalStatus
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requested_reason: str | None = None
    policy_reasons: list[str] = Field(default_factory=list)
    matched_signals: list[str] = Field(default_factory=list)
    safety_exclusion_signals: list[str] = Field(default_factory=list)
    scope_fingerprint: str
    approved_at: datetime | None = None
    approved_by: str | None = None
    approval_note: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    rejection_note: str | None = None


class DevoApprovalLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = APPROVAL_SCHEMA_VERSION
    project_name: str
    run_id: str
    approvals: dict[str, DevoApprovalRecord] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DevoApprovalBundleStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class DevoApprovalBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = APPROVAL_BUNDLE_SCHEMA_VERSION
    bundle_id: str
    project_name: str
    run_id: str
    task_id: str
    work_package_run_id: str
    status: DevoApprovalBundleStatus
    child_approval_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_at: datetime | None = None
    approved_by: str | None = None
    approval_note: str | None = None


def create_approval_request(
    project_name: str,
    run_id: str,
    task_id: str,
    action_type: str,
    reason: str | None = None,
    workspace_root: Path | None = None,
) -> DevoApprovalRecord:
    root = workspace_root or get_workspace_root()
    load_run(project_name, run_id, workspace_root=root)
    policy = check_policy(project_name, run_id, task_id, action_type=action_type, workspace_root=root)
    requested_at = datetime.now(UTC)
    approval_id = _approval_id(policy, requested_at)
    status = DevoApprovalStatus.BLOCKED if policy.blocked else DevoApprovalStatus.PENDING
    record = DevoApprovalRecord(
        approval_id=approval_id,
        project_name=project_name,
        run_id=run_id,
        task_id=task_id,
        task_title=_task_title(policy),
        action_type=policy.action_type,
        risk_level=policy.risk_level,
        approval_required=policy.approval_required,
        blocked=policy.blocked,
        status=status,
        requested_at=requested_at,
        requested_reason=reason,
        policy_reasons=policy.reasons,
        matched_signals=policy.matched_risk_signals,
        safety_exclusion_signals=policy.safety_exclusion_signals,
        scope_fingerprint=scope_fingerprint_for_policy(policy),
    )
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    ledger.approvals[approval_id] = record
    save_approval_record(record, ledger, workspace_root=root)
    return record


def create_approval_bundle(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> DevoApprovalBundle:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    if not package.validation_commands:
        msg = "Work package must include a validation command before requesting an approval bundle."
        raise ValueError(msg)
    command_id, command_text = validation_command_details(project_name, package.validation_commands[0], workspace_root=root)
    created_at = datetime.now(UTC)
    bundle_id = bundle_id_for_package(project_name, run_id, task_id, created_at)
    scope_summary = _work_package_scope_summary(package)
    source = create_approval_request(
        project_name,
        run_id,
        task_id,
        "target_repo_code_edit",
        reason=f"Approval bundle {bundle_id} source edit child. {scope_summary}",
        workspace_root=root,
    )
    build = create_approval_request(
        project_name,
        run_id,
        task_id,
        "target_repo_build",
        reason=(
            f"Approval bundle {bundle_id} build validation child. "
            f"Validate with registered command {command_id}: {command_text}. "
            f"No source edits during validation. {scope_summary}"
        ),
        workspace_root=root,
    )
    bundle = DevoApprovalBundle(
        bundle_id=bundle_id,
        project_name=project_name,
        run_id=run_id,
        task_id=task_id,
        work_package_run_id=package.run_id,
        status=_derive_bundle_status([source, build]),
        child_approval_ids=[source.approval_id, build.approval_id],
        created_at=created_at,
    )
    save_approval_bundle(bundle, workspace_root=root)
    package = package.model_copy(update={"approval_bundle_id": bundle.bundle_id, "status": WorkPackageStatus.APPROVAL_REQUESTED})
    save_work_package(package, workspace_root=root)
    return bundle


def get_approval_bundle(
    project_name: str,
    run_id: str,
    bundle_id: str,
    workspace_root: Path | None = None,
) -> DevoApprovalBundle:
    root = workspace_root or get_workspace_root()
    load_run(project_name, run_id, workspace_root=root)
    path = _approval_bundle_path(root, project_name, run_id, bundle_id)
    if not path.exists():
        msg = f"Approval bundle not found: {bundle_id}"
        raise ValueError(msg)
    data = json.loads(path.read_text(encoding="utf-8"))
    bundle = DevoApprovalBundle.model_validate(data)
    return refresh_approval_bundle_status(bundle, workspace_root=root)


def approve_approval_bundle(
    project_name: str,
    run_id: str,
    bundle_id: str,
    approved_by: str,
    note: str | None = None,
    workspace_root: Path | None = None,
) -> DevoApprovalBundle:
    root = workspace_root or get_workspace_root()
    bundle = get_approval_bundle(project_name, run_id, bundle_id, workspace_root=root)
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    children = [_require_approval(ledger, child_id) for child_id in bundle.child_approval_ids]
    if any(child.status == DevoApprovalStatus.REJECTED for child in children):
        msg = "Approval bundle cannot be approved because a child approval is rejected."
        raise ValueError(msg)
    if any(child.blocked or child.status == DevoApprovalStatus.BLOCKED for child in children):
        msg = "Approval bundle cannot be approved because a child approval is blocked."
        raise ValueError(msg)
    for child in children:
        if child.status == DevoApprovalStatus.PENDING:
            approve_approval(project_name, run_id, child.approval_id, approved_by=approved_by, note=note, workspace_root=root)
    updated = bundle.model_copy(
        update={
            "status": DevoApprovalBundleStatus.APPROVED,
            "approved_at": datetime.now(UTC),
            "approved_by": approved_by,
            "approval_note": note,
            "updated_at": datetime.now(UTC),
        }
    )
    save_approval_bundle(updated, workspace_root=root)
    try:
        package = load_work_package(project_name, run_id, workspace_root=root)
        if package.approval_bundle_id == bundle_id:
            save_work_package(package.model_copy(update={"status": WorkPackageStatus.APPROVED}), workspace_root=root)
    except ValueError:
        pass
    return updated


def approve_approval(
    project_name: str,
    run_id: str,
    approval_id: str,
    approved_by: str,
    note: str | None = None,
    workspace_root: Path | None = None,
) -> DevoApprovalRecord:
    root = workspace_root or get_workspace_root()
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    record = _require_approval(ledger, approval_id)
    if record.status == DevoApprovalStatus.BLOCKED or record.blocked:
        msg = "Blocked approval requests cannot be approved."
        raise ValueError(msg)
    if record.status != DevoApprovalStatus.PENDING:
        msg = f"Only pending approval requests can be approved. Current status: {record.status.value}"
        raise ValueError(msg)
    updated = record.model_copy(
        update={
            "status": DevoApprovalStatus.APPROVED,
            "approved_at": datetime.now(UTC),
            "approved_by": approved_by,
            "approval_note": note,
        }
    )
    ledger.approvals[approval_id] = updated
    save_approval_record(updated, ledger, workspace_root=root)
    return updated


def reject_approval(
    project_name: str,
    run_id: str,
    approval_id: str,
    rejected_by: str,
    note: str | None = None,
    workspace_root: Path | None = None,
) -> DevoApprovalRecord:
    root = workspace_root or get_workspace_root()
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    record = _require_approval(ledger, approval_id)
    if record.status != DevoApprovalStatus.PENDING:
        msg = f"Only pending approval requests can be rejected. Current status: {record.status.value}"
        raise ValueError(msg)
    updated = record.model_copy(
        update={
            "status": DevoApprovalStatus.REJECTED,
            "rejected_at": datetime.now(UTC),
            "rejected_by": rejected_by,
            "rejection_note": note,
        }
    )
    ledger.approvals[approval_id] = updated
    save_approval_record(updated, ledger, workspace_root=root)
    return updated


def refresh_approval_bundle_status(bundle: DevoApprovalBundle, workspace_root: Path | None = None) -> DevoApprovalBundle:
    root = workspace_root or get_workspace_root()
    ledger = load_approval_ledger(bundle.project_name, bundle.run_id, workspace_root=root)
    children = [_require_approval(ledger, child_id) for child_id in bundle.child_approval_ids]
    status = _derive_bundle_status(children)
    updated = bundle.model_copy(update={"status": status, "updated_at": datetime.now(UTC)})
    if updated != bundle:
        save_approval_bundle(updated, workspace_root=root)
    return updated


def get_approval_status(
    project_name: str,
    run_id: str,
    approval_id: str | None = None,
    workspace_root: Path | None = None,
) -> list[DevoApprovalRecord]:
    ledger = load_approval_ledger(project_name, run_id, workspace_root=workspace_root)
    if approval_id:
        return [_require_approval(ledger, approval_id)]
    return sorted(ledger.approvals.values(), key=lambda item: item.requested_at)


def find_matching_approved_approval(
    project_name: str,
    run_id: str,
    task_id: str,
    action_type: str,
    workspace_root: Path | None = None,
) -> DevoApprovalRecord | None:
    root = workspace_root or get_workspace_root()
    policy = check_policy(project_name, run_id, task_id, action_type=action_type, workspace_root=root)
    fingerprint = scope_fingerprint_for_policy(policy)
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    for approval in ledger.approvals.values():
        if (
            approval.task_id == task_id
            and approval.action_type == policy.action_type
            and approval.scope_fingerprint == fingerprint
            and approval.status == DevoApprovalStatus.APPROVED
            and not approval.blocked
        ):
            return approval
    return None


def scope_fingerprint_for_policy(policy: PolicyCheckResult) -> str:
    payload = {
        "project_name": policy.project_name,
        "run_id": policy.run_id,
        "task_id": policy.task_id,
        "task_title": _task_title(policy),
        "action_type": policy.action_type,
        "risk_level": policy.risk_level,
        "policy_reasons": policy.reasons,
        "matched_signals": policy.matched_risk_signals,
        "safety_exclusion_signals": policy.safety_exclusion_signals,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_approval_ledger(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> DevoApprovalLedger:
    root = workspace_root or get_workspace_root()
    load_run(project_name, run_id, workspace_root=root)
    ledger_path = _approvals_dir(root, project_name, run_id) / APPROVAL_LEDGER_NAME
    if not ledger_path.exists():
        return DevoApprovalLedger(project_name=project_name, run_id=run_id)
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    return DevoApprovalLedger.model_validate(data)


def save_approval_record(
    record: DevoApprovalRecord,
    ledger: DevoApprovalLedger,
    workspace_root: Path | None = None,
) -> None:
    root = workspace_root or get_workspace_root()
    approvals_dir = _approvals_dir(root, record.project_name, record.run_id)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    ledger.updated_at = datetime.now(UTC)
    (approvals_dir / APPROVAL_LEDGER_NAME).write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    (approvals_dir / f"approval-{record.approval_id}.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
    (approvals_dir / f"approval-{record.approval_id}.md").write_text(_render_approval_markdown(record), encoding="utf-8")


def approval_artifact_paths(record: DevoApprovalRecord, workspace_root: Path | None = None) -> dict[str, Path]:
    root = workspace_root or get_workspace_root()
    approvals_dir = _approvals_dir(root, record.project_name, record.run_id)
    return {
        "ledger": approvals_dir / APPROVAL_LEDGER_NAME,
        "json": approvals_dir / f"approval-{record.approval_id}.json",
        "markdown": approvals_dir / f"approval-{record.approval_id}.md",
    }


def save_approval_bundle(bundle: DevoApprovalBundle, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    directory = _approval_bundles_dir(root, bundle.project_name, bundle.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    bundle = bundle.model_copy(update={"updated_at": datetime.now(UTC)})
    (directory / f"approval-bundle-{bundle.bundle_id}.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    (directory / f"approval-bundle-{bundle.bundle_id}.md").write_text(_render_bundle_markdown(bundle, root), encoding="utf-8")


def approval_bundle_artifact_paths(bundle: DevoApprovalBundle, workspace_root: Path | None = None) -> dict[str, Path]:
    root = workspace_root or get_workspace_root()
    directory = _approval_bundles_dir(root, bundle.project_name, bundle.run_id)
    return {
        "json": directory / f"approval-bundle-{bundle.bundle_id}.json",
        "markdown": directory / f"approval-bundle-{bundle.bundle_id}.md",
    }


def _approval_id(policy: PolicyCheckResult, requested_at: datetime) -> str:
    seed = f"{scope_fingerprint_for_policy(policy)}|{requested_at.isoformat()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _task_title(policy: PolicyCheckResult) -> str:
    # PolicyCheckResult does not carry title; keep the field stable in the fingerprint.
    return f"Task {policy.task_id}"


def _require_approval(ledger: DevoApprovalLedger, approval_id: str) -> DevoApprovalRecord:
    record = ledger.approvals.get(approval_id)
    if not record:
        msg = f"Approval request not found: {approval_id}"
        raise ValueError(msg)
    return record


def _approvals_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / "approvals"


def _approval_bundles_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / "approval-bundles"


def _approval_bundle_path(workspace_root: Path, project_name: str, run_id: str, bundle_id: str) -> Path:
    return _approval_bundles_dir(workspace_root, project_name, run_id) / f"approval-bundle-{bundle_id}.json"


def _render_approval_markdown(record: DevoApprovalRecord) -> str:
    lines = [
        f"# approval-{record.approval_id}",
        "",
        f"- schema_version: {record.schema_version}",
        f"- approval_id: {record.approval_id}",
        f"- project_name: {record.project_name}",
        f"- run_id: {record.run_id}",
        f"- task_id: {record.task_id}",
        f"- task_title: {record.task_title}",
        f"- action_type: {record.action_type}",
        f"- risk_level: {record.risk_level}",
        f"- approval_required: {record.approval_required}",
        f"- blocked: {record.blocked}",
        f"- status: {record.status.value}",
        f"- requested_at: {record.requested_at.isoformat()}",
        f"- requested_reason: {record.requested_reason or 'none'}",
        f"- scope_fingerprint: {record.scope_fingerprint}",
        f"- approved_at: {record.approved_at.isoformat() if record.approved_at else 'none'}",
        f"- approved_by: {record.approved_by or 'none'}",
        f"- approval_note: {record.approval_note or 'none'}",
        f"- rejected_at: {record.rejected_at.isoformat() if record.rejected_at else 'none'}",
        f"- rejected_by: {record.rejected_by or 'none'}",
        f"- rejection_note: {record.rejection_note or 'none'}",
        "",
        "## Policy Reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in record.policy_reasons or ["none"])
    lines.extend(["", "## Matched Signals", ""])
    lines.extend(f"- {signal}" for signal in record.matched_signals or ["none"])
    lines.extend(["", "## Safety Exclusions", ""])
    lines.extend(f"- {signal}" for signal in record.safety_exclusion_signals or ["none"])
    lines.append("")
    return "\n".join(lines)


def _derive_bundle_status(children: list[DevoApprovalRecord]) -> DevoApprovalBundleStatus:
    if any(child.blocked or child.status == DevoApprovalStatus.BLOCKED for child in children):
        return DevoApprovalBundleStatus.BLOCKED
    if any(child.status == DevoApprovalStatus.REJECTED for child in children):
        return DevoApprovalBundleStatus.REJECTED
    if children and all(child.status == DevoApprovalStatus.APPROVED for child in children):
        return DevoApprovalBundleStatus.APPROVED
    return DevoApprovalBundleStatus.PENDING


def _work_package_scope_summary(package: object) -> str:
    fields = [
        f"Goal: {getattr(package, 'goal')}.",
        f"Lane: {getattr(package, 'lane')}.",
        "Files: " + ", ".join(getattr(package, "approved_files")) + ".",
        "Allowed changes: " + ", ".join(getattr(package, "allowed_changes")) + ".",
        "Forbidden changes: " + ", ".join(getattr(package, "forbidden_changes")) + ".",
        "Validation: " + ", ".join(getattr(package, "validation_commands")) + ".",
    ]
    return " ".join(fields)


def _render_bundle_markdown(bundle: DevoApprovalBundle, workspace_root: Path) -> str:
    ledger = load_approval_ledger(bundle.project_name, bundle.run_id, workspace_root=workspace_root)
    lines = [
        f"# approval-bundle-{bundle.bundle_id}",
        "",
        f"- schema_version: {bundle.schema_version}",
        f"- bundle_id: {bundle.bundle_id}",
        f"- project_name: {bundle.project_name}",
        f"- run_id: {bundle.run_id}",
        f"- task_id: {bundle.task_id}",
        f"- status: {bundle.status.value}",
        f"- created_at: {bundle.created_at.isoformat()}",
        f"- updated_at: {bundle.updated_at.isoformat()}",
        f"- approved_at: {bundle.approved_at.isoformat() if bundle.approved_at else 'none'}",
        f"- approved_by: {bundle.approved_by or 'none'}",
        f"- approval_note: {bundle.approval_note or 'none'}",
        "",
        "## Child Approvals",
        "",
    ]
    for child_id in bundle.child_approval_ids:
        child = ledger.approvals.get(child_id)
        if not child:
            lines.append(f"- {child_id}: missing")
            continue
        lines.append(f"- {child.approval_id}: {child.action_type} status={child.status.value} blocked={child.blocked}")
    lines.append("")
    return "\n".join(lines)
