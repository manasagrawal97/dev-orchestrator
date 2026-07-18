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


def test_install_script_defaults_to_every_12_hours() -> None:
    install_script = _script("install-devo-backup-task.ps1")

    assert '[string]$Frequency = "Every12Hours"' in install_script
    assert "New-TimeSpan -Hours 12" in install_script


def test_backup_script_defaults_retention_count_to_10() -> None:
    backup_script = _script("backup-devo-workspace.ps1")

    assert "[int]$RetentionCount = 10" in backup_script


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


def _script(name: str) -> str:
    return (SCRIPT_DIR / name).read_text(encoding="utf-8")
