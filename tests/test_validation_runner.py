from __future__ import annotations

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from devo.approvals import approve_approval, create_approval_request
from devo.main import app
from devo.schemas import ContextSnapshot, ContextState, ContextStatus, ProjectRegistration, RunArtifactType, RunState, RunStatus
from tests.test_policy import _policy_workspace

runner = CliRunner()


def test_validation_run_executes_low_risk_enabled_command_in_temp_dir(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "hello"], terminal_width=240)

    assert result.exit_code == 0
    assert "PASSED validation run" in result.output
    assert "Status: passed" in result.output
    assert "Exit code: 0" in result.output
    assert "hello" in result.output


def test_validation_run_writes_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "hello"], terminal_width=240)

    assert result.exit_code == 0
    run_dir = next((workspace / "projects" / "sample" / "validation-runs").iterdir())
    assert (run_dir / "validation-run.json").exists()
    assert (run_dir / "validation-run.md").exists()


def test_validation_run_captures_stdout(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)
    _add_command("stdout", _python_command("print('out-text')"), risk="low", approval=False)

    runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "stdout"], terminal_width=240)

    stdout_file = next((workspace / "projects" / "sample" / "validation-runs").glob("*/stdout.txt"))
    assert stdout_file.read_text(encoding="utf-8").strip() == "out-text"


def test_validation_run_captures_stderr(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)
    _add_command("stderr", _python_command("import sys; print('err-text', file=sys.stderr)"), risk="low", approval=False)

    runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "stderr"], terminal_width=240)

    stderr_file = next((workspace / "projects" / "sample" / "validation-runs").glob("*/stderr.txt"))
    assert stderr_file.read_text(encoding="utf-8").strip() == "err-text"


