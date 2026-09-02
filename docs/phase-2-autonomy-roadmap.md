# Phase 2 Autonomy Roadmap

## Purpose

Phase 2 makes Devo able to run approved batches with minimal human involvement, while preserving safety gates, traceability, review controls, and trusted local delivery.

This is practical autonomy, not reckless full automation. Devo should reduce repeated operator commands only after the work is bounded by approved planning artifacts, validation policy, pause conditions, and delivery safety checks.

Phase 2 should not try to make Codex or a sandboxed worker directly commit or push. Codex/sandbox prepares work, evidence, and runner requests. A trusted local Devo executor running in the normal Windows user context performs delivery.

TASK-DEVO-152 adds an important operating note for real Codex subprocess dogfood: setup, queue-worker preparation, config, and `codex-worker-run-preview` can be prepared from Codex/sandbox, but launching real Codex from inside Codex is recursive/unclear. TASK-DEVO-153 hardens that boundary before another retry by using the real `codex exec -s workspace-write --output-last-message` shape, stdin prompt passing, strict JSON output guidance, and clearer recovery/next-action wording. TASK-DEVO-162 confirms that real Codex batch continuation should still be run from normal PowerShell, one item at a time, with Devo stopping at review and validation gates between items. TASK-DEVO-163 records the resulting readiness checkpoint in `docs/architecture/real-codex-batch-run-readiness-checkpoint.md`, TASK-DEVO-164 proves the same operating mode on a narrow live DevOrchestrator docs-only batch, and TASK-DEVO-165 adds the consolidated read-only batch-position summary. TASK-DEVO-171 adds `docs/architecture/reviewed-patch-apply-design.md`; TASK-DEVO-172 through TASK-DEVO-174 implement the first show/check/apply slices while keeping patch proposals separate from normal review, validation, delivery, and queue completion.

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

Patch-proposal fallback belongs to this same bounded model. A blocked or failed worker may preserve a proposed `.patch` or `.diff`, but that proposal is not completed work. Patch commands now support read-only show, explicit non-mutating check, and explicit reviewed apply. Apply requires a clean worktree, policy-scope checks, dry-run success, operator confirmation, and post-apply review/validation before trusted delivery.

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

### TASK-DEVO-137: Queue-Worker Dogfood Friction Polish

- Goal: Polish the operator friction found in the TASK-DEVO-136 live three-task sandbox dogfood.
- Scope: clearer queue-worker-loop next actions, explicit non-passing validation evidence wording, assisted-policy wording, temp dogfood remote guidance, and runner-watch/latest-request diagnostics.
- Not in scope: real Codex execution, AI/API calls, UI controls, background daemon changes, runner-watch execution from queue-worker-loop, parallel work, or delivery safety bypasses.
- Status: Completed. See `docs/dogfood/task-devo-137-queue-worker-friction-polish.md`.

### TASK-DEVO-138: Polished Assisted Dogfood With Known-Good Delivery

- Goal: Prove the polished assisted queue-worker loop against a disposable project with a real local bare remote and trusted runner delivery.
- Result: Completed. Item 1 moved from worker evidence through review, validation, trusted delivery request, trusted runner delivery, and completion observation. The loop then selected item 2 and stopped safely at `waiting_worker`.
- Follow-up: clarify queue-state completion wording and scheduled runner status when schedule artifacts say enabled but Windows installation is absent.
- Status: Completed. See `docs/dogfood/task-devo-138-polished-assisted-known-good-delivery.md`.

### TASK-DEVO-139: Scheduled Runner Reliability And Health Self-Check

- Goal: Make scheduled trusted runner status reliable before approved queue auto-run depends on it.
- Scope: classify schedule health, detect enabled-metadata/task-missing drift, print repair commands, add read-only `runner-schedule-doctor`, and document direct trusted runner fallback.
- Not in scope: real Codex execution, AI/API calls, UI controls, daemon changes beyond existing schedule commands, direct commit/push, or delivery safety bypasses.
- Status: Completed. See `docs/dogfood/task-devo-139-scheduled-runner-health.md`.

### TASK-DEVO-139A: Scheduler Health Environment Context

- Goal: Clarify when scheduler drift is a real missing task versus a restricted process visibility mismatch.
- Scope: print process user, working directory, task query source/result, environment note, and normal-PowerShell verification guidance for drift.
- Not in scope: scheduler reinstall, approved queue auto-run, real Codex execution, UI controls, or delivery safety changes.
- Status: Completed. See `docs/dogfood/task-devo-139a-scheduler-environment-context.md`.

### TASK-DEVO-140: Approved Queue Auto-Run V1

