# TASK-DEVO-187 Intake Policy Create Next Dogfood

## Purpose

TASK-DEVO-187 reduces the manual gap between a materialized rough-goal intake and the first narrow execution policy.

Before this task, Devo could recommend the safest next slice with `intake-next-slice`, but the operator still had to manually translate that recommendation into a new narrow execution policy command. The new command keeps the recommendation-driven workflow, but removes the copy-and-assemble step.

## New command

Preview mode:

```powershell
devo project intake-policy-create-next --project DevOrchestrator --intake INTAKE-XXXX
```

Confirmed draft creation:

```powershell
devo project intake-policy-create-next --project DevOrchestrator --intake INTAKE-XXXX --confirm-create-policy
```

## What It Does

`intake-policy-create-next`:

- reads a materialized intake
- uses the current `intake-next-slice` recommendation
- creates a narrow draft execution policy for the next recommended task and queue item
- preserves the recommended allowed task
- preserves the recommended queue item
- preserves recommended allowed files
- preserves forbidden files and do-not-touch notes
- preserves validation commands
- preserves notes needed for operator review

The command is meant to help the operator move from rough goal to safe next slice faster, without turning broad materialized policies into approved execution policies by accident.

## Safety Behavior

Preview mode is read-only.

Confirmed mode creates a draft policy only. It does not:

- request approval
- approve the policy
- start a worker
- run Codex
- run validation
- create a delivery request
- commit
- push

The operator must still explicitly request and approve the policy before worker execution can begin.

## Dogfood Evidence

TASK-DEVO-187 core was delivered through `POL-0019`.

The implementation was split across focused slices:

- T019 delivered the service logic.
- T020 delivered scope preservation regression coverage.
- T021 delivered confirmed CLI behavior and tests.

The smoke test created draft `POL-0020` for `T022`, proving the command could materialize the recommended next slice as a narrow draft execution policy.

This replacement docs-only slice is `POL-0025` / `QWR-0025`.

## Why It Matters

The command reduces manual friction between materialized intake review and narrow policy creation.

The operator can now move from:

```text
rough goal -> intake-plan -> intake-materialize -> intake-next-slice -> draft narrow policy
```

without maintaining a separate planning sheet or manually reconstructing the policy command.

It still keeps the human gates intact: approval, worker execution, review evidence, validation evidence, and delivery remain separate explicit actions.

## Remaining Limitations

- The user still manually approves the policy.
- The user still manually records review evidence.
- The user still manually records validation evidence.
- The next improvement should be validation evidence automation.

