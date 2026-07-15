# DevOrchestrator

DevOrchestrator is an initial Python CLI for registering local software projects and producing safe, bounded project scan summaries.

This version intentionally does not include autonomous agents, AI API integration, or a web UI.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Install

From the repository root:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Usage

Show CLI help:

```powershell
devo --help
```

Register a project:

```powershell
devo project add --name MyProject --path E:\path\to\project
```

List registered projects:

```powershell
devo project list
```

Scan a registered project:

```powershell
devo project scan MyProject
```

List available agent definitions:

```powershell
devo agent list
```

Show an agent definition:

```powershell
devo agent show ProjectContextDiscoveryAgent
```

Generate a ready-to-paste Project Context Discovery prompt:

```powershell
devo agent prompt ProjectContextDiscoveryAgent --project MyProject
```

Import Project Context Discovery output:

```powershell
devo agent import-output ProjectContextDiscoveryAgent --project MyProject --file E:\path\to\discovery-output.md
```

Generate a ready-to-paste Project Context Reviewer prompt:

```powershell
devo agent prompt ProjectContextReviewerAgent --project MyProject
```

Import Project Context Reviewer output:

```powershell
devo agent import-output ProjectContextReviewerAgent --project MyProject --file E:\path\to\review-output.md
```

Show context lifecycle status:

```powershell
devo project context-status MyProject
```

Approve reviewed project context:

```powershell
devo project approve-context MyProject
```

Create a development run from approved context:

```powershell
devo run create --project MyProject --goal "Add command search"
```

List development runs:

```powershell
devo run list --project MyProject
```

Show run status:

```powershell
devo run status <runId> --project MyProject
```

Generate run-level prompts:

```powershell
devo agent prompt IdeaAnalystAgent --project MyProject --run <runId>
devo agent prompt RequirementsAgent --project MyProject --run <runId>
devo agent prompt PlannerAgent --project MyProject --run <runId>
devo agent prompt PlanReviewerAgent --project MyProject --run <runId>
devo agent prompt TaskDecomposerAgent --project MyProject --run <runId>
devo agent prompt ImplementationCoordinatorAgent --project MyProject --run <runId> --task <taskId>
devo agent prompt ValidatorAgent --project MyProject --run <runId> --task <taskId>
```

Import run-level agent outputs:

```powershell
devo agent import-output IdeaAnalystAgent --project MyProject --run <runId> --file E:\path\to\idea-output.md
devo agent import-output RequirementsAgent --project MyProject --run <runId> --file E:\path\to\requirements-output.md
devo agent import-output PlannerAgent --project MyProject --run <runId> --file E:\path\to\planner-output.md
devo agent import-output PlanReviewerAgent --project MyProject --run <runId> --file E:\path\to\plan-review-output.md
devo agent import-output TaskDecomposerAgent --project MyProject --run <runId> --file E:\path\to\task-decomposer-output.md
devo agent import-output ImplementationCoordinatorAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\implementation-output.md
devo agent import-output ValidatorAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\validation-output.md
```

Record implementation completion evidence after implementation is performed outside DevOrchestrator:

```powershell
devo implementation report --project MyProject --run <runId> --task <taskId> --file E:\path\to\completion-report.md
devo implementation status --project MyProject --run <runId> --task <taskId>
```

Review validation evidence after implementation completion is reported:

```powershell
devo agent prompt ValidatorAgent --project MyProject --run <runId> --task <taskId>
devo agent import-output ValidatorAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\validation-output.md
devo validation status --project MyProject --run <runId> --task <taskId>
```

Show run artifacts and generated prompts:

```powershell
devo run artifacts <runId> --project MyProject
```

Select an active project or run:

```powershell
devo use --project MyProject
devo use --project MyProject --run <runId>
```

Registered projects are stored under:

```text
workspace/projects/<projectName>/project.json
```

Scan results are stored under:

```text
workspace/projects/<projectName>/scan-result.json
```

The registered path must exist and must be a directory. DevOrchestrator records whether the directory looks like a software project by checking for `.git`, `.sln`, `.csproj`, `package.json`, `pyproject.toml`, or `README.md`.

The scanner walks the registered project in read-only mode and records bounded metadata only: paths, categories, counts, and safe Git summary information when available. It skips generated folders, caches, virtual environments, secret-like files, large files, and common media/binary files.

## Agent Concept

Agents are prompt-only role definitions in this version. Each agent is a YAML contract that describes its purpose, allowed inputs, expected outputs, workflow rules, approval requirements, and next state. DevOrchestrator can list these definitions, show their details, and generate a bounded ProjectContextDiscoveryAgent prompt from `scan-result.json`.

