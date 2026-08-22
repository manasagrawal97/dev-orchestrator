# Phase 2 Autonomy Roadmap

## Purpose

Phase 2 makes Devo able to run approved batches with minimal human involvement, while preserving safety gates, traceability, review controls, and trusted local delivery.

This is practical autonomy, not reckless full automation. Devo should reduce repeated operator commands only after the work is bounded by approved planning artifacts, validation policy, pause conditions, and delivery safety checks.

Phase 2 should not try to make Codex or a sandboxed worker directly commit or push. Codex/sandbox prepares work, evidence, and runner requests. A trusted local Devo executor running in the normal Windows user context performs delivery.

## 1. Phase 2 Vision

The target workflow is:

```text
Manas approves a batch or policy.
Devo creates or uses queue items.
Devo prepares Codex handoffs.
Codex or another worker executes one task at a time.
Devo imports or reads worker output.
Devo runs validation.
Devo records review state.
Devo creates a delivery runner request.
A trusted local executor delivers safely.
Devo continues to the next task unless a pause condition occurs.
```

The end-user experience should become:

```text
approve a batch once
-> Devo schedules/queues multiple tasks
-> Devo gives tasks to Codex/worker
-> Devo validates work
-> Devo commits/pushes through trusted local context
-> user reviews summaries, failures, or risky changes
```

The important boundary is that approval is still explicit and bounded. Devo can continue within an approved contract, but it must stop when the contract no longer covers the situation.

## 2. Autonomy Levels

Phase 2 should move through levels deliberately:

- Level 0: manual commands, Phase 1 style.
- Level 1: trusted runner auto-delivers pending runner requests.
- Level 2: queue worker runs one approved queue item at a time.
- Level 3: approved batch runs multiple tasks sequentially.
- Level 4: UI-managed autonomy with pause, resume, and review controls.
- Level 5: AI-agent role workers attached to Devo contracts.

The next work should start with Levels 1-3. Do not jump directly to Level 5. The existing Phase 1 control plane is valuable because it already contains state, approvals, validation evidence, worker records, queue state, delivery safety, and runner requests.

## 3. Priority Roadmap

### TASK-DEVO-126: Trusted Runner Watch Mode

- Goal: Add a trusted runner watch command that can process pending delivery runner requests from normal PowerShell/user context.
- Why it matters: It removes the remaining manual `runner-run` command without asking Codex/sandbox to write `.git/index.lock`.
- Scope: Find safe pending runner requests, run the existing `runner-run` logic, write runner-run artifacts, support `--once` first, and stop on blockers.
- Not in scope: Windows scheduled installation, daemon/service behavior, queue execution, Codex execution, UI controls, or new delivery bypasses.
- Safety rules: Only process requested runner requests, never process cancelled/completed requests, verify request freshness and repo state, and preserve all existing delivery gates.
- Done criteria: A normal PowerShell operator can run one watch command and have it deliver one pending safe request or stop with a clear blocker.

### TASK-DEVO-127: Windows Scheduled/Background Trusted Runner

- Goal: Add an explicit local scheduling path for the trusted runner after watch mode is proven.
- Why it matters: It lets Devo deliver approved safe requests from normal user context even when Codex/sandbox cannot commit.
- Scope: Task Scheduler plan/install/status/enable/disable/run-now/remove commands, disabled-by-default setup, wrapper/log artifacts, and one request per trigger through `runner-watch --once`.
- Not in scope: Always-on service, public network listener, UI delivery buttons, or automatic approval.
- Safety rules: Explicit install/enable only, local user context only, clear logs, project/repo allowlists, bounded per-cycle work, and approval policy required.
- Done criteria: Manas can intentionally install, inspect, and disable a trusted scheduled runner without triggering target project commands or unsafe delivery.

### TASK-DEVO-128: Batch Execution Policy And Approval Contract

- Goal: Define the bounded contract that lets Devo run more than one queue item after one approval.
- Why it matters: Batch autonomy is only safe if approval carries precise limits.
- Scope: Policy fields for project, batch id, approved queue ids, allowed tasks/files, forbidden files, max changed files, max tasks per run, validation commands, auto-delivery flags, pause conditions, approver, expiry, and status.
- Not in scope: Worker loop execution, UI controls, or AI-agent decisions.
- Safety rules: Batch approval is not blanket permission for anything; it is a bounded contract.
- Done criteria: Devo can represent whether a planned queue item is inside or outside an approved batch policy.
- Status: Completed. Devo now stores batch execution policy artifacts under `workspace/projects/<project>/planning/execution-policies/` and exposes create/request/approve/reject/list/show/check commands. These commands create approval evidence only and do not execute queues, run Codex, validate, stage, commit, push, or modify target projects.

