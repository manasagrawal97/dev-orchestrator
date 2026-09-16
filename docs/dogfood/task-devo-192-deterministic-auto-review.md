# TASK-DEVO-192 Deterministic Auto-Review

## Purpose

TASK-DEVO-192 adds a conservative deterministic review helper for completed queue-worker evidence. It is the next Supervised Auto Mode building block after TASK-DEVO-191 optional auto-validation.

## Command

Preview without recording evidence:

```powershell
devo project queue-worker-run-review --project <project> --policy <POL-ID> --run <QWR-ID>
```

Record a passed deterministic review only when every required check passes:

```powershell
devo project queue-worker-run-review --project <project> --policy <POL-ID> --run <QWR-ID> --confirm-run-review
```

## Deterministic Checks

The helper verifies approved low-risk policy status, policy/run and queue/item/task linkage, completed non-patch-only worker evidence, actual Git changes, exact worker/Git changed-file agreement, allowed and forbidden path scope, effective changed-file limits, unstaged state, and the established delivery secret-risk checks. Ambiguous or failed checks block automatic review evidence.

## Safety Boundary

A deterministic pass proves only the listed objective checks. It does not prove semantic correctness, architecture, business behavior, or code quality. Manual `queue-worker-record-review` remains available. Validation is a separate gate, and trusted delivery remains the only commit/push path.

The helper never runs validation, creates a delivery request, invokes the trusted runner, stages, commits, or pushes.

## Implementation Status

The source and focused regression tests are implemented under approved policy `POL-0033`. The live implementation run `QWR-0029` remains `waiting_worker`; this task did not dogfood or mutate that run. Dogfood should occur only after implementation worker evidence is recorded through the normal workflow.

## First Dogfood Repair

The first `QWR-0029` preview exposed two operator-facing issues while stopping safely before review evidence:

- A complete real-looking token literal used by the new regression test caused the established delivery scanner to classify `tests/test_project_planning.py` as secret risk. The deterministic review then displayed that risk separately while filtering it from its general delivery-safety row, producing contradictory FAIL/PASS output. The test now constructs the token at runtime, as established delivery tests do, and deterministic review reports one canonical trusted-delivery safety classification without filtering secret blockers. Real secret signals still block; harmless placeholders and documentation-only terms retain the canonical non-blocking behavior.
- `queue-worker-record-worker-result --files-changed` is one comma-separated scalar option. Repeating the flag caused Click to retain only the final value, so `report-WR031` listed only this dogfood report even though Git listed all seven files. Exact worker/Git agreement remains mandatory.

For a worker run that is still eligible to record successful worker evidence, supply all paths in one option:

```powershell
devo project queue-worker-record-worker-result --project DevOrchestrator --run <QWR-ID> --status completed --summary "<summary>" --files-changed "src/devo/main.py,src/devo/project_planning.py,tests/test_project_planning.py,docs/current-state.md,docs/how-to-use-devo.md,docs/usability-roadmap.md,docs/dogfood/task-devo-192-deterministic-auto-review.md" --confirm-record
```

Because successful worker-result recording is accepted only at `waiting_worker`, do not blindly rerun this command against a run that has already advanced to `waiting_review`. Use the normal safe retry/recovery path chosen by the operator, then record the corrected comma-separated evidence on the eligible run.
