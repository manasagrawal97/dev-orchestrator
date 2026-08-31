# TASK-DEVO-173 Patch-Proposal Show/Check Dogfood

## Goal

Dogfood the TASK-DEVO-172 patch-proposal inspection commands against the fake blocked worker evidence from TASK-DEVO-170.

The commands under test were:

```powershell
.\.venv\Scripts\devo.exe project patch-proposal-show --project DevOrchestrator --run QWR-0005
.\.venv\Scripts\devo.exe project patch-proposal-check --project DevOrchestrator --run QWR-0005 --confirm-check
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project DevOrchestrator --policy POL-0003
```

No real Codex CLI was run, and no patch was applied.

## Source Evidence

- Project: `DevOrchestrator`
- Policy: `POL-0003`
- Batch: `B005`
- Queue: `Q005`
- Queue item: `QI001`
- Task: `T001`
- Queue-worker run: `QWR-0005`
- Preparation: `CWP-20260829130934-QWR-0005`
- Ingest: `CWI-20260829130957-QWR-0005`
- Worker evidence id: `qwr-0005-worker-result`
- Worker status: `blocked`

Patch proposal artifact:

```text
E:\DevOrchestrator\workspace\projects\DevOrchestrator\codex-worker\preparations\CWP-20260829130934-QWR-0005\task-devo-170-proposed.patch
```

## Show Verdict

`patch-proposal-show` correctly reported:

- patch proposal present: `True`
- patch artifact path
- patch artifact exists: `True`
- linked policy: `POL-0003`
- queue item: `QI001`
- task: `T001`
- ingest: `CWI-20260829130957-QWR-0005`
- safe next action: run the non-mutating patch check
- read-only safety text: no `git apply`, queue mutation, review, validation, delivery, commit, or push

Verdict: PASS.

## Check Verdict

`patch-proposal-check --confirm-check` created a check artifact:

```text
E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\patch-proposals\checks\PPC-20260831131102-QWR-0005\
```

The check blocked safely:

- worker status was `blocked`, which is valid for patch-proposal fallback
- target repo status before check was clean
- touched file parsed as `src/devo/main.py`
- no forbidden file path was accepted
- `git apply --check` failed because the TASK-DEVO-170 proposal was intentionally only a minimal proposal snippet, not a fully applyable patch
- no source file was changed
- no queue/review/validation/delivery state was advanced

Blocker:

```text
git apply --check failed: error: patch with only garbage at ...\task-devo-170-proposed.patch:4
```

Verdict: PASS for safety and artifact creation; PARTIAL for applyability because the older fake proposal was not a valid patch. This is acceptable dogfood friction and should inform TASK-DEVO-174.

## Summary Verdict

`codex-worker-batch-summary --project DevOrchestrator --policy POL-0003` correctly reported:

- `QI001 / T001`
- `qwr=QWR-0005`
- worker evidence: `blocked`
- review evidence: `missing`
- validation evidence: `not_provided`
- patch proposal present and artifact path
- no delivery request
- no trusted runner run
- no commit or push
- next action: review patch proposal manually and do not record normal review/validation/delivery until changes are actually applied and validated

TASK-DEVO-173 also found one small wording polish: the summary next action was safe, but the recommended command still pointed back to `codex-worker-batch-summary`. The command now recommends:

```powershell
devo project patch-proposal-show --project DevOrchestrator --run QWR-0005
```

This keeps the operator on the patch-inspection path instead of a summary self-loop.

## Mutation Check

The dogfood confirmed:

- no patch was applied
- no normal review evidence was recorded
- no validation evidence was recorded
- no delivery request was created
- no queue item was completed
- no commit or push occurred
- Git status remained clean before TASK-DEVO-173 source/docs/test edits
- only workspace patch-check artifacts were written by the check command

Forbidden-path blocking is covered by focused tests for patch-proposal check. The reused TASK-DEVO-170 patch did not exercise a forbidden path directly; it exercised invalid/non-applyable patch blocking.

## Friction Found

- Older fake patch proposals may be proposal snippets rather than fully applyable unified diffs.
- The dogfood report should distinguish "proposal present" from "proposal can pass dry-run apply".
- Batch summary should point operators to `patch-proposal-show` or `patch-proposal-check` when patch-only evidence exists.

## Recommendation For TASK-DEVO-174

Dogfood with a fresh fake blocked worker result whose patch artifact is a valid unified diff and passes `git apply --check`, while still not applying it. That should prove the positive check path before implementing any reviewed patch-apply command.

TASK-DEVO-174 should remain no-apply unless separately approved.

## Verdict

PASS.

Patch-proposal show/check are useful and safe. The check command preserves the key boundary: a patch proposal is not completed work, and the operator must not record normal review, validation, delivery, or queue completion until a patch is explicitly applied and validated through a later approved flow.
