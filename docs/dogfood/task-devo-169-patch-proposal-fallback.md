# TASK-DEVO-169 Patch-Proposal Fallback

## Goal

Preserve useful implementation intent when a real Codex subprocess understands a scoped change but cannot update existing tracked files.

## Result

TASK-DEVO-169 adds patch-proposal fallback v1. Devo can now ingest blocked or failed worker-result JSON that includes a patch proposal signal, keep the worker status blocked/failed, and show manual patch-review guidance in the operator-facing readouts.

Supported signals:

- `patch_proposal_present: true`
- `patch_artifact_path: "<path-to.patch>"`
- `patch_proposal_path` or `patch_path`
- `artifact_path` ending in `.patch` or `.diff`
- inline `patch_proposal` text in the raw result JSON

## Safety Boundary

Patch proposals are not applied work.

Devo does not:

- apply the patch
- record normal review automatically
- record validation automatically
- create delivery automatically
- run the trusted runner
- commit or push

The next action for a blocked/failed patch-only result is:

```text
Review patch proposal manually. Do not record normal review/validation/delivery until changes are actually applied and validated.
```

## Operator Flow

1. Inspect the blocked worker ingest or batch summary.
2. Review the patch artifact manually.
3. Decide whether to apply it through a future explicit trusted/local patch-apply command or by a separately approved manual/Codex edit flow.
4. Validate the actually applied change.
5. Only then continue normal review, validation, delivery request, and trusted runner delivery gates.

## Why This Matters

TASK-DEVO-167 showed that the Codex subprocess could inspect approved source/test files and produce strict JSON, but could not update existing files in the current process context. Patch-proposal fallback keeps the useful reasoning and proposed implementation from being lost while preserving Devo's safety model.

## Remaining Work

Future work may add a separate explicit patch-apply command with its own approval and validation gates. That is intentionally out of scope for TASK-DEVO-169.
