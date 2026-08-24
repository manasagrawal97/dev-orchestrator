from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from devo.api import create_app
from devo.delivery import (
    build_delivery_latest_summary,
    commit_delivery_report,
    create_delivery_plan,
    approve_delivery_plan,
    create_delivery_runner_request,
    load_delivery_runner_request,
    load_delivery_runner_run,
    load_delivery_report,
    list_delivery_checks,
    list_delivery_runner_watches,
    prepare_delivery_report,
    preview_delivery_commit,
    preview_delivery_push,
    push_delivery_report,
    request_delivery_approval,
    refresh_delivery_report,
    run_delivery_runner_watch,
    run_delivery_commit_diagnostics,
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


def test_delivery_latest_reports_clean_empty_check_as_no_delivery_needed(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)
    summary = build_delivery_latest_summary("sample", workspace_root=workspace)

    assert result.exit_code == 0, result.output
    assert "Latest delivery check: DEL-0001 | ready | empty True" in result.output
    assert "No delivery needed; repository is clean." in result.output
    assert summary.latest_delivery_check_is_empty is True
    assert summary.latest_meaningful_delivery_check_id is None


def test_delivery_latest_distinguishes_latest_check_from_latest_meaningful(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    _git(repo, "add", "changed.txt")
    _git(repo, "commit", "-m", "make repo clean")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest delivery check: DEL-0002 | ready | empty True" in result.output
    assert "Latest meaningful delivery check: DEL-0001" in result.output
    assert "No delivery needed; repository is clean." in result.output


def test_delivery_latest_recommends_plan_for_safe_changes(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest delivery check: DEL-0001" in result.output
    assert "devo delivery plan --project sample --delivery DEL-0001" in result.output


def test_delivery_latest_shows_pending_runner_request_and_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    created = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"],
        terminal_width=240,
    )
    assert created.exit_code == 0, created.output

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest runner request: REQ-0001 | requested" in result.output
    assert "Latest runner run: none | unknown" in result.output
    assert "Latest runner commit: none" in result.output
    assert "Latest runner pushed: unknown" in result.output
    assert "Runner next action:" in result.output
    assert "runner-run --project sample --request REQ-0001" in result.output


def test_delivery_latest_recommends_fixing_blockers(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest delivery check: DEL-0001 | blocked" in result.output
    assert "Fix blockers from DEL-0001" in result.output


def test_delivery_latest_recommends_report_prepare_for_approved_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    create_delivery_plan("sample", check.delivery_id, "feat: deliver", workspace_root=workspace)
    request_delivery_approval("sample", check.delivery_id, "review", workspace_root=workspace)
    approve_delivery_plan("sample", check.delivery_id, "Manas", "approved", workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest plan: DEL-0001 | approved" in result.output
    assert "delivery report-prepare --project sample --plan DEL-0001" in result.output


def test_delivery_latest_recommends_commit_preview_for_ready_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest report: DEL-0001 | ready" in result.output
    assert "delivery commit-preview --project sample --report DEL-0001" in result.output


def test_delivery_latest_recommends_push_preview_for_committed_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest commit result: DEL-0001 | committed" in result.output
    assert "delivery push-preview --project sample --report DEL-0001" in result.output


def test_delivery_latest_reports_pushed_delivery_as_completed(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest push result: DEL-0001 | pushed" in result.output
    assert "Latest pushed delivery: DEL-0001" in result.output
    assert "Delivery completed and pushed" in result.output


def test_delivery_latest_json_output_and_read_only(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    before_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    before_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout

    result = runner.invoke(app, ["delivery", "latest", "--project", "sample", "--json"], terminal_width=240)
    after_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    after_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout
    payload = json.loads(result.output)

    assert result.exit_code == 0, result.output
    assert payload["latest_delivery_check_id"] == "DEL-0001"
    assert "delivery plan --project sample --delivery DEL-0001" in payload["next_action"]
    assert after_status == before_status
    assert after_count == before_count


def test_delivery_runner_request_creates_snapshot_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner", "--note", "TASK"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Runner request: REQ-0001" in result.output
    assert "runner-run --project sample --request REQ-0001" in result.output
    assert "Next normal PowerShell command:" in result.output
    assert "Changed file count: 1" in result.output
    assert "Warnings count:" in result.output
    assert "Blockers count: 0" in result.output
    assert "Request artifact path:" in result.output
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert request is not None
    assert request.expected_changed_files == ["changed.txt"]
    overview = build_project_overview("sample", workspace_root=workspace)
    assert overview.latest_runner_request_id == "REQ-0001"
    assert overview.latest_runner_request_status == "requested"
    assert overview.latest_runner_run_id is None
    assert overview.latest_runner_commit_hash is None
    assert overview.latest_runner_pushed is None
    assert "runner-run --project sample --request REQ-0001" in (overview.latest_runner_next_action or "")
    request_dir = workspace / "projects" / "sample" / "delivery" / "runner-requests"
    assert (request_dir / "runner-request-req-0001.json").exists()
    assert (request_dir / "runner-request-req-0001.md").exists()
    assert (request_dir / "runner-request-index.json").exists()


def test_delivery_runner_request_refuses_clean_repo_by_default(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch)

    try:
        create_delivery_runner_request("sample", "feat: trusted runner", "", workspace_root=workspace)
    except ValueError as exc:
        assert "Target repository is clean" in str(exc)
    else:
        raise AssertionError("Expected clean repo runner request to be refused.")


def test_delivery_runner_request_allows_clean_repo_with_explicit_flag(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "chore: empty", "--allow-empty-request"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert request is not None
    assert request.expected_changed_files == []


def test_delivery_runner_request_refuses_forbidden_changed_files(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "workspace").mkdir()
    (repo / "workspace" / "artifact.md").write_text("artifact\n", encoding="utf-8")

    try:
        create_delivery_runner_request("sample", "feat: trusted runner", "", workspace_root=workspace)
    except ValueError as exc:
        assert "Forbidden delivery paths are changed" in str(exc)
    else:
        raise AssertionError("Expected forbidden path runner request to be refused.")


def test_delivery_runner_request_refuses_secret_risk_blockers(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / ".env").write_text("TOKEN=value\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Secret-risk files or signals" in result.output


def test_delivery_runner_request_allows_documentation_secret_warnings(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    docs = repo / "docs"
    docs.mkdir()
    (docs / "delivery.md").write_text("Document how secrets are handled without values.\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "docs: update delivery docs"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert request is not None
    assert request.expected_changed_files == ["docs/delivery.md"]
    assert request.warnings


def test_delivery_runner_list_and_show_work(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    created = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"],
        terminal_width=240,
    )
    assert created.exit_code == 0, created.output

    listed = runner.invoke(app, ["delivery", "runner-list", "--project", "sample"], terminal_width=240)
    shown = runner.invoke(app, ["delivery", "runner-show", "--project", "sample", "--request", "REQ-0001"], terminal_width=240)

    assert listed.exit_code == 0, listed.output
    assert shown.exit_code == 0, shown.output
    assert "REQ-0001 | requested" in listed.output
    assert "Expected changed files: 1" in shown.output


def test_delivery_runner_latest_shows_no_request_cleanly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["delivery", "runner-latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest runner request: none" in result.output
    assert "Expected changed files: 0" in result.output
    assert "No runner action needed" in result.output


def test_delivery_runner_latest_shows_pending_request_and_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)

    result = runner.invoke(app, ["delivery", "runner-latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Latest runner request: REQ-0001 | requested" in result.output
    assert "Expected changed files: 1" in result.output
    assert "Latest runner run: none" in result.output
    assert "Commit hash: none" in result.output
    assert "Pushed: False" in result.output
    assert "runner-run --project sample --request REQ-0001" in result.output


def test_delivery_runner_run_refuses_without_confirmation(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)

    result = runner.invoke(
        app,
        ["delivery", "runner-run", "--project", "sample", "--request", "REQ-0001", "--approver", "Manas"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "--confirm-runner-delivery is required" in result.output


def test_delivery_runner_run_blocks_before_staging_if_index_lock_probe_fails(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)

    def fake_probe(_repo_path: Path):
        from devo.delivery import IndexLockProbeResult

        return IndexLockProbeResult(
            ok=False,
            category="index_lock_permission_denied",
            message="Permission denied creating .git/index.lock",
            lock_path=str(repo / ".git" / "index.lock"),
        )

    monkeypatch.setattr("devo.delivery._probe_git_index_lock", fake_probe)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-run",
            "--project",
            "sample",
            "--request",
            "REQ-0001",
            "--approver",
            "Manas",
            "--confirm-runner-delivery",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run = load_delivery_runner_run("sample", "REQ-0001", workspace_root=workspace)
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert request is not None
    assert run.status == "blocked"
    assert request.status == "requested"
    assert run.delivery_check_id is None
    assert "Permission denied creating .git/index.lock" in result.output
    assert _git(repo, "diff", "--cached", "--name-only", capture=True).stdout.strip() == ""


def test_delivery_runner_run_blocks_if_changed_files_differ_from_snapshot(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)
    (repo / "extra.txt").write_text("extra\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-run",
            "--project",
            "sample",
            "--request",
            "REQ-0001",
            "--approver",
            "Manas",
            "--confirm-runner-delivery",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run = load_delivery_runner_run("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "blocked"
    assert any("Current changed files differ" in blocker for blocker in run.blockers)
    assert _git(repo, "diff", "--cached", "--name-only", capture=True).stdout.strip() == ""


def test_delivery_runner_run_completes_guarded_commit_and_push(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    created = runner.invoke(
        app,
        ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner", "--note", "approved batch"],
        terminal_width=240,
    )
    assert created.exit_code == 0, created.output

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-run",
            "--project",
            "sample",
            "--request",
            "REQ-0001",
            "--approver",
            "Manas",
            "--confirm-runner-delivery",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Trusted delivery runner completed." in result.output
    assert "Repo should now be clean." in result.output
    assert "Next check: git status" in result.output
    run = load_delivery_runner_run("sample", "REQ-0001", workspace_root=workspace)
    request = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert request is not None
    assert run.status == "completed"
    assert run.commit_hash
    assert run.pushed is True
    assert request.status == "completed"
    assert _git(repo, "status", "--short", capture=True).stdout.strip() == ""
    remote_ref = _git(repo, "ls-remote", "origin", "refs/heads/main", capture=True).stdout
    assert run.commit_hash in remote_ref
    overview = build_project_overview("sample", workspace_root=workspace)
    assert overview.latest_runner_request_id == "REQ-0001"
    assert overview.latest_runner_request_status == "completed"
    assert overview.latest_runner_run_id == run.run_id
    assert overview.latest_runner_run_status == "completed"
    assert overview.latest_runner_commit_hash == run.commit_hash
    assert overview.latest_runner_pushed is True

    latest = runner.invoke(app, ["delivery", "runner-latest", "--project", "sample"], terminal_width=240)
    assert latest.exit_code == 0, latest.output
    assert "Latest runner request: REQ-0001 | completed" in latest.output
    assert "Final status: completed" in latest.output
    assert "Pushed: True" in latest.output

    delivery_latest = runner.invoke(app, ["delivery", "latest", "--project", "sample"], terminal_width=240)
    assert delivery_latest.exit_code == 0, delivery_latest.output
    assert "Latest runner request: REQ-0001 | completed" in delivery_latest.output
    assert "Latest runner run: RUN-" in delivery_latest.output
    assert "Latest runner pushed: True" in delivery_latest.output


def test_delivery_runner_run_does_not_push_if_commit_fails(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)
    push_called = False
    import devo.delivery as delivery_module

    real_run_git = delivery_module._run_git

    def fake_run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        nonlocal push_called
        if args[:1] == ["commit"]:
            return subprocess.CompletedProcess(args, 1, "", "commit failed")
        if args[:1] == ["push"]:
            push_called = True
        return real_run_git(repo_path, args)

    monkeypatch.setattr("devo.delivery._run_git", fake_run_git)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-run",
            "--project",
            "sample",
            "--request",
            "REQ-0001",
            "--approver",
            "Manas",
            "--confirm-runner-delivery",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run = load_delivery_runner_run("sample", "REQ-0001", workspace_root=workspace)
    assert run is not None
    assert run.status == "failed"
    assert push_called is False
    assert run.pushed is False


def test_delivery_runner_watch_refuses_without_confirmation(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)

    result = runner.invoke(
        app,
        ["delivery", "runner-watch", "--project", "sample", "--approver", "Manas", "--once"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Refusing to run trusted runner watch without --confirm-runner-watch." in result.output


def test_delivery_runner_watch_requires_approver(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["delivery", "runner-watch", "--project", "sample", "--once", "--confirm-runner-watch"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output
    assert "--approver" in result.output


def test_delivery_runner_watch_no_pending_exits_cleanly(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Pending requests: 0" in result.output
    assert "Status: no_pending" in result.output
    assert "No pending runner requests." in result.output
    watches = list_delivery_runner_watches("sample", workspace_root=workspace)
    assert len(watches) == 1
    assert watches[0].status == "no_pending"
    assert watches[0].selected_request_id is None
    assert _git(repo, "status", "--short", capture=True).stdout.strip() == ""
    assert _git(repo, "diff", "--cached", "--name-only", capture=True).stdout.strip() == ""


def test_delivery_runner_watch_selects_oldest_requested_request(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    create_delivery_runner_request("sample", "feat: first", "", workspace_root=workspace)
    create_delivery_runner_request("sample", "feat: second", "", workspace_root=workspace)

    watch, _json_path, _markdown_path = run_delivery_runner_watch(
        "sample",
        approver="Manas",
        once=True,
        confirm_runner_watch=True,
        workspace_root=workspace,
    )

    assert watch.status == "completed"
    assert watch.pending_request_count == 2
    assert watch.selected_request_id == "REQ-0001"
    assert watch.selected_run_id
    assert watch.commit_hash
    assert watch.pushed is True
    first = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    second = load_delivery_runner_request("sample", "REQ-0002", workspace_root=workspace)
    assert first is not None
    assert second is not None
    assert first.status == "completed"
    assert second.status == "requested"


def test_delivery_runner_watch_completes_guarded_commit_and_push(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted watch"], terminal_width=240)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Pending requests: 1" in result.output
    assert "Selected request: REQ-0001" in result.output
    assert "Status: completed" in result.output
    assert "Pushed: True" in result.output
    assert "Trusted runner watch completed one request." in result.output
    watch = list_delivery_runner_watches("sample", workspace_root=workspace)[0]
    run = load_delivery_runner_run("sample", "REQ-0001", workspace_root=workspace)
    assert watch.status == "completed"
    assert run is not None
    assert watch.selected_run_id == run.run_id
    assert watch.delivery_id == run.delivery_report_id
    assert watch.commit_hash == run.commit_hash
    assert watch.pushed is True
    assert _git(repo, "status", "--short", capture=True).stdout.strip() == ""
    remote_ref = _git(repo, "ls-remote", "origin", "refs/heads/main", capture=True).stdout
    assert watch.commit_hash in remote_ref


def test_delivery_runner_watch_stops_after_one_request(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    create_delivery_runner_request("sample", "feat: first", "", workspace_root=workspace)
    create_delivery_runner_request("sample", "feat: second", "", workspace_root=workspace)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    first = load_delivery_runner_request("sample", "REQ-0001", workspace_root=workspace)
    second = load_delivery_runner_request("sample", "REQ-0002", workspace_root=workspace)
    assert first is not None
    assert second is not None
    assert first.status == "completed"
    assert second.status == "requested"


def test_delivery_runner_watch_does_not_process_non_requested_requests(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    from devo.delivery import write_delivery_runner_request

    completed, _json_path, _markdown_path = create_delivery_runner_request("sample", "feat: done", "", workspace_root=workspace)
    cancelled, _json_path, _markdown_path = create_delivery_runner_request("sample", "feat: cancelled", "", workspace_root=workspace)
    failed, _json_path, _markdown_path = create_delivery_runner_request("sample", "feat: failed", "", workspace_root=workspace)
    create_delivery_runner_request("sample", "feat: pending", "", workspace_root=workspace)
    for request, status in [(completed, "completed"), (cancelled, "cancelled"), (failed, "failed")]:
        write_delivery_runner_request(request.model_copy(update={"status": status, "updated_at": datetime.now(UTC)}), workspace_root=workspace)

    watch, _watch_json, _watch_md = run_delivery_runner_watch(
        "sample",
        approver="Manas",
        once=True,
        confirm_runner_watch=True,
        workspace_root=workspace,
    )

    assert watch.pending_request_count == 1
    assert watch.selected_request_id == "REQ-0004"
    statuses = {
        request_id: load_delivery_runner_request("sample", request_id, workspace_root=workspace).status  # type: ignore[union-attr]
        for request_id in ["REQ-0001", "REQ-0002", "REQ-0003"]
    }
    assert statuses == {"REQ-0001": "completed", "REQ-0002": "cancelled", "REQ-0003": "failed"}


def test_delivery_runner_watch_blocks_when_snapshot_changes(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    runner.invoke(app, ["delivery", "runner-request", "--project", "sample", "--message", "feat: trusted runner"], terminal_width=240)
    (repo / "extra.txt").write_text("extra\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Status: blocked" in result.output
    assert "Current changed files differ" in result.output
    watch = list_delivery_runner_watches("sample", workspace_root=workspace)[0]
    assert watch.status == "blocked"
    assert watch.selected_request_id == "REQ-0001"
    assert any("Current changed files differ" in blocker for blocker in watch.blockers)
    assert _git(repo, "diff", "--cached", "--name-only", capture=True).stdout.strip() == ""


def test_delivery_runner_watch_latest_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )

    result = runner.invoke(app, ["delivery", "runner-watch-latest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Runner watch: WATCH-" in result.output
    assert result.output.count("Project: sample") == 1
    assert "Status: no_pending" in result.output


def test_delivery_runner_watch_latest_explains_newer_pending_request_after_no_pending_watch(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "delivery",
            "runner-watch",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--once",
            "--confirm-runner-watch",
        ],
        terminal_width=240,
    )
    (repo / "changed-after-watch.txt").write_text("new request\n", encoding="utf-8")
    request, _json_path, _markdown_path = create_delivery_runner_request("sample", "docs: newer request", "", workspace_root=workspace)

    result = runner.invoke(app, ["delivery", "runner-watch-latest", "--project", "sample"], terminal_width=240)

    assert request.status == "requested"
    assert result.exit_code == 0, result.output
    assert "Status: no_pending" in result.output
    assert "latest runner request is newer than this no-pending watch" in result.output
    assert "Latest requested item: REQ-0001" in result.output
    assert "delivery runner-run --project sample --request REQ-0001" in result.output


def test_delivery_runner_schedule_plan_prints_without_installing(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-plan",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--interval-minutes",
            "5",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Scheduled task: DevoTrustedRunner-sample" in result.output
    assert "runner-watch --project sample --approver Manas --once --confirm-runner-watch" in result.output
    assert not (workspace / "projects" / "sample" / "delivery" / "runner-schedule").exists()


def test_delivery_runner_schedule_install_refuses_without_confirmation(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--interval-minutes",
            "5",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "--confirm-install is required." in result.output


def test_delivery_runner_schedule_install_dry_run_does_not_call_scheduler(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)

    def fail_scheduler(_args: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError("scheduler should not be called for dry-run")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fail_scheduler)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--interval-minutes",
            "5",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Scheduled trusted runner dry-run prepared." in result.output
    schedule_dir = workspace / "projects" / "sample" / "delivery" / "runner-schedule"
    config = json.loads((schedule_dir / "runner-schedule-config.json").read_text(encoding="utf-8"))
    status = json.loads((schedule_dir / "runner-schedule-status.json").read_text(encoding="utf-8"))
    wrapper = (schedule_dir / "runner-watch-sample.cmd").read_text(encoding="utf-8")
    assert config["task_name"] == "DevoTrustedRunner-sample"
    assert config["enabled"] is False
    assert config["last_action"] == "install_dry_run"
    assert status["installed"] is False
    assert "delivery runner-watch --project sample --approver Manas --once --confirm-runner-watch" in wrapper


def test_delivery_runner_schedule_install_writes_config_status_and_defaults_disabled(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--interval-minutes",
            "5",
            "--confirm-install",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    schedule_dir = workspace / "projects" / "sample" / "delivery" / "runner-schedule"
    config = json.loads((schedule_dir / "runner-schedule-config.json").read_text(encoding="utf-8"))
    status = json.loads((schedule_dir / "runner-schedule-status.json").read_text(encoding="utf-8"))
    assert config["enabled"] is False
    assert config["last_action"] == "install"
    assert status["installed"] is True
    assert status["enabled"] is False
    assert any("/Create" in call for call in calls)
    assert any("/DISABLE" in call for call in calls)


def test_delivery_runner_schedule_install_enable_flag_enables_task(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    calls: list[list[str]] = []

    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--interval-minutes",
            "5",
            "--enable",
            "--confirm-install",
        ],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    config = json.loads(
        (workspace / "projects" / "sample" / "delivery" / "runner-schedule" / "runner-schedule-config.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["enabled"] is True
    assert any("/ENABLE" in call for call in calls)


def test_delivery_runner_schedule_status_handles_missing_schedule_gracefully(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["delivery", "runner-schedule-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Installed: False" in result.output
    assert "Health: not_installed" in result.output
    assert "Latest watch: none" in result.output


def test_delivery_runner_schedule_status_reports_healthy_when_installed_and_enabled(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--enable",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        output = "\n".join(
            [
                "TaskName: DevoTrustedRunner-sample",
                "Scheduled Task State: Enabled",
                "Last Run Time: 2026-08-24 10:00:00",
                "Next Run Time: 2026-08-24 10:05:00",
                "Last Result: 0",
            ]
        )
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(app, ["delivery", "runner-schedule-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Installed: True" in result.output
    assert "Enabled: True" in result.output
    assert "Health: healthy" in result.output
    assert "Task query source: schtasks.exe" in result.output
    assert "Environment note: none" in result.output
    assert "Repair commands:" not in result.output


def test_delivery_runner_schedule_status_reports_disabled_when_installed_but_disabled(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--enable",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "Scheduled Task State: Disabled\n", "")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(app, ["delivery", "runner-schedule-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Installed: True" in result.output
    assert "Enabled: False" in result.output
    assert "Health: disabled" in result.output
    assert "runner-schedule-enable --project sample --confirm-enable" in result.output


def test_delivery_runner_schedule_status_reports_drift_when_enabled_metadata_task_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--enable",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "ERROR: The system cannot find the file specified.")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(app, ["delivery", "runner-schedule-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Installed: False" in result.output
    assert "Enabled: False" in result.output
    assert "Health: drift" in result.output
    assert "metadata says enabled" in result.output
    assert "Possible cause: scheduled task is missing, or this process cannot see Windows scheduled tasks." in result.output
    assert "Process user:" in result.output
    assert "Working directory:" in result.output
    assert "Task query source: schtasks.exe" in result.output
    assert "Task query result: ERROR: The system cannot find the file specified." in result.output
    assert "Codex/sandbox may have restricted scheduled-task visibility" in result.output
    assert "Normal PowerShell verification:" in result.output
    assert "runner-schedule-status --project sample" in result.output
    assert "runner-schedule-doctor --project sample" in result.output
    assert "do not reinstall repeatedly" in result.output
    assert "runner-schedule-install --project sample" in result.output
    assert "runner-schedule-enable --project sample --confirm-enable" in result.output


def test_delivery_runner_schedule_status_reports_not_installed_when_disabled_metadata_task_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "ERROR: The system cannot find the file specified.")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(app, ["delivery", "runner-schedule-status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Installed: False" in result.output
    assert "Health: not_installed" in result.output
    assert "runner-schedule-install --project sample" in result.output


def test_delivery_runner_schedule_doctor_reports_health_read_only(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    before = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file())

    result = runner.invoke(app, ["delivery", "runner-schedule-doctor", "--project", "sample"], terminal_width=240)

    after = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file())
    assert result.exit_code == 0, result.output
    assert "Runner schedule doctor" in result.output
    assert "Health: not_installed" in result.output
    assert "Read-only: no scheduler changes were made." in result.output
    assert "Doctor result: scheduled task is not installed." in result.output
    assert after == before


def test_delivery_runner_schedule_doctor_reports_drift_environment_guidance(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--enable",
            "--dry-run",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output
    before = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file())

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "ERROR: Access is denied.")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)

    result = runner.invoke(app, ["delivery", "runner-schedule-doctor", "--project", "sample"], terminal_width=240)

    after = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*") if path.is_file())
    assert result.exit_code == 0, result.output
    assert "Runner schedule doctor" in result.output
    assert "Health: drift" in result.output
    assert "Task query result: ERROR: Access is denied." in result.output
    assert "Verify from normal PowerShell before reinstalling" in result.output
    assert "Normal PowerShell verification:" in result.output
    assert "Doctor result: scheduler metadata drift detected" in result.output
    assert after == before


def test_delivery_runner_schedule_confirmation_guards(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    commands = [
        ["delivery", "runner-schedule-enable", "--project", "sample"],
        ["delivery", "runner-schedule-disable", "--project", "sample"],
        ["delivery", "runner-schedule-run-now", "--project", "sample"],
        ["delivery", "runner-schedule-remove", "--project", "sample"],
    ]
    expected = ["--confirm-enable", "--confirm-disable", "--confirm-run-now", "--confirm-remove"]
    for command, text in zip(commands, expected, strict=True):
        result = runner.invoke(app, command, terminal_width=240)
        assert result.exit_code != 0
        assert f"{text} is required." in result.output


def test_delivery_runner_schedule_remove_updates_status_safely(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    import devo.delivery as delivery_module

    monkeypatch.setattr(delivery_module.os, "name", "nt", raising=False)

    def fake_scheduler(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr("devo.delivery._run_scheduler_command", fake_scheduler)
    installed = runner.invoke(
        app,
        [
            "delivery",
            "runner-schedule-install",
            "--project",
            "sample",
            "--approver",
            "Manas",
            "--confirm-install",
        ],
        terminal_width=240,
    )
    assert installed.exit_code == 0, installed.output

    result = runner.invoke(
        app,
        ["delivery", "runner-schedule-remove", "--project", "sample", "--confirm-remove"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    status = json.loads(
        (workspace / "projects" / "sample" / "delivery" / "runner-schedule" / "runner-schedule-status.json").read_text(
            encoding="utf-8"
        )
    )
    config = json.loads(
        (workspace / "projects" / "sample" / "delivery" / "runner-schedule" / "runner-schedule-config.json").read_text(
            encoding="utf-8"
        )
    )
    assert status["last_action"] == "remove"
    assert status["installed"] is False
    assert config["enabled"] is False


def test_delivery_check_blocks_runner_schedule_workspace_artifacts(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "src.txt").write_text("source\n", encoding="utf-8")
    schedule_artifact = repo / "workspace" / "projects" / "sample" / "delivery" / "runner-schedule" / "runner-watch.log"
    schedule_artifact.parent.mkdir(parents=True)
    schedule_artifact.write_text("log\n", encoding="utf-8")

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample")

    assert check.readiness_status == "blocked"
    assert "workspace/projects/sample/delivery/runner-schedule/runner-watch.log" in check.changed_files
    assert "workspace/projects/sample/delivery/runner-schedule/runner-watch.log" in check.forbidden_changed_files
    assert any("Forbidden delivery paths are changed" in blocker for blocker in check.blockers)


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
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
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
    assert overview.latest_delivery_readiness_status == "warnings"
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
    assert overview.latest_delivery_summary_status == "pending_changes"
    assert overview.latest_delivery_summary_id == "DEL-0001"
    assert overview.latest_delivery_summary_kind == "delivery_check"
    assert "commit-preview" in (overview.latest_delivery_summary_next_action or "")
    assert overview.current_repo_has_pending_changes is True
    assert overview.latest_meaningful_delivery_id == "DEL-0001"


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


def test_delivery_check_treats_readme_secret_terms_as_warning_only(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "README.md").write_text(
        "Do not commit secrets, .env files, API keys, tokens, or passwords. Use <api-key> or your-token-here examples only.\n",
        encoding="utf-8",
    )

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert check.blockers == []
    assert check.secrets_risk_files == []
    assert check.secret_warning_files == ["README.md"]
    assert check.readiness_status == "warnings"
    assert any("Documentation-only secret terms detected" in warning for warning in check.warnings)


def test_delivery_check_treats_docs_secret_terms_as_warning_only(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    docs = repo / "docs"
    docs.mkdir()
    (docs / "delivery.md").write_text(
        "Secret-risk files are blocked. Placeholder token examples such as redacted, dummy, xxxx, and **** are not real values.\n",
        encoding="utf-8",
    )

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert check.blockers == []
    assert check.secrets_risk_files == []
    assert check.secret_warning_files == ["docs/delivery.md"]
    assert check.readiness_status == "warnings"


def test_delivery_check_blocks_readme_with_real_looking_api_token(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    token = "sk-proj-" + "1234567890abcdef1234567890abcdef"
    (repo / "README.md").write_text(
        f"Do not publish this example:\nOPENAI_API_KEY={token}\n",
        encoding="utf-8",
    )

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert "README.md" in check.secrets_risk_files
    assert check.secret_warning_files == []
    assert any("Secret-risk files or signals" in blocker for blocker in check.blockers)
    assert check.readiness_status == "blocked"


def test_delivery_check_blocks_readme_with_private_key(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    private_key_start = "-----BEGIN " + "PRIVATE KEY-----"
    private_key_end = "-----END " + "PRIVATE KEY-----"
    (repo / "README.md").write_text(
        f"Bad example:\n{private_key_start}\nnot-real-but-high-confidence\n{private_key_end}\n",
        encoding="utf-8",
    )

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert "README.md" in check.secrets_risk_files
    assert check.readiness_status == "blocked"


def test_delivery_check_blocks_secret_file_paths(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "cert.pem").write_text("not a real cert\n", encoding="utf-8")
    (repo / "deploy.key").write_text("not a real key\n", encoding="utf-8")

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert "cert.pem" in check.forbidden_changed_files
    assert "deploy.key" in check.forbidden_changed_files
    assert "cert.pem" in check.secrets_risk_files
    assert "deploy.key" in check.secrets_risk_files
    assert check.readiness_status == "blocked"


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
    assert "push-preview" in result.output
    assert "future TASK-DEVO-109" not in result.output
    assert status == ""
    assert report_payload["final_status"] == "committed"
    assert report_payload["commit_ready"] is False
    assert report_payload["pushed"] is False
    assert report_payload["commit_hash"]
    assert report_payload["readiness_currentness"] == "historical_snapshot"
    assert "Historical readiness snapshot" in report_payload["readiness_snapshot_note"]
    assert commit_payload["status"] == "committed"
    assert "push-preview" in commit_payload["next_action"]
    assert "future" not in commit_payload["next_action"].lower()
    assert commit_payload["eligible_files"] == ["changed.txt"]
    assert overview.latest_delivery_commit_hash == report_payload["commit_hash"]
    assert overview.latest_delivery_commit_status == "committed"
    assert overview.latest_delivery_pushed is False
    assert _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout.strip() == "2"


def test_delivery_report_markdown_labels_historical_snapshot_after_commit(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    markdown = (workspace / "projects" / "sample" / "delivery" / "delivery-report-del-0001.md").read_text(encoding="utf-8")

    assert "Readiness currentness: `historical_snapshot`" in markdown
    assert "Historical readiness snapshot; run delivery check for current repo state." in markdown


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
        if args[:2] == ["rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(args, 0, ".git", "")
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


def test_delivery_commit_failure_classifies_index_lock_permission_denied(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    def fake_run_git(_repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(args, 0, ".git", "")
        if args[:1] == ["add"]:
            return subprocess.CompletedProcess(
                args,
                128,
                "",
                "fatal: Unable to create 'E:/DevOrchestrator/.git/index.lock': Permission denied",
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("devo.delivery._run_git", fake_run_git)

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    report = load_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    assert result.status == "failed"
    assert result.failure_category == "index_lock_permission_denied"
    assert result.failure_retryable is True
    assert report is not None
    assert report.final_status == "blocked"
    assert report.last_commit_failure_category == "index_lock_permission_denied"
    assert report.last_commit_failure_retryable is True
    assert "report-refresh" in report.next_action


def test_delivery_commit_failure_classifies_index_lock_exists_as_retryable(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    def fake_run_git(_repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(args, 0, ".git", "")
        if args[:1] == ["add"]:
            return subprocess.CompletedProcess(
                args,
                128,
                "",
                "fatal: Unable to create '.git/index.lock': File exists. Another git process seems to be running.",
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("devo.delivery._run_git", fake_run_git)

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    report = load_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    assert result.failure_category == "index_lock_exists"
    assert result.failure_retryable is True
    assert report is not None
    assert report.last_commit_failure_category == "index_lock_exists"
    assert report.last_commit_failure_retryable is True


def test_delivery_commit_blocks_before_staging_when_index_lock_exists(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)
    lock = repo / ".git" / "index.lock"
    lock.write_text("stale\n", encoding="utf-8")

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    report = load_delivery_report("sample", "DEL-0001", workspace_root=workspace)
    lock.unlink()
    status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.status == "blocked"
    assert result.failure_category == "index_lock_exists"
    assert result.failure_retryable is True
    assert "index-lock preflight failed before staging" in result.stderr
    assert "commit-diagnostics --project sample --report DEL-0001 --index-lock-probe --confirm-probe" in result.next_action
    assert "delivery report-refresh --project sample --report DEL-0001 --reopen" in result.next_action
    assert status == "?? changed.txt\n"
    assert report is not None
    assert report.final_status == "blocked"
    assert report.last_commit_failure_category == "index_lock_exists"


def test_delivery_commit_blocks_before_staging_when_index_lock_probe_fails(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_ready_report(workspace)

    def fake_probe(_repo_path: Path):
        from devo.delivery import IndexLockProbeResult

        return IndexLockProbeResult(
            ok=False,
            category="index_lock_permission_denied",
            message="Permission denied creating .git/index.lock during guarded commit preflight.",
            lock_path=str(repo / ".git" / "index.lock"),
        )

    def fake_run_git(_repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["add"]:
            raise AssertionError("git add must not run when index-lock preflight fails")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("devo.delivery._probe_git_index_lock", fake_probe)
    monkeypatch.setattr("devo.delivery._run_git", fake_run_git)

    result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    report = load_delivery_report("sample", "DEL-0001", workspace_root=workspace)
    status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.status == "blocked"
    assert result.failure_category == "index_lock_permission_denied"
    assert result.failure_retryable is True
    assert "normal PowerShell" in result.next_action
    assert "delivery report-refresh --project sample --report DEL-0001 --reopen" in result.next_action
    assert status == "?? changed.txt\n"
    assert report is not None
    assert report.final_status == "blocked"
    assert report.last_commit_failure_category == "index_lock_permission_denied"
    assert report.last_commit_failure_retryable is True


def test_delivery_report_refresh_without_reopen_keeps_retryable_report_blocked(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    before = _git(repo, "status", "--short", capture=True).stdout

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="lock gone",
        workspace_root=workspace,
    )
    after = _git(repo, "status", "--short", capture=True).stdout

    assert result.recovery_status == "reopen_allowed"
    assert result.reopen_allowed is True
    assert result.reopened is False
    assert report.final_status == "blocked"
    assert report.commit_ready is False
    assert report.readiness_currentness == "current"
    assert "lock gone" in report.recovery_history[-1]
    assert after == before


def test_delivery_report_refresh_reopen_restores_commit_ready_for_retryable_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    before = _git(repo, "status", "--short", capture=True).stdout

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="permission issue cleared",
        reopen=True,
        workspace_root=workspace,
    )
    after = _git(repo, "status", "--short", capture=True).stdout

    assert result.recovery_status == "reopened"
    assert result.reopened is True
    assert report.final_status == "ready"
    assert report.commit_ready is True
    assert report.blocker_summary == "none"
    assert "commit-preview" in report.next_action
    assert after == before


def test_delivery_report_refresh_command_reopens_retryable_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = runner.invoke(
        app,
        [
            "delivery",
            "report-refresh",
            "--project",
            "sample",
            "--report",
            "DEL-0001",
            "--reopen",
            "--note",
            "diagnostics clear",
        ],
        terminal_width=240,
    )
    report = load_delivery_report("sample", "DEL-0001", workspace_root=workspace)

    assert result.exit_code == 0, result.output
    assert "Recovery status: reopened" in result.output
    assert "Commit ready: True" in result.output
    assert report is not None
    assert report.final_status == "ready"
    assert report.commit_ready is True


def test_delivery_report_refresh_reopen_refuses_when_current_readiness_blocked(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="try reopen",
        reopen=True,
        workspace_root=workspace,
    )

    assert result.recovery_status == "refused"
    assert result.reopened is False
    assert result.current_readiness_status == "blocked"
    assert report.final_status == "blocked"
    assert report.commit_ready is False
    assert "Forbidden delivery paths are changed" in report.blocker_summary


def test_delivery_report_refresh_reopen_refuses_without_approved_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    plan_path = workspace / "projects" / "sample" / "delivery" / "delivery-plan-del-0001.json"
    plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
    plan_payload["approval_status"] = "requested"
    plan_path.write_text(json.dumps(plan_payload), encoding="utf-8")

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="approval regressed",
        reopen=True,
        workspace_root=workspace,
    )

    assert result.recovery_status == "refused"
    assert result.reopened is False
    assert "approved" in result.recovery_reason
    assert report.final_status == "blocked"
    assert report.commit_ready is False


def test_delivery_report_refresh_does_not_reopen_already_committed_report(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="snapshot only",
        reopen=True,
        workspace_root=workspace,
    )

    assert result.recovery_status == "refused"
    assert result.reopened is False
    assert report.final_status == "committed"
    assert report.commit_hash
    assert report.commit_ready is False


def test_delivery_report_refresh_does_not_reopen_already_pushed_report(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    _create_committed_report(workspace)
    push_delivery_report("sample", "DEL-0001", confirm_push=True, workspace_root=workspace)

    result, report, _json_path, _markdown_path = refresh_delivery_report(
        "sample",
        "DEL-0001",
        note="snapshot only",
        reopen=True,
        workspace_root=workspace,
    )

    assert result.recovery_status == "refused"
    assert result.reopened is False
    assert report.final_status == "pushed"
    assert report.pushed is True


def test_delivery_commit_preview_shows_recovery_guidance_for_retryable_blocked_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = runner.invoke(app, ["delivery", "commit-preview", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "retryable guarded commit failure" in result.output
    assert "delivery report-refresh" in result.output


def test_delivery_commit_preview_shows_diagnostics_command_for_retryable_blocked_report(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = runner.invoke(app, ["delivery", "commit-preview", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "delivery commit-diagnostics --project sample --report DEL-0001" in result.output
    assert "delivery report-refresh --project sample --report DEL-0001 --reopen" in result.output


def test_delivery_commit_diagnostics_shows_retryable_failure_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = run_delivery_commit_diagnostics("sample", "DEL-0001", workspace_root=workspace)

    assert result.report_final_status == "blocked"
    assert result.report_commit_ready is False
    assert result.last_commit_failure_category == "index_lock_permission_denied"
    assert result.last_commit_failure_retryable is True
    assert result.failure_looks_retryable is True
    assert result.git_index_lock_exists is False
    assert any("Controlled Folder Access" in cause for cause in result.possible_causes)
    assert any("commit-diagnostics" not in action for action in result.next_actions)


def test_delivery_commit_diagnostics_is_read_only(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    before_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    before_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout

    result = runner.invoke(app, ["delivery", "commit-diagnostics", "--project", "sample", "--report", "DEL-0001"], terminal_width=240)
    after_status = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout
    after_count = _git(repo, "rev-list", "--count", "HEAD", capture=True).stdout

    assert result.exit_code == 0, result.output
    assert "Last failure category: index_lock_permission_denied" in result.output
    assert after_status == before_status
    assert after_count == before_count


def test_delivery_commit_diagnostics_reports_index_lock_present(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)
    lock = repo / ".git" / "index.lock"
    lock.write_text("stale\n", encoding="utf-8")

    result = run_delivery_commit_diagnostics("sample", "DEL-0001", workspace_root=workspace)

    assert result.git_index_lock_exists is True
    assert result.git_index_lock_path == str(lock)


def test_delivery_commit_diagnostics_handles_missing_report_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["delivery", "commit-diagnostics", "--project", "sample", "--report", "DEL-9999"], terminal_width=240)

    assert result.exit_code != 0
    assert "Delivery report not found: DEL-9999" in result.output


def test_index_lock_probe_requires_confirmation(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = runner.invoke(
        app,
        ["delivery", "commit-diagnostics", "--project", "sample", "--report", "DEL-0001", "--index-lock-probe"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "--confirm-probe is required" in result.output
    assert not (repo / ".git" / "index.lock").exists()


def test_index_lock_probe_uses_temp_repo_and_cleans_up(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    _create_index_lock_failed_report(workspace, monkeypatch)

    result = run_delivery_commit_diagnostics(
        "sample",
        "DEL-0001",
        index_lock_probe=True,
        confirm_probe=True,
        workspace_root=workspace,
    )

    assert result.probe_requested is True
    assert result.probe_ran is True
    assert result.can_create_index_lock is True
    assert result.probe_error == ""
    assert not (repo / ".git" / "index.lock").exists()


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
    assert report_payload["readiness_currentness"] == "historical_snapshot"
    assert "delivery push-show" in report_payload["next_action"]
    assert push_payload["push_status"] == "pushed"
    assert push_payload["pushed"] is True
    assert "Delivery pushed" in push_payload["next_action"]
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


def test_delivery_check_classifies_global_ignore_warning_as_non_blocking(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch)
    warning = "warning: unable to access 'C:\\Users\\manas/.config/git/ignore': Permission denied"

    def fake_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["rev-parse", "--is-inside-work-tree"]:
            return subprocess.CompletedProcess(args, 0, "true\n", "")
        if args == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args, 0, f"{repo}\n", "")
        if args == ["branch", "--show-current"]:
            return subprocess.CompletedProcess(args, 0, "main\n", "")
        if args == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, "1" * 40 + "\n", "")
        if args == ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
            return subprocess.CompletedProcess(args, 0, "origin/main\n", "")
        if args == ["remote"]:
            return subprocess.CompletedProcess(args, 0, "origin\n", warning)
        if args == ["rev-list", "--left-right", "--count", "HEAD...@{u}"]:
            return subprocess.CompletedProcess(args, 0, "0\t0\n", "")
        if args == ["status", "--porcelain=v1", "-uall"]:
            return subprocess.CompletedProcess(args, 0, "", warning)
        if args == ["diff", "--check"]:
            return subprocess.CompletedProcess(args, 0, "", warning)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("devo.git_delivery._git", fake_git)

    check, _json_path, _markdown_path = run_delivery_readiness_check("sample", workspace_root=workspace)

    assert check.blockers == []
    assert check.readiness_status == "ready"
    assert any("Git global ignore file is unreadable" in warning for warning in check.warnings)


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


def _create_index_lock_failed_report(workspace: Path, monkeypatch) -> None:
    _create_ready_report(workspace)

    def fake_run_git(_repo_path: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(args, 0, ".git", "")
        if args[:1] == ["add"]:
            return subprocess.CompletedProcess(
                args,
                128,
                "",
                "fatal: Unable to create 'E:/DevOrchestrator/.git/index.lock': Permission denied",
            )
        return subprocess.CompletedProcess(args, 0, "", "")

    with monkeypatch.context() as scoped:
        scoped.setattr("devo.delivery._run_git", fake_run_git)
        result, _json_path, _markdown_path = commit_delivery_report("sample", "DEL-0001", confirm_commit=True, workspace_root=workspace)
    assert result.status == "failed"
    assert result.failure_retryable is True


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
