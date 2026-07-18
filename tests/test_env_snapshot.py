from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.environment import (
    create_environment_snapshot,
    generate_environment_bootstrap_plan,
    verify_environment_snapshot,
)
from devo.main import app

runner = CliRunner()


def test_snapshot_creates_environment_snapshot_and_bootstrap_plan(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    snapshot, snapshot_file, plan_file = create_environment_snapshot("sample", project)

    assert snapshot.name == "sample"
    assert snapshot_file.exists()
    assert plan_file.exists()
    assert json.loads(snapshot_file.read_text(encoding="utf-8"))["name"] == "sample"
    assert "# Bootstrap Plan: sample" in plan_file.read_text(encoding="utf-8")


def test_snapshot_detects_python_dependency_files(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    snapshot, _snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    assert "pyproject.toml" in snapshot.dependency_files_found
    assert "requirements.txt" in snapshot.dependency_files_found
    assert "typer>=0.12" in snapshot.package_versions_summary["pyproject.toml"]
    assert "pytest>=8.0" in snapshot.package_versions_summary["requirements.txt"]


def test_snapshot_detects_dotnet_solution_and_project_files(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    snapshot, _snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    assert "Sample.sln" in snapshot.detected_solution_files
    assert "Sample.slnx" in snapshot.detected_solution_files
    assert "src/App/App.csproj" in snapshot.detected_project_files
    assert "tests/App.Tests/App.Tests.csproj" in snapshot.detected_test_projects
    assert "src/App/App.csproj" in snapshot.package_versions_summary


def test_snapshot_detects_missing_expected_files_without_failing(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    snapshot, _snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    assert "AGENTS.md" in snapshot.dependency_files_missing
    assert "poetry.lock" in snapshot.dependency_files_missing


def test_snapshot_excludes_heavy_folders(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    for folder in (".venv", "node_modules", ".packages", ".tools", "bin", "obj", "__pycache__", ".pytest_cache", ".git"):
        directory = project / folder
        directory.mkdir(parents=True)
        (directory / "Ignored.csproj").write_text("<Project />", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    snapshot, _snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    assert ".venv" in snapshot.excluded_heavy_paths
    assert "node_modules" in snapshot.excluded_heavy_paths
    assert not any("Ignored.csproj" in path for path in snapshot.detected_project_files)
    assert not any("node_modules" in path for path in snapshot.dependency_files_found)


def test_verify_passes_for_fresh_snapshot(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    snapshot, snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    verified = verify_environment_snapshot(snapshot_file)

    assert verified.name == snapshot.name
    assert verified.project_path == project.resolve()


def test_verify_fails_if_snapshot_missing_required_fields(tmp_path: Path) -> None:
    snapshot_file = tmp_path / "environment-snapshot.json"
    snapshot_file.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")

    with pytest.raises(ValueError, match="schema validation"):
        verify_environment_snapshot(snapshot_file)


def test_bootstrap_plan_works_from_snapshot(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))
    _snapshot, snapshot_file, _plan_file = create_environment_snapshot("sample", project)

    result, plan_file, plan_text = generate_environment_bootstrap_plan(snapshot_file)

    assert result.name == "sample"
    assert plan_file.exists()
    assert "Recommended Commands" in plan_text
    assert str(project.resolve()) in plan_text


def test_unknown_path_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["env", "snapshot", "--name", "missing", "--path", str(tmp_path / "missing")],
        terminal_width=200,
    )

    assert result.exit_code != 0
    assert "Project path does not exist" in result.output


def test_snapshot_does_not_copy_env_or_local_settings_values(tmp_path: Path, monkeypatch) -> None:
    project = _sample_project(tmp_path)
    (project / ".env").write_text("SECRET_TOKEN=super-secret-value", encoding="utf-8")
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.local.json").write_text('{"token":"local-secret-value"}', encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    snapshot, snapshot_file, plan_file = create_environment_snapshot("sample", project)
    snapshot_text = snapshot_file.read_text(encoding="utf-8")
    plan_text = plan_file.read_text(encoding="utf-8")

    assert any(".env" in warning for warning in snapshot.warnings)
    assert any("settings.local.json" in warning for warning in snapshot.warnings)
    assert "super-secret-value" not in snapshot_text
    assert "local-secret-value" not in snapshot_text
    assert "super-secret-value" not in plan_text
    assert "local-secret-value" not in plan_text


def _sample_project(tmp_path: Path) -> Path:
    project = tmp_path / "sample-project"
    (project / "src" / "App").mkdir(parents=True)
    (project / "tests" / "App.Tests").mkdir(parents=True)
    (project / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        """
[project]
name = "sample"
dependencies = ["typer>=0.12"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]
""".strip(),
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text("pytest>=8.0\n", encoding="utf-8")
    (project / "Sample.sln").write_text("Microsoft Visual Studio Solution File\n", encoding="utf-8")
    (project / "Sample.slnx").write_text("<Solution></Solution>\n", encoding="utf-8")
    (project / "global.json").write_text('{"sdk":{"version":"10.0.100"}}', encoding="utf-8")
    (project / "NuGet.Config").write_text("<configuration />", encoding="utf-8")
    (project / "Directory.Build.props").write_text("<Project />", encoding="utf-8")
    (project / "src" / "App" / "App.csproj").write_text(
        """
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <OutputType>Exe</OutputType>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="10.0.0" />
  </ItemGroup>
</Project>
""".strip(),
        encoding="utf-8",
    )
    (project / "tests" / "App.Tests" / "App.Tests.csproj").write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="xunit" Version="2.9.0" />
    <ProjectReference Include="..\\..\\src\\App\\App.csproj" />
  </ItemGroup>
</Project>
""".strip(),
        encoding="utf-8",
    )
    return project
