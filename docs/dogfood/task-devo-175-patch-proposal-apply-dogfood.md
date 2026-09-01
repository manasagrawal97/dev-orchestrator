# TASK-DEVO-175 Patch-Proposal-Apply Dogfood

## Goal

Dogfood `devo project patch-proposal-apply` with a fake blocked worker result and a valid, policy-scoped patch proposal.

The dogfood proves that reviewed patch apply can preserve the safety boundary:

- patch apply modifies the working tree only
- patch apply does not stage files
- patch apply does not commit or push
- patch apply does not complete queue items
- patch apply does not record normal review or validation evidence
- patch apply does not create a delivery request

No real Codex CLI was run.

## Setup

- Project: `DevOrchestrator`
- Batch: `B006`
- Queue: `Q006`
- Queue item: `QI001`
- Task: `T001`
- Policy: `POL-0004`
- Queue-worker run: `QWR-0006`
- Worker run: `WR008`

Policy `POL-0004` was intentionally narrow:

- allowed task: `T001`
- allowed queue item: `QI001`
- allowed file: `docs/dogfood/task-devo-175-patch-proposal-apply-dogfood.md`
- forbidden files: `.env`, `workspace/**`, `src/**`, `ui/**`
- max changed files per task: `1`
- validation command: `git diff --check`
- auto delivery: `False`
- auto push: `False`

The backlog task title attached to `T001` is historical from a prior dogfood task, but the execution policy is the active safety envelope for this run.

## Fake Worker Result

A synthetic blocked worker result was created under workspace artifacts and ingested through Devo.

- Fake result path: `E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\patch-proposals\dogfood-175\fake-blocked-worker-result.json`
- Patch artifact path: `E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\patch-proposals\dogfood-175\task-devo-175-report-title.patch`
- Ingest id: `CWI-20260901040132-QWR-0006`
- Worker evidence id: `qwr-0006-worker-result`
- Worker evidence status: `blocked`

The fake result reported:

- `status`: `blocked`
- `patch_proposal_present`: `true`
- `patch_artifact_path`: the `.patch` artifact above
- changed files: none
- failure details: synthetic write blocker with patch proposal produced

This kept the queue-worker before normal review, validation, delivery, and completion gates.

## Show Result

Command:

```powershell
.\.venv\Scripts\devo.exe project patch-proposal-show --project DevOrchestrator --run QWR-0006
```

Verdict: PASS.

`patch-proposal-show` displayed:

- patch proposal present: `True`
- patch artifact exists: `True`
- linked policy: `POL-0004`
- queue item: `QI001`
- task: `T001`
- safe next action: run `patch-proposal-check`
- safety note: read-only, no `git apply`, no queue/review/validation/delivery mutation, no commit, no push

Git status remained clean after show.

## Check Result

Command:

```powershell
.\.venv\Scripts\devo.exe project patch-proposal-check --project DevOrchestrator --run QWR-0006 --confirm-check
```

Verdict: PASS.

- Patch check id: `PPC-20260901040151-QWR-0006`
- Status: `checked`
- Patch hash: `9597dee7068393879cfb4ba3c8ed7220f52e9c4f99b714744e2d0cf7abd72026`
- Before git status: `clean`
- Dry-run apply supported: `True`
- Dry-run apply succeeded: `True`
- Touched files: `docs/dogfood/task-devo-175-patch-proposal-apply-dogfood.md`
- Rejected files: none
- Warnings: none
- Blockers: none

The command wrote only workspace check artifacts and did not apply the patch.

Tiny polish found: the check next-action still said "Future explicit patch apply" even though `patch-proposal-apply` now exists. TASK-DEVO-175 updates that wording to point at explicit reviewed apply after human review.

## Apply Result

Command:

```powershell
.\.venv\Scripts\devo.exe project patch-proposal-apply --project DevOrchestrator --run QWR-0006 --reviewed-by "Manas" --confirm-apply-patch
```

Verdict: PASS.

