from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .projects import get_workspace_root
from .runs import create_run, load_run, run_path, save_run_state
from .scanner import load_registered_project
from .schemas import RunArtifact, RunArtifactType, RunStatus, ValidationCommandCategory, ValidationRunRecord
from .validation_registry import get_validation_command, list_validation_commands

WORK_PACKAGE_SCHEMA_VERSION = "1"
WORK_PACKAGE_DIR = "work-package"
WORK_PACKAGE_JSON = "work-package.json"
WORK_PACKAGE_MD = "work-package.md"
OPERATOR_PROMPT_MD = "operator-prompt.md"
SCOPE_TEMPLATE_MD = "scope-template.md"
SUPPORTED_PROMPT_PHASES = {"scope", "implement", "validate", "deliver", "complete"}


class WorkPackageStatus(StrEnum):
    DRAFT = "draft"
    SCOPE_PROPOSED = "scope_proposed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    VALIDATED = "validated"
    DELIVERED = "delivered"
    CLOSED = "closed"


class WorkLane(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    allowed: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    default_validation_commands: list[str] = Field(default_factory=list)
    default_validation_categories: list[str] = Field(default_factory=list)
    require_registered_validation_command: bool = False
    notes: list[str] = Field(default_factory=list)


class WorkPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = WORK_PACKAGE_SCHEMA_VERSION
    project: str
    run_id: str
    goal: str
    lane: str
    status: WorkPackageStatus
    proposed_items: list[str] = Field(default_factory=list)
    approved_files: list[str] = Field(default_factory=list)
    allowed_changes: list[str] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    delivery_plan: list[str] = Field(default_factory=list)
    approval_bundle_id: str | None = None
    delivered_at: datetime | None = None
    commit_hash: str | None = None
    delivery_summary: str | None = None
    validation_run_id: str | None = None
    validation_status: str | None = None
    approval_bundle_status: str | None = None
    final_git_status: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScopeImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package: WorkPackage
    scope_file: Path
    missing_sections: list[str] = Field(default_factory=list)


class WorkPackageNextStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_status: WorkPackageStatus
    next_action: str
    required_command: str | None = None
    suggested_prompt_command: str | None = None
    stop_conditions: list[str] = Field(default_factory=list)
    user_approval_needed: bool = False


class WorkPackagePhasePrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    prompt_path: Path
    prompt_text: str


class WorkPackageScopeTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_path: Path
    template_text: str


BUILT_IN_LANES: dict[str, WorkLane] = {
    "docs-only": WorkLane(
        id="docs-only",
        name="Docs only",
        allowed=[
            "README.md",
            "docs/**",
            "Markdown documentation",
            "Mermaid diagrams in docs",
            "non-source planning notes",
        ],
        forbidden=[
            "source code",
            "target project source files unless explicitly scoped",
            "DB/migrations",
            "secrets/appsettings/local settings",
            "scripts/backups",
            "generated files",
            "build/test/app run unless explicitly requested",
        ],
        default_validation_commands=["git-diff-check"],
        notes=[
            "No build required by default.",
            "Use git diff --check as the normal docs-only validation.",
        ],
    ),
    "low-risk-ui-maintenance": WorkLane(
        id="low-risk-ui-maintenance",
        name="Low-risk UI maintenance",
        allowed=[
            "Razor UI files",
            "UI help text",
            "empty states",
            "mechanical analyzer/warning fixes",
            "small display-only prompts using already-loaded data",
            "dotnet build validation",
        ],
        forbidden=[
            "DB changes",
            "migrations",
            "appsettings",
            "secrets",
            "local settings",
            "scripts",
            "backups",
            "generated files",
            "user data",
            "app run",
            "external API calls",
            "behavior-heavy refactors",
        ],
        default_validation_commands=["dotnet-build-personalos"],
        require_registered_validation_command=True,
        notes=[
            "Prefer project validation command dotnet-build-personalos when present.",
            "If that command is not registered, import-scope must provide a validation command.",
        ],
    ),
    "warning-cleanup": WorkLane(
        id="warning-cleanup",
        name="Warning cleanup",
        allowed=[
            "small mechanical warning/analyzer fixes",
            "source files needed for exact warning cleanup",
            "docs update if needed",
        ],
        forbidden=[
            "behavior refactors",
            "DB/migrations",
            "config/secrets",
            "app run/external APIs",
            "unrelated cleanup",
        ],
        default_validation_commands=["<project-build-command-id>"],
        default_validation_categories=[ValidationCommandCategory.BUILD.value],
        notes=["Prefer the registered project build validation command when available."],
    ),
    "small-bugfix": WorkLane(
        id="small-bugfix",
        name="Small bugfix",
        allowed=[
            "small focused source fix",
            "minimal tests if existing",
            "docs note if needed",
        ],
        forbidden=[
            "DB schema changes",
            "broad refactor",
            "config/secrets",
            "app run/external APIs unless explicitly approved",
            "unrelated files",
        ],
        default_validation_commands=["<build-command-id>", "<targeted-test-command-id>"],
        default_validation_categories=[ValidationCommandCategory.BUILD.value, ValidationCommandCategory.TEST.value],
        notes=["Use build validation and targeted tests when registered and appropriate."],
    ),
    "small-feature": WorkLane(
        id="small-feature",
        name="Small feature",
        allowed=[
            "small feature within approved files/modules",
            "UI/application changes",
            "tests/docs if relevant",
        ],
        forbidden=[
            "DB/migrations unless separate high-risk approval",
            "config/secrets",
            "broad architecture changes",
            "external APIs unless explicitly approved",
        ],
        default_validation_commands=["<build-command-id>", "<test-command-id>"],
        default_validation_categories=[ValidationCommandCategory.BUILD.value, ValidationCommandCategory.TEST.value],
        notes=["Keep scope to one approved feature/requirement and validate with build plus tests when available."],
    ),
    "test-only": WorkLane(
        id="test-only",
        name="Test only",
        allowed=[
            "test files",
            "test helpers",
            "docs note if needed",
        ],
        forbidden=[
            "production source changes unless explicitly approved",
            "DB/migrations",
            "config/secrets",
            "app run/external APIs",
        ],
        default_validation_commands=["<targeted-test-command-id>", "<full-test-command-id>"],
        default_validation_categories=[ValidationCommandCategory.TEST.value],
        notes=["Prefer a targeted registered test command; use full tests only when registered and approved."],
    ),
    "backup-maintenance": WorkLane(
        id="backup-maintenance",
        name="Backup maintenance",
        allowed=[
            "Devo backup/recovery scripts",
            "backup status/list/reporting code",
            "recovery docs",
            "tests using temp directories",
        ],
        forbidden=[
            "real restore",
            "deleting real backups",
            "modifying live scheduler unless explicitly approved",
            "creating real backup unless explicitly approved",
            "PersonalOS changes",
        ],
        default_validation_commands=["backup-recovery-tests"],
        default_validation_categories=[ValidationCommandCategory.TEST.value],
        notes=["Validation should use temp directories only and must not touch real backups."],
    ),
    "devo-internal-source": WorkLane(
        id="devo-internal-source",
        name="DevOrchestrator internal source",
        allowed=[
            "DevOrchestrator source code",
            "tests",
            "docs",
        ],
        forbidden=[
            "PersonalOS changes",
            "workspace artifacts in commits",
            ".venv/.env/.pytest_cache/pt-* folders",
            "real backup/restore unless explicitly approved",
        ],
        default_validation_commands=["py-compile-core", "focused-tests", "full-pytest"],
        default_validation_categories=[
            ValidationCommandCategory.COMPILE.value,
            ValidationCommandCategory.TEST.value,
            ValidationCommandCategory.LINT.value,
        ],
        notes=["Use py_compile, focused tests, full suite, and git diff --check as appropriate for Devo source work."],
    ),
}

REQUIRED_SCOPE_SECTIONS = {
    "selected items": "proposed_items",
    "exact files": "approved_files",
    "allowed changes": "allowed_changes",
    "forbidden changes": "forbidden_changes",
    "validation command": "validation_commands",
    "delivery plan": "delivery_plan",
}


def list_lanes() -> list[WorkLane]:
    return list(BUILT_IN_LANES.values())


def get_lane(lane_id: str) -> WorkLane:
    normalized = lane_id.strip()
    lane = BUILT_IN_LANES.get(normalized)
    if not lane:
        allowed = ", ".join(sorted(BUILT_IN_LANES))
        msg = f"Unknown work lane: {lane_id}. Available lanes: {allowed}"
        raise ValueError(msg)
    return lane


def start_work_package(
    project_name: str,
    lane_id: str,
    goal: str,
    workspace_root: Path | None = None,
) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    lane = get_lane(lane_id)
    run_state = create_run(project_name, goal, workspace_root=root)
    validation_commands = _default_validation_commands(project_name, lane, root)
    package = WorkPackage(
        project=project_name,
        run_id=run_state.run_id,
        goal=goal,
        lane=lane.id,
        status=WorkPackageStatus.DRAFT,
        allowed_changes=list(lane.allowed),
        forbidden_changes=list(lane.forbidden),
        validation_commands=validation_commands,
    )
    save_work_package(package, workspace_root=root)
    return package


def import_work_scope(
    project_name: str,
    run_id: str,
    scope_file: Path,
    workspace_root: Path | None = None,
) -> ScopeImportResult:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    source_path = scope_file.expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        msg = f"Scope import file does not exist: {source_path}"
        raise ValueError(msg)
    text = source_path.read_text(encoding="utf-8")
    sections = _extract_sections(text)
    missing = [section for section in REQUIRED_SCOPE_SECTIONS if not sections.get(section)]
    if missing:
        msg = f"Scope file is missing required sections: {', '.join(missing)}"
        raise ValueError(msg)

    updated = package.model_copy(
        update={
            "status": WorkPackageStatus.SCOPE_PROPOSED,
            "proposed_items": _section_items(sections["selected items"]),
            "approved_files": _section_items(sections["exact files"]),
            "allowed_changes": _section_items(sections["allowed changes"]),
            "forbidden_changes": _section_items(sections["forbidden changes"]),
            "validation_commands": _normalize_validation_commands(_section_items(sections["validation command"])),
            "delivery_plan": _section_items(sections["delivery plan"]),
            "updated_at": datetime.now(UTC),
        }
    )
    save_work_package(updated, workspace_root=root)
    _write_task_artifact(updated, workspace_root=root)
    return ScopeImportResult(package=updated, scope_file=source_path)


def load_work_package(project_name: str, run_id: str, workspace_root: Path | None = None) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    load_run(project_name, run_id, workspace_root=root)
    path = work_package_path(project_name, run_id, workspace_root=root)
    if not path.exists():
        msg = f"Work package not found for run: {run_id}"
        raise ValueError(msg)
    data = json.loads(path.read_text(encoding="utf-8"))
    return WorkPackage.model_validate(data)


def complete_work_package(
    project_name: str,
    run_id: str,
    commit_hash: str,
    delivery_summary: str,
    workspace_root: Path | None = None,
) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    normalized_commit = commit_hash.strip()
    normalized_summary = delivery_summary.strip()
    if not normalized_commit:
        msg = "Commit hash is required."
        raise ValueError(msg)
    if not normalized_summary:
        msg = "Delivery summary is required."
        raise ValueError(msg)

    validation = _latest_validation_record(project_name, run_id, root)
    updated = package.model_copy(
        update={
            "status": WorkPackageStatus.DELIVERED,
            "delivered_at": datetime.now(UTC),
            "commit_hash": normalized_commit,
            "delivery_summary": normalized_summary,
            "validation_run_id": validation.validation_run_id if validation else None,
            "validation_status": validation.status.value if validation else None,
            "approval_bundle_status": _approval_bundle_status(package, root),
            "final_git_status": _latest_git_delivery_status(project_name, run_id, root),
            "updated_at": datetime.now(UTC),
        }
    )
    return save_work_package(updated, workspace_root=root)


def save_work_package(package: WorkPackage, workspace_root: Path | None = None) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    package = package.model_copy(update={"updated_at": datetime.now(UTC)})
    directory = _work_package_dir(root, package.project, package.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / WORK_PACKAGE_JSON).write_text(package.model_dump_json(indent=2), encoding="utf-8")
    (directory / WORK_PACKAGE_MD).write_text(render_work_package_markdown(package), encoding="utf-8")
    (directory / OPERATOR_PROMPT_MD).write_text(render_operator_prompt(package, workspace_root=root), encoding="utf-8")
    return package


def set_work_package_approval_bundle(
    project_name: str,
    run_id: str,
    bundle_id: str,
    workspace_root: Path | None = None,
) -> WorkPackage:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    updated = package.model_copy(
        update={
            "approval_bundle_id": bundle_id,
            "status": WorkPackageStatus.APPROVAL_REQUESTED,
            "updated_at": datetime.now(UTC),
        }
    )
    return save_work_package(updated, workspace_root=root)


def work_package_path(project_name: str, run_id: str, workspace_root: Path | None = None) -> Path:
    root = workspace_root or get_workspace_root()
    return _work_package_dir(root, project_name, run_id) / WORK_PACKAGE_JSON


def work_package_artifact_paths(package: WorkPackage, workspace_root: Path | None = None) -> dict[str, Path]:
    root = workspace_root or get_workspace_root()
    directory = _work_package_dir(root, package.project, package.run_id)
    return {
        "json": directory / WORK_PACKAGE_JSON,
        "markdown": directory / WORK_PACKAGE_MD,
        "operator_prompt": directory / OPERATOR_PROMPT_MD,
        "scope_template": directory / SCOPE_TEMPLATE_MD,
    }


def work_package_phase_prompt_path(
    project_name: str,
    run_id: str,
    phase: str,
    workspace_root: Path | None = None,
) -> Path:
    root = workspace_root or get_workspace_root()
    normalized_phase = _normalize_phase(phase)
    return _work_package_dir(root, project_name, run_id) / f"operator-prompt-{normalized_phase}.md"


def generate_work_package_phase_prompt(
    project_name: str,
    run_id: str,
    phase: str,
    workspace_root: Path | None = None,
) -> WorkPackagePhasePrompt:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    normalized_phase = _normalize_phase(phase)
    prompt_text = render_phase_operator_prompt(package, normalized_phase, workspace_root=root)
    prompt_path = work_package_phase_prompt_path(project_name, run_id, normalized_phase, workspace_root=root)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text, encoding="utf-8")
    return WorkPackagePhasePrompt(phase=normalized_phase, prompt_path=prompt_path, prompt_text=prompt_text)


