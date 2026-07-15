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


class RunArtifactType(StrEnum):
    IDEA_ANALYSIS = "idea_analysis"
    REQUIREMENTS = "requirements"
    PLAN = "plan"
    PLAN_REVIEW = "plan_review"
    TASKS = "tasks"


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


class CurrentSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: str
    project_path: Path
    run_id: str | None = None
    run_path: Path | None = None
    selected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
