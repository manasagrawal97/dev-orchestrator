# Codex Worker Adapter Design

Source/freshness: TASK-DEVO-092 update, after the first guarded one-run Codex CLI execution prototype was added. Devo still does not implement queue-wide automation, AI API usage, automatic validation, automatic delivery, or autonomous completion.

## Purpose

Devo should remain the orchestrator: the local software-development company operating system that owns project state, planning artifacts, approvals, validation evidence, delivery evidence, reports, recovery notes, and safety boundaries.

Codex CLI/Desktop should be the default local worker for personal development. The worker adapter is a future bridge that can reduce manual copy/paste over time while preserving Devo's audit trail and safety model.

Manual handoff mode must remain supported permanently. The user should always be able to run:

```powershell
devo project handoff-next --project <project> --queue <queueId>
```

Then copy the generated prompt into Codex manually.

Direct API/model agents, including OpenAI, Claude, Gemini, or local model adapters, remain optional future scope. Devo should not require paid API tokens for the current local-first workflow.

## Current Manual Worker Flow

The supported worker flow today is:

1. `devo project handoff-next --project <project> --queue <queueId>`
2. Devo writes a Codex-ready handoff prompt under `workspace/projects/<project>/planning/handoffs/`.
3. The user copies the prompt.
4. The user pastes the prompt into Codex.
5. Codex executes under normal Codex/Desktop safety boundaries.
6. The user reviews the result.
7. The user can import a structured manual worker report into Devo.
8. The user reviews the report, validation evidence, and repository state.
9. The user updates Devo queue/task/progress state manually with commands such as `queue-complete-item`, `queue-block-item`, `queue-pause`, or `queue-resume`.

This is safe and already working. Devo does not run Codex, does not execute target commands, does not call AI APIs, does not validate or commit automatically, and does not mark implementation complete without explicit user action. Imported reports are review evidence, not proof of delivery.

Devo can now also preflight a tracked worker run, write a run-plan preview, and launch one supervised Codex CLI process only when the run plan is approved and `--confirm-execute` is supplied. Execution logs are evidence only; they do not complete queue/task state or prove delivery.

## Future Worker Modes

### Mode 0: Manual Handoff

Current behavior.

- Devo generates prompts only.
- User runs Codex manually.
- User records queue/progress outcomes manually.
- No worker execution records beyond existing handoff artifacts.

### Mode 1: Assisted Handoff

Smallest next step after design.

- Devo generates the prompt and an expected execution-report schema.
- User still runs Codex manually.
- User imports or pastes the execution report back into Devo.
- Devo stores worker-style evidence without launching Codex itself.

### Mode 2: Local Codex CLI Worker, Supervised

First real adapter mode.

- Devo starts a Codex process only after explicit approval.
- User can inspect the generated prompt before launch.
- Devo captures transcript/log output.
- Devo records worker status and next recommended action.
- Devo does not auto-commit unless a later delivery workflow explicitly permits it and delivery checks pass.

### Mode 3: Queue Worker

More automated but still bounded.

- Devo runs approved queue items one at a time.
- Devo pauses on usage limits, failures, safety gates, changed scope, missing approvals, or review requirements.
- Devo preserves queue state and resume hints.
- Approval boundaries still apply per project, batch, queue item, worker run, validation, and delivery.

### Mode 4: Future Multi-Worker Agents

Later architecture.

- Planner, reviewer, validator, and implementer roles may use worker adapters.
- Worker backends may include manual operation, Codex CLI/Desktop, direct API models, or local models.
- Devo owns the role contract and state machine; the backend is pluggable.

## Worker Adapter Contract

A worker adapter should accept structured input and return structured evidence.

Input:

- project
- target repo path
- handoff id
- queue id
- queue item id
- task id
- batch id
- prompt path
- allowed scope
- forbidden scope
- validation expectations
- safety boundaries

Output:

- worker run id
- status: `not_started`, `running`, `completed`, `failed`, `paused_usage_limit`, `blocked_needs_approval`, `cancelled`
- started_at
- completed_at
- command summary
- transcript/log path
- changed files summary
- validation attempted
- validation result
- reported commit hash if Codex committed
- safety warnings
- next recommended Devo action

The output is evidence, not proof of completion. Devo should still require validation/review evidence before marking work completed.

