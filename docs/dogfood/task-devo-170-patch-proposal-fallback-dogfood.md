# TASK-DEVO-170 Patch-Proposal Fallback Dogfood

## Goal

Dogfood TASK-DEVO-169 patch-proposal fallback v1 with a fake blocked worker result that points at a `.patch` artifact, while proving Devo preserves the proposal without treating it as completed work.

## Setup

- Project: `DevOrchestrator`
- Policy: `POL-0003`
- Batch: `B005`
- Queue: `Q005`
- Queue item: `QI001`
- Task: `T001`
- Retry queue-worker run: `QWR-0005`
- Worker run: `WR007`
- Preparation: `CWP-20260829130934-QWR-0005`
- Ingest: `CWI-20260829130957-QWR-0005`

`POL-0003` was reused because it is the narrow approved code-task policy from TASK-DEVO-167. That policy is already scoped to `src/devo/main.py` and `tests/test_project_planning.py`, and it represents the exact write-access blocker that patch-proposal fallback exists to handle.

## Fake Worker Result Shape

The fake result was written under the preparation artifact directory and ingested through `codex-worker-ingest`.

Key fields:

```json
{
  "status": "blocked",
  "summary": "Fake TASK-DEVO-170 worker could identify the harmless output wording change, but simulated Failed to write file / access denied while updating an existing tracked source file. Patch proposal was written for manual review only.",
  "work_performed": [],
  "changed_files": [],
  "commands_run": ["fake worker attempted patch proposal only"],
  "risks": ["write access blocked; patch proposal not applied"],
  "artifact_path": "E:\\DevOrchestrator\\workspace\\projects\\DevOrchestrator\\codex-worker\\preparations\\CWP-20260829130934-QWR-0005\\task-devo-170-proposed.patch",
  "patch_proposal_present": true,
  "patch_artifact_path": "E:\\DevOrchestrator\\workspace\\projects\\DevOrchestrator\\codex-worker\\preparations\\CWP-20260829130934-QWR-0005\\task-devo-170-proposed.patch",
  "dirty_repo_status": "clean",
  "failure_details": "Failed to write file; access denied while updating existing tracked source file"
}
```

Patch artifact:

```text
E:\DevOrchestrator\workspace\projects\DevOrchestrator\codex-worker\preparations\CWP-20260829130934-QWR-0005\task-devo-170-proposed.patch
```

The patch was not applied.

## Commands Run

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project DevOrchestrator --policy POL-0003
.\.venv\Scripts\devo.exe project queue-worker-retry --project DevOrchestrator --run QWR-0004 --confirm-retry
.\.venv\Scripts\devo.exe project codex-worker-prepare --project DevOrchestrator --run QWR-0005 --recorded-by "Codex" --note "TASK-DEVO-170 fake patch-proposal dogfood; no real Codex execution." --confirm-prepare
.\.venv\Scripts\devo.exe project codex-worker-ingest --project DevOrchestrator --run QWR-0005 --prepare CWP-20260829130934-QWR-0005 --result-file "E:\DevOrchestrator\workspace\projects\DevOrchestrator\codex-worker\preparations\CWP-20260829130934-QWR-0005\task-devo-170-worker-result.json" --recorded-by "Codex" --note "TASK-DEVO-170 fake blocked worker result with patch proposal artifact; patch not applied." --confirm-ingest
.\.venv\Scripts\devo.exe project queue-worker-show --project DevOrchestrator --run QWR-0005
.\.venv\Scripts\devo.exe project queue-worker-evidence --project DevOrchestrator --run QWR-0005
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project DevOrchestrator --policy POL-0003
```

No real Codex CLI was run.

## Output Verdict

`codex-worker-ingest` correctly reported:

- result status: `blocked`
- patch proposal present: `True`
- patch artifact path: the `.patch` artifact
- next action: review patch proposal manually
- warning that the patch proposal is review material only

`queue-worker-evidence` now clearly reports:

- worker report status: `blocked`
- patch proposal present: `True`
- patch artifact path
- no delivery request
- next action: `Review patch proposal manually. Do not record normal review/validation/delivery until changes are actually applied and validated.`

`codex-worker-batch-summary` correctly reports:

- `QI001 / T001`
- `qwr=QWR-0005`
- `ingest=CWI-20260829130957-QWR-0005`
- worker evidence `blocked`
- review evidence missing
- validation evidence not provided
- patch proposal present and artifact path
- delivery request `none`
- trusted runner `none`
- no commit or push
- same manual patch-review next action

## Safety Verdict

PASS.

Devo preserved useful implementation intent without treating patch-only evidence as completed work.

Confirmed safety properties:

- patch proposal was not applied
- worker status stayed `blocked`
- no normal review evidence was recorded
- no validation evidence was recorded
- no delivery request was created
- trusted runner was not run
- no commit or push occurred
- PersonalOS was not modified

## Friction Found

`codex-worker-batch-summary` and `codex-worker-ingest` were already clear after TASK-DEVO-169.

`queue-worker-evidence` initially only implied the patch proposal through blockers. TASK-DEVO-170 adds the explicit patch proposal present/path lines and patch-review next action to that readout.

`queue-worker-show` still reflects the stored queue-worker run's older next action because it shows the run artifact itself. That is acceptable for now because `queue-worker-evidence` and `codex-worker-batch-summary` are the decision views for blocked evidence.

## Recommendation For TASK-DEVO-171

Add a separately approved patch-review/apply design before any automatic or trusted patch application exists.

Suggested boundary:

- read patch proposal
- validate it is inside policy file bounds
- require explicit operator approval
- apply through a trusted local command, not Codex subprocess
- require validation evidence after apply
- keep trusted runner as the only commit/push path

TASK-DEVO-171 implements that recommendation as design-only in `docs/architecture/reviewed-patch-apply-design.md`. The design recommends TASK-DEVO-172 start with read-only patch proposal show/check commands before any apply command is implemented.
