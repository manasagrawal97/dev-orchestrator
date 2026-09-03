# TASK-DEVO-185: Full rough-goal workflow dogfood

## Result

PASS with useful friction found.

This task dogfooded the fresh rough-goal workflow:

rough goal file
-> intake-plan
-> intake-materialize
-> intake-next-slice
-> narrow policy approval
-> queue-worker handoff

## Intake used

- Intake: INTAKE-0003
- Materialized batch: B009
- Materialized queue: Q009
- Materialized broad policy: POL-0008
- Replacement narrow policy: POL-0010
- Queue worker run: QWR-0012
- Selected task: T012
- Selected queue item: QI007

## What worked

- intake-plan created a structured intake from a rough markdown goal.
- intake-materialize created draft tasks, batch, queue, and policy artifacts.
- intake-next-slice inspected the materialized intake and gave a concrete next-slice recommendation.
- Broad policy POL-0008 was correctly treated as draft/review-only.
- A narrow one-task policy was created and approved explicitly.
- approved-queue-run created QWR-0012 after the policy had validation commands.

## Manual work avoided

Compared to the earlier workflow, Manas did not need to manually create the first planning structure from scratch.

Avoided manual setup included:

- manually writing candidate backlog tasks
- manually inventing batch and queue ids
- manually drafting the broad policy structure
- manually collecting allowed files from the rough goal
- manually carrying do-not-touch notes into the policy
- manually deciding that the broad materialized policy should remain draft

## Friction found

### 1. intake-next-slice recommended an already-performed planning step

intake-next-slice recommended T006 / QI001: "Run intake-plan on this rough goal."

That task was already completed as part of running the workflow, so it was not the best next execution slice.

Better behavior:
intake-next-slice should prefer the first useful not-yet-done implementation or documentation slice, not prerequisite workflow steps that already happened.

### 2. intake-next-slice omitted validation commands from the narrow-policy command

The first narrow policy, POL-0009, was approved but approved-queue-run blocked because validation_commands were missing.

The replacement policy, POL-0010, fixed this by adding:

- git diff --check
- git diff --cached --check

Better behavior:
intake-next-slice should include validation-command flags in generated execution-policy-create commands when validation notes exist.

### 3. summary recommended codex-worker-batch-run even though policy blockers existed

After POL-0009 blocked, codex-worker-batch-summary still showed codex-worker-batch-run as the recommended command.

Better behavior:
when policy blockers exist, the recommended command should point to fixing the policy, not starting the worker.

## Recommendation for TASK-DEVO-186

Add intake-next-slice polish:

- skip or deprioritize already-completed workflow setup tasks
- include validation-command flags in narrow policy commands
- make summaries avoid recommending worker start commands when policy blockers exist
- keep the task small and focused on reducing dogfood friction

## Safety

- PersonalOS was not touched.
- No UI work was done.
- No AI API integration was added.
- No parallel worker behavior was added.
- No patch-engine work was added.
