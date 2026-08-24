# TASK-DEVO-143 Approved Queue Run Dogfood

## Dogfood Goal

Run a small end-to-end Phase 2 assisted queue automation dogfood using current Devo tools without adding new features.

The target workflow was:

```text
intake/status
-> planning state review
-> batch/queue/handoff readiness
-> approved queued docs-only tasks
-> worker evidence
-> review evidence
-> validation evidence
-> delivery request
-> trusted runner delivery
-> Devo detects completion
-> next queue item starts
```

This dogfood used disposable temp repositories only. It did not modify PersonalOS, run PersonalOS commands, run real Codex CLI, call model APIs, run backup/restore, modify scheduler state, add UI controls, or bypass Devo safety gates.

## Commands Run

DevOrchestrator readiness:

```powershell
git status --short
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-status --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-doctor --project DevOrchestrator
```

Operator intake and planning observations:

```powershell
.\.venv\Scripts\devo.exe project intake-status --project DevOrchestrator
.\.venv\Scripts\devo.exe project intake-next --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe project progress --project DevOrchestrator
.\.venv\Scripts\devo.exe work list --project DevOrchestrator
.\.venv\Scripts\devo.exe worker codex flow-summary --project DevOrchestrator
.\.venv\Scripts\devo.exe worker codex flow-summary --project DevOrchestrator --queue Q003
```

Disposable dogfood project setup used `project add`, `brief-create`, `brief-approve`, `blueprint-create`, `blueprint-approve`, `backlog-validate`, `backlog-import`, `backlog-approve`, `batch-create`, `batch-approve`, `queue-create`, `execution-policy-create`, `execution-policy-request`, and `execution-policy-approve`.

For each delivered task, the loop used:

```powershell
.\.venv\Scripts\devo.exe project approved-queue-run --project Dogfood143B --policy POL-0001 --confirm-auto-run --no-require-scheduler-healthy
.\.venv\Scripts\devo.exe project queue-worker-handoff-show --project Dogfood143B --run <QWR-ID>
git -C .\pt-143-dogfood-b\work diff --check
.\.venv\Scripts\devo.exe project queue-worker-record-worker-result --project Dogfood143B --run <QWR-ID> --status completed --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-review --project Dogfood143B --run <QWR-ID> --status passed --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-validation --project Dogfood143B --run <QWR-ID> --status passed --confirm-record
.\.venv\Scripts\devo.exe delivery runner-run --project Dogfood143B --request <REQ-ID> --approver "Manas" --confirm-runner-delivery
```

## Current Intake And Status Result

`devo project intake-status --project DevOrchestrator` reported:

- Brief: approved
- Blueprint: approved
- Backlog: approved
- Tasks: total 1, ready 0, blocked 1
- Batches: total 3, latest B003, approved
- Queues: total 3, latest Q003, waiting_review
- Handoffs: total 3, latest H003, draft
- Next action: use the latest Codex handoff or create a worker run from it

`devo project intake-next --project DevOrchestrator` returned the same concise next action.

`devo project progress --project DevOrchestrator` showed the old real-Codex dry-run path as blocked. That is accurate, but it can make project-level progress look unhealthy even while a separate dogfood path is safe to run.

`devo worker codex flow-summary --project DevOrchestrator` failed safely because `--queue` is required. The corrected command with `--queue Q003` worked and showed queue Q003 waiting on a rejected/failed worker-review path.

## Dogfood Execution Result

The successful disposable dogfood project was `Dogfood143B`, backed by:

- Work repo: `E:\DevOrchestrator\pt-143-dogfood-b\work`
- Local bare remote: `E:\DevOrchestrator\pt-143-dogfood-b\remote.git`
- Queue: Q001
- Policy: POL-0001
- Approved batch: B001

Three queue items were completed end to end:

- QWR-0001 / REQ-0001: updated `dogfood-note.md`, committed and pushed `e02b2ab8ebb5fcc85bb71c8928e4ddfafe50c2fa`
- QWR-0002 / REQ-0002: updated `dogfood-checklist.md`, committed and pushed `11d8f871b7f932648c2a024c87a94e4b38c299fd`
- QWR-0003 / REQ-0003: updated `dogfood-summary.md`, committed and pushed `c4075f00edba2b7e9f549adcba23997fdd8777aa`

