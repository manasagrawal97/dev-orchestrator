# TASK-DEVO-140 Approved Queue Auto-Run V1

## Goal

Add and dogfood a small approved queue auto-run wrapper that reduces repeated operator commands without adding new unsafe execution.

The command is intentionally conservative: it reuses the existing one-task-at-a-time queue-worker loop, checks policy readiness before execution, checks trusted runner scheduler health before mutation by default, and stops at the same worker/review/validation/delivery boundaries.

## Commands Run

```powershell
git status --short
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-status --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-doctor --project DevOrchestrator
.\.venv\Scripts\devo.exe project approved-queue-run --project DevOrchestrator --policy POL-0001 --dry-run
```

The scheduler status commands still reported drift from the Codex/sandbox context, but Manas had just verified from normal PowerShell that the scheduled runner is installed, enabled, healthy, and that `REQ-0027` completed and pushed. Per the operating rule from TASK-DEVO-139A, this was treated as environment visibility mismatch rather than a reason to reinstall repeatedly.

## Implementation Summary

`devo project approved-queue-run` now supports:

- `--policy <POL-ID>`
- `--run <QWR-ID>` for an explicit queue-worker run
- `--max-cycles`, default `10`
- `--dry-run`
- `--message` and `--note` for delivery-request creation
- `--require-scheduler-healthy` / `--no-require-scheduler-healthy`
- `--confirm-auto-run` for mutating execution

The command first performs a read-only one-step preview. If policy readiness fails, it reports the queue-worker blocker and does not check/mutate further. If execution could proceed, it checks scheduler health unless the operator explicitly disables that gate. It then delegates to the existing queue-worker loop and stops at the next safe boundary.

## Dogfood Observations

The DevOrchestrator smoke command was intentionally read-only:

```powershell
.\.venv\Scripts\devo.exe project approved-queue-run --project DevOrchestrator --policy POL-0001 --dry-run
```

Result:

- Mode: dry-run
- Mutation occurred: `False`
- Stop reason: `policy no longer valid`
- Blocker: `Policy status is draft (not approved yet); approved is required before queue-worker execution.`
- Scheduler health shown from Codex/sandbox: `drift`
- Environment note correctly mentioned possible restricted scheduled-task visibility

This is the right behavior for v1: the command did not auto-run against an unapproved policy, did not run Codex, did not run validation, did not run runner-watch, and did not stage/commit/push.

## Stop Conditions

The wrapper preserves the existing queue-worker loop stop conditions:

- missing worker result/report
- missing worker review
- missing validation evidence
- non-passing validation evidence
- trusted delivery request pending
- trusted delivery failure or unsafe delivery state
- unapproved, expired, or out-of-scope policy
- paused, failed, cancelled, blocked, terminal, or unknown queue-worker states
- no eligible queue item
- max cycles reached
- scheduler not healthy when scheduler health is required

## Boundaries

TASK-DEVO-140 does not implement:

- real Codex execution
- validation execution
- runner-watch execution
- guarded commit/push execution
- queue parallelism
- background daemon changes
- UI controls
- voice, gesture, or assistant controls
- ECC integration
- AI/API model calls

ECC remains future spike territory only. If it is ever considered, it should be framed as a separate explicit research/design task, not smuggled into queue automation.

## Verdict

Approved queue auto-run v1 is ready for further CLI dogfood. It improves ergonomics without weakening the Phase 2 safety model.

Recommended next step: use the command on a deliberately small approved queue where worker/review/validation evidence and trusted runner delivery can be observed end to end.
