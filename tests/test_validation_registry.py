from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import (
    FileTreeSummary,
    GitInfo,
    ProjectRegistration,
    ProjectScanResult,
    ScanCategories,
    ScanLimits,
)

runner = CliRunner()


def test_validation_list_works_with_empty_registry(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["validation", "list", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "No validation commands registered" in result.output


def test_validation_add_creates_registry_file(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)

    result = _add_pytest_command()

    assert result.exit_code == 0
    assert (workspace / "projects" / "sample" / "validation-commands.json").exists()


def test_validation_add_stores_command_metadata(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)

    result = _add_pytest_command(note="Uses pytest only.")

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "sample" / "validation-commands.json").read_text(encoding="utf-8"))
    command = data["commands"][0]
    assert command["id"] == "pytest"
    assert command["name"] == "Run pytest"
    assert command["command"] == "python -m pytest"
    assert command["working_dir"] == str(project_path.resolve())
    assert command["category"] == "test"
    assert command["enabled"] is True
    assert command["source"] == "manual"
    assert command["notes"] == ["Uses pytest only."]


def test_validation_add_refuses_duplicate_id_unless_replace(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    assert _add_pytest_command().exit_code == 0

    duplicate = _add_pytest_command()

    assert duplicate.exit_code != 0
    assert "Validation command already exists: pytest" in duplicate.output

    replaced = _add_pytest_command(command="python -m pytest -q", replace=True)
    assert replaced.exit_code == 0
    assert "python -m pytest -q" in replaced.output


def test_validation_show_displays_existing_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    assert _add_pytest_command().exit_code == 0

    result = runner.invoke(app, ["validation", "show", "--project", "sample", "--id", "pytest"], terminal_width=240)

    assert result.exit_code == 0
    assert "Run pytest" in result.output
    assert "Policy classification" in result.output


def test_validation_check_classifies_high_risk_target_project_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, solution=True)
    assert _add_dotnet_command().exit_code == 0

    result = runner.invoke(app, ["validation", "check", "--project", "sample", "--id", "dotnet-build"], terminal_width=240)

    assert result.exit_code == 0
    assert "Allowed: False" in result.output
    assert "Approval required: True" in result.output
    assert "Risk level: high" in result.output
    assert "devo approval request --project sample" in result.output
    assert "--run <runId> --task <taskId> --action target_command" in result.output


def test_validation_check_classifies_medium_internal_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    result = runner.invoke(
        app,
        [
            "validation",
            "add",
            "--project",
            "sample",
            "--id",
            "internal-pytest",
            "--name",
            "Internal pytest",
            "--command",
            "python -m pytest --basetemp=E:\\DevOrchestrator\\pt-validation",
            "--category",
            "test",
            "--working-dir",
            str(Path.cwd()),
            "--source",
            "manual",
        ],
        terminal_width=240,
    )
    assert result.exit_code == 0

    checked = runner.invoke(app, ["validation", "check", "--project", "sample", "--id", "internal-pytest"], terminal_width=240)

    assert checked.exit_code == 0
    assert "Allowed: True" in checked.output
    assert "Approval required: False" in checked.output
    assert "Risk level: medium" in checked.output


