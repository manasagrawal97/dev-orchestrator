from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import (
    ProjectScanResult,
    ValidationCommand,
    ValidationCommandCategory,
    ValidationCommandCheck,
    ValidationCommandRegistry,
    ValidationRiskLevel,
)

REGISTRY_SCHEMA_VERSION = "1"
REGISTRY_FILE_NAME = "validation-commands.json"
TARGET_COMMAND_RISK = ValidationRiskLevel.HIGH
INTERNAL_TEST_RISK = ValidationRiskLevel.MEDIUM


def registry_path(project_name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return root / "projects" / project_name / REGISTRY_FILE_NAME


def load_registry(project_name: str, workspace_root: Path | None = None) -> ValidationCommandRegistry:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    path = registry_path(project_name, workspace_root=root)
    if not path.exists():
        return ValidationCommandRegistry(project_name=project_name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        registry = ValidationCommandRegistry.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"Validation command registry is malformed: {path}"
        raise ValueError(msg) from exc
    if registry.project_name != project_name:
        msg = f"Validation command registry project mismatch: {registry.project_name}"
        raise ValueError(msg)
    return registry


def save_registry(
    registry: ValidationCommandRegistry,
    workspace_root: Path | None = None,
) -> ValidationCommandRegistry:
    path = registry_path(registry.project_name, workspace_root=workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = registry.model_copy(update={"updated_at": datetime.now(UTC)})
    path.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
    return registry


def list_validation_commands(project_name: str, workspace_root: Path | None = None) -> list[ValidationCommand]:
    return load_registry(project_name, workspace_root=workspace_root).commands


def add_validation_command(
    project_name: str,
    command_id: str,
    name: str,
    command: str,
    category: str,
    working_dir: Path | None = None,
    risk: str | None = None,
    approval_required: bool | None = None,
    enabled: bool = True,
    source: str = "manual",
    note: str | None = None,
    replace: bool = False,
    workspace_root: Path | None = None,
) -> ValidationCommand:
    root = workspace_root or get_workspace_root()
    project = load_registered_project(project_name, workspace_root=root)
    registry = load_registry(project_name, workspace_root=root)
    normalized_id = _normalize_id(command_id)
    existing_index = _command_index(registry, normalized_id)
    if existing_index is not None and not replace:
        msg = f"Validation command already exists: {normalized_id}"
        raise ValueError(msg)

    category_value = _parse_category(category)
    working_directory = _resolve_working_dir(working_dir, project.path)
    classification = classify_validation_command(
        project_name=project_name,
        command_id=normalized_id,
        command=command,
        category=category_value,
        working_dir=working_directory,
        explicit_risk=risk,
        explicit_approval_required=approval_required,
        project_path=project.path,
    )
    now = datetime.now(UTC)
    if existing_index is not None:
        created_at = registry.commands[existing_index].created_at
    else:
        created_at = now
    validation_command = ValidationCommand(
        id=normalized_id,
        name=name.strip(),
        command=command.strip(),
        working_dir=working_directory,
        category=category_value,
        risk_level=classification.risk_level,
        approval_required=classification.approval_required,
        enabled=enabled,
        source=source.strip() or "manual",
        notes=[note.strip()] if note and note.strip() else [],
        created_at=created_at,
        updated_at=now,
    )
    if existing_index is None:
        registry.commands.append(validation_command)
    else:
        registry.commands[existing_index] = validation_command
    registry.commands = sorted(registry.commands, key=lambda item: item.id)
    save_registry(registry, workspace_root=root)
    return validation_command


def get_validation_command(
    project_name: str,
    command_id: str,
    workspace_root: Path | None = None,
) -> ValidationCommand:
    registry = load_registry(project_name, workspace_root=workspace_root)
    normalized_id = _normalize_id(command_id)
    for command in registry.commands:
        if command.id == normalized_id:
            return command
    msg = f"Validation command not found: {normalized_id}"
    raise ValueError(msg)


def check_validation_command(
    project_name: str,
    command_id: str,
    workspace_root: Path | None = None,
) -> ValidationCommandCheck:
    root = workspace_root or get_workspace_root()
    command = get_validation_command(project_name, command_id, workspace_root=root)
    classification = classify_validation_command(
        project_name=project_name,
        command_id=command.id,
        command=command.command,
        category=command.category,
        working_dir=command.working_dir,
        explicit_risk=command.risk_level.value,
        explicit_approval_required=command.approval_required,
    )
    reasons = list(classification.reasons)
    if not command.enabled:
        reasons.append("Command is disabled in the registry and should not be executed.")
    return classification.model_copy(update={"reasons": _dedupe(reasons)})


def classify_validation_command(
    project_name: str,
    command_id: str,
    command: str,
    category: ValidationCommandCategory,
    working_dir: Path | None = None,
    explicit_risk: str | None = None,
    explicit_approval_required: bool | None = None,
    project_path: Path | None = None,
) -> ValidationCommandCheck:
    normalized_command = " ".join(command.strip().split())
    command_lower = normalized_command.lower()
    reasons: list[str] = []
    risk = _risk_from_category(category)

    if category in {ValidationCommandCategory.RESTORE, ValidationCommandCategory.BUILD, ValidationCommandCategory.TEST, ValidationCommandCategory.RUN}:
        if _looks_like_target_command(command_lower):
            risk = _max_risk(risk, TARGET_COMMAND_RISK)
            reasons.append("Target project restore/build/test/run commands are high risk until an execution runner exists.")

    if command_lower.startswith("python -m pytest") or command_lower.startswith(".\\.venv\\scripts\\python -m pytest"):
        if _is_internal_devorchestrator_path(working_dir):
            risk = _max_risk(risk, INTERNAL_TEST_RISK)
            reasons.append("DevOrchestrator internal pytest command is medium risk unless constrained by temp directories and workflow approval.")
        elif "--basetemp" in command_lower:
            risk = _max_risk(risk, ValidationRiskLevel.MEDIUM)
            reasons.append("Pytest command uses an explicit basetemp but still creates local test files.")
        else:
            risk = _max_risk(risk, TARGET_COMMAND_RISK)
            reasons.append("Project pytest command may execute target project tests and is high risk by default.")

    if any(token in command_lower for token in ("remove-item", " rm -rf", " del ", " rmdir ")):
        risk = ValidationRiskLevel.CRITICAL
        reasons.append("Command text contains destructive delete-like operations.")

    if project_path and working_dir:
        try:
            working_dir.resolve().relative_to(project_path.resolve())
            if _looks_like_target_command(command_lower):
                risk = _max_risk(risk, TARGET_COMMAND_RISK)
                reasons.append("Working directory is inside the registered target project.")
        except ValueError:
            pass

    if explicit_risk:
        risk = _parse_risk(explicit_risk)
        reasons.append(f"Risk level explicitly set to {risk.value}.")

    approval_required = risk in {ValidationRiskLevel.HIGH, ValidationRiskLevel.CRITICAL}
    if explicit_approval_required is not None:
        approval_required = explicit_approval_required
        reasons.append(f"Approval requirement explicitly set to {approval_required}.")

    blocked = risk == ValidationRiskLevel.CRITICAL
    allowed = not blocked and not approval_required
    if approval_required and not blocked:
        reasons.append("Approval is required before this validation command can be executed.")
    if blocked:
        reasons.append("Critical-risk validation commands are blocked by policy.")
    if not reasons:
        reasons.append("No high-risk validation signals detected.")

    return ValidationCommandCheck(
        project_name=project_name,
        command_id=command_id,
        allowed=allowed,
        approval_required=approval_required,
        blocked=blocked,
        risk_level=risk,
        reasons=_dedupe(reasons),
        suggested_approval_request_command=(
            f"devo approval request --project {project_name} --run <runId> --task <taskId> --action target_command"
            if approval_required and not blocked
            else None
        ),
    )


def suggest_validation_commands(
    project_name: str,
    write: bool = False,
    workspace_root: Path | None = None,
) -> list[ValidationCommand]:
    root = workspace_root or get_workspace_root()
    project = load_registered_project(project_name, workspace_root=root)
    suggestions = _build_suggestions(project_name, project.path, root)
    if write:
        registry = load_registry(project_name, workspace_root=root)
        existing_ids = {command.id for command in registry.commands}
        for suggestion in suggestions:
            if suggestion.id not in existing_ids:
                registry.commands.append(suggestion)
        registry.commands = sorted(registry.commands, key=lambda item: item.id)
        save_registry(registry, workspace_root=root)
    return suggestions


def _build_suggestions(project_name: str, project_path: Path, workspace_root: Path) -> list[ValidationCommand]:
    scan = _load_scan_result(project_name, workspace_root)
    solution_files = _scan_paths(scan, "solution_files") or _find_files(project_path, ("*.sln", "*.slnx"))
    project_files = _scan_paths(scan, "project_files") or _find_files(project_path, ("*.csproj", "*.fsproj", "*.vbproj"))
    package_files = _scan_paths(scan, "package_dependency_files")
    suggestions: list[ValidationCommand] = []

    for solution in solution_files[:3]:
        solution_path = Path(solution)
        solution_name = solution_path.name
        base_id = _slugify(solution_path.stem)
        suggestions.extend(
            [
                _suggestion(project_name, f"dotnet-restore-{base_id}", f"dotnet restore {solution_name}", f"Restore {solution_name}", ValidationCommandCategory.RESTORE, project_path, ["Suggested from solution file metadata."]),
                _suggestion(project_name, f"dotnet-build-{base_id}", f"dotnet build {solution_name}", f"Build {solution_name}", ValidationCommandCategory.BUILD, project_path, ["Suggested from solution file metadata."]),
                _suggestion(project_name, f"dotnet-test-{base_id}", f"dotnet test {solution_name}", f"Test {solution_name}", ValidationCommandCategory.TEST, project_path, ["Suggested from solution file metadata."]),
            ]
        )

    for project_file in project_files[:20]:
        project_rel = Path(project_file)
        if "test" not in str(project_rel).lower():
            continue
        command_text = f"dotnet test {project_rel.as_posix()}"
        suggestions.append(
            _suggestion(
                project_name,
                f"dotnet-test-{_slugify(project_rel.stem)}",
                command_text,
                f"Test {project_rel.stem}",
                ValidationCommandCategory.TEST,
                project_path,
                ["Suggested from test project metadata."],
            )
        )

    if _has_python_project(project_path, package_files):
        suggestions.append(
            _suggestion(
                project_name,
                "python-pytest",
                "python -m pytest",
                "Run pytest",
                ValidationCommandCategory.TEST,
                project_path,
                ["Suggested from Python project metadata."],
            )
        )

    for package_json in _package_json_paths(project_path, package_files)[:5]:
        scripts = _package_json_scripts(project_path / package_json)
        if "test" in scripts:
            suggestions.append(
                _suggestion(project_name, "npm-test", "npm test", "Run npm test", ValidationCommandCategory.TEST, project_path, ["Suggested from package.json test script."])
            )
        if "build" in scripts:
            suggestions.append(
                _suggestion(project_name, "npm-run-build", "npm run build", "Run npm build", ValidationCommandCategory.BUILD, project_path, ["Suggested from package.json build script."])
            )

    return _dedupe_commands(suggestions)


def _suggestion(
    project_name: str,
    command_id: str,
    command: str,
    name: str,
    category: ValidationCommandCategory,
    working_dir: Path,
    notes: list[str],
) -> ValidationCommand:
    check = classify_validation_command(
        project_name=project_name,
        command_id=command_id,
        command=command,
        category=category,
        working_dir=working_dir,
        project_path=working_dir,
    )
    return ValidationCommand(
        id=command_id,
        name=name,
        command=command,
        working_dir=working_dir.resolve(),
        category=category,
        risk_level=check.risk_level,
        approval_required=check.approval_required,
        enabled=not check.approval_required and not check.blocked,
        source="suggested",
        notes=notes,
    )


def _load_scan_result(project_name: str, workspace_root: Path) -> ProjectScanResult | None:
    path = workspace_root / "projects" / project_name / "scan-result.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectScanResult.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def _scan_paths(scan: ProjectScanResult | None, category_name: str) -> list[str]:
    if not scan:
        return []
    return list(getattr(scan.categories, category_name, []))


def _find_files(project_path: Path, patterns: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    ignored_parts = {".git", "bin", "obj", "node_modules", ".venv", ".pytest_cache"}
    for pattern in patterns:
        for path in sorted(project_path.rglob(pattern)):
            if any(part in ignored_parts for part in path.parts):
                continue
            found.append(path.relative_to(project_path).as_posix())
    return found


def _has_python_project(project_path: Path, package_files: list[str]) -> bool:
    names = {Path(path).name for path in package_files}
    return "pyproject.toml" in names or (project_path / "pyproject.toml").exists() or (project_path / "pytest.ini").exists()


def _package_json_paths(project_path: Path, package_files: list[str]) -> list[Path]:
    paths = [Path(path) for path in package_files if Path(path).name == "package.json"]
    if not paths and (project_path / "package.json").exists():
        paths = [Path("package.json")]
    return paths


def _package_json_scripts(path: Path) -> dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items()}


def _resolve_working_dir(working_dir: Path | None, project_path: Path) -> Path:
    if not working_dir:
        return project_path.resolve()
    candidate = working_dir.expanduser()
    if not candidate.is_absolute():
        candidate = project_path / candidate
    return candidate.resolve()


def _command_index(registry: ValidationCommandRegistry, command_id: str) -> int | None:
    for index, command in enumerate(registry.commands):
        if command.id == command_id:
            return index
    return None


def _parse_category(value: str) -> ValidationCommandCategory:
    try:
        return ValidationCommandCategory(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ValidationCommandCategory)
        msg = f"Invalid validation category: {value}. Allowed: {allowed}"
        raise ValueError(msg) from exc


def _parse_risk(value: str) -> ValidationRiskLevel:
    try:
        return ValidationRiskLevel(value.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(item.value for item in ValidationRiskLevel)
        msg = f"Invalid validation risk level: {value}. Allowed: {allowed}"
        raise ValueError(msg) from exc


def _risk_from_category(category: ValidationCommandCategory) -> ValidationRiskLevel:
    if category in {ValidationCommandCategory.LINT, ValidationCommandCategory.COMPILE}:
        return ValidationRiskLevel.MEDIUM
    if category in {ValidationCommandCategory.RESTORE, ValidationCommandCategory.BUILD, ValidationCommandCategory.TEST, ValidationCommandCategory.RUN}:
        return ValidationRiskLevel.MEDIUM
    if category == ValidationCommandCategory.BACKUP:
        return ValidationRiskLevel.HIGH
    return ValidationRiskLevel.MEDIUM


def _looks_like_target_command(command_lower: str) -> bool:
    return any(
        token in command_lower
        for token in (
            "dotnet restore",
            "dotnet build",
            "dotnet test",
            "npm test",
            "npm run build",
        )
    )


def _is_internal_devorchestrator_path(path: Path | None) -> bool:
    if not path:
        return False
    try:
        return path.resolve() == Path.cwd().resolve()
    except OSError:
        return False


def _normalize_id(command_id: str) -> str:
    normalized = command_id.strip()
    if not normalized:
        msg = "Validation command id is required."
        raise ValueError(msg)
    if not re.fullmatch(r"[A-Za-z0-9._-]+", normalized):
        msg = "Validation command id may contain only letters, numbers, dots, underscores, and hyphens."
        raise ValueError(msg)
    return normalized


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "command"


def _max_risk(left: ValidationRiskLevel, right: ValidationRiskLevel) -> ValidationRiskLevel:
    ranks = {
        ValidationRiskLevel.LOW: 0,
        ValidationRiskLevel.MEDIUM: 1,
        ValidationRiskLevel.HIGH: 2,
        ValidationRiskLevel.CRITICAL: 3,
    }
    return left if ranks[left] >= ranks[right] else right


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _dedupe_commands(commands: list[ValidationCommand]) -> list[ValidationCommand]:
    seen: set[str] = set()
    result: list[ValidationCommand] = []
    for command in commands:
        if command.id in seen:
            continue
        seen.add(command.id)
        result.append(command)
    return result
