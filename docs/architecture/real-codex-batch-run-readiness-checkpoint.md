# Real Codex Batch-Run Readiness Checkpoint

## Purpose

TASK-DEVO-163 records the readiness state after TASK-DEVO-162 proved real Codex multi-item continuation on disposable project `Dogfood162`.

This checkpoint is intentionally conservative. Devo is now past "can this launch one real Codex worker?" but it is not yet "fully unattended coding." The usable mode is approved batch worker execution with manual review, manual validation, and trusted-runner-only delivery.

## What Is Proven Now

The following path is proven on disposable repositories:

1. Create or import bounded planning tasks.
2. Approve a planning batch.
3. Create an execution queue.
4. Create and approve a narrow execution policy.
5. Configure a real Codex subprocess command.
6. Run `codex-worker-batch-run --dry-run`.
7. Run real `codex-worker-batch-run` from normal PowerShell for one item.
8. Ingest strict JSON worker output.
9. Stop at the review gate.
10. Record manual review evidence.
11. Record manual validation evidence.
12. Create a trusted delivery request.
13. Let the trusted runner commit and push.
14. Complete the queue item.
15. Continue to the next eligible item.
16. Stop when all allowed queue items are completed.

TASK-DEVO-162 proved that this can continue across two real Codex subprocess items on a disposable project:

- `T001/QI001/QWR-0001` delivered through `REQ-0001` with commit `0cb7e7a`.
- `T002/QI002/QWR-0002` delivered through `REQ-0002` with commit `18b91bd`.
- Final `CWBR-0003` reported that all allowed queue items were completed.

TASK-DEVO-164 then proved the same operating mode on the live DevOrchestrator repo for a narrow docs-only policy:

- `QI001/T001/QWR-0001` delivered through `REQ-0052` with commit `f9360f7`.
- `QI002/T002/QWR-0002` delivered through `REQ-0053` with commit `3b6c44d`.
- Final `CWBR-0004` reported that all allowed queue items were completed.

TASK-DEVO-166 dogfooded the read-only consolidated summary against that completed live policy. `devo project codex-worker-batch-summary --project DevOrchestrator --policy POL-0002` reported both completed items, productive Codex batch/worker/ingest artifacts, review and validation evidence, delivery requests, trusted runner runs, pushed commits, and terminal no-action guidance in one view.

TASK-DEVO-167 then attempted a first narrow live DevOrchestrator code-task policy and blocked safely. Real Codex could inspect approved files and produce strict JSON, but the subprocess could not update existing allowed source/test files. TASK-DEVO-168 documents that this is a write-context blocker: do not treat it as implementation evidence, and do not retry blindly without changing the launcher/process permission context or using a future patch-proposal fallback.

## Safe For Disposable Projects

Real Codex batch-run is safe for disposable dogfood projects when all of these are true:

- The repo is disposable and has a verified upstream or local bare remote.
- The policy is narrow and approved.
- The allowed file list is explicit.
- Forbidden paths include secret and workspace patterns.
- `max_changed_files_per_task` is small.
- `max_tasks_per_run` remains `1`.
- The operator runs real Codex from normal PowerShell, not from inside a Codex/sandbox session.
- The worker output is strict JSON.
- Review and validation are recorded manually before delivery.
- The trusted runner is the only committer and pusher.

Fake workers remain useful for testing state-machine behavior, retry handling, prompt shape, and continuation without spending real Codex usage.

## Safe For DevOrchestrator

Real Codex batch-run is now reasonable to try on DevOrchestrator only for narrow, low-risk scopes such as:

- docs-only changes
- isolated tests
- tiny source polish with focused tests
- disposable or clearly bounded dogfood artifacts

Additional guardrails should be used:

- Prefer one task per policy until more real dogfood is complete.
- Keep policies file-specific rather than broad directory-specific when possible.
- Run dry-run first.
- Use normal PowerShell for real Codex subprocess execution.
- Require manual review and validation evidence before delivery.
- Use `delivery runner-request` and trusted runner delivery only.
- Avoid running real Codex against pending unreviewed source changes.

TASK-DEVO-164 proved this on a docs-only live DevOrchestrator batch. The recommended ongoing mode is still narrow and operator-gated: inspect the position with `devo project codex-worker-batch-summary --project DevOrchestrator --policy <POL-ID>`, run at most one real Codex item at a time, review manually, validate manually, and deliver only through the trusted runner.

TASK-DEVO-167 shows that live DevOrchestrator code edits have one more readiness condition: the real Codex subprocess must be able to update existing approved files, not merely read them or create new probe files. If worker evidence reports `Failed to write file`, `UnauthorizedAccessException`, access denied, or permission denied, stop for diagnostics before review, validation, or delivery.

## Not Ready For PersonalOS Or Family-Use Development

Real Codex batch-run is not yet ready as a default PersonalOS/family-use workflow.

PersonalOS has app behavior, data, local settings, secrets, database concerns, migrations, and user-facing risk. Before real Codex batch-run should touch PersonalOS, Devo needs more evidence around:

- stronger policy review for app/data boundaries
- clearer validation command approval and result capture
- better operator summaries between items
- more dogfood on DevOrchestrator low-risk work
- explicit handling for target projects with secrets, databases, and user data

