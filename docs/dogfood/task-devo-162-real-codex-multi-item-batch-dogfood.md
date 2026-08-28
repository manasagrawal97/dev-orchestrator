# TASK-DEVO-162 Real Codex Multi-Item Batch Dogfood

## Goal

Dogfood the real `devo project codex-worker-batch-run` flow on a disposable project with two tiny queue items.

The purpose was to prove that Devo can continue from one completed real Codex subprocess item to the next eligible item while preserving the v1 safety model: one task at a time, strict JSON ingest, manual review, manual validation evidence, trusted-runner-only delivery, and no direct Codex commit or push.

## Safety Boundary

This dogfood used only disposable project `Dogfood162`.

- Real Codex was not run from inside the active Codex/sandbox session.
- Real Codex was run by the operator from normal PowerShell.
- PersonalOS was not touched.
- No AI/API token integration was added.
- No parallel workers were used.
- No UI actions were added.
- Codex did not commit or push.
- Trusted runner performed both commits and pushes.

## Disposable Project

- Project: `Dogfood162`
- Work repo: `E:\DevOrchestrator\pt-162-dogfood\work`
- Bare remote: `E:\DevOrchestrator\pt-162-dogfood\remote.git`
- Remote URL: `file:///E:/DevOrchestrator/pt-162-dogfood/remote.git`
- Batch: `B001`
- Queue: `Q001`
- Policy: `POL-0001`
- Queue items: `QI001`, `QI002`
- Tasks: `T001`, `T002`
- Allowed files: `note-a.md`, `note-b.md`
- Forbidden files: `.env`, `workspace/**`
- Max changed files per task: `1`
- Max tasks per run: `1`

The disposable repo was seeded and pushed from normal PowerShell before real Codex execution so the trusted runner had a valid upstream push target.

## Setup And Dry Run

The Codex/sandbox side prepared the disposable project, planning artifacts, queue, execution policy, and worker config. The worker config used a non-WindowsApps Codex executable and the hardened command shape:

```text
codex exec -s workspace-write --output-last-message "{result_path}"
```

Prompt content was passed through stdin, and Codex was required to write strict JSON as the final result.

The dry-run command selected the first item without launching a subprocess or mutating artifacts:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood162 --policy POL-0001 --max-items 1 --max-cycles 1 --no-require-scheduler-healthy --dry-run
```

Result:

- Batch run: `CWBR-0001`
- Status: `dry_run_ready`
- Selected item: `QI001`
- Selected task: `T001`
- Mutation occurred: `False`

## Item 1 Result

- Queue item: `QI001`
- Task: `T001`
- Queue-worker run: `QWR-0001`
- Real Codex batch-run status: `completed_with_result`
- JSON result: ingested
- Review: passed
- Validation: passed
- Delivery request: `REQ-0001`
- Delivery result: completed
- Commit: `0cb7e7a`
- Commit message: `feat: complete Update note A`

What succeeded:

- `codex-worker-batch-run` launched real Codex once from normal PowerShell.
- It processed exactly one eligible queue item.
- Codex modified only `note-a.md`.
- Codex did not commit or push.
- Devo ingested strict JSON evidence.
- The flow stopped at the review gate.
- Manual review and validation evidence were recorded.
- Trusted runner delivered the commit and push.

## Item 2 Result

- Queue item: `QI002`
- Task: `T002`
- Queue-worker run: `QWR-0002`
- Real Codex batch-run status: `completed_with_result`
- JSON result: ingested
- Review: passed
- Validation: passed
- Delivery request: `REQ-0002`
- Delivery result: completed
- Commit: `18b91bd`
- Commit message: `feat: complete Update note B`

What succeeded:

- After item 1 completed, Devo selected the next eligible item.
- It did not reuse the wrong queue-worker run, preparation, worker run, ingest, or delivery request.
- Codex modified only `note-b.md`.
- Review, validation, delivery, and queue completion remained explicit gates.
- Trusted runner delivered the second commit and push.

## Final State

- Final batch-run check: `CWBR-0003`
- Final message: all allowed queue items are completed
- Disposable repo state: clean
- Direct Codex commit/push: no
- Trusted runner commits/pushes: yes, both items

## What Worked

- Real Codex multi-item continuation works when the operator runs the subprocess step from normal PowerShell.
- The v1 one-item limit remains understandable and safe.
- The queue can continue from a completed item to the next eligible item.
- Strict JSON ingest works for both real Codex runs.
- Manual review and validation gates are still enforced.
- Trusted runner remains the only delivery path.
- The completed-queue guidance added in TASK-DEVO-161 is working: the final continuation check clearly reports that all allowed queue items are completed.

## Friction Found

No blocker was reported for TASK-DEVO-162.

The remaining friction for TASK-DEVO-163 should focus on ergonomics rather than safety:

1. Capturing the normal-PowerShell output back into the dogfood report is still manual.
2. The operator still has to run separate review, validation, delivery, runner, and completion commands between items.
3. The real Codex subprocess step must remain outside Codex/sandbox, so Devo should keep making that handoff obvious.
4. A future continuation helper could summarize the exact next evidence/delivery command after each real Codex item without loosening gates.

## Verdict

PASS.

TASK-DEVO-162 proves real Codex multi-item batch continuation on a disposable project. Two queue items completed one at a time through real Codex subprocess execution, strict JSON ingest, manual review, manual validation, Devo delivery requests, and trusted runner commits/pushes. The disposable repo ended clean, Codex did not commit or push, PersonalOS was not modified, and the final batch-run check reported that all allowed queue items were completed.

TASK-DEVO-163 records the readiness checkpoint for this result in `docs/architecture/real-codex-batch-run-readiness-checkpoint.md`. The recommended next implementation task is TASK-DEVO-164: polish real multi-item continuation ergonomics and operator output capture without adding parallel workers, automatic review, automatic validation, or direct Codex commit/push.
