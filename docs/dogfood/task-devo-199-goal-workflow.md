# TASK-DEVO-199 Goal Workflow Coverage

## Purpose

TASK-DEVO-199 reduces the reviewed-goal path to three high-level commands: prepare the materialized goal, inspect its current state, and run or resume it after one bounded bundle approval. This report records the implementation trace, the deterministic five-child integration proof added by T058, and the completed live five-child dogfood.

## Implementation trace

The implementation came from reviewed/materialized `INTAKE-0035`, batch `B028`, and queue `Q028`, with children `T054` through `T058`. Earlier implementation children completed through their own normal policy and delivery boundaries. When the new preparation command was exercised during rollout, it excluded already-terminal children and prepared the remaining `T057/QI004/POL-0063` and `T058/QI005/POL-0064` mappings in `GP-INTAKE-0035`. Goal-scoped bundle `PAB-0004` pins those two policies. This is migration and implementation evidence that preparation does not duplicate completed work or silently absorb historical child policies; it is not the clean five-pending-child unattended dogfood required for final acceptance.

## Automated five-child integration proof

`test_goal_workflow_integration_completes_five_low_risk_children_after_one_approval` builds a disposable Git project and a reviewed rough goal with five explicit low-risk children. It runs the real intake/materialization and TASK-DEVO-199 preparation code, then asserts:

- reviewed task order is `T054`, `T055`, `T056`, `T057`, `T058`;
- queue order is `QI001` through `QI005`;
- exactly five requested narrow policies, `POL-0002` through `POL-0006`, each own one task and one queue item with `max_tasks=1` and `max_tasks_per_run=1`;
- exactly one requested bundle, `PAB-0001`, pins those five policies;
- one explicit bundle-approval command approves the bundle and its existing child policy records;
- prepared-goal supervision visits all five policies, items, and tasks in the reviewed order;
- only one child is active at every delivery wait;
- each child receives an independent queue-worker run and delivery request (`QWR-0001`/`REQ-0001` through `QWR-0005`/`REQ-0005`);
- all five simulated delivery waits reconcile canonical pushed-delivery evidence; and
- the durable supervisor finishes with `status=completed`, `stop_reason=bundle_completed`, and `children_completed=5`.

The test uses a fake subprocess worker and injects simulated external trusted-runner completion evidence in a disposable repository. It deliberately fails if the supervisor calls the trusted runner. The result proves orchestration, ordering, gate composition, and terminal reconciliation without calling a model API or changing trusted-delivery implementation. It must not be cited as completed live dogfood.

## Live dogfood status

Live `INTAKE-0039` dogfood completed under batch `B032`, queue `Q032`, source policy `POL-0070`, child policies `POL-0071` through `POL-0075`, and one approved bundle `PAB-0005`. Durable supervisor `ABSR-20260929043832601599` visited the five policies in order, created `QWR-0064` through `QWR-0068`, and finished with `status=completed`, `stop_reason=bundle_completed`, `children_completed=5`, and `resume_count=0`. Each child used a real configured Codex worker, deterministic low-risk review, approved validation, and its own scheduled trusted-delivery request (`REQ-0112` through `REQ-0116`). No operator action occurred between successful children.

The first live preparation attempt correctly stopped because deterministic materialization leaves auto-delivery and auto-push disabled and no supported preparation command had yet captured an operator's permission to enable them. The resulting narrow fix added an explicit, paired `goal-prepare` supervised-delivery opt-in with authorizer identity. It updated only the draft source permission snapshot, created requested bounded child policies, and still stopped at the one bundle-approval gate before the successful live run.

## Safety result

One bundle approval does not mean one broad worker or parallel execution. Every child remains an independent task, one-task policy, worker context, review, validation, delivery request, and commit boundary. The supervisor advances the next child only after pushed trusted-delivery evidence completes and reconciles the current child. Failure, ambiguity, usage limits, review/validation blockers, delivery failure, timeout, recovery contradiction, or policy drift still stop the workflow without automatic retry.

## Operator friction recorded for follow-up

1. Windows validation needs a known safe temp root. In a restricted validation context, `%TEMP%` and ordinary pytest `--basetemp` creation can produce `WinError 5` because the process can create but not enumerate a Python `0o700` directory. Operators must use a temp location and ACL that both the parent and subprocess identities can create, enumerate, and clean.
2. Expected state boundaries can look like command failures. A safe stop at approval, review, or pending trusted delivery may return non-zero even though the durable workflow is healthy and waiting for the intended actor. Readouts should distinguish `waiting` or `action required` from `failed`.
3. Planning and runtime completion can diverge temporarily. Backlog/materialized task state may lag queue-worker and trusted-delivery evidence. Status should reconcile canonical runtime completion, surface the stale planning record, and avoid suggesting duplicate work.

## Next roadmap

TASK-DEVO-199 is complete. TASK-DEVO-200 should expose this workflow in the existing UI as an operator console. TASK-DEVO-201 should then add the local/background service that powers continuous state refresh and approved execution. The usability acceptance target for those two slices is zero PowerShell during normal Devo use. PowerShell and the CLI remain available for auditing, expert diagnosis, and recovery.
