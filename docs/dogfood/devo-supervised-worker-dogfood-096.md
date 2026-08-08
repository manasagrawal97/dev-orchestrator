# TASK-DEVO-096 Supervised Worker Dogfood

## Summary

TASK-DEVO-096 dogfooded the supervised Codex worker flow against DevOrchestrator itself using a controlled fake `codex.cmd` shim. The scenario was "Dogfood supervised worker review gate." The fake worker printed a success-like no-op message, reported that no source files changed, and exited `0`.

No real Codex CLI was executed. No PersonalOS commands were run. No backup, restore, scheduler, AI API/model, validation automation, commit automation, or delivery automation was used during the dogfood flow.

## Fake Codex Strategy

A temporary fake `codex.cmd` was created outside the repository and later mirrored into the Codex runner's injected temporary PATH directory so Devo's safe `shutil.which("codex")` detection and guarded execution resolved to the fake command:

- Fake command used by approved run plan: `C:\Users\manas\.codex\tmp\arg0\codex-arg0Xf5Jg4\codex.CMD`
- Fake output summary:
  - `Fake Codex dogfood run succeeded.`
  - `No source files changed.`
  - `Dogfood-only supervised worker validation path.`

Important finding: creating only a temp `codex.cmd` under `%TEMP%` was not enough in this Codex desktop shell because the command runner injects its own PATH segment and the installed `codex.EXE` was otherwise preferred. The dogfood avoided real Codex execution by placing the fake shim where `execute-preview` showed the fake path.

## Commands Run

High-level command sequence:

```powershell
git status -sb
devo project context-status DevOrchestrator
devo project onboard --project DevOrchestrator
devo project settings-show --project DevOrchestrator
devo project brief-create --project DevOrchestrator --title "Dogfood supervised worker review gate" --file <temp-brief>
devo project brief-approve --project DevOrchestrator
devo project blueprint-create --project DevOrchestrator
devo project blueprint-approve --project DevOrchestrator
devo project backlog-create --project DevOrchestrator
devo project backlog-approve --project DevOrchestrator
devo project batch-suggest --project DevOrchestrator --limit 1 --write
devo project batch-approval-request --project DevOrchestrator --batch B002 --note "Dogfood fake-worker flow only." --reviewer Codex
devo project batch-review --project DevOrchestrator --batch B002 --note "Reviewed for fake-worker dogfood; no source changes expected." --reviewer Codex
devo project batch-approve --project DevOrchestrator --batch B002 --note "Approved fake-worker dogfood batch."
devo project queue-create --project DevOrchestrator --batch B002
devo project queue-start --project DevOrchestrator --queue Q002
devo worker codex prepare-next --project DevOrchestrator --queue Q002
devo worker codex run-plan --project DevOrchestrator --run WR001
devo worker codex run-plan-show --project DevOrchestrator --plan RP002
devo worker codex run-plan-approve --project DevOrchestrator --plan RP002 --note "Approved fake-worker dogfood only."
devo worker codex execute-preview --project DevOrchestrator --run WR001 --plan RP002
devo worker codex execute --project DevOrchestrator --run WR001 --plan RP002 --confirm-execute
devo project queue-complete-item --project DevOrchestrator --queue Q002 --item QI001 --note "Attempt before reviewed_passed evidence."
devo worker codex report-template --project DevOrchestrator --run WR001
devo worker codex report-validate --project DevOrchestrator --run WR001 --file <dogfood-report-json>
devo worker codex report-import --project DevOrchestrator --run WR001 --file <dogfood-report-json>
devo worker codex report-show --project DevOrchestrator --run WR001
devo worker codex review-template --project DevOrchestrator --run WR001
devo worker codex review-attach-evidence --project DevOrchestrator --run WR001 --status provided --summary "Fake-worker dogfood evidence only; no source changes expected."
devo worker codex review-record --project DevOrchestrator --run WR001 --status reviewed_passed --reviewer "Codex" --note "Reviewed fake-worker dogfood output; no source changes expected."
devo project queue-complete-item --project DevOrchestrator --queue Q002 --item QI001 --note "Completed fake-worker dogfood item after reviewed_passed evidence."
devo project progress --project DevOrchestrator
devo worker codex queue-status --project DevOrchestrator --queue Q002
```

## Generated Workspace Artifacts

Planning artifacts:

- `workspace/projects/DevOrchestrator/planning/project-brief.json`
- `workspace/projects/DevOrchestrator/planning/project-brief.md`
- `workspace/projects/DevOrchestrator/planning/blueprint.json`
- `workspace/projects/DevOrchestrator/planning/blueprint.md`
- `workspace/projects/DevOrchestrator/planning/backlog.json`
- `workspace/projects/DevOrchestrator/planning/backlog.md`
- `workspace/projects/DevOrchestrator/planning/batches/batch-B002.json`
- `workspace/projects/DevOrchestrator/planning/batches/batch-B002.md`
- `workspace/projects/DevOrchestrator/planning/batches/approvals/batch-B002-approval.json`
- `workspace/projects/DevOrchestrator/planning/batches/approvals/batch-B002-approval.md`
- `workspace/projects/DevOrchestrator/planning/queues/queue-Q002.json`
- `workspace/projects/DevOrchestrator/planning/queues/queue-Q002.md`
- `workspace/projects/DevOrchestrator/planning/handoffs/handoff-H002.json`
- `workspace/projects/DevOrchestrator/planning/handoffs/handoff-H002.md`