### TASK-DEVO-129: Autonomous Queue Worker Loop

- Goal: Add the first loop that advances approved queue work one item at a time.
- Why it matters: This is the core of practical batch autonomy.
- Scope: Load approved batch policy, select the next queue item, create/refresh handoff, start/track worker run, wait for result or import, run validation, record review state, create delivery runner request, wait for trusted delivery, mark complete, and continue.
- Not in scope: Fully reliable real Codex automation if the launcher path is still not ready, AI model integration, daemonization, or broad UI controls.
- Safety rules: Work one queue item at a time, stop on any pause condition, never silently continue after validation or delivery failure, and require the trusted executor for delivery.
- Done criteria: Devo can run through one approved queue item and either complete it safely or pause with a precise reason.
- Status: Completed as a v1 preparation loop. `devo project queue-worker-plan` and `devo project queue-worker-run --once --confirm-queue-worker` now load an approved policy, choose one eligible queue item, create/reuse the Codex handoff and manual/assisted worker run record, write queue-worker run artifacts, and pause at `waiting_worker` or a blocker. The v1 loop deliberately does not run real Codex, validation, delivery runner requests, queue completion, commit, or push.

### TASK-DEVO-130: Failure Pause/Resume And Usage-Limit Handling

- Goal: Make every autonomous pause recoverable and clear.
- Why it matters: Autonomy without good pause/resume becomes fragile and scary.
- Scope: Pause records, resume guidance, usage-limit state, failed validation state, delivery failure state, retry rules, and operator summary.
- Not in scope: Automatic risky retries, ACL fixes, arbitrary shell recovery, or ignoring failed validation.
- Safety rules: Stop on failures, preserve evidence, require explicit continuation when risk changes, and avoid losing the current queue item.
- Done criteria: A paused queue can explain what happened, what is safe to retry, and what command or review is needed next.
- Status: Completed as lifecycle control for queue-worker run artifacts. `devo project queue-worker-status`, `queue-worker-pause`, `queue-worker-resume --confirm-resume`, `queue-worker-fail`, `queue-worker-retry --confirm-retry`, and `queue-worker-cancel --confirm-cancel` now make pause reason, missing evidence, retry linkage, policy/item rechecks, and next safe command explicit. This still does not run real Codex, validation, delivery runner requests, queue completion, commit, or push.

### TASK-DEVO-131: Worker-Result Continuation And Delivery-Request Handoff

- Goal: Connect queue-worker runs to imported worker result evidence, review evidence, validation evidence, and trusted delivery runner requests.
- Why it matters: Queue-worker runs need a clear post-worker continuation path before any broader batch automation or UI controls are safe.
- Scope: `queue-worker-evidence`, `queue-worker-continue --confirm-continue`, `queue-worker-request-delivery --confirm-delivery-request`, evidence summaries, delivery request links, and read-model visibility for the latest queue-worker delivery request.
- Not in scope: real Codex execution, AI/API calls, validation execution, runner-watch execution, queue completion, guarded commit/push, UI controls, or multi-task automation.
- Safety rules: advance only through completed worker report, passed review, and passed validation evidence; create a trusted runner request rather than running delivery; stop on policy/scope drift or failed/partial worker evidence.
- Done criteria: A queue-worker run can move from `waiting_worker` to `waiting_review`, `waiting_validation`, `ready_for_delivery_request`, and `delivery_requested` while preserving review and delivery safety.
- Status: Completed. Devo now has read-only evidence inspection, explicit continuation, delivery request creation through the existing trusted runner request flow, and queue-worker/read-model fields that show linked delivery request id/status.

### TASK-DEVO-132: Queue-Worker Assisted End-To-End Dogfood

- Goal: Prove the assisted single-item queue-worker path end to end before deeper automation.
- Why it matters: Dogfood should find friction while the system is still CLI-first and easy to reason about.
- Scope: Temp-project dogfood from approved policy through worker report, review, validation, ready-for-delivery, and trusted runner request creation.
- Not in scope: real Codex execution, AI/API calls, live PersonalOS work, UI controls, runner-watch execution, queue completion, commit, push, daemon behavior, or multi-task automation.
- Status: Completed. See `docs/dogfood/task-devo-132-queue-worker-assisted-e2e.md`; the dogfood proved the path works and identified command-count/operator-order friction.

