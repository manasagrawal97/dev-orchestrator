# TASK-DEVO-142 Lightweight Handoff Checklist V1

## Why This Is Needed

`approved-queue-run` and `queue-worker-loop` can now bring an approved queue item to the worker boundary, but the worker/operator needs one compact pre-work checklist before implementation starts.

The checklist keeps the next assisted step clear without implementing real Codex-worker execution.

## Checklist Fields

- objective
- allowed scope
- forbidden scope
- relevant files
- acceptance criteria
- required tests
- expected worker result format
- risk notes
- next action

Missing task or policy details use the fallback `Not specified in current task/policy.` rather than inventing files or tests.

## Where It Appears

Queue-worker run artifacts now store a lightweight checklist when a run is created. `queue-worker-show` and `queue-worker-latest` print it when present.

The read-only command below can show or derive the checklist for an existing queue-worker run:

```powershell
.\.venv\Scripts\devo.exe project queue-worker-handoff-show --project DevOrchestrator --run QWR-0001
```

## Connection To Evidence Schema V1

The checklist points to the TASK-DEVO-141 worker evidence schema v1. It reminds the operator to record:

- status
- summary
- changed files
- commands/tests run
- risks
- recommended next action
- artifact path if any
- recorded by
- timestamp

It also prints the `queue-worker-record-worker-result` command with the schema fields.

## How It Supports Approved Queue Run

`approved-queue-run` and `queue-worker-loop` still stop at the worker boundary. The next action now points the operator toward the checklist before worker result evidence is recorded.

## Still Manual

The checklist does not run Codex, validation, review, delivery, commit, or push. It does not complete queue items and does not trust worker output by itself.

## Future Scope

This is not a full agent-role contract system. Real Codex-worker execution, least-privilege role permissions, parallel workers, and broader autonomous multi-task execution remain future work.

## Recommended Next Task

TASK-DEVO-143: Live 3-5 task assisted queue dogfood.
