from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any

import yaml

from .context import get_discovery_draft_text
from .projects import get_workspace_root
from .runs import (
    IDEA_ANALYST_AGENT_NAME,
    IMPLEMENTATION_COORDINATOR_AGENT_NAME,
    PLANNER_AGENT_NAME,
    PLAN_REVIEWER_AGENT_NAME,
    REQUIREMENTS_AGENT_NAME,
    TASK_DECOMPOSER_AGENT_NAME,
    extract_task_excerpt,
    get_run_artifact_text,
    load_run,
    require_context_approved,
    require_run_artifact,
    require_run_status_at_least,
    require_task_id,
    run_path,
)
from .scanner import load_registered_project
from .schemas import AgentDefinition, GeneratedPromptMetadata, ProjectScanResult, RunArtifactType, RunState, RunStatus

DISCOVERY_AGENT_NAME = "ProjectContextDiscoveryAgent"
REVIEWER_AGENT_NAME = "ProjectContextReviewerAgent"
DISCOVERY_TEMPLATE_NAME = "project_context_discovery.md"
REVIEWER_TEMPLATE_NAME = "project_context_reviewer.md"
IDEA_ANALYST_TEMPLATE_NAME = "idea_analyst.md"
REQUIREMENTS_TEMPLATE_NAME = "requirements_agent.md"
PLANNER_TEMPLATE_NAME = "planner.md"
PLAN_REVIEWER_TEMPLATE_NAME = "plan_reviewer.md"
TASK_DECOMPOSER_TEMPLATE_NAME = "task_decomposer.md"
IMPLEMENTATION_COORDINATOR_TEMPLATE_NAME = "implementation_coordinator.md"
MAX_CATEGORY_PATHS = 20
MAX_SAMPLE_PATHS = 40
MAX_WARNINGS = 10
MAX_COMMITS = 10
MAX_CONTEXT_ARTIFACT_CHARS = 12_000


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


def generate_run_agent_prompt(
    agent_name: str,
    project_name: str,
    run_id: str,
    task_id: str | None = None,
    workspace_root: Path | None = None,
    agents_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> GeneratedPromptMetadata:
    root = workspace_root or get_workspace_root()
    registration = load_registered_project(project_name, workspace_root=root)
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    agent = load_agent_definition(agent_name, agents_dir=agents_dir)

    if agent.name == IDEA_ANALYST_AGENT_NAME:
        template_name = IDEA_ANALYST_TEMPLATE_NAME
        output_name = "idea-analyst.prompt.md"
    elif agent.name == REQUIREMENTS_AGENT_NAME:
        template_name = REQUIREMENTS_TEMPLATE_NAME
        output_name = "requirements-agent.prompt.md"
    elif agent.name == PLANNER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.REQUIREMENTS_DRAFTED,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.REQUIREMENTS,
            "PlannerAgent requires RequirementsAgent output before planning.",
        )
        template_name = PLANNER_TEMPLATE_NAME
        output_name = "planner.prompt.md"
    elif agent.name == PLAN_REVIEWER_AGENT_NAME:
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "PlanReviewerAgent requires PlannerAgent output before review.",
        )
        template_name = PLAN_REVIEWER_TEMPLATE_NAME
        output_name = "plan-reviewer.prompt.md"
    elif agent.name == TASK_DECOMPOSER_AGENT_NAME:
        require_run_status_at_least(
            run_state,
            RunStatus.PLAN_REVIEWED,
            "TaskDecomposerAgent requires a reviewed plan before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN,
            "TaskDecomposerAgent requires PlannerAgent output before task decomposition.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.PLAN_REVIEW,
            "TaskDecomposerAgent requires PlanReviewerAgent output before task decomposition.",
        )
        template_name = TASK_DECOMPOSER_TEMPLATE_NAME
        output_name = "task-decomposer.prompt.md"
    elif agent.name == IMPLEMENTATION_COORDINATOR_AGENT_NAME:
        normalized_task_id = require_task_id(task_id)
        require_run_status_at_least(
            run_state,
            RunStatus.TASKS_DRAFTED,
            "ImplementationCoordinatorAgent requires drafted tasks before implementation coordination.",
        )
        require_run_artifact(
            run_state,
            RunArtifactType.TASKS,
            "ImplementationCoordinatorAgent requires TaskDecomposerAgent output before implementation coordination.",
        )
        tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS)
        task_excerpt = extract_task_excerpt(tasks_text or "", normalized_task_id)
        if not task_excerpt:
            msg = f"Task id not found in tasks.md: {normalized_task_id}"
            raise ValueError(msg)
        template_name = IMPLEMENTATION_COORDINATOR_TEMPLATE_NAME
        output_name = f"implementation-coordinator-{normalized_task_id}.prompt.md"
    else:
        msg = f"Run-level prompt generation is not supported for agent: {agent_name}"
        raise ValueError(msg)

    template_text = _load_prompt_template(template_name, prompts_dir=prompts_dir)
    prompt = _render_run_agent_prompt(
        template_text=template_text,
        agent=agent,
        project_path=str(registration.path),
        run_state=run_state,
        selected_task_id=task_id,
    )

    output_file = run_path(project_name, run_id, workspace_root=root) / "prompts" / output_name
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