def work_package_scope_template_path(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> Path:
    root = workspace_root or get_workspace_root()
    return _work_package_dir(root, project_name, run_id) / SCOPE_TEMPLATE_MD


def generate_work_scope_template(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> WorkPackageScopeTemplate:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    template_text = render_work_scope_template(package, workspace_root=root)
    template_path = work_package_scope_template_path(project_name, run_id, workspace_root=root)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template_text, encoding="utf-8")
    return WorkPackageScopeTemplate(template_path=template_path, template_text=template_text)


def render_work_scope_template(package: WorkPackage, workspace_root: Path | None = None) -> str:
    root = workspace_root or get_workspace_root()
    lane = get_lane(package.lane)
    validation_commands = _scope_template_validation_commands(package, lane, root)
    lines = [
        f"# Work Package Scope Template: {package.goal}",
        "",
        f"- project: {package.project}",
        f"- run_id: {package.run_id}",
        f"- lane: {lane.id}",
        "- instructions: Fill TODO items, keep the scope low-risk, then import with `devo work import-scope`.",
        "",
        "## Selected Items",
        "",
    ]
    lines.extend(_template_items(package.proposed_items, ["TODO: describe selected item 1"]))
    lines.extend(["", "## Exact Files", ""])
    lines.extend(_template_items(package.approved_files, ["TODO: list exact file path or approved area"]))
    lines.extend(["", "## Allowed Changes", ""])
    lines.extend(_template_items(package.allowed_changes or lane.allowed, lane.allowed))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_template_items(package.forbidden_changes or lane.forbidden, lane.forbidden))
    lines.extend(["", "## Validation Command", ""])
    lines.extend(_template_items(validation_commands, ["<validation-command-id>"]))
    lines.extend(["", "## Delivery Plan", ""])
    lines.extend(
        _template_items(
            package.delivery_plan,
            [
                "Run safe git status and diff checks before validation.",
                "Run approved validation command through Devo.",
                "Commit and push only approved files after validation passes.",
                "Run `devo work complete` with the delivered commit hash.",
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Lane Notes",
            "",
        ]
    )
    lines.extend(_template_items(lane.notes, ["Review lane constraints before requesting approval."]))
    lines.extend(
        [
            "",
            "## Excluded Items",
            "",
            "- TODO: list intentionally excluded files, warnings, features, or behaviors",
            "",
            "## Expected Validation Result",
            "",
            f"- {', '.join(validation_commands)} passes without app run, DB commands, scripts, backups, or external API calls.",
            "",
            "## Stop Conditions",
            "",
        ]
    )
    lines.extend(_bullets(_default_stop_conditions()))
    lines.extend(
        [
            "",
            "## Approval Bundle Note",
            "",
            "- Request one approval bundle after importing this scope.",
            "- Do not edit target project files before the bundle is approved.",
            "",
            "## Final Report Expectations",
            "",
            "- changed files",
            "- implementation summary",
            "- validation result and artifact path",
            "- Devo report/context artifacts",
            "- commit hash and push result",
            "- final Git status",
            "",
        ]
    )
    return "\n".join(lines)


def render_work_scope_example(lane_id: str) -> str:
    lane = get_lane(lane_id)
    validation_commands = lane.default_validation_commands or ["<validation-command-id>"]
    lines = [
        f"# Example Work Package Scope: {lane.name}",
        "",
        "## Selected Items",
        "",
        "- Add empty/help states to approved Razor list pages",
        "- Add display-only guidance using already-loaded data",
        "",
        "## Exact Files",
        "",
        "- src/web/PersonalOS.Web/Components/Pages/ExampleList.razor",
        "- src/web/PersonalOS.Web/Components/Pages/ExampleDetails.razor",
        "",
        "## Allowed Changes",
        "",
    ]
    lines.extend(_bullets(lane.allowed))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(lane.forbidden))
    lines.extend(["", "## Validation Command", ""])
    lines.extend(_bullets(validation_commands))
    lines.extend(
        [
            "",
            "## Delivery Plan",
            "",
            "- Run safe git status and diff checks before validation.",
            "- Run approved validation command through Devo.",
            "- Commit and push only approved files after validation passes.",
            "",
            "## Lane Notes",
            "",
        ]
    )
    lines.extend(_bullets(lane.notes))
    lines.extend(
        [
            "",
            "## Excluded Items",
            "",
            "- DB, services, models, config, secrets, generated files, app run, and external APIs",
            "",
            "## Expected Validation Result",
            "",
            f"- {', '.join(validation_commands)} passes.",
            "",
            "## Stop Conditions",
            "",
        ]
    )
    lines.extend(_bullets(_default_stop_conditions()))
    lines.extend(
        [
            "",
            "## Approval Bundle Note",
            "",
            "- Request one approval bundle after importing the completed scope.",
            "",
            "## Final Report Expectations",
            "",
            "- changed files",
            "- validation result",
            "- commit hash and push result",
            "",
        ]
    )
    return "\n".join(lines)


