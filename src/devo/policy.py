from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .projects import get_workspace_root
from .runs import (
    IMPLEMENTATION_COORDINATOR_AGENT_NAME,
    extract_task_excerpt,
    get_run_artifact_text,
    list_run_tasks,
    load_run,
    require_context_approved,
)
from .schemas import RunArtifactType

RISK_LEVELS = ("low", "medium", "high", "critical")
RISK_RANK = {level: index for index, level in enumerate(RISK_LEVELS)}
ACTION_TYPES = {
    "plan",
    "implementation_prompt",
    "implementation",
    "validation",
    "target_command",
    "target_repo_docs_edit",
    "target_repo_code_edit",
    "target_repo_config_edit",
    "target_repo_validation",
    "target_repo_build",
    "target_repo_test",
    "target_repo_run",
    "target_repo_migration",
    "target_repo_database",
    "target_repo_script",
    "git_commit",
    "git_push",
    "backup",
    "restore",
    "scheduler",
    "cleanup",
    "unknown",
}


@dataclass
class PolicyClassification:
    project_name: str
    run_id: str
    task_id: str
    task_title: str
    risk_level: str
    approval_required: bool
    blocked: bool
    reasons: list[str] = field(default_factory=list)
    matched_risk_signals: list[str] = field(default_factory=list)
    safety_exclusion_signals: list[str] = field(default_factory=list)
    safe_action_categories: list[str] = field(default_factory=list)
    unsafe_action_categories: list[str] = field(default_factory=list)
    recommended_next_command: str | None = None
    closure_status: str = "open"
    disposition_status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyCheckResult:
    project_name: str
    run_id: str
    task_id: str
    task_title: str
    action_type: str
    allowed: bool
    approval_required: bool
    blocked: bool
    risk_level: str
    reasons: list[str] = field(default_factory=list)
    matched_risk_signals: list[str] = field(default_factory=list)
    safety_exclusion_signals: list[str] = field(default_factory=list)
    required_approval_note: str | None = None
    suggested_safer_alternative: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyStatus:
    project_name: str
    run_id: str
    tasks: list[PolicyClassification]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_task(
    project_name: str,
    run_id: str,
    task_id: str,
    workspace_root: Path | None = None,
) -> PolicyClassification:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    run_state = load_run(project_name, run_id, workspace_root=root)
    task = _require_task(project_name, run_id, task_id, workspace_root=root)
    tasks_text = get_run_artifact_text(run_state, RunArtifactType.TASKS) or ""
    excerpt = extract_task_excerpt(tasks_text, task_id)
    if not excerpt:
        msg = f"Task id not found in tasks.md: {task_id}"
        raise ValueError(msg)

    task_title = str(task.get("task_title") or "unknown")
    evidence_text = _normalize_text(
        " ".join(
            [
                task_id,
                task_title,
                excerpt,
                str(task.get("disposition_status") or ""),
                str(task.get("disposition_note") or ""),
            ]
        )
    )
    evaluation = _evaluate_text(evidence_text)
    risk_level = evaluation["risk_level"]
    reasons = list(evaluation["reasons"])

    if not evaluation["matched_risk_signals"]:
        risk_level = _max_risk(risk_level, "medium")
        reasons.append("No clear low-risk evidence was found; treating task risk as medium.")

    approval_required = risk_level in {"high", "critical"}
    blocked = risk_level == "critical"
    if risk_level == "medium":
        reasons.append("Medium risk is allowed but approval is recommended.")
    if risk_level == "high":
        reasons.append("High risk requires explicit approval before proceeding.")
    if risk_level == "critical":
        reasons.append("Critical risk is blocked until a future approval/override workflow exists.")

    return PolicyClassification(
        project_name=project_name,
        run_id=run_id,
        task_id=task_id,
        task_title=task_title,
        risk_level=risk_level,
        approval_required=approval_required,
        blocked=blocked,
        reasons=_dedupe(reasons),
        matched_risk_signals=evaluation["matched_risk_signals"],
        safety_exclusion_signals=evaluation["safety_exclusion_signals"],
        safe_action_categories=evaluation["safe_action_categories"],
        unsafe_action_categories=evaluation["unsafe_action_categories"],
        recommended_next_command=_recommended_command(project_name, run_id, task_id, risk_level),
        closure_status=str(task.get("closure_status") or "open"),
        disposition_status=str(task.get("disposition_status") or "open"),
    )


