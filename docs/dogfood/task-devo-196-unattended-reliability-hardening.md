# TASK-DEVO-196 Unattended Reliability Hardening

## Purpose

TASK-DEVO-195 exposed two failures that make an otherwise bounded unattended run require manual recovery:

- Windows could decode captured Codex output through the active locale (commonly cp1252). UTF-8 or malformed bytes could raise in a subprocess reader thread and lose useful worker diagnostics.
- a first worker attempt could leave legitimate in-scope WIP, but its linked retry hit the unconditional clean-repository preflight and could not continue that exact work.

This task hardens those two boundaries without changing review, validation, delivery, commit, push, scheduler, or parallel-worker semantics.

## Hardened Behavior

Both configured Codex subprocess execution and the older supervised Codex execution path now pass explicit `encoding="utf-8"` and `errors="replace"` capture settings. Timeout output uses the same decoder. Unexpected bytes therefore appear as the Unicode replacement character in UTF-8 log artifacts while the surrounding stdout/stderr remains available for classification and diagnosis.

Each configured worker attempt also records deterministic before/after Git-state fingerprints. The fingerprint covers branch and HEAD identity, staged/unstaged/untracked path categories, binary staged and unstaged Git diffs, and raw untracked-file content.

Dirty execution is still denied unless every bounded retry condition is true:

- the run directly links its parent through `retry_of`;
- policy, queue, item, task, and handoff lineage are unchanged;
- the latest parent subprocess attempt recorded a dirty after-state fingerprint;
- branch, HEAD, and staged/unstaged/untracked path sets exactly match;
- current content produces the same fingerprint;
- every changed path remains inside approved policy/task scope and outside forbidden scope;
- the changed-file count stays within the approved policy limit.

Any missing artifact, older artifact without a fingerprint, new file, content edit, staging change, branch/HEAD change, scope violation, or lineage mismatch blocks before subprocess launch. There is no general dirty-repository override.

## Automated Exact-Inherited-WIP Success Coverage

Focused fake-worker coverage exercises the successful bounded path:

1. A fake subprocess writes invalid UTF-8 bytes to both stdout and stderr and still writes a valid result. The run completes with result evidence, and both log files preserve the invalid byte as Unicode replacement character `U+FFFD`.
2. A parent fake worker creates one allowed untracked source file. An immediately linked retry sees the exact same WIP, proves the parent fingerprint and scope, runs successfully, and records `inherited_wip_verified=true` plus `inherited_wip_from_run_id=QWR-0001`.

## Automated Fail-Closed Coverage

Focused regression coverage proves that a linked retry blocks before creating its subprocess-run artifact when:

- inherited file content changes;
- a new or unrelated dirty file appears after the parent attempt;
- inherited WIP falls outside the policy allowed-file scope or matches a forbidden-file pattern;
- the parent subprocess artifact predates `git_state_fingerprint_after` and therefore cannot prove its baseline;
- the same path moves between untracked and staged Git-state categories; or
- the repository branch changes after the parent attempt.

The ordinary non-retry dirty-repository rejection and invalid UTF-8 stdout/stderr capture tests remain in place. There is no generic dirty-tree bypass.

## Live QWR-0041 Dogfood Result

The real QWR-0041 correction attempt linked to QWR-0040 and encountered intentional TASK-DEVO-196 WIP. QWR-0040 was created before retry fingerprints were recorded, so its subprocess artifact had no `git_state_fingerprint_after`. QWR-0041 correctly failed closed before subprocess launch because that legacy parent baseline could not be cryptographically proven. This is expected safety behavior and was not weakened.

The earlier UTF-8 and exact-inherited-WIP tests passed when invoked directly in isolated local fixtures. In this restricted correction context, both the new focused selection and the registered pytest selection were blocked at fixture setup by an environment-level `%TEMP%` `Access is denied` cleanup error, so the new cases still require operator-side execution. Python compilation and both Git diff checks passed.

## Safety Result

Worker result ingest, deterministic review, approved validation, delivery requests, and trusted-runner-only commit/push behavior are unchanged. The new evidence only decides whether one linked retry may start with proven parent WIP. Human semantic review remains required for this medium-risk change.
