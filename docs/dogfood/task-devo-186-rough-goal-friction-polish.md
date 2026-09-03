# TASK-DEVO-186 Rough-Goal Friction Polish

## Goal

Polish the rough-goal materialization flow after dogfooding `intake-next-slice`.

## Finding

Materialized intakes can include workflow setup tasks that are already effectively done by the time `intake-next-slice` runs, such as:

- running `intake-plan`
- reviewing generated intake JSON/Markdown
- checking whether the intake produced useful draft task/batch/queue/policy suggestions
- materializing the intake into draft planning artifacts

Before this polish, those tasks could still be recommended as the next slice because their queue items remained pending.

## Change

`intake-next-slice` now deprioritizes already-performed setup/review tasks when the intake and materialization artifacts already exist. It keeps those tasks visible in the output under "Deprioritized already-performed setup tasks" and recommends the next actual follow-up task when one is available.

The command remains read-only. It does not mark tasks completed, approve policies, create queue-worker runs, run Codex, validate, create delivery requests, commit, or push.

## Validation

- `.\.venv\Scripts\python -m py_compile src/devo/main.py src/devo/project_planning.py`
- `.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k intake_next_slice`

## Result

PASS. The recommendation logic now better matches the operator's mental model after a rough goal has already been converted into real draft artifacts.
