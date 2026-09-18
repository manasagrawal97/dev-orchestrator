# TASK-DEVO-195: Supervised `auto-run-approved`

## Outcome

TASK-DEVO-195 adds the first bundle-bounded supervised execution command:

```powershell
devo project auto-run-approved --project <project> --bundle <PAB-ID> --dry-run
devo project auto-run-approved --project <project> --bundle <PAB-ID> --confirm-auto-run
```

The input is one already-approved TASK-DEVO-194 execution-policy approval bundle. The command does not create backlog, batch, queue, policy, or approval artifacts. Human review still happens before bundle approval and before the confirmed command.

## Safety Contract

Before any mutation, every invocation rechecks:

- bundle status, policy count, and aggregate task/file bounds
- every child policy's approved and unexpired state
- exact low-risk classification
- the bundle's pinned scope fingerprint, task ids, and queue-item ids
- approved batch and matching queue linkage
- explicit allowed files, forbidden files, and validation commands
- required worker-review and validation-evidence gates
- `max_tasks_per_run=1` and positive policy limits
- auto-delivery and auto-push permission
- non-overlapping child task and queue-item ownership
- current queue-item/run linkage and at most one active bundle run

Confirmed mode selects only the existing active child or the first pending child in bundle order. It then reuses the existing queue-worker services for one configured worker subprocess, strict JSON ingest, deterministic low-risk policy/scope review, approved validation commands, delivery-request creation, and later trusted-runner completion reconciliation.

Dry-run is independent of trusted-runner scheduler availability: it does not perform the scheduler-health lookup. Its mutation-free output identifies the selected child policy and queue item, states whether confirmed execution would resume an existing queue-worker run or create a new one, and lists those six gates in order. Confirmed execution still requires healthy scheduler status by default unless the operator explicitly supplies `--no-require-scheduler-healthy`.

Any drift, invalid worker result, unsupported review state, changed-file mismatch, secret/scope blocker, or failed validation stops the command. A newly created delivery request is a hard waiting boundary. The command never invokes runner-watch, stages, commits, pushes, retries failed work automatically, or starts another child in parallel. Deterministic review remains objective safety review only; it does not claim semantic, architectural, business-logic, or code-quality correctness.

## Synthetic Dogfood

Focused tests use a disposable registered project and a scripted fake worker; no real Codex CLI or model API is called.

The covered scenarios are:

1. Normal dry-run rechecks an approved two-policy bundle without a scheduler lookup, selects `POL-0001` / `QI001`, previews a new queue-worker run and the ordered gate sequence, and creates no queue-worker, worker, review, validation, delivery, or target artifacts.
2. A child changed from low to medium risk after approval is rejected before worker execution, and the pinned fingerprint drift is also reported.
3. A failed latest queue-worker run blocks automatic retry and does not launch a replacement worker.
4. Confirmed mode runs exactly one fake worker for `POL-0001` / `QI001`, records passing deterministic review, runs the approved harmless validation command, creates `REQ-0001`, and stops waiting for trusted delivery. After a synthetic pushed trusted-runner result, the next invocation reconciles `QWR-0001` without starting another child; the following dry-run selects `POL-0002` while still writing nothing.
5. Confirmed execution with unhealthy scheduler status stops before the fake worker and creates no execution artifacts, preserving the scheduler safety boundary.
6. Existing `approved-queue-run` regression tests remain passing.

The first implementation worker's focused selection passed with 11 tests using its documented disposable in-process temp-directory workaround. During the bounded correction retry, the registered `%TEMP%` basetemp command selected 12 tests but stopped during fixture setup with the known Python 3.14 restricted-worker `WinError 5` ACL failure, before any test body ran. No ACL change or repository workaround was made; host-side independent validation remains required for the corrected suite.

## Operator Sequence

```powershell
# 1. Review the materialized child policies, request the bundle, and approve it explicitly.
devo project execution-policy-approval-bundle-show --project <project> --bundle <PAB-ID>

# 2. Recheck and preview without querying scheduler health or launching a subprocess.
devo project auto-run-approved --project <project> --bundle <PAB-ID> --dry-run

# 3. Confirm one child only after reviewing the preview and scheduler state.
devo project auto-run-approved --project <project> --bundle <PAB-ID> --confirm-auto-run

# 4. Let the trusted runner process the pending request outside this command.
devo delivery runner-watch --project <project> --approver "Manas" --once --confirm-runner-watch

# 5. Rerun to reconcile that completed delivery before any next child is selected.
devo project auto-run-approved --project <project> --bundle <PAB-ID> --confirm-auto-run
```

`--no-require-scheduler-healthy` remains an explicit disposable/manual-runner escape hatch; it is not the normal live default.

## Remaining Risk

The synthetic dogfood proves gate composition and one-child stopping, not a live multi-child Codex run. A future narrow dogfood should exercise repeated trusted-runner completion and next-child selection on disposable work. Real usage must keep exact worker/Git file agreement and should use manual semantic review whenever deterministic checks are insufficient.