- Patch apply id: `PPA-20260901040201-QWR-0006`
- Status: `applied`
- Reviewed by: `Manas`
- Patch check: `PPC-20260901040151-QWR-0006`
- Patch hash: `9597dee7068393879cfb4ba3c8ed7220f52e9c4f99b714744e2d0cf7abd72026`
- Before git status: `clean`
- After git status: `staged 0, unstaged 0, untracked 1`
- Touched files: `docs/dogfood/task-devo-175-patch-proposal-apply-dogfood.md`
- Rejected files: none
- Warnings: none
- Blockers: none

The apply output clearly said:

- patch applied to the working tree only
- inspect `git diff`
- run validation
- record normal evidence only after actual applied changes are reviewed and validated
- use normal trusted delivery afterward
- patch applied does not mean task completed

## Safety Proof After Apply

After apply, Devo evidence still showed:

- queue-worker status: `waiting_worker`
- worker report status: `blocked`
- review exists: `False`
- validation evidence exists: `False`
- delivery request exists: `False`
- delivery request: none
- queue item: still not completed

Git status showed the applied dogfood report as an untracked working-tree file, with no staged files.

`codex-worker-batch-summary` initially showed the patch proposal and blocked state safely, but still used pre-apply wording. TASK-DEVO-175 adds narrow summary polish so it now reports:

- patch apply id/status/path
- next action: inspect diff, run validation, then record normal worker/review/validation evidence
- recommended command: `queue-worker-record-worker-result`

This preserves the safety boundary while reducing operator confusion.

## Validation Commands

Validation after apply should cover the actual docs diff plus the tiny source/test wording polish:

```powershell
.\.venv\Scripts\python -m py_compile src/devo/main.py src/devo/project_planning.py src/devo/read_models.py
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k "patch_proposal_apply or patch_proposal_check or patch_proposal_show or blocked_patch_proposal" --basetemp=E:\DevOrchestrator\pt-175-focused
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py --basetemp=E:\DevOrchestrator\pt-175-project-planning
git diff --check
git diff --cached --check
```

Results:

- `py_compile` for `src/devo/main.py`, `src/devo/project_planning.py`, and `src/devo/read_models.py`: passed
- focused patch proposal tests: `18 passed, 183 deselected`
- full `tests/test_project_planning.py`: `201 passed`
- known warning: pytest cache path warning under `.pytest_cache`
- final whitespace checks are run before delivery request creation

## Normal Evidence And Delivery

Patch apply itself did not record normal evidence. After manual diff inspection and validation, the operator may record normal evidence and create delivery through the usual Devo flow.

The dogfood delivery request for DevOrchestrator changes was created only after validation passed.

- Delivery runner request: `REQ-0063`
- Commit message: `feat: dogfood reviewed patch apply`
- Trusted runner command: `.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request REQ-0063 --approver "Manas" --confirm-runner-delivery`

Trusted runner remains the only committer/pusher.

## Verdict

PASS so far.

`patch-proposal-apply` successfully applied a fake safe patch to the working tree only, preserved all workflow gates, wrote an apply artifact, and did not stage/commit/push/complete anything.

## Friction Found

- `patch-proposal-check` next-action wording still referred to future apply. Fixed in this task.
- `codex-worker-batch-summary` did not initially surface apply artifacts or the post-apply next action. Fixed narrowly in this task.
- The policy used historical backlog task metadata because the live DevOrchestrator backlog currently has only `T001`. For this dogfood the execution policy was narrow enough to remain safe, but future dogfoods would benefit from easier ad hoc one-off dogfood task creation.

## Recommendation For TASK-DEVO-176

Dogfood the full patch-apply continuation after validation:

1. record completed worker evidence only after applied diff review
2. record passed review evidence
3. record passed validation evidence
4. create delivery request
5. let trusted runner commit/push
6. confirm queue item completion

Keep the next dogfood docs-only or disposable before relying on patch apply for live source-code work.
