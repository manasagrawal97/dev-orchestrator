from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.backups import cleanup_backups, create_backup, list_backups, restore_backup, verify_backup
from devo.main import app

runner = CliRunner()


def test_backup_create_copies_workspace_roots(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups", label="sample")

    backup_workspace = manifest.backup_path / "workspace"
    assert (backup_workspace / "projects" / "sample" / "project.json").exists()
    assert (backup_workspace / "runs" / "sample" / "run-1" / "run-state.json").exists()
    assert (backup_workspace / "environment" / "sample" / "environment-snapshot.json").exists()
    assert (backup_workspace / "current.json").exists()


def test_backup_create_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups", label="before-task")

    manifest_file = manifest.backup_path / "backup-manifest.json"
    assert manifest_file.exists()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert data["label"] == "before-task"
    assert data["included_roots"] == ["projects", "runs", "environment", "current.json"]


def test_manifest_includes_counts_hashes_paths_and_timestamp(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups")

    assert manifest.file_count > 0
    assert manifest.total_bytes > 0
    assert manifest.source_workspace_path == workspace.resolve()
    assert manifest.backup_path.exists()
    assert manifest.created_at is not None
    assert manifest.sha256_by_file
    assert all(path.startswith("workspace/") for path in manifest.sha256_by_file)


def test_backup_verify_passes_for_fresh_backup(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    manifest = create_backup(tmp_path / "backups")

    verified = verify_backup(manifest.backup_path)

    assert verified.file_count == manifest.file_count
    assert verified.total_bytes == manifest.total_bytes


def test_backup_verify_fails_when_file_modified(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    manifest = create_backup(tmp_path / "backups")
    copied_file = manifest.backup_path / "workspace" / "projects" / "sample" / "project.json"
    copied_file.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="hash mismatch|total bytes mismatch"):
        verify_backup(manifest.backup_path)


def test_backup_verify_fails_when_file_missing(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    manifest = create_backup(tmp_path / "backups")
    copied_file = manifest.backup_path / "workspace" / "projects" / "sample" / "project.json"
    copied_file.unlink()

    with pytest.raises(ValueError, match="file count mismatch"):
        verify_backup(manifest.backup_path)


def test_backup_list_shows_created_backups(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    create_backup(backup_root, label="one")

    listed = list_backups(backup_root)
    result = runner.invoke(app, ["backup", "list", "--dest", str(backup_root)], terminal_width=200)

    assert len(listed) == 1
    assert result.exit_code == 0
    assert "devo-workspace-backup" in result.output
    assert "one" in result.output


def test_restore_copies_backup_workspace_to_empty_destination(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    manifest = create_backup(tmp_path / "backups")
    restore_dest = tmp_path / "restored-workspace"

    restore_backup(manifest.backup_path, restore_dest)

    assert (restore_dest / "projects" / "sample" / "project.json").exists()
    assert (restore_dest / "runs" / "sample" / "run-1" / "run-state.json").exists()
    assert (restore_dest / "current.json").exists()


def test_restore_refuses_non_empty_destination(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    manifest = create_backup(tmp_path / "backups")
    restore_dest = tmp_path / "restored-workspace"
    restore_dest.mkdir()
    (restore_dest / "existing.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(ValueError, match="must be empty"):
        restore_backup(manifest.backup_path, restore_dest)


def test_backup_excludes_cache_and_temporary_files(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    (workspace / "projects" / "sample" / "__pycache__").mkdir()
    (workspace / "projects" / "sample" / "__pycache__" / "x.pyc").write_text("cache", encoding="utf-8")
    (workspace / "runs" / ".pytest_cache").mkdir()
    (workspace / "runs" / ".pytest_cache" / "README.md").write_text("cache", encoding="utf-8")
    (workspace / "projects" / "sample" / "note.tmp").write_text("tmp", encoding="utf-8")
    (workspace / "projects" / "sample" / "state.lock").write_text("lock", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups")

    copied_paths = set(manifest.sha256_by_file)
    assert not any("__pycache__" in path for path in copied_paths)
    assert not any(".pytest_cache" in path for path in copied_paths)
    assert not any(path.endswith(".tmp") for path in copied_paths)
    assert not any(path.endswith(".lock") for path in copied_paths)


def test_missing_workspace_fails_safely(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "missing-workspace"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(app, ["backup", "create", "--dest", str(tmp_path / "backups")])

    assert result.exit_code != 0
    assert "Workspace does not exist" in result.output


def test_backup_does_not_include_git_venv_or_target_project_contents(tmp_path: Path, monkeypatch) -> None:
    workspace, target_project = _sample_workspace(tmp_path)
    (workspace / ".git").mkdir()
    (workspace / ".git" / "config").write_text("git", encoding="utf-8")
    (workspace / ".venv").mkdir()
    (workspace / ".venv" / "pyvenv.cfg").write_text("venv", encoding="utf-8")
    (target_project / "secret-source.txt").write_text("do not copy", encoding="utf-8")
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups")

    copied_paths = set(manifest.sha256_by_file)
    assert not any(".git" in path for path in copied_paths)
    assert not any(".venv" in path for path in copied_paths)
    assert not (manifest.backup_path / "workspace" / "secret-source.txt").exists()
    assert not list((manifest.backup_path / "workspace").rglob("secret-source.txt"))


def test_backup_cli_create_verify_and_restore(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    restore_dest = tmp_path / "restored"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    create_result = runner.invoke(
        app,
        ["backup", "create", "--dest", str(backup_root), "--label", "cli"],
        terminal_width=200,
    )
    backup_folder = next(backup_root.glob("devo-workspace-backup-*-cli"))
    verify_result = runner.invoke(app, ["backup", "verify", "--path", str(backup_folder)], terminal_width=200)
    restore_result = runner.invoke(
        app,
        ["backup", "restore", "--backup", str(backup_folder), "--dest", str(restore_dest)],
        terminal_width=200,
    )

    assert create_result.exit_code == 0
    assert "Created backup" in create_result.output
    assert verify_result.exit_code == 0
    assert "Verified backup" in verify_result.output
    assert restore_result.exit_code == 0
    assert "Restored backup" in restore_result.output
    assert (restore_dest / "projects" / "sample" / "project.json").exists()



def test_backup_cli_create_supports_protected_manifest_flag(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    result = runner.invoke(
        app,
        ["backup", "create", "--dest", str(backup_root), "--label", "milestone", "--protect"],
        terminal_width=200,
    )

    assert result.exit_code == 0
    backup_folder = next(backup_root.glob("devo-workspace-backup-*-milestone"))
    data = json.loads((backup_folder / "backup-manifest.json").read_text(encoding="utf-8"))
    assert data["protected"] is True
    assert "Protected: True" in result.output


def test_backup_cleanup_keeps_latest_3_unprotected_backups_by_default(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    created = _create_ordered_backups(backup_root, count=5)

    result = cleanup_backups(backup_root)

    deleted_names = {path.name for path in result.deleted_backups}
    assert deleted_names == {created[0].backup_path.name, created[1].backup_path.name}
    assert len(result.retained_backups) == 3
    assert not created[0].backup_path.exists()
    assert not created[1].backup_path.exists()
    assert created[2].backup_path.exists()


def test_backup_cleanup_never_deletes_protected_backups(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    created = _create_ordered_backups(backup_root, count=11)
    protected = create_backup(backup_root, label="protected", protect=True)
    _set_manifest_created_at(protected.backup_path, datetime(2026, 1, 1, tzinfo=UTC))

    result = cleanup_backups(backup_root, keep=1)

    assert protected.backup_path.exists()
    assert protected.backup_path in result.skipped_protected_backups
    assert any(path.name == created[0].backup_path.name for path in result.deleted_backups)


def test_backup_cleanup_skips_invalid_and_missing_manifest_folders(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    create_backup(backup_root, label="valid")
    missing_manifest = backup_root / "devo-workspace-backup-20260101-000000-missing"
    missing_manifest.mkdir(parents=True)
    invalid_manifest = backup_root / "devo-workspace-backup-20260101-000001-invalid"
    invalid_manifest.mkdir(parents=True)
    (invalid_manifest / "backup-manifest.json").write_text("not-json", encoding="utf-8")
    unknown = backup_root / "not-a-devo-backup"
    unknown.mkdir()

    result = cleanup_backups(backup_root, keep=0)

    assert missing_manifest.exists()
    assert invalid_manifest.exists()
    assert unknown.exists()
    skipped = "\n".join(result.skipped_invalid_backups)
    assert "missing" in skipped
    assert "invalid" in skipped
    assert "unknown folder" in skipped


def test_backup_cleanup_cli_supports_dry_run(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    created = _create_ordered_backups(backup_root, count=2)

    result = runner.invoke(
        app,
        ["backup", "cleanup", "--dest", str(backup_root), "--keep", "1", "--dry-run"],
        terminal_width=200,
    )

    assert result.exit_code == 0
    assert "Dry run: True" in result.output
    assert "Would delete backups" in result.output
    assert created[0].backup_path.exists()


def _sample_workspace(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    target_project = tmp_path / "target-project"
    target_project.mkdir()
    (target_project / "README.md").write_text("# Target\n", encoding="utf-8")

    project_dir = workspace / "projects" / "sample"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text(
        json.dumps(
            {
                "name": "sample",
                "path": str(target_project),
                "looks_like_software_project": True,
                "detected_markers": ["README.md"],
                "created_at": "2026-07-15T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (project_dir / "context").mkdir()
    (project_dir / "context" / "approved.md").write_text("approved", encoding="utf-8")

    run_dir = workspace / "runs" / "sample" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "run-state.json").write_text('{"status":"RUN_CLOSED"}', encoding="utf-8")
    (run_dir / "artifacts").mkdir()
    (run_dir / "artifacts" / "summary.md").write_text("summary", encoding="utf-8")


    environment_dir = workspace / "environment" / "sample"
    environment_dir.mkdir(parents=True)
    (environment_dir / "environment-snapshot.json").write_text('{"name":"sample"}', encoding="utf-8")

    (workspace / "current.json").write_text('{"project_name":"sample"}', encoding="utf-8")
    return workspace, target_project


def _create_ordered_backups(backup_root: Path, count: int):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    created = []
    for index in range(count):
        manifest = create_backup(backup_root, label=f"backup-{index:02d}")
        created_at = start + timedelta(hours=index)
        _set_manifest_created_at(manifest.backup_path, created_at)
        created.append(manifest.model_copy(update={"created_at": created_at}))
    return created


def _set_manifest_created_at(backup_path: Path, created_at: datetime) -> None:
    manifest_file = backup_path / "backup-manifest.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    data["created_at"] = created_at.isoformat().replace("+00:00", "Z")
    manifest_file.write_text(json.dumps(data), encoding="utf-8")