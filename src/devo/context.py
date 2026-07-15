from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import ApprovalRecord, ContextState, ContextStatus, ImportedAgentArtifact

DISCOVERY_AGENT_NAME = "ProjectContextDiscoveryAgent"
REVIEWER_AGENT_NAME = "ProjectContextReviewerAgent"

DISCOVERY_DRAFT_NAME = "project-context-discovery.md"
REVIEW_ARTIFACT_NAME = "project-context-review.md"
APPROVAL_RECORD_NAME = "context-approval.json"
CONTEXT_STATE_NAME = "context-state.json"


def import_agent_output(
    agent_name: str,
    project_name: str,
    source_file: Path,
    workspace_root: Path | None = None,
) -> ImportedAgentArtifact:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    source_path = source_file.expanduser().resolve()
    if not source_path.exists():
        msg = f"Import file does not exist: {source_path}"
        raise ValueError(msg)
    if not source_path.is_file():
        msg = f"Import path must be a file: {source_path}"
        raise ValueError(msg)

    _ensure_context_dirs(project_name, workspace_root=root)
    state = load_context_state(project_name, workspace_root=root)

    if agent_name == DISCOVERY_AGENT_NAME:
        artifact_path = _context_root(root, project_name) / "drafts" / DISCOVERY_DRAFT_NAME
        status = ContextStatus.CONTEXT_DRAFTED
    elif agent_name == REVIEWER_AGENT_NAME:
        if not state.discovery_artifact or not state.discovery_artifact.artifact_path.exists():
            msg = "ProjectContextReviewerAgent import requires a discovery draft."
            raise ValueError(msg)
        artifact_path = _context_root(root, project_name) / "reviews" / REVIEW_ARTIFACT_NAME
        status = ContextStatus.CONTEXT_REVIEWED
    else:
        msg = f"Import is not supported for agent: {agent_name}"
        raise ValueError(msg)

    shutil.copyfile(source_path, artifact_path)
    artifact = ImportedAgentArtifact(
        agent_name=agent_name,
        source_file_path=source_path,
        artifact_path=artifact_path,
    )

    state.project_name = project_name
    state.project_path = registration.path
    state.status = status
    state.updated_at = datetime.now(UTC)
    if agent_name == DISCOVERY_AGENT_NAME:
        state.discovery_artifact = artifact
    else:
        state.review_artifact = artifact

    save_context_state(state, workspace_root=root)
    return artifact


def load_context_state(project_name: str, workspace_root: Path | None = None) -> ContextState:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    state_file = _context_state_file(root, project_name)
    if state_file.exists():
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return ContextState.model_validate(data)

    return ContextState(
        project_name=project_name,
        project_path=registration.path,
        status=_initial_context_status(root, project_name),
    )


def save_context_state(state: ContextState, workspace_root: Path | None = None) -> None:
    root = workspace_root or get_workspace_root()
    _ensure_context_dirs(state.project_name, workspace_root=root)
    state_file = _context_state_file(root, state.project_name)
    state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def get_context_status(project_name: str, workspace_root: Path | None = None) -> dict[str, str | bool | None]:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    state = load_context_state(project_name, workspace_root=root)
    approval_file = _approval_file(root, project_name)
    scan_file = root / "projects" / project_name / "scan-result.json"

    return {
        "project_name": project_name,
        "project_path": str(registration.path),
        "scan_status": "SCANNED" if scan_file.exists() else "NOT_SCANNED",
        "context_status": state.status.value,
        "discovery_artifact_path": str(state.discovery_artifact.artifact_path) if state.discovery_artifact else None,
        "review_artifact_path": str(state.review_artifact.artifact_path) if state.review_artifact else None,
        "approval_status": "APPROVED" if approval_file.exists() else None,
    }


def approve_context(project_name: str, workspace_root: Path | None = None) -> ApprovalRecord:
    root = workspace_root or get_workspace_root()
    state = load_context_state(project_name, workspace_root=root)
    if not state.discovery_artifact or not state.discovery_artifact.artifact_path.exists():
        msg = "Cannot approve context before importing ProjectContextDiscoveryAgent output."
        raise ValueError(msg)
    if not state.review_artifact or not state.review_artifact.artifact_path.exists():
        msg = "Cannot approve context before importing ProjectContextReviewerAgent output."
        raise ValueError(msg)

    _ensure_context_dirs(project_name, workspace_root=root)
    approved_dir = _context_root(root, project_name) / "approved"
    approved_discovery = approved_dir / DISCOVERY_DRAFT_NAME
    approved_review = approved_dir / REVIEW_ARTIFACT_NAME
    shutil.copyfile(state.discovery_artifact.artifact_path, approved_discovery)
    shutil.copyfile(state.review_artifact.artifact_path, approved_review)

    record = ApprovalRecord(
        project_name=project_name,
        approved_by="user",
        discovery_artifact_path=state.discovery_artifact.artifact_path,
        review_artifact_path=state.review_artifact.artifact_path,
        approved_artifact_paths=[approved_discovery, approved_review],
    )

    approval_file = _approval_file(root, project_name)
    approval_file.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    state.status = ContextStatus.CONTEXT_APPROVED
    state.approved_at = record.approved_at
    state.approved_by = record.approved_by
    state.updated_at = datetime.now(UTC)
    save_context_state(state, workspace_root=root)
    return record


def get_discovery_draft_text(project_name: str, workspace_root: Path | None = None) -> str:
    root = workspace_root or get_workspace_root()
    state = load_context_state(project_name, workspace_root=root)
    if not state.discovery_artifact or not state.discovery_artifact.artifact_path.exists():
        msg = "ProjectContextDiscoveryAgent draft output not found."
        raise ValueError(msg)
    text = state.discovery_artifact.artifact_path.read_text(encoding="utf-8")
    return text[:20_000]


def _initial_context_status(workspace_root: Path, project_name: str) -> ContextStatus:
    scan_file = workspace_root / "projects" / project_name / "scan-result.json"
    return ContextStatus.SCANNED if scan_file.exists() else ContextStatus.REGISTERED


def _ensure_context_dirs(project_name: str, workspace_root: Path) -> None:
    context_root = _context_root(workspace_root, project_name)
    for path in (
        context_root,
        context_root / "drafts",
        context_root / "reviews",
        context_root / "approved",
        workspace_root / "projects" / project_name / "approvals",
    ):
        path.mkdir(parents=True, exist_ok=True)


def _context_root(workspace_root: Path, project_name: str) -> Path:
    return workspace_root / "projects" / project_name / "context"


def _context_state_file(workspace_root: Path, project_name: str) -> Path:
    return _context_root(workspace_root, project_name) / CONTEXT_STATE_NAME


def _approval_file(workspace_root: Path, project_name: str) -> Path:
    return workspace_root / "projects" / project_name / "approvals" / APPROVAL_RECORD_NAME
