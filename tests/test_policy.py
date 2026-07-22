from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.policy import check_policy, classify_task, get_policy_status
from devo.schemas import RunArtifactType, RunStatus
from tests.test_workflow import _workspace

runner = CliRunner()


def test_policy_classify_low_risk_read_only_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Summarize README.md safely with read-only inspection."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "low"
    assert classification.approval_required is False
    assert classification.blocked is False
    assert "read-only inspection" in classification.matched_risk_signals


def test_policy_classify_medium_risk_source_edit_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify DevOrchestrator source code in src/devo and tests/test_policy.py."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "medium"
    assert classification.approval_required is False
    assert "devorchestrator source edit" in classification.matched_risk_signals


def test_policy_classify_high_risk_target_project_modification(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source and make an app code change."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert classification.approval_required is True
    assert classification.blocked is False


def test_policy_classify_high_risk_database_migration_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Change database migrations and DbContext behavior."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert "database or migration" in classification.matched_risk_signals


def test_policy_docs_only_exclusions_do_not_create_database_risk(tmp_path: Path, monkeypatch) -> None:
    body = (
        "Create/update docs/current-state.md only. "
        "No code, DB, restore, build, test, scripts, migrations, secrets, generated files, "
        "or local settings changes."
    )
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": body})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "low"
    assert "database or migration" not in classification.matched_risk_signals
    assert "Database, app data, or migration work is high risk." not in classification.reasons
    assert "database exclusion" in classification.safety_exclusion_signals
    assert "migration exclusion" in classification.safety_exclusion_signals
    assert "build exclusion" in classification.safety_exclusion_signals
    assert "test exclusion" in classification.safety_exclusion_signals
    assert "restore exclusion" in classification.safety_exclusion_signals


def test_policy_real_migration_task_remains_high_risk(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run database migration for the target project."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert "database or migration" in classification.matched_risk_signals


def test_policy_real_database_update_task_remains_high_risk(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run dotnet ef database update."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert "database or migration" in classification.matched_risk_signals


def test_policy_classify_high_risk_git_push_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run git push to publish changes to GitHub."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert "git push" in classification.matched_risk_signals


def test_policy_classify_high_risk_google_drive_external_backup_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Create a Google Drive backup using an external folder write."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "high"
    assert "external folder write" in classification.matched_risk_signals


def test_policy_classify_critical_broad_delete_task(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Run rm -rf during broad recursive delete of unknown folders."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "critical"
    assert classification.blocked is True


def test_policy_check_implementation_prompt_for_low_risk_is_allowed(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})

    result = check_policy("sample", "run-1", "T001", action_type="implementation_prompt", workspace_root=workspace)

    assert result.allowed is True
    assert result.approval_required is False
    assert result.blocked is False


def test_policy_check_target_repo_docs_edit_is_medium_and_allowed(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Update docs/current-state.md only."})

    result = check_policy("sample", "run-1", "T001", action_type="target_repo_docs_edit", workspace_root=workspace)

    assert result.action_type == "target_repo_docs_edit"
    assert result.risk_level == "medium"
    assert result.allowed is True
    assert result.approval_required is False
    assert "target repo docs edit" in result.matched_risk_signals


def test_policy_target_repo_docs_edit_is_lower_risk_than_code_edit(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Update docs/current-state.md only."})

    docs_result = check_policy("sample", "run-1", "T001", action_type="target_repo_docs_edit", workspace_root=workspace)
    code_result = check_policy("sample", "run-1", "T001", action_type="target_repo_code_edit", workspace_root=workspace)

    assert docs_result.risk_level == "medium"
    assert code_result.risk_level == "high"
    assert code_result.approval_required is True


def test_policy_check_target_repo_code_edit_is_high_risk(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})

    result = check_policy("sample", "run-1", "T001", action_type="target_repo_code_edit", workspace_root=workspace)

    assert result.risk_level == "high"
    assert result.approval_required is True
    assert "target repo code edit" in result.matched_risk_signals


def test_policy_check_target_repo_command_actions_are_high_risk(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})

    for action_type in (
        "target_repo_validation",
        "target_repo_build",
        "target_repo_test",
        "target_repo_run",
        "target_repo_migration",
        "target_repo_database",
        "target_repo_script",
    ):
        result = check_policy("sample", "run-1", "T001", action_type=action_type, workspace_root=workspace)
        assert result.risk_level == "high"
        assert result.approval_required is True


def test_policy_check_implementation_for_high_risk_requires_approval(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})

    result = check_policy("sample", "run-1", "T001", action_type="implementation", workspace_root=workspace)

    assert result.allowed is False
    assert result.approval_required is True
    assert result.blocked is False
    assert result.required_approval_note


def test_policy_check_critical_action_is_blocked(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Use Remove-Item -Recurse for broad recursive delete."})

    result = check_policy("sample", "run-1", "T001", action_type="cleanup", workspace_root=workspace)

    assert result.allowed is False
    assert result.blocked is True


def test_policy_status_lists_all_tasks_in_run(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(
        tmp_path,
        monkeypatch,
        {
            "T001": "Read-only docs summary.",
            "T002": "Modify DevOrchestrator source code.",
        },
    )

    status = get_policy_status("sample", "run-1", workspace_root=workspace)

    assert [task.task_id for task in status.tasks] == ["T001", "T002"]
    assert status.tasks[0].risk_level == "low"
    assert status.tasks[1].risk_level == "medium"


def test_policy_unknown_task_fails_safely(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})

    result = runner.invoke(app, ["policy", "classify", "--project", "sample", "--run", "run-1", "--task", "missing"])

    assert result.exit_code != 0
    assert "Task id not found in tasks.md: missing" in result.output


def test_policy_unknown_task_risk_is_conservative(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Do the next ambiguous thing."})

    classification = classify_task("sample", "run-1", "T001", workspace_root=workspace)

    assert classification.risk_level == "medium"
    assert "No clear low-risk evidence" in " ".join(classification.reasons)


def test_workflow_next_includes_policy_warning_for_high_risk_selected_task(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})

    result = runner.invoke(app, ["workflow", "next", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Action type: approval_required" in result.output
    assert "Policy risk for task T001: high" in result.output
    assert "devo approval request" in result.output


def test_workflow_batch_stops_on_high_risk_selected_task(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Modify target project source."})

    result = runner.invoke(app, ["workflow", "batch", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Stop reason: INCONSISTENT_STATE" in result.output
    assert "approval_required" in result.output


def test_task_next_displays_risk_summary_if_available(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."}, risks={"T001": "low"})

    result = runner.invoke(app, ["task", "next", "--project", "sample", "--run", "run-1", "--include-skipped"], terminal_width=240)

    assert result.exit_code == 0
    assert "risk: low" in result.output


def test_policy_rules_do_not_mutate_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace = _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})
    project_path = Path(json.loads((workspace / "projects" / "sample" / "project.json").read_text(encoding="utf-8"))["path"])
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")

    assert runner.invoke(app, ["policy", "status", "--project", "sample", "--run", "run-1"]).exit_code == 0
    assert runner.invoke(app, ["policy", "check", "--project", "sample", "--run", "run-1", "--task", "T001", "--action", "implementation_prompt"]).exit_code == 0

    assert sentinel.read_text(encoding="utf-8") == before


def test_policy_commands_require_no_external_commands_or_ai(tmp_path: Path, monkeypatch) -> None:
    _policy_workspace(tmp_path, monkeypatch, {"T001": "Read-only docs summary."})

    result = runner.invoke(app, ["policy", "status", "--project", "sample", "--run", "run-1"], terminal_width=240)

    assert result.exit_code == 0
    assert "Risk level" not in result.output
    assert "risk level: low" in result.output


def test_policy_commands_are_documented() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "devo policy classify" in readme
    assert "devo policy check" in readme
    assert "devo policy status" in readme


def _policy_workspace(
    tmp_path: Path,
    monkeypatch,
    task_bodies: dict[str, str],
    risks: dict[str, str] | None = None,
) -> Path:
    tasks = tuple(task_bodies)
    workspace = _workspace(tmp_path, monkeypatch, RunStatus.TASKS_DRAFTED, artifacts=[RunArtifactType.TASKS], tasks=tasks)
    risks = risks or {}
    sections = []
    for task_id, body in task_bodies.items():
        lines = [
            f"## Task {task_id}",
            "",
            f"- task title: {body}",
            f"- objective: {body}",
        ]
        if task_id in risks:
            lines.append(f"- risk level: {risks[task_id]}")
        sections.append("\n".join(lines) + "\n")
    (workspace / "runs" / "sample" / "run-1" / "artifacts" / "tasks.md").write_text("\n".join(sections), encoding="utf-8")
    return workspace