- Goal: Add one command that continues an approved queue as far as current evidence safely allows.
- Scope: `devo project approved-queue-run --project <project> --policy <POL-ID> --confirm-auto-run`, `--dry-run`, optional `--run`, `--max-cycles`, `--message`, `--note`, and scheduler health gating through the existing trusted runner schedule status.
- Not in scope: real Codex execution, validation execution, runner-watch execution, commit, push, background daemon changes, parallel execution, UI controls, AI/API calls, ECC integration, or delivery safety bypasses.
- Safety rules: preview policy readiness before execution, require explicit confirmation for mutation, stop on unapproved/expired/out-of-scope policy, stop on missing worker/review/validation evidence, stop on non-passing validation, stop on delivery requested or failed delivery, stop on terminal/unknown states, and require healthy scheduler evidence by default before executing mutating queue continuation.
- Status: Completed as a v1 wrapper around the existing one-task-at-a-time queue-worker loop. `--no-require-scheduler-healthy` exists for explicit operator fallback when normal PowerShell health evidence is trusted but the current restricted process cannot see the scheduler.

### TASK-DEVO-141: Worker Result Evidence Schema V1

- Goal: Make worker, review, and validation evidence deterministic enough for `approved-queue-run` to consume safely.
- Scope: shared evidence record fields for evidence id, queue-worker run, queue item/task, type/status, summary, changed files, commands run, artifact path, risks, recommended next action, note, timestamp, and recorder.
- Not in scope: real Codex execution, AI/API calls, validation execution, parallel workers, ECC integration, voice/Jarvis/gesture controls, least-privilege role permissions, or broader autonomous multi-task execution.
- Status: Completed. Existing evidence intake commands now store schema v1 records while older artifacts remain readable and non-success statuses remain non-advancing.

### TASK-DEVO-142: Lightweight Handoff Checklist V1

- Goal: Make the worker boundary clearer before manual/Codex-assisted implementation starts.
- Scope: derive objective, allowed scope, forbidden scope, relevant files, acceptance criteria, required tests, expected worker result fields, risk notes, and next evidence command from existing queue, task, and policy artifacts.
- Not in scope: real Codex-worker execution, a full agent-role contract system, least-privilege role permissions, AI/API calls, parallel workers, or delivery safety bypasses.
- Status: Completed. `queue-worker-handoff-show` is a read-only checklist view, and queue-worker run/show output exposes the same lightweight checklist.

### TASK-DEVO-144: Assisted Queue Recovery And Flow Polish

- Goal: Close the main friction found in TASK-DEVO-143 before broader assisted queue dogfood.
- Scope: push-only trusted runner recovery after successful guarded commit/failed push, `approved-queue-run --continue-next`, clearer validation evidence wording, and latest/default flow-summary behavior.
- Not in scope: real Codex execution, validation execution automation, UI approval/build/test/commit/push controls, parallel workers, AI/API calls, or delivery safety bypasses.
- Status: Completed. `devo delivery runner-recover-push` handles the narrow push-only recovery case, `approved-queue-run --continue-next` starts at most one next eligible item after a specified run completes, and `worker codex flow-summary` / `project flow-summary` can use the uniquely latest queue when `--queue` is omitted.

### TASK-DEVO-145: Codex Worker Launch Integration Design

- Goal: Design the next Codex worker launch/integration layer before implementing new execution behavior.
- Scope: document manual handoff, prompt-file assisted, and future direct Codex CLI subprocess modes; define worker input packages, output contracts, safety preflight checks, runtime guardrails, failure states, ingestion flow, validation/review separation, and trusted-runner-only delivery.
- Not in scope: real Codex execution, AI/API calls, voice/Jarvis/gesture/clap controls, ECC adoption, broad parallel workers, least-privilege implementation, UI delivery controls, direct commit/push, or full autonomous multitask execution.
- Status: Completed as a design-only task. The recommended next step is TASK-DEVO-146: implement prompt-file assisted worker preparation first, then add result ingestion before any direct subprocess retry.

### TASK-DEVO-146: Codex Worker Prepare Prompt-File Mode V1

- Goal: Generate a complete Codex-ready prompt package for exactly one `waiting_worker` queue-worker run.
- Scope: `devo project codex-worker-prepare --project <project> --run <QWR-ID> --confirm-prepare`, preparation show/latest/list helpers, workspace-only prompt package artifacts, JSON and Markdown worker result templates, preflight checks, tests, and docs.
- Not in scope: running Codex, calling Codex Desktop, AI/API calls, result ingest, automatic evidence recording, validation execution, delivery requests, commit, push, UI changes, voice/Jarvis/gesture/clap controls, ECC adoption, parallel workers, least-privilege implementation, or full autonomous multitask execution.
- Status: Completed. Prompt packages are stored under `workspace/projects/<project>/codex-worker/preparations/<CWP-ID>/` and the operator still runs Codex manually before recording worker evidence.

