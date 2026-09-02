# Codex Worker Batch Loop Design

## 1. Purpose

TASK-DEVO-154 designs the next Codex worker layer before implementation. The goal is to let Devo process multiple approved queue items with Codex subprocess execution while keeping the v1 model conservative:

- one task at a time
- no parallel workers
- no Codex commit or push
- no automatic trust of process output
- trusted runner remains the only delivery path
- unsafe or ambiguous states always stop the loop

This document was created as design-only in TASK-DEVO-154. TASK-DEVO-155 implements the first conservative v1 from this design: `devo project codex-worker-batch-run` processes at most one approved queue item per invocation, writes batch-run artifacts, and stops at the review gate after strict JSON ingest. TASK-DEVO-158 proves that v1 with one real Codex subprocess item on disposable `Dogfood158`, followed by manual review/validation evidence and trusted runner delivery. TASK-DEVO-162 proves continuation across two real disposable Codex subprocess items on `Dogfood162`, still one item at a time and still delivered only through the trusted runner. TASK-DEVO-163 records the readiness checkpoint in `docs/architecture/real-codex-batch-run-readiness-checkpoint.md`. TASK-DEVO-164 proves the same one-item-at-a-time flow on a narrow live DevOrchestrator docs-only policy, and TASK-DEVO-165 adds `devo project codex-worker-batch-summary` as the read-only position summary for operators. TASK-DEVO-167/168 adds one more boundary: if a real worker can inspect approved files but cannot update existing files, the safe state is blocked diagnosis or patch-proposal fallback, not review, validation, or delivery. TASK-DEVO-169 adds that fallback's first safe slice: Devo can ingest and summarize a patch proposal, but it still cannot apply it automatically. TASK-DEVO-171 designs the separate reviewed patch-apply flow in `docs/architecture/reviewed-patch-apply-design.md`, TASK-DEVO-172 implements read-only `patch-proposal-show` plus explicit non-mutating `patch-proposal-check`, TASK-DEVO-173 dogfoods those commands against existing fake blocked evidence, and TASK-DEVO-174 adds explicit reviewed apply while still avoiding normal gate advancement. TASK-DEVO-176 through TASK-DEVO-178 then harden real inline patch proposals: inline `patch_proposal_text` can be materialized into a workspace artifact, but it must be a complete `git apply`-compatible unified diff before reviewed apply can proceed.

## 2. Current Proven Flow

TASK-DEVO-152 and TASK-DEVO-153 prove and harden this one-task flow:

```text
approved execution policy
-> queue-worker run
-> codex-worker-prepare prompt package
-> codex-worker-run subprocess execution
-> result file produced through codex exec --output-last-message
-> codex-worker-ingest strict JSON worker evidence
-> review evidence
-> validation evidence
-> trusted delivery runner request
-> trusted runner commit/push
-> queue-worker observes delivery completion
-> queue item completion
```

Important proven constraints:

- `codex-worker-run` executes exactly one configured subprocess after explicit confirmation.
- The default Codex command shape is `exec -s workspace-write --output-last-message "{result_path}"`.
- Devo passes the generated prompt to Codex on stdin.
- `codex-worker-ingest` accepts UTF-8 BOM JSON but still requires strict JSON.
- Non-JSON structured text is blocked with operator guidance.
- Delivery is still performed by trusted runner commands, not Codex.
- Real multi-item continuation has been proven only in the disposable normal-PowerShell pattern documented by TASK-DEVO-162.

## 3. Proposed Command Shape

