from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from devo.api import create_app
from devo.delivery import list_delivery_checks, run_delivery_readiness_check
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


def test_project_overview_includes_delivery_summary(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)

    overview = build_project_overview("sample", workspace_root=workspace)

    assert overview.delivery_check_count == 1
    assert overview.latest_delivery_id == "DEL-0001"
    assert overview.latest_delivery_readiness_status == "ready"
    assert overview.latest_delivery_blocker_count == 0


def test_api_exposes_delivery_checks(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo = _workspace(tmp_path, monkeypatch)
    run_delivery_readiness_check("sample", write=True, workspace_root=workspace)
    client = TestClient(create_app(workspace_root=workspace))

    listed = client.get("/api/projects/sample/delivery-checks")
    shown = client.get("/api/projects/sample/delivery-checks/DEL-0001")
    missing = client.get("/api/projects/sample/delivery-checks/DEL-9999")

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert shown.status_code == 200
    assert shown.json()["delivery_id"] == "DEL-0001"
    assert missing.status_code == 404


def test_delivery_check_does_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    result = runner.invoke(app, ["delivery", "check", "--project", "sample"], terminal_width=240)
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.exit_code == 0, result.output
    assert after == before


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
