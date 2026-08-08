# DevOrchestrator

DevOrchestrator, or Devo, is a local development control room for AI-assisted software work. It records project context, runs, agent workflow state, approvals, validation evidence, Git delivery evidence, reports, and recovery notes.

Devo is not the AI itself. ChatGPT plans and reviews, Codex implements and operates, and Devo manages the workflow guardrails and evidence trail. This version intentionally does not include autonomous agents or AI API integration. It now includes a local read-only API and dashboard for inspecting Devo state.

## Current Strategy

Devo itself is the main product priority now. Target projects such as PersonalOS are primarily real-world test projects for proving Devo workflows, approvals, validation, delivery, reports, history, and recovery.

The current strategy is CLI-first and local-first:

- Codex/Desktop/CLI acts as the AI worker.
- Devo CLI manages workflow, approvals, validation, delivery, reports, history, and generated visual artifacts.
- No direct AI API tokens are required for current Devo development.
- Manual/Codex mode must remain supported even after future model adapters exist.
- Dashboard/UI work stays read-only for now; the CLI remains the execution and recovery path.

The long-term product vision is documented in [Company-model vision](docs/devo-company-model.md): Devo should behave like a local software-development company operating system around AI workers, with Codex CLI as the default personal/local worker and optional API/model agents deferred. The next implementation priorities are tracked in [Remaining roadmap](docs/remaining-roadmap.md).

## Project Memory

Durable project direction is tracked in GitHub docs so DevOrchestrator can recover even if chat context is unavailable:

- [Current state](docs/current-state.md)
- [Devo vision](docs/devo-vision.md)
- [Company-model vision](docs/devo-company-model.md)
- [Codex worker adapter design](docs/codex-worker-adapter-design.md)
- [Real Codex supervised dry-run runbook](docs/runbooks/real-codex-supervised-dry-run.md)
- [Remaining roadmap](docs/remaining-roadmap.md)
- [Current capabilities](docs/current-capabilities.md)
- [Agent workflow](docs/agent-workflow.md)
- [Usability roadmap](docs/usability-roadmap.md)
- [Visual strategy](docs/visual-strategy.md)
- [UI/API architecture](docs/ui-architecture.md)
- [UI MVP specification](docs/ui-mvp-spec.md)
- [TASK-DEVO-085 planning pipeline dogfood report](docs/dogfood/devo-pipeline-dogfood-085.md)
- [TASK-DEVO-099 real Codex dry-run report](docs/dogfood/devo-real-codex-dry-run-099.md)
- [PersonalOS operating model](docs/personal-os-operating-model.md)
- [Roadmap](docs/roadmap.md)
- [How to use Devo](docs/how-to-use-devo.md)
- [Token usage](docs/token-usage.md)
- [Future improvements](docs/future-improvements.md)
- [Deferred scope](docs/deferred-scope.md)
- [Operating model](docs/operating-model.md)
- [Recovery guide](docs/recovery.md)

## How To Use Devo Day To Day

Start with `devo doctor` to check Devo health, or `devo doctor --project <name>` to include one registered project. For setup, use `devo project onboard --project <name>` to see registration, scan, context, validation, settings, doctor, and the next setup command in one checklist. Then use `devo report project --project <name>` or `devo report handoff --project <name>` to recover current state. Use `devo workflow status --project <name> --run <runId>` and `devo workflow next --project <name> --run <runId>` to find the next safe step. Let a human or coding agent perform implementation, then record evidence with Devo validation, review, delivery, context refresh, and handoff commands.

Devo keeps the workflow honest and recoverable; it does not call AI, implement code by itself, or bypass external security policy.

## Doctor Health Check

`devo doctor` is a compact read-only health check. It does not run build, test, backup, restore, app, migration, scheduler-update, or external API commands.

```powershell
devo doctor
devo doctor --project PersonalOS
```

Without `--project`, doctor checks Devo-level health: workspace folders, optional current selection, Python environment basics, core docs, backup inventory when a backup root is discoverable, and scheduled backup task status when safely checkable on Windows.

With `--project`, doctor also checks project registration, project path, Git status, project workflow settings, validation registry, build-command presence, recent work-package counts, latest validation status, and generated visual report presence. Each check reports `OK`, `WARN`, `FAIL`, or `SKIP`, followed by an overall status and one suggested next action.

## If Context Is Lost

1. Clone the repo from `https://github.com/manasagrawal97/dev-orchestrator`.
2. Read [docs/current-state.md](docs/current-state.md).
3. Read [docs/roadmap.md](docs/roadmap.md).
4. Run `powershell.exe -ExecutionPolicy Bypass -File .\scripts\recovery\check-devo-recovery-status.ps1`.
5. Run `devo report handoff --project DevOrchestrator` or `devo report project --project DevOrchestrator` for the latest compact workspace state.
6. Continue from the next planned task.

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

Set project workflow defaults:

```powershell
devo project onboard --project MyProject
devo project onboard --project MyProject --suggest-settings
devo project onboard --project MyProject --write-suggestions
devo project settings-show --project MyProject
devo project settings-set --project DevOrchestrator --default-lane devo-internal-source --default-branch main
devo project settings-set --project PersonalOS --default-lane low-risk-ui-maintenance --default-validation-command dotnet-build-personalos --default-branch master
```

