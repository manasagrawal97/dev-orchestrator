from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.approvals import approve_approval_bundle, create_approval_bundle
from devo.main import app
from devo.runs import create_run, load_run
from devo.schemas import (
    ContextSnapshot,
    ContextState,
    ContextStatus,
    ProjectRegistration,
    RunStatus,
    ValidationCommandCategory,
    ValidationRiskLevel,
    ValidationRunRecord,
    ValidationRunStatus,
)
from devo.validation_registry import add_validation_command
from devo.work_packages import WorkPackageStatus, complete_work_package, get_lane, list_lanes, load_work_package, save_work_package, start_work_package

runner = CliRunner()

BUILT_IN_LANE_IDS = {
    "docs-only",
    "low-risk-ui-maintenance",
    "warning-cleanup",
    "small-bugfix",
    "small-feature",
    "test-only",
    "backup-maintenance",
    "devo-internal-source",
}


def test_work_start_creates_run_and_draft_artifacts(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "start", "--project", "sample", "--lane", "low-risk-ui-maintenance", "--goal", "Polish warning cleanup"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run_id = _only_work_run(workspace)
    package = load_work_package("sample", run_id, workspace_root=workspace)
    paths = _package_paths(workspace, run_id)
    assert package.status == WorkPackageStatus.DRAFT
    assert package.lane == "low-risk-ui-maintenance"
    assert package.validation_commands == ["dotnet-build-personalos"]
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert paths["operator_prompt"].exists()
    assert paths["scope_template"].name == "scope-template.md"
    assert "devo work scope-template" in result.output


def test_work_new_creates_run_package_template_and_resume_guidance(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "new", "--project", "sample", "--lane", "low-risk-ui-maintenance", "--goal", "Bootstrap UI work"],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    run_id = _only_work_run(workspace)
    package = load_work_package("sample", run_id, workspace_root=workspace)
    template_path = _package_root(workspace, run_id) / "scope-template.md"
    assert package.status == WorkPackageStatus.DRAFT
    assert package.goal == "Bootstrap UI work"
    assert package.lane == "low-risk-ui-maintenance"
    assert template_path.exists()
    assert f"Run: {run_id}" in result.output
    assert "Lane: low-risk-ui-maintenance" in result.output
    assert "scope-template.md" in result.output
    assert "devo work resume --project sample --run" in result.output
    assert run_id in result.output


def test_work_new_print_resume_outputs_operator_plan(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "new", "--project", "sample", "--lane", "docs-only", "--goal", "Bootstrap docs work", "--print-resume"],
        terminal_width=240,
    )

    run_id = _only_work_run(workspace)
    assert result.exit_code == 0, result.output
    assert "# Work Resume: Bootstrap docs work" in result.output
    assert "Next phase: scope" in result.output
    assert "devo work scope-template --project sample --run" in result.output
    assert run_id in result.output


def test_work_new_no_template_skips_template(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "new", "--project", "sample", "--lane", "low-risk-ui-maintenance", "--goal", "No template", "--no-template"],
        terminal_width=240,
    )

    run_id = _only_work_run(workspace)
    assert result.exit_code == 0, result.output
    assert "Scope template: skipped" in result.output
    assert not (_package_root(workspace, run_id) / "scope-template.md").exists()


def test_work_new_validates_unknown_lane_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "new", "--project", "sample", "--lane", "not-a-lane", "--goal", "Bad lane"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Unknown work lane" in result.output


