from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.agents import DISCOVERY_AGENT_NAME, list_agent_definitions, load_agent_definition
from devo.main import app

runner = CliRunner()


def test_loads_agent_definitions() -> None:
    agents = list_agent_definitions()

    assert len(agents) == 14
    assert {agent.name for agent in agents} >= {
        "ProjectContextDiscoveryAgent",
        "GitDeliveryAgent",
    }

    discovery_agent = load_agent_definition(DISCOVERY_AGENT_NAME)
    assert discovery_agent.mode.value == "prompt_only"
    assert "project-profile.md" in discovery_agent.outputs


def test_agent_list_command_shows_available_agents() -> None:
    result = runner.invoke(app, ["agent", "list"], terminal_width=240)

    assert result.exit_code == 0
    assert "ProjectContextDiscoveryAgent" in result.output
    assert "prompt_only" in result.output
    assert "Requires approval" in result.output


def test_agent_show_command_shows_agent_details() -> None:
    result = runner.invoke(app, ["agent", "show", DISCOVERY_AGENT_NAME], terminal_width=240)

    assert result.exit_code == 0
    assert "name: ProjectContextDiscoveryAgent" in result.output
    assert "mode: prompt_only" in result.output
    assert "project-profile.md" in result.output


def test_agent_prompt_generates_project_context_discovery_prompt(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    (project_path / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
    (project_path / "Sample.slnx").write_text("<Solution />\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    add_result = runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    scan_result = runner.invoke(app, ["project", "scan", "sample"])
    prompt_result = runner.invoke(
        app,
        ["agent", "prompt", DISCOVERY_AGENT_NAME, "--project", "sample"],
        terminal_width=240,
    )

    assert add_result.exit_code == 0
    assert scan_result.exit_code == 0
    assert prompt_result.exit_code == 0

    prompt_file = workspace / "projects" / "sample" / "prompts" / "project-context-discovery.prompt.md"
    assert prompt_file.exists()
    prompt_text = prompt_file.read_text(encoding="utf-8")

    assert "ProjectContextDiscoveryAgent" in prompt_text
    assert "project-profile.md" in prompt_text
    assert "architecture-map.md" in prompt_text
    assert "Do not invent facts." in prompt_text
    assert "Clearly separate detected facts from assumptions." in prompt_text
    assert '"project_name": "sample"' in prompt_text
    assert '"scanned_file_count"' in prompt_text
    assert "README.md" in prompt_text
    assert "pyproject.toml" in prompt_text
    assert "Sample.slnx" in prompt_text
    assert '"solution_files": 1' in prompt_text
    assert "Stored in:" in prompt_result.output


def test_agent_prompt_errors_when_scan_result_is_missing(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    add_result = runner.invoke(app, ["project", "add", "--name", "sample", "--path", str(project_path)])
    prompt_result = runner.invoke(app, ["agent", "prompt", DISCOVERY_AGENT_NAME, "--project", "sample"])

    assert add_result.exit_code == 0
    assert prompt_result.exit_code != 0
    assert "scan-result.json not found" in prompt_result.output


def test_agent_show_errors_for_unknown_agent() -> None:
    result = runner.invoke(app, ["agent", "show", "UnknownAgent"])

    assert result.exit_code != 0
    assert "Unknown agent: UnknownAgent" in result.output


def test_agent_prompt_errors_for_unknown_agent(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    project_path = tmp_path / "sample-project"
    project_path.mkdir()
    scan_dir = workspace / "projects" / "sample"
    scan_dir.mkdir(parents=True)
    (scan_dir / "project.json").write_text(
        json.dumps(
            {
                "name": "sample",
                "path": str(project_path.resolve()),
                "looks_like_software_project": False,
                "detected_markers": [],
                "created_at": "2026-07-15T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(app, ["agent", "prompt", "UnknownAgent", "--project", "sample"])

    assert result.exit_code != 0
    assert "Unknown agent: UnknownAgent" in result.output
