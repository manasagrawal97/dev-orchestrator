from __future__ import annotations

import json
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .projects import get_workspace_root
from .schemas import EnvironmentSnapshot

ENV_SCHEMA_VERSION = "1"
SNAPSHOT_FILE_NAME = "environment-snapshot.json"
BOOTSTRAP_PLAN_FILE_NAME = "bootstrap-plan.md"

EXPECTED_ROOT_FILES = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "uv.lock",
    "global.json",
    "NuGet.Config",
    "Directory.Build.props",
    "Directory.Packages.props",
    "packages.lock.json",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
)

HEAVY_DIR_NAMES = {
    ".venv",
    "node_modules",
    ".packages",
    ".tools",
    "bin",
    "obj",
    "__pycache__",
    ".pytest_cache",
    ".git",
}

LOCAL_OR_SECRET_PATTERNS = (
    ".env",
    "*.env",
    "settings.local.json",
    "*.local.json",
    "appsettings.Development.json",
    "*.user",
    "*.key",
    "*.pem",
)

MAX_COMMAND_OUTPUT = 12000


def _env_dir(name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return root / "environment" / name


def snapshot_paths(name: str, workspace_root: Path | None = None) -> tuple[Path, Path]:
    output_dir = _env_dir(name, workspace_root=workspace_root)
    return output_dir / SNAPSHOT_FILE_NAME, output_dir / BOOTSTRAP_PLAN_FILE_NAME


def _safe_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _run_command(command: list[str], cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip()).strip()
    if result.returncode != 0 and not output:
        return None
    if not output:
        return None
    if len(output) > MAX_COMMAND_OUTPUT:
        return output[:MAX_COMMAND_OUTPUT] + "\n... truncated ..."
    return output


def _iter_project_files(root: Path) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    excluded: set[str] = set()

    def walk(directory: Path) -> None:
        try:
            children = list(directory.iterdir())
        except OSError:
            return
        for child in children:
            if child.is_dir():
                if child.name in HEAVY_DIR_NAMES:
                    excluded.add(_safe_relative(child, root))
                    continue
                walk(child)
            elif child.is_file():
                files.append(child)

    walk(root)
    return files, sorted(excluded)


def _looks_local_or_secret(path: Path) -> bool:
    name = path.name.lower()
    for pattern in LOCAL_OR_SECRET_PATTERNS:
        if path.match(pattern) or name == pattern.lower() or Path(name).match(pattern.lower()):
            return True
    return False


def _dependency_files(root: Path, files: list[Path]) -> tuple[list[str], list[str]]:
    found: set[str] = set()
    for filename in EXPECTED_ROOT_FILES:
        if (root / filename).is_file():
            found.add(filename)

    for file_path in files:
        if file_path.suffix.lower() in {".sln", ".slnx", ".csproj"}:
            found.add(_safe_relative(file_path, root))
        elif file_path.name in {"packages.lock.json"}:
            found.add(_safe_relative(file_path, root))

    missing = [filename for filename in EXPECTED_ROOT_FILES if not (root / filename).exists()]
    return sorted(found), missing


def _tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child_text(root: ET.Element, tag: str) -> str | None:
    for element in root.iter():
        if _tag_name(element) == tag and element.text and element.text.strip():
            return element.text.strip()
    return None


def _parse_csproj(project_file: Path, root: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": _safe_relative(project_file, root),
        "sdk": None,
        "target_frameworks": [],
        "output_type": None,
        "nullable": None,
        "implicit_usings": None,
        "package_references": [],
        "project_references": [],
    }
    try:
        xml_root = ET.parse(project_file).getroot()
    except ET.ParseError:
        summary["parse_error"] = "Unable to parse project file as XML."
        return summary

    summary["sdk"] = xml_root.attrib.get("Sdk")
    target_frameworks = _child_text(xml_root, "TargetFrameworks") or _child_text(xml_root, "TargetFramework")
    if target_frameworks:
        summary["target_frameworks"] = [part.strip() for part in target_frameworks.split(";") if part.strip()]
    summary["output_type"] = _child_text(xml_root, "OutputType")
    summary["nullable"] = _child_text(xml_root, "Nullable")
    summary["implicit_usings"] = _child_text(xml_root, "ImplicitUsings")

    packages: list[str] = []
    project_refs: list[str] = []
    for element in xml_root.iter():
        tag = _tag_name(element)
        if tag == "PackageReference":
            include = element.attrib.get("Include") or element.attrib.get("Update")
            version = element.attrib.get("Version")
            if version is None:
                version = _child_text(element, "Version")
            if include:
                packages.append(f"{include} {version or 'unspecified'}")
        elif tag == "ProjectReference":
            include = element.attrib.get("Include")
            if include:
                project_refs.append(include.replace("\\", "/"))
    summary["package_references"] = sorted(packages)
    summary["project_references"] = sorted(project_refs)
    return summary


def _parse_pyproject(project_file: Path) -> list[str]:
    try:
        import tomllib

        data = tomllib.loads(project_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    project = data.get("project", {}) if isinstance(data, dict) else {}
    dependencies = project.get("dependencies", []) if isinstance(project, dict) else []
    names: list[str] = []
    if isinstance(dependencies, list):
        names.extend(str(item) for item in dependencies)
    optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
    if isinstance(optional, dict):
        for group, items in sorted(optional.items()):
            if isinstance(items, list):
                names.extend(f"{group}: {item}" for item in items)
    return names


def _parse_requirements(requirements_file: Path) -> list[str]:
    try:
        lines = requirements_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        entries.append(stripped)
    return entries


def _parse_package_json(package_file: Path) -> tuple[list[str], list[str]]:
    try:
        data = json.loads(package_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], []
    packages: list[str] = []
    commands: list[str] = []
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        values = data.get(section, {})
        if isinstance(values, dict):
            packages.extend(f"{section}: {name} {version}" for name, version in sorted(values.items()))
    scripts = data.get("scripts", {})
    if isinstance(scripts, dict):
        commands.extend(f"npm run {name}" for name in sorted(scripts))
    return packages, commands


def _collect_package_summary(root: Path, project_files: list[Path]) -> tuple[dict[str, list[str]], list[str], list[str]]:
    summary: dict[str, list[str]] = {}
    commands: list[str] = []
    recommended: list[str] = []

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        deps = _parse_pyproject(pyproject)
        if deps:
            summary["pyproject.toml"] = deps
        recommended.append('python -m pip install -e ".[dev]"')
    for requirements_name in ("requirements.txt", "requirements-dev.txt"):
        req_file = root / requirements_name
        if req_file.is_file():
            deps = _parse_requirements(req_file)
            if deps:
                summary[requirements_name] = deps
            recommended.append(f"python -m pip install -r {requirements_name}")

    package_json = root / "package.json"
    if package_json.is_file():
        packages, npm_commands = _parse_package_json(package_json)
        if packages:
            summary["package.json"] = packages
        commands.extend(npm_commands)
        recommended.append("npm install")
        recommended.extend(npm_commands)

    for project_file in project_files:
        parsed = _parse_csproj(project_file, root)
        packages = parsed.get("package_references", [])
        if packages:
            summary[_safe_relative(project_file, root)] = list(packages)

    return summary, commands, recommended


def _git_info(root: Path) -> tuple[str | None, str | None, str | None]:
    inside = _run_command(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"])
    if inside is None or "true" not in inside.lower():
        return None, None, None
    branch = _run_command(["git", "-C", str(root), "branch", "--show-current"])
    commit = _run_command(["git", "-C", str(root), "rev-parse", "HEAD"])
    status = _run_command(["git", "-C", str(root), "status", "--short"])
    return branch or "unknown", commit or "unknown", status or "clean"


def _version_lines(output: str | None) -> list[str]:
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _recommended_commands(root: Path, solution_files: list[Path], base_commands: list[str]) -> list[str]:
    commands = list(dict.fromkeys(base_commands))
    if solution_files:
        solution = _safe_relative(solution_files[0], root)
        commands.extend([
            f"dotnet restore {solution}",
            f"dotnet build {solution}",
            f"dotnet test {solution}",
        ])
    elif any(root.glob("*.csproj")):
        commands.extend(["dotnet restore", "dotnet build", "dotnet test"])
    return list(dict.fromkeys(commands))


def create_environment_snapshot(
    name: str,
    project_path: Path,
    workspace_root: Path | None = None,
) -> tuple[EnvironmentSnapshot, Path, Path]:
    root = project_path.expanduser().resolve()
    if not root.exists():
        msg = f"Project path does not exist: {root}"
        raise ValueError(msg)
    if not root.is_dir():
        msg = f"Project path must be a directory: {root}"
        raise ValueError(msg)

    files, excluded_heavy_paths = _iter_project_files(root)
    dependency_files_found, dependency_files_missing = _dependency_files(root, files)
    solution_files = sorted([path for path in files if path.suffix.lower() in {".sln", ".slnx"}])
    project_files = sorted([path for path in files if path.suffix.lower() == ".csproj"])
    test_projects = [path for path in project_files if "test" in _safe_relative(path, root).lower()]
    package_summary, commands_detected, base_recommended = _collect_package_summary(root, project_files)
    branch, commit, git_status = _git_info(root)

    warnings: list[str] = []
    for file_path in files:
        if _looks_local_or_secret(file_path):
            warnings.append(f"Local or sensitive settings file detected and not read: {_safe_relative(file_path, root)}")

    dotnet_info = _run_command(["dotnet", "--info"])
    dotnet_sdks = _version_lines(_run_command(["dotnet", "--list-sdks"]))
    dotnet_runtimes = _version_lines(_run_command(["dotnet", "--list-runtimes"]))

    recommended = _recommended_commands(root, solution_files, [*base_recommended, *commands_detected])
    recovery_notes = [
        "This snapshot records structural environment metadata only; it does not copy source code or dependency caches.",
        "Restore source from Git, then use dependency files and recommended commands as recovery guidance.",
        "Review local settings and secrets manually on the machine that owns them; values are intentionally omitted.",
    ]

    snapshot = EnvironmentSnapshot(
        schema_version=ENV_SCHEMA_VERSION,
        created_at=datetime.now(UTC),
        name=name,
        project_path=root,
        project_git_branch=branch,
        project_git_commit=commit,
        project_git_status_summary=git_status,
        operating_system=f"{platform.system()} {platform.release()} ({platform.platform()})",
        python_version=_run_command(["python", "--version"]),
        pip_version=_run_command(["pip", "--version"]),
        dotnet_info=dotnet_info,
        dotnet_sdks=dotnet_sdks,
        dotnet_runtimes=dotnet_runtimes,
        git_version=_run_command(["git", "--version"]),
        node_version=_run_command(["node", "--version"]),
        npm_version=_run_command(["npm", "--version"]),
        dependency_files_found=dependency_files_found,
        dependency_files_missing=dependency_files_missing,
        detected_project_files=[_safe_relative(path, root) for path in project_files],
        detected_solution_files=[_safe_relative(path, root) for path in solution_files],
        detected_test_projects=[_safe_relative(path, root) for path in test_projects],
        package_versions_summary=package_summary,
        commands_detected=commands_detected,
        recommended_commands=recommended,
        excluded_heavy_paths=excluded_heavy_paths,
        warnings=warnings,
        recovery_notes=recovery_notes,
    )

    snapshot_file, plan_file = snapshot_paths(name, workspace_root=workspace_root)
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    plan_file.write_text(render_bootstrap_plan(snapshot), encoding="utf-8")
    return snapshot, snapshot_file, plan_file


def verify_environment_snapshot(snapshot_file: Path) -> EnvironmentSnapshot:
    path = snapshot_file.expanduser().resolve()
    if not path.exists():
        msg = f"Environment snapshot does not exist: {path}"
        raise ValueError(msg)
    if not path.is_file():
        msg = f"Environment snapshot must be a file: {path}"
        raise ValueError(msg)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Environment snapshot is not valid JSON: {path}"
        raise ValueError(msg) from exc
    try:
        snapshot = EnvironmentSnapshot.model_validate(data)
    except Exception as exc:
        msg = f"Environment snapshot failed schema validation: {exc}"
        raise ValueError(msg) from exc
    if snapshot.schema_version != ENV_SCHEMA_VERSION:
        msg = f"Unsupported environment snapshot schema version: {snapshot.schema_version}"
        raise ValueError(msg)
    return snapshot


def generate_environment_bootstrap_plan(snapshot_file: Path) -> tuple[EnvironmentSnapshot, Path, str]:
    snapshot = verify_environment_snapshot(snapshot_file)
    path = snapshot_file.expanduser().resolve()
    plan_path = path.parent / BOOTSTRAP_PLAN_FILE_NAME
    plan_text = render_bootstrap_plan(snapshot)
    plan_path.write_text(plan_text, encoding="utf-8")
    return snapshot, plan_path, plan_text


def _md_list(items: list[str], empty: str = "none") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def _package_summary_lines(summary: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for source, packages in sorted(summary.items()):
        lines.append(f"{source}: {len(packages)} entries")
        for package in packages[:20]:
            lines.append(f"  - {package}")
        if len(packages) > 20:
            lines.append(f"  - ... {len(packages) - 20} more omitted")
    return lines


def render_bootstrap_plan(snapshot: EnvironmentSnapshot) -> str:
    package_lines = _package_summary_lines(snapshot.package_versions_summary)
    status = snapshot.project_git_status_summary or "unknown"
    return "\n".join(
        [
            f"# Bootstrap Plan: {snapshot.name}",
            "",
            "## Snapshot",
            f"- Created at: {snapshot.created_at.isoformat()}",
            f"- Project path: {snapshot.project_path}",
            f"- Operating system: {snapshot.operating_system}",
            f"- Git branch: {snapshot.project_git_branch or 'unknown'}",
            f"- Git commit: {snapshot.project_git_commit or 'unknown'}",
            f"- Git status summary: {status}",
            "",
            "## Tool Versions",
            f"- Python: {snapshot.python_version or 'unknown'}",
            f"- pip: {snapshot.pip_version or 'unknown'}",
            f"- Git: {snapshot.git_version or 'unknown'}",
            f"- Node: {snapshot.node_version or 'unknown'}",
            f"- npm: {snapshot.npm_version or 'unknown'}",
            f"- .NET SDKs: {', '.join(snapshot.dotnet_sdks) if snapshot.dotnet_sdks else 'unknown'}",
            f"- .NET runtimes: {', '.join(snapshot.dotnet_runtimes) if snapshot.dotnet_runtimes else 'unknown'}",
            "",
            "## Dependency Files Found",
            _md_list(snapshot.dependency_files_found),
            "",
            "## Dependency Files Missing",
            _md_list(snapshot.dependency_files_missing),
            "",
            "## Detected Solutions",
            _md_list(snapshot.detected_solution_files),
            "",
            "## Detected Projects",
            _md_list(snapshot.detected_project_files),
            "",
            "## Detected Test Projects",
            _md_list(snapshot.detected_test_projects),
            "",
            "## Package Summary",
            _md_list(package_lines),
            "",
            "## Recommended Commands",
            _md_list(snapshot.recommended_commands, empty="none detected; inspect project docs before running recovery commands"),
            "",
            "## Excluded Heavy Paths",
            _md_list(snapshot.excluded_heavy_paths),
            "",
            "## Warnings",
            _md_list(snapshot.warnings),
            "",
            "## Recovery Notes",
            _md_list(snapshot.recovery_notes),
            "",
        ]
    )
