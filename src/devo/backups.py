from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from .projects import get_workspace_root
from .schemas import BackupCleanupResult, BackupManifest

BACKUP_SCHEMA_VERSION = "1"
BACKUP_FOLDER_PREFIX = "devo-workspace-backup"
MANIFEST_NAME = "backup-manifest.json"
WORKSPACE_BACKUP_DIR = "workspace"

INCLUDED_ROOTS = ("projects", "runs", "environment", "current.json")
OPTIONAL_INCLUDED_ROOTS = {"environment", "current.json"}
EXCLUDED_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "*.tmp",
    "*.lock",
    "*.swp",
    "*~",
    ".DS_Store",
)

EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git", ".venv"}
EXCLUDED_FILE_NAMES = {".DS_Store"}
EXCLUDED_FILE_SUFFIXES = {".tmp", ".lock", ".swp"}


def create_backup(
    dest: Path,
    label: str | None = None,
    workspace_root: Path | None = None,
    protect: bool = False,
) -> BackupManifest:
    source_workspace = (workspace_root or get_workspace_root()).resolve()
    if not source_workspace.exists():
        msg = f"Workspace does not exist: {source_workspace}"
        raise ValueError(msg)
    if not source_workspace.is_dir():
        msg = f"Workspace path must be a directory: {source_workspace}"
        raise ValueError(msg)

    backup_root = dest.expanduser().resolve()
    backup_root.mkdir(parents=True, exist_ok=True)

    folder_name = _backup_folder_name(label)
    final_backup_path = _unique_child_path(backup_root, folder_name)
    temp_backup_path = _unique_child_path(backup_root, f"{final_backup_path.name}.incomplete")

    warnings: list[str] = []
    copied_files: list[Path] = []

    try:
        backup_workspace = temp_backup_path / WORKSPACE_BACKUP_DIR
        backup_workspace.mkdir(parents=True)

        for root_name in INCLUDED_ROOTS:
            source = source_workspace / root_name
            if not source.exists():
                if root_name not in OPTIONAL_INCLUDED_ROOTS:
                    warnings.append(f"Included root is missing: {root_name}")
                continue

            if source.is_dir():
                copied_files.extend(_copy_directory(source, backup_workspace / root_name, source_workspace))
            elif source.is_file():
                target = backup_workspace / root_name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                copied_files.append(target)

        sha256_by_file: dict[str, str] = {}
        total_bytes = 0
        for file_path in sorted(copied_files):
            relative_path = _relative_posix(file_path, temp_backup_path)
            sha256_by_file[relative_path] = _sha256(file_path)
            total_bytes += file_path.stat().st_size

        manifest = BackupManifest(
            schema_version=BACKUP_SCHEMA_VERSION,
            created_at=datetime.now(UTC),
            source_workspace_path=source_workspace,
            backup_path=final_backup_path,
            label=label,
            included_roots=list(INCLUDED_ROOTS),
            excluded_patterns=list(EXCLUDED_PATTERNS),
            file_count=len(copied_files),
            total_bytes=total_bytes,
            sha256_by_file=sha256_by_file,
            warnings=warnings,
            tool_version="0.1.0",
            git_commit_hash=_git_output(["git", "rev-parse", "HEAD"]),
            git_branch=_git_output(["git", "branch", "--show-current"]),
            protected=protect,
        )

        (temp_backup_path / MANIFEST_NAME).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        temp_backup_path.rename(final_backup_path)
        return manifest.model_copy(update={"backup_path": final_backup_path})
    except Exception:
        if temp_backup_path.exists():
            marker = temp_backup_path / "BACKUP_INCOMPLETE.txt"
            marker.write_text("Backup did not complete successfully.\n", encoding="utf-8")
        raise


def list_backups(dest: Path) -> list[BackupManifest]:
    backup_root = dest.expanduser().resolve()
    if not backup_root.exists():
        return []

    backups: list[BackupManifest] = []
    for manifest_file in sorted(backup_root.glob(f"{BACKUP_FOLDER_PREFIX}-*/{MANIFEST_NAME}")):
        try:
            backups.append(_load_manifest(manifest_file.parent))
        except ValueError:
            continue
    return sorted(backups, key=lambda manifest: manifest.created_at)


def cleanup_backups(dest: Path, keep: int = 3, dry_run: bool = False) -> BackupCleanupResult:
    if keep < 0:
        msg = "Backup cleanup keep count must be zero or greater."
        raise ValueError(msg)

    backup_root = dest.expanduser().resolve()
    result = BackupCleanupResult(backup_root=backup_root, keep=keep, dry_run=dry_run)
    if not backup_root.exists():
        return result
    if not backup_root.is_dir():
        msg = f"Backup root must be a directory: {backup_root}"
        raise ValueError(msg)

    valid_backups: list[BackupManifest] = []
    for child in sorted(backup_root.iterdir()):
        if not child.is_dir():
            continue
        if not child.name.startswith(f"{BACKUP_FOLDER_PREFIX}-"):
            result.skipped_invalid_backups.append(f"{child}: unknown folder")
            continue
        try:
            valid_backups.append(_load_manifest(child))
        except ValueError as exc:
            result.skipped_invalid_backups.append(f"{child}: {exc}")

    normal_backups = sorted(
        (manifest for manifest in valid_backups if not manifest.protected),
        key=lambda manifest: manifest.created_at,
        reverse=True,
    )
    protected_backups = sorted(
        (manifest for manifest in valid_backups if manifest.protected),
        key=lambda manifest: manifest.created_at,
        reverse=True,
    )

    retained = normal_backups[:keep]
    deletion_candidates = normal_backups[keep:]
    result.retained_backups = [manifest.backup_path for manifest in retained]
    result.skipped_protected_backups = [manifest.backup_path for manifest in protected_backups]

    for manifest in deletion_candidates:
        result.deleted_backups.append(manifest.backup_path)
        if not dry_run:
            shutil.rmtree(manifest.backup_path)

    return result