Worker artifacts:

- `workspace/projects/DevOrchestrator/workers/codex/worker-run-WR001.json`
- `workspace/projects/DevOrchestrator/workers/codex/worker-run-WR001.md`
- `workspace/projects/DevOrchestrator/workers/codex/run-plans/run-plan-RP002.json`
- `workspace/projects/DevOrchestrator/workers/codex/run-plans/run-plan-RP002.md`
- `workspace/projects/DevOrchestrator/workers/codex/logs/worker-run-WR001.log`
- `workspace/projects/DevOrchestrator/workers/codex/logs/worker-run-WR001.stderr.log`
- `workspace/projects/DevOrchestrator/workers/codex/reports/report-WR001-template.json`
- `workspace/projects/DevOrchestrator/workers/codex/reports/report-WR001-template.md`
- `workspace/projects/DevOrchestrator/workers/codex/reports/report-WR001-dogfood.json`
- `workspace/projects/DevOrchestrator/workers/codex/reports/report-WR001.json`
- `workspace/projects/DevOrchestrator/workers/codex/reports/report-WR001.md`
- `workspace/projects/DevOrchestrator/workers/codex/reviews/review-WR001.json`
- `workspace/projects/DevOrchestrator/workers/codex/reviews/review-WR001.md`

These are workspace artifacts and must not be committed.

## State Transitions Observed

Observed IDs:

- Batch: `B002`
- Queue: `Q002`
- Queue item: `QI001`
- Handoff: `H002`
- Worker run: `WR001`
- Approved fake run plan: `RP002`
- Review: `REV-WR001`

Observed transitions:

- Queue `Q002`: `ready` -> `running` -> `waiting_review` -> `completed`
- Queue item `QI001`: `pending` -> `running` -> `waiting_review` -> `completed`
- Worker run `WR001`: `planned` -> `waiting_review`
- Report status: `missing` -> `present`
- Review status: `draft` -> `reviewed_passed`

Successful fake execution moved the worker run, linked queue item, and queue to `waiting_review`. No queue item or backlog task was completed automatically.

## Review Gate Result

Before review, this command was attempted:

```powershell
devo project queue-complete-item --project DevOrchestrator --queue Q002 --item QI001 --note "Attempt before reviewed_passed evidence."
```

Result: refused. Devo reported that `QI001` was not completion-ready because linked worker run `WR001` had no worker review artifact. The output printed next commands for `review-template` and `review-record`, plus the discouraged `--confirm-without-review` emergency override note.

After review evidence was attached and `reviewed_passed` was recorded, this command succeeded:

```powershell
devo project queue-complete-item --project DevOrchestrator --queue Q002 --item QI001 --note "Completed fake-worker dogfood item after reviewed_passed evidence."
```

Result: queue `Q002` became `completed`, item `QI001` became `completed`, and project progress showed one completed backlog task.

## UI/API Smoke

The optional local API/UI smoke was skipped because existing local servers did not respond within a short timeout:

- `http://127.0.0.1:8765/api/health`: timed out
- `http://127.0.0.1:5173`: timed out

The servers were not started for this dogfood because this task was operational validation/docs-first and the instruction said to skip if not already running and quick.

## What Worked

- The full planning -> batch -> queue -> handoff -> worker run -> run plan -> fake execution -> report import -> review evidence -> gated completion path worked end to end.
- `execute-preview` clearly showed the executable path, which made it possible to verify the fake command would be used before execution.
- Successful fake execution correctly moved worker/queue/item state to `waiting_review`, not completed.
- Worker report import preserved the distinction between worker-reported evidence and trusted delivery proof.
- `queue-complete-item` correctly blocked before review and allowed completion after `reviewed_passed`.
- The fake execution log clearly stated it was evidence only and not proof of completion.

## Awkward Or Confusing Parts

- Fake executable setup was awkward in the Codex desktop shell because the shell injects a temporary PATH segment and the installed `codex.EXE` was preferred over a normal `%TEMP%` fake `codex.cmd`.
- `prepare-next` created `RP001` before the fake shim was visible, so a second run plan `RP002` was created to capture the correct fake executable path. The old run plan remains as workspace history.
- `queue-status` after queue completion no longer shows linked worker/review context because there is no active item. `queue-show` shows completion state, but the worker linkage is less visible after completion.
- The deterministic starter backlog generated generic task text. It was acceptable for no-op dogfood, but real work needs backlog refinement before execution.
- The command flow is long. It is safe, but still tedious for the operator.

## Safety Gaps Or Follow-Ups

- Consider a configurable or explicit Codex executable path for supervised worker dogfood/testing so fake-worker validation does not depend on PATH quirks.
- Consider a queue item history/detail command that shows linked worker/report/review evidence even after the item is completed.
- Consider a compact `worker codex dogfood` or `worker codex smoke` helper that prepares a fake-only supervised run without requiring the full manual sequence.
- Consider clearer UI/API smoke guidance from `devo ui status` for when servers are not running.

## Recommended Next Task

Recommended TASK-DEVO-097: Worker flow operator polish.

Suggested scope:

- Add safer fake-executable/test-mode guidance or a `--codex-executable`/configured executable path design.
- Improve completed queue item evidence visibility.
- Add a compact operator summary command for the post-execution review gate.
- Keep commit/push automation and real Codex execution/delivery automation out of scope until this operator path is smoother.
