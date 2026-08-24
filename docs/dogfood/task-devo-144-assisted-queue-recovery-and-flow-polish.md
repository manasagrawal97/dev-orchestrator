# TASK-DEVO-144 Assisted Queue Recovery And Flow Polish

## Goal

Polish the assisted approved-queue flow after TASK-DEVO-143 without expanding Devo into full autonomous execution.

## Changes

- Added `devo delivery runner-recover-push` for the narrow recovery case where trusted runner commit succeeded but the guarded push failed.
- Added `devo project approved-queue-run --continue-next` so a specified completed run can immediately start one next eligible queue item and then stop at the next safe boundary.
- Updated validation evidence intake wording to point operators back to `approved-queue-run` after passing validation.
- Updated validation evidence output labels so supporting artifacts and validation evidence artifacts are easier to recognize.
- Updated `devo worker codex flow-summary` so `--queue` is optional when there is one uniquely latest queue.
- Added `devo project flow-summary` as a short alias for the same read-only flow summary.

## Push-Only Recovery Boundaries

`runner-recover-push` is intentionally narrower than normal delivery. It requires:

- an existing runner request
- a previous successful guarded commit result
- a recorded delivery report commit hash
- current `HEAD` matching the recorded commit
- clean staged, unstaged, and untracked Git status
- matching project path and branch
- explicit `--confirm-runner-push` unless `--dry-run` is used

It does not stage files, create commits, refresh reports, run validation, run Codex, or bypass delivery gates.

## Continuation Boundaries

`approved-queue-run --continue-next` only continues after a specified run safely reaches `specified queue-worker run completed`. It starts at most one next eligible item and then stops at the next normal queue-worker boundary, such as missing worker evidence.

## Still Not Added

- no real Codex execution
- no validation execution automation
- no UI approval/build/test/commit/push controls
- no parallel worker behavior
- no AI/API calls
- no delivery safety bypass

## Validation Notes

Focused tests cover:

- push-only runner recovery after failed push
- recovery dry-run behavior
- dirty-tree and head-mismatch blockers
- completed/missing recovery blockers
- `approved-queue-run --continue-next`
- validation evidence wording
- latest/default flow-summary queue behavior and ambiguity blocking

## Recommended Next Task

TASK-DEVO-145 should dogfood the polished assisted queue flow again and decide whether the next useful step is more CLI polish, read-only UI visibility for queue recovery, or a tightly scoped validation-evidence convenience command.
