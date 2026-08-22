# TASK-DEVO-137 Queue-Worker Friction Polish

## Goal

TASK-DEVO-137 addressed small usability issues found by the TASK-DEVO-136 live three-task assisted dogfood. The task stayed inside the assisted queue-worker model: no real Codex subprocess, no AI/API call, no UI controls, no background daemon change, no PersonalOS work, and no delivery safety bypass.

## TASK-DEVO-136 Friction Addressed

- `queue-worker-loop` now prints evidence-intake commands at the worker, review, and validation stop boundaries.
- Validation evidence that is present but not passing no longer falls through to generic `unknown or unsafe state` wording.
- Execution policy approval/check wording no longer implies a fully autonomous worker.
- Temporary dogfood repo guidance now explains that trusted delivery push tests need a valid disposable remote.
- `runner-watch-latest` now explains when an older `no_pending` watch artifact may coexist with a newer requested runner item.

## Commands And Output Improved

When a loop stops at `waiting_worker`, the next action points to:

```powershell
devo project queue-worker-record-worker-result --project <project> --run <QWR-ID> --status completed --summary "<summary>" --confirm-record
```

When it stops at `waiting_review`, the next action points to:

```powershell
devo project queue-worker-record-review --project <project> --run <QWR-ID> --status passed --summary "<summary>" --confirm-record
```

When it stops at missing validation evidence, the next action points to:

```powershell
devo project queue-worker-record-validation --project <project> --run <QWR-ID> --status passed --summary "<summary>" --confirm-record
```

## Validation-State Wording

Non-passing validation evidence now stops with clearer wording:

```text
Stop reason: validation evidence is not passing
Next action: Validation status: <status>. Fix validation issue, record new validation evidence, or retry/pause the queue-worker run.
```

Failed validation is still not success and remains a blocking failure. Blocked or not-run validation evidence remains non-passing and does not create delivery requests.

## Policy Wording

Execution policy approval output now describes the policy as an approved assisted queue policy. The command still creates only policy approval evidence; it does not run Codex, run validation, request delivery, commit, push, or modify a target repository.

## Temporary Dogfood Delivery Guidance

For disposable dogfood projects, use a valid local Git remote before testing trusted delivery push. A failed temp push is still a real safety stop. Do not manually `git add`, `git commit`, or `git push` around Devo during dogfood.

If `runner-watch-latest` reports an older `no_pending` watch but `runner-latest` shows a newer requested item, run `runner-watch` again or use the precise `runner-run --request <REQ-ID>` fallback.

## Runner-Watch Investigation

The TASK-DEVO-136 observation was consistent with artifact timing rather than a queue selection rewrite need: `runner-watch-latest` displays the most recent watch artifact, while `runner-latest` displays the most recent runner request. A watch that completed before a later request was created can truthfully show `no_pending`.

The small fix is diagnostic output: when the latest watch is `no_pending` and the latest runner request is a newer `requested` item, Devo now points to `runner-watch`/`runner-run` instead of leaving the operator to reconcile the two commands.

## Remaining Gaps Before Real Codex-Worker Integration

- A real non-WindowsApps Codex launcher or approved wrapper is still required before real supervised Codex execution.
- Multi-item continuation still depends on completed trusted delivery for each item.
- Queue-worker flow remains assisted; Devo does not run real Codex, validation, runner-watch, commit, push, or parallel work from the queue loop.
- UI controls for queue execution remain deferred.

## Recommended Next Task

TASK-DEVO-138 should run a smaller follow-up dogfood after this polish, preferably with a known-good disposable local remote or a docs-only DevOrchestrator queue item that can use the normal trusted runner path.