def verify_backup(path: Path) -> BackupManifest:
    backup_path = path.expanduser().resolve()
    manifest = _load_manifest(backup_path)
    workspace_path = backup_path / WORKSPACE_BACKUP_DIR
    if not workspace_path.exists() or not workspace_path.is_dir():
        msg = f"Backup workspace folder is missing: {workspace_path}"
        raise ValueError(msg)

    actual_files = sorted(file_path for file_path in workspace_path.rglob("*") if file_path.is_file())
    if len(actual_files) != manifest.file_count:
        msg = f"Backup file count mismatch: expected {manifest.file_count}, found {len(actual_files)}"
        raise ValueError(msg)

    actual_total_bytes = sum(file_path.stat().st_size for file_path in actual_files)
    if actual_total_bytes != manifest.total_bytes:
        msg = f"Backup total bytes mismatch: expected {manifest.total_bytes}, found {actual_total_bytes}"
        raise ValueError(msg)

    actual_relative_paths = {_relative_posix(file_path, backup_path) for file_path in actual_files}
    expected_relative_paths = set(manifest.sha256_by_file)
    if actual_relative_paths != expected_relative_paths:
        missing = sorted(expected_relative_paths - actual_relative_paths)
        extra = sorted(actual_relative_paths - expected_relative_paths)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing[:5])}")
        if extra:
            details.append(f"extra: {', '.join(extra[:5])}")
        msg = "Backup file set mismatch"
        if details:
            msg = f"{msg} ({'; '.join(details)})"
        raise ValueError(msg)

    for relative_path, expected_hash in manifest.sha256_by_file.items():
        file_path = backup_path / Path(relative_path)
        actual_hash = _sha256(file_path)
        if actual_hash != expected_hash:
            msg = f"Backup hash mismatch for {relative_path}"
            raise ValueError(msg)

    return manifest.model_copy(update={"backup_path": backup_path})


def restore_backup(backup: Path, dest: Path) -> BackupManifest:
    manifest = verify_backup(backup)
    backup_path = backup.expanduser().resolve()
    workspace_source = backup_path / WORKSPACE_BACKUP_DIR
    workspace_dest = dest.expanduser().resolve()

    if workspace_dest.exists() and any(workspace_dest.iterdir()):
        msg = f"Restore destination must be empty: {workspace_dest}"
        raise ValueError(msg)

    workspace_dest.mkdir(parents=True, exist_ok=True)
    for item in workspace_source.iterdir():
        target = workspace_dest / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    _verify_restored_workspace(manifest, workspace_dest)
    return manifest.model_copy(update={"backup_path": backup_path})


def _copy_directory(source: Path, target: Path, source_workspace: Path) -> list[Path]:
    copied_files: list[Path] = []
    for item in sorted(source.rglob("*")):
        relative_to_workspace = item.relative_to(source_workspace)
        if _is_excluded(relative_to_workspace, item.is_dir()):
            continue
        if item.is_dir():
            continue
        target_file = target / item.relative_to(source)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target_file)
        copied_files.append(target_file)
    return copied_files


def _is_excluded(relative_path: Path, is_dir: bool) -> bool:
    parts = set(relative_path.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    name = relative_path.name
    if is_dir:
        return name in EXCLUDED_DIR_NAMES
    if name in EXCLUDED_FILE_NAMES:
        return True
    return any(name.endswith(suffix) for suffix in EXCLUDED_FILE_SUFFIXES) or name.endswith("~")


def _load_manifest(backup_path: Path) -> BackupManifest:
    manifest_file = backup_path / MANIFEST_NAME
    if not manifest_file.exists():
        msg = f"Backup manifest is missing: {manifest_file}"
        raise ValueError(msg)
    try:
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        manifest = BackupManifest.model_validate(data)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        msg = f"Backup manifest is invalid: {manifest_file}"
        raise ValueError(msg) from exc
    return manifest.model_copy(update={"backup_path": backup_path.resolve()})


def _verify_restored_workspace(manifest: BackupManifest, workspace_dest: Path) -> None:
    expected_files = {
        relative_path.removeprefix(f"{WORKSPACE_BACKUP_DIR}/"): expected_hash
        for relative_path, expected_hash in manifest.sha256_by_file.items()
    }
    actual_files = sorted(file_path for file_path in workspace_dest.rglob("*") if file_path.is_file())
    if len(actual_files) != manifest.file_count:
        msg = f"Restored file count mismatch: expected {manifest.file_count}, found {len(actual_files)}"
        raise ValueError(msg)
    for relative_path, expected_hash in expected_files.items():
        file_path = workspace_dest / Path(relative_path)
        if not file_path.exists():
            msg = f"Restored file is missing: {relative_path}"
            raise ValueError(msg)
        if _sha256(file_path) != expected_hash:
            msg = f"Restored file hash mismatch: {relative_path}"
            raise ValueError(msg)


def _backup_folder_name(label: str | None) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    name = f"{BACKUP_FOLDER_PREFIX}-{timestamp}"
    if label:
        name = f"{name}-{_slugify(label)}"
    return name


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "backup"


def _unique_child_path(parent: Path, name: str) -> Path:
    candidate = parent / name
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        candidate = parent / f"{name}-{index}"
        if not candidate.exists():
            return candidate
    msg = f"Could not create unique backup path under {parent}"
    raise ValueError(msg)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _git_output(args: list[str]) -> str:
    try:
        completed = subprocess.run(args, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"