### TASK-DEVO-147: Codex Worker Result Ingest V1

- Goal: Convert a filled JSON worker result file into queue-worker worker evidence schema v1.
- Scope: `devo project codex-worker-ingest --project <project> --run <QWR-ID> --result-file <path> --confirm-ingest`, ingest show/latest/list helpers, dry-run mapping, raw result preservation, preflight checks, tests, and docs.
- Not in scope: running Codex, calling Codex Desktop, AI/API calls, Markdown result parsing, automatic review, validation execution, delivery requests, commit, push, UI changes, voice/Jarvis/gesture/clap controls, ECC adoption, parallel workers, least-privilege implementation, or full autonomous multitask execution.
- Status: Completed. Ingest artifacts are stored under `workspace/projects/<project>/codex-worker/ingests/<CWI-ID>/`, and the next safe step is `approved-queue-run` to continue through review/validation/delivery gates.

### TASK-DEVO-148: Prompt-File Codex Worker Dogfood

- Goal: Prove the prompt-file/manual worker loop on a disposable project before designing direct Codex subprocess execution.
- Scope: disposable Git repo plus local bare remote, `codex-worker-prepare`, manually filled JSON result, `codex-worker-ingest --dry-run`, confirmed ingest, manual review and validation evidence, approved queue continuation, trusted runner delivery request, trusted runner delivery, push-only recovery, and queue completion observation.
- Not in scope: real Codex CLI, Codex Desktop, AI/API calls, PersonalOS, automatic review, automatic validation execution, direct subprocess launch, UI changes, parallel workers, ECC adoption, voice/Jarvis/gesture controls, or delivery safety changes.
- Status: Completed. See `docs/dogfood/task-devo-148-prompt-file-codex-worker-dogfood.md`. Prompt-file worker mode is usable with the small next-action guidance fixes made during the task. Devo is ready for a subprocess execution design checkpoint, but not direct subprocess implementation yet.

### TASK-DEVO-149: Codex Subprocess Execution Design Checkpoint

- Goal: Decide the safest path from proven prompt-file/manual mode toward direct Codex CLI subprocess execution.
- Scope: readiness assessment, subprocess risks, non-goals, narrow v1 command shape, preflight checks, execution model, output artifacts, result handling, states, usage-limit handling, dirty repo handling, scope checking, override model, and implementation sequence.
- Not in scope: real Codex CLI, Codex Desktop, AI/API calls, subprocess dry-run launcher implementation, subprocess execution implementation, automatic review, automatic validation, automatic delivery, UI changes, parallel workers, ECC adoption, voice/Jarvis/gesture controls, least-privilege implementation, or full autonomous multi-task execution.
- Status: Completed as docs/design-only. See `docs/architecture/codex-subprocess-execution-checkpoint.md` and `docs/dogfood/task-devo-149-codex-subprocess-execution-checkpoint.md`. The verdict is ready only for a very narrow one-task subprocess v1.

### TASK-DEVO-150: Codex Subprocess Configuration And Dry-Run Launcher V1

- Goal: Add preview-only subprocess configuration and dry-run command planning before any real Codex launch.
- Scope: `codex-worker-config-show`, `codex-worker-config-set`, `codex-worker-config-validate`, `codex-worker-run-preview`, workspace-only config and preview artifacts, preflight checks, planned command rendering, tests, and docs.
- Not in scope: real Codex CLI, Codex Desktop, AI/API calls, subprocess execution implementation, automatic ingest, automatic review, automatic validation, automatic delivery, UI changes, parallel workers, ECC adoption, voice/Jarvis/gesture controls, least-privilege implementation, or full autonomous multi-task execution.
- Status: Completed. See `docs/dogfood/task-devo-150-codex-subprocess-config-and-dry-run-launcher-v1.md`. The next safe step is TASK-DEVO-151: one-task Codex subprocess execution v1, still narrow and explicitly gated.

### TASK-DEVO-151: One-Task Codex Subprocess Execution V1

- Goal: Run one configured subprocess for one approved `waiting_worker` queue-worker run after explicit confirmation.
- Scope: `codex-worker-run`, fake-command tests, stdout/stderr/exit-code capture, Git before/after capture, workspace-only run artifacts, result-state classification, timeout handling, usage-limit warning hints, lightweight scope warnings, and docs.
- Not in scope: real Codex dogfood during implementation, Codex Desktop, AI/API calls, automatic ingest, automatic review, automatic validation, automatic delivery, commit, push, UI changes, parallel workers, ECC adoption, voice/Jarvis/gesture controls, least-privilege implementation, or full autonomous multi-task execution.
- Status: Completed. See `docs/dogfood/task-devo-151-one-task-codex-subprocess-execution-v1.md`. The next safe step is TASK-DEVO-152: real Codex subprocess dogfood for one safe disposable task.

