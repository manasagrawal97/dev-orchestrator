# TASK-DEVO-193: Codex Worker Auto-Run And Auto-Ingest

## Goal

Reduce the manual preparation, subprocess, and strict-result-ingest steps at the worker boundary without widening review, validation, or delivery authority.

## Delivered Behavior

`devo project queue-worker-loop` now has an optional `--auto-worker` mode:

```powershell
devo project queue-worker-loop --project <project> --policy <POL-ID> --run <QWR-ID> --auto-worker --dry-run
devo project queue-worker-loop --project <project> --policy <POL-ID> --run <QWR-ID> --auto-worker --confirm-loop
```

The default loop remains unchanged and stops when worker evidence is missing. Dry-run prints the confirmed command but does not launch a subprocess or write worker artifacts. Confirmed mode binds execution to the exact selected queue-worker run, reuses the existing one-item Codex worker preparation, configured subprocess, and strict JSON ingest services, then stops at `waiting_review`.

## Safety Boundaries

- The execution policy must already be approved.
- At most one queue item and one subprocess run are attempted.
- Run-selection mismatch blocks before subprocess execution.
- Missing output, invalid JSON, process failure, usage limit, blocked result, or failed result stops before review, validation, and delivery.
- Review is not recorded automatically.
- Validation is not run automatically by `--auto-worker`.
- Delivery requests are not created at the worker boundary.
- The trusted runner is not invoked.
- Files are not staged, committed, or pushed.
- Parallel workers remain unsupported.

## Focused Fake-Worker Dogfood

Focused tests use the existing fake local worker executable; no real Codex CLI was run. They prove:

- default loop behavior starts no subprocess;
- `--auto-worker --dry-run` starts no subprocess and writes no run/preparation/ingest/batch artifacts;
- confirmed mode runs and ingests exactly one valid fake result, then stops at review;
- invalid JSON stops safely before review, validation, or delivery;
- an unapproved policy cannot start the subprocess;
- no trusted runner, staging, commit, push, or target-repo mutation occurs.

## Current Live State

POL-0035 remains the approved narrow implementation policy. QWR-0032 is the current retry run used for this interactive implementation handoff; this task does not mutate its workspace artifacts or launch real Codex. The returned strict worker JSON can be ingested through the normal evidence path before deterministic review and validation.

## Verdict

PASS for the narrow optional integration under fake-worker validation. Real use remains supervised and one item at a time. The next safe product slice is bounded approval and eventual composition of the existing worker, deterministic review, validation, delivery-request, and trusted-runner reconciliation services; it is not parallel or unattended coding.
