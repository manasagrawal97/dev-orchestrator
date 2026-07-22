from __future__ import annotations

from pathlib import Path

SCRIPT_DIR = Path("scripts/recovery")
REQUIRED_SCRIPTS = (
    "backup-devo-workspace.ps1",
    "restore-devo-workspace.ps1",
    "install-devo-backup-task.ps1",
    "uninstall-devo-backup-task.ps1",
    "check-devo-recovery-status.ps1",
)


def test_required_recovery_scripts_exist() -> None:
    for script_name in REQUIRED_SCRIPTS:
        assert (SCRIPT_DIR / script_name).exists()


def test_scripts_contain_expected_parameter_names() -> None:
    backup_script = _script("backup-devo-workspace.ps1")
    restore_script = _script("restore-devo-workspace.ps1")
    install_script = _script("install-devo-backup-task.ps1")

    for parameter in ("$BackupRoot", "$RepoPath", "$Label", "$RetentionCount", "$Verify", "$Cleanup", "$Protect", "$LogRoot"):
        assert parameter in backup_script
    for parameter in ("$BackupRoot", "$RepoPath", "$InstallSchedule", "$Force"):
        assert parameter in restore_script
    for parameter in ("$BackupRoot", "$RepoPath", "$TaskName", "$Frequency", "$RunNow", "$RetentionCount"):
        assert parameter in install_script


def test_scripts_reference_devo_backup_create_verify_and_restore() -> None:
    backup_script = _script("backup-devo-workspace.ps1")
    restore_script = _script("restore-devo-workspace.ps1")

    assert '"backup", "create"' in backup_script
    assert '"backup", "verify"' in backup_script
    assert '"backup", "cleanup"' in backup_script
    assert '"backup", "verify"' in restore_script
    assert '"backup", "restore"' in restore_script


def test_install_script_references_expected_task_name() -> None:
    install_script = _script("install-devo-backup-task.ps1")

    assert "DevOrchestrator Workspace Backup" in install_script
    assert "Register-ScheduledTask" in install_script


def test_install_script_defaults_to_every_6_hours() -> None:
    install_script = _script("install-devo-backup-task.ps1")

    assert '[string]$Frequency = "Every6Hours"' in install_script
    assert "New-TimeSpan -Hours 6" in install_script
    assert '[int]$RetentionCount = 3' in install_script


def test_install_script_registers_hidden_powershell_window() -> None:
    install_script = _script("install-devo-backup-task.ps1")

    assert "-WindowStyle Hidden" in install_script
    assert 'Write-Host "WindowStyle: Hidden"' in install_script


def test_backup_script_defaults_retention_count_to_3() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "[int]$RetentionCount = 3" in backup_script


def test_backup_script_supports_protect() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "[switch]$Protect" in backup_script
    assert '"--protect"' in backup_script


def test_restore_script_safely_handles_existing_workspace() -> None:
    restore_script = _script("restore-devo-workspace.ps1")

    assert "workspace.pre-restore-" in restore_script
    assert "Move-Item" in restore_script
    assert '"backup", "restore"' in restore_script


def test_check_status_script_references_latest_backup_verification() -> None:
    status_script = _script("check-devo-recovery-status.ps1")

    assert "Latest backup verifies" in status_script
    assert "backup verify" in status_script
    assert "older than 24 hours" in status_script
    assert "Select-Object -First 3" in status_script


def test_recovery_docs_exist_and_mention_commands() -> None:
    docs = Path("docs/recovery.md")
    text = docs.read_text(encoding="utf-8")

    assert docs.exists()
    assert ".\\scripts\\recovery\\backup-devo-workspace.ps1" in text
    assert ".\\scripts\\recovery\\restore-devo-workspace.ps1" in text
    assert ".\\scripts\\recovery\\install-devo-backup-task.ps1" in text
    assert ".\\scripts\\recovery\\check-devo-recovery-status.ps1" in text


def test_readme_mentions_recovery_docs() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "docs/recovery.md" in readme


def test_backup_script_cleanup_requires_successful_verify_text() -> None:
    backup_script = _script("backup-devo-workspace.ps1")
    verify_index = backup_script.index('"backup", "verify"')
    cleanup_index = backup_script.index('"backup", "cleanup"')

    assert verify_index < cleanup_index
    assert "if ($Cleanup -and $Verify)" in backup_script



def test_backup_script_parses_created_backup_output_line() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "Get-CreatedBackupPathFromOutput" in backup_script
    assert "Created backup" in backup_script
    assert "^\\s*Created backup\\s*(.*)$" in backup_script


def test_backup_script_falls_back_to_manifest_scan_after_script_start() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "Get-CreatedBackupPathFromManifestFallback" in backup_script
    assert "backup-manifest.json" in backup_script
    assert "$scriptStartUtc" in backup_script
    assert "created_at" in backup_script
    assert "$manifestLabel -ne $ExpectedLabel" in backup_script


def test_backup_script_prints_captured_output_on_detection_failure() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "Write-CapturedOutput" in backup_script
    assert "Captured backup create output" in backup_script
    assert "Could not determine created backup path" in backup_script


def test_backup_script_handles_paths_with_spaces_as_literal_paths() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "Test-Path -LiteralPath $clean" in backup_script
    assert "Resolve-Path -LiteralPath $clean" in backup_script
    assert "$parts -join \" \"" in backup_script


def test_backup_script_fails_if_created_path_is_still_incomplete() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert '$createdBackupPath.EndsWith(".incomplete")' in backup_script
    assert "Backup path is still incomplete" in backup_script


def test_install_script_passes_expected_backup_wrapper_arguments() -> None:
    install_script = _script("install-devo-backup-task.ps1")

    assert '-RepoPath `"$RepoPath`"' in install_script
    assert '-BackupRoot `"$BackupRoot`"' in install_script
    assert '-Label `"scheduled`"' in install_script
    assert "-RetentionCount $RetentionCount" in install_script


def test_recovery_docs_describe_current_backup_policy_and_repo_url() -> None:
    text = Path("docs/recovery.md").read_text(encoding="utf-8")

    assert "every 6 hours" in text
    assert "latest 3 normal backups" in text
    assert "Manual backup after every task is not required" in text
    assert "GitHub protects source code" in text
    assert "Google Drive backup protects Devo workspace/context" in text
    assert "https://github.com/manasagrawal97/dev-orchestrator.git" in text
    assert ("https://github.com/manasagrawal97/" + "DevOrchestrator.git") not in text


def test_readme_describes_current_backup_policy() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "every 6 hours" in readme
    assert "latest 3 normal backups" in readme
    assert "Manual backup after every task is not required" in readme
    assert "GitHub" in readme and "source code" in readme
    assert "workspace/context" in readme


def test_old_github_repo_url_is_absent_from_docs_and_recovery_scripts() -> None:
    old_url = "https://github.com/manasagrawal97/" + "DevOrchestrator.git"
    checked_paths = [Path("README.md"), Path("docs/recovery.md"), *SCRIPT_DIR.glob("*.ps1")]

    for path in checked_paths:
        assert old_url not in path.read_text(encoding="utf-8")

def _script(name: str) -> str:
    return (SCRIPT_DIR / name).read_text(encoding="utf-8")