## Storage Model

Codex worker run tracking artifacts live under:

```text
workspace/projects/<project>/workers/codex/
```

Files:

- `worker-run-index.json`
- `worker-run-<id>.json`
- `worker-run-<id>.md`
- `reports/report-<worker_run_id>.json`
- `reports/report-<worker_run_id>.md`
- `run-plans/run-plan-index.json`
- `run-plans/run-plan-<plan_id>.json`
- `run-plans/run-plan-<plan_id>.md`
- `logs/worker-run-<worker_run_id>.log`
- `logs/worker-run-<worker_run_id>.stderr.log`

These are generated workspace artifacts and should not be committed. They are part of Devo runtime state, like planning artifacts, validation run evidence, reports, and handoff prompts.

TASK-DEVO-088 implements worker run tracking. `devo worker codex run-create --project <project> --handoff <handoffId>` creates a planned worker run record from an existing handoff and snapshots the handoff/queue/item/batch/task references.

TASK-DEVO-089 implements manual worker report import. `devo worker codex report-template`, `report-validate`, `report-import`, `report-show`, and `report-list` let a user capture what a manually run Codex worker reported. Import updates only Devo workspace worker artifacts with report status, changed-file summary, validation summary, safety warnings, reviewer notes, and next action. It does not launch Codex, call AI APIs, execute target commands, mark queue/task completion, validate, commit, push, or modify target repositories.

TASK-DEVO-091 implements read-only preflight and run-plan preview artifacts. `devo worker codex preflight` checks project registration, worker run readiness, linked handoff/prompt file existence, target repo path existence, linked metadata where available, and Codex executable presence using safe `PATH` detection only. `devo worker codex run-plan` writes JSON/Markdown/index artifacts with a safe command preview, blocked reasons, warnings, scope, validation expectations, and next action. `run-plan-approve` is planning approval only; it does not grant execution approval.

TASK-DEVO-092 implements the first supervised single-run execution path. `devo worker codex execute-preview` is read-only. `devo worker codex execute --confirm-execute` launches Codex once only after the worker run and approved run plan pass execution checks. `devo worker codex execute-log` reads stored logs. Execution updates the worker run to review/failure/pause/block states but never completes queue/tasks, validates, commits, pushes, or trusts Codex output as proof.

TASK-DEVO-093 integrates that supervised path with one execution queue item at a time. `devo worker codex prepare-next --project <project> --queue <queueId>` creates or reuses the current queue-item handoff, creates a linked worker run, creates a run plan, and runs preflight without approval or execution. `devo worker codex queue-status` is read-only visibility into the queue item, linked worker run, linked run plan, latest execution state, and next CLI command.

TASK-DEVO-094 adds worker review evidence. `review-template`, `review-attach-evidence`, `review-record`, `review-show`, and `review-list` create workspace-only review artifacts under `workers/codex/reviews/`. Reviews capture validation evidence, changed-file review, safety review, acceptance criteria review, follow-up items, reviewer decision, and queue completion guidance. They do not run validation, commit, push, modify target repositories, or complete queue/tasks automatically.

TASK-DEVO-095 gates queue completion on that evidence. `devo project queue-complete-item` checks linked worker review state for Codex-linked or waiting-review items and refuses completion unless the review is `reviewed_passed` and validation evidence is not failed. Missing reviews, needs-changes/rejected decisions, and failed validation evidence print the next review commands instead. `--confirm-without-review` is reserved for emergency/manual legacy cases, requires a note, and records a warning.

## State Transitions

Worker state must map conservatively to queue state:

- Worker completed successfully -> worker, queue item, and queue become `waiting_review`.
- Worker failed -> queue should become `paused_failure`.
- Usage limit detected -> queue should become `paused_usage_limit`.
- Safety gate blocked -> queue should become `waiting_review`.
- User cancelled -> queue should become `paused_manual` or `waiting_review`.
- Validation failed -> queue should become `waiting_review` or `paused_failure`.

Do not automatically mark implementation done only because Codex finished. Worker completion means "Codex stopped and produced output"; it does not mean validation passed, review passed, or delivery is ready.

Final queue completion should require explicit user confirmation through an existing command such as:

```powershell
devo project queue-complete-item --project <project> --queue <queueId> --item <itemId> --note "<reviewed result>"
```

