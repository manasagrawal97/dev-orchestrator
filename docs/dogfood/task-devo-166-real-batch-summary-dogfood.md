# TASK-DEVO-166 Real Batch Summary Dogfood

## Verdict

PASS with one tiny polish applied. `devo project codex-worker-batch-summary --project DevOrchestrator --policy POL-0002` gives the operator one useful position view for the completed TASK-DEVO-164 real DevOrchestrator batch.

The command now shows the completed policy state without requiring the operator to manually join policy, queue, queue-worker, Codex subprocess, ingest, review, validation, delivery, runner, commit, push, and final queue artifacts.

## Command Run

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-summary --project DevOrchestrator --policy POL-0002
```

No real Codex CLI was run. The command is read-only and did not mutate queue state, evidence, delivery requests, Git state, or target files.

## Summary Evidence

The dogfood output reported:

- Project: `DevOrchestrator`
- Policy: `POL-0002`
- Policy status: `approved`
- Batch and queue: `B004` / `Q004`
- Allowed tasks: `T001`, `T002`
- Allowed queue items: `QI001`, `QI002`
- Completion: `2/2 completed`
- Terminal message: `All allowed queue items are completed.`
- Next action: `No action needed. Create/approve another queue or policy for more work.`
- Recommended command: `none`
- Warnings: none
- Blockers: none

## Item 1

- Queue item / task: `QI001` / `T001`
- Queue-worker run: `QWR-0001`
- Queue-worker status: `completed`
- Codex batch run: `CWBR-0001`
- Codex worker run: `CWR-20260828071814-QWR-0001`
- Ingest: `CWI-20260828071900-QWR-0001`
- Worker evidence: `completed`
- Review evidence: `reviewed_passed`
- Validation evidence: `passed`
- Delivery request: `REQ-0052`, completed
- Runner run: `RUN-20260828083703-req-0052`, completed
- Commit: `f9360f785c5b720b0759d447a2b99c8e47d9c115`
- Pushed: `True`

## Item 2

- Queue item / task: `QI002` / `T002`
- Queue-worker run: `QWR-0002`
- Queue-worker status: `completed`
- Codex batch run: `CWBR-0003`
- Codex worker run: `CWR-20260828083810-QWR-0002`
- Ingest: `CWI-20260828084019-QWR-0002`
- Worker evidence: `completed`
- Review evidence: `reviewed_passed`
- Validation evidence: `passed`
- Delivery request: `REQ-0053`, completed
- Runner run: `RUN-20260828100328-req-0053`, completed
- Commit: `3b6c44dc050e76f866bb12e8baf82caf9d7e6294`
- Pushed: `True`

## Comparison With Old Flow

Before the summary command, the operator had to inspect or remember several separate artifacts:

- execution policy `POL-0002`
- planning batch `B004`
- execution queue `Q004`
- queue-worker runs `QWR-0001` and `QWR-0002`
- Codex batch runs `CWBR-0001` through `CWBR-0004`
- Codex worker ingests
- review and validation evidence
- delivery requests
- trusted runner runs
- commit and push results

The new summary removes most of that artifact joining for routine operator decisions. The detailed artifacts still exist for audit, but the main question, "where is this policy and what is safe next?", is answered in one command.

## Tiny Polish Applied

Initial dogfood found that item 1 selected redundant batch-run `CWBR-0002`, a safe review-boundary re-run with no subprocess, instead of the productive `CWBR-0001` artifact with worker and ingest evidence.

The summary selection now prefers evidence-bearing Codex batch-run artifacts for each queue item. After the polish, item 1 correctly reports `CWBR-0001`, `CWR-20260828071814-QWR-0001`, and `CWI-20260828071900-QWR-0001`.

## Remaining Friction

No blocker was found. Minor future polish for TASK-DEVO-167 could make the item detail less dense, for example by adding a compact/default mode and a verbose mode. That should remain read-only and should not widen autonomy.

## Safety Confirmation

- No real Codex run occurred in TASK-DEVO-166.
- No PersonalOS files were touched.
- No queue mutation was performed by the summary command.
- No review, validation, delivery request, runner execution, commit, or push was performed by the summary command.
- DevOrchestrator delivery for this task should use the existing trusted runner request flow.
