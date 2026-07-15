from __future__ import annotations

import fnmatch
import json
import os
import subprocess
from pathlib import Path

from .projects import get_workspace_root
from .schemas import (
    FileTreeSummary,
    GitInfo,
    ProjectRegistration,
    ProjectScanResult,
    ScanCategories,
    ScanLimits,
)

IGNORED_DIRECTORY_NAMES = {
    ".git",
    "bin",
    "obj",
    "node_modules",
    "dist",
    "build",
    "logs",
    "backups",
    "outputs",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vs",
    ".vscode",
}

IGNORED_FILE_PATTERNS = (
    ".env",
    "*.env",
    "*.secret.*",
    "*secret*",
    "*password*",
    "*.key",
    "*.pem",
)

BINARY_MEDIA_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bmp",
    ".dll",
    ".dmg",
    ".exe",
    ".gif",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".msi",
    ".pdf",
    ".png",
    ".so",
    ".tar",
    ".tiff",
    ".webm",
    ".webp",
    ".zip",
}

MAX_FILE_SIZE_BYTES = 1_000_000
MAX_RECORDED_PATHS_PER_CATEGORY = 100
MAX_TREE_ENTRIES = 250


def load_registered_project(project_name: str, workspace_root: Path | None = None) -> ProjectRegistration:
    root = workspace_root or get_workspace_root()
    project_file = root / "projects" / project_name / "project.json"
    if not project_file.exists():
        msg = f"Registered project not found: {project_name}"
        raise ValueError(msg)

    data = json.loads(project_file.read_text(encoding="utf-8"))
    return ProjectRegistration.model_validate(data)


def scan_registered_project(project_name: str, workspace_root: Path | None = None) -> ProjectScanResult:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    result = scan_project(project_name=project_name, project_path=registration.path)

    output_file = root / "projects" / project_name / "scan-result.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


def scan_project(project_name: str, project_path: Path) -> ProjectScanResult:
    root = project_path.expanduser().resolve()
    if not root.exists():
        msg = f"Project path does not exist: {root}"
        raise ValueError(msg)
    if not root.is_dir():
        msg = f"Project path must be a directory: {root}"
        raise ValueError(msg)

    categories = ScanCategories()
    file_tree = FileTreeSummary()
    warnings: list[str] = []

    for current_dir_name, directory_names, file_names in os.walk(root, onerror=lambda error: warnings.append(str(error))):
        current_dir = Path(current_dir_name)
        relative_dir = _relative_path(current_dir, root)
        kept_directories = []
        for directory_name in sorted(directory_names):
            if _should_ignore_directory(directory_name):
                file_tree.ignored_directory_count += 1
                continue

            kept_directories.append(directory_name)
            file_tree.scanned_directory_count += 1
            directory_path = current_dir / directory_name
            relative_directory = _relative_path(directory_path, root)
            _record_tree_path(file_tree, f"{relative_directory}/")
            _record_test_folder(categories, relative_directory)

        directory_names[:] = kept_directories
        file_tree.max_depth = max(file_tree.max_depth, _path_depth(relative_dir))

        for file_name in sorted(file_names):
            file_path = current_dir / file_name
            relative_file = _relative_path(file_path, root)

            if _should_ignore_file(file_path):
                file_tree.ignored_file_count += 1
                continue

            try:
                file_size = file_path.stat().st_size
            except OSError as exc:
                file_tree.ignored_file_count += 1
                warnings.append(f"Could not stat {relative_file}: {exc}")
                continue

            if file_size > MAX_FILE_SIZE_BYTES or _is_large_media_or_binary(file_path):
                file_tree.ignored_file_count += 1
                continue

            file_tree.scanned_file_count += 1
            file_tree.total_scanned_bytes += file_size
            file_tree.max_depth = max(file_tree.max_depth, _path_depth(relative_file))
            _record_tree_path(file_tree, relative_file)
            _categorize_file(categories, relative_file)

    return ProjectScanResult(
        project_name=project_name,
        project_path=root,
        limits=ScanLimits(
            max_file_size_bytes=MAX_FILE_SIZE_BYTES,
            max_recorded_paths_per_category=MAX_RECORDED_PATHS_PER_CATEGORY,
            max_tree_entries=MAX_TREE_ENTRIES,
        ),
        file_tree=file_tree,
        categories=categories,
        git=_collect_git_info(root),
        warnings=warnings[:20],
    )


def _should_ignore_directory(directory_name: str) -> bool:
    normalized = directory_name.lower()
    return normalized in IGNORED_DIRECTORY_NAMES or "pycache" in normalized


