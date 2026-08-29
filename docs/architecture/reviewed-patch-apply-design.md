# Reviewed Patch-Apply Design

## 1. Purpose

TASK-DEVO-171 designs the reviewed patch-apply workflow before implementation.

Patch proposals exist because a Codex subprocess may understand a safe change but be unable to update existing files in the target repository. TASK-DEVO-169 lets blocked or failed worker evidence preserve that implementation intent as a `.patch` or `.diff` artifact. TASK-DEVO-170 proved the fallback with fake blocked worker evidence.

The key boundary remains:

- a patch proposal is evidence, not completed work
- applying a patch is a separate explicit operator action
- applying a patch does not mean the task is reviewed, validated, delivered, or complete
- trusted runner remains the only commit/push path

This document is design-only. It does not implement patch application.

## 2. Proposed Command Model

Future commands should be project-scoped and tied to a queue-worker run:

```powershell
devo project patch-proposal-show --project <project> --run <QWR-ID>
devo project patch-proposal-check --project <project> --run <QWR-ID> --confirm-check
devo project patch-proposal-apply --project <project> --run <QWR-ID> --reviewed-by "Manas" --confirm-apply-patch
```

`patch-proposal-show` should be read-only. It displays the linked worker evidence, proposal path, patch hash if available, current queue-worker status, policy scope, and the safe next command.

`patch-proposal-check` should be an explicit dry-run/preflight command. It must not modify the target repository. It should verify that the patch is known to Devo, applies cleanly in dry-run mode, and touches only allowed files.

`patch-proposal-apply` should be the first write command. It should require an operator-reviewed patch, an explicit confirmation flag, and a clean pre-apply repository. It should apply the patch only; it must not commit, push, mark review passed, mark validation passed, or complete the queue item.

## 3. Safety Gates

The apply command must require all of these gates before writing:

- target Git worktree is clean before apply
- patch file path comes from ingested worker evidence
- linked worker status is `blocked` or `failed`, not `completed`
- patch proposal is present
- patch file exists
- patch only touches policy-allowed files
- patch touches no forbidden files
- patch does not touch `workspace/**`
- patch does not touch `.env`
- patch does not touch `.venv/**`
- patch does not touch PersonalOS unless a future PersonalOS-specific policy explicitly allows it
- patch does not touch paths outside the target repository
- patch passes a dry-run apply check first
- operator passes an explicit confirm flag
- command records who reviewed/applied the patch
- command does not commit or push
- command does not complete the queue item

If any gate fails, the command should create a blocked/failed check artifact and leave the target repo unchanged.

## 4. State And Artifact Model

Patch proposal checks and applies should create workspace-only artifacts under a future directory such as:

```text
workspace/projects/<project>/planning/patch-proposals/
  checks/<PPC-ID>/
    patch-proposal-check.json
    patch-proposal-check.md
  applies/<PPA-ID>/
    patch-proposal-apply.json
    patch-proposal-apply.md
```

The check artifact should contain:

- check id
- project
- queue-worker run id
- linked worker evidence id
- patch artifact path
- patch hash
- status: `checked`, `blocked`, or `failed`
- policy id and queue item id
- changed files detected from the patch
- rejected files
- warnings
- blockers
- dry-run command/method used
- before git status
- next recommended action
- timestamp
- recorded by

The apply artifact should contain:

- apply id
- linked check id
- project
- queue-worker run id
- linked worker evidence id
- patch artifact path
- patch hash
- status: `applied`, `blocked`, or `failed`
- changed files
- rejected files
- warnings
- blockers
- before git status
- after git status
- reviewed by
- applied by
- timestamp
- next recommended action

Artifacts are evidence for the patch-apply step only. They should not replace worker, review, validation, delivery, or queue completion evidence.

## 5. Workflow After Patch Apply

After a patch is applied:

1. Operator reviews the actual repository diff.
2. Operator runs the policy-required validation.
3. Operator records normal review evidence only after the applied diff is acceptable.
4. Operator records validation evidence only after validation passes.
5. Devo can then create a delivery request through the existing queue-worker path.
6. Trusted runner commits and pushes.
7. Queue completion happens only after trusted delivery is complete and pushed.

