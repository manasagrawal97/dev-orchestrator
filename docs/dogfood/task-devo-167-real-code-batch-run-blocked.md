# TASK-DEVO-167 Real Code Batch-Run Blocked

## Verdict

BLOCKED safely. TASK-DEVO-167 attempted the first narrow real Codex batch-run against DevOrchestrator source code. Devo correctly ingested strict JSON worker results, preserved the blocked evidence, and stopped before review, validation, delivery request, commit, or push.

This is a useful dogfood result: the control plane behaved safely when the worker could inspect files but could not update existing source files.

## Scope

- Project: `DevOrchestrator`
- Policy: `POL-0003`
- Batch / queue: `B005` / `Q005`
- Queue item / task: `QI001` / `T001`
- Allowed files:
  - `src/devo/main.py`
  - `tests/test_project_planning.py`
- Intended tiny change: remove the duplicate `Project: DevOrchestrator` line printed immediately under `Codex worker batch summary: DevOrchestrator`, plus add focused output coverage.

## Attempts

First attempt:

- Queue-worker run: `QWR-0003`
- Codex worker run: `CWR-20260828163855-QWR-0003`
- Ingest: `CWI-20260828164102-QWR-0003`
- Worker evidence: `blocked`

Second attempt:

- Queue-worker run: `QWR-0004`
- Codex worker run: `CWR-20260828175012-QWR-0004`
- Ingest: `CWI-20260828175147-QWR-0004`
- Worker evidence: `blocked`

Both attempts produced valid strict JSON. Both were ingested as non-success evidence.

## Blocker

The real Codex subprocess could inspect the approved files and create a temporary probe file, but it could not update existing files:

- `apply_patch` failed with `Failed to write file`.
- Direct file writes failed with `UnauthorizedAccessException`.
- No source or test file changes landed.
- The DevOrchestrator repo remained clean.

Normal PowerShell later confirmed it could open the same two files with read-write access. That points to a process/context permission difference for the Codex subprocess rather than a normal Git dirty-state problem or a Devo policy mismatch.

## Safety Result

Devo did the right thing:

- It did not treat `status=blocked` as completed work.
- It did not recommend review, validation, or delivery as if implementation existed.
- It did not create a delivery request.
- It did not commit or push.
- It preserved the raw result and worker evidence artifacts for audit.

Review and validation were not recorded because there was no implemented code change to review or validate.

## Recommendation

Before retrying real Codex code edits on DevOrchestrator, diagnose the subprocess write context. Compare the launcher path, wrapper, working directory, Windows security context, and file write permissions from normal PowerShell versus the Codex child process.

If the worker can produce a patch but cannot edit existing files, prefer a future patch-proposal fallback:

1. Codex writes a patch/diff artifact instead of editing source files.
2. The operator reviews the patch artifact.
3. A separate trusted/local command applies it only after explicit approval.
4. Trusted runner remains the only commit/push path.

TASK-DEVO-168 adds safer CLI guidance for this blocked state and documents the diagnostic path. Do not keep retrying `codex-worker-batch-run` blindly after access-denied blocked evidence.

## Confirmations

- No PersonalOS files were touched.
- No real Codex commit or push occurred.
- No review, validation, or delivery request was recorded for the blocked worker output.
- Workspace artifacts were evidence only and should not be committed.