or a future controlled review action.

## Safety Model

Required safety boundaries:

- Explicit approval is required before launching a Codex worker.
- The generated prompt must be visible before execution.
- The project must be registered and context-approved.
- The batch and queue item must be approved where applicable.
- Allowed scope and forbidden scope must be included in the prompt and checked after the run.
- Source changes outside allowed scope should stop delivery.
- Workspace artifacts must not be committed.
- Secrets and local settings must not be committed or exposed.
- PersonalOS must not be touched unless the selected project is PersonalOS and the task explicitly says so.
- Backup, restore, scheduler, database, migration, script, app run, and external API work must remain forbidden unless the task explicitly allows it.
- Autonomous commit/push must not happen until delivery safety checks pass and the delivery workflow explicitly allows it.
- Safety gates must stop the worker path and ask for explicit trusted approval.

The adapter must not be a back door around Devo policy, Codex approval policy, Git delivery checks, or user review.

## Approval Model

Worker integration needs separate approval layers:

- Planning approval: approves brief, blueprint, backlog, and batch intent.
- Execution approval: permits running a worker for one specific queue item or task.
- Delivery approval: permits commit/push when not already covered by standing safe workflow rules.
- Safety override approval: explicit trusted approval when a safety gate blocks.

These approvals are separate. Batch approval does not authorize Codex execution. Worker execution approval does not authorize commit/push. Delivery approval does not waive validation or safety checks.

## Codex Usage Limit Handling

Codex may stop because of usage limits, availability limits, account issues, or process interruption.

Expected behavior:

- Devo records worker status as `paused_usage_limit`.
- Devo captures the partial transcript/log path when available.
- The queue retains the current item.
- The UI/read models show the pause reason and resume hint.
- The user can resume later with `queue-resume` and a new worker run.
- No task or queue item is marked completed because of a usage-limit pause.

Usage limit handling must make recovery boring: the user should not have to reconstruct context from chat history.

## Validation And Review Handling

Codex worker output can report tests/checks it ran, but Devo should not blindly trust free-form text.

Future behavior should support:

- worker-reported validation attempted/result fields
- validation result import from structured evidence
- links to Devo validation runner records when safe validation commands are run
- queue state `waiting_review` before final completion
- explicit review action before `queue-complete-item` or future equivalent completion

Final completion should require explicit user action, review evidence, or a future controlled review action. A worker transcript alone is not enough.

## CLI Command Roadmap

Implemented tracking commands:

```powershell
devo worker codex run-create --project <project> --handoff <handoffId>
devo worker codex run-list --project <project>
devo worker codex run-show --project <project> --run <workerRunId>
devo worker codex run-status --project <project> --run <workerRunId> --status <status> --note "<note>"
devo worker codex run-mark-used --project <project> --run <workerRunId>
```

These commands mutate only Devo workspace worker artifacts. `run-status completed` means the manual/Codex session stopped and reported output; it does not mean the work passed validation, review, delivery checks, commit, push, or queue completion. `run-mark-used` marks only the linked handoff used and does not imply worker completion.

Implemented manual report commands:

```powershell
devo worker codex report-template --project <project> --run <workerRunId>
devo worker codex report-validate --project <project> --run <workerRunId> --file <reportFile>
devo worker codex report-import --project <project> --run <workerRunId> --file <reportFile>
devo worker codex report-show --project <project> --run <workerRunId>
devo worker codex report-list --project <project>
```

These commands mutate only Devo workspace worker report artifacts when importing. `report-import` maps worker-reported states conservatively: completed and partial reports become waiting-for-review states, failed reports become failed, approval blockers become blocked-needs-approval, and usage-limit reports become paused-usage-limit. It does not complete queues/tasks automatically.

Implemented preflight and run-plan commands:

```powershell
devo worker codex preflight --project <project> --run <workerRunId>
devo worker codex run-plan --project <project> --run <workerRunId>
devo worker codex run-plan-list --project <project>
devo worker codex run-plan-show --project <project> --plan <planId>
devo worker codex run-plan-approve --project <project> --plan <planId> --note "<note>"
```

These commands are the safety foundation for a future supervised adapter. They do not invoke Codex, call AI APIs, execute target commands, validate, commit, push, or modify target repositories. The proposed command is stored as a preview only. `run-plan-approve` records that the preview was reviewed as planning metadata; it is not execution approval for a future worker launch.