Future v1 command:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project <project> --policy <POL-ID> --confirm-codex-batch-run
```

Suggested options:

```powershell
--max-items 1
--stop-after worker|review|validation|delivery_request|delivery|completed
--require-scheduler-healthy / --no-require-scheduler-healthy
--continue-next
--dry-run
--recorded-by "Manas"
--note "..."
```

Default v1 behavior should be conservative:

- `--max-items 1` by default, or a very small bounded value only after implementation tests prove it.
- Require explicit confirmation for mutation.
- Require scheduler health unless the operator explicitly uses `--no-require-scheduler-healthy`.
- Stop at review and validation gates unless a later approved policy explicitly allows auto-review or auto-validation.
- Never run validation commands directly in this first batch loop unless a future task approves that scope.

## 4. V1 Loop Algorithm

For each iteration:

1. Load and check the approved execution policy.
2. Check scheduler health unless explicitly bypassed.
3. Check target repo state.
4. Select the next eligible approved queue item.
5. Create or reuse one queue-worker run.
6. Ensure handoff checklist exists.
7. Create or reuse a Codex worker preparation package.
8. Run `codex-worker-run` for exactly one task.
9. Check subprocess state and expected result file.
10. Ingest result only if strict JSON is present and valid.
11. Stop at review evidence boundary unless review is already recorded.
12. Stop at validation evidence boundary unless validation is already recorded.
13. Create trusted delivery request only after worker, review, and validation evidence are present.
14. Wait for or observe trusted runner delivery.
15. Mark queue item complete only after trusted delivery is completed and pushed.
16. Continue to the next item only if policy, queue state, repo state, and stop conditions all allow it.

The loop should be built from existing one-step primitives where possible. It should not duplicate delivery safety logic.

## 5. State Machine

| State | Meaning | Default next action |
| --- | --- | --- |
| `policy_ready` | Approved policy is usable. | Select queue item. |
| `item_selected` | One eligible queue item is selected. | Create/reuse queue-worker run. |
| `handoff_ready` | Handoff/checklist exists. | Prepare Codex prompt package. |
| `waiting_worker` | Prompt package is ready. | Run one Codex subprocess if confirmed. |
| `worker_running` | Subprocess is active. | Wait for process result. |
| `worker_result_ready` | Process ended and expected result file exists. | Ingest strict JSON. |
| `worker_ingested` | Worker evidence is recorded. | Stop for review unless review exists. |
| `waiting_review` | Review evidence missing. | Stop and ask operator to review. |
| `review_passed` | Review evidence passed. | Stop for validation unless validation exists. |
| `waiting_validation` | Validation evidence missing. | Stop and ask operator to validate. |
| `validation_passed` | Validation evidence passed. | Request trusted delivery. |
| `delivery_requested` | Runner request exists. | Wait for trusted runner. |
| `delivery_completed` | Trusted runner committed and pushed. | Mark item complete. |
| `item_completed` | Queue item is complete. | Continue only if policy and command limits allow. |
| `paused` | Safe manual pause. | Resume only by explicit operator command. |
| `blocked` | Safety blocker exists. | Resolve blocker before retry. |
| `failed` | Worker/process/validation/delivery failure. | Explicit retry or manual recovery only. |

## 6. Stop Conditions

The batch loop must stop immediately when any of these occur:

- policy is missing, unapproved, expired, or out of scope
- queue is missing, paused, cancelled, or has no eligible item
- target repo is dirty before worker launch
- dirty repo after worker launch includes files outside allowed scope
- subprocess result file is missing
- result JSON is invalid
- result status is `failed`, `blocked`, or `usage_limit`
- worker evidence reports access denied, `Failed to write file`, `UnauthorizedAccessException`, or another existing-file write blocker
- worker evidence is patch-only; use `patch-proposal-show`, `patch-proposal-check --confirm-check`, and then explicit reviewed `patch-proposal-apply --confirm-apply-patch` before normal review/validation/delivery
- subprocess exits non-zero
- subprocess times out
- subprocess is cancelled
- scope violation is detected
- review evidence is missing
- review evidence is rejected or needs changes
- validation evidence is missing
- validation evidence is failed or unclear
- trusted delivery request has blockers
- trusted runner scheduler is unhealthy and no explicit manual-runner bypass is provided
- trusted runner commit/push fails
- queue-worker run state is ambiguous or does not match expected item/policy
- max item count or max step count is reached

The loop should prefer a clear `blocked` or `paused` result over guessing.

## 7. Retry And Resume Behavior

V1 should separate retry from automatic continuation.

Recommended behavior:

- `codex-worker-batch-run` may resume a known safe state.
- Retry of a failed subprocess requires explicit operator confirmation.
- Retry should create a new worker run or retry-linked artifact rather than overwriting old evidence.
- Retry-created queue-worker runs should link a worker run before entering `waiting_worker`; if linking cannot be done safely, they should block rather than leaving a partial run.
- Stale active queue-worker runs tied to completed items should not block selecting the next eligible item; Devo should warn when it ignores stale runs.
- Usage limit should pause the queue-worker run and preserve stdout/stderr/result text.
- Invalid JSON should preserve the raw result and tell the operator to normalize it or rerun with stricter JSON-only instructions.
- Missing result should preserve process logs and expected result path.
- Scope violation should not be retried until policy/scope is reviewed.
- Delivery push failure should use existing trusted runner recovery, not rerun Codex.
- Fake or scripted workers should parse the explicit `Task id:` line in the generated prompt rather than scanning broad objective or policy text.

Suggested future commands:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project <project> --policy <POL-ID>
.\.venv\Scripts\devo.exe project codex-worker-batch-resume --project <project> --policy <POL-ID> --confirm-codex-batch-resume
.\.venv\Scripts\devo.exe project codex-worker-batch-retry --project <project> --run <QWR-ID> --confirm-codex-batch-retry
```

