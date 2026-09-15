# TASK-DEVO-191 Queue Worker Loop Auto-Validation

## Purpose

TASK-DEVO-191 connects the TASK-DEVO-190 validation evidence runner to `queue-worker-loop` behind an explicit opt-in flag. This removes one operator command after review passes without widening worker, approval, or delivery authority.

## Command

```powershell
devo project queue-worker-loop --project DevOrchestrator --policy POL-0029 --run QWR-0027 --auto-validation --confirm-loop
```

The existing command without `--auto-validation` keeps its manual validation stop. A dry-run with the flag reports that validation is enabled but does not execute commands or record evidence.

## Behavior

At `waiting_validation`, confirmed auto-validation reuses `run_queue_worker_policy_validation`. That service requires an approved policy, matching queue-worker run and selected queue/task, completed worker evidence, passed review, configured validation commands, and an existing target repository.

When every command passes, Devo records automatic validation evidence and the existing loop continues toward its normal delivery-request step. When any command fails, failed evidence is recorded and the loop stops. A blocked validation also stops and surfaces its blockers. No failed or blocked path creates a delivery request.

## Safety Boundaries

The integration does not:

- bypass policy approval
- bypass worker review
- run real Codex
- invoke the trusted runner
- stage files
- commit
- push
- start parallel work

Delivery request creation remains existing queue-worker-loop behavior and occurs only after passing evidence. Commit and push remain trusted-runner-only operations.

## Focused Validation

Focused regression coverage proves:

- the default loop still stops at validation
- auto-validation dry-run executes nothing
- passed validation evidence is recorded before delivery-request creation
- failed validation evidence stops the loop without delivery
- pending review and unapproved policy gates are not bypassed
- the loop does not invoke the trusted runner or stage, commit, or push

## Remaining Manual Gaps

- Worker review evidence is still manual.
- Codex worker execution and ingest need further hardening.
- Bounded bulk approval remains future work.
- The full supervised `auto-run-approved` sequential loop remains future work.

## Verdict

The optional integration is ready for narrow supervised use. It automates only approved validation after review, leaves the default behavior unchanged, and preserves trusted-runner-only delivery.