Implemented supervised one-run execution commands:

```powershell
devo worker codex prepare-next --project <project> --queue <queueId>
devo worker codex queue-status --project <project> --queue <queueId>
devo worker codex execute-preview --project <project> --run <workerRunId> --plan <planId>
devo worker codex execute --project <project> --run <workerRunId> --plan <planId> --confirm-execute
devo worker codex execute-log --project <project> --run <workerRunId>
devo worker codex review-template --project <project> --run <workerRunId>
devo worker codex review-attach-evidence --project <project> --run <workerRunId> --status <provided|passed|failed|partial> --summary "<summary>"
devo worker codex review-record --project <project> --run <workerRunId> --status <reviewed_passed|reviewed_needs_changes|rejected> --reviewer "<name>" --note "<note>"
devo worker codex review-show --project <project> --run <workerRunId>
devo worker codex review-list --project <project>
```

`prepare-next` is the queue bridge: it prepares one current running or next pending queue item and stops before approval or execution. `execute` launches one Codex CLI process through `subprocess.run` without `shell=True`, passes the approved prompt through stdin, captures stdout/stderr logs, and updates the linked worker/queue state conservatively. Exit code `0` becomes `waiting_review`; non-zero failures become `failed`/`paused_failure` unless output clearly indicates usage limit or safety/approval blocking. Review and report import remain required before queue/task completion or delivery.

`review-record --status reviewed_passed` still does not complete the queue item. It only records the reviewer decision and prints the explicit `devo project queue-complete-item` command for the operator to run if the evidence is sufficient. `queue-complete-item` then performs the final review gate before mutating queue/task state.

Proposed future execution commands:

```powershell
devo worker codex run-task --project <project> --task <taskId>
devo worker codex resume --project <project> --queue <queueId>
```

Command names are proposals and may change after supervised execution is implemented.

## UI Roadmap

UI exposes worker state cautiously:

- Handoffs page worker-run summary
- dedicated Worker Runs page
- worker run status
- source handoff
- report status
- run-plan count/status
- latest preflight status
- execution status, exit code, and log path
- imported report summary
- review status, reviewer, decision note, and validation evidence status
- blocked reasons and warnings
- reported changed-file and validation counts
- safety warnings
- current queue item
- pause reason
- resume guidance
- review checklist
- copyable CLI commands for preflight, run-plan, run-plan list/show, execute preview/log/guarded execute, report template, validation, import, show/list, review template/evidence/record/show/list, and explicit post-review queue completion

The UI is read-only. The Worker Runs page inspects existing worker run/report/run-plan/execution artifacts and shows copyable CLI guidance, but it does not import reports from the UI, launch Codex, execute target commands, complete queue items, validate, commit, push, restore, modify scheduler settings, run target apps, or call model/API agents.

Later, the controlled Action Safety model may expose workspace-safe worker actions with explicit confirmation, such as generating worker plan artifacts or importing a worker report. Launching Codex from UI should require a stronger approval and safety model.

## Rollout Plan

Recommended future sequence:

1. TASK-DEVO-088: Worker run/report data model - completed.
2. TASK-DEVO-089: Manual execution report import - completed.
3. TASK-DEVO-090: Worker run UI visibility and review affordance polish - completed.
4. TASK-DEVO-091: Codex worker preflight and run-plan model - completed.
5. TASK-DEVO-092: Supervised Codex CLI adapter prototype - completed.
6. TASK-DEVO-093: Queue integration for one item at a time.
7. TASK-DEVO-094: Validation/review integration - completed.
8. TASK-DEVO-095: Review-gated queue completion - completed.
9. TASK-DEVO-096: Pause/resume/usage-limit handling.
10. TASK-DEVO-097: Optional commit/push delivery integration after safety review.

This rollout keeps the current manual handoff path stable while adding evidence and automation in layers.

## Deferred Scope

Explicitly deferred:

- direct AI API agents
- full autonomous queue execution
- unsupervised Codex runs
- automatic commit/push without delivery checks
- running multiple workers in parallel
- public SaaS or multi-user mode
- replacing Codex, Cursor, Claude Code, or ChatGPT
- general AI chat clone behavior
