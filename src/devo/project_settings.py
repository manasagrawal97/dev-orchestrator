from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .projects import get_workspace_root
from .scanner import load_registered_project
from .validation_registry import list_validation_commands, registry_path

PROJECT_SETTINGS_SCHEMA_VERSION = "1"
PROJECT_SETTINGS_FILE = "settings.json"


class DeliveryMode(StrEnum):
    MANUAL_COMMIT_PUSH = "manual_commit_push"
    APPROVED_COMMIT_PUSH = "approved_commit_push"


class ProjectSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = PROJECT_SETTINGS_SCHEMA_VERSION
    project_name: str
    default_lane: str | None = None
    default_validation_command: str | None = None
    default_full_test_command: str | None = None
    default_branch: str | None = None
    allow_auto_scope_template: bool = True
    delivery_mode: DeliveryMode = DeliveryMode.MANUAL_COMMIT_PUSH
    notes: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectSettingsUpdateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settings: ProjectSettings
    path: Path
    warnings: list[str] = Field(default_factory=list)


def project_settings_path(project_name: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    return root / "projects" / project_name / PROJECT_SETTINGS_FILE


def load_project_settings(project_name: str, workspace_root: Path | None = None) -> ProjectSettings:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    path = project_settings_path(project_name, workspace_root=root)
    if not path.exists():
        return ProjectSettings(project_name=project_name)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        settings = ProjectSettings.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        msg = f"Project settings are malformed: {path}"
        raise ValueError(msg) from exc
    if settings.project_name != project_name:
        msg = f"Project settings project mismatch: {settings.project_name}"
        raise ValueError(msg)
    return settings


def save_project_settings(settings: ProjectSettings, workspace_root: Path | None = None) -> ProjectSettingsUpdateResult:
    root = workspace_root or get_workspace_root()
    load_registered_project(settings.project_name, workspace_root=root)
    path = project_settings_path(settings.project_name, workspace_root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = settings.model_copy(update={"updated_at": datetime.now(UTC)})
    path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    return ProjectSettingsUpdateResult(settings=settings, path=path)


def update_project_settings(
    project_name: str,
    *,
    default_lane: str | None = None,
    default_validation_command: str | None = None,
    default_full_test_command: str | None = None,
    default_branch: str | None = None,
    allow_auto_scope_template: bool | None = None,
    delivery_mode: str | None = None,
    notes: str | None = None,
    workspace_root: Path | None = None,
) -> ProjectSettingsUpdateResult:
    root = workspace_root or get_workspace_root()
    current = load_project_settings(project_name, workspace_root=root)
    warnings: list[str] = []
    updates: dict[str, object] = {}

    if default_lane is not None:
        updates["default_lane"] = _clean_optional(default_lane)
    if default_validation_command is not None:
        command_id = _clean_optional(default_validation_command)
        _validate_command_id(project_name, command_id, "default validation command", root, warnings)
        updates["default_validation_command"] = command_id
    if default_full_test_command is not None:
        command_id = _clean_optional(default_full_test_command)
        _validate_command_id(project_name, command_id, "default full test command", root, warnings)
        updates["default_full_test_command"] = command_id
    if default_branch is not None:
        updates["default_branch"] = _clean_optional(default_branch)
    if allow_auto_scope_template is not None:
        updates["allow_auto_scope_template"] = allow_auto_scope_template
    if delivery_mode is not None:
        try:
            updates["delivery_mode"] = DeliveryMode(delivery_mode)
        except ValueError as exc:
            allowed = ", ".join(mode.value for mode in DeliveryMode)
            msg = f"Unknown delivery mode: {delivery_mode}. Expected one of: {allowed}"
            raise ValueError(msg) from exc
    if notes is not None:
        updates["notes"] = _clean_optional(notes)

    settings = current.model_copy(update=updates)
    result = save_project_settings(settings, workspace_root=root)
    return ProjectSettingsUpdateResult(settings=result.settings, path=result.path, warnings=warnings)


def _validate_command_id(
    project_name: str,
    command_id: str | None,
    label: str,
    workspace_root: Path,
    warnings: list[str],
) -> None:
    if not command_id:
        return
    path = registry_path(project_name, workspace_root=workspace_root)
    commands = list_validation_commands(project_name, workspace_root=workspace_root)
    if not path.exists():
        warnings.append(f"{label} set to {command_id}, but no validation registry exists yet.")
        return
    command_ids = {command.id for command in commands}
    if command_id not in command_ids:
        msg = f"Configured {label} is not registered: {command_id}"
        raise ValueError(msg)


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
