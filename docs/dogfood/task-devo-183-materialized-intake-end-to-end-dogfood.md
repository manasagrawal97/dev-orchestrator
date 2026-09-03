# TASK-DEVO-183 Materialized Intake End-To-End Dogfood

## Goal

Use artifacts created by `devo project intake-materialize` as the real starting point for a small DevOrchestrator task, instead of manually creating backlog tasks, a batch, a queue, and an execution policy from scratch.

## Intake And Materialized Artifacts

- Intake id: `INTAKE-0002`
- Materialized tasks: `T002`, `T003`, `T004`, `T005`
- Materialized batch: `B008`
- Materialized queue: `Q008`
- Materialized draft policy: `POL-0006`
- Materialization receipt: `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0002/materialization.md`

The materialized batch and queue were readable and linked correctly. `POL-0006` preserved the intake scope, but it covered all four materialized tasks and included source/test files, so it was intentionally left as a broad draft instead of being approved for this dogfood.

## Smallest Safe Slice

To keep the dogfood narrow, a new one-item policy was created from the materialized `B008/Q008` artifacts:

- Policy: `POL-0007`
- Allowed queue item: `QI004`
- Allowed task: `T005`
- Queue-worker run: `QWR-0011`
- Worker evidence: `qwr-0011-worker-result` (`report-WR013.json` / `report-WR013.md`)
- Review evidence: `qwr-0011-review` (`review-WR013.json` / `review-WR013.md`)
- Validation evidence: `qwr-0011-validation` (`review-WR013.json` / `review-WR013.md`)
- Delivery request: `REQ-0071`
- Allowed files:
  - `src/devo/project_planning.py`
  - `tests/test_project_planning.py`
  - `docs/dogfood/task-devo-183-materialized-intake-end-to-end-dogfood.md`
  - `docs/current-state.md`
  - `docs/how-to-use-devo.md`

This policy was requested and approved only for the TASK-DEVO-183 dogfood/report plus the tiny summary wording polish found during inspection.

## Commands Run

```powershell
.\.venv\Scripts\devo.exe project backlog-show --project DevOrchestrator
.\.venv\Scripts\devo.exe project batch-show --project DevOrchestrator --batch B008
.\.venv\Scripts\devo.exe project queue-show --project DevOrchestrator --queue Q008
.\.venv\Scripts\devo.exe project execution-policy-show --project DevOrchestrator --policy POL-0006
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project DevOrchestrator --policy POL-0006
.\.venv\Scripts\devo.exe project execution-policy-create --project DevOrchestrator --batch B008 --queue Q008 --title "TASK-DEVO-183 materialized intake dogfood slice" --allowed-task T005 ...
.\.venv\Scripts\devo.exe project execution-policy-request --project DevOrchestrator --policy POL-0007 --note "TASK-DEVO-183 reviewed smallest safe materialized intake slice."
.\.venv\Scripts\devo.exe project execution-policy-approve --project DevOrchestrator --policy POL-0007 --approver "Manas" --note "Approved for TASK-DEVO-183 one-item materialized intake dogfood slice only."
.\.venv\Scripts\devo.exe project approved-queue-run --project DevOrchestrator --policy POL-0007 --dry-run --no-require-scheduler-healthy
.\.venv\Scripts\devo.exe project approved-queue-run --project DevOrchestrator --policy POL-0007 --confirm-auto-run --no-require-scheduler-healthy
.\.venv\Scripts\devo.exe project queue-worker-record-worker-result --project DevOrchestrator --run QWR-0011 --status completed --summary "Implemented TASK-DEVO-183 materialized-intake dogfood report and draft-policy summary wording polish." --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-review --project DevOrchestrator --run QWR-0011 --status passed --summary "Reviewed TASK-DEVO-183 diff: summary wording polish is narrow, materialized-intake dogfood report is docs-only, and files remain inside POL-0007 scope." --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-validation --project DevOrchestrator --run QWR-0011 --status passed --summary "Validation passed: py_compile succeeded, focused summary regression passed, and full tests/test_project_planning.py passed with 220 tests." --confirm-record
.\.venv\Scripts\devo.exe project approved-queue-run --project DevOrchestrator --policy POL-0007 --run QWR-0011 --confirm-auto-run --no-require-scheduler-healthy
```

## What Worked

- The materialized backlog, batch, queue, and policy ids were easy to inspect.
- The materialized queue preserved queue item/task linkage: `QI004` maps to `T005`.
- Creating a narrower policy from the materialized batch and queue avoided approving broad work.
- `approved-queue-run --dry-run` clearly previewed that it would create one queue-worker run.
- `approved-queue-run --confirm-auto-run` created `QWR-0011` and stopped at the worker evidence gate.
- Manual worker, review, and validation evidence advanced `QWR-0011` through the normal gates.
- Devo created delivery request `REQ-0071` after evidence was present.
- No real Codex subprocess was launched.
- No validation, commit, or push happened automatically.

## Friction Found

`codex-worker-batch-summary` correctly reported that draft `POL-0006` was blocked, but it still recommended `codex-worker-batch-run` in the main command and per-item next-action rows. That was confusing because a draft policy cannot be executed.

Tiny polish was applied:

- draft policies now recommend `execution-policy-request`
- requested policies now recommend `execution-policy-approve`
- per-item next-action rows match the policy approval state

## Manual Work Avoided

This dogfood avoided manually creating the first backlog tasks, batch, queue, and broad policy from the rough goal. The operator only had to inspect the materialized artifacts and create a narrower execution policy for the selected safe slice.

That is a meaningful reduction in spreadsheet-style planning work.

## Still Manual

- The operator still needs to decide which materialized task is the safe slice.
- A narrower policy still has to be created manually when the materialized draft policy is too broad.
- Approval remains explicit.
- Worker evidence, review evidence, validation evidence, and delivery request creation remain separate gates.
- The summary for `POL-0007` correctly links the delivery request, but one readout used `--confirm-runner-run` while `runner-latest` printed `--confirm-runner-delivery`; the runner-latest command should be treated as the clearest handoff command for now.

## Validation

- `.\.venv\Scripts\python -m py_compile src/devo/main.py src/devo/project_planning.py`: passed
- `.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k codex_worker_batch_summary_for_draft_policy --basetemp=E:\DevOrchestrator\pt-183-focused`: passed, 1 selected
- `.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py --basetemp=E:\DevOrchestrator\pt-183-planning`: passed, 220 tests
- `git diff --check`: passed
- `git diff --cached --check`: passed

## Delivery Handoff

`approved-queue-run` created delivery request `REQ-0071` after worker, review, and validation evidence were recorded.

Trusted runner command for normal PowerShell:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request REQ-0071 --approver "Manas" --confirm-runner-delivery
```

At the time of this report, the delivery request is waiting for trusted runner execution. No manual `git add`, `git commit`, or `git push` was used.

## Verdict

PASS with small UX polish.

`intake-materialize` produced usable draft planning artifacts, and one materialized queue item advanced through policy approval, worker evidence, review evidence, validation evidence, and delivery request creation. The task is now at the trusted-runner delivery boundary.

## Recommendation

TASK-DEVO-184 should consider a small `intake-materialization-status` or "narrow policy from materialized task" helper if this pattern repeats. Do not add more autonomy yet; the next useful improvement is reducing the policy-slicing command length while preserving explicit approval.
