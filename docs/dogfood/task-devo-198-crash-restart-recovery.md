# TASK-DEVO-198 Crash/Restart Recovery

## Goal

Make continuous approved-bundle supervision safe to re-enter after its process or machine stops, without duplicating queue-worker runs, Codex execution, review, validation, delivery requests, trusted delivery, commits, pushes, or completed children.

## Implemented Contract

A confirmed `auto-run-approved --supervise` process takes an operating-system lock scoped to one project and approval bundle. The lock is released by the operating system after normal exit or process death. A second process for the same bundle fails before workflow mutation.

The first process creates an `ABSR-*` artifact before child execution. Atomic JSON and Markdown checkpoints record start/re-entry, bundle rechecks, the intent and result of each child advance, delivery-wait boundaries, and reconciliation boundaries. A checkpoint with no `completed_at` is incomplete. Re-entry accepts exactly one incomplete checkpoint, retains its supervisor id and event history, increments `resume_count`, and reconstructs completed-child progress from canonical queue items rather than trusting process memory.

Queue-worker, worker-ingest, review, validation, delivery-request, and trusted-runner artifacts remain the sources of truth for their gates. If a waiting worker already has ambiguous subprocess-attempt or non-passing ingest evidence, recovery stops with `contradictory_durable_state`; it does not relaunch Codex. Multiple incomplete supervisor checkpoints, invalid event sequence, or missing checkpoint-referenced queue-worker runs also fail closed.

## Deterministic Dogfood Evidence

The focused `restart_safe` tests use a two-child approved bundle and scripted worker. The first supervisor is interrupted by a test exception only after child one has one queue-worker run, one completed worker/review/validation path, one delivery request, and a durable `delivery_wait_started` checkpoint. No terminal supervisor artifact is written.

The second invocation uses the same bundle and checkpoint. It keeps the same `ABSR-*` id, records one re-entry, observes externally written completed/pushed delivery evidence, reconciles child one, executes child two once, and finishes `bundle_completed`. Final evidence contains exactly two queue-worker runs, two worker batch runs, and two delivery requests. Separate tests prove same-bundle lock exclusion and deterministic rejection of two incomplete checkpoints.

## Operator Live-Dogfood Plan

Use an already-reviewed two-child low-risk documentation bundle from normal PowerShell. Keep the external scheduled trusted runner healthy; the supervisor never invokes it.

1. Preview the bundle with `devo project auto-run-approved --project DevOrchestrator --bundle <PAB-ID> --supervise --dry-run`.
2. Start confirmed supervision with a bounded wait: `devo project auto-run-approved --project DevOrchestrator --bundle <PAB-ID> --supervise --poll-interval-seconds 5 --max-wait-seconds 600 --confirm-auto-run`.
3. After the supervisor artifact reaches `delivery_wait_started` for child one, terminate only the supervisor process. Do not stop or manually invoke trusted delivery, and do not create worker or delivery artifacts.
4. Inspect the incomplete `approved-bundle-supervisor.json`, the selected `QWR-*`, and its single `REQ-*`. Confirm no second child has started.
5. Rerun the exact confirmed command. Confirm output reports the same supervisor id, `Resume count: 1`, and a `supervisor_reentry` event in the artifact.
6. Let external trusted delivery finish both children. Verify `bundle_completed`, two completed child queue items, exactly one queue-worker run and delivery request per child, and no duplicated worker/review/validation evidence.
7. Run the approved validation commands and preserve the supervisor, worker, validation, and delivery evidence for review.

## Safety Verdict

PASS for deterministic crash/re-entry coverage. Live process termination remains an explicit operator dogfood step because this implementation worker did not run real Codex, invoke the trusted runner, configure the scheduler, commit, or push. Recovery is deliberately conservative: ambiguity stops for human inspection instead of retrying failed or possibly-started work.
