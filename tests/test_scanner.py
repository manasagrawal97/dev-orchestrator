from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app

runner = CliRunner()


def test_scan_registered_project_creates_bounded_result(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    _create_sample_project(project_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    add_result = runner.invoke(
        app,
        ["project", "add", "--name", "sample", "--path", str(project_path)],
    )
    scan_result = runner.invoke(app, ["project", "scan", "sample"])

    assert add_result.exit_code == 0
    assert scan_result.exit_code == 0
    assert "Scanned" in scan_result.output

    scan_file = workspace / "projects" / "sample" / "scan-result.json"
    assert scan_file.exists()
    data = json.loads(scan_file.read_text(encoding="utf-8"))

    assert data["project_name"] == "sample"
    assert Path(data["project_path"]) == project_path.resolve()
    assert data["file_tree"]["scanned_file_count"] > 0
    assert data["file_tree"]["sample_paths"]
    assert len(data["file_tree"]["sample_paths"]) <= data["limits"]["max_tree_entries"]
    assert data["categories"]["solution_files"] == ["Sample.sln", "Sample.slnx"]
    assert len(data["categories"]["solution_files"]) == 2
    assert data["categories"]["project_files"] == ["src/Sample.csproj", "tests/Sample.Tests.csproj"]
    assert "README.md" in data["categories"]["readme_docs_files"]
    assert "Dockerfile" in data["categories"]["docker_files"]
    assert "package.json" in data["categories"]["package_dependency_files"]
    assert "migrations/001_create_widgets.sql" in data["categories"]["migration_database_files"]


def test_scan_excludes_ignored_directories_and_secret_like_files(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    _create_sample_project(project_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    result = runner.invoke(app, ["project", "scan", "sample"])

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "sample" / "scan-result.json").read_text(encoding="utf-8"))
    serialized = json.dumps(data)

    assert "node_modules" not in serialized
    assert ".pytest_cache" not in serialized
    assert "__pycache__" not in serialized
    assert ".env" not in serialized
    assert "passwords.txt" not in serialized
    assert "service.secret.json" not in serialized
    assert "private.key" not in serialized
    assert "large-video.mp4" not in serialized


def test_scan_git_info_is_false_when_project_is_not_git_repo(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    result = runner.invoke(app, ["project", "scan", "sample"])

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "sample" / "scan-result.json").read_text(encoding="utf-8"))
    assert data["git"]["is_git_repo"] is False
    assert data["git"]["current_branch"] is None
    assert data["git"]["last_commit_subjects"] == []


def test_scan_git_info_is_collected_when_project_is_git_repo(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "git-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Git Sample\n", encoding="utf-8")
    _run_git(project_path, "init")
    _run_git(project_path, "config", "user.email", "test@example.com")
    _run_git(project_path, "config", "user.name", "Test User")
    _run_git(project_path, "add", "README.md")
    _run_git(project_path, "commit", "-m", "initial sample")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    runner.invoke(app, ["project", "add", "--name", "git-sample", "--path", str(project_path)])
    result = runner.invoke(app, ["project", "scan", "git-sample"])

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "git-sample" / "scan-result.json").read_text(encoding="utf-8"))
    assert data["git"]["is_git_repo"] is True
    assert data["git"]["current_branch"]
    assert data["git"]["status_summary"] == "clean"
    assert data["git"]["last_commit_subjects"] == ["initial sample"]
    assert ".git" not in json.dumps(data["file_tree"])


def _create_sample_project(project_path: Path) -> None:
    (project_path / "src").mkdir(parents=True)
    (project_path / "tests").mkdir()
    (project_path / "migrations").mkdir()
    (project_path / "node_modules").mkdir()
    (project_path / ".pytest_cache").mkdir()
    (project_path / "__pycache__").mkdir()

    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_path / "Sample.sln").write_text("solution\n", encoding="utf-8")
    (project_path / "Sample.slnx").write_text("<Solution />\n", encoding="utf-8")
    (project_path / "src" / "Sample.csproj").write_text("<Project />\n", encoding="utf-8")
    (project_path / "tests" / "Sample.Tests.csproj").write_text("<Project />\n", encoding="utf-8")
    (project_path / "package.json").write_text("{}\n", encoding="utf-8")
    (project_path / "appsettings.template.json").write_text("{}\n", encoding="utf-8")
    (project_path / "migrations" / "001_create_widgets.sql").write_text("select 1;\n", encoding="utf-8")
    (project_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")

    (project_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
    (project_path / "passwords.txt").write_text("password\n", encoding="utf-8")
    (project_path / "service.secret.json").write_text("{}\n", encoding="utf-8")
    (project_path / "private.key").write_text("key\n", encoding="utf-8")
    (project_path / "large-video.mp4").write_bytes(b"0" * 32)
    (project_path / "node_modules" / "package.json").write_text("{}\n", encoding="utf-8")
    (project_path / ".pytest_cache" / "cache.txt").write_text("cache\n", encoding="utf-8")
    (project_path / "__pycache__" / "module.pyc").write_bytes(b"cache")


def _run_git(cwd: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
