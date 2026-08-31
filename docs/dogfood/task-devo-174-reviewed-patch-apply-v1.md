# TASK-DEVO-174 Reviewed Patch-Proposal Apply V1

## Goal

Add the first reviewed patch-proposal apply command while preserving the safety boundary from TASK-DEVO-171 through TASK-DEVO-173.

The new command is:

```powershell
devo project patch-proposal-apply --project <project> --run <QWR-ID> --reviewed-by "Manas" --confirm-apply-patch
```

## Scope

TASK-DEVO-174 implements patch apply for a previously checked patch proposal only. It is not delivery automation.

The command can modify the target repository working tree, but it must not:

- stage files
- commit
- push
- complete queue items
- record normal review evidence
- record validation evidence
- create delivery requests
- run real Codex
- bypass the trusted runner

## Safety Gates

`patch-proposal-apply` requires:

- explicit `--confirm-apply-patch`
- non-empty `--reviewed-by`
- clean target Git worktree before apply
- queue-worker run exists
- latest ingested worker evidence exists
- worker status is `blocked` or `failed`, not `completed`
- patch proposal is present
- patch artifact exists
- patch artifact is in the target repo or approved Devo workspace artifact area
- latest successful `patch-proposal-check` exists for the same run and patch hash
- current patch hash matches the successful check
- touched files match the successful check
- patch touches only policy-allowed file patterns
- patch touches no forbidden files
- patch does not touch `workspace/**`, `.env`, `.venv/**`, `PersonalOS/**`, or `Personal OS/**`
- patch is not a binary patch
- patch paths are safe relative repository paths

If any gate fails, the command writes a blocked or failed apply artifact and does not apply the patch.

## Apply Artifact

Apply artifacts are workspace-only:

```text
workspace/projects/<project>/planning/patch-proposals/applies/<PPA-ID>/
  patch-proposal-apply.json
  patch-proposal-apply.md
```

They record:

- apply id
- project
- queue-worker run id
- worker evidence id
- policy id
- queue item id
- task id
- patch artifact path
- patch hash
- linked patch check id
- reviewed by
- status
- touched/rejected files
- blockers/warnings
- git status before and after
- `git apply` stdout/stderr
- next action
- safety note

## Operator Meaning

`Status: applied` means only:

```text
The patch was applied to the working tree.
```

It does not mean:

- the worker completed the task
- the patch is reviewed
- validation passed
- delivery is ready
- the queue item is complete

After apply, the operator must inspect `git diff`, run validation, record normal evidence only after actual applied changes are reviewed and validated, and then use the trusted runner delivery flow.

## Validation Shape

Focused tests cover:

- missing confirmation
- missing reviewer
- dirty worktree blocker
- completed worker evidence blocker
- missing patch proposal blocker
- missing successful check blocker
- changed patch hash blocker
- forbidden path blocker
- policy-scoped apply success
- unstaged working-tree diff after success
- no queue completion
- no review/validation/delivery evidence recording
- read-model visibility for latest apply artifacts

## Dogfood Boundary

TASK-DEVO-174 does not run `patch-proposal-apply` against the real DevOrchestrator repository. That should be a separate TASK-DEVO-175 dogfood using a disposable project or a fresh synthetic patch flow.

No real Codex CLI is run in this task.
