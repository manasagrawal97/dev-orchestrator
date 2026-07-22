from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .projects import get_workspace_root
from .runs import run_path
from .scanner import load_registered_project
from .work_history import WorkPackageSummary, list_work_package_summaries
from .work_packages import WorkPackage, WorkPackageStatus, load_work_package


class VisualReportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    markdown: str


def generate_work_package_visual(
    project_name: str,
    run_id: str,
    workspace_root: Path | None = None,
) -> VisualReportResult:
    root = workspace_root or get_workspace_root()
    package = load_work_package(project_name, run_id, workspace_root=root)
    summary = next(
        (item for item in list_work_package_summaries(project_name, limit=100, workspace_root=root) if item.run_id == run_id),
        None,
    )
    markdown = render_work_package_visual(package, summary)
    path = run_path(project_name, run_id, workspace_root=root) / "artifacts" / "visuals" / "work-package-flow.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return VisualReportResult(path=path, markdown=markdown)


def generate_project_activity_visual(
    project_name: str,
    limit: int = 10,
    workspace_root: Path | None = None,
) -> VisualReportResult:
    root = workspace_root or get_workspace_root()
    load_registered_project(project_name, workspace_root=root)
    safe_limit = max(1, min(limit, 25))
    summaries = list_work_package_summaries(project_name, limit=safe_limit, workspace_root=root)
    markdown = render_project_activity_visual(project_name, summaries, safe_limit)
    path = root / "projects" / project_name / "visuals" / "project-activity.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return VisualReportResult(path=path, markdown=markdown)


def render_work_package_visual(package: WorkPackage, summary: WorkPackageSummary | None = None) -> str:
    status = package.status.value
    active_node = _status_node(package.status)
    approval_status = _first_value(package.approval_bundle_status, summary.approval_bundle_status if summary else None)
    validation_status = _first_value(package.validation_status, summary.latest_validation_status if summary else None)
    commit_hash = _first_value(package.commit_hash, summary.commit_hash if summary else None)
    lines = [
        f"# Work Package Visual: {package.goal}",
        "",
        "Generated from Devo work-package and validation artifacts. This is a live workspace artifact, not committed documentation.",
        "",
        f"- project: {package.project}",
        f"- run_id: {package.run_id}",
        f"- current_status: {status}",
        f"- approval_bundle_status: {approval_status}",
        f"- latest_validation_status: {validation_status}",
        f"- delivered_commit: {commit_hash}",
        "",
        "```mermaid",
        "flowchart LR",
        '    start["work start"] --> scope["scope imported"]',
        '    scope --> bundle["approval bundle"]',
        '    bundle --> approved["approved"]',
        '    approved --> implemented["implemented"]',
        '    implemented --> validated["validated"]',
        '    validated --> delivered["delivered"]',
        '    delivered --> completed["completed"]',
        '    classDef current fill:#fff3bf,stroke:#b08900,stroke-width:2px,color:#1f2937',
        f"    class {active_node} current",
        "```",
        "",
    ]
    return "\n".join(lines)


def render_project_activity_visual(project_name: str, summaries: list[WorkPackageSummary], limit: int) -> str:
    lines = [
        f"# Project Activity Visual: {project_name}",
        "",
        "Generated from Devo run and work-package artifacts. This is a live workspace artifact, not committed documentation.",
        "",
        f"- item_limit: {limit}",
        f"- items_rendered: {len(summaries)}",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    if not summaries:
        lines.append('    empty["No recent runs found"]')
    else:
        for index, summary in enumerate(summaries):
            lines.append(f'    item{index}["{_activity_label(summary)}"]')
        for index in range(len(summaries) - 1):
            lines.append(f"    item{index} --> item{index + 1}")
    lines.extend(["```", ""])
    return "\n".join(lines)


def _status_node(status: WorkPackageStatus) -> str:
    mapping = {
        WorkPackageStatus.DRAFT: "start",
        WorkPackageStatus.SCOPE_PROPOSED: "scope",
        WorkPackageStatus.APPROVAL_REQUESTED: "bundle",
        WorkPackageStatus.APPROVED: "approved",
        WorkPackageStatus.IMPLEMENTED: "implemented",
        WorkPackageStatus.VALIDATED: "validated",
        WorkPackageStatus.DELIVERED: "delivered",
        WorkPackageStatus.CLOSED: "completed",
    }
    return mapping.get(status, "start")


def _activity_label(summary: WorkPackageSummary) -> str:
    commit = summary.commit_hash[:12] if summary.commit_hash else "none"
    label = f"{summary.goal}\\nstatus: {summary.status}\\ncommit: {commit}"
    return _mermaid_label(label)


def _mermaid_label(value: str) -> str:
    return value.replace('"', "'").replace("\r", " ").replace("\n", "\\n")


def _first_value(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return "not available"