def render_work_package_markdown(package: WorkPackage) -> str:
    lines = [
        f"# Work Package: {package.goal}",
        "",
        f"- schema_version: {package.schema_version}",
        f"- project: {package.project}",
        f"- run_id: {package.run_id}",
        f"- lane: {package.lane}",
        f"- status: {package.status.value}",
        f"- approval_bundle_id: {package.approval_bundle_id or 'none'}",
        f"- created_at: {package.created_at.isoformat()}",
        f"- updated_at: {package.updated_at.isoformat()}",
        "",
        "## Proposed Items",
        "",
    ]
    lines.extend(_bullets(package.proposed_items))
    lines.extend(["", "## Approved Files", ""])
    lines.extend(_bullets(package.approved_files))
    lines.extend(["", "## Allowed Changes", ""])
    lines.extend(_bullets(package.allowed_changes))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(package.forbidden_changes))
    lines.extend(["", "## Validation Commands", ""])
    lines.extend(_bullets(package.validation_commands))
    lines.extend(["", "## Delivery Plan", ""])
    lines.extend(_bullets(package.delivery_plan))
    lines.extend(
        [
            "",
            "## Final Delivery",
            "",
            f"- delivered_at: {package.delivered_at.isoformat() if package.delivered_at else 'none'}",
            f"- commit_hash: {package.commit_hash or 'none'}",
            f"- delivery_summary: {package.delivery_summary or 'none'}",
            f"- validation_run_id: {package.validation_run_id or 'none'}",
            f"- validation_status: {package.validation_status or 'none'}",
            f"- approval_bundle_status: {package.approval_bundle_status or 'none'}",
            f"- final_git_status: {package.final_git_status or 'none'}",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def render_operator_prompt(package: WorkPackage, workspace_root: Path | None = None) -> str:
    root = workspace_root or get_workspace_root()
    project = load_registered_project(package.project, workspace_root=root)
    lines = [
        f"# Codex Operator Prompt: {package.goal}",
        "",
        f"Project: {package.project}",
        f"Project path: {project.path}",
        f"Run id: {package.run_id}",
        f"Lane: {package.lane}",
        f"Status: {package.status.value}",
        "",
        "## Goal",
        "",
        package.goal,
        "",
        "## Allowed Changes",
        "",
    ]
    lines.extend(_bullets(package.allowed_changes))
    lines.extend(["", "## Approved Files Or Areas", ""])
    lines.extend(_bullets(package.approved_files))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(package.forbidden_changes))
    lines.extend(
        [
            "",
            "## Approval Rules",
            "",
            "- Do not edit target project files until the approval bundle is approved.",
            "- Child approvals remain normal Devo approvals.",
            "- A bundle does not bypass Codex, OS, GitHub, shell, or external-service approval policy.",
            "- Stop if scope changes or a child approval is rejected/blocked.",
            "",
            "## Validation Command",
            "",
        ]
    )
    lines.extend(_bullets(package.validation_commands))
    lines.extend(
        [
            "",
            "## Delivery Rules",
            "",
        ]
    )
    lines.extend(_bullets(package.delivery_plan))
    lines.extend(
        [
            "",
            "## Stop Conditions",
            "",
            "- DB, migrations, appsettings, secrets, local settings, scripts, backups, generated files, user data, app run, or external API calls are needed.",
            "- A file outside the approved scope is needed.",
            "- The fix requires a behavior-heavy refactor.",
            "- Validation fails.",
            "- Git is dirty in an unexpected way.",
            "",
            "## Final Report Format",
            "",
            "- changed files",
            "- exact behavior changed",
            "- validation result",
            "- Devo artifacts",
            "- commit hash",
            "- push result",
            "- final Git status",
            "",
        ]
    )
    return "\n".join(lines)


def render_phase_operator_prompt(package: WorkPackage, phase: str, workspace_root: Path | None = None) -> str:
    root = workspace_root or get_workspace_root()
    normalized_phase = _normalize_phase(phase)
    project = load_registered_project(package.project, workspace_root=root)
    next_step = get_work_package_next_step(package)
    lines = [
        f"# Codex Work-Package Prompt: {normalized_phase}",
        "",
        f"Project: {package.project}",
        f"Project path: {project.path}",
        f"Run id: {package.run_id}",
        f"Lane: {package.lane}",
        f"Goal: {package.goal}",
        f"Status: {package.status.value}",
        f"Approval bundle: {package.approval_bundle_id or 'none'}",
        f"Approval bundle status: {package.approval_bundle_status or 'unknown'}",
        "",
        "## Approved Files",
        "",
    ]
    lines.extend(_bullets(package.approved_files))
    lines.extend(["", "## Allowed Changes", ""])
    lines.extend(_bullets(package.allowed_changes))
    lines.extend(["", "## Forbidden Changes", ""])
    lines.extend(_bullets(package.forbidden_changes))
    lines.extend(["", "## Validation Command", ""])
    lines.extend(_bullets(package.validation_commands))
    lines.extend(
        [
            "",
            "## Phase Objective",
            "",
            _phase_objective(normalized_phase, package),
            "",
            "## Exact Commands",
            "",
        ]
    )
    lines.extend(_phase_commands(normalized_phase, package))
    lines.extend(["", "## Stop Conditions", ""])
    lines.extend(_bullets(next_step.stop_conditions))
    lines.extend(
        [
            "",
            "## Final Report Format",
            "",
            "- phase completed",
            "- files changed, or confirmation none changed",
            "- validation result, if validation was run",
            "- Devo artifact paths",
            "- commit hash and push result, if delivered",
            "- final Git status",
            "",
        ]
    )
    return "\n".join(lines)


def _write_task_artifact(package: WorkPackage, workspace_root: Path) -> None:
    run_state = load_run(package.project, package.run_id, workspace_root=workspace_root)
    artifacts_dir = run_path(package.project, package.run_id, workspace_root=workspace_root) / "artifacts"
    tasks_path = artifacts_dir / "tasks.md"
    task_text = _render_task_artifact(package)
    tasks_path.write_text(task_text, encoding="utf-8")
    artifact = RunArtifact(
        artifact_type=RunArtifactType.TASKS,
        agent_name="WorkPackage",
        source_file_path=work_package_artifact_paths(package, workspace_root=workspace_root)["markdown"],
        artifact_path=tasks_path,
    )
    run_state.artifacts = [item for item in run_state.artifacts if item.artifact_type != RunArtifactType.TASKS]
    run_state.artifacts.append(artifact)
    run_state.status = RunStatus.TASKS_DRAFTED
    run_state.updated_at = datetime.now(UTC)
    save_run_state(run_state, workspace_root=workspace_root)


def _render_task_artifact(package: WorkPackage) -> str:
    return "\n".join(
        [
            "# task-list.md",
            "",
            "## Task T001",
            "",
            "- task id: T001",
            f"- task title: {package.goal}",
            f"- objective: {package.goal}",
            f"- scope: Work package lane {package.lane}; files {', '.join(package.approved_files) or 'none specified'}.",
            f"- out-of-scope: {', '.join(package.forbidden_changes) or 'none specified'}.",
            f"- likely files or areas: {', '.join(package.approved_files) or 'none specified'}.",
            f"- validation required: {', '.join(package.validation_commands) or 'none specified'}.",
            "- risk level: high",
            "- dependencies: Approval bundle before source edit and build validation.",
            "- recommended executor: Codex after bundled approval.",
            "",
            "# task-dependency-map.md",
            "",
            "- T001 has no implementation dependencies other than approval.",
            "",
            "# first-safe-task.md",
            "",
            "T001 is the selected work package task after approval.",
            "",
        ]
    )


def _extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(r"(?ims)^#{1,6}\s+(.+?)\s*$\n?(.*?)(?=^#{1,6}\s+.+?\s*$|\Z)")
    for match in pattern.finditer(text):
        title = _normalize_heading(match.group(1))
        body = match.group(2).strip()
        if title in REQUIRED_SCOPE_SECTIONS:
            sections[title] = body
    return sections


def _normalize_heading(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
    normalized = " ".join(normalized.split())
    aliases = {
        "validation commands": "validation command",
    }
    return aliases.get(normalized, normalized)


def _section_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[-*]\s+", "", stripped)
        stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
        if stripped:
            items.append(stripped.strip("`"))
    if not items and text.strip():
        items.append(" ".join(text.strip().split()))
    return items


def _normalize_validation_commands(items: list[str]) -> list[str]:
    commands: list[str] = []
    for item in items:
        value = item.strip()
        if not value:
            continue
        match = re.search(r"\b[A-Za-z0-9._-]+\b", value)
        commands.append(match.group(0) if match else value)
    return commands


def _default_validation_commands(project_name: str, lane: WorkLane, workspace_root: Path) -> list[str]:
    return _registered_lane_validation_commands(project_name, lane, workspace_root)


def _scope_template_validation_commands(package: WorkPackage, lane: WorkLane, workspace_root: Path) -> list[str]:
    if package.validation_commands:
        return package.validation_commands
    registered_defaults = _registered_lane_validation_commands(package.project, lane, workspace_root)
    if registered_defaults:
        return registered_defaults
    if lane.require_registered_validation_command:
        return ["<validation-command-id>"]
    return lane.default_validation_commands or ["<validation-command-id>"]


def _registered_lane_validation_commands(project_name: str, lane: WorkLane, workspace_root: Path) -> list[str]:
    commands = list_validation_commands(project_name, workspace_root=workspace_root)
    registered_by_id = {command.id: command for command in commands}
    selected: list[str] = []
    for command_id in lane.default_validation_commands:
        if command_id in registered_by_id:
            selected.append(command_id)
    categories = set(lane.default_validation_categories)
    for command in commands:
        if command.category.value in categories:
            selected.append(command.id)
    return _dedupe(selected)


def _template_items(existing_items: list[str], fallback_items: list[str]) -> list[str]:
    items = existing_items or fallback_items
    return _bullets(items)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _work_package_dir(workspace_root: Path, project_name: str, run_id: str) -> Path:
    return run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / WORK_PACKAGE_DIR


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def bundle_id_for_package(project_name: str, run_id: str, task_id: str, created_at: datetime) -> str:
    seed = f"{project_name}|{run_id}|{task_id}|{created_at.isoformat()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def validation_command_details(project_name: str, command_id: str, workspace_root: Path | None = None) -> tuple[str, str]:
    command = get_validation_command(project_name, command_id, workspace_root=workspace_root)
    return command.id, command.command


def get_work_package_next_step(package: WorkPackage) -> WorkPackageNextStep:
    stop_conditions = _default_stop_conditions()
    if package.status == WorkPackageStatus.DRAFT:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Generate/fill/import scope",
            required_command=f"devo work scope-template --project {package.project} --run {package.run_id}",
            suggested_prompt_command=None,
            stop_conditions=stop_conditions,
            user_approval_needed=False,
        )
    if package.status == WorkPackageStatus.SCOPE_PROPOSED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Request approval bundle",
            required_command=f"devo work request-approval-bundle --project {package.project} --run {package.run_id} --task T001",
            suggested_prompt_command=None,
            stop_conditions=stop_conditions,
            user_approval_needed=True,
        )
    if package.status == WorkPackageStatus.APPROVAL_REQUESTED:
        command = None
        if package.approval_bundle_id:
            command = (
                f"devo approval bundle-approve --project {package.project} --run {package.run_id} "
                f"--bundle {package.approval_bundle_id} --by <name>"
            )
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Approve bundle or wait",
            required_command=command,
            suggested_prompt_command=None,
            stop_conditions=stop_conditions,
            user_approval_needed=True,
        )
    if package.status == WorkPackageStatus.APPROVED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Implement approved scope",
            required_command=_prompt_command(package, "implement"),
            suggested_prompt_command=_prompt_command(package, "implement"),
            stop_conditions=stop_conditions,
            user_approval_needed=False,
        )
    if package.status == WorkPackageStatus.IMPLEMENTED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Run validation",
            required_command=_prompt_command(package, "validate"),
            suggested_prompt_command=_prompt_command(package, "validate"),
            stop_conditions=stop_conditions,
            user_approval_needed=False,
        )
    if package.status == WorkPackageStatus.VALIDATED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="Generate delivery report and commit/push",
            required_command=_prompt_command(package, "deliver"),
            suggested_prompt_command=_prompt_command(package, "deliver"),
            stop_conditions=stop_conditions,
            user_approval_needed=False,
        )
    if package.status == WorkPackageStatus.DELIVERED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="No action needed",
            required_command=None,
            suggested_prompt_command=None,
            stop_conditions=[],
            user_approval_needed=False,
        )
    if package.status == WorkPackageStatus.CLOSED:
        return WorkPackageNextStep(
            current_status=package.status,
            next_action="No action needed",
            required_command=None,
            suggested_prompt_command=None,
            stop_conditions=[],
            user_approval_needed=False,
        )
    return WorkPackageNextStep(
        current_status=package.status,
        next_action="Inspect work package state",
        required_command=f"devo work status --project {package.project} --run {package.run_id}",
        suggested_prompt_command=None,
        stop_conditions=stop_conditions,
        user_approval_needed=False,
    )


