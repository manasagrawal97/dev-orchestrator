# Codex Subprocess Write-Access Diagnostics

## Purpose

Use this runbook when a real Codex subprocess can inspect a repository but cannot update existing approved files.

This is different from a normal policy block. The worker may have the right Devo policy, the right allowed file list, and a valid result JSON, but still report access-denied failures while editing.

## Symptoms

Common signals:

- Codex can read or search the approved files.
- Codex can create a new temporary probe file.
- Codex cannot update existing source or test files.
- `apply_patch` reports `Failed to write file`.
- Direct writes report `UnauthorizedAccessException`, `access denied`, or `permission denied`.
- Normal PowerShell can open the same files with read-write access.
- The target repo remains clean.

When these appear, stop. Do not record review or validation. Do not create delivery.

## Things To Check

Check the launcher path:

- Is Devo using the current intended Codex executable?
- Is the path stale after a Codex app update?
- Is the command a WindowsApps alias? WindowsApps aliases remain blocked for guarded execution.
- Would `codex.cmd` or an explicit wrapper behave differently than the pinned local `codex.exe`?

Check the process context:

- Is the real Codex subprocess launched from normal PowerShell?
- Is the parent process running under the expected Windows user?
- Does the subprocess inherit a restricted sandbox or protected file policy?
- Does antivirus or Controlled Folder Access treat child-process writes differently?

Check filesystem behavior:

- Can normal PowerShell open the file read-write?
- Can the Codex subprocess update an existing file, not just create a new file?
- Are file attributes, ACLs, or repository ownership unusual?
- Is the repository in a synced or protected folder?

## Safe Stop Rule

If worker evidence is `blocked` because existing-file writes failed:

1. Do not record review.
2. Do not record validation.
3. Do not create a delivery request.
4. Do not retry repeatedly without changing the launcher or permission context.
5. Preserve the blocked result as diagnostic evidence.

## Patch-Proposal Fallback

If write access remains unreliable, Devo can now preserve a worker's implementation intent as a patch proposal:

- Codex reports `status=blocked` or `status=failed` when it cannot edit files.
- Codex can include `patch_proposal_present: true`.
- Codex can point `patch_artifact_path` or `artifact_path` at a `.patch` or `.diff` artifact.
- Devo ingest, `queue-worker-evidence`, and `codex-worker-batch-summary` surface the patch proposal and its path.
- `devo project patch-proposal-show --project <project> --run <QWR-ID>` inspects the linked proposal without mutation.
- `devo project patch-proposal-check --project <project> --run <QWR-ID> --confirm-check` writes a workspace-only check artifact and can run `git apply --check` without applying the patch.
- The patch artifact is reviewed by the operator.
- `devo project patch-proposal-apply --project <project> --run <QWR-ID> --reviewed-by "Manas" --confirm-apply-patch` can apply a previously checked proposal as an explicit operator action.
- Normal review and validation evidence are still required.
- Trusted runner remains the only commit/push path.

This fallback does not auto-apply patches inside `codex-worker-batch-run`. Applying a patch is a separate write action and needs its own explicit safety gate. Do not record normal review, validation, or delivery for a patch-only result until the patch has actually been applied and validated.

TASK-DEVO-171 designs that gate in `docs/architecture/reviewed-patch-apply-design.md`; TASK-DEVO-172 implements the read-only show/check slice; TASK-DEVO-174 implements explicit reviewed apply. Apply requires a clean worktree, proves the patch came from ingested worker evidence, enforces policy allowed/forbidden files, records who reviewed/applied it, and still avoids commit, push, normal evidence recording, and queue completion.

TASK-DEVO-173 dogfoods show/check against existing fake blocked evidence. The check command can safely reject a non-applyable proposal while preserving the artifact for review; rejected checks are not evidence that the task is implemented. TASK-DEVO-174 adds apply for checked proposals only; use a disposable or synthetic dogfood before relying on it for live code work.

Expected worker-result shape:

```json
{
  "status": "blocked",
  "summary": "Could not update existing files; patch proposal produced for manual review.",
  "work_performed": [],
  "changed_files": [],
  "commands_run": ["attempted apply_patch"],
  "risks": ["write access blocked"],
  "recommended_next_action": "",
  "artifact_path": "path/to/proposed.patch",
  "patch_proposal_present": true,
  "patch_artifact_path": "path/to/proposed.patch",
  "dirty_repo_status": "clean",
  "usage_limit_details": "",
  "failure_details": "Failed to write file; UnauthorizedAccessException"
}
```

## What Not To Do

- Do not use `shell=True` to bypass launcher problems.
- Do not use dangerous sandbox bypasses by default.
- Do not weaken allowed/forbidden file policy.
- Do not treat a blocked worker result as reviewable implementation.
- Do not bypass Devo delivery with manual `git add`, `git commit`, or `git push` during dogfood.

## Related Docs

- `docs/dogfood/task-devo-167-real-code-batch-run-blocked.md`
- `docs/runbooks/codex-launcher-setup.md`
- `docs/runbooks/real-codex-supervised-dry-run.md`
- `docs/architecture/real-codex-batch-run-readiness-checkpoint.md`
- `docs/architecture/reviewed-patch-apply-design.md`
