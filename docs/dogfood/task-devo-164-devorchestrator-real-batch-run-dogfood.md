# TASK-DEVO-164 DevOrchestrator Real Batch-Run Dogfood

## Scope And Evidence Cutoff

This report records the live, two-item, docs-only TASK-DEVO-164 dogfood against the DevOrchestrator repository. It reflects evidence available when `T002` / `QI002` / `QWR-0002` entered worker execution on 2026-08-28. Item 2 review, validation, delivery, and commit are intentionally reported as pending where they had not yet occurred.

## Policy

- Policy: `POL-0002`, approved by Manas on 2026-08-28
- Risk: low
- Batch and queue: `B004` / `Q004`
- Allowed tasks and items: `T001`, `T002` / `QI001`, `QI002`
- Allowed files: `docs/how-to-use-devo.md` and this report
- Per-task limit: one changed file and one task per run
- Required validation: `git diff --check`
- Required evidence: worker review and validation
- Delivery boundary: worker execution must not stage, commit, or push; guarded delivery remains trusted-runner-only

The policy allowed automatic delivery and push after the required gates, but it did not authorize the worker to perform either operation.

## Batch

Planning batch `B004`, titled `TASK-DEVO-164 real Codex internal docs dogfood`, was approved with two low-risk docs-only tasks. `T002` depended on `T001`, which made the intended sequence explicit.

- `T001`: add a real batch operating-mode note to `docs/how-to-use-devo.md`
- `T002`: create this dogfood report

## Queue

Execution queue `Q004` preserved the two-item order. After trusted delivery completed for item 1, Devo marked `QI001` completed and selected `QI002` as the next eligible item. At this report's evidence cutoff, `QI002` was pending in the queue while its queue-worker run waited for worker evidence.

## Queue-Worker Runs

### QWR-0001 / T001 / QI001

`QWR-0001` selected `QI001`, linked handoff `H004` and worker run `WR003`, and moved through worker, review, validation, and delivery gates. Its final status was `completed`, with trusted delivery request `REQ-0052` completed.

### QWR-0002 / T002 / QI002

`QWR-0002` started after item 1 delivery completed. It selected `QI002`, skipped completed `QI001`, and linked handoff `H005` and worker run `WR004`. Its recorded status at the cutoff was `waiting_worker`, with no blockers or warnings. This was the correct safe stop while this report was being authored.

## Codex Batch Runs

`CWBR-0001` processed exactly one item. It created `QWR-0001`, prepared package `CWP-20260828071814-QWR-0001`, ran the configured real Codex subprocess from normal PowerShell, ingested strict JSON as `CWI-20260828071900-QWR-0001`, and stopped at `waiting_review` because review evidence was intentionally manual.

`CWBR-0002` was invoked before the missing review evidence was recorded. It processed no new item and stopped on the existing `QWR-0001` review boundary. This was a safe, non-bypassing result, though the extra invocation added operator noise. After the item-1 gates and trusted delivery completed, the next-item flow created `QWR-0002` and its preparation package `CWP-20260828083809-QWR-0002`.

No batch-run artifact for automatic item-2 completion existed at the cutoff, and none is claimed here.

## Manual Gates

The run preserved the intended human-controlled boundaries:

1. Real Codex execution occurred from normal PowerShell under the narrow approved policy.
2. Strict worker JSON was ingested, then the batch run stopped for review.
3. Item 1 review was recorded manually after checking the focused diff and file scope.
4. Item 1 validation was recorded manually after `git diff --check` and repository-status review.
5. Only after those gates did Devo create a trusted delivery request.
6. Item 2 must repeat review and validation before any delivery request can be created.

The validation artifact warns, correctly, that manually recorded validation was not automatically executed or independently verified by Devo.

## Delivery

Item 1 used trusted delivery request `REQ-0052`. The normal-PowerShell trusted runner completed index-lock preflight, delivery check and plan `DEL-0132`, delivery approval, report preparation, commit preview, guarded commit, push preview, and guarded push to `origin/main`.

The delivery runner reported two reviewable warnings: the repository had the expected uncommitted documentation change before delivery, and documentation-only secret terminology appeared in `docs/how-to-use-devo.md`. Neither warning represented a forbidden path or an actual secret-risk file.

Item 2 had no delivery request at the cutoff. Its eventual delivery must remain behind worker-result ingestion, manual review, manual validation, and trusted-runner gates.

## Commit

Item 1 was committed and pushed by the trusted runner as:

- Commit: `f9360f785c5b720b0759d447a2b99c8e47d9c115`
- Message: `feat: complete Add real batch operating-mode note`
- Changed file: `docs/how-to-use-devo.md`
- Remote and branch: `origin/main`

The Codex worker did not stage, commit, or push. Item 2 had no commit at the cutoff.

## Friction

1. The operator needed several explicit commands between worker ingest, review, validation, delivery request, runner execution, and next-item selection. The safety boundaries were clear, but capturing the resulting identifiers and outputs for a final report remained manual.
2. Re-running `codex-worker-batch-run` while `QWR-0001` waited for review produced `CWBR-0002`, which safely stopped but did not advance work. A clearer current-position summary could prevent this redundant invocation.
3. The batch-run artifact ends at the review gate, while later review, validation, delivery, commit, and push evidence lives in separate artifacts. Reconstructing one item lifecycle requires joining several read-only records.
4. Queue state and queue-worker state briefly describe the active second item differently (`QI002` pending while `QWR-0002` is `waiting_worker`). This is internally consistent, but a consolidated operator readout would reduce interpretation cost.
5. The report necessarily has an evidence cutoff: its own item-2 delivery and commit cannot be known before the report has passed downstream gates.

## Verdict

PASS for the evidence available at the cutoff. TASK-DEVO-164 demonstrated a real Codex docs-only item on the live DevOrchestrator repository under a narrow approved policy, strict one-item execution, manual review, manual validation, and trusted-runner-only commit and push. It also demonstrated safe continuation to the dependent second item without parallel execution or gate bypass.

The verdict is not a claim that `T002` was already reviewed, validated, delivered, or committed. Those states remain pending until Devo records their evidence after this worker result.

## Next Task

The next follow-up should improve read-only operator ergonomics without widening autonomy: add a consolidated real-batch position summary that joins policy, queue item, queue-worker run, Codex batch run, review, validation, delivery request, commit, and push state, and prints the single correct next command. Keep review, validation, trusted delivery, commit, and push manual or trusted-runner-controlled, and retain one-item-at-a-time execution.

For this run, the immediate next action is to ingest the strict JSON worker result for `QWR-0002`, review this focused diff, record passing validation only after `git diff --check`, and continue through the existing trusted delivery gates.

## Reviewer Update Before Delivery

After this report was generated, item 2 worker execution completed through `codex-worker-batch-run` as `CWBR-0003`.

- Queue-worker run: `QWR-0002`
- Queue item / task: `QI002` / `T002`
- Preparation: `CWP-20260828083809-QWR-0002`
- Codex worker run: `CWR-20260828083810-QWR-0002`
- Ingest: `CWI-20260828084019-QWR-0002`
- Current state before review: `waiting_review`

The earlier cutoff language remains useful as a record of what the worker knew while writing the report. The current operator next action is no longer result ingest; it is manual review, manual validation, delivery-request creation, and trusted-runner delivery for `QWR-0002`.