def test_validation_run_records_non_zero_exit_as_failed(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("fail", _python_command("import sys; print('bad'); sys.exit(3)"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "fail"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: failed" in result.output
    assert "Exit code: 3" in result.output


def test_validation_run_handles_timeout(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("timeout", _python_command("import time; time.sleep(5)"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "timeout", "--timeout-seconds", "1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: timed_out" in result.output
    assert "timed out" in result.output


def test_validation_dry_run_does_not_execute_command(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    marker = tmp_path / "would-run.txt"
    _add_command("dry", _python_command(f"from pathlib import Path; Path(r'{marker}').write_text('ran')"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "dry-run", "--project", "sample", "--id", "dry"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: dry_run" in result.output
    assert not marker.exists()


def test_validation_run_blocks_unknown_command_id(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "missing"], terminal_width=240)

    assert result.exit_code != 0
    assert "Validation command not found: missing" in result.output


def test_validation_run_blocks_disabled_command_by_default(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("disabled", _python_command("print('nope')"), risk="low", approval=False, extra=["--disabled"])

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "disabled"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: blocked" in result.output
    assert "disabled" in result.output.lower()


def test_validation_run_with_allow_disabled_still_respects_policy(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("disabled-high", _python_command("print('nope')"), risk="high", approval=True, extra=["--disabled"])

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "disabled-high", "--allow-disabled"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: blocked" in result.output
    assert "approval" in result.output.lower()


def test_high_risk_command_without_approval_is_blocked(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("high", _python_command("print('high')"), risk="high", approval=True)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "high"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: blocked" in result.output
    assert "approval" in result.output.lower()


def test_critical_command_is_blocked(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("critical", _python_command("print('critical')"), risk="critical", approval=True)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "critical"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: blocked" in result.output
    assert "Critical-risk" in result.output


def test_broad_delete_command_is_blocked(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("delete", "rm -rf temp", risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "delete"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: blocked" in result.output
    assert "rm -rf" in result.output


def test_history_lists_previous_validation_runs(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)
    runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "hello"], terminal_width=240)

    result = runner.invoke(app, ["validation", "history", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0
    assert "Validation history for sample" in result.output
    assert "Command ID: hello" in result.output
    assert "Status: passed" in result.output


def test_run_linked_validation_stores_artifacts_under_run_artifacts_path(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch, with_run=True)
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--run", "run-1", "--task", "T001", "--id", "hello"], terminal_width=240)

    assert result.exit_code == 0
    assert next((workspace / "runs" / "sample" / "run-1" / "artifacts" / "validation-runs").glob("*/validation-run.json")).exists()


def test_project_level_validation_stores_artifacts_under_project_path(tmp_path: Path, monkeypatch) -> None:
    workspace, _project = _workspace(tmp_path, monkeypatch)
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "hello"], terminal_width=240)

    assert result.exit_code == 0
    assert next((workspace / "projects" / "sample" / "validation-runs").glob("*/validation-run.json")).exists()


def test_approval_id_is_recorded_when_approval_authorizes_command(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})
    _add_command("approved-high", _python_command("print('approved')"), risk="high", approval=True)
    command_text = _python_command("print('approved')")
    record = create_approval_request(
        "sample",
        "run-1",
        "T001",
        "target_command",
        reason=f"validation-command:approved-high command:{command_text}",
        workspace_root=workspace,
    )
    approve_approval(
        "sample",
        "run-1",
        record.approval_id,
        approved_by="tester",
        note=f"validation-command:approved-high command:{command_text}",
        workspace_root=workspace,
    )

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--run", "run-1", "--task", "T001", "--id", "approved-high"], terminal_width=240)

    assert result.exit_code == 0
    assert "Status: passed" in result.output
    data = json.loads(next((workspace / "runs" / "sample" / "run-1" / "artifacts" / "validation-runs").glob("*/validation-run.json")).read_text(encoding="utf-8"))
    assert data["approval_id"] == record.approval_id


def test_command_working_dir_missing_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    missing = tmp_path / "missing-workdir"
    _add_command("missing-dir", _python_command("print('x')"), risk="low", approval=False, extra=["--working-dir", str(missing)])

    result = runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "missing-dir"], terminal_width=240)

    assert result.exit_code != 0
    assert result.exit_code != 0


def test_no_personalos_files_are_modified_in_tests(tmp_path: Path, monkeypatch) -> None:
    _workspace_path, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")
    _add_command("hello", _python_command("print('hello')"), risk="low", approval=False)

    runner.invoke(app, ["validation", "run", "--project", "sample", "--id", "hello"], terminal_width=240)

    assert sentinel.read_text(encoding="utf-8") == before


def test_readme_documents_validation_runner_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo validation run" in readme
    assert "devo validation dry-run" in readme
    assert "devo validation history" in readme
    assert "PersonalOS commands are registered but high-risk and disabled by default" in readme


def _workspace(tmp_path: Path, monkeypatch, with_run: bool = False) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    project_path = tmp_path / "target-project"
    project_path.mkdir()
    (project_path / "README.md").write_text("# Sample\n", encoding="utf-8")
    project_dir = workspace / "projects" / "sample"
    project_dir.mkdir(parents=True)
    registration = ProjectRegistration(name="sample", path=project_path, looks_like_software_project=True, detected_markers=["README.md"])
    (project_dir / "project.json").write_text(registration.model_dump_json(indent=2), encoding="utf-8")
    if with_run:
        _write_run(workspace, project_path)
    return workspace, project_path


def _write_run(workspace: Path, project_path: Path) -> None:
    run_dir = workspace / "runs" / "sample" / "run-1"
    (run_dir / "artifacts").mkdir(parents=True)
    (workspace / "projects" / "sample" / "context").mkdir(parents=True, exist_ok=True)
    context_state = ContextState(project_name="sample", project_path=project_path, status=ContextStatus.CONTEXT_APPROVED)
    approval_path = workspace / "projects" / "sample" / "approvals" / "context-approval.json"
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text("{}", encoding="utf-8")
    context_path = workspace / "projects" / "sample" / "context" / "context-state.json"
    context_path.write_text(context_state.model_dump_json(indent=2), encoding="utf-8")
    tasks_path = run_dir / "artifacts" / "tasks.md"
    tasks_path.write_text("## Task T001\n\n- task title: Read-only validation.\n", encoding="utf-8")
    state = RunState(
        project_name="sample",
        project_path=project_path,
        run_id="run-1",
        goal="test",
        status=RunStatus.TASKS_DRAFTED,
        context_snapshot=ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[]),
        artifacts=[],
    )
    (run_dir / "run-state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")


def _add_command(command_id: str, command: str, risk: str, approval: bool, extra: list[str] | None = None):
    args = [
        "validation",
        "add",
        "--project",
        "sample",
        "--id",
        command_id,
        "--name",
        command_id,
        "--command",
        command,
        "--category",
        "test",
        "--risk",
        risk,
    ]
    args.append("--approval-required" if approval else "--no-approval-required")
    if extra:
        args.extend(extra)
    result = runner.invoke(app, args, terminal_width=240)
    assert result.exit_code == 0, result.output
    return result


def _python_command(code: str) -> str:
    escaped = code.replace('"', '\\"')
    return f'{sys.executable} -c "{escaped}"'