### TASK-DEVO-133: One-Task Assisted Queue-Worker Step

- Goal: Reduce queue-worker operator command count without adding autonomous multi-task execution.
- Why it matters: TASK-DEVO-132 proved the path works, but the operator still had to remember the exact sequence across worker report, review, validation, delivery request, and trusted runner completion.
- Scope: `devo project queue-worker-step --project <project> --policy <POL-ID> --confirm-step`, `--dry-run`, optional run/message/note targeting, one safe transition per invocation, compact status output, evidence-gate checks, delivery-request creation, and trusted-delivery completion observation.
- Not in scope: real Codex execution, AI/API calls, validation execution, runner-watch execution, queue completion, UI controls, daemon behavior, commit, push, or multi-task loops.
- Safety rules: exactly one transition per call, approved policy required, policy/item drift blocks, missing evidence waits, failed/unknown evidence pauses or fails, delivery request creation uses trusted runner request artifacts only, and completed delivery requires a completed/pushed trusted runner run.
- Done criteria: one command can safely move a queue-worker run from no active run through `waiting_worker`, `waiting_review`, `waiting_validation`, `ready_for_delivery_request`, `delivery_requested`, and completed delivery observation while stopping at every evidence boundary.
- Status: Completed. `queue-worker-step` is the preferred CLI assisted loop; lower-level queue-worker commands remain available for explicit inspection and recovery.

### TASK-DEVO-134: Batch Continuation Loop For One Task At A Time

- Goal: Add a bounded loop that repeats the one-step queue-worker behavior until the next safe stop condition.
- Why it matters: It reduces operator command repetition across approved queue work without pretending Devo can autonomously do worker execution, validation, delivery, or review.
- Scope: `devo project queue-worker-loop --project <project> --policy <POL-ID> --confirm-loop`, `--dry-run`, max-step bounds, optional run/message/note, safe stop reasons, evidence-boundary output, pending-delivery stops, and conservative post-delivery queue item completion through existing queue checks.
- Not in scope: real Codex execution, AI/API calls, validation execution, runner-watch execution, background daemon changes, UI controls, parallel task execution, raw commit/push, or delivery safety bypasses.
- Safety rules: reuse `queue-worker-step`, stop on missing worker report/review/validation, stop on pending trusted delivery, stop on paused/failed/cancelled/blocked states, stop on no eligible item or max steps, and treat unknown states as unsafe.
- Done criteria: a single command can start the next approved item, stop at `waiting_worker`, continue through already-recorded evidence, create a trusted delivery request, observe completed trusted delivery, and then start at most the next eligible item before stopping again at `waiting_worker`.
- Status: Completed. The loop is a one-task-at-a-time assisted operator command, not full autonomy.

### Future: UI Approval And Queue Controls

- Goal: Add safe UI controls only after the CLI evidence and delivery handoff path stays comfortable.
- Why it matters: UI can reduce friction, but only if it calls Devo safety flows instead of bypassing them.
- Scope: View queue, view runner requests, approve batch policy, pause queue, resume queue, cancel pending request, view logs, view blockers, and view summaries.
- Not in scope: Raw commit buttons, raw push buttons, arbitrary shell command buttons, UI bypass of delivery safety, or direct `.git` writes.
- Safety rules: UI actions must go through Devo approval/policy commands and leave artifacts.
- Done criteria: UI can manage approved Devo workflow states without introducing new dangerous action paths.

### TASK-DEVO-134: Progress/Read-Model Cleanup

- Goal: Make progress and current-state summaries reflect delivered work, planning state, queue state, and delivery state more accurately.
- Why it matters: Phase 1 left some planning-oriented summaries that can look blocked even after successful delivery.
- Scope: Read-model cleanup, latest/default queue handling, progress wording, delivered-state summaries, and UI/CLI consistency.
- Not in scope: New autonomy mechanics or UI write actions.
- Safety rules: Read-only summaries must not mutate target repos or workspace approvals.
- Done criteria: `project progress`, intake/status, UI cards, and activity summaries agree on useful next actions.

### TASK-DEVO-135: Workspace Artifact Compaction/Indexing

