from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ProjectRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    path: Path
    looks_like_software_project: bool
    detected_markers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScanLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_file_size_bytes: int
    max_recorded_paths_per_category: int
    max_tree_entries: int


class FileTreeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scanned_file_count: int = 0
    scanned_directory_count: int = 0
    ignored_file_count: int = 0
    ignored_directory_count: int = 0
    total_scanned_bytes: int = 0
    max_depth: int = 0
    sample_paths: list[str] = Field(default_factory=list)


class GitInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_git_repo: bool = False
    current_branch: str | None = None
    status_summary: str | None = None
    last_commit_subjects: list[str] = Field(default_factory=list)


class ScanCategories(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solution_files: list[str] = Field(default_factory=list)
    project_files: list[str] = Field(default_factory=list)
    readme_docs_files: list[str] = Field(default_factory=list)
    config_template_files: list[str] = Field(default_factory=list)
    migration_database_files: list[str] = Field(default_factory=list)
    test_projects_folders: list[str] = Field(default_factory=list)
    docker_files: list[str] = Field(default_factory=list)
    package_dependency_files: list[str] = Field(default_factory=list)


class ProjectScanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    project_path: Path
    scanned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    limits: ScanLimits
    file_tree: FileTreeSummary
    categories: ScanCategories
    git: GitInfo
    warnings: list[str] = Field(default_factory=list)


class AgentMode(StrEnum):
    PROMPT_ONLY = "prompt_only"


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    mode: AgentMode
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requires_approval: bool
    next_state: str | None = None


class AgentPromptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    project_name: str


class GeneratedPromptMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    project_name: str
    prompt_path: Path
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextStatus(StrEnum):
    REGISTERED = "REGISTERED"
    SCANNED = "SCANNED"
    CONTEXT_DRAFTED = "CONTEXT_DRAFTED"
    CONTEXT_REVIEWED = "CONTEXT_REVIEWED"
    CONTEXT_APPROVED = "CONTEXT_APPROVED"


class ImportedAgentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    source_file_path: Path
    imported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    artifact_path: Path


class ContextState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    project_path: Path
    status: ContextStatus = ContextStatus.REGISTERED
    discovery_artifact: ImportedAgentArtifact | None = None
    review_artifact: ImportedAgentArtifact | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_by: str
    discovery_artifact_path: Path
    review_artifact_path: Path
    approved_artifact_paths: list[Path] = Field(default_factory=list)


class RunStatus(StrEnum):
    RUN_CREATED = "RUN_CREATED"
    IDEA_ANALYSIS_DRAFTED = "IDEA_ANALYSIS_DRAFTED"
    REQUIREMENTS_DRAFTED = "REQUIREMENTS_DRAFTED"
    PLAN_DRAFTED = "PLAN_DRAFTED"
    PLAN_REVIEWED = "PLAN_REVIEWED"
    TASKS_DRAFTED = "TASKS_DRAFTED"
    IMPLEMENTATION_READY = "IMPLEMENTATION_READY"
    IMPLEMENTATION_REPORTED = "IMPLEMENTATION_REPORTED"
    VALIDATION_REVIEWED = "VALIDATION_REVIEWED"
    CODE_REVIEWED = "CODE_REVIEWED"
    FINAL_AUDITED = "FINAL_AUDITED"
    TASK_CLOSED = "TASK_CLOSED"
    RUN_CLOSED = "RUN_CLOSED"


class RunArtifactType(StrEnum):
    IDEA_ANALYSIS = "idea_analysis"
    REQUIREMENTS = "requirements"
    PLAN = "plan"
    PLAN_REVIEW = "plan_review"
    TASKS = "tasks"
    IMPLEMENTATION_BRIEF = "implementation_brief"
    VALIDATION_REPORT = "validation_report"
    CODE_REVIEW = "code_review"
    FINAL_AUDIT = "final_audit"


class TaskDispositionStatus(StrEnum):
    OPEN = "open"
    COVERED_BY = "covered_by"
    SUPERSEDED = "superseded"
    NOT_NEEDED = "not_needed"
    CLOSED_MANUALLY = "closed_manually"


class TaskLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    disposition_status: TaskDispositionStatus = TaskDispositionStatus.OPEN
    covered_by_task_id: str | None = None
    disposition_note: str | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    run_id: str
    entries: dict[str, TaskLedgerEntry] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: RunArtifactType
    agent_name: str
    source_file_path: Path
    artifact_path: Path
    imported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunAgentImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    run_id: str
    agent_name: str
    artifact: RunArtifact
    status_after_import: RunStatus


class ContextSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_state_path: Path
    approval_record_path: Path
    approved_artifact_paths: list[Path] = Field(default_factory=list)


class ImplementationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    agent_name: str
    source_file_path: Path
    implementation_brief_path: Path
    imported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completion_report_path: Path | None = None
    reported_at: datetime | None = None
    validation_summary: str = "unknown"
    commit_hash: str = "unknown"
    validation_report_path: Path | None = None
    validated_at: datetime | None = None
    validation_decision: str = "unknown"
    code_review_path: Path | None = None
    reviewed_at: datetime | None = None
    review_decision: str = "unknown"
    final_audit_path: Path | None = None
    audited_at: datetime | None = None
    final_decision: str = "unknown"
    closure_record_path: Path | None = None
    closed_at: datetime | None = None
    closure_status: str | None = None
    closure_note: str | None = None


class RunState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    project_path: Path
    run_id: str
    goal: str
    status: RunStatus = RunStatus.RUN_CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context_snapshot: ContextSnapshot
    artifacts: list[RunArtifact] = Field(default_factory=list)
    current_task_id: str | None = None
    implementation_brief_path: Path | None = None
    implementation_ready_at: datetime | None = None
    implementation_records: list[ImplementationRecord] = Field(default_factory=list)
    task_ledger_path: Path | None = None
    closed_at: datetime | None = None
    run_summary_path: Path | None = None
    closure_note: str | None = None


class CurrentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    project_path: Path
    run_id: str | None = None
    run_path: Path | None = None
    selected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_workspace_path: Path
    backup_path: Path
    label: str | None = None
    included_roots: list[str] = Field(default_factory=list)
    excluded_patterns: list[str] = Field(default_factory=list)
    file_count: int = 0
    total_bytes: int = 0
    sha256_by_file: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    tool_version: str = "unknown"
    git_commit_hash: str = "unknown"
    git_branch: str = "unknown"


class EnvironmentSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str
    project_path: Path
    project_git_branch: str | None = None
    project_git_commit: str | None = None
    project_git_status_summary: str | None = None
    operating_system: str
    python_version: str | None = None
    pip_version: str | None = None
    dotnet_info: str | None = None
    dotnet_sdks: list[str] = Field(default_factory=list)
    dotnet_runtimes: list[str] = Field(default_factory=list)
    git_version: str | None = None
    node_version: str | None = None
    npm_version: str | None = None
    dependency_files_found: list[str] = Field(default_factory=list)
    dependency_files_missing: list[str] = Field(default_factory=list)
    detected_project_files: list[str] = Field(default_factory=list)
    detected_solution_files: list[str] = Field(default_factory=list)
    detected_test_projects: list[str] = Field(default_factory=list)
    package_versions_summary: dict[str, list[str]] = Field(default_factory=dict)
    commands_detected: list[str] = Field(default_factory=list)
    recommended_commands: list[str] = Field(default_factory=list)
    excluded_heavy_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recovery_notes: list[str] = Field(default_factory=list)
