# TASK-DEVO-178 Real Codex Inline Patch End-to-End Dogfood

## Goal

Retry the real Codex inline patch-proposal flow after TASK-DEVO-177 added the canonical `patch_proposal_text` field to the worker result contract.

The target task stayed intentionally tiny: remove the redundant standalone `Project: <project>` line immediately under `Codex worker batch summary: <project>` and add focused coverage.

## Setup

- Project: `DevOrchestrator`
- Policy: `POL-0005`
- Batch: `B007`
- Queue: `Q007`
- Queue item: `QI001`
- Task: `T001`
- Queue-worker retry run: `QWR-0009`
- Worker run: `WR011`
- Codex worker run: `CWR-20260902063844-QWR-0009`
- Ingest: `CWI-20260902064051-QWR-0009`
- Batch run: `CWBR-0011`

Allowed files:

- `src/devo/main.py`
- `tests/test_project_planning.py`

## Real Codex Result

Real Codex launched from normal PowerShell and returned strict JSON with `status=blocked`. This was the expected safe fallback because the subprocess still could not update existing tracked source/test files.

This time the worker result included inline `patch_proposal_text`. Confirmed ingest materialized that inline patch into:

```text
E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\patch-proposals\artifacts\QWR-0009\CWI-20260902064051-QWR-0009.patch
```

`patch-proposal-show` worked as intended:

- patch proposal present: yes
- patch artifact path: materialized workspace `.patch`
- patch artifact exists: yes
- no apply, review, validation, delivery, commit, push, or queue completion occurred

## Patch Check Result

`patch-proposal-check` created:

- Patch check: `PPC-20260902064131-QWR-0009`
- Status: `blocked`

The blocker was:

```text
git apply --check failed with corrupt patch at line 11
```

The patch proposal was semantically correct, but it was not `git apply` compatible. The hunk header declared line counts that the hunk body did not satisfy, so Devo correctly refused to apply it.

## Safety Verdict

PASS for fallback safety.

The important safety behavior held:

- inline `patch_proposal_text` was preserved as a workspace artifact
- `patch-proposal-show` could inspect it
- `patch-proposal-check` blocked the malformed patch
- no patch was applied
- no normal review evidence was recorded
- no validation evidence was recorded
- no delivery request was created
- no queue item was completed
- no commit or push occurred
- the repository remained clean

## Polish Added

TASK-DEVO-178 tightens the worker prompt/result contract:

- `patch_proposal_text` must contain a valid git-apply-compatible unified diff
- the diff must include `diff --git` headers
- the diff must include `--- a/...` and `+++ b/...` file headers
- hunk headers must have correct line numbers and line counts
- hunk bodies must include enough context/removal/addition lines to satisfy the hunk header
- rough/snippet diffs, absolute-path diffs, and incomplete hunks are not acceptable
- if the worker cannot produce a valid patch, it should leave `patch_proposal_present=false` and explain why in `failure_details`
- patch-only output remains `blocked` or `failed`, never `completed`

`patch-proposal-check` guidance now calls out corrupt patches explicitly: do not apply, request a fresh worker result with a valid git-apply-compatible unified diff in `patch_proposal_text`, and do not manually force-apply or edit source files outside the reviewed patch flow.

## Friction Found

Real Codex understood the tiny change and used the new inline field, but it produced a snippet-like patch with inconsistent hunk counts. That is enough for human understanding but not enough for safe `git apply --check`.

## Recommendation

TASK-DEVO-179 should retry this same narrow real Codex patch-proposal path after the prompt/check guidance lands. Success criteria for the next retry:

```text
blocked JSON with valid patch_proposal_text
-> ingest materializes workspace .patch
-> patch-proposal-show
-> patch-proposal-check passes
-> reviewed patch-proposal-apply
-> manual diff review
-> validation
-> normal review/validation evidence
-> trusted delivery
```
