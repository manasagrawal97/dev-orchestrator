from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.approvals import (
    DevoApprovalBundleStatus,
    DevoApprovalStatus,
    approve_approval_bundle,
    create_approval_bundle,
    get_approval_bundle,
    load_approval_ledger,
    reject_approval,
)
from devo.main import app
from devo.validation_registry import add_validation_command
from devo.work_packages import WorkPackageStatus, import_work_scope, load_work_package, start_work_package
from tests.test_work_packages import _scope_file, _workspace

runner = CliRunner()


def test_approval_bundle_request_creates_normal_child_approvals(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)

    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    ledger = load_approval_ledger("sample", package.run_id, workspace_root=workspace)

    assert bundle.status == DevoApprovalBundleStatus.PENDING
    assert len(bundle.child_approval_ids) == 2
    child_actions = {ledger.approvals[approval_id].action_type for approval_id in bundle.child_approval_ids}
    assert child_actions == {"target_repo_code_edit", "target_repo_build"}
    assert all(ledger.approvals[approval_id].status == DevoApprovalStatus.PENDING for approval_id in bundle.child_approval_ids)


def test_bundle_approve_approves_all_child_approvals(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)

    approved = approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", note="approved", workspace_root=workspace)
    ledger = load_approval_ledger("sample", package.run_id, workspace_root=workspace)
    updated_package = load_work_package("sample", package.run_id, workspace_root=workspace)

    assert approved.status == DevoApprovalBundleStatus.APPROVED
    assert updated_package.status == WorkPackageStatus.APPROVED
    assert all(ledger.approvals[approval_id].status == DevoApprovalStatus.APPROVED for approval_id in bundle.child_approval_ids)


def test_bundle_status_reflects_rejected_child_approval(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)

    reject_approval("sample", package.run_id, bundle.child_approval_ids[0], rejected_by="reviewer", note="too broad", workspace_root=workspace)
    refreshed = get_approval_bundle("sample", package.run_id, bundle.bundle_id, workspace_root=workspace)

    assert refreshed.status == DevoApprovalBundleStatus.REJECTED


def test_bundle_approve_refuses_rejected_child_approval(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    reject_approval("sample", package.run_id, bundle.child_approval_ids[0], rejected_by="reviewer", note="too broad", workspace_root=workspace)

    with pytest.raises(ValueError, match="child approval is rejected"):
        approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)


def test_bundle_approval_authorizes_registered_build_validation(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    _replace_build_command_with_python(workspace)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)

    result = runner.invoke(
        app,
        [
            "validation",
            "run",
            "--project",
            "sample",
            "--run",
            package.run_id,
            "--task",
            "T001",
            "--id",
            "dotnet-build-personalos",
            "--allow-disabled",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "PASSED validation run" in result.output
    assert "Approval ID:" in result.output


def test_bundle_request_cli_reports_approve_command(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)

    result = runner.invoke(
        app,
        ["work", "request-approval-bundle", "--project", "sample", "--run", package.run_id, "--task", "T001"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Approval bundle:" in result.output
    assert "devo approval bundle-approve" in result.output


def test_approval_bundle_artifacts_are_written(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    bundle_dir = workspace / "runs" / "sample" / package.run_id / "artifacts" / "approval-bundles"

    assert (bundle_dir / f"approval-bundle-{bundle.bundle_id}.json").exists()
    markdown = (bundle_dir / f"approval-bundle-{bundle.bundle_id}.md").read_text(encoding="utf-8")
    assert "## Child Approvals" in markdown
    assert "target_repo_build" in markdown


def _prepared_package(workspace: Path, tmp_path: Path):
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    import_work_scope("sample", package.run_id, _scope_file(tmp_path), workspace_root=workspace)
    return load_work_package("sample", package.run_id, workspace_root=workspace)


def _replace_build_command_with_python(workspace: Path) -> None:
    command = f'{sys.executable} -c "print(\'bundle build ok\')"'
    add_validation_command(
        "sample",
        "dotnet-build-personalos",
        "Build PersonalOS",
        command,
        "build",
        risk="high",
        approval_required=True,
        enabled=False,
        replace=True,
        workspace_root=workspace,
    )