`devo project onboard` is read-only by default. `--write-suggestions` writes `workspace/projects/<project>/reports/onboarding-report.md`; it still does not modify the target project. `--suggest-settings` prints a suggested `settings-set` command but does not write settings.

Project settings are Devo workspace metadata. They do not modify the target project. Defaults can store the normal lane, validation command, full-test command, branch, scope-template behavior, delivery mode, and notes for a project.

Create the first planning artifacts from a final project brief:

```powershell
devo project brief-create --project MyProject --title "My Project" --file E:\path\to\brief.md
devo project brief-show --project MyProject
devo project brief-approve --project MyProject
devo project blueprint-create --project MyProject
devo project blueprint-show --project MyProject
devo project blueprint-approve --project MyProject
```

Project Brief and Blueprint artifacts are stored under `workspace/projects/<project>/planning/`. They are deterministic Devo workspace artifacts only. This does not create batches or execution queues, does not call AI, does not call Codex CLI, and does not modify the target project.

Create the first deterministic backlog/task placeholders from an approved blueprint:

```powershell
devo project backlog-create --project MyProject
devo project backlog-show --project MyProject
devo project task-list --project MyProject
devo project task-show --project MyProject --task T001
devo project backlog-approve --project MyProject
```

Backlog artifacts are also stored under `workspace/projects/<project>/planning/` as `backlog.json` and `backlog.md`. TASK-DEVO-075 creates template-based starter tasks from blueprint milestones/epics only. It does not create batches, run an execution queue, call AI, call Codex CLI, approve implementation, or modify the target project.

Generate a Codex/manual planning handoff prompt to refine the starter backlog:

```powershell
devo project backlog-prompt --project MyProject
devo project backlog-validate --project MyProject --file E:\path\to\refined-backlog.json
devo project backlog-import --project MyProject --file E:\path\to\refined-backlog.json
```

`backlog-prompt` writes `workspace/projects/<project>/planning/backlog-refinement-prompt.md`. It does not call Codex or any AI API. `backlog-import` validates the refined JSON and imports it as a draft backlog; it does not approve implementation or modify the target project.

Create a planning batch from backlog tasks:

```powershell
devo project batch-suggest --project MyProject
devo project batch-suggest --project MyProject --write
devo project batch-create --project MyProject --title "First batch" --tasks T001,T002
devo project batch-list --project MyProject
devo project batch-show --project MyProject --batch B001
devo project batch-approval-request --project MyProject --batch B001 --note "Ready for planning review."
devo project batch-approval-show --project MyProject --batch B001
devo project batch-approval-list --project MyProject
devo project batch-review --project MyProject --batch B001 --note "Looks scoped."
devo project batch-review --project MyProject --batch B001 --note "Needs a smaller split." --needs-changes
devo project batch-approve --project MyProject --batch B001 --note "Approved for queue creation."
devo project batch-reject --project MyProject --batch B001 --note "Needs a safer split."
```

Batch artifacts are stored under `workspace/projects/<project>/planning/batches/` as `batch-<batch_id>.json`, `batch-<batch_id>.md`, and `batch-index.json`. Batch approval artifacts are stored under `workspace/projects/<project>/planning/batches/approvals/` as `batch-<batch_id>-approval.json` and `.md`. Batch approval is planning approval only; it does not run Codex, create an execution queue, approve implementation, run validation, commit, push, or modify the target project. Queue creation remains a separate explicit command after approval.

Compute deterministic planning progress:

```powershell
devo project progress --project MyProject
devo project progress --project MyProject --json
```

Progress is derived from Project Brief, Blueprint, Backlog/Task, and Batch artifacts. It reports count-based task completion, backlog readiness, blocked percentage, batch completion, and milestone/epic rollups. Weighted scoring, execution queue progress, Codex execution tracking, and AI/API automation are deferred.

Create and track an execution queue from an approved planning batch:

```powershell
devo project queue-create --project MyProject --batch B001
devo project queue-list --project MyProject
devo project queue-show --project MyProject --queue Q001
devo project queue-start --project MyProject --queue Q001
devo project queue-next --project MyProject --queue Q001
devo project queue-complete-item --project MyProject --queue Q001 --item QI001 --note "Completed manually."
devo project queue-block-item --project MyProject --queue Q001 --item QI002 --note "Needs review."
devo project queue-pause --project MyProject --queue Q001 --reason usage_limit --note "Resume when usage resets."
devo project queue-resume --project MyProject --queue Q001
```

Queue artifacts are stored under `workspace/projects/<project>/planning/queues/` as `queue-<queue_id>.json`, `queue-<queue_id>.md`, and `queue-index.json`. The execution queue is state tracking only. It does not run Codex, run validation, run Git commands, commit, push, or modify target project source.

Generate Codex-ready handoff prompts from queue items, backlog tasks, or batches:

```powershell
devo project handoff-next --project MyProject --queue Q001
devo project handoff-task --project MyProject --task T001
devo project handoff-batch --project MyProject --batch B001
devo project handoff-list --project MyProject
devo project handoff-show --project MyProject --handoff H001
devo project handoff-mark-used --project MyProject --handoff H001
```