### TASK-DEVO-152 And TASK-DEVO-153: Real Codex Dogfood Boundary

- Goal: Prepare one disposable real Codex subprocess dogfood and harden the command/output boundary before retrying.
- Scope: disposable `Dogfood152` setup through preview, normal-PowerShell launch guidance, real Codex CLI default args, stdin prompt passing, strict JSON output guidance, BOM-tolerant ingest, completed queue-worker output cleanup, validation evidence label clarity, and disposable manual-runner scheduler-gate guidance.
- Not in scope: batch Codex worker loop, automatic retry, automatic ingest/review/validation/delivery, UI actions, PersonalOS, AI/API calls, parallel workers, or delivery safety weakening.
- Status: TASK-DEVO-152 reached preview and TASK-DEVO-153 completed hardening. The next safe step is a normal-PowerShell real Codex subprocess continuation only from a safe launcher/context.

### TASK-DEVO-154: Batch Codex-Worker Loop Design

- Goal: Design how Devo should process multiple approved queue items with Codex subprocess execution while keeping v1 one-task-at-a-time and evidence-gated.
- Scope: `docs/architecture/codex-worker-batch-loop-design.md`, proposed `codex-worker-batch-run` command shape, state machine, stop conditions, retry/resume behavior, safety gates, evidence requirements, trusted-runner delivery behavior, scheduler/manual-runner behavior, expected artifacts, CLI UX examples, out-of-scope boundaries, and TASK-DEVO-155 acceptance criteria.
- Not in scope: implementation, real Codex execution, batch worker automation, parallel workers, automatic review, automatic validation, UI actions, AI/API calls, PersonalOS, scheduler modification, or delivery safety weakening.
- Status: Completed as design-only. TASK-DEVO-155 implemented the smallest fake-tested v1 around existing one-task primitives.

### TASK-DEVO-155: Batch Codex-Worker Loop V1

- Goal: Add the first safe command that coordinates one approved queue item through the Codex worker subprocess path.
- Scope: `devo project codex-worker-batch-run --project <project> --policy <POL-ID> --confirm-codex-batch-run`, `--dry-run`, scheduler health gating by default, queue-worker selection, Codex prompt preparation, one configured subprocess run, strict JSON ingest, batch-run artifacts, and stop-at-review behavior.
- Not in scope: real Codex execution during implementation, parallel workers, multiple items per invocation, automatic review, automatic validation, automatic delivery, trusted runner execution, commit, push, queue completion, UI controls, AI/API calls, PersonalOS, scheduler mutation, or delivery safety weakening.
- Status: Completed. V1 is capped to one item and one cycle, uses fake-worker tests for subprocess outcomes, writes artifacts under `workspace/projects/<project>/codex-worker/batch-runs/<CWBR-ID>/`, and stops on missing/invalid JSON, failed process, timeout, usage-limit, scope warning/violation, scheduler unhealthy, policy drift, dirty repo, no eligible item, or the worker review gate.

### TASK-DEVO-156: Batch-Run Fake Worker Dogfood

- Goal: Prove `codex-worker-batch-run` on a disposable project before using it for live Devo or PersonalOS work.
- Scope: disposable `Dogfood156`, three small note-file tasks, approved execution policy, fake Python subprocess worker, dry-run, confirmed one-item execution, strict JSON ingest, manual review evidence, manual validation evidence, and trusted delivery request creation.
- Not in scope: real Codex CLI, PersonalOS, parallel workers, automatic review, automatic validation, automatic trusted runner execution, direct worker commit/push, source feature work, UI actions, or delivery safety weakening.
- Status: Completed with a delivery-readiness caveat. The core path passed and is documented in `docs/dogfood/task-devo-156-batch-run-fake-worker-dogfood.md`; the disposable trusted runner was not executed because the sandbox-local temp repo lacked a working upstream after a local bare push failure. TASK-DEVO-157 polishes that operator friction.

### TASK-DEVO-157: Batch-Run Dogfood Polish And Disposable Delivery Readiness

- Goal: Make the TASK-DEVO-156 caveat easier to avoid before broader batch-run dogfood.
- Scope: disposable repo setup guidance, local bare remote/upstream checklist, clearer no-upstream delivery warnings, and `execution-policy-create` changed-file-limit discoverability.
- Not in scope: real Codex batch dogfood, parallel workers, UI actions, PersonalOS, AI/API calls, scheduler mutation, backup/restore, delivery safety weakening, or manual Git delivery.
- Status: Completed. Disposable projects should verify `git branch -vv` and `git remote -v` after an initial `git push -u origin main`; no-upstream delivery requests are still allowed when policy permits, but now warn that trusted runner push may block or fail until an upstream push target exists.

