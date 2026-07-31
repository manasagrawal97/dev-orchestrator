from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.project_planning import load_project_blueprint, load_project_brief, planning_artifact_paths
from devo.read_models import build_project_overview
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration

runner = CliRunner()


def test_brief_create_from_file_creates_json_and_markdown_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    before_target = _target_snapshot(project_path)

    result = runner.invoke(
        app,
        ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    assert "Project brief saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert paths.brief_json.exists()
    assert paths.brief_markdown.exists()
    data = json.loads(paths.brief_json.read_text(encoding="utf-8"))
    assert data["project"] == "sample"
    assert data["title"] == "Sample Product"
    assert data["status"] == "draft"
    assert data["goals"] == ["Track the work queue", "Show progress clearly"]
    assert "Original Brief Text" in paths.brief_markdown.read_text(encoding="utf-8")
    assert _target_snapshot(project_path) == before_target


def test_brief_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "brief-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project brief: sample" in result.output
    assert "Status: draft" in result.output


def test_brief_approve_marks_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "brief-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project brief approved" in result.output
    brief = load_project_brief("sample", workspace_root=workspace)
    assert brief is not None
    assert brief.status == "approved"


def test_blueprint_create_creates_deterministic_draft_from_brief(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])

    result = runner.invoke(app, ["project", "blueprint-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint saved" in result.output
    paths = planning_artifact_paths("sample", workspace_root=workspace)
    assert paths.blueprint_json.exists()
    assert paths.blueprint_markdown.exists()
    blueprint = load_project_blueprint("sample", workspace_root=workspace)
    assert blueprint is not None
    assert blueprint.status == "draft"
    assert len(blueprint.milestones) == 2
    assert len(blueprint.epics) == 2
    assert "no AI or Codex automation" in "\n".join(blueprint.architecture_notes)


def test_blueprint_show_works(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])

    result = runner.invoke(app, ["project", "blueprint-show", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint: sample" in result.output
    assert "Milestones: 2" in result.output
    assert "Epics: 2" in result.output


def test_blueprint_approve_marks_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])

    result = runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project blueprint approved" in result.output
    assert "TASK-DEVO-075" in result.output
    blueprint = load_project_blueprint("sample", workspace_root=workspace)
    assert blueprint is not None
    assert blueprint.status == "approved"


def test_unknown_project_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)

    result = runner.invoke(
        app,
        ["project", "brief-create", "--project", "missing", "--title", "Missing", "--file", str(brief_file)],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found" in result.output


def test_blueprint_create_without_brief_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["project", "blueprint-create", "--project", "sample"], terminal_width=240)

    assert result.exit_code != 0
    assert "Project brief not found" in result.output


def test_read_models_include_planning_summary(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)

    missing = build_project_overview("sample", workspace_root=workspace)
    assert missing.brief_status == "missing"
    assert "brief-create" in missing.planning_next_action

    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])

    overview = build_project_overview("sample", workspace_root=workspace)
    assert overview.brief_status == "approved"
    assert overview.blueprint_status == "approved"
    assert overview.blueprint_milestone_count == 2
    assert overview.blueprint_epic_count == 2
    assert "TASK-DEVO-075" in overview.planning_next_action


def test_planning_commands_do_not_mutate_target_repo(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    brief_file = _brief_file(tmp_path)
    before_target = _target_snapshot(project_path)

    runner.invoke(app, ["project", "brief-create", "--project", "sample", "--title", "Sample Product", "--file", str(brief_file)])
    runner.invoke(app, ["project", "brief-approve", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-create", "--project", "sample"])
    runner.invoke(app, ["project", "blueprint-approve", "--project", "sample"])

    assert _target_snapshot(project_path) == before_target


def _brief_file(tmp_path: Path) -> Path:
    path = tmp_path / "brief.md"
    path.write_text(
        """# Sample Brief

Build a local planning dashboard for controlled work.

## Goals
- Track the work queue
- Show progress clearly

## Non-Goals
- Run builds from the UI

## Target Users
- Solo developer

## Constraints
- Local-only
- No AI API calls

## Risks
- Scope drift

## Tech Stack
- Python
- React

## Validation
- Run focused tests
""",
        encoding="utf-8",
    )
    return path


def _workspace(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    monkeypatch.setenv("DEVO_DOCTOR_SKIP_SCHEDULED_TASK", "1")
    monkeypatch.delenv("DEVO_BACKUP_ROOT", raising=False)
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


def _target_snapshot(project_path: Path) -> dict[str, str]:
    return {str(path.relative_to(project_path)): path.read_text(encoding="utf-8") for path in project_path.rglob("*") if path.is_file()}