def check_policy(
    project_name: str,
    run_id: str,
    task_id: str,
    action_type: str = "unknown",
    workspace_root: Path | None = None,
) -> PolicyCheckResult:
    normalized_action = _normalize_action_type(action_type)
    classification = classify_task(project_name, run_id, task_id, workspace_root=workspace_root)
    action_evaluation = _evaluate_action(normalized_action)
    risk_level = _max_risk(classification.risk_level, action_evaluation["risk_level"])
    reasons = [*classification.reasons, *action_evaluation["reasons"]]
    matched = [*classification.matched_risk_signals, *action_evaluation["matched_risk_signals"]]
    safety_exclusions = [
        *classification.safety_exclusion_signals,
        *action_evaluation.get("safety_exclusion_signals", []),
    ]
    approval_required = risk_level in {"high", "critical"}
    blocked = risk_level == "critical"
    allowed = not blocked and not approval_required
    if approval_required and not blocked:
        reasons.append("Policy approval is required before this action can proceed.")
    if blocked:
        reasons.append("This action is blocked by current policy.")

    return PolicyCheckResult(
        project_name=project_name,
        run_id=run_id,
        task_id=task_id,
        task_title=classification.task_title,
        action_type=normalized_action,
        allowed=allowed,
        approval_required=approval_required,
        blocked=blocked,
        risk_level=risk_level,
        reasons=_dedupe(reasons),
        matched_risk_signals=_dedupe(matched),
        safety_exclusion_signals=_dedupe(safety_exclusions),
        required_approval_note=(
            f"Approval required for {risk_level} risk {normalized_action} on task {task_id}."
            if approval_required
            else None
        ),
        suggested_safer_alternative=_safer_alternative(normalized_action, risk_level),
    )


def get_policy_status(project_name: str, run_id: str, workspace_root: Path | None = None) -> PolicyStatus:
    root = workspace_root or get_workspace_root()
    require_context_approved(project_name, workspace_root=root)
    tasks = list_run_tasks(project_name, run_id, workspace_root=root)
    classifications = [
        classify_task(project_name, run_id, str(task["task_id"]), workspace_root=root)
        for task in tasks
    ]
    return PolicyStatus(project_name=project_name, run_id=run_id, tasks=classifications)


def _require_task(project_name: str, run_id: str, task_id: str, workspace_root: Path) -> dict[str, object]:
    tasks = list_run_tasks(project_name, run_id, workspace_root=workspace_root)
    for task in tasks:
        if task.get("task_id") == task_id:
            return task
    msg = f"Task id not found in tasks.md: {task_id}"
    raise ValueError(msg)


def _evaluate_text(text: str) -> dict[str, Any]:
    risk_level = "low"
    reasons: list[str] = []
    matched: list[str] = []
    safety_exclusions: list[str] = []
    safe: list[str] = []
    unsafe: list[str] = []
    risk_text, exclusion_texts = _split_risk_and_exclusion_text(text)

    for exclusion_text in exclusion_texts:
        safety_exclusions.extend(_safety_exclusion_signals(exclusion_text))

    for level, signal, pattern, category, reason in _risk_rules():
        if re.search(pattern, risk_text):
            risk_level = _max_risk(risk_level, level)
            matched.append(signal)
            reasons.append(reason)
            if level == "low":
                safe.append(category)
            else:
                unsafe.append(category)

    explicit = _explicit_risk(risk_text)
    if explicit:
        risk_level = _max_risk(risk_level, explicit)
        matched.append(f"explicit risk: {explicit}")
        reasons.append(f"Task text declares risk level {explicit}.")

    if matched and all(signal.startswith(("read-only", "docs", "prompt", "report", "status", "test temp", "readme")) for signal in matched):
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "reasons": _dedupe(reasons),
        "matched_risk_signals": _dedupe(matched),
        "safety_exclusion_signals": _dedupe(safety_exclusions),
        "safe_action_categories": _dedupe(safe),
        "unsafe_action_categories": _dedupe(unsafe),
    }


