# TASK-DEVO-123 Phase 1 End-To-End Dogfood

## 1. Dogfood Goal

Prove the current Devo Phase 1 workflow from operator status intake through trusted delivery on DevOrchestrator itself.

This was intentionally a small docs/report dogfood. It did not add features, run real Codex CLI, touch PersonalOS, run backup/restore, weaken delivery safety, or create fake planning artifacts.

Target workflow:

```text
intake/status
-> planning state review
-> batch/queue/handoff readiness
-> small docs-only dogfood change
-> validation
-> runner request
-> one-command trusted local delivery
```

## 2. Commands Run

Initial state and delivery context:

```powershell
git status --short --branch
git log --oneline -n 5
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
```

Dogfood observation commands:

```powershell
.\.venv\Scripts\devo.exe project intake-status --project DevOrchestrator
.\.venv\Scripts\devo.exe project intake-next --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe project progress --project DevOrchestrator
.\.venv\Scripts\devo.exe work list --project DevOrchestrator
.\.venv\Scripts\devo.exe worker codex flow-summary --project DevOrchestrator
.\.venv\Scripts\devo.exe worker codex flow-summary --project DevOrchestrator --queue Q003
.\.venv\Scripts\devo.exe project handoff-show --project DevOrchestrator --handoff H003
.\.venv\Scripts\devo.exe project queue-show --project DevOrchestrator --queue Q003
```

Validation commands:

```powershell
git diff --check
git diff --cached --check
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
```

Delivery request command:

```powershell
.\.venv\Scripts\devo.exe delivery runner-request --project DevOrchestrator --message "docs: dogfood phase 1 end-to-end workflow" --note "TASK-DEVO-123 end-to-end Phase 1 dogfood."
```

## 3. Current Intake/Status Result

`devo project intake-status --project DevOrchestrator` worked and gave a compact whole-pipeline view:

- Brief: `approved`
- Blueprint: `approved`
- Backlog: `approved`
- Tasks: total `1`, ready `0`, blocked `1`
- Batches: total `3`, latest `B003`, status `approved`, approval `approved`
- Queues: total `3`, latest `Q003`, status `waiting_review`
- Handoffs: total `3`, latest `H003`, status `draft`
- Progress: project `0.0%`, backlog readiness `0.0%`, blocked `100.0%`
- Next action: use the latest Codex handoff or create a worker run from it
- Suggested command: `devo worker codex run-create --project DevOrchestrator --handoff H003`

`devo project intake-next --project DevOrchestrator` correctly printed the same next action without the extra status detail.

## 4. Planning, Batch, Queue, And Handoff Observations

`devo project progress --project DevOrchestrator` showed that the old real-Codex dry-run planning path is still present but blocked:

- one active task, `T001`
- task status is blocked
- milestone `M001` and epic `E001` both show blocked progress
- latest batch `B003` is approved
- the generic progress next action says an approved planning batch is ready for queue or batch handoff

`devo project queue-show --project DevOrchestrator --queue Q003` gave the more precise current execution state:

- queue `Q003` is `waiting_review`
- current item `QI001` is `blocked`
- linked worker run is `WR002`
- worker review status is `rejected`
- validation evidence status is `failed`
- completion readiness is `no`
- the resume hint says to review the blocked item and generate a new handoff only after the blocker is resolved

`devo worker codex flow-summary --project DevOrchestrator` failed safely because `--queue` is required. The corrected command, `devo worker codex flow-summary --project DevOrchestrator --queue Q003`, worked and summarized the queue -> handoff -> worker -> review state:

- queue `Q003` status: `waiting_review`
- item `QI001` status: `blocked`
- handoff `H003`
- worker run `WR002` status: `failed`
- run plan `RP003` status: `ready`, preflight `passed`
- report: `failed`
- review: `rejected`, validation `failed`
- completion ready: `no`

`devo project handoff-show --project DevOrchestrator --handoff H003` confirmed the latest handoff exists and is still a draft prompt for `T001: No-op supervised Codex docs-inspection dry-run`.

## 5. What Worked Well

- `intake-status` is the best new first command. It answers where the project is in the planning pipeline without requiring manual folder inspection.
- `intake-next` is useful when the operator only needs the next command.
- `delivery latest` is now a strong recovery/status command: it showed the last pushed delivery, runner state, commit hash, push result, and no pending delivery work before this task.
- `runner-latest` makes it easy to see that the previous runner request completed and pushed.
- `queue-show` and corrected `flow-summary --queue Q003` made the blocked worker state clear without running Codex or mutating queue state.
- Trusted runner delivery remains the right end step for Codex/sandbox work.

## 6. What Felt Too Manual

- The operator still needs to know when to switch from `intake-status` to `queue-show`, `handoff-show`, or `flow-summary`.
- `worker codex flow-summary` requires a queue id, but the requested command omitted it. The CLI failure was clear, but a future `--latest` or current-queue default would reduce friction.
- `project progress` and `intake-status` disagree in emphasis: progress says the approved batch is ready, while queue state says the current queue is blocked. Both are true, but the operator needs queue-aware guidance to avoid picking the wrong next step.
- Dogfood delivery still requires remembering that the runner request id cannot be committed into the report without changing the expected file snapshot.

## 7. Blockers Or Friction

No blocker prevents Phase 1 checkpoint work.

Friction found:

- `flow-summary` needs `--queue`; a queue-default shortcut would help.
- Progress next-action text is planning-oriented and does not account for blocked queue/review state.
- Some old planning artifacts from the real Codex dry-run make current progress look unhealthy even though the current docs-only dogfood can proceed independently.

None of these justify new feature work before TASK-DEVO-124. They should be captured as post-checkpoint polish.

## 8. Phase 1 Checkpoint Readiness

Phase 1 is ready for the final checkpoint task.

Reasoning:

- project intake/status is understandable
- planning, queue, handoff, worker, review, delivery, and runner states are inspectable
- blocked worker state is visible and not accidentally completed
- docs-only changes can be delivered through the trusted runner path
- safety gates remain intact
- no Phase 2 automation is required to operate the workflow

The main caution from TASK-DEVO-122 remains valid: Devo should pause new features and checkpoint the current working system before adding Phase 2 intelligence.

## 9. Recommended Final Task

Recommended next task:

```text
TASK-DEVO-124: Phase 1 MVP tag/checkpoint
```

TASK-DEVO-124 should create the final Phase 1 docs/checkpoint/tag guidance and record this dogfood result as evidence.

## 10. Delivery Runner Request Evidence

This dogfood uses the trusted runner flow for final delivery.

The runner request is intentionally created after this report and the related docs pass validation, so the committed report does not hard-code a runner request id that would drift after request creation. The delivery command is:

```powershell
.\.venv\Scripts\devo.exe delivery runner-request --project DevOrchestrator --message "docs: dogfood phase 1 end-to-end workflow" --note "TASK-DEVO-123 end-to-end Phase 1 dogfood."
```

The final operator report for TASK-DEVO-123 records the actual runner request id and exact normal PowerShell `runner-run` command.