### TASK-DEVO-158: Real Codex Batch-Run One-Item Dogfood

- Goal: Prove `codex-worker-batch-run` with a real Codex subprocess on exactly one disposable queue item.
- Scope: disposable `Dogfood158`, one task `T001`, allowed file `dogfood-note.md`, real Codex launched from normal PowerShell, strict JSON result ingest, manual review evidence, manual validation evidence, Devo delivery request, trusted runner commit/push, and clean final disposable repo.
- Not in scope: PersonalOS, DevOrchestrator source edits by Codex, parallel workers, automatic review, automatic validation, direct Codex commit/push, UI actions, scheduler mutation, backup/restore, or larger batch execution.
- Status: Completed with PASS verdict. Commit `3eff3c36515063a65de6283032364e2df467b540` was pushed to the disposable local bare remote.

### TASK-DEVO-159: Real Codex Batch-Run Polish

- Goal: Polish the readout friction found during Dogfood158 before expanding real Codex batch dogfood.
- Scope: reduce false-positive `usage_limit_detected` warnings from echoed schema/prompt text after successful completed results, label validation evidence as shared queue-worker evidence artifacts, tighten completed trusted-delivery next actions, and update docs.
- Not in scope: real Codex execution, PersonalOS, parallel workers, automatic review, automatic validation, automatic delivery, direct Codex commit/push, UI actions, scheduler mutation, backup/restore, or larger batch execution.
- Status: Completed. TASK-DEVO-160 and TASK-DEVO-162 later proved continuation with fake and real workers while keeping one item at a time.

### TASK-DEVO-160: Multi-Item Fake-Worker Batch Continuation Dogfood

- Goal: Prove `codex-worker-batch-run` can continue from completed item 1 to item 2 and item 3 before spending real Codex usage on a larger continuation run.
- Scope: disposable `Dogfood160`, three docs-only note tasks, fake Python worker subprocess, one item per batch-run invocation, manual review and validation evidence, trusted delivery requests, trusted runner commit/push, and final queue completion.
- Not in scope: real Codex execution, PersonalOS, parallel workers, automatic review, automatic validation, direct worker commit/push, UI actions, scheduler mutation, backup/restore, or larger real batch execution.
- Status: Completed with PASS verdict. All three queue items completed and pushed. TASK-DEVO-161 should polish stale retry/run selection and completed-queue next-action wording found during the dogfood.

### TASK-DEVO-161: Batch Continuation Friction Polish

- Goal: Fix the narrow continuation friction found in TASK-DEVO-160 without changing the conservative one-item-at-a-time architecture.
- Scope: stale active queue-worker run selection, retry worker-run linkage, completed-queue/no-ready wording, push-only recovery guidance, and generated prompt guidance for fake/scripted worker task selection.
- Not in scope: real Codex execution, parallel workers, UI actions, PersonalOS, automatic review/validation/delivery, direct worker commit/push, scheduler mutation, or backup/restore.
- Status: Completed. TASK-DEVO-162 later rechecked the continuation path with real Codex on disposable `Dogfood162`.

### TASK-DEVO-162: Real Codex Multi-Item Batch Dogfood

- Goal: Prove real `codex-worker-batch-run` continuation across two disposable queue items.
- Scope: disposable `Dogfood162`, two docs-only note tasks, real Codex subprocess execution from normal PowerShell, strict JSON ingest, manual review and validation evidence, trusted delivery requests, trusted runner commit/push, and final completed queue guidance.
- Not in scope: PersonalOS, parallel workers, automatic review, automatic validation, direct Codex commit/push, UI actions, scheduler mutation, backup/restore, or real-project batch execution.
- Status: Completed with PASS verdict. See `docs/dogfood/task-devo-162-real-codex-multi-item-batch-dogfood.md`.

### TASK-DEVO-163: Real Codex Batch-Run Readiness Checkpoint

- Goal: Document what is safe after TASK-DEVO-162 and what remains manual-gated.
- Scope: readiness checkpoint, operating mode, docs polish, and conservative next-task guidance.
- Not in scope: real Codex execution, parallel workers, UI actions, PersonalOS, automatic review/validation/delivery, direct worker commit/push, scheduler mutation, or backup/restore.
- Status: Completed. See `docs/architecture/real-codex-batch-run-readiness-checkpoint.md`.