def _evaluate_action(action_type: str) -> dict[str, Any]:
    action_risks = {
        "plan": ("low", "planning action", "planning", "Planning is non-mutating."),
        "implementation_prompt": ("low", "implementation prompt", "prompt_generation", "Prompt generation is non-mutating."),
        "implementation": ("medium", "implementation action", "local_mutation", "Implementation may modify files and needs evidence."),
        "validation": ("low", "validation review", "review", "Validation review is non-mutating when it only reviews evidence."),
        "target_command": ("high", "target command", "target_command", "Target project commands require approval."),
        "target_repo_docs_edit": ("medium", "target repo docs edit", "target_repo_docs", "Docs-only target repository edits are medium risk and should stay path-scoped."),
        "target_repo_code_edit": ("high", "target repo code edit", "target_project_mutation", "Target repository code edits are high risk."),
        "target_repo_config_edit": ("high", "target repo config edit", "target_config", "Target repository configuration edits are high risk."),
        "target_repo_validation": ("high", "target repo validation", "target_command", "Target project validation commands are high risk by default."),
        "target_repo_build": ("high", "target repo build", "target_command", "Target project build commands are high risk by default."),
        "target_repo_test": ("high", "target repo test", "target_command", "Target project test commands are high risk by default."),
        "target_repo_run": ("high", "target repo run", "target_command", "Target project run commands are high risk by default."),
        "target_repo_migration": ("high", "target repo migration", "database", "Target project migration work is high risk."),
        "target_repo_database": ("high", "target repo database", "database", "Target project database work is high risk."),
        "target_repo_script": ("high", "target repo script", "target_command", "Target project scripts are high risk by default."),
        "git_commit": ("medium", "git commit", "git", "Local commits are medium risk."),
        "git_push": ("high", "git push", "git", "Git push is high risk because it changes a remote."),
        "backup": ("high", "backup/export", "external_write", "Backups may write outside the local workspace."),
        "restore": ("high", "restore", "restore", "Restore can overwrite or create workspace state."),
        "scheduler": ("high", "scheduler", "scheduler", "Scheduled task changes affect machine state."),
        "cleanup": ("high", "cleanup/delete", "cleanup", "Cleanup can delete files and requires approval."),
        "unknown": ("medium", "unknown action", "unknown", "Unknown action type is treated conservatively."),
    }
    level, signal, category, reason = action_risks[action_type]
    return {
        "risk_level": level,
        "reasons": [reason],
        "matched_risk_signals": [signal],
        "safety_exclusion_signals": [],
        "unsafe_action_categories": [] if level == "low" else [category],
    }


def _risk_rules() -> list[tuple[str, str, str, str, str]]:
    return [
        ("critical", "broad recursive delete", r"\b(rm\s+-rf|remove-item\s+.*-recurse|broad recursive delete|delete unknown folders?)\b", "destructive", "Broad or unknown-scope delete operation detected."),
        ("critical", "secrets exposure", r"\b(copying? secrets?|expos(?:e|ing) secrets?|committing secrets?|credentials?|tokens?)\b", "secrets", "Secret or credential handling detected."),
        ("critical", "production database", r"\b(update|modify|change|write|apply|migrate|run|execute)\b.{0,80}\bproduction database\b|\bproduction database\b.{0,80}\b(update|modify|change|write|apply|migrate|run|execute)\b", "production_data", "Production database modification risk detected."),
        ("critical", "approval bypass", r"\b(bypass(?:ing)? approval|force cleanup of invalid folders?|force-push|force push)\b", "policy_bypass", "Approval bypass or force operation detected."),
        ("high", "target project modification", r"\b(target project source modification|modify(?:ing)? target project|target repo modification|app code change|modify personalos repo)\b", "target_project_mutation", "Target project modification is high risk."),
        ("high", "target build/test/restore", r"\b(target project build|target project test|target project restore|build/test/restore|package restore|dotnet restore|dotnet build|dotnet test|run restore|run build|run test)\b", "target_command", "Target project command execution is high risk."),
        ("high", "database or migration", r"\b(database|dbcontext|migration|migrations|ef migration|dotnet ef database update|appdata)\b", "database", "Database, app data, or migration work is high risk."),
        ("high", "service control", r"\b(start/stop services?|start service|stop service|run start\.bat|run stop\.bat|start\.bat|stop\.bat|scheduler|scheduled task)\b", "service_or_scheduler", "Service or scheduler operations are high risk."),
        ("high", "backup restore or cleanup", r"\b(backup restore|restore backup|cleanup|delete operation)\b", "restore_or_cleanup", "Restore or cleanup operation is high risk."),
        ("high", "git push", r"\b(git push|push to github|pushed? to main)\b", "git_remote", "Git push changes remote state and is high risk."),
        ("high", "external folder write", r"\b(google drive|external folder|external write|outside workspace)\b", "external_write", "External folder writes are high risk."),
        ("high", "shell profile or environment config", r"\b(shell profile|environment configuration|machine configuration|path configuration)\b", "machine_config", "Machine or shell configuration is high risk."),
        ("medium", "devorchestrator source edit", r"\b(source code edit|edit source|modify devorchestrator|src/devo|tests/test_|local code change)\b", "source_edit", "Local DevOrchestrator source edits are medium risk."),
        ("medium", "temp test files", r"\b(temp files?|temporary files?|pytest|tests creating local temp)\b", "local_temp_files", "Tests or temporary local files are medium risk."),
        ("medium", "local commit", r"\b(git commit|local commit|commit hash)\b", "git_local", "Local commits are medium risk."),
        ("medium", "ledger or workspace mutation", r"\b(task closure|ledger mutation|workspace artifact writes?|generated artifacts?|local generated reports?)\b", "workspace_mutation", "Workspace artifact or ledger mutation is medium risk."),
        ("low", "read-only inspection", r"\b(read-only|inspect|inventory|discover|extract|classify|summarize|summary)\b", "read_only", "Read-only inspection or summarization detected."),
        ("low", "docs-only", r"\b(docs-only|documentation|readme|claude\.md|docs/)\b", "documentation", "Documentation-focused work detected."),
        ("low", "prompt generation", r"\b(prompt generation|generate prompt|agent prompt)\b", "prompt_generation", "Prompt generation is non-mutating."),
        ("low", "report generation", r"\b(report generation|status display|run status|task status|workflow status|workflow next|workflow batch)\b", "reporting", "Status/report workflow detected."),
        ("low", "test temp dirs", r"\b(tests? against temp dirs?|basetemp)\b", "temp_tests", "Tests constrained to temp directories detected."),
        ("low", "readme update", r"\breadme updates?\b", "documentation", "README update detected."),
    ]