No AI model is called yet. No autonomous agent workflow, Codex integration, code modification, or web UI is implemented.

## Context Lifecycle

Project context moves through a manual approval lifecycle:

```text
REGISTERED -> SCANNED -> CONTEXT_DRAFTED -> CONTEXT_REVIEWED -> CONTEXT_APPROVED
```

After scanning a registered project, generate a ProjectContextDiscoveryAgent prompt and paste it into your AI tool of choice. Import the resulting Markdown with `devo agent import-output ProjectContextDiscoveryAgent --project MyProject --file <file>`. This stores the draft under `workspace/projects/<projectName>/context/drafts/` and records lifecycle metadata in `context/context-state.json`.

Discovery imports must include all required sections in order: `project-profile.md`, `architecture-map.md`, `module-map.md`, `data-model-summary.md`, `validation-profile.md`, `risk-profile.md`, and `unknowns.md`. DevOrchestrator refuses incomplete or truncated discovery drafts before generating reviewer prompts.

Next, generate the ProjectContextReviewerAgent prompt. It uses `project.json`, the bounded `scan-result.json` summary, and the imported discovery draft. Import the reviewer output with `devo agent import-output ProjectContextReviewerAgent --project MyProject --file <file>`. Once both discovery and review artifacts exist, approve the context with `devo project approve-context MyProject`.

Approval creates `workspace/projects/<projectName>/approvals/context-approval.json` and promotes the reviewed artifacts into `workspace/projects/<projectName>/context/approved/`. DevOrchestrator does not modify the scanned project.

## Run Concept

A development run is the workspace container for one feature, bugfix, refactor, or new project goal. Runs are created only after project context is approved, so later requirements, planning, task decomposition, implementation prompts, validation, review, and final audit can all refer back to an approved context snapshot.

Run data is stored under:

```text
workspace/runs/<projectName>/<runId>/
```

Each run includes `goal.md`, `run-state.json`, and folders for artifacts, prompts, validation, reviews, logs, and approvals. Active project/run selection is stored in `workspace/current.json`.

This version creates runs and supports prompt-only IdeaAnalystAgent, RequirementsAgent, PlannerAgent, PlanReviewerAgent, TaskDecomposerAgent, ImplementationCoordinatorAgent, and ValidatorAgent workflow. It does not execute implementations, run tests automatically, call AI models, integrate Codex, or provide a web UI.

## Run-Level Agent Workflow

Run-level agents are still prompt-only. After a run is created, generate the IdeaAnalystAgent prompt with `devo agent prompt IdeaAnalystAgent --project MyProject --run <runId>`. Import the resulting Markdown with `devo agent import-output IdeaAnalystAgent --project MyProject --run <runId> --file <file>`. This stores `artifacts/idea-analysis.md` and moves the run to `IDEA_ANALYSIS_DRAFTED`.

Next, generate the RequirementsAgent prompt with `devo agent prompt RequirementsAgent --project MyProject --run <runId>`. The prompt includes approved project context, the run goal, run state, and imported idea analysis when available. Import the requirements output with `devo agent import-output RequirementsAgent --project MyProject --run <runId> --file <file>`. This stores `artifacts/requirements.md` and moves the run to `REQUIREMENTS_DRAFTED`.

After requirements are drafted, generate the PlannerAgent prompt with `devo agent prompt PlannerAgent --project MyProject --run <runId>`. The prompt includes approved project context, `goal.md`, `run-state.json`, idea analysis, and requirements. Import the planner output with `devo agent import-output PlannerAgent --project MyProject --run <runId> --file <file>`. This stores `artifacts/plan.md` and moves the run to `PLAN_DRAFTED`.

Then generate the PlanReviewerAgent prompt with `devo agent prompt PlanReviewerAgent --project MyProject --run <runId>`. It includes the same evidence plus `artifacts/plan.md`. Import the review output with `devo agent import-output PlanReviewerAgent --project MyProject --run <runId> --file <file>`. This stores `artifacts/plan-review.md` and moves the run to `PLAN_REVIEWED`.

After a plan has been reviewed, generate the TaskDecomposerAgent prompt with `devo agent prompt TaskDecomposerAgent --project MyProject --run <runId>`. It includes approved context, `goal.md`, `run-state.json`, idea analysis, requirements, the plan, and the plan review. Import the task decomposition output with `devo agent import-output TaskDecomposerAgent --project MyProject --run <runId> --file <file>`. This stores `artifacts/tasks.md` and moves the run to `TASKS_DRAFTED`.