### TASK-DEVO-164: DevOrchestrator Real Batch-Run Narrow Internal Dogfood

- Goal: Prove real `codex-worker-batch-run` on the live DevOrchestrator repo with a tiny docs-only policy.
- Scope: two docs-only queue items, real Codex subprocess execution from normal PowerShell, strict JSON ingest, manual review, manual validation, trusted delivery requests, trusted runner commits, and final all-completed batch guidance.
- Not in scope: PersonalOS, source-code feature work, parallel workers, automatic review/validation, direct Codex commit/push, UI actions, scheduler mutation, or backup/restore.
- Status: Completed with PASS verdict. `QI001/T001/QWR-0001` delivered `REQ-0052` commit `f9360f7`; `QI002/T002/QWR-0002` delivered `REQ-0053` commit `3b6c44d`; final `CWBR-0004` reported all allowed queue items completed.

### TASK-DEVO-165: Consolidated Real-Batch Position Summary

- Goal: Reduce operator artifact-joining overhead without widening autonomy.
- Scope: read-only `devo project codex-worker-batch-summary --project <project> --policy <POL-ID>`, item-by-item policy/queue/worker/Codex/evidence/delivery/runner/commit/push summary, one safe next command, and terminal all-completed guidance.
- Not in scope: real Codex execution, queue mutation from the summary command, review/validation recording, delivery request creation, runner execution, commit, push, UI, parallel workers, or PersonalOS.
- Status: Completed. Use the summary before rerunning batch commands when the operator needs to know exactly where a policy stands.

### TASK-DEVO-166: Real Batch Summary Dogfood

- Goal: Prove `codex-worker-batch-summary` against completed live DevOrchestrator policy `POL-0002`.
- Scope: read-only dogfood, docs report, and tiny summary selection polish so completed items prefer evidence-bearing Codex batch-run artifacts over redundant no-subprocess boundary runs.
- Not in scope: real Codex execution, queue mutation, review/validation recording, delivery request creation by the summary, runner execution, commit, push, UI, parallel workers, or PersonalOS.
- Status: Completed with PASS verdict. The summary reports both completed queue items, `QWR-0001` and `QWR-0002`, productive Codex batch/worker/ingest IDs, review/validation evidence, delivery requests `REQ-0052` and `REQ-0053`, pushed commits, and terminal no-action guidance.

### TASK-DEVO-167/TASK-DEVO-168: Real Code Batch-Run Write-Access Blocker

- Goal: Attempt the first narrow real Codex code-task batch-run on live DevOrchestrator and harden the blocked-result guidance.
- Scope: one approved source/test policy, blocked-result dogfood report, write-access diagnostics runbook, and safer next-action text for blocked worker evidence.
- Not in scope: real Codex retry from Codex/sandbox, PersonalOS, automatic review, automatic validation, automatic delivery, direct Codex commit/push, UI, parallel workers, dangerous sandbox bypasses, or automatic patch application.
- Status: TASK-DEVO-167 blocked safely. Real Codex produced strict JSON twice but could not update existing approved files even though it could inspect them. TASK-DEVO-168 documents the finding and points blocked write-access states toward diagnosis or future patch-proposal fallback before retry/review/validation/delivery.

### TASK-DEVO-169: Patch-Proposal Fallback V1

- Goal: Preserve useful worker implementation intent when source writes are blocked without widening autonomy.
- Scope: worker-result ingest metadata, consolidated batch-summary guidance, prompt-package instructions, write-access diagnostics docs, and focused fake-worker tests.
- Not in scope: automatic patch apply, dangerous sandbox bypass, automatic review, automatic validation, delivery creation, trusted runner execution, UI, real Codex execution, or PersonalOS.
- Status: Completed. Blocked/failed worker JSON can now carry `patch_proposal_present` plus `patch_artifact_path` or a `.patch`/`.diff` `artifact_path`; Devo surfaces the proposal while keeping the result non-successful and telling the operator to review it manually before any normal review/validation/delivery gates.

### TASK-DEVO-170: Patch-Proposal Fallback Dogfood

- Goal: Prove patch-proposal fallback v1 with fake blocked worker evidence before adding any patch-apply flow.
- Scope: `POL-0003`, retry run `QWR-0005`, fake blocked result JSON, `.patch` artifact, ingest/evidence/summary readout check, dogfood report, and tiny evidence-output wording polish.
- Not in scope: real Codex execution, patch application, normal review/validation/delivery for patch-only evidence, trusted runner delivery for the fake worker item, UI, parallel workers, or PersonalOS.
- Status: Completed with PASS verdict. `codex-worker-ingest`, `queue-worker-evidence`, and `codex-worker-batch-summary` show the patch proposal path while keeping the worker result blocked and telling the operator not to record normal review/validation/delivery until changes are actually applied and validated.