def _render_run_agent_prompt(
    template_text: str,
    agent: AgentDefinition,
    project_path: str,
    run_state: RunState,
    selected_task_id: str | None = None,
) -> str:
    template = Template(template_text)
    idea_analysis = get_run_artifact_text(run_state, RunArtifactType.IDEA_ANALYSIS)
    idea_analysis_status = "available" if idea_analysis else "missing"
    requirements = get_run_artifact_text(run_state, RunArtifactType.REQUIREMENTS)
    requirements_status = "available" if requirements else "missing"
    plan = get_run_artifact_text(run_state, RunArtifactType.PLAN)
    plan_status = "available" if plan else "missing"
    plan_review = get_run_artifact_text(run_state, RunArtifactType.PLAN_REVIEW)
    plan_review_status = "available" if plan_review else "missing"
    tasks = get_run_artifact_text(run_state, RunArtifactType.TASKS)
    tasks_status = "available" if tasks else "missing"
    normalized_task_id = (selected_task_id or "").strip()
    selected_task_excerpt = extract_task_excerpt(tasks or "", normalized_task_id) if normalized_task_id else None
    return template.safe_substitute(
        agent_name=agent.name,
        agent_version=agent.version,
        agent_purpose=agent.purpose,
        project_name=run_state.project_name,
        project_path=project_path,
        run_id=run_state.run_id,
        run_status=run_state.status.value,
        goal=run_state.goal,
        goal_markdown=_read_run_file(run_state, "goal.md"),
        run_state_summary=json.dumps(_build_run_state_summary(run_state), indent=2, default=str),
        approved_context=_build_approved_context_text(run_state),
        idea_analysis_status=idea_analysis_status,
        idea_analysis=idea_analysis or "MISSING: IdeaAnalystAgent output has not been imported yet.",
        requirements_status=requirements_status,
        requirements=requirements or "MISSING: RequirementsAgent output has not been imported yet.",
        plan_status=plan_status,
        plan=plan or "MISSING: PlannerAgent output has not been imported yet.",
        plan_review_status=plan_review_status,
        plan_review=plan_review or "MISSING: PlanReviewerAgent output has not been imported yet.",
        tasks_status=tasks_status,
        tasks=tasks or "MISSING: TaskDecomposerAgent output has not been imported yet.",
        selected_task_id=normalized_task_id or "MISSING: no task id was provided.",
        selected_task_excerpt=selected_task_excerpt or "MISSING: selected task was not found in tasks.md.",
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


def _build_run_state_summary(run_state: RunState) -> dict[str, Any]:
    return {
        "project_name": run_state.project_name,
        "project_path": str(run_state.project_path),
        "run_id": run_state.run_id,
        "goal": run_state.goal,
        "status": run_state.status.value,
        "created_at": run_state.created_at.isoformat(),
        "updated_at": run_state.updated_at.isoformat(),
        "context_snapshot": run_state.context_snapshot.model_dump(mode="json"),
        "artifacts": [artifact.model_dump(mode="json") for artifact in run_state.artifacts],
    }


def _build_approved_context_text(run_state: RunState) -> str:
    sections: list[str] = []
    for artifact_path in run_state.context_snapshot.approved_artifact_paths:
        if not artifact_path.exists():
            sections.append(f"## Missing approved context artifact\n\n{artifact_path}")
            continue
        text = artifact_path.read_text(encoding="utf-8")[:MAX_CONTEXT_ARTIFACT_CHARS]
        sections.append(f"## {artifact_path.name}\n\n{text}")
    if not sections:
        return "No approved context artifacts were listed in the context snapshot."
    return "\n\n---\n\n".join(sections)


def _read_run_file(run_state: RunState, file_name: str) -> str:
    path = run_path(run_state.project_name, run_state.run_id) / file_name
    if not path.exists():
        return f"MISSING: {file_name}"
    return path.read_text(encoding="utf-8")


def _agents_dir() -> Path:
    return _repo_root() / "agents"


def _prompts_dir() -> Path:
    return _repo_root() / "prompts"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