def test_validation_suggest_detects_dotnet_solution_command_from_project_metadata(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, solution=True, scan=True)

    result = runner.invoke(app, ["validation", "suggest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "dotnet-restore-sample" in result.output
    assert "dotnet restore Sample.slnx" in result.output
    assert "dotnet build Sample.slnx" in result.output
    assert "dotnet test Sample.slnx" in result.output
    assert "No registry changes made" in result.output


def test_validation_suggest_does_not_execute_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, solution=True, scan=True)

    def fail_run(*_args, **_kwargs):
        raise AssertionError("external command execution is forbidden")

    monkeypatch.setattr(subprocess, "run", fail_run)

    result = runner.invoke(app, ["validation", "suggest", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "dotnet restore Sample.slnx" in result.output


def test_validation_suggest_write_writes_suggested_commands(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch, solution=True, scan=True)

    result = runner.invoke(app, ["validation", "suggest", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "sample" / "validation-commands.json").read_text(encoding="utf-8"))
    ids = {command["id"] for command in data["commands"]}
    assert {"dotnet-restore-sample", "dotnet-build-sample", "dotnet-test-sample"}.issubset(ids)


def test_suggested_personalos_style_dotnet_commands_are_approval_required(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch, name="PersonalOS", solution_name="PersonalOS.slnx", solution=True, scan=True)

    result = runner.invoke(app, ["validation", "suggest", "--project", "PersonalOS", "--write"], terminal_width=240)

    assert result.exit_code == 0
    data = json.loads((workspace / "projects" / "PersonalOS" / "validation-commands.json").read_text(encoding="utf-8"))
    dotnet_commands = [command for command in data["commands"] if command["command"].startswith("dotnet ")]
    assert dotnet_commands
    assert all(command["risk_level"] == "high" for command in dotnet_commands)
    assert all(command["approval_required"] is True for command in dotnet_commands)
    assert all(command["enabled"] is False for command in dotnet_commands)
    assert (project_path / "PersonalOS.slnx").exists()


def test_validation_registry_handles_missing_project_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["validation", "list", "--project", "missing"], terminal_width=240)

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_validation_registry_handles_malformed_file_safely(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)
    registry = workspace / "projects" / "sample" / "validation-commands.json"
    registry.write_text("not-json", encoding="utf-8")

    result = runner.invoke(app, ["validation", "list", "--project", "sample"], terminal_width=240)

    assert result.exit_code != 0
    assert "Validation command registry is malformed" in result.output


def test_disabled_commands_are_shown_as_disabled(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    result = _add_pytest_command(extra=["--disabled"])
    assert result.exit_code == 0

    listed = runner.invoke(app, ["validation", "list", "--project", "sample"], terminal_width=240)

    assert listed.exit_code == 0
    assert "Enabled: False" in listed.output


def test_readme_documents_validation_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "validation command registry" in readme.lower()
    assert "devo validation list" in readme
    assert "devo validation add" in readme
    assert "devo validation show" in readme
    assert "devo validation check" in readme
    assert "devo validation suggest" in readme
    assert "does not execute" in readme.lower()


def test_validation_registry_does_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch, solution=True, scan=True)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    assert runner.invoke(app, ["validation", "suggest", "--project", "sample", "--write"], terminal_width=240).exit_code == 0
    assert _add_dotnet_command(command="dotnet test Sample.slnx", replace=True).exit_code == 0
    assert runner.invoke(app, ["validation", "check", "--project", "sample", "--id", "dotnet-build"], terminal_width=240).exit_code == 0

    assert sentinel.read_text(encoding="utf-8") == before


def test_validation_registry_tests_execute_no_external_commands(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, solution=True, scan=True)

    def fail_run(*_args, **_kwargs):
        raise AssertionError("external command execution is forbidden")

    monkeypatch.setattr(subprocess, "run", fail_run)

    assert runner.invoke(app, ["validation", "list", "--project", "sample"], terminal_width=240).exit_code == 0
    assert runner.invoke(app, ["validation", "suggest", "--project", "sample"], terminal_width=240).exit_code == 0


def _workspace(
    tmp_path: Path,
    monkeypatch,
    name: str = "sample",
    solution_name: str = "Sample.slnx",
    solution: bool = False,
    scan: bool = False,
) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project_path = tmp_path / "target-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    if solution:
        (project_path / solution_name).write_text("<Solution></Solution>\n", encoding="utf-8")
        src = project_path / "src" / "Sample.App"
        tests = project_path / "tests" / "Sample.Tests"
        src.mkdir(parents=True)
        tests.mkdir(parents=True)
        (src / "Sample.App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\" />\n", encoding="utf-8")
        (tests / "Sample.Tests.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\" />\n", encoding="utf-8")
    project_dir = workspace / "projects" / name
    project_dir.mkdir(parents=True)
    registration = ProjectRegistration(
        name=name,
        path=project_path,
        looks_like_software_project=True,
        detected_markers=["README.md"],
    )
    (project_dir / "project.json").write_text(registration.model_dump_json(indent=2), encoding="utf-8")
    if scan:
        scan_result = ProjectScanResult(
            project_name=name,
            project_path=project_path,
            limits=ScanLimits(max_file_size_bytes=1_000_000, max_recorded_paths_per_category=100, max_tree_entries=250),
            file_tree=FileTreeSummary(scanned_file_count=4, scanned_directory_count=4, sample_paths=[solution_name]),
            categories=ScanCategories(
                solution_files=[solution_name],
                project_files=["src/Sample.App/Sample.App.csproj", "tests/Sample.Tests/Sample.Tests.csproj"],
                package_dependency_files=[],
            ),
            git=GitInfo(is_git_repo=False),
            warnings=[],
        )
        (project_dir / "scan-result.json").write_text(scan_result.model_dump_json(indent=2), encoding="utf-8")
    return workspace, project_path


def _add_pytest_command(
    command: str = "python -m pytest",
    note: str | None = None,
    replace: bool = False,
    extra: list[str] | None = None,
):
    args = [
        "validation",
        "add",
        "--project",
        "sample",
        "--id",
        "pytest",
        "--name",
        "Run pytest",
        "--command",
        command,
        "--category",
        "test",
    ]
    if note:
        args.extend(["--note", note])
    if replace:
        args.append("--replace")
    if extra:
        args.extend(extra)
    return runner.invoke(app, args, terminal_width=240)


def _add_dotnet_command(command: str = "dotnet build Sample.slnx", replace: bool = False):
    args = [
        "validation",
        "add",
        "--project",
        "sample",
        "--id",
        "dotnet-build",
        "--name",
        "Build solution",
        "--command",
        command,
        "--category",
        "build",
    ]
    if replace:
        args.append("--replace")
    return runner.invoke(app, args, terminal_width=240)