After QWR-0003 delivery, `approved-queue-run` detected the completed trusted delivery and a subsequent auto-select started QWR-0004 at `waiting_worker`. That proves the intended continuation behavior:

```text
completed delivery -> Devo observes completion -> next queue item starts -> stop at worker evidence
```

## What Worked Well

- `approved-queue-run` gives a good policy-first wrapper around the queue-worker loop.
- `queue-worker-handoff-show` is a strong worker boundary artifact. It clearly lists objective, allowed files, forbidden scope, acceptance criteria, required validation, evidence shape, and record command.
- The evidence intake commands are easy to use and preserve the manual/assisted safety model.
- Trusted runner delivery works for the disposable project when run from a normal-permission context.
- Devo correctly stops at each evidence gate, at pending delivery, and at the next worker boundary.
- Devo detected completed runner requests and marked queue-worker runs completed.
- Auto-select can start the next pending queue item after the previous run is completed.

## What Felt Too Manual

- A complete item still needs several repeated commands: worker result, loop, review, loop, validation, loop, runner-run, loop again, auto-select again.
- `approved-queue-run --max-cycles 1` can stop one step before delivery request creation; `--max-cycles 2` is more ergonomic after validation evidence.
- After a specified run completes, Devo does not automatically start the next queue item. Running `approved-queue-run` again without `--run` does start the next item, but the user has to know that pattern.
- The validation evidence command output writes to review artifact paths, which is confusing even though the evidence state becomes `passed`.
- Backlog import printed `Ready: 0`, while backlog approval correctly showed `Ready: 5`.
- `flow-summary` requires a queue id; defaulting to latest/current queue would reduce command friction.

## Blockers And Friction

The first disposable attempt, `Dogfood143`, exposed a real partial-delivery recovery gap:

- The trusted runner created the guarded commit for REQ-0001.
- The push failed in the Codex/sandbox context with a Git-for-Windows shell permission error.
- A normal-permission retry of `runner-run` then blocked because the working tree no longer matched the original request snapshot.
- `delivery report-refresh` correctly refused to reopen because a commit hash already existed.
- `delivery push-preview` and guarded `delivery push` still blocked because the report status was `failed`, not `committed`.

This did not affect DevOrchestrator source delivery, but it is worth preserving as a future recovery-polish item: Devo needs a safe way to resume push-only delivery after a runner commit succeeds but push fails.

The successful second dogfood avoided that issue by running the trusted runner from the normal-permission context for each request.

## Phase Readiness Verdict

Verdict: Phase 2 assisted queue automation is usable for personal low-risk batches with an operator in the loop.

The current tools are ready for controlled small batches when:

- the batch and execution policy are approved
- the handoff checklist is inspected before work
- worker/review/validation evidence is recorded explicitly
- trusted delivery is run from the normal local user context
- the queue is advanced one item at a time

This is not full autonomy yet. The workflow is safe and understandable, but still command-heavy.

## Recommended Next Task

Recommended next task:

```text
TASK-DEVO-144: Polish assisted queue continuation after dogfood
```

Suggested scope:

- add clearer next action after a specified queue-worker run completes
- consider an explicit "start next item" hint
- fix confusing validation evidence artifact wording if it is just output text
- document partial commit/push recovery as a known delivery-runner gap
- keep all changes small and safety-preserving

## Delivery Runner Request Evidence

Successful disposable runner requests:

- `Dogfood143B` REQ-0001 completed and pushed commit `e02b2ab8ebb5fcc85bb71c8928e4ddfafe50c2fa`
- `Dogfood143B` REQ-0002 completed and pushed commit `11d8f871b7f932648c2a024c87a94e4b38c299fd`
- `Dogfood143B` REQ-0003 completed and pushed commit `c4075f00edba2b7e9f549adcba23997fdd8777aa`

The final DevOrchestrator docs delivery should use the normal trusted runner request flow:

```powershell
.\.venv\Scripts\devo.exe delivery runner-request --project DevOrchestrator --message "docs: dogfood approved queue run" --note "TASK-DEVO-143 assisted queue auto-run dogfood."
```