- Goal: Reduce artifact noise while preserving auditability.
- Why it matters: Phase 1 created many useful artifacts, but navigation is getting heavy.
- Scope: Artifact index, latest pointers, retention guidance for generated reports, compact summaries, and safe search/list commands.
- Not in scope: Deleting historical evidence by default, backup mutation, or lossy cleanup.
- Safety rules: Never remove audit artifacts without explicit approval and documented retention policy.
- Done criteria: Operators can find the current relevant artifacts without hand-browsing many folders.

### TASK-DEVO-136: Docs Consolidation

- Goal: Reduce overlapping docs after Phase 1.
- Why it matters: The docs are valuable but increasingly duplicated.
- Scope: Canonical doc map, archived/superseded notes, shortened how-to flows, and pointer cleanup.
- Not in scope: Removing historical records that still explain safety decisions.
- Safety rules: Preserve delivery safety, runner, and worker runbooks.
- Done criteria: A new operator can find current workflow guidance quickly without reading the whole history.

### TASK-DEVO-137: Phase 2 AI-Agent Worker-Brain Design

- Goal: Design how future AI brains attach to Devo's existing role contracts.
- Why it matters: Devo should add agents by extending contracts, not by bypassing state and approvals.
- Scope: Planner, Architect, Reviewer, QA, Release, local model adapter, API model adapter, Codex adapter, Claude adapter, and Gemini adapter design.
- Not in scope: Real API calls, token storage, autonomous unapproved execution, or replacing Codex/manual mode.
- Safety rules: Manual/Codex mode remains first-class, cost is controlled, and AI outputs remain evidence requiring policy checks.
- Done criteria: There is a design for AI workers that preserves Devo's Phase 1/2 safety model.

## 4. Trusted Local Executor Model

Codex/sandbox remains untrusted for direct `.git` writes. The `.git/index.lock` failures from restricted contexts are a useful boundary, not a problem to hack around.

The trusted executor runs from the normal Windows user context. It consumes explicit Devo workspace requests and performs the same guarded delivery logic already proven by `delivery runner-run`.

The executor must:

- verify request freshness
- verify project and repo path
- verify branch and upstream
- verify changed files
- verify no workspace artifacts are staged
- verify safety gates and blockers
- stop on blockers
- stop on failure
- write runner-run artifacts
- avoid silently continuing after failure
- avoid bypassing delivery runner safety

Possible future forms:

- manual `runner-run` command
- runner watch mode
- Windows scheduled task
- Windows background process
- later service/daemon only if needed

The preferred Phase 2 direction is to improve the trusted local executor rather than weaken sandbox permissions.

## 5. Runner Watch Mode Design

TASK-DEVO-126 starts with this command shape:

```powershell
.\.venv\Scripts\devo.exe delivery runner-watch --project DevOrchestrator --approver "Manas" --once --confirm-runner-watch
```

TASK-DEVO-127 builds background scheduling around the same one-shot behavior rather than adding continuous watch mode:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-plan --project DevOrchestrator --approver "Manas" --interval-minutes 5
.\.venv\Scripts\devo.exe delivery runner-schedule-install --project DevOrchestrator --approver "Manas" --interval-minutes 5 --dry-run --confirm-install
```

Expected behavior:

- find pending runner requests
- pick the oldest safe pending request
- run the same delivery logic as `runner-run`
- write runner-run artifact
- write runner-watch artifact
- stop on blocker or failure
- with `--once`, process one request and exit
- continuous interval mode is deferred
- never process cancelled or completed requests
- never run without trusted approval policy

Watch mode does not implement queue execution, Codex execution, scheduling, UI controls, or new delivery safety behavior. It is a small wrapper around the already trusted runner path.

## 6. Background/Scheduled Runner Design

TASK-DEVO-127 builds on watch mode.

Preferred approach:

```text
Windows Task Scheduler launches Devo runner-watch --once from normal user context.
This avoids Codex sandbox .git restrictions.
```

Safety controls:

- disabled by default
- explicitly installed and enabled only by Manas
- read-only plan/status before any install
- dry-run install that writes only Devo schedule artifacts
- clear status command
- clear enable, disable, run-now, and remove commands
- wrapper and log path under `workspace/projects/<project>/delivery/runner-schedule/`
- one pending request per trigger
- project allowlist
- repo allowlist
- approval policy required
- no public listener
- no arbitrary shell command execution

The scheduled runner should be understandable, quiet, and reversible. It should not feel like a random hidden process with unclear authority.

Implemented command shape:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-plan --project DevOrchestrator --approver "Manas" --interval-minutes 5
.\.venv\Scripts\devo.exe delivery runner-schedule-install --project DevOrchestrator --approver "Manas" --interval-minutes 5 --confirm-install
.\.venv\Scripts\devo.exe delivery runner-schedule-status --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-enable --project DevOrchestrator --confirm-enable
.\.venv\Scripts\devo.exe delivery runner-schedule-disable --project DevOrchestrator --confirm-disable
.\.venv\Scripts\devo.exe delivery runner-schedule-run-now --project DevOrchestrator --confirm-run-now
.\.venv\Scripts\devo.exe delivery runner-schedule-remove --project DevOrchestrator --confirm-remove
```