### TASK-DEVO-172: Patch-Proposal Show/Check V1

- Goal: Make patch proposals inspectable and checkable before any patch apply command exists.
- Scope: `patch-proposal-show`, explicit `patch-proposal-check --confirm-check`, workspace-only check artifacts, read-model summary, focused tests, and docs.
- Not in scope: patch application, queue completion, normal review/validation evidence, delivery creation, trusted runner execution, real Codex execution, UI, parallel workers, or PersonalOS.
- Status: Completed. Operators can now inspect patch proposal evidence and run a non-mutating check that enforces blocked/failed evidence status, clean worktree, policy allowed/forbidden file scope, safe patch paths, and `git apply --check`.

### TASK-DEVO-173: Patch-Proposal Show/Check Dogfood

- Goal: Prove `patch-proposal-show` and `patch-proposal-check` against existing fake blocked patch evidence before any patch apply command exists.
- Scope: `QWR-0005`, `POL-0003`, the TASK-DEVO-170 `.patch` artifact, show/check/summary readouts, dogfood report, and one small summary recommended-command polish.
- Not in scope: real Codex execution, patch application, queue completion, normal review/validation evidence, delivery creation, trusted runner execution, UI, parallel workers, or PersonalOS.
- Status: Completed with PASS verdict. Show finds the proposal and read-only safety guidance, check writes only a workspace artifact and blocks the older non-applyable proposal, and batch summary now recommends `patch-proposal-show` for patch-only evidence. TASK-DEVO-174 follows this with explicit reviewed apply.

### TASK-DEVO-174: Reviewed Patch-Proposal Apply V1

- Goal: Add the first explicit, human-confirmed apply command for a previously checked patch proposal.
- Scope: `patch-proposal-apply`, apply audit artifacts, policy/path/hash rechecks, read-model summary, focused tests, and docs.
- Not in scope: real Codex execution, automatic patch apply from batch-run, queue completion, normal review/validation evidence, delivery creation, trusted runner execution by apply, UI, parallel workers, or PersonalOS.
- Status: Completed. Apply requires `--reviewed-by`, `--confirm-apply-patch`, a clean worktree, blocked/failed worker evidence, a present patch proposal, and a latest successful matching check artifact. It applies the patch to the working tree only, leaves files unstaged, writes an audit artifact, and tells the operator to inspect the diff, validate, then record normal evidence before delivery.

### TASK-DEVO-175: Patch-Proposal Apply Dogfood

- Goal: Prove reviewed apply with a fake safe patch before live source-code use.
- Scope: one docs-only policy, fake blocked worker result, valid unified diff proposal, show/check/apply commands, dogfood report, focused summary/check wording polish, and focused tests.
- Not in scope: real Codex execution, automatic patch apply from batch-run, queue completion by apply, normal review/validation evidence by apply, delivery creation by apply, direct commit/push, UI, parallel workers, or PersonalOS.
- Status: Completed. `patch-proposal-apply` applies the checked dogfood report patch to the working tree only, leaves files unstaged, preserves blocked queue/review/validation/delivery state, and the summary now surfaces apply artifacts plus the post-apply evidence next action.

### TASK-DEVO-176: Real Codex Patch-Proposal Materialization

- Goal: Preserve useful real Codex patch intent when a worker returns the proposal inline in JSON instead of as a `.patch` artifact path.
- Scope: confirmed ingest-time materialization of inline patch text, show/check compatibility, focused tests, and dogfood documentation for `POL-0005` / `QWR-0007`.
- Not in scope: real Codex rerun, automatic patch apply, queue completion, normal review/validation evidence from patch-only output, delivery creation from patch-only output, direct commit/push, UI, parallel workers, or PersonalOS.
- Status: In progress. The first real fallback run produced blocked evidence with an inline patch proposal and no artifact path. Future confirmed ingests now materialize inline patch text under `workspace/projects/<project>/planning/patch-proposals/artifacts/<QWR-ID>/<CWI-ID>.patch`; patch-only evidence remains blocked until an operator checks, applies, reviews, validates, and delivers through the normal gates.

### TASK-DEVO-177: Real Codex Inline Patch Contract Retry

- Goal: Give real Codex an explicit allowed JSON field for inline patch text when it cannot write files or create a patch artifact.
- Scope: generated prompt/result template contract, canonical `patch_proposal_text` ingest materialization, focused tests, and dogfood report for `POL-0005` / `QWR-0008`.
- Not in scope: real Codex rerun from Codex/sandbox, patch apply, queue completion, normal review/validation evidence from patch-only output, delivery creation from patch-only output, direct commit/push, UI, parallel workers, or PersonalOS.
- Status: In progress. The retry showed the exact field list only exposed `patch_proposal_present` and `patch_artifact_path`, so the worker had no canonical inline patch field. The prompt/template now include `patch_proposal_text`, and ingest materializes that field into a workspace `.patch` artifact while preserving blocked/failed status.

