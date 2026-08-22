# TASK-DEVO-135 Evidence Intake Dogfood

## Scenario Tested

TASK-DEVO-135 dogfooded queue-worker evidence intake in focused temporary-project tests. The scenario used a registered `sample` project under pytest `tmp_path`, an approved execution policy, one queue item, one generated handoff, and one linked manual/assisted worker run. No PersonalOS repository, real Codex CLI, AI/API call, automatic validation execution, runner-watch, commit, or push was used.

## Commands Run

- `devo project queue-worker-record-worker-result --project sample --run QWR-0001 --status completed --summary "Implemented requested change." --confirm-record`
- `devo project queue-worker-record-review --project sample --run QWR-0001 --status passed --summary "Review passed." --confirm-record`
- `devo project queue-worker-record-validation --project sample --run QWR-0001 --status passed --summary "Validation passed." --commands-run "pytest" --confirm-record`
- `devo project queue-worker-loop --project sample --policy POL-0001 --confirm-loop`

Live smoke used read-only/dry-run commands against DevOrchestrator only:

- `devo project queue-worker-loop --project DevOrchestrator --policy POL-0001 --dry-run`
- `devo project execution-policy-list --project DevOrchestrator`
- `devo project queue-worker-status --project DevOrchestrator`
- `devo delivery runner-schedule-status --project DevOrchestrator`

## Evidence Records Created

- Worker result evidence writes a Codex worker report artifact and updates the linked worker-run report metadata.
- Review evidence writes a Codex worker review artifact with mapped review status.
- Validation evidence updates the review validation evidence section with status, summary, reported commands, and optional evidence paths.

The record commands require `--confirm-record`, require an existing queue-worker run, preserve the queue-worker run status, and tell the operator to run `queue-worker-loop` again.

## State Transitions Observed

The loop consumed the new evidence without a new state model:

```text
waiting_worker
-> record worker result
-> queue-worker-loop
-> waiting_review
-> record review
-> queue-worker-loop
-> waiting_validation
-> record validation
-> queue-worker-loop
-> delivery_requested
```

Failed or blocked evidence was not treated as success. A blocked worker result caused the loop to pause the queue-worker run instead of advancing toward delivery.

## Policy Usability Observations

Draft policies now say they are not approved yet, and `execution-policy-list` marks policies as `APPROVED` or `NOT_APPROVED(<status>)`. This makes dry-run output less alarming when a policy is merely waiting for approval.

## What Still Feels Manual

- The operator still performs the actual work, review, and validation outside Devo.
- The operator must honestly summarize commands and files changed.
- The trusted runner is still a separate delivery step.
- The live DevOrchestrator policy currently remains draft, so live evidence recording was not forced during this task.

## Readiness

The evidence intake layer is ready for a live three-task assisted dogfood as long as the batch has an explicit approved policy and the operator keeps the worker/review/validation evidence honest.

## Recommended Next Task

TASK-DEVO-136 should run a small live three-task assisted queue-worker dogfood on DevOrchestrator using:

```text
queue-worker-loop
-> manual work
-> queue-worker-record-worker-result
-> queue-worker-loop
-> queue-worker-record-review
-> queue-worker-loop
-> queue-worker-record-validation
-> queue-worker-loop
-> trusted runner delivery
```

Keep the batch docs-only or tiny source/docs, and do not add real Codex automation yet.
