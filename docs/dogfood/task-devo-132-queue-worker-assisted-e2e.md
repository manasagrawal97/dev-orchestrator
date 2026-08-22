# TASK-DEVO-132 Queue-Worker Assisted E2E Dogfood

## Scenario Used

TASK-DEVO-132 dogfooded the queue-worker assisted flow with a disposable pytest temp project instead of a live target repository. The scenario used a registered `sample` project under pytest `tmp_path`, initialized it as a local git repository, created an approved batch execution policy, ran one queue-worker item, imported simulated worker/report/review/validation evidence, and created a trusted delivery runner request artifact.

This avoided PersonalOS, real Codex CLI execution, AI/API calls, UI controls, background loops, real guarded commit/push, and risky live delivery requests.

## Exact Commands Run

```powershell
git status --short --branch
git log --oneline -n 5
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py -k "queue_worker_assisted_e2e_flow" --basetemp=E:\DevOrchestrator\pt-132-e2e
.\.venv\Scripts\python -m pytest -q tests/test_project_planning.py tests/test_read_models.py tests/test_api.py --basetemp=E:\DevOrchestrator\pt-132-focused
```

The dedicated dogfood test is:

```text
tests/test_project_planning.py::test_queue_worker_assisted_e2e_flow
```

## Artifacts Created

All dogfood workflow artifacts were created under pytest temporary workspace/project folders only. The representative artifact families were:

- `workspace/projects/sample/planning/execution-policies/`
- `workspace/projects/sample/planning/queues/`
- `workspace/projects/sample/planning/handoffs/`
- `workspace/projects/sample/planning/queue-worker-runs/`
- `workspace/projects/sample/workers/codex/`
- `workspace/projects/sample/workers/codex/reports/`
- `workspace/projects/sample/workers/codex/reviews/`
- `workspace/projects/sample/delivery/runner-requests/`

No workspace artifacts from the live DevOrchestrator workspace were staged or committed.

## Evidence Used

The sandbox dogfood used simulated but structured evidence:

- imported `CodexWorkerReport` with `status_reported_by_worker=completed`
- recorded worker review with `review_status=reviewed_passed`
- attached validation evidence with `validation_status=passed`
- created one temp-repo changed file, `src/feature.py`, so the trusted delivery request had a real changed-file snapshot
- verified `queue-worker-show`, `queue-worker-latest`, `queue-worker-status`, and `queue-worker-evidence` showed the linked delivery request id/status after handoff

## State Transitions Observed

The temp-project dogfood observed the intended queue-worker assisted path:

```text
approved policy
-> queue-worker-run
-> waiting_worker
-> worker report imported
-> queue-worker-continue
-> waiting_review
-> reviewed_passed recorded
-> queue-worker-continue
-> waiting_validation
-> validation evidence passed
-> queue-worker-continue
-> ready_for_delivery_request
-> queue-worker-request-delivery
-> delivery_requested
```

The trusted delivery runner request was created with status `requested` and expected changed files limited to the temp repo's `src/feature.py`. The temp repo still had only its initial commit, proving that the dogfood did not commit or push.

The live DevOrchestrator documentation/test delivery for this dogfood was handed to the trusted runner as `REQ-0018`. The scheduled trusted runner later completed it as commit `229ffa4937a9fc16fd152a0fec43400f5cdc6320` and pushed it to `origin/main`.

## What Worked

- The queue-worker run respected the approved execution policy and selected one queue item.
- Missing evidence and continuation gates were explicit.
- Imported worker report evidence moved the run to review wait.
- Passed review moved the run to validation wait.
- Passed validation moved the run to delivery-request readiness.
- Delivery handoff reused the trusted `delivery runner-request` flow instead of inventing a second delivery path.
- The runner request was created without running runner-watch, guarded commit, guarded push, or queue completion.

## What Failed Or Felt Awkward

- The assisted flow still requires many commands and separate evidence files.
- A user needs to know the worker report, review, validation, and queue-worker continuation order.
- The current dogfood is test-driven rather than a single operator command that assembles a sandbox scenario.
- The live `DevOrchestrator` project currently has no real queue-worker runs, so read-only smoke on live state cannot show the full evidence chain yet.

None of these blocked the dogfood path. They are product ergonomics gaps rather than safety failures.

## Safety Gates Observed

- No real Codex CLI execution occurred.
- No AI/API calls occurred.
- No PersonalOS commands or modifications occurred.
- No UI controls were added or used.
- Execution policy checks remained in the queue-worker path.
- Review and validation gates were required before delivery request readiness.
- Delivery request creation did not run trusted runner watch or guarded commit/push.
- The temp git repo was not committed or pushed after the initial fixture commit.

## Manual Steps Still Required

- A worker or operator must fill/import the worker report.
- A reviewer must record review status.
- Validation evidence must be attached explicitly.
- The operator must run `queue-worker-continue` at each gate.
- The trusted local runner must still process the delivery request separately.

## Recommended Next Task

TASK-DEVO-133 should focus on operator ergonomics for this flow, not deeper autonomy yet. A good next step is a read-only/low-risk queue-worker resume or flow-summary command that prints the exact next command for the current evidence gate and makes the worker report -> review -> validation -> delivery-request sequence harder to misuse.

Do not jump straight to multi-task autonomous execution until this single-item assisted path feels comfortable in live dogfood.
