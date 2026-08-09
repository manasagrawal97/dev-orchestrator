from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from devo.api import create_app
from devo.delivery import (
    commit_delivery_report,
    create_delivery_plan,
    list_delivery_checks,
    prepare_delivery_report,
    preview_delivery_commit,
    preview_delivery_push,
    push_delivery_report,
    run_delivery_readiness_check,
)
from devo.main import app
from devo.project_planning import (
    ExecutionQueue,
    QueueItem,
    ValidationEvidence,
    WorkerReview,
    WorkerRun,
    queue_artifact_paths,
    worker_review_artifact_paths,
    worker_run_artifact_paths,
)
from devo.read_models import build_project_overview
from devo.schemas import ContextState, ContextStatus, ProjectRegistration

runner = CliRunner()


def test_delivery_check_ready_for_clean_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["delivery", "check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Readiness: ready" in result.output
    assert "Git status: clean" in result.output


def test_delivery_check_write_creates_json_markdown_and_index(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["delivery", "check", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0, result.output
    delivery_dir = workspace / "projects" / "sample" / "delivery"
    payload = json.loads((delivery_dir / "del-0001.json").read_text(encoding="utf-8"))
    assert payload["delivery_id"] == "DEL-0001"
    assert payload["readiness_status"] == "ready"
    assert (delivery_dir / "del-0001.md").exists()
    index = json.loads((delivery_dir / "delivery-index.json").read_text(encoding="utf-8"))
    assert index["checks"][0]["delivery_id"] == "DEL-0001"
    assert list_delivery_checks("sample", workspace_root=workspace)[0].delivery_id == "DEL-0001"


def test_delivery_check_blocks_forbidden_staged_paths(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")
    (repo / "workspace" / "artifact.txt").parent.mkdir()
    (repo / "workspace" / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    _git(repo, "add", ".env", "workspace/artifact.txt")

    result = runner.invoke(app, ["delivery", "check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Readiness: blocked" in result.output
    assert "Forbidden delivery paths are staged" in result.output
    assert "Workspace artifacts are staged" in result.output
    assert ".env" in result.output


def test_delivery_check_blocks_when_linked_queue_item_not_completed(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _write_queue(workspace, status="running")

    check, _json_path, _markdown_path = run_delivery_readiness_check(
        "sample",
        queue_id="QUEUE-001",
        item_id="ITEM-001",
        workspace_root=workspace,
    )

    assert check.target_repo_path == str(repo)
    assert check.readiness_status == "blocked"
    assert check.queue_item_status == "running"
    assert any("not completed" in blocker for blocker in check.blockers)


def test_delivery_check_accepts_completed_queue_item_with_passed_review(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _write_queue(workspace, status="completed")
    _write_worker_run_and_review(workspace, review_status="reviewed_passed", validation_status="passed")

    check, _json_path, _markdown_path = run_delivery_readiness_check(
        "sample",
        queue_id="QUEUE-001",
        item_id="ITEM-001",
        workspace_root=workspace,
    )

    assert check.readiness_status == "ready"
    assert check.source_worker_run_id == "WORKER-001"
    assert check.source_review_id == "REV-WORKER-001"
    assert check.review_status == "reviewed_passed"
    assert check.validation_evidence_status == "passed"


def test_delivery_check_blocks_failed_validation_evidence(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _write_queue(workspace, status="completed")
    _write_worker_run_and_review(workspace, review_status="reviewed_passed", validation_status="failed")

    check, _json_path, _markdown_path = run_delivery_readiness_check(
        "sample",
        queue_id="QUEUE-001",
        item_id="ITEM-001",
        workspace_root=workspace,
    )

    assert check.readiness_status == "blocked"
    assert any("validation evidence status is failed" in blocker for blocker in check.blockers)


def test_delivery_list_and_show_commands_read_written_artifact(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    created = runner.invoke(app, ["delivery", "check", "--project", "sample", "--write"], terminal_width=240)

    listed = runner.invoke(app, ["delivery", "list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["delivery", "show", "--project", "sample", "--delivery", "DEL-0001"], terminal_width=240)

    assert created.exit_code == 0, created.output
    assert listed.exit_code == 0, listed.output
    assert "DEL-0001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Delivery ID: DEL-0001" in shown.output


def test_delivery_plan_creates_json_markdown_from_readiness_check(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    result = runner.invoke(
        app,
        ["delivery", "plan", "--project", "sample", "--delivery", "DEL-0001", "--message", "feat: deliver safely"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Delivery plan: DEL-0001" in result.output
    delivery_dir = workspace / "projects" / "sample" / "delivery"
    payload = json.loads((delivery_dir / "delivery-plan-del-0001.json").read_text(encoding="utf-8"))
    assert payload["source_delivery_check_id"] == "DEL-0001"
    assert payload["intended_commit_message"] == "feat: deliver safely"
    assert payload["delivery_status"] == "planned"
    assert payload["approval_status"] == "not_requested"
    assert (delivery_dir / "delivery-plan-del-0001.md").exists()


def test_delivery_plan_from_blocked_check_has_blocked_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _write_queue(workspace, status="running")
    run_delivery_readiness_check("sample", queue_id="QUEUE-001", item_id="ITEM-001", write=True, workspace_root=workspace)

    plan, _json_path, _markdown_path = create_delivery_plan("sample", "DEL-0001", "fix: blocked plan", workspace_root=workspace)

    assert plan.readiness_status == "blocked"
    assert plan.delivery_status == "blocked"
    assert plan.blockers


def test_delivery_plan_list_and_show_commands_work(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)

    listed = runner.invoke(app, ["delivery", "plan-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["delivery", "plan-show", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "DEL-0001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Intended commit message: feat: deliver safely" in shown.output


def test_delivery_approval_request_show_and_list_work(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)

    requested = runner.invoke(
        app,
        ["delivery", "approval-request", "--project", "sample", "--plan", "DEL-0001", "--note", "Please review"],
        terminal_width=240,
    )
    shown = runner.invoke(app, ["delivery", "approval-show", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)
    listed = runner.invoke(app, ["delivery", "approval-list", "--project", "sample"], terminal_width=240)

    assert requested.exit_code == 0, requested.output
    assert "Approval status: requested" in requested.output
    approval = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-approval-del-0001.json").read_text(encoding="utf-8"))
    assert approval["approval_status"] == "requested"
    assert approval["decision_note"] == "Please review"
    assert shown.exit_code == 0, shown.output
    assert "Approval status: requested" in shown.output
    assert listed.exit_code == 0, listed.output
    assert "DEL-0001" in listed.output


def test_delivery_approve_succeeds_for_ready_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)
    runner.invoke(app, ["delivery", "approval-request", "--project", "sample", "--plan", "DEL-0001", "--note", "review"], terminal_width=240)

    result = runner.invoke(
        app,
        ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "Approved"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Approval status: approved" in result.output
    assert "Next: prepare a delivery report" in result.output
    plan = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-plan-del-0001.json").read_text(encoding="utf-8"))
    assert plan["approval_status"] == "approved"
    assert plan["delivery_status"] == "approved"


def test_delivery_approve_refuses_blocked_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _write_queue(workspace, status="running")
    run_delivery_readiness_check("sample", queue_id="QUEUE-001", item_id="ITEM-001", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "fix: blocked plan", workspace_root=workspace)

    result = runner.invoke(
        app,
        ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "Approved"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Blocked delivery plans cannot be approved" in result.output


def test_delivery_reject_marks_plan_and_approval_rejected(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)

    result = runner.invoke(
        app,
        ["delivery", "reject", "--project", "sample", "--plan", "DEL-0001", "--reviewer", "Manas", "--note", "Not ready"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Approval status: rejected" in result.output
    plan = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-plan-del-0001.json").read_text(encoding="utf-8"))
    approval = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-approval-del-0001.json").read_text(encoding="utf-8"))
    assert plan["delivery_status"] == "rejected"
    assert approval["approval_status"] == "rejected"


def test_delivery_report_prepare_creates_json_markdown_from_approved_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_approved_plan(workspace)

    result = runner.invoke(app, ["delivery", "report-prepare", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Delivery report: DEL-0001" in result.output
    assert "Commit ready: True" in result.output
    payload = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.json").read_text(encoding="utf-8"))
    assert payload["source_delivery_plan_id"] == "DEL-0001"
    assert payload["proposed_commit_message"] == "feat: deliver safely"
    assert payload["final_status"] == "ready"
    assert payload["commit_ready"] is True
    assert payload["push_ready"] is False
    assert (workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.md").exists()


def test_delivery_report_prepare_blocks_unapproved_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "report-prepare", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "is not approved" in result.output


def test_delivery_report_prepare_reflects_current_blocked_readiness(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_approved_plan(workspace)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")

    report, _json_path, _markdown_path = prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    assert report.final_status == "blocked"
    assert report.commit_ready is False
    assert "Forbidden delivery paths are changed" in report.blocker_summary


def test_delivery_report_list_and_show_commands_work(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_approved_plan(workspace)
    prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    listed = runner.invoke(app, ["delivery", "report-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["delivery", "report-show", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert "DEL-0001" in listed.output
    assert shown.exit_code == 0, shown.output
    assert "Proposed commit message: feat: deliver safely" in shown.output


def test_delivery_commit_message_prints_proposed_message(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "commit-message", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "feat: deliver safely"


def test_project_overview_includes_delivery_summary(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)
    runner.invoke(
        app,
        ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "Approved"],
        terminal_width=240,
    )
    prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    overview = build_project_overview("sample", workspace_root=workspace)

    assert overview.delivery_check_count == 1
    assert overview.latest_delivery_id == "DEL-0001"
    assert overview.latest_delivery_readiness_status == "ready"
    assert overview.latest_delivery_blocker_count == 0
    assert overview.delivery_plan_count == 1
    assert overview.latest_delivery_plan_id == "DEL-0001"
    assert overview.latest_delivery_plan_status == "approved"
    assert overview.latest_delivery_approval_status == "approved"
    assert overview.delivery_report_count == 1
    assert overview.latest_delivery_report_id == "DEL-0001"
    assert overview.latest_delivery_report_status == "ready"
    assert overview.latest_delivery_commit_ready is True
    assert overview.latest_delivery_push_ready is False


def test_api_exposes_delivery_checks_plans_and_approvals(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)
    runner.invoke(app, ["delivery", "approval-request", "--project", "sample", "--plan", "DEL-0001", "--note", "review"], terminal_width=240)
    runner.invoke(app, ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "approved"], terminal_width=240)
    prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    checks = client.get("/api/projects/sample/delivery-checks")
    check = client.get("/api/projects/sample/delivery-checks/DEL-0001")
    missing_check = client.get("/api/projects/sample/delivery-checks/DEL-9999")
    plans = client.get("/api/projects/sample/delivery-plans")
    plan = client.get("/api/projects/sample/delivery-plans/DEL-0001")
    approvals = client.get("/api/projects/sample/delivery-approvals")
    approval = client.get("/api/projects/sample/delivery-plans/DEL-0001/approval")
    reports = client.get("/api/projects/sample/delivery-reports")
    report = client.get("/api/projects/sample/delivery-reports/DEL-0001")

    assert checks.status_code == 200
    assert checks.json()["count"] == 1
    assert check.status_code == 200
    assert check.json()["delivery_id"] == "DEL-0001"
    assert missing_check.status_code == 404
    assert plans.status_code == 200
    assert plans.json()["count"] == 1
    assert plan.status_code == 200
    assert plan.json()["intended_commit_message"] == "feat: deliver safely"
    assert approvals.status_code == 200
    assert approvals.json()["count"] == 1
    assert approval.status_code == 200
    assert approval.json()["approval_status"] == "approved"
    assert reports.status_code == 200
    assert reports.json()["count"] == 1
    assert report.status_code == 200
    assert report.json()["proposed_commit_message"] == "feat: deliver safely"


def test_delivery_check_does_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    result = runner.invoke(app, ["delivery", "check", "--project", "sample"], terminal_width=240)
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.exit_code == 0, result.output
    assert after == before


def test_delivery_plan_and_approval_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    plan = runner.invoke(
        app,
        ["delivery", "plan", "--project", "sample", "--delivery", "DEL-0001", "--message", "feat: deliver safely"],
        terminal_width=240,
    )
    request = runner.invoke(
        app,
        ["delivery", "approval-request", "--project", "sample", "--plan", "DEL-0001", "--note", "review"],
        terminal_width=240,
    )
    approve = runner.invoke(
        app,
        ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "approved"],
        terminal_width=240,
    )
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert plan.exit_code == 0, plan.output
    assert request.exit_code == 0, request.output
    assert approve.exit_code == 0, approve.output
    assert after == before


def test_delivery_report_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)
    runner.invoke(app, ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "approved"], terminal_width=240)
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    prepare = runner.invoke(app, ["delivery", "report-prepare", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)
    shown = runner.invoke(app, ["delivery", "report-show", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)
    message = runner.invoke(app, ["delivery", "commit-message", "--project", "sample", "--plan", "DEL-0001"], terminal_width=240)
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert prepare.exit_code == 0, prepare.output
    assert shown.exit_code == 0, shown.output
    assert message.exit_code == 0, message.output
    assert after == before


def test_delivery_commit_preview_shows_eligible_files_without_staging(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    result = runner.invoke(app, ["delivery", "commit-preview", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.exit_code == 0, result.output
    assert "Commit ready: True" in result.output
    assert "changed.txt" in result.output
    assert after == before


def test_delivery_commit_refuses_without_confirm_commit(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    result = runner.invoke(app, ["delivery", "commit", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "--confirm-commit is required" in result.output


def test_delivery_commit_refuses_unapproved_delivery_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    plan_path = workspace / "projects" / "sample" / "delivery" / "delivery-plan-del-0001.json"
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    payload["approval_status"] = "not_requested"
    plan_path.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(
        app,
        ["delivery", "commit", "--project", "sample", "--report", "DEL-0001", "--confirm-commit"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "not approved" in result.output


def test_delivery_commit_refuses_blocked_delivery_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_approved_plan(workspace)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")
    prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    result = runner.invoke(
        app,
        ["delivery", "commit", "--project", "sample", "--report", "DEL-0001", "--confirm-commit"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "not ready" in result.output or "not commit-ready" in result.output


def test_delivery_commit_refuses_forbidden_changed_files(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")

    preview = preview_delivery_commit("sample", "DEL-0001", workspace_root=workspace)

    assert preview.commit_ready is False
    assert ".env" in preview.blocked_files
    assert any("Forbidden delivery paths are changed" in blocker for blocker in preview.blockers)


def test_delivery_commit_refuses_staged_workspace_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    (repo / "workspace").mkdir()
    (repo / "workspace" / "artifact.txt").write_text("artifact\n", encoding="utf-8")
    _git(repo, "add", "workspace/artifact.txt")

    preview = preview_delivery_commit("sample", "DEL-0001", workspace_root=workspace)

    assert preview.commit_ready is False
    assert "workspace/artifact.txt" in preview.blocked_files
    assert any("Workspace artifacts are staged" in blocker for blocker in preview.blockers)


def test_delivery_commit_refuses_staged_secret_risk_file(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")
    _git(repo, "add", ".env")

    preview = preview_delivery_commit("sample", "DEL-0001", workspace_root=workspace)

    assert preview.commit_ready is False
    assert ".env" in preview.blocked_files
    assert any("Secret-risk files or signals" in blocker for blocker in preview.blockers)


def test_delivery_commit_refuses_when_no_eligible_changes(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_ready_report(workspace)

    preview = preview_delivery_commit("sample", "DEL-0001", workspace_root=workspace)

    assert preview.commit_ready is False
    assert "No commit-eligible changed files were found." in preview.blockers


def test_delivery_commit_stages_only_eligible_files_and_creates_commit(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    result = runner.invoke(
        app,
        ["delivery", "commit", "--project", "sample", "--report", "DEL-0001", "--confirm-commit"],
        terminal_width=240,
    )
    status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    report_payload = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.json").read_text(encoding="utf-8"))
    commit_payload = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-commit-del-0001.json").read_text(encoding="utf-8"))
    overview = build_project_overview("sample", workspace_root=workspace)

    assert result.exit_code == 0, result.output
    assert "Commit status: committed" in result.output
    assert status == ""
    assert report_payload["final_status"] == "committed"
    assert report_payload["commit_ready"] is False
    assert report_payload["pushed"] is False
    assert report_payload["commit_hash"]
    assert commit_payload["status"] == "committed"
    assert commit_payload["eligible_files"] == ["changed.txt"]
    assert overview.latest_delivery_commit_hash == report_payload["commit_hash"]
    assert overview.latest_delivery_commit_status == "committed"
    assert overview.latest_delivery_pushed is False
    assert _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout.strip() == "2"


def test_delivery_commit_does_not_push(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    ahead = _git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}", capture=True).stdout.strip()

    assert result.status == "committed"
    assert ahead.startswith("1")


def test_delivery_commit_failure_is_captured_safely(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    def fake_run_git(_repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["add"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:1] == ["commit"]:
            return subprocess.CompletedProcess(args, 1, "", "commit failed")
        return subprocess.CompletedProcess(args, 0, "HEAD", "")

    monkeypatch.setattr("devo.delivery._run_git", fake_run_git)

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)

    assert result.status == "failed"
    assert result.returncode == 1
    assert "commit failed" in result.stderr


def test_api_exposes_delivery_commit_result(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/delivery-reports/DEL-0001/commit")

    assert response.status_code == 200
    assert response.json()["status"] == "committed"
    assert response.json()["commit_hash"]


def test_delivery_push_preview_shows_target_without_pushing(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    before = _git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}", capture=True).stdout.strip()

    result = runner.invoke(app, ["delivery", "push-preview", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)
    after = _git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}", capture=True).stdout.strip()

    assert result.exit_code == 0, result.output
    assert "Push allowed: True" in result.output
    assert "Push target: origin main" in result.output
    assert before.startswith("1")
    assert after == before


def test_delivery_push_refuses_without_confirm_push(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)

    result = runner.invoke(app, ["delivery", "push", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)

    assert result.exit_code != 0
    assert "--confirm-push is required" in result.output


def test_delivery_push_refuses_missing_commit_hash(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_ready_report(workspace)

    preview = preview_delivery_push("sample", "DEL-0001", workspace_root=workspace)

    assert preview.push_allowed is False
    assert any("has no commit hash" in blocker for blocker in preview.blockers)


def test_delivery_push_refuses_already_pushed_delivery(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)

    result = runner.invoke(
        app,
        ["delivery", "push", "--project", "sample", "--report", "DEL-0001", "--confirm-push"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "already pushed" in result.output


def test_delivery_push_refuses_missing_remote(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    _git(repo, "remote", "remove", "origin")

    preview = preview_delivery_push("sample", "DEL-0001", workspace_root=workspace)

    assert preview.push_allowed is False
    assert any("Git remote was not found" in blocker for blocker in preview.blockers)


def test_delivery_push_refuses_unknown_branch(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)

    preview = preview_delivery_push("sample", "DEL-0001", branch_override="missing-branch", workspace_root=workspace)

    assert preview.push_allowed is False
    assert any("Git branch was not found" in blocker for blocker in preview.blockers)


def test_delivery_push_refuses_commit_hash_not_contained_in_branch(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    report_path = workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["commit_hash"] = "0" * 40
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    preview = preview_delivery_push("sample", "DEL-0001", workspace_root=workspace)

    assert preview.push_allowed is False
    assert any("not contained" in blocker for blocker in preview.blockers)


def test_delivery_push_succeeds_to_local_bare_remote_and_updates_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    before_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout.strip()

    result = runner.invoke(
        app,
        ["delivery", "push", "--project", "sample", "--report", "DEL-0001", "--confirm-push"],
        terminal_width=240,
    )
    after_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout.strip()
    ahead = _git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}", capture=True).stdout.strip()
    report_payload = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.json").read_text(encoding="utf-8"))
    push_payload = json.loads((workspace / "projects" / "sample" / "delivery" / "delivery-push-del-0001.json").read_text(encoding="utf-8"))
    overview = build_project_overview("sample", workspace_root=workspace)

    assert result.exit_code == 0, result.output
    assert "Push status: pushed" in result.output
    assert before_count == after_count
    assert ahead.startswith("0")
    assert report_payload["pushed"] is True
    assert report_payload["push_remote"] == "origin"
    assert report_payload["push_branch"] == "main"
    assert report_payload["push_status"] == "pushed"
    assert report_payload["final_status"] == "pushed"
    assert push_payload["push_status"] == "pushed"
    assert push_payload["pushed"] is True
    assert overview.latest_delivery_push_status == "pushed"
    assert overview.latest_delivery_push_remote == "origin"
    assert overview.latest_delivery_push_branch == "main"
    assert overview.latest_delivery_pushed_at


def test_delivery_push_show_command_works(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "push-show", "--project", "sample", "--delivery", "DEL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Push status: pushed" in result.output


def test_delivery_push_does_not_stage_unstage_or_create_commits(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    (repo / "leftover.txt").write_text("leftover\n", encoding="utf-8")
    before_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    before_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout

    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)
    after_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    after_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout

    assert before_status == "?? leftover.txt\n"
    assert after_status == before_status
    assert after_count == before_count


def test_api_exposes_delivery_push_result(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    response = client.get("/api/projects/sample/delivery-reports/DEL-0001/push")

    assert response.status_code == 200
    assert response.json()["push_status"] == "pushed"
    assert response.json()["pushed"] is True


def _workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    repo = _repo(tmp_path)
    repo.mkdir()
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main")
    project_dir = workspace / "projects" / "sample"
    project_dir.mkdir(parents=True)
    registration = ProjectRegistration(name="sample", path=repo, looks_like_software_project=True, detected_markers=["README.md"])
    (project_dir / "project.json").write_text(registration.model_dump_json(indent=2), encoding="utf-8")
    context_dir = project_dir / "context"
    context_dir.mkdir(parents=True)
    context = ContextState(project_name="sample", project_path=repo, status=ContextStatus.CONTEXT_APPROVED)
    (context_dir / "context-state.json").write_text(context.model_dump_json(indent=2), encoding="utf-8")
    return workspace, repo


def _create_approved_plan(workspace: Path) -> None:
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", "DEL-0001", "feat: deliver safely", workspace_root=workspace)
    result = runner.invoke(
        app,
        ["delivery", "approve", "--project", "sample", "--plan", "DEL-0001", "--approver", "Manas", "--note", "Approved"],
        terminal_width=240,
    )
    assert result.exit_code == 0, result.output


def _create_ready_report(workspace: Path) -> None:
    _create_approved_plan(workspace)
    report, _json_path, _markdown_path = prepare_delivery_report("sample", "DEL-0001", workspace_root=workspace)
    assert report.final_status == "ready"
    assert report.commit_ready is True


def _create_committed_report(workspace: Path) -> None:
    repo = _repo(workspace.parent)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    assert result.status == "committed"
    assert result.commit_hash


def _write_queue(workspace: Path, status: str) -> None:
    now = datetime.now(UTC)
    item = QueueItem(
        item_id="ITEM-001",
        task_id="T001",
        title="Deliver safely",
        lane="devo-internal-source",
        risk_level="low",
        status=status,
        batch_id="BATCH-001",
        completed_at=now if status == "completed" else None,
    )
    queue = ExecutionQueue(
        project="sample",
        queue_id="QUEUE-001",
        title="Queue",
        source_batch_id="BATCH-001",
        source_backlog_reference="backlog",
        status="completed" if status == "completed" else "running",
        items=[item],
        item_count=1,
        completed_count=1 if status == "completed" else 0,
        running_count=1 if status == "running" else 0,
        created_at=now,
        updated_at=now,
    )
    json_path, _markdown_path = queue_artifact_paths("sample", "QUEUE-001", workspace_root=workspace)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(queue.model_dump_json(indent=2), encoding="utf-8")


def _write_worker_run_and_review(workspace: Path, *, review_status: str, validation_status: str) -> None:
    now = datetime.now(UTC)
    repo = _repo(workspace.parent)
    worker_run = WorkerRun(
        project="sample",
        worker_run_id="WORKER-001",
        source_queue_id="QUEUE-001",
        source_queue_item_id="ITEM-001",
        source_task_id="T001",
        title="Worker",
        status="completed",
        prompt_path=str(workspace / "prompt.md"),
        target_repo_path=str(repo),
        created_at=now,
        updated_at=now,
    )
    run_json, _run_md = worker_run_artifact_paths("sample", "WORKER-001", workspace_root=workspace)
    run_json.parent.mkdir(parents=True, exist_ok=True)
    run_json.write_text(worker_run.model_dump_json(indent=2), encoding="utf-8")
    review = WorkerReview(
        project="sample",
        review_id="REV-WORKER-001",
        worker_run_id="WORKER-001",
        source_queue_id="QUEUE-001",
        source_queue_item_id="ITEM-001",
        source_task_id="T001",
        review_status=review_status,
        validation_evidence=ValidationEvidence(validation_status=validation_status, validation_summary="checked"),
        created_at=now,
        updated_at=now,
    )
    review_json, _review_md = worker_review_artifact_paths("sample", "WORKER-001", workspace_root=workspace)
    review_json.parent.mkdir(parents=True, exist_ok=True)
    review_json.write_text(review.model_dump_json(indent=2), encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def _git(cwd: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=capture, text=True)