def work_package_next_action(package: WorkPackage) -> str:
    return get_work_package_next_step(package).next_action


def _prompt_command(package: WorkPackage, phase: str) -> str:
    return f"devo work prompt --project {package.project} --run {package.run_id} --phase {phase}"


def _normalize_phase(phase: str) -> str:
    normalized = phase.strip().lower()
    if normalized not in SUPPORTED_PROMPT_PHASES:
        allowed = ", ".join(sorted(SUPPORTED_PROMPT_PHASES))
        msg = f"Unknown work prompt phase: {phase}. Supported phases: {allowed}"
        raise ValueError(msg)
    return normalized


def _default_stop_conditions() -> list[str]:
    return [
        "The task needs DB, migrations, appsettings, secrets, local settings, scripts, backups, generated files, user data, app run, or external API calls.",
        "A file outside the approved work-package scope is needed.",
        "The change requires a behavior-heavy refactor or a different risk category.",
        "Validation fails or the validation method changes.",
        "Git is dirty in an unexpected way.",
    ]


def _phase_objective(phase: str, package: WorkPackage) -> str:
    objectives = {
        "scope": "Prepare a low-risk scope markdown file and import it into this work package. Do not edit target project source files.",
        "implement": "Implement only the approved work-package scope in the approved files, then run safe diff checks.",
        "validate": "Run the registered validation command through Devo using the existing approval bundle. Do not bypass Devo validation gates.",
        "deliver": "Generate delivery evidence, refresh reports, commit only approved target files, and push after validation has passed.",
        "complete": "Record the delivered commit and summary with `devo work complete`, then generate final reports.",
    }
    return objectives[phase].replace("this work package", f"this {package.lane} work package")