### TASK-DEVO-178: Real Codex Inline Patch Compatibility

- Goal: Prove the `patch_proposal_text` fallback end to end and tighten the contract when the first real inline patch is not applyable.
- Scope: generated prompt/result contract wording, corrupt-patch check guidance, focused tests, and dogfood report for `POL-0005` / `QWR-0009`.
- Not in scope: running real Codex from Codex/sandbox, manually applying patches, automatic patch apply, queue completion, normal review/validation evidence from invalid patch-only output, delivery creation from invalid patch-only output, direct commit/push, UI, parallel workers, or PersonalOS.
- Status: In progress. Real Codex returned blocked evidence with `patch_proposal_text`, and Devo materialized it into a workspace `.patch`; `patch-proposal-check` blocked safely because `git apply --check` reported a corrupt patch. The prompt/check guidance now requires complete git-apply-compatible unified diffs and recommends a fresh worker result for corrupt patches.

### TASK-DEVO-179: Whitespace-Tolerant Patch Check/Apply

- Goal: Add explicit audited check/apply mode for materialized patches that fail strict `git apply` but pass Git whitespace-tolerant diagnostics.
- Scope: `--ignore-whitespace --confirm-ignore-whitespace` flags for `patch-proposal-check` and `patch-proposal-apply`, artifact fields for patch apply mode and git args, same-run/same-hash/same-mode apply gating, focused tests, and dogfood report for `POL-0005` / `QWR-0010`.
- Not in scope: automatic fallback, applying the real `QWR-0010` patch in this implementation task, real Codex rerun from Codex/sandbox, normal evidence/delivery from patch-only output, direct commit/push, UI, parallel workers, or PersonalOS.
- Status: In progress. Strict remains the default; whitespace-tolerant mode is explicit, non-mutating for check, working-tree-only for apply, and audited in artifacts.

### Future Spikes

- Compare Devo architecture against ECC / Everything Claude Code as a benchmark only; do not copy ECC or make Devo Claude-Code-only.
- Evaluate small controlled parallel read-only review workers later; do not add "300 agents" or parallel editing agents now.
- Consider least-privilege role permissions after real worker roles exist.
- Keep Devo text-driven for now; no current plan for voice, Jarvis, hand gesture, or clap-triggered operation.

### TASK-DEVO-135: Queue-Worker Evidence Intake

- Goal: Make it easier to feed manual worker, review, and validation evidence back into the queue-worker loop.
- Why it matters: The loop was safe but still required operators to remember lower-level worker report/review commands between stops.
- Scope: `devo project queue-worker-record-worker-result`, `queue-worker-record-review`, `queue-worker-record-validation`, clearer next actions, and clearer draft/unapproved policy output.
- Not in scope: real Codex execution, AI/API calls, validation execution, automatic review, runner-watch execution, commit, push, UI controls, background daemons, parallel work, or autonomous multi-task execution.
- Safety rules: record commands only write workspace evidence for an existing queue-worker run and require `--confirm-record`; the loop remains responsible for state transitions.
- Status: Completed. Evidence intake is now explicit and easier to pair with `queue-worker-loop`.

### TASK-DEVO-136: Live Three-Task Assisted Dogfood

- Goal: Try the current assisted queue-worker flow against a real temp/sandbox three-task batch.
- Result: Partial. Item 1 reached worker-result, review, validation, and trusted delivery request creation. The temp trusted runner commit succeeded, but guarded push failed with a Windows/Git shell permission error, so the loop correctly refused to continue to item 2.
- Follow-up: polish confusing stop/next-action text and document or improve temp trusted delivery setup before broader 3-5 task use.

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

Recommended next task: TASK-DEVO-152 Real Codex subprocess dogfood for one safe disposable task.

TASK-DEVO-149 documented the subprocess checkpoint. TASK-DEVO-150 implemented configuration and dry-run launcher behavior only, using fake-executable tests and preserving launcher readiness, explicit operator approval, clear result-file contracts, timeout/usage-limit planning, and trusted-runner-only delivery. TASK-DEVO-151 implemented the first narrow fake-tested execution step and still avoids automatic ingest, review, validation, delivery, commit, or push. TASK-DEVO-152 prepared real Codex dogfood on one disposable task through preview, and TASK-DEVO-153 hardens the command/output/recovery boundary before another normal-PowerShell retry.