def _split_risk_and_exclusion_text(text: str) -> tuple[str, list[str]]:
    risk_chunks: list[str] = []
    exclusion_chunks: list[str] = []
    for chunk in _iter_policy_chunks(text):
        if _is_safety_exclusion_chunk(chunk):
            exclusion_chunks.append(chunk)
        else:
            risk_chunks.append(chunk)
    return " ".join(risk_chunks), exclusion_chunks


def _iter_policy_chunks(text: str) -> list[str]:
    chunks = re.split(r"(?:[.;]|\s+-\s+|\n)+", text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _is_safety_exclusion_chunk(chunk: str) -> bool:
    return bool(
        re.search(
            r"\b("
            r"no|do not|don't|dont|without|excluded|excludes|forbidden|not allowed|"
            r"out[- ]of[- ]scope|out of scope|prohibited|avoid"
            r")\b",
            chunk,
        )
    )


def _safety_exclusion_signals(text: str) -> list[str]:
    signals: list[str] = []
    patterns = (
        ("database exclusion", r"\b(database|db|dbcontext|appdata)\b"),
        ("migration exclusion", r"\b(migration|migrations|ef migration)\b"),
        ("build exclusion", r"\b(build|dotnet build)\b"),
        ("test exclusion", r"\b(test|tests|dotnet test)\b"),
        ("restore exclusion", r"\b(restore|dotnet restore)\b"),
        ("run/script exclusion", r"\b(run|execute|script|start\.bat|stop\.bat)\b"),
        ("secret/config exclusion", r"\b(secret|secrets|credential|credentials|token|tokens|appsettings|local settings|\.env)\b"),
        ("generated-file exclusion", r"\b(generated|bin/|obj/|\.packages|logs?|backups?)\b"),
        ("code exclusion", r"\b(code|source)\b"),
    )
    for signal, pattern in patterns:
        if re.search(pattern, text):
            signals.append(signal)
    return signals


def _explicit_risk(text: str) -> str | None:
    match = re.search(r"\brisk(?: level)?\s*:\s*(critical|high|medium|low)\b", text)
    if match:
        return match.group(1)
    return None


def _recommended_command(project_name: str, run_id: str, task_id: str, risk_level: str) -> str:
    if risk_level == "critical":
        return "Do not proceed. Reduce scope or wait for a future explicit override workflow."
    if risk_level == "high":
        return f"devo policy check --project {project_name} --run {run_id} --task {task_id} --action implementation"
    return (
        f"devo agent prompt {IMPLEMENTATION_COORDINATOR_AGENT_NAME} "
        f"--project {project_name} --run {run_id} --task {task_id}"
    )


def _safer_alternative(action_type: str, risk_level: str) -> str | None:
    if risk_level == "critical":
        return "Do not execute. Narrow the scope, remove destructive/secret-handling behavior, and re-run policy check."
    if risk_level == "high":
        return "Generate or review a policy classification first, then obtain explicit approval before proceeding."
    if action_type in {"implementation", "git_commit"}:
        return "Generate an implementation prompt or validation plan before mutating files."
    return None


def _normalize_action_type(action_type: str) -> str:
    normalized = action_type.strip().lower()
    if normalized not in ACTION_TYPES:
        allowed = ", ".join(sorted(ACTION_TYPES))
        msg = f"Invalid action type: {action_type}. Allowed: {allowed}"
        raise ValueError(msg)
    return normalized


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _max_risk(left: str, right: str) -> str:
    return left if RISK_RANK[left] >= RISK_RANK[right] else right


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