Handoff artifacts are stored under `workspace/projects/<project>/planning/handoffs/` as `handoff-<handoff_id>.json`, `handoff-<handoff_id>.md`, and `handoff-index.json`. Handoff prompts are the first safe bridge from Devo planning to Codex execution: Devo writes a prompt, then the user manually pastes it into Codex. Devo still does not run Codex, call AI APIs, execute target commands, approve implementation, run validation, commit, push, or modify target project source.

Prepare one queue-linked supervised Codex worker without executing it:

```powershell
devo worker codex prepare-next --project MyProject --queue Q001
devo worker codex queue-status --project MyProject --queue Q001
devo worker codex queue-status --project MyProject --queue Q001 --item QI001
devo worker codex flow-summary --project MyProject --queue Q001
```

`prepare-next` finds the current running or next pending queue item, generates or reuses its handoff, creates a linked worker run, creates a run plan, and runs safe preflight. It does not approve the run plan, launch Codex, run validation, complete queue/tasks, commit, or push. `queue-status` is read-only status visibility for the queue item, linked worker run, linked run plan, latest execution/report/review status, completion readiness, and next CLI command. After a queue is completed, `queue-status` defaults to the most recently completed item so review evidence remains visible; use `--item` to inspect a specific queue item. `flow-summary` gives the shorter operator view of queue -> handoff -> worker -> run plan -> report -> review -> completion readiness.

Track manual Codex worker attempts without running Codex:

```powershell
devo worker codex run-create --project MyProject --handoff H001
devo worker codex run-list --project MyProject
devo worker codex run-show --project MyProject --run WR001
devo worker codex run-status --project MyProject --run WR001 --status waiting_review --note "Manual Codex session stopped."
devo worker codex run-mark-used --project MyProject --run WR001
```

Worker run artifacts are stored under `workspace/projects/<project>/workers/codex/` as `worker-run-<id>.json`, `worker-run-<id>.md`, and `worker-run-index.json`. These are workspace-only tracking records. They do not run Codex, call AI APIs, execute target commands, prove implementation complete, import execution reports, mark queue/task completion, validate, commit, push, or modify target project source.

Preflight supervised Codex runs and create safe run-plan previews:

```powershell
devo worker codex preflight --project MyProject --run WR001
devo worker codex preflight --project MyProject --run WR001 --codex-path E:\tools\fake-codex.cmd
devo worker codex run-plan --project MyProject --run WR001
devo worker codex run-plan --project MyProject --run WR001 --codex-path E:\tools\fake-codex.cmd
devo worker codex run-plan-list --project MyProject
devo worker codex run-plan-show --project MyProject --plan RP001
devo worker codex run-plan-approve --project MyProject --plan RP001 --note "Planning reviewed."
```

Run-plan artifacts are stored under `workspace/projects/<project>/workers/codex/run-plans/` as `run-plan-<id>.json`, `run-plan-<id>.md`, and `run-plan-index.json`. Preflight checks registration, linked handoff/prompt files, target repo path, worker status, linked metadata where available, and whether a Codex executable appears on `PATH` using safe detection only. Normal users can rely on `PATH`; dogfood or controlled tests can pass `--codex-path` to validate and store an explicit executable path in the run plan. It does not run Codex, invoke an AI model, execute target commands, validate, commit, push, complete queue/tasks, or modify target project source. Run-plan approval is planning approval only; guarded execution still requires explicit `execute --confirm-execute`.

Run one supervised Codex CLI worker for an approved run plan:

```powershell
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001 --codex-path E:\tools\fake-codex.cmd
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute --codex-path E:\tools\fake-codex.cmd
devo worker codex execute-log --project MyProject --run WR001
```

Execution is intentionally narrow. Devo refuses to launch Codex unless the worker run exists, the run plan exists, the run plan is approved, preflight is passed or warnings-only, the prompt path exists, the target repo path exists, an executable is resolved from the run plan, `PATH`, or an explicit `--codex-path`, and `--confirm-execute` is present. Devo captures logs under `workspace/projects/<project>/workers/codex/logs/`. Exit code `0` moves the worker run and linked queue item to `waiting_review`, not `completed`; failures become `failed`/`paused_failure`, obvious usage-limit output becomes `paused_usage_limit`, and obvious safety/approval output becomes `blocked_needs_approval` with the queue waiting for review. Devo does not trust Codex output as proof, complete queue/tasks, run validation, commit, push, or modify delivery state automatically. Queue item completion still requires `devo project queue-complete-item` after human review and validation evidence.

Record review and validation evidence before queue completion:

```powershell
devo worker codex review-template --project MyProject --run WR001
devo worker codex review-attach-evidence --project MyProject --run WR001 --status provided --summary "<validation summary>"
devo worker codex review-record --project MyProject --run WR001 --status reviewed_passed --reviewer "<name>" --note "<note>"
devo worker codex review-show --project MyProject --run WR001
devo worker codex review-list --project MyProject
```

Review artifacts live under `workspace/projects/<project>/workers/codex/reviews/`. They capture checklist evidence, validation summaries, changed-file review notes, safety review notes, reviewer decision, and next queue guidance. They are evidence only: Devo does not run validation, trust worker reports blindly, complete queue/tasks, commit, push, or modify target projects.