TaskDecomposerAgent output should include `task-list.md`, `task-dependency-map.md`, `first-safe-task.md`, `task-risk-notes.md`, `validation-requirements.md`, and `implementation-boundaries.md`. Each task should include its id, title, objective, scope, out-of-scope notes, likely files or areas when known, validation required, risk level, dependencies, and recommended executor.

After tasks are drafted, generate an ImplementationCoordinatorAgent prompt for one selected task with `devo agent prompt ImplementationCoordinatorAgent --project MyProject --run <runId> --task <taskId>`. The prompt includes the approved context, run artifacts, `artifacts/tasks.md`, the selected task id, and an extracted selected-task excerpt. It prepares implementation instructions only; it does not execute implementation. Import the output with `devo agent import-output ImplementationCoordinatorAgent --project MyProject --run <runId> --task <taskId> --file <file>`. This stores `artifacts/implementation/<taskId>/implementation-brief.md`, records the current task in `run-state.json`, and moves the run to `IMPLEMENTATION_READY`.

ImplementationCoordinatorAgent output should include `implementation-brief.md`, `selected-task.md`, `scope-boundaries.md`, `files-and-areas.md`, `validation-commands.md`, `safety-checks.md`, `codex-execution-prompt.md`, and `completion-report-template.md`.

After implementation is performed outside DevOrchestrator by Codex or a human, record completion evidence with `devo implementation report --project MyProject --run <runId> --task <taskId> --file <file>`. The completion report is copied to `artifacts/implementation/<taskId>/completion-report.md`, and DevOrchestrator records the report path, reported timestamp, validation summary when extractable, and commit hash when extractable. Git commit hashes are optional because some tasks may be local-only or documentation-only. Inspect the recorded evidence with `devo implementation status --project MyProject --run <runId> --task <taskId>`.

After completion evidence is reported, generate a ValidatorAgent prompt with `devo agent prompt ValidatorAgent --project MyProject --run <runId> --task <taskId>`. The prompt includes approved context, run artifacts, the selected task, `implementation-brief.md`, and `completion-report.md`. Import the validation review with `devo agent import-output ValidatorAgent --project MyProject --run <runId> --task <taskId> --file <file>`. This stores `artifacts/implementation/<taskId>/validation-report.md`, records the validation decision when extractable, and moves the run to `VALIDATION_REVIEWED`. Inspect the recorded review with `devo validation status --project MyProject --run <runId> --task <taskId>`.

ValidatorAgent output should include `validation-summary.md`, `validation-evidence.md`, `commands-reviewed.md`, `scope-coverage.md`, `gaps-or-concerns.md`, `validation-decision.md`, and `recommended-next-step.md`. The validation decision must be exactly one of `passed`, `passed_with_notes`, `failed`, or `needs_more_evidence`. DevOrchestrator does not run tests or validation commands automatically yet; it only records and reviews reported evidence.

The run-level status flow is:

```text
RUN_CREATED -> IDEA_ANALYSIS_DRAFTED -> REQUIREMENTS_DRAFTED -> PLAN_DRAFTED -> PLAN_REVIEWED -> TASKS_DRAFTED -> IMPLEMENTATION_READY -> IMPLEMENTATION_REPORTED -> VALIDATION_REVIEWED
```

`devo run artifacts <runId> --project MyProject` shows `goal.md`, `run-state.json`, imported artifacts including `idea-analysis`, `requirements`, `plan`, `plan-review`, `tasks`, implementation briefs, completion reports, and validation reports grouped by task id, plus every generated prompt.

RequirementsAgent import requires IdeaAnalystAgent output unless `--allow-missing-idea-analysis` is explicitly provided. PlannerAgent requires imported requirements and will not run directly from `RUN_CREATED` or `IDEA_ANALYSIS_DRAFTED`. PlanReviewerAgent requires imported PlannerAgent output. TaskDecomposerAgent requires a reviewed plan and will not run directly from `REQUIREMENTS_DRAFTED` or `PLAN_DRAFTED`. ImplementationCoordinatorAgent requires `TASKS_DRAFTED`, a provided `--task`, and a task id that exists in `tasks.md`. Implementation completion reporting requires an existing implementation brief for the selected task. ValidatorAgent requires `IMPLEMENTATION_REPORTED`, an implementation brief, and a completion report for the selected task. This version does not implement automatic validation runners, code review, fix, final audit, AI model calls, or a web UI.

## Development

Run tests:

```powershell
pytest
```
