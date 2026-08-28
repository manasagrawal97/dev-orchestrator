# TASK-DEVO-164 DevOrchestrator Real Batch-Run Dogfood

## Verdict

PASS. TASK-DEVO-164 proved that `devo project codex-worker-batch-run` can be used on the live DevOrchestrator repository itself for a narrow docs-only policy while preserving the current safety model:

- one queue item per real Codex subprocess run
- strict JSON worker result ingest
- manual review evidence
- manual validation evidence
- trusted-runner-only commit and push
- no direct Codex commit or push
- final all-completed batch guidance

## Policy

- Policy: `POL-0002`, approved by Manas on 2026-08-28
- Risk: low
- Batch and queue: `B004` / `Q004`
- Allowed tasks and items: `T001`, `T002` / `QI001`, `QI002`
- Allowed files: `docs/how-to-use-devo.md` and this report
- Per-task limit: one changed file and one task per run
- Required validation: `git diff --check`
- Required evidence: worker result, manual review, and manual validation
- Delivery boundary: worker execution must not stage, commit, or push; guarded delivery remains trusted-runner-only

The policy allowed delivery and push only through the trusted runner path after required evidence gates. It did not authorize the Codex worker to perform delivery.

## Batch And Queue

Planning batch `B004`, titled `TASK-DEVO-164 real Codex internal docs dogfood`, was approved with two low-risk docs-only tasks. `T002` depended on `T001`, which made the intended order explicit.

- `T001`: add a real batch operating-mode note to `docs/how-to-use-devo.md`
- `T002`: create this dogfood report

Execution queue `Q004` preserved that order. After item 1 was delivered and completed, Devo selected item 2. After item 2 was delivered and completed, final batch run `CWBR-0004` correctly reported that all allowed queue items were completed.

## Item 1 Result

- Queue item / task: `QI001` / `T001`
- Queue-worker run: `QWR-0001`
- Codex preparation: `CWP-20260828071814-QWR-0001`
- Codex batch run: `CWBR-0001`
- Codex worker ingest: `CWI-20260828071900-QWR-0001`
- Delivery request: `REQ-0052`
- Commit: `f9360f785c5b720b0759d447a2b99c8e47d9c115`
- Commit message: `feat: complete Add real batch operating-mode note`
- Changed file: `docs/how-to-use-devo.md`
- Final state: delivered, pushed, queue item completed

`CWBR-0001` processed exactly one item, ran the configured real Codex subprocess from normal PowerShell, ingested strict JSON, and stopped at the review gate. Review and validation were recorded manually before trusted delivery.

## Item 2 Result

- Queue item / task: `QI002` / `T002`
- Queue-worker run: `QWR-0002`
- Codex preparation: `CWP-20260828083809-QWR-0002`
- Codex worker run: `CWR-20260828083810-QWR-0002`
- Codex worker ingest: `CWI-20260828084019-QWR-0002`
- Delivery request: `REQ-0053`
- Commit: `3b6c44d`
- Changed file: `docs/dogfood/task-devo-164-devorchestrator-real-batch-run-dogfood.md`
- Final state: delivered, pushed, queue item completed

Item 2 repeated the same gate pattern: real Codex wrote the docs-only worker change, Devo ingested strict JSON, manual review and validation evidence were recorded, and the trusted runner delivered the final commit.

## Final Batch State

Final Codex worker batch run `CWBR-0004` reported:

```text
All allowed queue items are completed.
```

That is the correct terminal state. The next action for this policy is no action needed, or create and approve another queue or policy for more work.

## Manual Gates Preserved

The run preserved all intended human-controlled boundaries:

1. Real Codex execution occurred from normal PowerShell under a narrow approved policy.
2. Each subprocess invocation processed only one queue item.
3. Strict worker JSON was ingested before any review.
4. Review was recorded manually.
5. Validation was recorded manually after `git diff --check`.
6. Delivery requests were created only after required evidence existed.
7. The trusted runner was the only committer and pusher.

Codex did not stage, commit, or push. No PersonalOS files were modified.

## Friction Found

The workflow was safe, but the operator still had to mentally join many artifacts:

- execution policy
- planning batch
- execution queue and queue item
- queue-worker run
- Codex preparation
- Codex batch run
- Codex worker run and ingest
- review evidence
- validation evidence
- delivery request
- runner run
- commit and push status
- final queue status

After a specified run completed, `approved-queue-run` still printed "Start next eligible item" even though the policy had no remaining allowed items. A later `codex-worker-batch-run` invocation produced the correct terminal message. TASK-DEVO-165 exists to make that consolidated state and next action available directly.

## Recommendation

TASK-DEVO-165 should add a read-only real-batch position summary command that joins the policy, queue, queue-worker, Codex, evidence, delivery, runner, commit, and push records into one operator view. It should print one safe next command for active policies and clearly say all allowed queue items are completed for terminal policies.
