# TASK-DEVO-197 Continuous Approved-Bundle Supervisor

## Goal

Prove that one confirmed Devo invocation can supervise multiple already-approved low-risk children sequentially while preserving the trusted-runner boundary and every existing worker, review, validation, and policy gate.

## Command Shape

One-child TASK-DEVO-195 behavior remains the default:

```powershell
devo project auto-run-approved --project DevOrchestrator --bundle PAB-XXXX --confirm-auto-run
```

Continuous supervision is explicit:

```powershell
devo project auto-run-approved --project DevOrchestrator --bundle PAB-XXXX --supervise --poll-interval-seconds 5 --max-wait-seconds 600 --confirm-auto-run
```

Read-only preview:

```powershell
devo project auto-run-approved --project DevOrchestrator --bundle PAB-XXXX --supervise --dry-run
```

## Deterministic Dogfood

Focused tests create a two-policy approved bundle with one low-risk queue item per policy. A scripted worker makes one task-specific scoped change. The supervisor creates the existing review, validation, and delivery-request evidence through established services. A test-only callback then simulates an external trusted runner by writing canonical completed/pushed runner evidence; the supervisor itself never calls the runner.

The observed sequence is:

1. Recheck the approved bundle and one-active-child invariant.
2. Select child one and run worker, deterministic review, and approved validation.
3. Create one trusted delivery request and wait.
4. Observe completed/pushed trusted-runner evidence.
5. Reconcile child one and complete its queue item.
6. Recheck the bundle before selecting child two.
7. Repeat the same gates for child two.
8. Finish with `bundle_completed`.

The evidence artifact records visited policy, queue-item, task, queue-worker-run, and delivery-request IDs; delivery wait outcomes; completed child count; final stop reason; next action; and whether workflow state changed. It references existing evidence rather than copying it and creates no per-poll artifacts.

## Timeout And Resume

A pending delivery test uses an injected monotonic clock. The supervisor reaches `trusted_delivery_timeout`, leaves the existing request and queue-worker run unchanged, does not select child two, and writes a resumable next action. A second invocation resumes the same delivery request, observes simulated trusted completion, reconciles the child, and continues. No duplicate request or worker retry is created for the timed-out child.

## Safe Stops

Focused coverage verifies deterministic classification for human review, blocked worker, failed worker, usage limit, failed validation, failed trusted delivery, timeout, and policy drift. Drift injected after the first reconciliation prevents the second child from starting. Dry-run creates no supervisor artifact, queue-worker run, subprocess, evidence, delivery request, or polling sleep. An already-completed bundle starts no new worker or request.

## Safety Verdict

PASS for deterministic dogfood. The supervisor is a bounded coordinator over existing services. It never invokes trusted delivery, stages, commits, pushes, runs children concurrently, retries failed work automatically, or bypasses semantic-review requirements. Process-death recovery and a durable supervisor cursor remain TASK-DEVO-198 scope.

## Recommended Live Dogfood

Use a narrow already-approved two-policy docs bundle from normal PowerShell:

```powershell
.\.venv\Scripts\devo.exe project auto-run-approved --project DevOrchestrator --bundle PAB-XXXX --supervise --poll-interval-seconds 5 --max-wait-seconds 600 --confirm-auto-run
```

Keep the scheduled trusted runner healthy before starting. Stop and inspect the supervisor artifact on any reason other than `bundle_completed`; do not manually create duplicate delivery requests or retry failed workers.
