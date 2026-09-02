# TASK-DEVO-179 Real Codex Valid Inline Patch Dogfood

## Goal

Retry the real Codex inline patch proposal path after TASK-DEVO-178 required `patch_proposal_text` to be a git-apply-compatible unified diff.

The target task remains the same tiny DevOrchestrator code polish: remove the redundant standalone `Project: <project>` line immediately under `Codex worker batch summary: <project>` and add focused coverage.

## Setup

- Project: `DevOrchestrator`
- Policy: `POL-0005`
- Batch: `B007`
- Queue: `Q007`
- Queue item: `QI001`
- Task: `T001`
- Queue-worker run: `QWR-0010`
- Worker run: `WR012`
- Codex worker run: `CWR-20260902072505-QWR-0010`
- Ingest: `CWI-20260902072649-QWR-0010`
- Patch artifact: `E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\patch-proposals\artifacts\QWR-0010\CWI-20260902072649-QWR-0010.patch`

Allowed files:

- `src/devo/main.py`
- `tests/test_project_planning.py`

## Real Codex Result

Real Codex launched from normal PowerShell and returned blocked worker evidence with inline patch intent. Devo materialized the inline patch proposal into a workspace `.patch` artifact, and `patch-proposal-show` passed.

This was the desired fallback boundary:

- Codex did not commit or push
- Devo did not treat patch-only evidence as completed work
- review evidence was not recorded
- validation evidence was not recorded
- delivery was not requested
- queue completion did not happen

## Strict Check Result

Strict check:

```powershell
.\.venv\Scripts\devo.exe project patch-proposal-check --project DevOrchestrator --run QWR-0010 --confirm-check
```

Result:

- Patch check: `PPC-20260902072945-QWR-0010`
- Status: `blocked`
- Reason: `git apply --check` failed because the patch did not apply strictly

Attempted apply:

- Patch apply: `PPA-20260902072946-QWR-0010`
- Status: `blocked`
- Reason: no latest successful patch-proposal-check artifact existed for the same patch hash

That was correct: Devo refused to apply a patch that had not passed its required check gate.

## Manual Diagnostic

Manual diagnostic from normal PowerShell showed:

```powershell
git apply --check --verbose <patch>
# strict_exit=1

git apply --check --ignore-space-change --ignore-whitespace --verbose <patch>
# ignore_whitespace_exit=0
```

The patch appears to be git-shaped and useful, but it needs whitespace-tolerant `git apply` behavior. Devo did not have an explicit audited mode for that yet.

## Polish Added

TASK-DEVO-179 adds explicit whitespace-tolerant patch proposal check/apply mode:

- strict check/apply remains the default
- `patch-proposal-check --ignore-whitespace --confirm-ignore-whitespace` runs `git apply --check --ignore-space-change --ignore-whitespace`
- `patch-proposal-apply --ignore-whitespace --confirm-ignore-whitespace` runs `git apply --ignore-space-change --ignore-whitespace`
- both check and apply artifacts record `patch_apply_mode`
- artifacts record the exact git apply args used
- apply requires a latest successful check with the same queue-worker run, same patch hash, and same patch apply mode
- strict apply cannot use a whitespace-tolerant check
- whitespace-tolerant apply cannot use a strict check
- apply remains working-tree-only and still does not stage, commit, push, record review/validation, create delivery, or complete the queue item

## Safety Verdict

PASS so far.

The real Codex fallback preserved useful implementation intent, and Devo correctly refused unsafe apply when the strict check failed. The new whitespace-tolerant mode is explicit and audited; there is no automatic fallback from strict mode.

## Recommendation

After this lands, TASK-DEVO-180 should resume `QWR-0010` by running an explicit whitespace-tolerant check. If it passes, use explicit reviewed whitespace-tolerant apply, inspect the real diff, run validation, then record normal evidence and deliver through the trusted runner.
