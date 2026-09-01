# TASK-DEVO-177 Real Codex Inline Patch Retry Dogfood

## Goal

Retry the real Codex patch-proposal fallback after TASK-DEVO-176 added inline patch materialization.

The target task remained intentionally tiny: remove the redundant standalone `Project: <project>` line immediately under `Codex worker batch summary: <project>` and add focused coverage.

## Setup

- Project: `DevOrchestrator`
- Policy: `POL-0005`
- Batch: `B007`
- Queue: `Q007`
- Queue item: `QI001`
- Task: `T001`
- Retry queue-worker run: `QWR-0008`
- Worker run: `WR010`
- Codex worker run: `CWR-20260901093949-QWR-0008`
- Ingest: `CWI-20260901094057-QWR-0008`
- Batch run: `CWBR-0010`

Allowed files:

- `src/devo/main.py`
- `tests/test_project_planning.py`

## Real Codex Result

Real Codex launched from normal PowerShell, inspected the approved files, and returned strict JSON. The worker result was safely ingested as `blocked`.

Observed summary:

```text
Workspace writes were denied, so the approved source and test changes could not be applied.
```

Safety held:

- repository remained clean
- queue item was not completed
- review evidence was not recorded
- validation evidence was not recorded
- delivery request was not created
- no direct commit or push occurred

## Finding

`patch-proposal-show` for `QWR-0008` reported:

```text
Patch proposal present: False
Patch artifact path: none
Patch artifact exists: False
```

Root cause: the generated worker output contract said to use exactly the listed JSON fields, and that list contained `patch_proposal_present` plus `patch_artifact_path`, but not an inline patch content field. Real Codex could not safely create a patch artifact and had no canonical allowed field for inline patch text, so it returned `patch_proposal_present=false`.

## Fix

TASK-DEVO-177 adds `patch_proposal_text` as the canonical inline patch field in the worker result contract.

The generated prompt now says:

- if file writes fail but the safe change is known, return `status=blocked` or `status=failed`
- set `patch_proposal_present=true`
- if a patch artifact exists inside the target repo or approved Devo workspace artifact flow, set `patch_artifact_path`
- if no patch artifact exists, put a unified diff directly in `patch_proposal_text`
- do not set `status=completed` unless target files were actually changed
- do not create patch artifacts outside the target repo or approved Devo workspace artifact flow
- patch-only output is review material only, not completed work

`codex-worker-ingest` now treats non-empty `patch_proposal_text` as patch proposal evidence and materializes it into a workspace `.patch` artifact when no artifact path is provided. Existing aliases remain readable for compatibility, but `patch_proposal_text` is the documented field.

## Validation

Commands:

```powershell
.\.venv\Scripts\python -m py_compile src/devo/main.py src/devo/project_planning.py
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k "patch_proposal_text or inline_patch or patch_proposal_check or patch_proposal_show or codex_worker_prompt_includes_patch_proposal_fallback_contract" --tb=short --basetemp=E:\DevOrchestrator\pt-177-focused
```

Focused result:

- `py_compile`: passed
- focused tests: `8 passed, 194 deselected`
- known warning: pytest cache warning under `.pytest_cache`

## Delivery Request

- Runner request: `REQ-0065`
- Commit message: `feat: add inline patch proposal text contract`
- Trusted runner command:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request REQ-0065 --approver "Manas" --confirm-runner-delivery
```

## Verdict

PARTIAL dogfood, safe blocker.

The real Codex retry proved that the worker still blocks safely when writes fail, but it also showed the prompt contract needed an explicit inline patch field. TASK-DEVO-177 fixes that contract so the next real retry can preserve patch intent as `patch_proposal_text` and let Devo materialize it into a patch artifact.

## Recommendation

TASK-DEVO-178 should retry the same narrow real Codex patch-proposal fallback once this contract fix lands. The expected successful fallback path is:

```text
blocked JSON with patch_proposal_text
-> confirmed ingest materializes workspace .patch
-> patch-proposal-show
-> patch-proposal-check
-> reviewed patch-proposal-apply
-> manual validation and review
-> trusted delivery
```