def test_work_new_fails_clearly_for_unknown_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEVO_WORKSPACE", str(tmp_path / "workspace"))

    result = runner.invoke(
        app,
        ["work", "new", "--project", "missing", "--lane", "docs-only", "--goal", "Missing project"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Registered project not found: missing" in result.output


def test_all_built_in_lanes_load() -> None:
    lanes = {lane.id: lane for lane in list_lanes()}

    assert BUILT_IN_LANE_IDS.issubset(lanes)
    for lane_id in BUILT_IN_LANE_IDS:
        assert get_lane(lane_id).id == lane_id
    assert lanes["docs-only"].default_validation_commands == ["git-diff-check"]
    assert "No build required by default." in lanes["docs-only"].notes
    assert lanes["low-risk-ui-maintenance"].default_validation_commands == ["dotnet-build-personalos"]


def test_unknown_lane_fails_clearly(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        ["work", "start", "--project", "sample", "--lane", "not-a-lane", "--goal", "Unknown"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Unknown work lane" in result.output


def test_work_lanes_output_includes_all_built_in_lanes(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["work", "lanes"], terminal_width=240)

    assert result.exit_code == 0, result.output
    for lane_id in BUILT_IN_LANE_IDS:
        assert lane_id in result.output


def test_work_lane_show_includes_rules_and_validation_defaults() -> None:
    result = runner.invoke(app, ["work", "lane-show", "--lane", "docs-only"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "docs-only" in result.output
    assert "README.md" in result.output
    assert "source code" in result.output
    assert "git-diff-check" in result.output
    assert "No build required by default." in result.output


def test_work_import_scope_updates_package_and_tasks_artifact(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    scope = _scope_file(tmp_path)

    result = runner.invoke(
        app,
        ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(scope)],
        terminal_width=240,
    )

    assert result.exit_code == 0, result.output
    updated = load_work_package("sample", package.run_id, workspace_root=workspace)
    run_state = load_run("sample", package.run_id, workspace_root=workspace)
    tasks_path = workspace / "runs" / "sample" / package.run_id / "artifacts" / "tasks.md"
    assert updated.status == WorkPackageStatus.SCOPE_PROPOSED
    assert updated.proposed_items == ["Convert button titles", "Refresh page labels"]
    assert updated.approved_files == ["src/web/App.razor", "src/web/Nav.razor"]
    assert updated.validation_commands == ["dotnet-build-personalos"]
    assert run_state.status == RunStatus.TASKS_DRAFTED
    assert tasks_path.exists()
    assert "## Task T001" in tasks_path.read_text(encoding="utf-8")


def test_work_status_reports_artifact_paths(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    _scope_file(tmp_path)

    result = runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Work package:" in result.output
    assert "Operator prompt:" in result.output
    assert "work-package.json" in result.output
    assert "Suggested next command:" in result.output
    assert "devo work scope-template" in result.output


def test_work_scope_template_creates_template_file(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id], terminal_width=240)

    template_path = _package_root(workspace, package.run_id) / "scope-template.md"
    text = template_path.read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "scope-template.md" in result.output
    assert template_path.exists()
    for heading in [
        "## Selected Items",
        "## Exact Files",
        "## Allowed Changes",
        "## Forbidden Changes",
        "## Validation Command",
        "## Delivery Plan",
    ]:
        assert heading in text


def test_work_scope_template_includes_lane_rules_and_validation_command(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id], terminal_width=240)

    text = (_package_root(workspace, package.run_id) / "scope-template.md").read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "- Razor UI files" in text
    assert "- empty states" in text
    assert "- mechanical analyzer/warning fixes" in text
    assert "- DB changes" in text
    assert "- external API calls" in text
    assert "- dotnet-build-personalos" in text


def test_work_scope_template_includes_docs_only_defaults(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch, include_validation_command=False)
    package = start_work_package("sample", "docs-only", "Update docs", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id], terminal_width=240)

    text = (_package_root(workspace, package.run_id) / "scope-template.md").read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "- README.md" in text
    assert "- docs/**" in text
    assert "- source code" in text
    assert "- git-diff-check" in text
    assert "No build required by default." in text


def test_work_scope_template_uses_placeholder_when_validation_command_unavailable(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch, include_validation_command=False)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id], terminal_width=240)

    text = (_package_root(workspace, package.run_id) / "scope-template.md").read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "<validation-command-id>" in text


def test_work_scope_template_fails_if_work_package_missing(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run_state = create_run("sample", "Standalone run", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", run_state.run_id], terminal_width=240)

    assert result.exit_code != 0
    assert "Work package not found" in result.output


def test_work_scope_example_works_for_each_lane() -> None:
    for lane in list_lanes():
        result = runner.invoke(app, ["work", "scope-example", "--lane", lane.id], terminal_width=240)
        assert result.exit_code == 0, result.output
        assert "## Selected Items" in result.output
        assert "## Exact Files" in result.output
        assert "## Validation Command" in result.output


def test_work_scope_template_uses_registered_category_defaults(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch, include_validation_command=False)
    add_validation_command(
        "sample",
        "sample-build",
        "Build sample",
        "dotnet build Sample.slnx",
        "build",
        risk="high",
        approval_required=True,
        enabled=False,
        workspace_root=workspace,
    )
    package = start_work_package("sample", "warning-cleanup", "Fix warnings", workspace_root=workspace)

    result = runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id], terminal_width=240)

    text = (_package_root(workspace, package.run_id) / "scope-template.md").read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "- sample-build" in text
    assert "<project-build-command-id>" not in text


def test_work_next_for_draft_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Current status: draft" in result.output
    assert "Next action: Generate/fill/import scope" in result.output
    assert "devo work scope-template" in result.output
    assert "User approval needed: False" in result.output


def test_work_next_for_scope_proposed_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])

    result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Current status: scope_proposed" in result.output
    assert "Next action: Request approval bundle" in result.output
    assert "devo work request-approval-bundle" in result.output
    assert "User approval needed: True" in result.output