def _should_ignore_file(file_path: Path) -> bool:
    file_name = file_path.name.lower()
    return any(fnmatch.fnmatch(file_name, pattern.lower()) for pattern in IGNORED_FILE_PATTERNS)


def _is_large_media_or_binary(file_path: Path) -> bool:
    return file_path.suffix.lower() in BINARY_MEDIA_EXTENSIONS


def _relative_path(path: Path, root: Path) -> str:
    if path == root:
        return "."
    return path.relative_to(root).as_posix()


def _path_depth(relative_path: str) -> int:
    if relative_path == ".":
        return 0
    return len(Path(relative_path).parts)


def _record_tree_path(file_tree: FileTreeSummary, relative_path: str) -> None:
    if len(file_tree.sample_paths) < MAX_TREE_ENTRIES:
        file_tree.sample_paths.append(relative_path)


def _record_category(paths: list[str], relative_path: str) -> None:
    if relative_path not in paths and len(paths) < MAX_RECORDED_PATHS_PER_CATEGORY:
        paths.append(relative_path)


def _record_test_folder(categories: ScanCategories, relative_path: str) -> None:
    parts = [part.lower() for part in Path(relative_path).parts]
    if any(part in {"test", "tests", "spec", "specs"} for part in parts):
        _record_category(categories.test_projects_folders, relative_path)


def _categorize_file(categories: ScanCategories, relative_path: str) -> None:
    path = Path(relative_path)
    name = path.name
    lower_name = name.lower()
    lower_path = relative_path.lower()
    suffix = path.suffix.lower()

    if suffix == ".sln":
        _record_category(categories.solution_files, relative_path)

    if suffix in {".csproj", ".fsproj", ".vbproj"}:
        _record_category(categories.project_files, relative_path)

    if lower_name.startswith("readme") or lower_path.startswith("docs/") or suffix in {".md", ".rst"}:
        _record_category(categories.readme_docs_files, relative_path)

    if _is_config_or_template_file(path):
        _record_category(categories.config_template_files, relative_path)

    if "migration" in lower_path or "database" in lower_path or suffix == ".sql":
        _record_category(categories.migration_database_files, relative_path)

    if _is_test_path(relative_path):
        _record_category(categories.test_projects_folders, relative_path)

    if _is_docker_file(lower_name):
        _record_category(categories.docker_files, relative_path)

    if _is_package_dependency_file(lower_name):
        _record_category(categories.package_dependency_files, relative_path)


def _is_config_or_template_file(path: Path) -> bool:
    lower_name = path.name.lower()
    return (
        path.suffix.lower() in {".cfg", ".conf", ".ini", ".json", ".toml", ".yaml", ".yml"}
        or lower_name.endswith(".template")
        or lower_name.endswith(".example")
        or "template" in lower_name
    )


def _is_test_path(relative_path: str) -> bool:
    lower_path = relative_path.lower()
    parts = [part.lower() for part in Path(relative_path).parts]
    return (
        any(part in {"test", "tests", "spec", "specs"} for part in parts)
        or ".tests." in lower_path
        or lower_path.endswith(".tests.csproj")
    )


def _is_docker_file(lower_name: str) -> bool:
    return lower_name == "dockerfile" or lower_name == ".dockerignore" or lower_name.startswith("docker-compose")


def _is_package_dependency_file(lower_name: str) -> bool:
    return lower_name in {
        "build.gradle",
        "cargo.lock",
        "cargo.toml",
        "composer.json",
        "composer.lock",
        "go.mod",
        "go.sum",
        "package-lock.json",
        "package.json",
        "pipfile",
        "pipfile.lock",
        "poetry.lock",
        "pom.xml",
        "pnpm-lock.yaml",
        "pyproject.toml",
        "requirements.txt",
        "yarn.lock",
    } or (lower_name.startswith("requirements-") and lower_name.endswith(".txt"))


def _collect_git_info(project_path: Path) -> GitInfo:
    if not (project_path / ".git").exists():
        return GitInfo(is_git_repo=False)

    branch = _run_git(project_path, ["branch", "--show-current"])
    status = _run_git(project_path, ["status", "--short"])
    commits = _run_git(project_path, ["log", "-10", "--pretty=%s"])

    return GitInfo(
        is_git_repo=True,
        current_branch=branch.strip() or None,
        status_summary=status.strip() or "clean",
        last_commit_subjects=[line for line in commits.splitlines() if line][:10],
    )


def _run_git(project_path: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(project_path), *args],
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout
