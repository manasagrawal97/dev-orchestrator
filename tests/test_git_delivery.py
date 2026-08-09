from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.git_delivery import get_git_repository_status, run_delivery_check
from devo.main import app
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration, RunArtifactType, RunState, RunStatus, ValidationRunRecord, ValidationRunStatus, ValidationCommandCategory, ValidationRiskLevel

runner = CliRunner()


def test_git_status_works_on_temp_git_repo(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch, git=True)

    result = runner.invoke(app, ["git", "status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "sample" in result.output
    assert "Working tree clean: True" in result.output
    assert str(repo) in result.output


def test_git_status_works_on_temp_git_repo_with_spaces(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch, git=True, repo_name="repo with spaces")

    result = runner.invoke(app, ["git", "status", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Working tree clean: True" in result.output
    assert str(repo) in result.output


def test_git_status_fails_safely_on_non_git_path(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=False)

    result = runner.invoke(app, ["git", "status", "--project", "sample"], terminal_width=240)

    assert result.exit_code != 0
    with pytest.raises(ValueError, match="Project path is not a git repository|Project path is inside a git work tree but is not the repository root"):
        get_git_repository_status("sample", workspace_root=tmp_path / "workspace")


def test_delivery_check_passes_for_clean_temp_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Delivery readiness: ready" in result.output
    assert "git diff --check: passed" in result.output


def test_delivery_check_passes_for_clean_temp_repo_with_spaces(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True, repo_name="repo with spaces")

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Delivery readiness: ready" in result.output
    assert "git diff --check: passed" in result.output


def test_delivery_check_uses_registered_path_with_spaces_as_git_cwd(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True, repo_name="repo with spaces")
    repo = _repo(tmp_path, "repo with spaces").resolve()

    check = run_delivery_check("sample", workspace_root=tmp_path / "workspace")

    assert check.repo_path == repo
    assert check.status.current_branch == "main"
    assert check.readiness.value == "ready"


def test_delivery_check_detects_staged_normal_file(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)
    repo = _repo(tmp_path)
    (repo / "feature.txt").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample", "--run", "run-1", "--task", "T001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "feature.txt" in result.output
    assert "Delivery readiness: warning" in result.output
    assert "No validation run evidence" in result.output


def test_delivery_check_blocks_staged_env_file(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)
    repo = _repo(tmp_path)
    (repo / ".env").write_text("SAFE_PLACEHOLDER=true\n", encoding="utf-8")
    _git(repo, "add", ".env")

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Delivery readiness: blocked" in result.output
    assert "Forbidden file staged: .env" in result.output


def test_delivery_check_detects_secret_like_content_without_printing_value(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)
    repo = _repo(tmp_path)
    secret_value = "super-secret-value-not-for-output"
    (repo / "config.txt").write_text(f"API_KEY={secret_value}\n", encoding="utf-8")
    _git(repo, "add", "config.txt")

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "config.txt: API_KEY" in result.output
    assert secret_value not in result.output
    assert "Delivery readiness: blocked" in result.output


def test_delivery_check_detects_workspace_and_venv_forbidden_paths(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)
    repo = _repo(tmp_path)
    (repo / "workspace" / "state.txt").parent.mkdir()
    (repo / "workspace" / "state.txt").write_text("state\n", encoding="utf-8")
    (repo / ".venv" / "cache.txt").parent.mkdir()
    (repo / ".venv" / "cache.txt").write_text("cache\n", encoding="utf-8")
    _git(repo, "add", "workspace/state.txt", ".venv/cache.txt")

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Forbidden file staged: workspace/state.txt" in result.output
    assert "Forbidden file staged: .venv/cache.txt" in result.output


def test_delivery_check_runs_git_diff_check_when_safe(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)

    check = run_delivery_check("sample", workspace_root=tmp_path / "workspace")

    assert "git diff --check" in check.checks_performed
    assert "git diff --check: passed" in check.checks_performed


def test_delivery_report_writes_markdown_and_json_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch, git=True)

    result = runner.invoke(app, ["git", "delivery-report", "--project", "sample", "--message", "test delivery"], terminal_width=240)

    assert result.exit_code == 0, result.output
    report_dir = workspace / "projects" / "sample" / "git-delivery"
    markdown = next(report_dir.glob("git-delivery-report-*.md"))
    payload = json.loads(next(report_dir.glob("git-delivery-report-*.json")).read_text(encoding="utf-8"))
    assert markdown.exists()
    assert payload["requested_commit_message"] == "test delivery"
    assert "If push is blocked by Codex approval policy" in markdown.read_text(encoding="utf-8")


def test_delivery_report_includes_suggested_push_command_when_branch_is_ahead(tmp_path: Path, monkeypatch) -> None:
    workspace, repo = _workspace(tmp_path, monkeypatch, git=True)
    (repo / "ahead.txt").write_text("ahead\n", encoding="utf-8")
    _git(repo, "add", "ahead.txt")
    _git(repo, "commit", "-m", "ahead commit")

    result = runner.invoke(app, ["git", "delivery-report", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    payload = json.loads(next((workspace / "projects" / "sample" / "git-delivery").glob("git-delivery-report-*.json")).read_text(encoding="utf-8"))
    assert payload["delivery_check"]["suggested_push_command"] == "git push origin main"


def test_delivery_report_handles_missing_validation_evidence_with_warning(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)

    result = runner.invoke(app, ["git", "delivery-report", "--project", "sample", "--run", "run-1", "--task", "T001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    payload = _latest_report_payload(tmp_path)
    assert "No validation run evidence was found" in " ".join(payload["delivery_check"]["warnings"])


def test_delivery_report_includes_validation_evidence_when_artifact_exists(tmp_path: Path, monkeypatch) -> None:
    workspace, _repo_path = _workspace(tmp_path, monkeypatch, git=True)
    _write_validation_record(workspace)

    result = runner.invoke(app, ["git", "delivery-report", "--project", "sample", "--run", "run-1", "--task", "T001"], terminal_width=240)

    assert result.exit_code == 0, result.output
    payload = _latest_report_payload(tmp_path)
    assert any("pytest passed" in item or "pytest" in item for item in payload["delivery_check"]["validation_evidence"])


def test_delivery_check_does_not_mutate_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, git=True)
    repo = _repo(tmp_path)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    before = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    result = runner.invoke(app, ["git", "delivery-check", "--project", "sample"], terminal_width=240)
    after = _git(repo, "status", "--porcelain=v1", "-uall", capture=True).stdout

    assert result.exit_code == 0, result.output
    assert after == before


def test_readme_documents_git_delivery_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo git status" in readme
    assert "devo git delivery-check" in readme
    assert "devo git delivery-report" in readme
    assert "does not bypass external approval policies" in readme


def _workspace(tmp_path: Path, monkeypatch, git: bool, repo_name: str = "repo") -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    repo = _repo(tmp_path, repo_name)
    repo.mkdir()
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    if git:
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
    _write_context_and_run(workspace, repo)
    return workspace, repo


def _write_context_and_run(workspace: Path, repo: Path) -> None:
    context_dir = workspace / "projects" / "sample" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir = workspace / "projects" / "sample" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    context_path = context_dir / "context-state.json"
    approval_path = approvals_dir / "context-approval.json"
    context = ContextState(project_name="sample", project_path=repo, status=ContextStatus.CONTEXT_APPROVED)
    context_path.write_text(context.model_dump_json(indent=2), encoding="utf-8")
    approval_path.write_text("{}", encoding="utf-8")
    run_dir = workspace / "runs" / "sample" / "run-1"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True)
    tasks_path = artifacts_dir / "tasks.md"
    tasks_path.write_text("## Task T001\n\n- task title: Read-only delivery check.\n- risk level: low\n", encoding="utf-8")
    run_state = RunState(
        project_name="sample",
        project_path=repo,
        run_id="run-1",
        goal="delivery test",
        status=RunStatus.TASKS_DRAFTED,
        context_snapshot=ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[]),
        artifacts=[
            {
                "artifact_type": RunArtifactType.TASKS,
                "agent_name": "TaskDecomposerAgent",
                "source_file_path": tasks_path,
                "artifact_path": tasks_path,
            }
        ],
    )
    (run_dir / "run-state.json").write_text(run_state.model_dump_json(indent=2), encoding="utf-8")


def _write_validation_record(workspace: Path) -> None:
    validation_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "validation-runs" / "validation-run-1"
    validation_dir.mkdir(parents=True)
    record = ValidationRunRecord(
        validation_run_id="validation-run-1",
        project_name="sample",
        run_id="run-1",
        task_id="T001",
        command_id="pytest",
        command_name="pytest passed",
        command="pytest",
        working_dir=_repo(workspace.parent),
        category=ValidationCommandCategory.TEST,
        risk_level=ValidationRiskLevel.LOW,
        approval_required=False,
        status=ValidationRunStatus.PASSED,
        exit_code=0,
    )
    (validation_dir / "validation-run.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")


def _latest_report_payload(tmp_path: Path) -> dict[str, object]:
    report_dir = tmp_path / "workspace" / "runs" / "sample" / "run-1" / "artifacts" / "git-delivery"
    return json.loads(next(report_dir.glob("git-delivery-report-*.json")).read_text(encoding="utf-8"))


def _repo(tmp_path: Path, repo_name: str = "repo") -> Path:
    return tmp_path / repo_name


def _git(cwd: Path, *args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=capture, text=True)