`devo project queue-complete-item` is review-aware for queue items linked to Codex worker runs or waiting in review. It refuses completion by default unless the linked worker review is `reviewed_passed` and validation evidence is not failed. If evidence is missing, needs changes, rejected, or failed, Devo prints the next review commands instead of completing the item. The emergency `--confirm-without-review` override exists for legacy/manual cases only, requires a non-empty note, and records a warning in queue item notes. No validation, commit, push, or target command is run automatically.

The fake-worker end-to-end dogfood for this flow is documented in [docs/dogfood/devo-supervised-worker-dogfood-096.md](docs/dogfood/devo-supervised-worker-dogfood-096.md).

Before the first real Codex supervised worker launch, read [docs/runbooks/real-codex-supervised-dry-run.md](docs/runbooks/real-codex-supervised-dry-run.md). The first real run should be no-op or docs-only, target DevOrchestrator first, and validate orchestration/review gates rather than productivity. It must not auto-validate, complete queues/tasks, commit, push, or touch PersonalOS.

The first real dry-run attempt is documented in [docs/dogfood/devo-real-codex-dry-run-099.md](docs/dogfood/devo-real-codex-dry-run-099.md). It reached the guarded launch step, but Windows denied `CreateProcess` for the detected WindowsApps Codex executable path before Codex produced output. Do not retry real supervised execution until the launch path and failure handling are hardened.

