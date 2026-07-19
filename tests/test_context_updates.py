from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import (
    ContextSnapshot,
    ContextState,
    ContextStatus,
    EnvironmentSnapshot,
    FileTreeSummary,
    GitInfo,
    ProjectRegistration,
    ProjectScanResult,
    RunState,
    RunStatus,
    ScanCategories,
    ScanLimits,
    ValidationCommand,
    ValidationCommandCategory,
    ValidationCommandRegistry,
    ValidationRiskLevel,
)

runner = CliRunner()


def test_context_summary_works_for_registered_project(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True)

    result = runner.invoke(app, ["project", "context-summary", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "sample" in result.output
    assert "Context status: CONTEXT_APPROVED" in result.output


def test_context_summary_handles_missing_context_gracefully(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=False)

    result = runner.invoke(app, ["project", "context-summary", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project context is not approved" in result.output
    assert "No scan-result.json found" in result.output


def test_context_refresh_reads_project_metadata(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, scan=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Registered project path" in result.output
    assert "Project markers" in result.output
    assert "Scan result" in result.output


def test_context_refresh_includes_validation_registry_summary(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, registry=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Validation registry commands: total=1" in result.output
    assert "pytest" in result.output


def test_context_refresh_includes_environment_snapshot_summary(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, environment=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Environment snapshot created_at" in result.output
    assert "Dependency files found" in result.output


def test_context_refresh_includes_recent_run_summary(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, with_run=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "run-1" in result.output
    assert "status=RUN_CLOSED" in result.output


def test_context_refresh_write_draft_writes_markdown_and_json(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, approved=True, scan=True, registry=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)

    assert result.exit_code == 0, result.output
    update_dir = workspace / "projects" / "sample" / "context-updates"
    assert next(update_dir.glob("context-update-*.md")).exists()
    assert next(update_dir.glob("context-update-*.json")).exists()
    assert (update_dir / "context-updates-ledger.json").exists()


def test_context_refresh_does_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, scan=True)
    target = _project(tmp_path) / "README.md"
    before = target.read_text(encoding="utf-8")

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert target.read_text(encoding="utf-8") == before


def test_context_apply_applies_generated_draft(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, approved=True, scan=True)
    runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)
    update_json = next((workspace / "projects" / "sample" / "context-updates").glob("context-update-*.json"))

    result = runner.invoke(app, ["project", "context-apply", "--project", "sample", "--file", str(update_json)], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Applied context update" in result.output
    data = json.loads(update_json.read_text(encoding="utf-8"))
    assert data["status"] == "applied"
    state = json.loads((workspace / "projects" / "sample" / "context" / "context-state.json").read_text(encoding="utf-8"))
    assert state["latest_context_update_file"] == str(update_json)
    assert state["status"] == "CONTEXT_APPROVED"


def test_context_apply_refuses_unknown_non_generated_file(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True)
    outside = tmp_path / "not-generated.json"
    outside.write_text("{}", encoding="utf-8")

    result = runner.invoke(app, ["project", "context-apply", "--project", "sample", "--file", str(outside)], terminal_width=240)

    assert result.exit_code != 0
    assert "only accepts generated context-refresh JSON files" in result.output


def test_context_history_lists_draft_and_applied_updates(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, approved=True, scan=True)
    runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)
    update_json = next((workspace / "projects" / "sample" / "context-updates").glob("context-update-*.json"))
    runner.invoke(app, ["project", "context-apply", "--project", "sample", "--file", str(update_json)], terminal_width=240)

    result = runner.invoke(app, ["project", "context-history", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Status: draft" in result.output
    assert "Status: applied" in result.output


def test_context_update_ledger_is_append_only(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch, approved=True, scan=True)
    runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)
    update_json = next((workspace / "projects" / "sample" / "context-updates").glob("context-update-*.json"))
    runner.invoke(app, ["project", "context-apply", "--project", "sample", "--file", str(update_json)], terminal_width=240)
    ledger = json.loads((workspace / "projects" / "sample" / "context-updates" / "context-updates-ledger.json").read_text(encoding="utf-8"))

    assert [entry["status"] for entry in ledger["updates"]] == ["draft", "applied"]


def test_context_summary_missing_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["project", "context-summary", "missing"], terminal_width=240)

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_context_refresh_avoids_secrets_and_local_sensitive_values(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch, approved=True, registry=True, environment=True, secretish=True)

    result = runner.invoke(app, ["project", "context-refresh", "--project", "sample", "--write-draft"], terminal_width=240)

    assert result.exit_code == 0, result.output
    update_json = next((tmp_path / "workspace" / "projects" / "sample" / "context-updates").glob("context-update-*.json"))
    text = update_json.read_text(encoding="utf-8")
    assert "super-secret-value" not in text
    assert "settings.local.json" not in text
    assert "[sensitive]" in text or "Local/sensitive settings artifact" in text


def test_readme_documents_context_update_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo project context-summary" in readme
    assert "devo project context-refresh" in readme
    assert "devo project context-apply" in readme
    assert "devo project context-history" in readme


def _workspace(
    tmp_path: Path,
    monkeypatch,
    approved: bool,
    scan: bool = False,
    registry: bool = False,
    environment: bool = False,
    with_run: bool = False,
    secretish: bool = False,
) -> Path:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project = _project(tmp_path)
    project.mkdir()
    (project / "README.md").write_text("# Sample\n", encoding="utf-8")
    project_dir = workspace / "projects" / "sample"
    project_dir.mkdir(parents=True)
    registration = ProjectRegistration(name="sample", path=project, looks_like_software_project=True, detected_markers=["README.md"])
    (project_dir / "project.json").write_text(registration.model_dump_json(indent=2), encoding="utf-8")
    context_dir = project_dir / "context"
    context_dir.mkdir(parents=True)
    context_state = ContextState(
        project_name="sample",
        project_path=project,
        status=ContextStatus.CONTEXT_APPROVED if approved else ContextStatus.REGISTERED,
    )
    (context_dir / "context-state.json").write_text(context_state.model_dump_json(indent=2), encoding="utf-8")
    if approved:
        approved_dir = context_dir / "approved"
        approved_dir.mkdir()
        (approved_dir / "project-context-discovery.md").write_text("# project-profile.md\n", encoding="utf-8")
    if scan:
        scan_result = ProjectScanResult(
            project_name="sample",
            project_path=project,
            limits=ScanLimits(max_file_size_bytes=1000, max_recorded_paths_per_category=10, max_tree_entries=10),
            file_tree=FileTreeSummary(scanned_file_count=2),
            categories=ScanCategories(readme_docs_files=["README.md"]),
            git=GitInfo(is_git_repo=False),
        )
        (project_dir / "scan-result.json").write_text(scan_result.model_dump_json(indent=2), encoding="utf-8")
    if registry:
        note = "safe note"
        if secretish:
            note = "API_KEY=super-secret-value"
        registry_model = ValidationCommandRegistry(
            project_name="sample",
            commands=[
                ValidationCommand(
                    id="pytest",
                    name="Run pytest",
                    command="python -m pytest",
                    category=ValidationCommandCategory.TEST,
                    risk_level=ValidationRiskLevel.LOW,
                    notes=[note],
                )
            ],
        )
        (project_dir / "validation-commands.json").write_text(registry_model.model_dump_json(indent=2), encoding="utf-8")
    if environment:
        env_dir = workspace / "environment" / "sample"
        env_dir.mkdir(parents=True)
        warning = "safe warning"
        if secretish:
            warning = "settings.local.json is local config"
        snapshot = EnvironmentSnapshot(
            schema_version="1",
            name="sample",
            project_path=project,
            operating_system="test-os",
            dependency_files_found=["README.md"],
            warnings=[warning],
        )
        (env_dir / "environment-snapshot.json").write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    if with_run:
        _write_run(workspace, project)
    return workspace


def _write_run(workspace: Path, project: Path) -> None:
    run_dir = workspace / "runs" / "sample" / "run-1"
    run_dir.mkdir(parents=True)
    context_path = workspace / "projects" / "sample" / "context" / "context-state.json"
    approval_path = workspace / "projects" / "sample" / "approvals" / "context-approval.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text("{}", encoding="utf-8")
    state = RunState(
        project_name="sample",
        project_path=project,
        run_id="run-1",
        goal="finished context enrichment",
        status=RunStatus.RUN_CLOSED,
        context_snapshot=ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[]),
    )
    (run_dir / "run-state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")


def _project(tmp_path: Path) -> Path:
    return tmp_path / "target-project"
