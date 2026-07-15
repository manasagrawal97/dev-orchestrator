from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

import yaml

from .context import get_discovery_draft_text
from .projects import get_workspace_root
from .scanner import load_registered_project
from .schemas import AgentDefinition, GeneratedPromptMetadata, ProjectScanResult

DISCOVERY_AGENT_NAME = "ProjectContextDiscoveryAgent"
REVIEWER_AGENT_NAME = "ProjectContextReviewerAgent"
DISCOVERY_TEMPLATE_NAME = "project_context_discovery.md"
REVIEWER_TEMPLATE_NAME = "project_context_reviewer.md"
MAX_CATEGORY_PATHS = 20
MAX_SAMPLE_PATHS = 40
MAX_WARNINGS = 10
MAX_COMMITS = 10


def list_agent_definitions(agents_dir: Path | None = None) -> list[AgentDefinition]:
    root = agents_dir or _agents_dir()
    if not root.exists():
        return []

    agents = [load_agent_definition(path.stem, agents_dir=root) for path in sorted(root.glob("*.yaml"))]
    return sorted(agents, key=lambda agent: agent.name)


def load_agent_definition(agent_name: str, agents_dir: Path | None = None) -> AgentDefinition:
    root = agents_dir or _agents_dir()
    agent_file = root / f"{agent_name}.yaml"
    if not agent_file.exists():
        msg = f"Unknown agent: {agent_name}"
        raise ValueError(msg)

    data = yaml.safe_load(agent_file.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        msg = f"Agent definition must be a YAML mapping: {agent_file}"
        raise ValueError(msg)
    return AgentDefinition.model_validate(data)


def render_agent_definition(agent: AgentDefinition) -> str:
    return yaml.safe_dump(agent.model_dump(mode="json"), sort_keys=False)


def generate_project_context_discovery_prompt(
    project_name: str,
    workspace_root: Path | None = None,
    agents_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> GeneratedPromptMetadata:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    scan_result = _load_scan_result(project_name, workspace_root=root)
    agent = load_agent_definition(DISCOVERY_AGENT_NAME, agents_dir=agents_dir)
    template_text = _load_prompt_template(DISCOVERY_TEMPLATE_NAME, prompts_dir=prompts_dir)

    prompt = _render_project_context_prompt(
        template_text=template_text,
        agent=agent,
        project_name=project_name,
        project_path=str(registration.path),
        scan_result=scan_result,
    )

    output_file = root / "projects" / project_name / "prompts" / "project-context-discovery.prompt.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(prompt, encoding="utf-8")
    return GeneratedPromptMetadata(
        agent_name=agent.name,
        project_name=project_name,
        prompt_path=output_file,
    )


def generate_project_context_reviewer_prompt(
    project_name: str,
    workspace_root: Path | None = None,
    agents_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> GeneratedPromptMetadata:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    scan_result = _load_scan_result(project_name, workspace_root=root)
    discovery_draft = get_discovery_draft_text(project_name, workspace_root=root)
    agent = load_agent_definition(REVIEWER_AGENT_NAME, agents_dir=agents_dir)
    template_text = _load_prompt_template(REVIEWER_TEMPLATE_NAME, prompts_dir=prompts_dir)

    prompt = _render_project_context_reviewer_prompt(
        template_text=template_text,
        agent=agent,
        project_name=project_name,
        project_path=str(registration.path),
        scan_result=scan_result,
        discovery_draft=discovery_draft,
    )

    output_file = root / "projects" / project_name / "prompts" / "project-context-reviewer.prompt.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(prompt, encoding="utf-8")
    return GeneratedPromptMetadata(
        agent_name=agent.name,
        project_name=project_name,
        prompt_path=output_file,
    )


def _load_scan_result(project_name: str, workspace_root: Path) -> ProjectScanResult:
    scan_file = workspace_root / "projects" / project_name / "scan-result.json"
    if not scan_file.exists():
        msg = f"scan-result.json not found for project: {project_name}"
        raise ValueError(msg)

    data = json.loads(scan_file.read_text(encoding="utf-8"))
    return ProjectScanResult.model_validate(data)


def _load_prompt_template(template_name: str, prompts_dir: Path | None = None) -> str:
    root = prompts_dir or _prompts_dir()
    template_file = root / template_name
    if not template_file.exists():
        msg = f"Prompt template not found: {template_name}"
        raise ValueError(msg)
    return template_file.read_text(encoding="utf-8")


def _render_project_context_prompt(
    template_text: str,
    agent: AgentDefinition,
    project_name: str,
    project_path: str,
    scan_result: ProjectScanResult,
) -> str:
    summary = _build_scan_summary(scan_result)
    template = Template(template_text)
    return template.safe_substitute(
        agent_name=agent.name,
        agent_version=agent.version,
        agent_purpose=agent.purpose,
        project_name=project_name,
        project_path=project_path,
        scan_summary=json.dumps(summary, indent=2, default=str),
        allowed_actions=_markdown_list(agent.allowed_actions),
        forbidden_actions=_markdown_list(agent.forbidden_actions),
        expected_outputs=_markdown_list(agent.outputs),
    )


def _render_project_context_reviewer_prompt(
    template_text: str,
    agent: AgentDefinition,
    project_name: str,
    project_path: str,
    scan_result: ProjectScanResult,
    discovery_draft: str,
) -> str:
    summary = _build_scan_summary(scan_result)
    template = Template(template_text)
    return template.safe_substitute(
        agent_name=agent.name,
        agent_version=agent.version,
        agent_purpose=agent.purpose,
        project_name=project_name,
        project_path=project_path,
        scan_summary=json.dumps(summary, indent=2, default=str),
        discovery_draft=discovery_draft,
        allowed_actions=_markdown_list(agent.allowed_actions),
        forbidden_actions=_markdown_list(agent.forbidden_actions),
        expected_outputs=_markdown_list(agent.outputs),
    )


def _build_scan_summary(scan_result: ProjectScanResult) -> dict[str, Any]:
    categories = scan_result.categories.model_dump(mode="json")
    detected_categories = {
        name: paths[:MAX_CATEGORY_PATHS]
        for name, paths in categories.items()
        if paths
    }
    category_counts = {
        name: len(paths)
        for name, paths in categories.items()
    }

    return {
        "project_name": scan_result.project_name,
        "project_path": str(scan_result.project_path),
        "scanned_at": scan_result.scanned_at.isoformat(),
        "file_tree_counts": {
            "scanned_file_count": scan_result.file_tree.scanned_file_count,
            "scanned_directory_count": scan_result.file_tree.scanned_directory_count,
            "ignored_file_count": scan_result.file_tree.ignored_file_count,
            "ignored_directory_count": scan_result.file_tree.ignored_directory_count,
            "total_scanned_bytes": scan_result.file_tree.total_scanned_bytes,
            "max_depth": scan_result.file_tree.max_depth,
        },
        "detected_categories": detected_categories,
        "category_counts": category_counts,
        "git": {
            "is_git_repo": scan_result.git.is_git_repo,
            "current_branch": scan_result.git.current_branch,
            "status_summary": scan_result.git.status_summary,
            "last_commit_subjects": scan_result.git.last_commit_subjects[:MAX_COMMITS],
        },
        "warnings": scan_result.warnings[:MAX_WARNINGS],
        "sample_paths": scan_result.file_tree.sample_paths[:MAX_SAMPLE_PATHS],
    }


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- none"
    return "\n".join(f"- {item}" for item in items)


def _agents_dir() -> Path:
    return _repo_root() / "agents"


def _prompts_dir() -> Path:
    return _repo_root() / "prompts"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
