# TASK-DEVO-182 Intake Materialize Dogfood

## Goal

Prove that a reviewed rough-goal intake can be converted into real draft Devo planning artifacts without manual spreadsheet-style setup.

## Setup

- Project: `DevOrchestrator`
- Source intake: `INTAKE-0002`
- Source intake file: `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0002/intake-plan.json`
- Command:

```powershell
.\.venv\Scripts\devo.exe project intake-materialize --project DevOrchestrator --intake INTAKE-0002 --confirm-materialize
```

## Result

The command completed successfully and created workspace-only draft planning artifacts:

- Created draft task ids: `T002`, `T003`, `T004`, `T005`
- Draft batch: `B008`
- Draft queue: `Q008`
- Draft execution policy: `POL-0006`
- Materialization JSON: `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0002/materialization.json`
- Materialization Markdown: `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0002/materialization.md`

The command preserved the intake scope:

- Allowed files included `src/devo/main.py`, `src/devo/project_planning.py`, `tests/test_project_planning.py`, `docs/current-state.md`, `docs/how-to-use-devo.md`, and the dogfood report path suggested by the intake.
- Forbidden/do-not-touch notes included `PersonalOS`, patch proposal engine unless a hard blocker, UI, parallel workers, `.env`, `.venv/**`, `workspace/**`, `ui/node_modules/**`, `ui/dist/**`, and `pt-*`.
- Validation notes included Python compile, focused pytest, `git diff --check`, and `git diff --cached --check`.
- Delivery notes preserved trusted-runner-only delivery guidance.

## Safety Check

The materialized artifacts remained draft/review-only:

- No batch approval was created.
- No execution policy approval was created.
- No Codex worker was run.
- No validation command was run by materialization.
- No delivery request was created by materialization.
- No files were staged, committed, or pushed by materialization.
- No target project files were edited by materialization.

The command output clearly printed:

- the intake id
- created task ids
- batch id
- queue id
- policy id
- allowed files
- risk notes
- exact next review/approval commands
- a safety message that no approvals, Codex run, validation, delivery request, commit, or push were created

## What Improved

Before this task, `intake-plan` produced useful candidate tasks and suggested batch/queue/policy ids, but the operator still had to translate the intake into real Devo planning artifacts by hand.

After this task, a reviewed intake can become draft backlog, batch, queue, and policy artifacts in one explicit command. This removes the most sheet-like part of the rough-goal flow while keeping all approval and execution gates separate.

## Remaining Friction

- Materialized task titles can still be long in console output; the JSON and Markdown artifacts remain the source of truth.
- The next step is still two explicit approval paths: batch approval and execution policy request/approval. That is acceptable for now, but a future helper could summarize the materialized draft readiness before approval.
- The intake source can suggest a dogfood report path that differs from the actual task report name. The materialization preserves the intake faithfully instead of guessing a rename.

## Verdict

PASS.

`devo project intake-materialize` successfully turns a reviewed rough-goal intake into draft planning artifacts without approving or executing work.

## Recommendation

TASK-DEVO-183 should dogfood the materialized draft path through explicit batch/policy review and approval, then decide whether a small `intake-review` or `materialization-status` helper is worth adding.