def test_work_next_for_approval_requested_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)

    result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Current status: approval_requested" in result.output
    assert "Next action: Approve bundle or wait" in result.output
    assert "devo approval bundle-approve" in result.output
    assert "User approval needed: True" in result.output


def test_work_next_for_approved_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)

    result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Current status: approved" in result.output
    assert "Next action: Implement approved scope" in result.output
    assert "devo work prompt --project sample" in result.output
    assert "--phase implement" in result.output
    assert "User approval needed: False" in result.output


def test_work_next_for_validated_and_delivered_status(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.IMPLEMENTED}), workspace_root=workspace)

    implemented_result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)
    save_work_package(package.model_copy(update={"status": WorkPackageStatus.VALIDATED}), workspace_root=workspace)

    validated_result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id], terminal_width=240)
    completed = complete_work_package("sample", package.run_id, "abc1234", "Delivered", workspace_root=workspace)
    delivered_result = runner.invoke(app, ["work", "next", "--project", "sample", "--run", completed.run_id], terminal_width=240)

    assert implemented_result.exit_code == 0, implemented_result.output
    assert "Current status: implemented" in implemented_result.output
    assert "Next action: Run validation" in implemented_result.output
    assert "--phase validate" in implemented_result.output
    assert validated_result.exit_code == 0, validated_result.output
    assert "Current status: validated" in validated_result.output
    assert "Next action: Generate delivery report and commit/push" in validated_result.output
    assert "--phase deliver" in validated_result.output
    assert delivered_result.exit_code == 0, delivered_result.output
    assert "Current status: delivered" in delivered_result.output
    assert "Next action: No action needed" in delivered_result.output
    assert "Required command: none" in delivered_result.output