def _phase_commands(phase: str, package: WorkPackage) -> list[str]:
    validation_commands = package.validation_commands or ["<validationCommandId>"]
    validation_lines = [
        f"- devo validation run --project {package.project} --run {package.run_id} --task T001 --id {command_id} --allow-disabled"
        for command_id in validation_commands
    ]
    diff_paths = " ".join(package.approved_files) if package.approved_files else "<approved-files>"
    commands = {
        "scope": [
            f"- devo work scope-template --project {package.project} --run {package.run_id}",
            "- Fill the generated scope-template.md with selected items, exact files, and delivery details.",
            f"- devo work import-scope --project {package.project} --run {package.run_id} --file <scopeMarkdownFile>",
            f"- devo work request-approval-bundle --project {package.project} --run {package.run_id} --task T001",
        ],
        "implement": [
            f"- devo approval bundle-status --project {package.project} --run {package.run_id} --bundle {package.approval_bundle_id or '<bundleId>'}",
            "- git status -sb",
            "- git diff --check",
            f"- git diff -- {diff_paths}",
            f"- devo git delivery-check --project {package.project}",
        ],
        "validate": validation_lines,
        "deliver": [
            f"- devo git delivery-report --project {package.project} --run {package.run_id} --message \"<summary>\"",
            f"- devo project context-refresh --project {package.project} --run {package.run_id} --write-draft",
            f"- devo report run --project {package.project} --run {package.run_id} --write",
            f"- devo report handoff --project {package.project} --run {package.run_id} --write",
            "- git status -sb",
            f"- git add {diff_paths}",
            "- git commit -m \"<message>\"",
            "- git push origin <branch>",
        ],
        "complete": [
            f"- devo work complete --project {package.project} --run {package.run_id} --commit <commitHash> --message \"<summary>\"",
            f"- devo work status --project {package.project} --run {package.run_id}",
            f"- devo report run --project {package.project} --run {package.run_id} --write",
            f"- devo report handoff --project {package.project} --run {package.run_id} --write",
        ],
    }
    return commands[phase]


