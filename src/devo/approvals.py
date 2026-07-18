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

APPROVAL_SCHEMA_VERSION = "1"
APPROVAL_LEDGER_NAME = "approvals-ledger.json"


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
        scope_fingerprint=scope_fingerprint_for_policy(policy),
    )
    ledger = load_approval_ledger(project_name, run_id, workspace_root=root)
    ledger.approvals[approval_id] = record
    save_approval_record(record, ledger, workspace_root=root)
    return record


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
    lines.append("")
    return "\n".join(lines)