Patch apply should move the task from "useful proposal preserved" to "local changes exist for review." It should not skip the existing gates.

## 6. UX Guidance

Command output should prevent false confidence:

```text
Patch applied. This does not complete the task.
Review the actual diff, run validation, then record normal review and validation evidence.
Trusted runner remains the only commit/push path.
```

For patch-only evidence before apply:

```text
Patch proposal present.
Review patch proposal manually.
Do not record normal review/validation/delivery until changes are actually applied and validated.
```

For failed checks:

```text
Patch check failed.
Do not manually force the patch.
Resolve blockers or request a new worker result.
```

The output should show one safe next command when possible. It should avoid recommending review, validation, delivery, or retry as the main action while the only evidence is an unapplied patch proposal.

## 7. Threat Model And Risks

The patch-apply path must assume patch files are untrusted input.

Risks to guard against:

- malicious patch touching forbidden files
- path traversal such as `../` or absolute paths
- patch generated from the wrong repository
- stale patch generated against an old HEAD
- patch partially applying
- line-ending mismatch causing noisy or partial changes
- binary file patches
- patch modifies tests only to fake success
- patch edits generated files or workspace artifacts
- patch edits `.env`, secrets, local settings, backups, or scheduler files
- accidental commit of workspace artifacts

The first implementation should prefer a blocked result over a clever recovery. A failed dry-run check should not be followed by automatic fallback strategies.

## 8. Future Implementation Phases

### Phase A: Read-Only Show And Check

Implement `patch-proposal-show` and `patch-proposal-check`.

The check command should parse the patch, list changed files, enforce policy allowed/forbidden paths, verify the patch path came from worker evidence, and run a dry-run apply check without modifying the repo.

### Phase B: Explicit Apply

Implement `patch-proposal-apply` with a dry-run precheck, clean-worktree requirement, explicit `--confirm-apply-patch`, and apply evidence artifact.

The command should apply only the patch. It must not record review, validation, delivery, or queue completion.

### Phase C: Fake Patch Dogfood

Dogfood the full show/check/apply path against a disposable project and a fake blocked worker result.

### Phase D: Real Codex Patch Proposal Dogfood

Use real Codex only from normal PowerShell and only against a narrow disposable or DevOrchestrator policy. The result should prove that a real blocked worker can provide a patch proposal and the operator can apply it through the reviewed flow.

### Phase E: Optional UI Readout

Add read-only UI visibility for patch proposals, checks, and apply artifacts. Do not add UI apply buttons until the safety model has more dogfood evidence.

## 9. Recommendation For TASK-DEVO-172

TASK-DEVO-172 should start with Phase A only:

- add read-only `patch-proposal-show`
- add explicit dry-run `patch-proposal-check --confirm-check`
- create check artifacts
- enforce worker evidence linkage
- enforce blocked/failed worker status
- enforce policy allowed/forbidden path checks
- verify that a dry-run apply would succeed
- add tests with synthetic `.patch` fixtures

Do not implement patch application in TASK-DEVO-172 unless the show/check layer is already proven and separately approved. The smallest safe slice is read-only display plus check artifacts, because it improves operator confidence without creating target repo changes.

## 10. Acceptance Criteria For Future Apply

The eventual apply implementation should be accepted only if:

- patch proposal path comes from ingested worker evidence
- patch-only evidence remains non-completed
- dry-run check blocks forbidden/out-of-repo/generated/workspace/secret paths
- apply requires a clean worktree and explicit confirmation
- apply records before/after git status and patch hash
- apply does not commit or push
- apply does not record normal review or validation
- apply does not complete the queue item
- after apply, the main next action is review actual diff and run validation
- tests cover blocked, failed, stale, forbidden path, out-of-repo path, and successful apply cases

Reviewed patch apply should make the fallback useful without making it sneaky. The operator stays in charge, Devo preserves evidence, and delivery remains trusted-runner-only.
