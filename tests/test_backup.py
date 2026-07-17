from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from devo.backups import create_backup, list_backups, restore_backup, verify_backup
from devo.main import app

runner = CliRunner()


def test_backup_create_copies_workspace_roots(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups", label="sample")

    backup_workspace = manifest.backup_path / "workspace"
    assert (backup_workspace / "projects" / "sample" / "project.json").exists()
    assert (backup_workspace / "runs" / "sample" / "run-1" / "run-state.json").exists()
    assert (backup_workspace / "current.json").exists()


def test_backup_create_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    workspace, _target = _sample_workspace(tmp_path)
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))

    manifest = create_backup(tmp_path / "backups", label="before-task")

    manifest_file = manifest.backup_path / "backup-manifest.json"
    assert manifest_file.exists()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert data["label"] == "before-task"
    assert data["included_roots"] == ["projects", "runs", "current.json"]


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

    (workspace / "current.json").write_text('{"project_name":"sample"}', encoding="utf-8")
    return workspace, target_project