def _latest_validation_record(project_name: str, run_id: str, workspace_root: Path) -> ValidationRunRecord | None:
    validation_root = run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / "validation-runs"
    records: list[ValidationRunRecord] = []
    for path in sorted(validation_root.glob("*/validation-run.json")):
        try:
            records.append(ValidationRunRecord.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    if not records:
        return None
    return sorted(records, key=lambda record: record.started_at, reverse=True)[0]


def _approval_bundle_status(package: WorkPackage, workspace_root: Path) -> str | None:
    if not package.approval_bundle_id:
        return None
    path = (
        run_path(package.project, package.run_id, workspace_root=workspace_root)
        / "artifacts"
        / "approval-bundles"
        / f"approval-bundle-{package.approval_bundle_id}.json"
    )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    status = data.get("status")
    return str(status) if status else None


def _latest_git_delivery_status(project_name: str, run_id: str, workspace_root: Path) -> str | None:
    delivery_root = run_path(project_name, run_id, workspace_root=workspace_root) / "artifacts" / "git-delivery"
    reports: list[tuple[datetime, str]] = []
    for path in sorted(delivery_root.glob("git-delivery-report-*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        created_at = _parse_datetime(str(data.get("created_at") or ""))
        check = data.get("delivery_check") or {}
        status = check.get("status") or {}
        readiness = check.get("readiness") or "unknown"
        branch = status.get("current_branch") or "unknown"
        head = status.get("head_commit") or "unknown"
        clean = status.get("working_tree_clean")
        reports.append((created_at, f"{readiness}; branch={branch}; head={head}; clean={clean}"))
    if not reports:
        return None
    return sorted(reports, key=lambda item: item[0], reverse=True)[0][1]


def _parse_datetime(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
