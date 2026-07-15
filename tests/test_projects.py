from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app

runner = CliRunner()


def test_project_add_registers_existing_project(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(
        app,
        ["project", "add", "--name", "sample", "--path", str(project_path)],
    )

    assert result.exit_code == 0
    project_file = workspace / "projects" / "sample" / "project.json"
    assert project_file.exists()

    data = json.loads(project_file.read_text(encoding="utf-8"))
    assert data["name"] == "sample"
    assert Path(data["path"]) == project_path.resolve()
    assert data["looks_like_software_project"] is True
    assert data["detected_markers"] == ["pyproject.toml"]


def test_project_add_rejects_missing_path(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    missing_path = tmp_path / "missing"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(
        app,
        ["project", "add", "--name", "missing", "--path", str(missing_path)],
    )

    assert result.exit_code != 0
    assert "Project path does not exist" in result.output
    assert not (workspace / "projects" / "missing" / "project.json").exists()


def test_project_add_rejects_file_path(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("not a project directory\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(
        app,
        ["project", "add", "--name", "file", "--path", str(file_path)],
    )

    assert result.exit_code != 0
    assert "Project path must be a directory" in result.output
    assert not (workspace / "projects" / "file" / "project.json").exists()


def test_project_add_records_non_software_directory(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "empty-directory"
    project_path.mkdir()
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(
        app,
        ["project", "add", "--name", "empty", "--path", str(project_path)],
    )

    assert result.exit_code == 0
    project_file = workspace / "projects" / "empty" / "project.json"
    data = json.loads(project_file.read_text(encoding="utf-8"))
    assert data["looks_like_software_project"] is False
    assert data["detected_markers"] == []


def test_project_list_shows_registered_projects(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    add_result = runner.invoke(
        app,
        ["project", "add", "--name", "sample", "--path", str(project_path)],
    )
    list_result = runner.invoke(app, ["project", "list"], terminal_width=200)

    assert add_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "sample" in list_result.output
    assert str(project_path.resolve()) in list_result.output
    assert "README.md" in list_result.output
