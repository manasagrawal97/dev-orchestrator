from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.approvals import (
    DevoApprovalStatus,
    approval_artifact_paths,
    approve_approval,
    create_approval_request,
    find_matching_approved_approval,
    get_approval_status,
    reject_approval,
    scope_fingerprint_for_policy,
)
from devo.main import app
from devo.policy import check_policy
from devo.schemas import RunArtifactType, RunStatus
from tests.test_policy import _policy_workspace
from tests.test_workflow import _workspace

runner = CliRunner()


def test_approval_request_creates_pending_approval_for_high_risk_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)

    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", reason="needed", workspace_root=workspace)

    assert record.status == DevoApprovalStatus.PENDING
    assert record.approval_required is True
    assert record.blocked is False
    assert record.risk_level == "high"


def test_approval_request_creates_blocked_approval_for_critical_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run rm -rf during broad recursive delete."})

    record = create_approval_request("sample", "run-1", "T001", "cleanup", workspace_root=workspace)

    assert record.status == DevoApprovalStatus.BLOCKED
    assert record.blocked is True
    assert record.risk_level == "critical"


def test_approval_approve_changes_pending_to_approved(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)

    approved = approve_approval("sample", "run-1", record.approval_id, approved_by="tester", note="ok", workspace_root=workspace)

    assert approved.status == DevoApprovalStatus.APPROVED
    assert approved.approved_by == "tester"
    assert approved.approval_note == "ok"


def test_approval_approve_refuses_blocked_request(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run rm -rf during broad recursive delete."})
    record = create_approval_request("sample", "run-1", "T001", "cleanup", workspace_root=workspace)

    result = runner.invoke(
        app,
        ["approval", "approve", "--project", "sample", "--run", "run-1", "--approval", record.approval_id, "--by", "tester"],
    )

    assert result.exit_code != 0
    assert "Blocked approval requests cannot be approved." in result.output


def test_approval_reject_changes_pending_to_rejected(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)

    rejected = reject_approval("sample", "run-1", record.approval_id, rejected_by="tester", note="no", workspace_root=workspace)

    assert rejected.status == DevoApprovalStatus.REJECTED
    assert rejected.rejected_by == "tester"
    assert rejected.rejection_note == "no"


def test_approval_status_lists_approvals(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)

    result = runner.invoke(app, ["approval", "status", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert record.approval_id in result.output
    assert "Status: pending" in result.output


def test_approval_ledger_is_created_and_updated(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)
    approve_approval("sample", "run-1", record.approval_id, approved_by="tester", workspace_root=workspace)
    paths = approval_artifact_paths(record, workspace_root=workspace)
    data = json.loads(paths["ledger"].read_text(encoding="utf-8"))

    assert paths["ledger"].exists()
    assert data["approvals"][record.approval_id]["status"] == "approved"


def test_approval_md_and_json_files_are_written(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)
    paths = approval_artifact_paths(record, workspace_root=workspace)

    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert record.approval_id in paths["markdown"].read_text(encoding="utf-8")


def test_scope_fingerprint_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    policy = check_policy("sample", "run-1", "T001", action_type="implementation_prompt", workspace_root=workspace)

    first = scope_fingerprint_for_policy(policy)
    second = scope_fingerprint_for_policy(policy)

    assert first == second


def test_changed_task_scope_does_not_match_old_approval(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)
    approve_approval("sample", "run-1", record.approval_id, approved_by="tester", workspace_root=workspace)
    _write_tasks(workspace, {"T001": "Modify target project source and run git push."})

    match = find_matching_approved_approval("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)

    assert match is None


def test_workflow_next_high_risk_recommends_approval_request_when_not_approved(tmp_path: Path, monkeypatch) -> None:
    _high_risk_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Action type: approval_required" in result.output
    assert "devo approval request" in result.output


def test_workflow_batch_high_risk_stops_with_approval_required_when_not_approved(tmp_path: Path, monkeypatch) -> None:
    _high_risk_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["workflow", "batch", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Stop reason: INCONSISTENT_STATE" in result.output
    assert "approval_required" in result.output


def test_workflow_next_high_risk_proceeds_after_matching_approval(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)
    approve_approval("sample", "run-1", record.approval_id, approved_by="tester", workspace_root=workspace)

    result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Agent: ImplementationCoordinatorAgent" in result.output
    assert f"Policy approval {record.approval_id}" in result.output


def test_critical_task_stays_blocked_even_if_approval_exists(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Run rm -rf during broad recursive delete."})

    result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Action type: blocked" in result.output
    assert "Policy gate blocked critical risk task T001" in result.output


def test_low_risk_task_does_not_require_approval(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})

    result = check_policy("sample", "run-1", "T001", action_type="implementation_prompt", workspace_root=workspace)

    assert result.approval_required is False
    assert result.allowed is True


def test_medium_risk_task_warns_but_does_not_require_approval(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify DevOrchestrator source code in src/devo."})

    result = check_policy("sample", "run-1", "T001", action_type="implementation_prompt", workspace_root=workspace)

    assert result.risk_level == "medium"
    assert result.approval_required is False
    assert result.allowed is True


def test_unknown_approval_id_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _high_risk_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["approval", "status", "--project", "sample", "--run", "run-1", "--approval", "missing"])

    assert result.exit_code != 0
    assert "Approval request not found: missing" in result.output


def test_unknown_task_run_project_fail_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    missing_project = runner.invoke(app, ["approval", "request", "--project", "missing", "--run", "run-1", "--task", "T001", "--action", "implementation_prompt"])
    _high_risk_workspace(tmp_path, monkeypatch)
    missing_run = runner.invoke(app, ["approval", "request", "--project", "sample", "--run", "missing", "--task", "T001", "--action", "implementation_prompt"])
    missing_task = runner.invoke(app, ["approval", "request", "--project", "sample", "--run", "run-1", "--task", "missing", "--action", "implementation_prompt"])

    assert missing_project.exit_code != 0
    assert "Registered project not found: missing" in missing_project.output
    assert missing_run.exit_code != 0
    assert "Run not found: missing" in missing_run.output
    assert missing_task.exit_code != 0
    assert "Task id not found in tasks.md: missing" in missing_task.output


def test_approval_commands_do_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace = _high_risk_workspace(tmp_path, monkeypatch)
    project_path = Path(json.loads((workspace / "projects" / "sample" / "project.json").read_text(encoding="utf-8"))["path"])
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    record = create_approval_request("sample", "run-1", "T001", "implementation_prompt", workspace_root=workspace)
    approve_approval("sample", "run-1", record.approval_id, approved_by="tester", workspace_root=workspace)
    get_approval_status("sample", "run-1", workspace_root=workspace)

    assert sentinel.read_text(encoding="utf-8") == before


def test_approval_commands_are_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo approval request" in readme
    assert "devo approval approve" in readme
    assert "devo approval reject" in readme
    assert "devo approval status" in readme


def _high_risk_workspace(tmp_path: Path, monkeypatch) -> Path:
    return _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})


def _write_tasks(workspace: Path, task_bodies: dict[str, str]) -> None:
    sections = []
    for task_id, body in task_bodies.items():
        sections.append("\n".join([f"## Task {task_id}", "", f"- task title: {body}", f"- objective: {body}", ""]))
    (workspace / "runs" / "sample" / "run-1" / "artifacts" / "tasks.md").write_text("\n".join(sections), encoding="utf-8")
