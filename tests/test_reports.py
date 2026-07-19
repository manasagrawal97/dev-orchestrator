from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.schemas import (
    ContextSnapshot,
    ContextStatus,
    ContextState,
    EnvironmentSnapshot,
    FileTreeSummary,
    GitInfo,
    ImplementationRecord,
    ProjectRegistration,
    ProjectScanResult,
    RunArtifact,
    RunArtifactType,
    RunState,
    RunStatus,
    ScanCategories,
    ScanLimits,
    TaskDispositionStatus,
    TaskLedger,
    TaskLedgerEntry,
    ValidationCommand,
    ValidationCommandCategory,
    ValidationCommandRegistry,
    ValidationRiskLevel,
    ValidationRunRecord,
    ValidationRunStatus,
)

runner = CliRunner()


def test_project_report_prints_project_summary(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True, scan=True, registry=True, environment=True, validation=True)

    result = runner.invoke(app, ["report", "project", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "Project Report" in result.output
    assert "sample" in result.output
    assert "CONTEXT_APPROVED" in result.output
    assert "validation-run-1" in result.output
    assert "run-1" in result.output


def test_run_report_prints_workflow_and_task_summary(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True, resolved_tasks=("T001",))

    result = runner.invoke(app, ["report", "run", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Run Report" in result.output
    assert "TASKS_DRAFTED" in result.output
    assert "unresolved" in result.output.lower()
    assert "T002" in result.output


def test_handoff_report_includes_inspection_commands(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "handoff", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Handoff Report" in result.output
    assert "devo report project --project sample" in result.output
    assert "devo report run --project sample --run run-1" in result.output
    assert "Do not modify registered target projects" in result.output


def test_project_report_write_creates_markdown_and_json(tmp_path: Path, monkeypatch) -> None:
    workspace, _ = _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "project", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0
    reports_dir = workspace / "projects" / "sample" / "reports"
    md_path = next(reports_dir.glob("project-report-*.md"))
    json_path = next(reports_dir.glob("project-report-*.json"))
    assert "Project Report" in md_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["report_type"] == "project"
    assert data["markdown_path"] == str(md_path)


def test_run_report_write_creates_run_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _ = _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "run", "--project", "sample", "--run", "run-1", "--write"], terminal_width=240)

    assert result.exit_code == 0
    reports_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "reports"
    assert next(reports_dir.glob("run-report-*.md")).exists()
    assert next(reports_dir.glob("run-report-*.json")).exists()


def test_handoff_report_write_creates_project_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _ = _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "handoff", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0
    reports_dir = workspace / "projects" / "sample" / "reports"
    assert next(reports_dir.glob("handoff-report-*.md")).exists()
    assert next(reports_dir.glob("handoff-report-*.json")).exists()


def test_report_json_format_outputs_json(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "project", "--project", "sample", "--format", "json"], terminal_width=240)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["report_type"] == "project"
    assert data["project_name"] == "sample"


def test_unknown_project_fails_safely(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(app, ["report", "project", "--project", "missing"], terminal_width=240)

    assert result.exit_code != 0
    assert "project not found" in result.output.lower()


def test_unknown_run_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=False, approved=True)

    result = runner.invoke(app, ["report", "run", "--project", "sample", "--run", "missing"], terminal_width=240)

    assert result.exit_code != 0
    assert "Run not found" in result.output


def test_project_report_warns_for_missing_optional_artifacts(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=False, approved=False, git_repo=False)

    result = runner.invoke(app, ["report", "project", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "Project Report" in result.output
    assert "Project context is not approved" in result.output
    assert "Git status unavailable" in result.output


def test_reports_sanitize_sensitive_local_settings_details(tmp_path: Path, monkeypatch) -> None:
    workspace, _ = _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True, registry=True, environment=True, secretish=True)
    update_dir = workspace / "projects" / "sample" / "context-updates"
    update_dir.mkdir(parents=True)
    (update_dir / "context-updates-ledger.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "project_name": "sample",
                "updates": [
                    {
                        "update_id": "context-update-1",
                        "project_name": "sample",
                        "project_path": str(_project(tmp_path)),
                        "status": "draft",
                        "facts_added": [".claude/settings.local.json uses API_KEY=super-secret-value"],
                        "warnings": ["appsettings.Development.json may contain PASSWORD=abc123"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["report", "project", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0
    report_text = result.output + next((workspace / "projects" / "sample" / "reports").glob("project-report-*.json")).read_text(encoding="utf-8")
    assert "super-secret-value" not in report_text
    assert "PASSWORD=abc123" not in report_text
    assert "settings.local.json" not in report_text
    assert "Local/sensitive settings artifact detected" in report_text


def test_report_generation_does_not_modify_target_project(tmp_path: Path, monkeypatch) -> None:
    _, project = _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)
    readme = project / "README.md"
    before = readme.read_text(encoding="utf-8")

    result = runner.invoke(app, ["report", "project", "--project", "sample", "--write"], terminal_width=240)

    assert result.exit_code == 0
    assert readme.read_text(encoding="utf-8") == before


def test_report_limit_applies_to_recent_runs(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True, extra_runs=3)

    result = runner.invoke(app, ["report", "project", "--project", "sample", "--limit", "2"], terminal_width=240)

    assert result.exit_code == 0
    assert "run-1" not in result.output
    assert "run-3" in result.output
    assert "run-4" in result.output


def test_run_report_includes_validation_and_git_delivery_evidence(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True, validation=True, git_delivery=True)

    result = runner.invoke(app, ["report", "run", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "validation-run-1" in result.output
    assert "git-delivery-report-1.json" in result.output
    assert "readiness=ready" in result.output


def test_run_report_missing_validation_evidence_warns_not_crashes(tmp_path: Path, monkeypatch) -> None:
    _write_workspace(tmp_path, monkeypatch, with_run=True, approved=True)

    result = runner.invoke(app, ["report", "run", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Validation Evidence Summary" in result.output
    assert "none" in result.output


def test_readme_documents_report_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "devo report project --project MyProject" in readme
    assert "devo report run --project MyProject --run <runId>" in readme
    assert "devo report handoff --project MyProject" in readme
    assert "context is lost" in readme.lower()


def _write_workspace(
    tmp_path: Path,
    monkeypatch,
    *,
    with_run: bool,
    approved: bool,
    scan: bool = False,
    registry: bool = False,
    environment: bool = False,
    secretish: bool = False,
    git_repo: bool = True,
    validation: bool = False,
    git_delivery: bool = False,
    resolved_tasks: tuple[str, ...] = (),
    extra_runs: int = 0,
) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project = _project(tmp_path)
    project.mkdir(parents=True)
    (project / "README.md").write_text("# Sample\n", encoding="utf-8")
    if git_repo:
        _git(project, "init")
        _git(project, "config", "user.email", "test@example.com")
        _git(project, "config", "user.name", "Test User")
        _git(project, "add", "README.md")
        _git(project, "commit", "-m", "initial")

    project_dir = workspace / "projects" / "sample"
    project_dir.mkdir(parents=True)
    registration = ProjectRegistration(name="sample", path=project.resolve(), looks_like_software_project=True, detected_markers=["README.md"])
    (project_dir / "project.json").write_text(registration.model_dump_json(indent=2), encoding="utf-8")
    _write_context(project_dir, project.resolve(), approved=approved)
    if scan:
        _write_scan(project_dir, project.resolve())
    if registry:
        _write_registry(project_dir, secretish=secretish)
    if environment:
        _write_environment(workspace, project.resolve(), secretish=secretish)
    if with_run:
        _write_run(workspace, project.resolve(), status=RunStatus.TASKS_DRAFTED, resolved_tasks=resolved_tasks)
        for index in range(2, extra_runs + 2):
            _write_run(workspace, project.resolve(), run_id=f"run-{index}", status=RunStatus.RUN_CLOSED, tasks=(f"T{index:03d}",))
    if validation:
        _write_validation_run(workspace, project.resolve())
    if git_delivery:
        _write_git_delivery(workspace)
    return workspace, project


def _write_context(project_dir: Path, project: Path, *, approved: bool) -> None:
    context_dir = project_dir / "context"
    approvals_dir = project_dir / "approvals"
    context_dir.mkdir(parents=True, exist_ok=True)
    approvals_dir.mkdir(parents=True, exist_ok=True)
    status = ContextStatus.CONTEXT_APPROVED if approved else ContextStatus.REGISTERED
    context_path = context_dir / "context-state.json"
    context_path.write_text(ContextState(project_name="sample", project_path=project, status=status).model_dump_json(indent=2), encoding="utf-8")
    if approved:
        approved_dir = context_dir / "approved"
        approved_dir.mkdir()
        (approved_dir / "project-context-discovery.md").write_text("# project-profile.md\n", encoding="utf-8")
        (approvals_dir / "context-approval.json").write_text('{"project_name":"sample"}', encoding="utf-8")


def _write_scan(project_dir: Path, project: Path) -> None:
    scan = ProjectScanResult(
        project_name="sample",
        project_path=project,
        limits=ScanLimits(max_file_size_bytes=1000, max_recorded_paths_per_category=10, max_tree_entries=10),
        file_tree=FileTreeSummary(scanned_file_count=2, sample_paths=["README.md"]),
        categories=ScanCategories(readme_docs_files=["README.md"]),
        git=GitInfo(is_git_repo=True, current_branch="main"),
    )
    (project_dir / "scan-result.json").write_text(scan.model_dump_json(indent=2), encoding="utf-8")


def _write_registry(project_dir: Path, *, secretish: bool) -> None:
    note = "safe note"
    if secretish:
        note = "API_KEY=super-secret-value"
    registry = ValidationCommandRegistry(
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
    (project_dir / "validation-commands.json").write_text(registry.model_dump_json(indent=2), encoding="utf-8")


def _write_environment(workspace: Path, project: Path, *, secretish: bool) -> None:
    env_dir = workspace / "environment" / "sample"
    env_dir.mkdir(parents=True)
    warning = "safe warning"
    if secretish:
        warning = ".claude/settings.local.json is local config"
    snapshot = EnvironmentSnapshot(
        schema_version="1",
        name="sample",
        project_path=project,
        operating_system="test-os",
        dependency_files_found=["README.md"],
        warnings=[warning],
    )
    (env_dir / "environment-snapshot.json").write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")


def _write_run(
    workspace: Path,
    project: Path,
    *,
    run_id: str = "run-1",
    status: RunStatus,
    tasks: tuple[str, ...] = ("T001", "T002"),
    resolved_tasks: tuple[str, ...] = (),
) -> None:
    run_dir = workspace / "runs" / "sample" / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "goal.md").write_text(f"# {run_id}\n\nDo useful work\n", encoding="utf-8")
    tasks_path = artifacts_dir / "tasks.md"
    tasks_path.write_text(_tasks_text(tasks), encoding="utf-8")
    ledger = TaskLedger(project_name="sample", run_id=run_id)
    for task_id in resolved_tasks:
        ledger.entries[task_id] = TaskLedgerEntry(
            task_id=task_id,
            disposition_status=TaskDispositionStatus.NOT_NEEDED,
            disposition_note="Resolved for report test.",
        )
    ledger_path = artifacts_dir / "task-ledger.json"
    if ledger.entries:
        ledger_path.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    context_path = workspace / "projects" / "sample" / "context" / "context-state.json"
    approval_path = workspace / "projects" / "sample" / "approvals" / "context-approval.json"
    run_state = RunState(
        project_name="sample",
        project_path=project,
        run_id=run_id,
        goal="Do useful work",
        status=status,
        context_snapshot=ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[]),
        artifacts=[RunArtifact(artifact_type=RunArtifactType.TASKS, agent_name="TaskDecomposerAgent", source_file_path=tasks_path, artifact_path=tasks_path)],
        implementation_records=[
            ImplementationRecord(
                task_id="T001",
                agent_name="ImplementationCoordinatorAgent",
                source_file_path=artifacts_dir / "implementation" / "T001" / "implementation-brief.md",
                implementation_brief_path=artifacts_dir / "implementation" / "T001" / "implementation-brief.md",
                closure_record_path=artifacts_dir / "implementation" / "T001" / "closure-record.md" if "T001" in resolved_tasks else None,
                closure_status="closed" if "T001" in resolved_tasks else None,
            )
        ],
        task_ledger_path=ledger_path if ledger.entries else None,
    )
    for record in run_state.implementation_records:
        record.implementation_brief_path.parent.mkdir(parents=True, exist_ok=True)
        record.implementation_brief_path.write_text("brief", encoding="utf-8")
        if record.closure_record_path:
            record.closure_record_path.write_text("closed", encoding="utf-8")
    (run_dir / "run-state.json").write_text(run_state.model_dump_json(indent=2), encoding="utf-8")


def _write_validation_run(workspace: Path, project: Path) -> None:
    validation_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "validation-runs" / "validation-run-1"
    validation_dir.mkdir(parents=True)
    record = ValidationRunRecord(
        validation_run_id="validation-run-1",
        project_name="sample",
        run_id="run-1",
        task_id="T001",
        command_id="pytest",
        command_name="pytest passed",
        command="python -m pytest",
        working_dir=project,
        category=ValidationCommandCategory.TEST,
        risk_level=ValidationRiskLevel.LOW,
        approval_required=False,
        status=ValidationRunStatus.PASSED,
        exit_code=0,
    )
    (validation_dir / "validation-run.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")


def _write_git_delivery(workspace: Path) -> None:
    delivery_dir = workspace / "runs" / "sample" / "run-1" / "artifacts" / "git-delivery"
    delivery_dir.mkdir(parents=True)
    (delivery_dir / "git-delivery-report-1.json").write_text(
        json.dumps(
            {
                "delivery_check": {
                    "readiness": "ready",
                    "status": {"current_branch": "main", "ahead": 0, "behind": 0},
                }
            }
        ),
        encoding="utf-8",
    )


def _tasks_text(tasks: tuple[str, ...]) -> str:
    return "\n\n".join(f"## Task {task_id}\n\n- task title: Task {task_id} title\n- risk level: low\n" for task_id in tasks)


def _project(tmp_path: Path) -> Path:
    return tmp_path / "target-project"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


