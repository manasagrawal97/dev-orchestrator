# TASK-DEVO-184 Intake Next-Slice Guidance Dogfood

## Goal

Add and dogfood a read-only helper that inspects materialized rough-goal intake artifacts and recommends the safest next slice, so the operator does not have to manually join intake, task, batch, queue, and policy details before creating a narrow execution policy.

## Source Artifacts

- Intake: `INTAKE-0002`
- Materialized tasks: `T002`, `T003`, `T004`, `T005`
- Batch: `B008`
- Queue: `Q008`
- Broad materialized policy: `POL-0006`

## Command Run

```powershell
.\.venv\Scripts\devo.exe project intake-next-slice --project DevOrchestrator --intake INTAKE-0002
```

## Output Verdict

The command successfully produced one compact read-only position:

- recommended task: `T002`
- recommended queue item: `QI001`
- related batch: `B008`
- related queue: `Q008`
- related policy: `POL-0006`
- policy status: `draft`
- broad-policy warning: `POL-0006` covers multiple tasks and queue items
- suggested narrow allowed files: copied from the materialized intake policy scope
- do-not-touch notes: preserved from the intake
- validation notes: preserved from the intake
- exact next commands: inspect batch/queue/policy, create a narrow one-task execution policy, request approval, approve after review

The helper did not approve anything, create a queue-worker run, run Codex, validate, create delivery, commit, or push.

## Would This Have Helped TASK-DEVO-183?

Yes. In TASK-DEVO-183, the operator manually inspected `B008`, `Q008`, and `POL-0006`, noticed that `POL-0006` was too broad, then hand-built a narrow `POL-0007` command for one queue item.

`intake-next-slice` now performs the artifact join and prints the narrow-policy command shape directly. The operator still has to review whether the recommendation is correct, but the spreadsheet-like lookup work is mostly gone.

## Manual Work Still Required

- Choose whether the recommended task is actually the right next business slice.
- Review and tighten allowed files if the intake scope is still broad.
- Create/request/approve the narrow policy explicitly.
- Run worker/review/validation/delivery gates separately.

## Friction Found

The materialized policy scope can still include every allowed file from the original intake. That is useful as a starting point, but a future helper could suggest a smaller file subset per task if the intake captured task-specific files.

The helper is intentionally read-only for v1; it does not create the narrow policy automatically.

## Safety Verdict

PASS. The command reduced materialized-intake decision friction without widening autonomy.

## Recommendation

TASK-DEVO-185 should dogfood using `intake-next-slice` as the first step before creating a narrow execution policy. If this repeats smoothly, consider a separate explicit `intake-create-slice-policy` command later, but only as a draft-policy creator with no approval or execution.