def test_work_resume_suggests_scope_template_when_scope_missing(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: scope" in result.output
    assert "Next action: Generate and import scope" in result.output
    assert "devo work scope-template --project sample" in result.output
    assert "Do not implement until scope is imported" in result.output


def test_work_resume_suggests_approval_bundle_when_scope_exists(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: approval-request" in result.output
    assert "devo work request-approval-bundle --project sample" in result.output
    assert "Do not implement until the bundle is approved" in result.output


def test_work_resume_blocks_implementation_when_approval_pending(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: approval" in result.output
    assert "Approval status: pending" in result.output
    assert "devo approval bundle-approve --project sample" in result.output
    assert package.run_id in result.output
    assert bundle.bundle_id in result.output
    assert "Do not suggest or perform source edits yet" in result.output


def test_work_resume_suggests_implementation_when_bundle_approved(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: implement" in result.output
    assert "Approval status: approved" in result.output
    assert "devo work prompt --project sample" in result.output
    assert "--phase implement" in result.output
    assert "Implement only the imported approved scope" in result.output
    assert "DB, migrations, appsettings, secrets, scripts, backups, user data" in result.output


def test_work_resume_suggests_delivery_after_validation_passes(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)
    _write_validation_record(workspace, package.run_id, "20260722-100000-build", ValidationRunStatus.PASSED)
    _write_git_delivery_report(workspace, package.run_id)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: deliver" in result.output
    assert "Latest validation: 20260722-100000-build (passed)" in result.output
    assert "Latest delivery status: ready; branch=master; head=def5678; clean=True" in result.output
    assert "devo git delivery-check --project sample" in result.output
    assert "devo work complete --project sample" in result.output


def test_work_resume_says_no_action_needed_when_delivered(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    completed = complete_work_package("sample", package.run_id, "abc1234", "Delivered", workspace_root=workspace)

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", completed.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: done" in result.output
    assert "Next action: No action needed" in result.output
    assert "devo work history --project sample" in result.output
    assert "No implementation, validation, or delivery action is needed" in result.output


def test_work_resume_handles_older_package_missing_optional_fields(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "docs-only", "Update docs", workspace_root=workspace)
    package_path = _package_paths(workspace, package.run_id)["json"]
    data = json.loads(package_path.read_text(encoding="utf-8"))
    data.pop("approval_bundle_status", None)
    data.pop("validation_run_id", None)
    data.pop("final_git_status", None)
    package_path.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Next phase: scope" in result.output
    assert "Lane: docs-only" in result.output
    assert "source code" in result.output


def test_work_prompt_creates_phase_prompt_file(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)

    result = runner.invoke(
        app,
        ["work", "prompt", "--project", "sample", "--run", package.run_id, "--phase", "implement"],
        terminal_width=240,
    )

    prompt_path = _package_root(workspace, package.run_id) / "operator-prompt-implement.md"
    assert result.exit_code == 0, result.output
    assert "operator-prompt-implement.md" in result.output
    assert prompt_path.exists()


def test_work_prompt_rejects_unknown_phase(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(
        app,
        ["work", "prompt", "--project", "sample", "--run", package.run_id, "--phase", "launch"],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Unknown work prompt phase" in result.output


def test_work_prompt_includes_scope_and_stop_rules(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = _prepared_package(workspace, tmp_path)

    result = runner.invoke(
        app,
        ["work", "prompt", "--project", "sample", "--run", package.run_id, "--phase", "validate"],
        terminal_width=240,
    )

    prompt = (_package_root(workspace, package.run_id) / "operator-prompt-validate.md").read_text(encoding="utf-8")
    assert result.exit_code == 0, result.output
    assert "src/web/App.razor" in prompt
    assert "src/web/Nav.razor" in prompt
    assert "DB, migrations, appsettings, secrets, scripts, backups, user data" in prompt
    assert "dotnet-build-personalos" in prompt
    assert "## Stop Conditions" in prompt


def test_work_list_shows_recent_work_packages_and_runs_without_package(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run_without_package = create_run("sample", "Standalone planning run", workspace_root=workspace)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    result = runner.invoke(app, ["work", "list", "--project", "sample", "--limit", "10"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert package.run_id in result.output
    assert "Fix small UI issues" in result.output
    assert "Has work package: True" in result.output
    assert run_without_package.run_id in result.output
    assert "Standalone planning run" in result.output
    assert "No work-package artifact found." in result.output


def test_work_list_limit_is_respected(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    start_work_package("sample", "low-risk-ui-maintenance", "First package", workspace_root=workspace)
    start_work_package("sample", "low-risk-ui-maintenance", "Second package", workspace_root=workspace)
    start_work_package("sample", "low-risk-ui-maintenance", "Third package", workspace_root=workspace)

    result = runner.invoke(app, ["work", "list", "--project", "sample", "--limit", "2"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert result.output.count("Run:") == 2
    assert result.output.count("Goal:") == 2


def test_work_history_prioritizes_delivered_packages(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    open_package = start_work_package("sample", "low-risk-ui-maintenance", "Open work", workspace_root=workspace)
    delivered_package = start_work_package("sample", "low-risk-ui-maintenance", "Delivered work", workspace_root=workspace)
    complete_work_package("sample", delivered_package.run_id, "abc1234", "Delivered polish", workspace_root=workspace)

    result = runner.invoke(app, ["work", "history", "--project", "sample", "--limit", "10"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert result.output.index(delivered_package.run_id) < result.output.index(open_package.run_id)
    assert "Status: delivered" in result.output
    assert "Commit: abc1234" in result.output
    assert "Delivery summary: Delivered polish" in result.output


def test_work_list_missing_optional_fields_do_not_crash(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    package_path = _package_paths(workspace, package.run_id)["json"]
    data = json.loads(package_path.read_text(encoding="utf-8"))
    data.pop("approval_bundle_status", None)
    data.pop("commit_hash", None)
    data.pop("delivery_summary", None)
    package_path.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["work", "list", "--project", "sample"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Approval bundle status: not available" in result.output
    assert "Commit: none" in result.output


def test_project_activity_includes_git_status_and_recent_evidence(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    _init_git_repo(project_path)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    complete_work_package("sample", package.run_id, "abc1234", "Delivered polish", workspace_root=workspace)
    _write_validation_record(workspace, package.run_id, "20260722-100000-build", ValidationRunStatus.PASSED)

    result = runner.invoke(app, ["project", "activity", "--project", "sample", "--limit", "5"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Project activity: sample" in result.output
    assert "Current Git status: branch=" in result.output
    assert "Recent runs:" in result.output
    assert package.run_id in result.output
    assert "Delivered work packages:" in result.output
    assert "abc1234" in result.output
    assert "Latest validation runs:" in result.output
    assert "20260722-100000-build" in result.output
    assert "Suggested next action:" in result.output


def test_work_complete_updates_status_and_delivery_fields(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    completed = complete_work_package(
        "sample",
        package.run_id,
        commit_hash="abc1234",
        delivery_summary="Delivered small UI fixes",
        workspace_root=workspace,
    )

    assert completed.status == WorkPackageStatus.DELIVERED
    assert completed.delivered_at is not None
    assert completed.commit_hash == "abc1234"
    assert completed.delivery_summary == "Delivered small UI fixes"


def test_work_complete_stores_latest_validation_bundle_and_git_evidence(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])
    bundle = create_approval_bundle("sample", package.run_id, "T001", workspace_root=workspace)
    approve_approval_bundle("sample", package.run_id, bundle.bundle_id, approved_by="Manas", workspace_root=workspace)
    _write_validation_record(workspace, package.run_id, "20260722-100000-build", ValidationRunStatus.PASSED)
    _write_git_delivery_report(workspace, package.run_id)

    completed = complete_work_package(
        "sample",
        package.run_id,
        commit_hash="def5678",
        delivery_summary="Delivered and pushed",
        workspace_root=workspace,
    )

    assert completed.status == WorkPackageStatus.DELIVERED
    assert completed.validation_run_id == "20260722-100000-build"
    assert completed.validation_status == "passed"
    assert completed.approval_bundle_status == "approved"
    assert completed.final_git_status == "ready; branch=master; head=def5678; clean=True"


def test_work_status_shows_delivered_state(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    complete_result = runner.invoke(
        app,
        [
            "work",
            "complete",
            "--project",
            "sample",
            "--run",
            package.run_id,
            "--commit",
            "abc1234",
            "--message",
            "Delivered small UI fixes",
        ],
        terminal_width=240,
    )
    status_result = runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id], terminal_width=240)

    assert complete_result.exit_code == 0, complete_result.output
    assert status_result.exit_code == 0, status_result.output
    assert "Status: delivered" in status_result.output
    assert "Delivery commit: abc1234" in status_result.output
    assert "Validation: none (none)" in status_result.output
    assert "Next action: No action needed" in status_result.output


def test_work_complete_fails_if_no_work_package_exists(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    run_state = create_run("sample", "Run without work package", workspace_root=workspace)

    result = runner.invoke(
        app,
        [
            "work",
            "complete",
            "--project",
            "sample",
            "--run",
            run_state.run_id,
            "--commit",
            "abc1234",
            "--message",
            "Should fail",
        ],
        terminal_width=240,
    )

    assert result.exit_code != 0
    assert "Work package not found" in result.output


def test_import_scope_requires_complete_sections(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    scope = tmp_path / "scope.md"
    scope.write_text("# Selected items\n\n- one item\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Scope file is missing required sections"):
        from devo.work_packages import import_work_scope

        import_work_scope("sample", package.run_id, scope, workspace_root=workspace)


def test_lane_registry_exposes_low_risk_ui_maintenance() -> None:
    lanes = {lane.id: lane for lane in list_lanes()}

    assert "low-risk-ui-maintenance" in lanes
    lane = lanes["low-risk-ui-maintenance"]
    assert "DB changes" in lane.forbidden
    assert "dotnet-build-personalos" in lane.default_validation_commands


def test_operator_prompt_contains_stop_conditions_and_delivery_rules(tmp_path: Path, monkeypatch) -> None:
    workspace, _project_path = _workspace(tmp_path, monkeypatch)
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])

    operator_prompt = _package_paths(workspace, package.run_id)["operator_prompt"].read_text(encoding="utf-8")

    assert "## Stop Conditions" in operator_prompt
    assert "## Final Report Format" in operator_prompt
    assert "Project path:" in operator_prompt
    assert "dotnet-build-personalos" in operator_prompt


def test_work_commands_do_not_modify_target_project_files(tmp_path: Path, monkeypatch) -> None:
    workspace, project_path = _workspace(tmp_path, monkeypatch)
    sentinel = project_path / "README.md"
    before = sentinel.read_text(encoding="utf-8")
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)

    runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])
    runner.invoke(app, ["work", "status", "--project", "sample", "--run", package.run_id])
    runner.invoke(app, ["work", "next", "--project", "sample", "--run", package.run_id])
    runner.invoke(app, ["work", "resume", "--project", "sample", "--run", package.run_id])
    runner.invoke(app, ["work", "scope-template", "--project", "sample", "--run", package.run_id])
    runner.invoke(app, ["work", "scope-example", "--lane", "low-risk-ui-maintenance"])
    runner.invoke(app, ["work", "prompt", "--project", "sample", "--run", package.run_id, "--phase", "implement"])
    runner.invoke(app, ["work", "list", "--project", "sample"])
    runner.invoke(app, ["work", "history", "--project", "sample"])
    runner.invoke(app, ["work", "new", "--project", "sample", "--lane", "docs-only", "--goal", "Read-only bootstrap"])
    runner.invoke(app, ["project", "activity", "--project", "sample"])
    complete_work_package("sample", package.run_id, "abc1234", "Delivered", workspace_root=workspace)

    assert sentinel.read_text(encoding="utf-8") == before


def _workspace(tmp_path: Path, monkeypatch, include_validation_command: bool = True) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
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
    run_state = ContextSnapshot(context_state_path=context_path, approval_record_path=approval_path, approved_artifact_paths=[])
    assert run_state.context_state_path == context_path
    if include_validation_command:
        add_validation_command(
            "sample",
            "dotnet-build-personalos",
            "Build PersonalOS",
            "dotnet build PersonalOS.slnx",
            "build",
            risk="high",
            approval_required=True,
            enabled=False,
            workspace_root=workspace,
        )
    return workspace, project_path


def _scope_file(tmp_path: Path) -> Path:
    scope = tmp_path / "scope.md"
    scope.write_text(
        "\n".join(
            [
                "# Selected items",
                "- Convert button titles",
                "- Refresh page labels",
                "",
                "# Exact files",
                "- src/web/App.razor",
                "- src/web/Nav.razor",
                "",
                "# Allowed changes",
                "- UI-only Razor markup updates",
                "",
                "# Forbidden changes",
                "- DB, migrations, appsettings, secrets, scripts, backups, user data",
                "",
                "# Validation command",
                "- dotnet-build-personalos",
                "",
                "# Delivery plan",
                "- Run build validation after approval",
                "- Commit and push after validation passes",
            ]
        ),
        encoding="utf-8",
    )
    return scope


def _only_work_run(workspace: Path) -> str:
    run_root = workspace / "runs" / "sample"
    run_ids = [path.name for path in run_root.iterdir() if path.is_dir()]
    assert len(run_ids) == 1
    return run_ids[0]


def _prepared_package(workspace: Path, tmp_path: Path):
    package = start_work_package("sample", "low-risk-ui-maintenance", "Fix small UI issues", workspace_root=workspace)
    import_result = runner.invoke(app, ["work", "import-scope", "--project", "sample", "--run", package.run_id, "--file", str(_scope_file(tmp_path))])
    assert import_result.exit_code == 0, import_result.output
    return load_work_package("sample", package.run_id, workspace_root=workspace)


def _package_root(workspace: Path, run_id: str) -> Path:
    return workspace / "runs" / "sample" / run_id / "artifacts" / "work-package"


def _package_paths(workspace: Path, run_id: str) -> dict[str, Path]:
    root = _package_root(workspace, run_id)
    return {
        "json": root / "work-package.json",
        "markdown": root / "work-package.md",
        "operator_prompt": root / "operator-prompt.md",
        "scope_template": root / "scope-template.md",
    }


def _write_validation_record(
    workspace: Path,
    run_id: str,
    validation_run_id: str,
    status: ValidationRunStatus,
) -> None:
    validation_dir = workspace / "runs" / "sample" / run_id / "artifacts" / "validation-runs" / validation_run_id
    validation_dir.mkdir(parents=True)
    record = ValidationRunRecord(
        validation_run_id=validation_run_id,
        project_name="sample",
        run_id=run_id,
        task_id="T001",
        command_id="dotnet-build-personalos",
        command_name="Build PersonalOS",
        command="dotnet build PersonalOS.slnx",
        working_dir=workspace,
        category=ValidationCommandCategory.BUILD,
        risk_level=ValidationRiskLevel.HIGH,
        approval_required=True,
        status=status,
        exit_code=0,
        started_at=datetime(2026, 7, 22, 10, 0, tzinfo=UTC),
    )
    (validation_dir / "validation-run.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")


def _write_git_delivery_report(workspace: Path, run_id: str) -> None:
    delivery_dir = workspace / "runs" / "sample" / run_id / "artifacts" / "git-delivery"
    delivery_dir.mkdir(parents=True)
    report = {
        "created_at": "2026-07-22T10:05:00+00:00",
        "delivery_check": {
            "readiness": "ready",
            "status": {
                "current_branch": "master",
                "head_commit": "def5678",
                "working_tree_clean": True,
            },
        },
    }
    (delivery_dir / "git-delivery-report-20260722-100500.json").write_text(json.dumps(report), encoding="utf-8")


def _init_git_repo(project_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=project_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=project_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tests"], cwd=project_path, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=project_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=project_path, check=True, capture_output=True, text=True)
