# Codex Worker Adapter Design

Source/freshness: TASK-DEVO-089 update, after manual Codex worker report import was added. This is still a design document for future worker execution. Devo does not implement Codex CLI execution, AI API usage, target command execution, or autonomous delivery.

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
- optional future `logs/worker-run-<id>.log`

These are generated workspace artifacts and should not be committed. They are part of Devo runtime state, like planning artifacts, validation run evidence, reports, and handoff prompts.

TASK-DEVO-088 implements worker run tracking. `devo worker codex run-create --project <project> --handoff <handoffId>` creates a planned worker run record from an existing handoff and snapshots the handoff/queue/item/batch/task references.

TASK-DEVO-089 implements manual worker report import. `devo worker codex report-template`, `report-validate`, `report-import`, `report-show`, and `report-list` let a user capture what a manually run Codex worker reported. Import updates only Devo workspace worker artifacts with report status, changed-file summary, validation summary, safety warnings, reviewer notes, and next action. It does not launch Codex, call AI APIs, execute target commands, mark queue/task completion, validate, commit, push, or modify target repositories.

## State Transitions

Worker state must map conservatively to queue state:

- Worker completed successfully -> queue item may become `ready_for_review` or stay running until explicit review.
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
- queue state `ready_for_review` or `waiting_review` before final completion
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

Proposed future execution commands:

```powershell
devo worker codex plan --project <project>
devo worker codex run-next --project <project> --queue <queueId>
devo worker codex run-task --project <project> --task <taskId>
devo worker codex logs --project <project> --run <workerRunId>
devo worker codex resume --project <project> --queue <queueId>
```

Command names are proposals and may change after supervised execution is implemented.

## UI Roadmap

UI exposes worker state cautiously:

- Handoffs page worker-run summary
- worker run status
- source handoff
- report status
- imported report summary
- reported changed-file and validation counts
- safety warnings
- current queue item
- pause reason
- resume guidance
- review checklist
- copyable CLI commands for report template, validation, import, show, and list

The UI is read-only. It does not include risky buttons for execution, validation, commit, push, restore, scheduler changes, target app runs, or model/API calls.

Later, the controlled Action Safety model may expose workspace-safe worker actions with explicit confirmation, such as generating worker plan artifacts or importing a worker report. Launching Codex from UI should require a stronger approval and safety model.

## Rollout Plan

Recommended future sequence:

1. TASK-DEVO-088: Worker run/report data model - completed.
2. TASK-DEVO-089: Manual execution report import - completed.
3. TASK-DEVO-090: Worker run UI visibility and review affordance polish.
4. TASK-DEVO-091: Supervised Codex CLI adapter prototype.
5. TASK-DEVO-092: Queue integration for one item at a time.
6. TASK-DEVO-093: Pause/resume/usage-limit handling.
7. TASK-DEVO-094: Validation/review integration.
8. TASK-DEVO-095: Optional commit/push delivery integration after safety review.

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