Real scheduled delivery remains a normal-Windows-user operation. Codex/sandbox can plan and dry-run the schedule, but Manas should decide whether to install and enable the live task.

## 7. Batch Execution Policy

TASK-DEVO-128 defines the batch policy contract before multi-task autonomy.

Suggested fields:

- project
- batch id
- approved queue ids
- allowed tasks
- allowed files/areas
- forbidden files/areas
- max changed files per task
- max tasks per run
- validation commands
- auto-delivery allowed true/false
- auto-push allowed true/false
- pause conditions
- approver
- expiry
- status

Batch execution policy approval is not blanket permission for anything. It is a bounded contract. `auto_delivery_allowed` and `auto_push_allowed` are meaningful only inside that contract and still require the trusted delivery runner path.

If work exceeds the contract, Devo must pause and ask for a new approval or revised policy.

## 8. Autonomous Queue Worker Loop

TASK-DEVO-129 should design and implement the queue worker loop carefully.

Loop:

```text
load approved batch policy
select next queue item
create or refresh handoff
start or track worker run
wait for worker result or imported report
run validation
record review status
create delivery runner request
trusted executor delivers
mark queue item complete
move to next queue item
pause on blocker
```

Be realistic about Codex. If Devo cannot programmatically run Codex reliably yet, Phase 2 can start with assisted/manual Codex execution plus automated tracking and delivery.

The queue loop should make the state machine boring: pending, running, waiting for worker, validating, waiting for delivery, completed, paused, failed.

## 9. Pause Conditions

Hard stops:

- test failure
- validation failure
- secret-risk blocker
- forbidden path touched
- workspace artifact staged
- changed files differ from approved scope
- too many files changed
- merge conflict
- Codex usage limit
- Codex output unclear
- manual review required
- delivery commit/push failure
- runner request mismatch
- branch/upstream mismatch

Pause records should include what happened, what evidence exists, what files changed, what command failed, and the safest next action.

## 10. UI Control Boundary

UI controls should come after the autonomy foundation.

Safe UI controls:

- view queue
- view runner requests
- approve batch policy
- pause queue
- resume queue
- cancel pending request
- view logs
- view blockers
- view summary

Still risky and deferred:

- raw commit button
- raw push button
- arbitrary shell command button
- UI bypass of delivery safety
- UI direct `.git` write

The UI can become an operator console, but it must call Devo's safety model rather than becoming a second implementation of that model.

## 11. Cleanup And Maintenance

Important later cleanup:

- workspace artifact compaction/indexing
- docs consolidation
- progress/read-model cleanup
- shorter prompt standard
- latest/default queue support
- old dogfood artifact handling

These are important, but they should come after trusted executor and autonomous queue basics. The immediate Phase 2 value is reducing manual intervention while preserving the safety model.

## 12. Phase 2 AI-Agent Boundary

AI agents are later Phase 2, not the first step.

Current Devo already has role contracts, prompts, state, artifacts, and safety gates. Future AI brains can attach to those contracts.

Examples:

- Planner AI
- Architect AI
- Reviewer AI
- QA AI
- Release AI
- local model adapter
- API model adapter
- Codex adapter
- Claude adapter
- Gemini adapter

Do not start with API/model integration. First make the trusted executor and queue loop reliable using the current manual/Codex workflow.

## 13. Recommended Immediate Next Task

Recommended next task: TASK-DEVO-126 Trusted runner watch mode.

It removes the remaining manual `runner-run` command and is the smallest practical step toward zero manual delivery. It also respects the key Phase 2 architecture decision: delivery happens from trusted local Windows user context, while Codex/sandbox prepares bounded requests and evidence.