`codex-worker-batch-summary` is implemented as the current read-only status command. Resume and retry-specific batch commands remain future options if the lower-level queue-worker commands are still too manual.

## 8. Safety Gates

Execution policy gate:

- policy must be approved
- selected queue item must be allowed by policy
- selected task must be allowed by policy
- changed files must match allowed file patterns
- forbidden paths always block
- policy item limits and expiry must be honored

Worker gate:

- queue-worker run must be for the selected policy/item
- handoff checklist and prompt package must match the run
- subprocess config must validate
- target repo must be clean before launch
- only one subprocess may be active for the run

Evidence gate:

- worker evidence must come from successful strict JSON ingest
- review evidence must be passed
- validation evidence must be passed
- non-passing or missing evidence blocks continuation

Delivery gate:

- delivery request must be created only after evidence gates pass
- trusted runner remains the only commit/push mechanism
- Devo must not call raw `git add`, `git commit`, or `git push` from Codex/sandbox batch execution
- queue completion requires trusted runner pushed state

## 9. Evidence Requirements

Each item needs durable evidence:

- queue-worker run id
- queue id and queue item id
- policy id
- handoff id
- Codex preparation id
- Codex subprocess run id
- raw stdout/stderr/process info
- result path and raw result copy
- worker ingest id
- worker evidence status
- review evidence id and status
- validation evidence id and status
- delivery runner request id
- trusted runner run id
- commit hash and pushed flag
- final queue item status
- patch proposal present/path when the worker could not apply the change

The batch run should summarize these per item without hiding lower-level artifact paths.

Patch proposals are evidence of implementation intent, not evidence that files changed. A blocked or failed worker may set `patch_proposal_present` and provide `patch_artifact_path`; if it cannot create a patch artifact, it should put a complete `git apply`-compatible unified diff in canonical field `patch_proposal_text` so ingest can materialize a workspace `.patch` artifact. Snippet diffs, absolute paths, or hunks with incorrect line counts must stay blocked and be replaced by a fresh worker result. The queue item must stay before normal review/validation/delivery until the operator applies and validates the patch through a separate approved path.

The reviewed apply path is designed separately in `docs/architecture/reviewed-patch-apply-design.md`. TASK-DEVO-172 implements read-only show/check commands and TASK-DEVO-174 implements explicit reviewed apply. Even after apply, normal review, validation, delivery, trusted runner, and queue completion gates still remain.

The read-only batch summary should also join these records after the fact. For a terminal policy it should lead with:

```text
All allowed queue items are completed.
Next action: No action needed. Create/approve another queue or policy for more work.
```

For an active policy, it should print one recommended command for the current evidence boundary rather than asking the operator to reconstruct state from separate artifacts.

## 10. Scheduler And Manual Runner Behavior

Normal project default:

- require trusted runner scheduler health before a loop depends on automatic delivery
- if scheduler is unhealthy, stop before creating delivery or clearly stop at delivery-request-ready state
- print `delivery runner-schedule-doctor` and repair guidance

Disposable/manual-runner default:

- allow explicit `--no-require-scheduler-healthy`
- clearly state that the operator must run trusted delivery manually
- print the exact `delivery runner-run` or `delivery runner-watch --once` command
- do not treat missing scheduler as safe unless the bypass flag is explicit

The bypass is for local/disposable dogfood only. It is not a delivery safety bypass; it only changes how the trusted runner is expected to execute the delivery request.

## 11. Expected Artifacts

Suggested workspace artifacts:

```text
workspace/projects/<project>/codex-worker/batch-runs/<CWBR-ID>/
  codex-worker-batch-run.json
  codex-worker-batch-run.md
  items/
    <queue-item-id>/
      summary.json
      summary.md
```

Batch run summary fields:

- batch worker run id
- project
- policy id
- queue id
- status
- started_at / updated_at / completed_at
- max_items
- processed item count
- selected item ids
- current queue-worker run id
- latest Codex worker run id
- latest ingest id
- latest review/validation evidence ids
- latest delivery request/run ids
- stop reason
- blockers
- warnings
- next action

Artifacts are workspace-only and must not be staged or committed.

## 12. CLI UX Examples

Dry run:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project DevOrchestrator --policy POL-0001 --dry-run
```

Confirmed one-item run:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project DevOrchestrator --policy POL-0001 --confirm-codex-batch-run
```

Disposable/manual-runner dogfood:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood154 --policy POL-0001 --no-require-scheduler-healthy --confirm-codex-batch-run
```

Expected stop output:

```text
Codex worker batch run: CWBR-0001
Project: DevOrchestrator
Policy: POL-0001
Status: waiting_review
Processed items: 1
Current queue-worker run: QWR-0001
Stop reason: review evidence missing
Next action:
  devo project queue-worker-record-review --project DevOrchestrator --run QWR-0001 --status passed --summary "<summary>" --confirm-record
```

## 13. Explicitly Out Of Scope For V1

- parallel workers
- multiple active subprocesses
- automatic review
- automatic validation command execution
- automatic retry after failed/timeout/usage-limit states
- direct Codex commit or push
- raw Git commit/push from the batch loop
- automatic patch application from worker output
- UI controls
- AI API/model integration
- PersonalOS-specific behavior
- scheduler installation or repair
- deleting or rewriting old workspace artifacts
- broad least-privilege role system
- multi-project orchestration

## 14. TASK-DEVO-155 Acceptance Criteria

TASK-DEVO-155 should be accepted only if:

- `codex-worker-batch-run` exists or the chosen command name is clearly documented.
- The command processes at most one item at a time in v1.
- Dry-run mode explains the selected item and next steps without mutation.
- Confirmed mode requires `--confirm-codex-batch-run`.
- Policy, queue, item, file-scope, and repo-clean checks are enforced.
- Existing `codex-worker-prepare`, `codex-worker-run`, `codex-worker-ingest`, review, validation, and trusted delivery primitives are reused where practical.
- Missing/invalid result JSON stops safely.
- Usage-limit, timeout, failed process, and scope violation stop safely.
- Missing review/validation evidence stops safely.
- Delivery request creation remains evidence-gated.
- Commit/push remains trusted-runner-only.
- Scheduler health behavior is explicit and supports the existing disposable/manual-runner bypass pattern.
- Workspace artifacts summarize each processed item and final stop reason.
- Tests use fake subprocesses only and never run real Codex.
- No PersonalOS commands, UI changes, parallel workers, AI/API calls, or delivery safety weakening are introduced.

## 15. Verdict

The batch loop is implementable as a conservative wrapper around the proven one-task primitives. The important product improvement is not parallelism; it is reducing operator command stitching while preserving every evidence and delivery gate.

TASK-DEVO-155 should implement a small v1 that runs or advances one item at a time and stops loudly at the first human gate or unsafe state.
