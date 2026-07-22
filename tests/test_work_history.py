from __future__ import annotations

import subprocess
from pathlib import Path

from devo.work_history import build_project_activity_summary, list_work_package_summaries
from devo.work_packages import WorkPackageStatus, save_work_package, start_work_package
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration


def test_work_history_lists_delivered_package_first_when_requested(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    open_package = start_work_package("sample", "low-risk-ui-maintenance", "Open package", workspace_root=workspace)
    delivered_package = start_work_package("sample", "low-risk-ui-maintenance", "Delivered package", workspace_root=workspace)
    save_work_package(
        delivered_package.model_copy(update={"status": WorkPackageStatus.DELIVERED, "commit_hash": "abc1234"}),
        workspace_root=workspace,
    )

    summaries = list_work_package_summaries("sample", delivered_first=True, workspace_root=workspace)

    assert summaries[0].run_id == delivered_package.run_id
    assert summaries[0].commit_hash == "abc1234"
    assert any(summary.run_id == open_package.run_id for summary in summaries)


def test_project_activity_summary_includes_git_status(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _init_git_repo(project_path)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Delivered package", workspace_root=workspace)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.DELIVERED, "commit_hash": "def5678"}), workspace_root=workspace)

    summary = build_project_activity_summary("sample", workspace_root=workspace)

    assert "branch=main" in summary.current_git_status
    assert summary.delivered_work_packages
    assert summary.delivered_work_packages[0].commit_hash == "def5678"


def _workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project_path = tmp_path / "target-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")

    project_dir = workspace / "projects" / "sample"
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True)
    approvals_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        ProjectRegistration(
            name="sample",
            path=project_path,
            looks_like_software_project=True,
            detected_markers=["README.md"],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    context_path = context_dir / "context-state.json"
    context_path.write_text(
        ContextState(project_name="sample", project_path=project_path, status=ContextStatus.CONTEXT_APPROVED).model_dump_json(indent=2),
        encoding="utf-8",
    )
    approval_path = approvals_dir / "context-approval.json"
    approval_path.write_text("{}", encoding="utf-8")
    snapshot = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert snapshot.context_state_path == context_path
    return workspace, project_path


def _init_git_repo(project_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=project_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=project_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=project_path, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=project_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project_path, check=True, capture_output=True, text=True)