PersonalOS can still be used for controlled manual/Codex work packages and Devo validation, but real Codex batch-run should remain paused for PersonalOS until a later checkpoint approves that operating mode.

## Manual Gates That Remain Required

Real Codex output is not automatically trusted.

These gates remain manual in the current operating mode:

- Review the worker change and result JSON.
- Record passed review evidence.
- Run or otherwise perform validation appropriate to the policy.
- Record passed validation evidence.
- Create or approve the trusted delivery request path.
- Run or allow the trusted local runner to commit and push.
- Confirm queue completion before moving to larger scopes.

If worker evidence is `blocked`, review/validation should only be recorded after a real implemented change exists. For write-access blockers, the correct next step is diagnostics or patch-proposal fallback, not delivery. TASK-DEVO-169 adds patch-proposal fallback v1: blocked/failed worker JSON can preserve a proposed `.patch` or `.diff`, but the result still is not completed work and must not proceed through normal review, validation, or delivery until the patch is actually applied and validated. TASK-DEVO-170 dogfoods that fallback with fake blocked evidence and confirms the ingest, evidence, and batch summary readouts keep the operator on the manual patch-review path.

The real Codex subprocess step may spend Codex usage. Use it only for narrow approved policies where the expected change is worth the usage cost.

## Trusted-Runner-Only Delivery

Codex must not commit or push directly.

Delivery remains trusted-runner-only:

- `codex-worker-batch-run` can produce and ingest worker evidence.
- Devo can create delivery requests after review and validation evidence.
- The trusted runner commits and pushes from the normal local user context.
- Push-only failures should use `devo delivery runner-recover-push`.

This keeps Git delivery separate from worker execution and avoids repeating the earlier sandbox `.git/index.lock` and restricted-context delivery problems.

## Recommended Operating Mode

Use this practical workflow after TASK-DEVO-162:

1. Discuss the task with ChatGPT.
2. Create or choose a narrow batch in Devo.
3. Create and approve a narrow execution policy.
4. Run `devo project codex-worker-batch-run --project <project> --policy <POL-ID> --dry-run`.
5. From normal PowerShell, run `devo project codex-worker-batch-run --project <project> --policy <POL-ID> --confirm-codex-batch-run`.
6. Let it process one queue item.
7. Stop at the review gate.
8. Review the diff and worker result.
9. Record review evidence.
10. Validate using the policy-approved validation method.
11. Record validation evidence.
12. Create the delivery request from queue-worker evidence.
13. Run the trusted runner or allow the scheduled trusted runner to deliver.
14. Confirm the queue item is completed.
15. Repeat for the next eligible item only if the repo is clean and the policy still applies.

This is approved batch worker execution with manual gates, not fully unattended coding.

## Real Codex Result Expectations

Real Codex worker prompts should continue to require strict JSON final output. The result should include:

- task id
- status
- summary
- changed files
- commands run
- risks
- recommended next action

If Codex produces missing, malformed, or non-JSON output, stop. Do not infer success from prose. Preserve the raw output and either normalize it manually into the generated result template or rerun with stricter JSON-only instructions.

## Completed Batch Guidance

When all allowed items are completed, the main operator message should say that clearly:

```text
All allowed queue items are completed.
Next action: No action needed, or create/approve another queue/policy for more work.
```

Detailed diagnostics can remain available, but completed-queue output should not lead with `no_ready_item` as if something is wrong.

## What Can Use Fake Worker

Use fake workers for:

- state-machine regression tests
- prompt/result path checks
- continuation from item 1 to item 2
- stale retry/run behavior
- completed-queue guidance
- scope violation tests
- timeout/non-JSON/failure simulations

Fake-worker tests should parse the explicit `Task id:` line in the generated prompt rather than broad task objective text.

## What Can Use Real Codex

Use real Codex for:

- disposable repo dogfood
- DevOrchestrator docs-only changes
- very small DevOrchestrator test or source polish after dry-run
- tasks where review and validation remain manual

Do not use real Codex batch-run for:

- PersonalOS by default
- migrations
- database changes
- secrets or local settings
- backup/restore
- scheduler changes
- broad refactors
- multi-file behavior changes without a fresh policy and checkpoint

## Out Of Scope For Now

- parallel workers
- automatic review
- automatic validation execution
- automatic trusted runner execution from the worker loop
- direct Codex commit or push
- UI execution controls
- model/API agent integrations
- PersonalOS real-Codex batch execution
- background queue daemon behavior
- weakening delivery safety to reduce friction

## Recommended Next Task

TASK-DEVO-165 finished the first operator-readout polish by adding a read-only consolidated real-batch position summary. TASK-DEVO-166 proved it against completed live policy `POL-0002`. The summary joins the execution policy, queue item, queue-worker run, Codex preparation/batch/ingest, review, validation, delivery request, runner run, commit, push, and the single safe next command without widening autonomy.

The next implementation should continue with small real-batch dogfood/readout polish only. Do not add automatic review, automatic validation, automatic delivery, direct Codex commit/push, parallel workers, or PersonalOS real-Codex batch execution without a new checkpoint.
