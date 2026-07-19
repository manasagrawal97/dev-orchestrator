# DevOrchestrator

DevOrchestrator is an initial Python CLI for registering local software projects and producing safe, bounded project scan summaries.

This version intentionally does not include autonomous agents, AI API integration, or a web UI.

## Project Memory

Durable project direction is tracked in GitHub docs so DevOrchestrator can recover even if chat context is unavailable:

- [Current state](docs/current-state.md)
- [Roadmap](docs/roadmap.md)
- [Deferred scope](docs/deferred-scope.md)
- [Operating model](docs/operating-model.md)
- [Recovery guide](docs/recovery.md)

## If Context Is Lost

1. Clone the repo from `https://github.com/manasagrawal97/dev-orchestrator`.
2. Read [docs/current-state.md](docs/current-state.md).
3. Read [docs/roadmap.md](docs/roadmap.md).
4. Run `powershell.exe -ExecutionPolicy Bypass -File .\scripts\recovery\check-devo-recovery-status.ps1`.
5. Continue from the next planned task.

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
devo agent prompt CodeReviewerAgent --project MyProject --run <runId> --task <taskId>
devo agent prompt FinalAuditorAgent --project MyProject --run <runId> --task <taskId>
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
devo agent import-output CodeReviewerAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\code-review-output.md
devo agent import-output FinalAuditorAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\final-audit-output.md
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

Review implementation evidence after validation has been reviewed:

```powershell
devo agent prompt CodeReviewerAgent --project MyProject --run <runId> --task <taskId>
devo agent import-output CodeReviewerAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\code-review-output.md
devo review status --project MyProject --run <runId> --task <taskId>
```

Audit final task evidence after code review:

```powershell
devo agent prompt FinalAuditorAgent --project MyProject --run <runId> --task <taskId>
devo agent import-output FinalAuditorAgent --project MyProject --run <runId> --task <taskId> --file E:\path\to\final-audit-output.md
devo audit status --project MyProject --run <runId> --task <taskId>
```

Close a final-audited task:

```powershell
devo task close --project MyProject --run <runId> --task <taskId>
devo task close --project MyProject --run <runId> --task <taskId> --note "Closure note"
devo task status --project MyProject --run <runId> --task <taskId>
devo task list --project MyProject --run <runId>
```

Mark task disposition when the original task list is stale or one implementation covers multiple task entries:

```powershell
devo task mark --project MyProject --run <runId> --task T001 --status covered_by --covered-by T002 --note "Covered by the implementation and validation recorded for T002."
devo task mark --project MyProject --run <runId> --task T004 --status not_needed --note "No separate documentation change was needed."
devo task mark --project MyProject --run <runId> --task T003 --status open
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

This version creates runs and supports prompt-only IdeaAnalystAgent, RequirementsAgent, PlannerAgent, PlanReviewerAgent, TaskDecomposerAgent, ImplementationCoordinatorAgent, ValidatorAgent, CodeReviewerAgent, and FinalAuditorAgent workflow. It does not execute implementations, run tests automatically, inspect diffs automatically, apply fixes, call AI models, integrate Codex, or provide a web UI.

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

After validation has been reviewed, generate a CodeReviewerAgent prompt with `devo agent prompt CodeReviewerAgent --project MyProject --run <runId> --task <taskId>`. The prompt includes approved context, run artifacts, the selected task, `implementation-brief.md`, `completion-report.md`, and `validation-report.md`. Import the review with `devo agent import-output CodeReviewerAgent --project MyProject --run <runId> --task <taskId> --file <file>`. This stores `artifacts/implementation/<taskId>/code-review.md`, records the review decision when extractable, and moves the run to `CODE_REVIEWED`. Inspect the recorded review with `devo review status --project MyProject --run <runId> --task <taskId>`.

CodeReviewerAgent output should include `review-summary.md`, `scope-review.md`, `changed-files-review.md`, `quality-review.md`, `risk-review.md`, `test-review.md`, `findings.md`, `review-decision.md`, and `recommended-next-step.md`. The review decision must be exactly one of `approve`, `approve_with_notes`, `changes_requested`, or `blocked`. DevOrchestrator does not automatically inspect Git diffs yet, so CodeReviewerAgent must state whether it reviewed actual code/diff or only completion and validation evidence.

After code review has been recorded, generate a FinalAuditorAgent prompt with `devo agent prompt FinalAuditorAgent --project MyProject --run <runId> --task <taskId>`. The prompt includes approved context, run artifacts, the selected task, `implementation-brief.md`, `completion-report.md`, `validation-report.md`, and `code-review.md`. Import the audit with `devo agent import-output FinalAuditorAgent --project MyProject --run <runId> --task <taskId> --file <file>`. This stores `artifacts/implementation/<taskId>/final-audit.md`, records the final decision when extractable, and moves the run to `FINAL_AUDITED`. Inspect the recorded audit with `devo audit status --project MyProject --run <runId> --task <taskId>`.

FinalAuditorAgent output should include `audit-summary.md`, `lifecycle-check.md`, `evidence-check.md`, `decision-check.md`, `unresolved-notes.md`, `final-decision.md`, and `recommended-next-step.md`. The final decision must be exactly one of `close_task`, `close_with_notes`, `needs_follow_up`, or `blocked`. This workflow can recommend closure or follow-up, but it does not modify code or apply fixes; use the task closure command to record `TASK_CLOSED`.

After final audit, close a task with `devo task close --project MyProject --run <runId> --task <taskId>`. Closure is allowed only when the final decision is `close_task` or `close_with_notes`; `needs_follow_up`, `blocked`, and `unknown` block closure. This stores `artifacts/implementation/<taskId>/closure-record.md`, records closure metadata in `run-state.json`, and moves the run to `TASK_CLOSED`. Add `--note "<closure note>"` to record explicit closure context. Inspect one task with `devo task status --project MyProject --run <runId> --task <taskId>`, or list all run tasks with `devo task list --project MyProject --run <runId>`.

Formal task closure records that a selected task completed the implementation, validation, review, and final audit lifecycle. Task disposition is separate bookkeeping for reconciliation: use `devo task mark` to mark task-list entries as `covered_by`, `superseded`, `not_needed`, `closed_manually`, or reset them to `open`. Disposition writes `artifacts/task-ledger.json`, does not change the run status, does not replace closure records, and does not pretend a task completed the formal lifecycle. When a task has both a formal closure and a disposition, task status prefers the closure status while still showing disposition details.

Task closure and task disposition create durable ledger entries so already-completed, covered, or unnecessary work can be avoided by manual selection and by later automatic task-selection workflows. Once every task in `tasks.md` is resolved by a formal closure record or by a disposition of `covered_by`, `superseded`, `not_needed`, or `closed_manually`, close the run with `devo run close --project MyProject --run <runId>`. Run closure writes `run-summary.md`, records `closed_at`, `run_summary_path`, and an optional closure note in `run-state.json`, and moves the run to `RUN_CLOSED`. It does not require every task to have gone through the full implementation lifecycle, and it does not modify target projects.

Use `devo run summary --project MyProject --run <runId>` to inspect the run goal, final status, unresolved task list, task resolution table, and summary path. A task is unresolved when it has neither a formal closure record nor one of the resolved disposition statuses. Use `devo task candidates --project MyProject --run <runId>` to inspect selectable and skipped tasks with rank, risk, priority, disposition, blocker state, and skip reasons. Use `devo task next --project MyProject --run <runId>` to choose the next deterministic actionable task. The default strategy is `first-open-safe`; optional strategies are `first-open`, `safest`, and `priority`. Add `--include-skipped` to `devo task next` to show skipped tasks, or `--format json` to produce machine-readable output.

The run-level status flow is:

```text
RUN_CREATED -> IDEA_ANALYSIS_DRAFTED -> REQUIREMENTS_DRAFTED -> PLAN_DRAFTED -> PLAN_REVIEWED -> TASKS_DRAFTED -> IMPLEMENTATION_READY -> IMPLEMENTATION_REPORTED -> VALIDATION_REVIEWED -> CODE_REVIEWED -> FINAL_AUDITED -> TASK_CLOSED -> RUN_CLOSED
```

`devo task status` and `devo task list` show both formal closure state and disposition state. `devo run artifacts <runId> --project MyProject` shows `goal.md`, `run-state.json`, imported artifacts including `idea-analysis`, `requirements`, `plan`, `plan-review`, `tasks`, `task-ledger.json` when present, `run-summary.md` when present, implementation briefs, completion reports, validation reports, code review reports, final audit reports, and closure records grouped by task id, plus every generated prompt.

RequirementsAgent import requires IdeaAnalystAgent output unless `--allow-missing-idea-analysis` is explicitly provided. PlannerAgent requires imported requirements and will not run directly from `RUN_CREATED` or `IDEA_ANALYSIS_DRAFTED`. PlanReviewerAgent requires imported PlannerAgent output. TaskDecomposerAgent requires a reviewed plan and will not run directly from `REQUIREMENTS_DRAFTED` or `PLAN_DRAFTED`. ImplementationCoordinatorAgent requires `TASKS_DRAFTED`, a provided `--task`, and a task id that exists in `tasks.md`. Implementation completion reporting requires an existing implementation brief for the selected task. ValidatorAgent requires `IMPLEMENTATION_REPORTED`, an implementation brief, and a completion report for the selected task. CodeReviewerAgent requires `VALIDATION_REVIEWED`, an implementation brief, a completion report, and a validation report for the selected task. FinalAuditorAgent requires `CODE_REVIEWED`, an implementation brief, a completion report, a validation report, and a code review report for the selected task. Task closure requires `FINAL_AUDITED`, a final audit report, and a closeable final decision. Task disposition requires an approved project context, an existing run, and a task id from `tasks.md`; `covered_by` also requires `--covered-by`, and all non-`open` dispositions require `--note`. Task selection requires approved project context, an existing run, and `tasks.md`; it skips formal closures and resolved dispositions, skips blocked tasks when blocker metadata is present, warns on unknown statuses, and does not invent missing risk or priority. Run closure requires approved project context, an existing run, `tasks.md`, and no unresolved tasks. This version does not implement automatic next-run creation, automatic validation runners, automatic diff extraction, fix, AI model calls, or a web UI.

## Approval Ledger

The approval ledger records explicit user approval for a specific Devo task/action scope. It is an internal audit record only: it does not bypass Codex/OpenAI approval policy, does not grant OS, GitHub, Google Drive, scheduler, or shell permissions, and does not execute risky commands.

```powershell
devo approval request --project MyProject --run <runId> --task <taskId> --action implementation_prompt --reason "Why approval is needed"
devo approval approve --project MyProject --run <runId> --approval <approvalId> --by "Your Name" --note "Approved scope"
devo approval reject --project MyProject --run <runId> --approval <approvalId> --by "Your Name" --note "Rejected reason"
devo approval status --project MyProject --run <runId>
devo approval status --project MyProject --run <runId> --approval <approvalId>
devo approval list --project MyProject --run <runId>
```

Approval records are written under `workspace/runs/<projectName>/<runId>/artifacts/approvals/` as `approvals-ledger.json`, `approval-<approvalId>.json`, and `approval-<approvalId>.md`. Each record stores task id/title, action type, risk level, policy reasons, matched signals, requested/approved/rejected metadata, and a deterministic scope fingerprint. If task text or policy reasons change later, a prior approval will not silently match the changed scope.

High-risk workflow recommendations stop at `devo approval request` until a matching pending request is approved. Once a matching approval exists, `devo workflow next` and `devo workflow batch` can recommend the normal next command while showing the approval reference. Critical/blocked actions remain blocked for now; break-glass override and approval expiry are deferred.
## Policy Gates

Policy commands classify task risk and check whether a task/action can proceed before implementation or execution. They are deterministic and read existing run artifacts, task text, task ledger state, and known action hints. They do not call AI, run target project commands, modify registered projects, or store approvals.

```powershell
devo policy classify --project MyProject --run <runId> --task <taskId>
devo policy check --project MyProject --run <runId> --task <taskId> --action implementation_prompt
devo policy status --project MyProject --run <runId>
```

Risk levels are `low`, `medium`, `high`, and `critical`. Low risk is allowed without approval. Medium risk is allowed with warnings and approval recommended. High risk requires approval before proceeding. Critical risk is blocked until a future approval/override workflow exists.

Policy signals include low-risk read-only inspection, prompt/report generation, docs summaries, and non-mutating workflow checks; medium-risk local source edits, workspace artifact writes, ledger mutations, and local commits; high-risk target project modification, target commands, database or migration work, scheduler changes, restore/cleanup, Git push, external folder writes such as Google Drive, and machine configuration changes; and critical destructive deletes, secret or credential handling, production database modification, force operations, or approval bypass attempts.

`devo workflow next` and `devo workflow batch` use policy checks when choosing an implementation task. Low and medium tasks can still produce the normal next command, with medium warnings. High or critical tasks stop at a policy review recommendation instead of pretending they are safe to implement. Approval storage and overrides are intentionally deferred.
## Validation Command Registry And Runner

The validation command registry records known project validation commands with metadata before execution. It stores command id, name, command text, working directory, category, risk level, approval requirement, enabled state, source, and notes under `workspace/projects/<projectName>/validation-commands.json`.

```powershell
devo validation list --project MyProject
devo validation add --project MyProject --id dotnet-build --name "Build solution" --command "dotnet build MyProject.slnx" --category build
devo validation add --project MyProject --id pytest --name "Run pytest" --command "python -m pytest" --category test --risk medium --no-approval-required
devo validation show --project MyProject --id dotnet-build
devo validation check --project MyProject --id dotnet-build
devo validation suggest --project MyProject
devo validation suggest --project MyProject --write
devo validation run --project MyProject --id pytest --timeout-seconds 300
devo validation run --project MyProject --id dotnet-build --run <runId> --task <taskId> --dry-run
devo validation dry-run --project MyProject --id dotnet-build
devo validation history --project MyProject
devo validation history --project MyProject --id pytest
```

`devo validation suggest` proposes likely commands from project metadata such as `.sln`/`.slnx`, `.csproj`, `pyproject.toml`, and `package.json`; `--write` records those suggestions in the Devo workspace registry. `devo validation run` only executes registered commands. It never accepts arbitrary free-form execution input outside the registry.

The validation runner uses deterministic safety gates: disabled commands are blocked unless `--allow-disabled` is supplied, critical commands are blocked, high-risk commands require matching approved approval, missing working directories fail safely, timeouts are enforced, stdout/stderr are captured, and artifacts are written under either project-level `validation-runs/` or run-linked `artifacts/validation-runs/` folders.

PersonalOS commands are registered but high-risk and disabled by default. PersonalOS restore/build/test commands should be inspected with `devo validation dry-run` until the user explicitly approves a matching validation or target-command scope. The Devo approval ledger does not bypass Codex/OpenAI/OS/GitHub security policy.
## Environment Snapshot

Environment snapshots are read-only recovery notes for a project machine setup. They record tool versions, Git branch and commit, dependency files, solution/project files, package references, recommended recovery commands, excluded heavy/cache paths, and warnings about local or sensitive settings files. They do not copy source code, dependency caches, `.venv`, `.git`, `.packages`, `.tools`, `node_modules`, build outputs, `.env` values, or local settings values.

Environment snapshots complement workspace backups. A workspace backup preserves DevOrchestrator runtime state under `workspace/`. An environment snapshot helps rebuild or understand a development environment after a machine failure by pointing to Git state, dependency files, tool versions, and bootstrap commands.

Create an environment snapshot:

```powershell
devo env snapshot --name DevOrchestrator --path "E:\DevOrchestrator"
devo env snapshot --name PersonalOS --path "E:\Personal OS"
```

Snapshots are written to:

```text
workspace/environment/<name>/environment-snapshot.json
workspace/environment/<name>/bootstrap-plan.md
```

Verify a snapshot:

```powershell
devo env verify --snapshot "E:\DevOrchestrator\workspace\environment\DevOrchestrator\environment-snapshot.json"
```

Render or refresh the bootstrap plan from a snapshot:

```powershell
devo env bootstrap-plan --snapshot "E:\DevOrchestrator\workspace\environment\DevOrchestrator\environment-snapshot.json"
```

Recovery strategy: restore DevOrchestrator source from Git, restore `workspace/` from a verified workspace backup, then use environment snapshots to reinstall tools and dependencies deliberately. Treat recommended commands as recovery candidates; inspect project documentation before running them. Local secrets and machine-specific settings must be restored manually by the owner, because DevOrchestrator intentionally records only their path classification and never their values.
## Recovery Automation

For scripted backup, restore, retention cleanup, scheduled backups, and disaster recovery steps, see [docs/recovery.md](docs/recovery.md). The committed scripts under scripts/recovery/ are the preferred wrappers around the devo backup commands.

## Workflow Guidance

Workflow commands inspect a run and recommend the next safe orchestration step without calling AI, modifying target projects, running builds/tests, committing Git changes, or fabricating agent outputs.

```powershell
devo workflow status --project MyProject --run <runId>
devo workflow next --project MyProject --run <runId>
devo workflow advance --project MyProject --run <runId>
devo workflow batch --project MyProject --run <runId> --max-steps 20
```

`devo workflow status` shows the run goal, lifecycle stage, context status, present and missing artifacts, task ledger summary, open tasks, closed or dispositioned tasks, warnings, whether the run can be closed, and the next recommended action.

`devo workflow next` prints one recommended action: the agent prompt command to run, an implementation report command to use, a task close command when final audit permits closure, a run close command when all tasks are resolved, or no action for a closed run.

`devo workflow advance` is intentionally conservative. It does not fake missing AI outputs or execute target-project work. For prompt-based or report-based steps, it shows the exact command to run explicitly.

`devo workflow batch` repeatedly evaluates the run until it reaches a safe stop condition such as waiting for agent output, an implementation report, task closure, run closure, inconsistent state, or a closed run. It writes concise Markdown and JSON reports under `artifacts/workflow/batch-report-YYYYMMDD-HHMMSS.*` and remains non-mutating by default.
## Workspace Backup

DevOrchestrator source code is protected by GitHub, but the local `workspace/` folder contains runtime state that Git intentionally does not track: registered project metadata, approved context artifacts, run history, prompt outputs, task closure records, validation/review/audit reports, run summaries, environment snapshots, and enriched context artifacts. Google Drive Desktop backup protects this Devo workspace/context only. Scheduled backups run every 6 hours by default, keep the latest 3 normal backups, and auto-delete older normal backups only after a new backup is successfully created and verified.

Workspace backup includes only:

```text
workspace/projects/**
workspace/runs/**
workspace/environment/**
workspace/current.json
```

Workspace backup does not include DevOrchestrator source code, `.git`, `.venv`, target project repositories such as `E:\Personal OS`, caches, temporary files, lock files, or arbitrary paths outside the DevOrchestrator workspace. Do not use Google Drive as the active DevOrchestrator workspace; keep the active workspace local and use Drive only as a backup destination.

Create a normal backup:

```powershell
devo backup create --dest "G:\My Drive\Backups\DevOrchestrator" --label "before-task-017"
```

Create a protected milestone backup that cleanup never deletes:

```powershell
devo backup create --dest "G:\My Drive\Backups\DevOrchestrator" --label "before-major-work" --protect
```

List backups:

```powershell
devo backup list --dest "G:\My Drive\Backups\DevOrchestrator"
```

Verify a backup:

```powershell
devo backup verify --path "G:\My Drive\Backups\DevOrchestrator\devo-workspace-backup-20260715-210000-before-task-017"
```

Clean up old unprotected backups after a backup has been created and verified:

```powershell
devo backup cleanup --dest "G:\My Drive\Backups\DevOrchestrator" --keep 3
devo backup cleanup --dest "G:\My Drive\Backups\DevOrchestrator" --keep 3 --dry-run
```

Restore a backup into an empty workspace folder:

```powershell
devo backup restore --backup "G:\My Drive\Backups\DevOrchestrator\devo-workspace-backup-20260715-210000-before-task-017" --dest "E:\RestoredDevOrchestratorWorkspace"
```

Manual backup after every task is not required. Use manual backups only for risky milestones or backup/recovery system changes:

```powershell
devo backup create --dest "G:\My Drive\Backups\DevOrchestrator" --label "before-risky-milestone"
```

Each backup is written to a timestamped folder named `devo-workspace-backup-YYYYMMDD-HHMMSS[-label]` and includes `backup-manifest.json` plus a copied `workspace/` folder. The manifest records included roots, excluded patterns, file count, total bytes, per-file SHA-256 hashes, source workspace path, backup path, Git commit, Git branch, warnings, creation timestamp, and `protected: true/false`. `devo backup verify` fails if the manifest is missing, a copied file is missing, file count or total bytes differ, or any file hash differs. `devo backup cleanup` keeps the latest 3 normal backups by default, never deletes protected backups, and skips unknown or invalid folders.

## Development

Run tests:

```powershell
pytest
```
