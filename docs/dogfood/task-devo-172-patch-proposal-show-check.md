# TASK-DEVO-172 Patch Proposal Show/Check

## Goal

TASK-DEVO-172 adds the first safe patch-proposal commands before any patch application exists.

The goal is to let an operator inspect and preflight a Codex worker patch proposal when worker evidence is `blocked` or `failed`, without treating the patch as completed work.

## Commands Added

```powershell
devo project patch-proposal-show --project <project> --run <QWR-ID>
devo project patch-proposal-check --project <project> --run <QWR-ID> --confirm-check
```

`patch-proposal-show` is read-only. It locates the latest ingested worker evidence for a queue-worker run and reports the worker status, patch proposal presence, patch artifact path, artifact existence, linked policy, queue item, task, and safe next action.

`patch-proposal-check` requires `--confirm-check`. It still does not apply the patch. It creates a workspace-only check artifact after verifying the worker evidence and patch proposal:

- queue-worker run exists
- latest worker evidence exists
- worker status is `blocked` or `failed`, not `completed`
- patch proposal is present
- patch artifact exists
- patch artifact is in the target repo or approved Devo workspace artifact area
- target repo worktree is clean
- patch paths are safe relative repo paths
- patch touches no forbidden files
- patch touches only policy-allowed file patterns
- `git apply --check` succeeds when the static checks pass

Check artifacts are written under:

```text
workspace/projects/<project>/planning/patch-proposals/checks/<PPC-ID>/
  patch-proposal-check.json
  patch-proposal-check.md
```

## Safety Boundary

Patch proposal show/check do not:

- apply patches
- mutate queue state
- record normal review evidence
- record validation evidence
- create delivery requests
- commit
- push
- complete queue items

If a check passes, the task is still not complete. The next step is a future explicit patch-apply command or manual operator review, followed by normal diff review, validation, evidence recording, and trusted-runner delivery.

## Validation

Focused project-planning validation passed with a repo-local basetemp:

```text
191 passed
```

The first attempt without explicit basetemp hit a local Windows temp-directory permission problem, so the focused suite was rerun outside the restricted sandbox against `E:\DevOrchestrator\pt-172-focused`.

## Verdict

PASS for the show/check slice.

TASK-DEVO-172 makes patch proposals inspectable and checkable without widening autonomy. The safe next task is TASK-DEVO-173: dogfood show/check against the existing fake blocked patch evidence, then implement reviewed patch apply only after that layer is proven.