The future Codex CLI worker adapter is documented in [docs/codex-worker-adapter-design.md](docs/codex-worker-adapter-design.md). Manual handoff remains first-class, and any future worker execution must preserve explicit approval, validation/review evidence, queue pause/resume state, delivery checks, and target repository safety boundaries.

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
devo current
devo work resume
devo work status
devo project activity
devo doctor
```

Common project and work-package commands can use the saved current project/run when `--project` or `--run` are omitted. When Devo uses saved context, it prints `Using current project: ...` or `Using current run: ...`. If no current context exists, it tells you to run `devo use --project <project>` or `devo use --project <project> --run <runId>`.

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

No AI model is called yet. No autonomous agent workflow, Codex integration, or code modification is implemented. The local dashboard is read-only and does not execute workflow actions.

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

This version creates runs and supports prompt-only IdeaAnalystAgent, RequirementsAgent, PlannerAgent, PlanReviewerAgent, TaskDecomposerAgent, ImplementationCoordinatorAgent, ValidatorAgent, CodeReviewerAgent, and FinalAuditorAgent workflow. It does not execute implementations, run tests automatically, inspect diffs automatically, apply fixes, call AI models, or integrate Codex. The local dashboard only reads and displays Devo state.

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

RequirementsAgent import requires IdeaAnalystAgent output unless `--allow-missing-idea-analysis` is explicitly provided. PlannerAgent requires imported requirements and will not run directly from `RUN_CREATED` or `IDEA_ANALYSIS_DRAFTED`. PlanReviewerAgent requires imported PlannerAgent output. TaskDecomposerAgent requires a reviewed plan and will not run directly from `REQUIREMENTS_DRAFTED` or `PLAN_DRAFTED`. ImplementationCoordinatorAgent requires `TASKS_DRAFTED`, a provided `--task`, and a task id that exists in `tasks.md`. Implementation completion reporting requires an existing implementation brief for the selected task. ValidatorAgent requires `IMPLEMENTATION_REPORTED`, an implementation brief, and a completion report for the selected task. CodeReviewerAgent requires `VALIDATION_REVIEWED`, an implementation brief, a completion report, and a validation report for the selected task. FinalAuditorAgent requires `CODE_REVIEWED`, an implementation brief, a completion report, a validation report, and a code review report for the selected task. Task closure requires `FINAL_AUDITED`, a final audit report, and a closeable final decision. Task disposition requires an approved project context, an existing run, and a task id from `tasks.md`; `covered_by` also requires `--covered-by`, and all non-`open` dispositions require `--note`. Task selection requires approved project context, an existing run, and `tasks.md`; it skips formal closures and resolved dispositions, skips blocked tasks when blocker metadata is present, warns on unknown statuses, and does not invent missing risk or priority. Run closure requires approved project context, an existing run, `tasks.md`, and no unresolved tasks. This version does not implement automatic next-run creation, automatic validation runners, automatic diff extraction, fixes, AI model calls, or dashboard write actions.

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

Approval records are written under `workspace/runs/<projectName>/<runId>/artifacts/approvals/` as `approvals-ledger.json`, `approval-<approvalId>.json`, and `approval-<approvalId>.md`. Each record stores task id/title, action type, risk level, policy reasons, matched signals, safety exclusions, requested/approved/rejected metadata, and a deterministic scope fingerprint. If task text, policy signals, or safety exclusions change later, a prior approval will not silently match the changed scope.

High-risk workflow recommendations stop at `devo approval request` until a matching pending request is approved. Once a matching approval exists, `devo workflow next` and `devo workflow batch` can recommend the normal next command while showing the approval reference. Critical/blocked actions remain blocked for now; break-glass override and approval expiry are deferred.

## Work Packages And Approval Bundles

Work packages are a lighter-weight path for bounded maintenance batches. They create a run plus scoped artifacts under `workspace/runs/<projectName>/<runId>/artifacts/work-package/`: `work-package.json`, `work-package.md`, `operator-prompt.md`, generated scope templates, and phase prompts. The MVP includes the built-in `low-risk-ui-maintenance` lane for UI-only, non-DB, non-config work validated by a registered build command.

```powershell
devo work lanes
devo work lane-show --lane low-risk-ui-maintenance
devo work new --project MyProject --goal "Fix UI warning group"
devo work new --project MyProject --lane low-risk-ui-maintenance --goal "Fix UI warning group"
devo work start --project MyProject --lane low-risk-ui-maintenance --goal "Fix UI warning group"
devo work resume --project MyProject --run <runId>
devo work scope-template --project MyProject --run <runId>
devo work import-scope --project MyProject --run <runId> --file E:\path\to\scope.md
devo work status --project MyProject --run <runId>
devo work next --project MyProject --run <runId>
devo work prompt --project MyProject --run <runId> --phase implement
devo work request-approval-bundle --project MyProject --run <runId> --task T001
devo work complete --project MyProject --run <runId> --commit <commitHash> --message "Delivered summary"
devo work list --project MyProject --limit 10
devo work history --project MyProject --limit 10
devo project activity --project MyProject --limit 10
devo visual work-package --project MyProject --run <runId>
devo visual project-activity --project MyProject --limit 10
devo work scope-example --lane low-risk-ui-maintenance
```

`devo work new` is the shortest start command. It creates a run, starts a work package in the selected lane, generates `scope-template.md` by default, and prints the `devo work resume` command for the new run. If `--lane` is omitted, Devo uses the project's configured `default_lane`; if neither exists, it fails clearly. `--no-template` skips template generation, and `--template` can force template generation when project settings disable automatic templates. It does not import scope, request approval, edit target project files, run validation, commit, or push.

`devo work scope-template` writes `scope-template.md` under the work-package artifacts folder with the required import sections plus lane-specific allowed/forbidden defaults. Codex or a human fills the template, then `devo work import-scope` imports it. `devo work import-scope` expects Markdown sections for selected items, exact files, allowed changes, forbidden changes, validation command, and delivery plan. It writes a deterministic `tasks.md` for `T001` so the normal policy and approval system remains in charge.

Built-in lanes currently include:

- `docs-only`: README/docs/Markdown/Mermaid work; default validation is `git diff --check`, with no build required by default.
- `low-risk-ui-maintenance`: UI-only Razor help text, empty states, mechanical analyzer fixes, and display-only prompts validated by a registered build command.
- `warning-cleanup`: small mechanical analyzer/warning fixes validated by the project build command when available.
- `small-bugfix`: focused source fixes with build and targeted tests when registered.
- `small-feature`: one small approved feature or requirement, with build/tests as appropriate.
- `test-only`: test files/helpers and docs notes, preferring targeted registered tests.
- `backup-maintenance`: Devo backup/recovery scripts, status/reporting, recovery docs, and temp-directory tests only.
- `devo-internal-source`: DevOrchestrator source, tests, and docs with py_compile, focused tests, full suite, and git diff checks.

Lanes are reusable scope templates and defaults; they do not bypass policy, approvals, validation runner checks, Git delivery checks, or Codex/OS permissions. If a task needs DB, migrations, secrets, config, app run, external APIs, live scheduler changes, real backup/restore, or a broader risk class, the exact scope and approval must say so explicitly.

Approval bundles are a convenience layer over normal Devo approvals, not a bypass. A bundle writes `approval-bundle-<bundleId>.json` and `.md` under `artifacts/approval-bundles/`, creates child approvals for the scoped source edit and registered validation command, and approves those child approvals together only when none are rejected or blocked.

```powershell
devo approval bundle-status --project MyProject --run <runId> --bundle <bundleId>
devo approval bundle-approve --project MyProject --run <runId> --bundle <bundleId> --by "Your Name" --note "Approved scope"
```

Exact `target_command` approval remains supported for maximum precision. Bundled `target_repo_build` or `target_repo_test` child approvals still have to match the registered validation command category plus the exact command id and command text before the validation runner will execute them.

`devo work resume` is the easiest continuation command. It reads the work package, lane, imported scope, approval bundle status, latest validation evidence, and latest Git delivery evidence, then prints the current state, next phase, exact recommended commands, Codex operator instructions, lane rules, stop conditions, and final report expectations. It is read-only and does not implement, validate, approve, commit, push, or mutate the target project.

`devo work next` prints a smaller next-action view for the current package state, including required command, stop conditions, and whether user approval is needed. For draft packages it suggests `devo work scope-template` before import, which avoids hand-building inconsistent scope files. `devo work prompt --phase <phase>` writes a Codex-ready phase prompt under `operator-prompt-<phase>.md`; supported phases are `scope`, `implement`, `validate`, `deliver`, and `complete`.

After implementation, registered validation, commit, and push, run `devo work complete` to mark the package delivered. Completion stores the commit hash, delivery summary, latest validation run id/status when available, approval bundle status, final Git delivery status when available, and delivered timestamp. `devo work status` then shows the compact final state, next action, and suggested next command. The intended low-risk package loop is:

```text
work new -> work resume
```

`work resume` then guides the detailed loop:

```text
fill scope template -> import scope -> request approval bundle -> bundle approve -> prompt/implement -> prompt/validate -> prompt/deliver -> work complete -> final report
```

For recent activity, `devo work list` shows compact open and recent work-package state, including approval bundle status, latest validation status, delivered commit, and next action. `devo work history` puts delivered/closed packages first and includes the delivery summary. `devo project activity` combines recent runs, delivered packages, latest validation runs, recent context/report artifacts, current Git delivery status, and a suggested next action.

`devo visual work-package` and `devo visual project-activity` generate Mermaid Markdown under `workspace/` from current Devo artifacts. Static Mermaid docs explain stable concepts; generated visual reports summarize live/current work and are not committed.

UI-ready read models are available through JSON output:

```powershell
devo project overview --project MyProject --json
devo project activity --project MyProject --json
devo work status --project MyProject --run <runId> --json
devo doctor --project MyProject --json
```

These commands are read-only. They provide the data contract for the local API and dashboard. UI code should consume read models or API responses, not scrape raw `workspace/` folders directly. The local UI/API shape and safety model are documented in [docs/ui-architecture.md](docs/ui-architecture.md), and the first read-only dashboard scope is defined in [docs/ui-mvp-spec.md](docs/ui-mvp-spec.md).

## Local Read-Only API

Devo serves the same read models through a local-only FastAPI server for dashboard work:

```powershell
devo api routes
devo api serve
```

The default URL is `http://127.0.0.1:8765`. API v1 started read-only and still blocks non-local hosts. UI v2 now adds a tiny controlled workspace-safe action endpoint that can write Devo workspace artifacts only after confirmation. It does not run validations, builds, tests, restores, commits, pushes, scheduler changes, target apps, or model/API agents.
API responses include a lightweight `X-Devo-Elapsed-Ms` header to help identify slow read-model endpoints during dashboard review.
Slow read-model endpoints can also return an opt-in JSON timing breakdown:

```text
GET /api/projects/DevOrchestrator/overview?include_timing=true
GET /api/projects/PersonalOS/doctor?include_timing=true
GET /api/projects/PersonalOS/activity?include_timing=true
```

Timing metadata is omitted by default. It is read-only diagnostic data; Devo does not add DB-backed dashboard caching yet.

Example health endpoint:

```text
GET http://127.0.0.1:8765/api/health
```

UI action safety metadata is also available through read-only endpoints:

```text
GET /api/actions
GET /api/actions/allowed
GET /api/actions/{action_id}
POST /api/actions/execute
```

These endpoints describe which dashboard actions are read-only now, which workspace-only actions are available through the controlled executor, and which approval/delivery/restore/scheduler/model actions are deferred or blocked. `POST /api/actions/execute` is limited to `work.new.create`, `work.scope_template.generate`, `visual.work_package.generate`, `visual.project_activity.generate`, and `onboarding.report.write`; it requires `confirm: true` and never modifies target repositories.

## React UI Scaffold

The read-only dashboard lives under `ui/`. It consumes the local API.

UI helper commands:

```powershell
devo ui info
devo ui urls
devo ui status
devo ui open
```

`devo ui status` checks whether the local API and UI dev server are reachable without starting them. It is a reachability check only; it does not prove dashboard pages load unless the API and UI servers are already running. For browser/page verification, start both servers first, then open the UI. `devo ui open` opens `http://127.0.0.1:5173` only when the UI is already reachable; otherwise it prints the manual start commands.

Start the backend:

```powershell
devo api serve
```

Start the frontend:

```powershell
cd ui
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The dashboard includes Projects, Project Overview, Planning Intake, Blueprint, Backlog, Batches, Queues, Handoffs, Worker Runs, Progress, Work Package, Activity, Health, and Action Safety pages backed by the local API. Planning Intake is a read-only operator guide for the brief -> blueprint -> backlog -> batch -> queue -> handoff -> worker run -> progress workflow. Blueprint, Backlog, Batches, Queues, Handoffs, Worker Runs, and Progress provide detailed read-only inspection of planning artifacts, milestone/epic rollups, task filters, batch risk/lane summaries, queue item state, handoff and worker-run/report/run-plan/execution metadata, progress bars, warnings, and next actions. The dashboard shows selection separately from saved CLI current context, uses section-level loading for slower project data, keeps raw paths quieter, shows UI action safety metadata, provides copyable CLI commands, can create Devo work-package drafts, and can generate the approved workspace-only artifacts from the Action Safety page after confirmation. CLI/Codex remains the execution path for approvals, validation, implementation, commit, push, restore, scheduler work, target app runs, and model/API agents.

Manual Codex worker report import is available for assisted handoff workflows:

```powershell
devo worker codex report-template --project MyProject --run WR001
devo worker codex report-validate --project MyProject --run WR001 --file report-WR001.json
devo worker codex report-import --project MyProject --run WR001 --file report-WR001.json
devo worker codex report-show --project MyProject --run WR001
devo worker codex report-list --project MyProject
```

Reports are stored under `workspace/projects/<project>/workers/codex/reports/` and summarize what a manually run worker reported: status, changed files, validation, tests, commands, optional commit hash, warnings, blockers, follow-ups, and notes. Importing a report is not proof of completion. It does not run Codex, call AI APIs, execute target commands, complete queue/tasks, run validation, commit, push, or modify target repositories.

Codex run plans are safe previews for a future supervised execution path:

```powershell
devo worker codex preflight --project MyProject --run WR001
devo worker codex run-plan --project MyProject --run WR001
devo worker codex run-plan-list --project MyProject
devo worker codex run-plan-show --project MyProject --plan RP001
devo worker codex run-plan-approve --project MyProject --plan RP001 --note "Planning reviewed."
```

Run plans live under `workspace/projects/<project>/workers/codex/run-plans/`. They store readiness checks, blocked reasons, warnings, a safe command preview, allowed/forbidden scope, validation expectations, and next action guidance. They do not execute Codex, call AI APIs, run target commands, trust implementation complete, validate, commit, push, or complete queue/task state. `run-plan-approve` is a planning-review marker only.

Supervised Codex execution is available only through an approved run plan and explicit confirmation:

```powershell
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute
devo worker codex execute-log --project MyProject --run WR001
```

The command launches one Codex CLI process, passes the linked prompt through stdin, uses the run-plan working directory, captures stdout/stderr logs, and updates the worker-run record cautiously. It does not run validation, complete queue/task state, commit, push, or treat Codex output as delivery proof. Review logs, then use `report-template`/`report-import` and explicit queue/task commands only after human review.

## Policy Gates

Policy commands classify task risk and check whether a task/action can proceed before implementation or execution. They are deterministic and read existing run artifacts, task text, task ledger state, and known action hints. They do not call AI, run target project commands, modify registered projects, or store approvals.

```powershell
devo policy classify --project MyProject --run <runId> --task <taskId>
devo policy check --project MyProject --run <runId> --task <taskId> --action implementation_prompt
devo policy status --project MyProject --run <runId>
```

Risk levels are `low`, `medium`, `high`, and `critical`. Low risk is allowed without approval. Medium risk is allowed with warnings and approval recommended. High risk requires approval before proceeding. Critical risk is blocked until a future approval/override workflow exists.

Known action hints include non-mutating actions such as `implementation_prompt` and `validation`, local mutation actions such as `implementation` and `git_commit`, remote delivery such as `git_push`, and target repository actions such as `target_repo_docs_edit`, `target_repo_code_edit`, `target_repo_config_edit`, `target_repo_validation`, `target_repo_build`, `target_repo_test`, `target_repo_run`, `target_repo_migration`, `target_repo_database`, and `target_repo_script`. Docs-only target repository edits are medium risk and path-scoped; target repository code, config, validation/build/test/run, migration, database, and script actions are high risk by default.

Policy signals include low-risk read-only inspection, prompt/report generation, docs summaries, and non-mutating workflow checks; medium-risk local source edits, target repository docs edits, workspace artifact writes, ledger mutations, and local commits; high-risk target project modification, target commands, database or migration work, scheduler changes, restore/cleanup, Git push, external folder writes such as Google Drive, and machine configuration changes; and critical destructive deletes, secret or credential handling, production database modification, force operations, or approval bypass attempts. Safety-boundary wording such as "no DB, migrations, build, test, restore, secrets, generated files, or local settings" is recorded as safety exclusions instead of being treated as positive risk evidence.

`devo workflow next` and `devo workflow batch` use policy checks when choosing an implementation task. Low and medium tasks can still produce the normal next command, with medium warnings. High or critical tasks stop at a policy review recommendation instead of pretending they are safe to implement. Critical override behavior is intentionally deferred.
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

PersonalOS commands are registered but high-risk and disabled by default. PersonalOS restore/build/test commands should be inspected with `devo validation dry-run` until the user explicitly approves a matching validation or target-command scope. Exact `target_command` approval remains supported for maximum precision. The validation runner also recognizes safely scoped `target_repo_build`, `target_repo_test`, and `target_repo_validation` approvals when the action matches the registered command category and the approval text still covers the exact command id and command text. The Devo approval ledger does not bypass Codex/OpenAI/OS/GitHub security policy.
## Project Context Updates

Project context updates keep Devo workspace knowledge fresh after scans, completed runs, validation registry changes, environment snapshots, delivery reports, and approval ledger changes. They are deterministic summaries of existing Devo artifacts only: DevOrchestrator does not call AI, does not modify target projects, and does not overwrite approved baseline context automatically.

```powershell
devo project context-summary MyProject
devo project context-refresh --project MyProject
devo project context-refresh --project MyProject --run <runId> --write-draft
devo project context-apply --project MyProject --file E:\path\to\context-update.json
devo project context-history --project MyProject
```

`devo project context-summary` shows the registered path, lifecycle status, approved context artifacts when present, latest scan summary, validation registry summary, environment snapshot summary, recent run statuses, warnings, and the suggested next context action.

`devo project context-refresh` reads only Devo workspace metadata such as `project.json`, `scan-result.json`, approved context paths, `validation-commands.json`, environment snapshots, recent run summaries, workflow batch reports, validation run records, git delivery reports, and approval ledgers. By default it prints a non-mutating summary. With `--write-draft`, it writes `context-update-YYYYMMDD-HHMMSS.md` and `.json` under `workspace/projects/<projectName>/context-updates/` and records the draft in `context-updates-ledger.json`.

`devo project context-apply` accepts only generated context-refresh JSON files. Applying a reviewed draft appends an applied record to the context update ledger and records `latest_context_update_at` and `latest_context_update_file` in Devo context metadata. If baseline context is already approved, it stays approved; the update is stored separately. If context is not approved, Devo records the update but does not pretend it is approved baseline context.

Context updates use `facts_added` and `facts_changed` only for deterministic facts already present in Devo artifacts. Missing data becomes warnings instead of invented facts, and secret-like or local sensitive values are omitted or classified rather than copied.
## Git Delivery

Git delivery commands inspect registered project repositories without staging, committing, pushing, or modifying target files.

```powershell
devo git status --project MyProject
devo git delivery-check --project MyProject
devo git delivery-check --project MyProject --run <runId> --task <taskId>
devo git delivery-report --project MyProject --message "feat: describe delivered work"
devo git delivery-report --project MyProject --run <runId> --task <taskId> --message "feat: describe delivered work"
```

`devo git status` shows the branch, HEAD commit, upstream, ahead/behind counts when available, clean/dirty state, staged files, unstaged files, untracked files, and warnings.

`devo git delivery-check` performs deterministic readiness checks. It detects staged forbidden paths such as `.env`, key files, `workspace/`, backup folders, `.venv/`, `node_modules/`, `.pytest_cache/`, `__pycache__/`, `bin/`, `obj/`, and `.packages/`. It scans changed text files for conservative secret-like signals such as `OPENAI_API_KEY`, `API_KEY=`, `SECRET=`, `PASSWORD=`, `TOKEN=`, `PRIVATE KEY`, and connection strings with passwords. Secret values are never printed; only the path and signal type are reported. It also runs `git diff --check`, summarizes validation evidence when a run/task is supplied, and notes Devo approval evidence for `git_commit` and `git_push` when available.

`devo git delivery-report` writes Markdown and JSON reports under `workspace/projects/<projectName>/git-delivery/` or, when a run is supplied, under `workspace/runs/<projectName>/<runId>/artifacts/git-delivery/`. Reports include readiness (`ready`, `warning`, or `blocked`), changed-file summaries, blockers, warnings, validation/approval evidence, suggested commit guidance, suggested push guidance when the branch is ahead, and the exact next human action.

DevOrchestrator does not auto-push and does not bypass external approval policies. If push is blocked by Codex approval policy, the user must run `git push` manually after reviewing the delivery report.

## Reports And Handoff

Deterministic reports collect the current Devo workspace state into compact summaries. They are useful when context is lost, after a long interruption, or before handing work from ChatGPT to Codex or a human.

```powershell
devo report project --project MyProject
devo report project --project MyProject --write
devo report run --project MyProject --run <runId>
devo report run --project MyProject --run <runId> --write --format json
devo report handoff --project MyProject
devo report handoff --project MyProject --run <runId> --write
```

`devo report project` summarizes registered project metadata, Git repository state when available, context approval/update state, recent runs, validation records, approval records, Git delivery reports, warnings, and suggested next actions.

`devo report run` summarizes one run: run state, workflow next-action guidance, task selection, task resolution, policy and approval evidence, validation evidence, Git delivery evidence, context updates, blockers, and suggested next human or Codex action.

`devo report handoff` is the concise recovery view. It includes the current state, last completed run/task signal, next action, safety constraints, commands to inspect state, key docs to read, what not to do, and deferred scope reminders.

Use `--write` to store Markdown and JSON artifacts. Project and handoff reports are written under `workspace/projects/<projectName>/reports/`; run reports are written under `workspace/runs/<projectName>/<runId>/artifacts/reports/`. Report commands are read-only with respect to registered target projects and do not run validation, create approvals, push Git changes, call AI models, or modify workflow state.

DevOrchestrator now dogfoods these report and handoff commands on Devo itself and occasional controlled target-project batches. PersonalOS should validate Devo behavior, not drive the main roadmap.

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

Check backup health without creating, restoring, deleting, or scheduling anything:

```powershell
devo backup status --dest "G:\My Drive\Backups\DevOrchestrator"
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

Each backup is written to a timestamped folder named `devo-workspace-backup-YYYYMMDD-HHMMSS[-label]` and includes `backup-manifest.json` plus a copied `workspace/` folder. The manifest records included roots, excluded patterns, file count, total bytes, per-file SHA-256 hashes, source workspace path, backup path, Git commit, Git branch, warnings, creation timestamp, and `protected: true/false`. `devo backup verify` fails if the manifest is missing, a copied file is missing, file count or total bytes differ, or any file hash differs. Complete backups are the only restorable backups.

During creation, Devo uses a temporary `.incomplete` folder and renames it only after the manifest is written. If a folder still ends with `.incomplete`, the backup was interrupted or failed, commonly because the PowerShell process was closed before completion. Incomplete folders are reported separately by `devo backup list` and `devo backup status`; they are not counted as successful backups and are not retention candidates.

`devo backup cleanup` keeps the latest 3 complete normal backups by default, never deletes protected backups, and skips unknown, invalid, and incomplete folders. Scheduled backup installs use hidden PowerShell mode so a random terminal window should not appear. If an older visible scheduled task is still installed, reinstall it later with `.\scripts\recovery\install-devo-backup-task.ps1` after approving scheduler changes.

## Development

Run tests:

```powershell
pytest
```
