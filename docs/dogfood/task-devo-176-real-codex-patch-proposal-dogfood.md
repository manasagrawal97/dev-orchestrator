# TASK-DEVO-176 Real Codex Patch-Proposal Dogfood

## Goal

Prove the real Codex patch-proposal fallback path for a narrow DevOrchestrator code task:

real Codex subprocess -> blocked worker result with patch proposal -> Devo ingest -> patch proposal show/check/apply -> manual validation/review -> trusted delivery.

This task intentionally stopped before applying the real Codex patch because the first dogfood revealed a missing bridge: real Codex returned the patch proposal inline in JSON instead of writing a separate `.patch` artifact.

## Setup

- Project: `DevOrchestrator`
- Batch: `B007`
- Queue: `Q007`
- Queue item: `QI001`
- Task: `T001`
- Policy: `POL-0005`
- Queue-worker run: `QWR-0007`
- Codex worker run: `CWR-20260901052027-QWR-0007`
- Ingest: `CWI-20260901052116-QWR-0007`
- Batch run: `CWBR-0009`

Policy `POL-0005` allowed only:

- `src/devo/main.py`
- `tests/test_project_planning.py`

The requested tiny code polish was to remove the redundant standalone `Project: <project>` line immediately under the `Codex worker batch summary: <project>` heading and add focused coverage.

## Observed Real Codex Result

Real Codex returned strict JSON and Devo ingested it successfully. The worker status was `blocked`.

Summary:

> The safe change was identified, but both approved files were unwritable through the required patch mechanism.

Devo correctly preserved this as non-success worker evidence:

- worker status stayed blocked
- review evidence was not recorded
- validation evidence was not recorded
- delivery request was not created
- queue item was not completed
- no commit or push happened

## Friction Found

The worker result included a patch proposal inline in the raw JSON, but did not provide `patch_artifact_path`.

Before TASK-DEVO-176 materialization polish:

- `codex-worker-batch-summary` showed `patch proposal: yes; artifact=provided inline in raw result`
- `patch-proposal-show` showed `Patch proposal present: True`, `Patch artifact path: none`, and `Patch artifact exists: False`
- `patch-proposal-check` correctly blocked with `Patch proposal is present but no patch artifact path was provided.`

This was safe, but it meant useful implementation intent could not proceed through show/check/apply without asking for a fresh worker result.

## Materialization Polish

TASK-DEVO-176 adds a small ingest-time bridge:

- if a blocked/failed worker result includes inline patch proposal content and no patch artifact path, confirmed `codex-worker-ingest` writes the inline patch text to a workspace artifact
- the materialized path is stored as `patch_artifact_path`
- downstream `patch-proposal-show` and `patch-proposal-check` can use the materialized `.patch`
- explicit `patch_artifact_path` behavior remains unchanged
- dry-run ingest remains non-mutating and does not materialize a patch

Materialized patches are written under:

```text
workspace/projects/<project>/planning/patch-proposals/artifacts/<QWR-ID>/<CWI-ID>.patch
```

The CLI now warns:

```text
Inline patch proposal was materialized as a workspace artifact; it is still not applied work.
```

## Validation

Validation for the materialization bridge:

```powershell
.\.venv\Scripts\python -m py_compile src/devo/main.py src/devo/project_planning.py
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k "inline_patch or patch_proposal_check or patch_proposal_show or patch_proposal_apply" --tb=short --basetemp=E:\DevOrchestrator\pt-176-focused-3
```

Results:

- `py_compile`: passed
- focused patch proposal tests: `17 passed, 185 deselected`
- known warning: pytest cache warning under `.pytest_cache`

## Delivery Request

DevOrchestrator delivery is handed to the trusted runner:

- Runner request: `REQ-0064`
- Commit message: `feat: materialize inline patch proposals`
- Trusted runner command:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request REQ-0064 --approver "Manas" --confirm-runner-delivery
```

## Safety Verdict

PASS for the new materialization behavior.

The real Codex dogfood remains PARTIAL until a fresh real worker result, or another explicit ingest path, produces a materialized patch artifact that can be checked and applied. The important safety behavior held: inline patch evidence was not treated as completed work.

No real patch was applied in this materialization task. No normal review, validation, delivery, queue completion, commit, or push was recorded from patch-only evidence.

## Recommendation

TASK-DEVO-177 should retry the narrow real Codex patch-proposal dogfood after this bridge is delivered, or add a tightly scoped recovery command for materializing inline patch proposals from existing ingests without changing their worker status.
