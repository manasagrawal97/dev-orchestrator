# Real Codex Supervised Dry-Run Runbook

Source/freshness: TASK-DEVO-100, after TASK-DEVO-099 found the WindowsApps `codex.exe` launch failure and TASK-DEVO-100 added Codex executable diagnostics and launch-failure handling.

## Purpose

This runbook is for the first real Codex supervised worker dry-run through Devo.

The goal is to validate controlled orchestration, not productivity. The first real run should be a no-op or docs-only inspection task that proves Devo can launch real Codex through an approved run plan, capture evidence, preserve review gates, and stop before delivery automation.

The first dry-run must not automatically complete work, trust validation, commit, push, or mutate delivery state. Codex output is evidence only until a human reviews it and explicitly records the next Devo state transition.

## Preconditions

Before starting:

- DevOrchestrator repo is clean: `git status -sb`.
- Backup health is known and acceptable.
- API/UI may be running, but they are optional and not required.
- Real Codex CLI is installed and authenticated.
- Codex executable path is known or `codex` is available on `PATH`.
- `devo worker codex doctor` does not report a WindowsApps app execution alias as the selected launch path.
- Devo tests are currently passing from recent source validation.
- The user has enough Codex usage available for a short run.
- Target project is DevOrchestrator first, not PersonalOS.
- The selected queue item is intentionally low risk.
- Workspace artifacts are not staged.

Do not start with PersonalOS. PersonalOS remains a real-world test project for later controlled batches, not the first real supervised Codex launch.

## Allowed First Real Dry-Run Scope

Use a no-op or docs-only inspection task. Prefer a task that produces a report and no file changes.

Allowed first-run shape:

- docs-only or no-op inspection
- no source code changes
- no target repository command execution unless separately approved
- no commit or push
- no backup, restore, or scheduler changes
- no PersonalOS
- no model/API integration beyond the existing local Codex CLI process

Example safe task:

```text
Inspect the README and docs/current-state.md and report whether the supervised worker instructions are understandable. Do not modify files.
```

## Stop Conditions

Stop immediately if:

- Codex asks for extra permissions outside scope.
- Codex tries to modify source unexpectedly.
- Codex tries to run risky commands.
- Codex asks to commit or push.
- Codex reaches a usage limit.
- A safety gate blocks execution.
- Output is unclear or missing a final report.
- Workspace artifacts appear staged.
- Target repo status becomes dirty unexpectedly.
- The prompt, run plan, executable path, or target path does not match what was approved.
- `execute-preview` does not show the expected executable and paths.

## Exact Operator Sequence

Use placeholders until real ids exist:

- `<project>`: expected first value is `DevOrchestrator`
- `<queueId>`: execution queue id
- `<workerRunId>`: Codex worker run id
- `<planId>`: run plan id
- `<itemId>`: queue item id
- `<reportFile>`: filled worker report JSON

Create or choose a safe planning path:

```powershell
devo project brief-create --project <project> --title "Real Codex supervised dry-run" --file <safeBriefFile>
devo project brief-approve --project <project>
devo project blueprint-create --project <project>
devo project blueprint-approve --project <project>
devo project backlog-create --project <project>
devo project backlog-approve --project <project>
devo project batch-suggest --project <project> --limit 1 --write
devo project batch-approval-request --project <project> --batch <batchId> --note "First real Codex supervised dry-run; no-op/docs-only scope."
devo project batch-review --project <project> --batch <batchId> --note "Reviewed for no-op/docs-only dry-run."
devo project batch-approve --project <project> --batch <batchId> --note "Approved for first real supervised dry-run."
devo project queue-create --project <project> --batch <batchId>
devo project queue-start --project <project> --queue <queueId>
```

Prepare exactly one worker item:

```powershell
devo project handoff-next --project <project> --queue <queueId>
devo worker codex run-create --project <project> --handoff <handoffId>
```

Or use the queue shortcut:

```powershell
devo worker codex prepare-next --project <project> --queue <queueId>
```

Inspect before execution:

```powershell
devo worker codex queue-status --project <project> --queue <queueId>
devo worker codex flow-summary --project <project> --queue <queueId>
devo worker codex doctor --project <project>
devo worker codex preflight --project <project> --run <workerRunId>
devo worker codex run-plan --project <project> --run <workerRunId>
devo worker codex run-plan-show --project <project> --plan <planId>
devo worker codex run-plan-approve --project <project> --plan <planId> --note "Approved first real Codex dry-run only."
devo worker codex execute-preview --project <project> --run <workerRunId> --plan <planId>
```

Run only after preview is correct:

```powershell
devo worker codex execute --project <project> --run <workerRunId> --plan <planId> --confirm-execute
devo worker codex execute-log --project <project> --run <workerRunId>
devo worker codex flow-summary --project <project> --queue <queueId>
```

Record worker output and human review:

```powershell
devo worker codex report-template --project <project> --run <workerRunId>
devo worker codex report-validate --project <project> --run <workerRunId> --file <reportFile>
devo worker codex report-import --project <project> --run <workerRunId> --file <reportFile>
devo worker codex review-template --project <project> --run <workerRunId>
devo worker codex review-attach-evidence --project <project> --run <workerRunId> --status provided --summary "First real dry-run evidence reviewed; no source changes expected."
devo worker codex review-record --project <project> --run <workerRunId> --status reviewed_passed --reviewer "<name>" --note "Reviewed dry-run evidence; safe to complete queue item."
```

Complete only after review:

```powershell
devo project queue-complete-item --project <project> --queue <queueId> --item <itemId> --note "Completed first real supervised dry-run after review."
devo project progress --project <project>
devo worker codex queue-status --project <project> --queue <queueId> --item <itemId>
git status -sb
```

If review is not safe, do not complete. Use one of:

```powershell
devo worker codex review-record --project <project> --run <workerRunId> --status reviewed_needs_changes --reviewer "<name>" --note "<reason>"
devo worker codex review-record --project <project> --run <workerRunId> --status rejected --reviewer "<name>" --note "<reason>"
devo project queue-block-item --project <project> --queue <queueId> --item <itemId> --note "<reason>"
```

## Real Codex Path Guidance

Run `devo worker codex doctor` before the first real run. The doctor command is read-only: it resolves the candidate executable, reports whether the path exists, identifies WindowsApps app execution aliases, and does not run `codex --version`.

Prefer normal `PATH` detection only when the doctor reports a normal launchable executable.

On Windows, `PATH` can resolve `codex.exe` to a Windows App Execution Alias or package path under `WindowsApps`. That path can pass existence checks and still fail when Devo calls `subprocess.run`/`CreateProcess`. Devo now blocks those paths for guarded execution and prints:

```text
Codex resolved to WindowsApps app execution alias and may not be launchable by Devo. Use --codex-path with a real executable/wrapper path.
```

The preferred workaround is to create or choose a real local executable/wrapper script and pass it explicitly with `--codex-path`. Do not use `shell=True` as a workaround; it would weaken Devo's launch boundary and make command auditing harder.

TASK-DEVO-101 confirmed that this machine currently exposes only the blocked WindowsApps Codex paths through normal command discovery. Do not retry real supervised execution here until a safe non-WindowsApps wrapper or executable path exists and `devo worker codex doctor --codex-path <path>` reports no launch blockers.

Use `--codex-path` only if `PATH` resolution is unreliable or ambiguous:

```powershell
devo worker codex preflight --project <project> --run <workerRunId> --codex-path <realCodexPath>
devo worker codex run-plan --project <project> --run <workerRunId> --codex-path <realCodexPath>
devo worker codex execute-preview --project <project> --run <workerRunId> --plan <planId> --codex-path <realCodexPath>
devo worker codex execute --project <project> --run <workerRunId> --plan <planId> --confirm-execute --codex-path <realCodexPath>
```

Do not use a fake Codex path for the first real dry-run. Fake executable testing was already covered by TASK-DEVO-096 and TASK-DEVO-097 tests.

Always verify `execute-preview` before `execute`. The preview must show the expected executable path, target repo path, prompt path, and empty blocker list.

Do not run `codex --version` from Devo as part of this runbook. If the operator wants to inspect Codex installation manually, do that outside this Devo worker flow and record the result separately.

## Expected State Transitions

Expected path:

- `execute` success -> worker run moves to `waiting_review`.
- `execute` success -> linked queue item and queue move to `waiting_review`.
- `report-import` -> report metadata only.
- `review-record reviewed_passed` -> review metadata only.
- `queue-complete-item` -> queue item completes explicitly.
- Queue/task completion does not happen before explicit completion.
- Commit/push never happens automatically.

Failure path:

- execution failure -> worker run `failed`, queue paused or waiting for review depending on classification
- usage limit -> `paused_usage_limit`
- safety/approval block -> `blocked_needs_approval` or waiting review
- review rejected -> queue remains incomplete

## Review And Report Expectations

The Codex final report should include:

- summary
- changed files, ideally none for the first dry-run
- commands run, ideally none or safe inspection only
- validation performed, if any
- blockers
- safety notes
- follow-up recommendations

For the first real dry-run, "no files changed" is a good result. Do not treat a productive implementation as better than a clean no-op validation of the orchestration path.

## Recovery Plan

If execution fails:

```powershell
devo worker codex doctor --project <project>
devo worker codex execute-log --project <project> --run <workerRunId>
devo worker codex run-show --project <project> --run <workerRunId>
devo worker codex flow-summary --project <project> --queue <queueId>
```

If usage limit is reached:

- Leave the queue paused as `paused_usage_limit`.
- Do not complete the queue item.
- Resume later with a new explicit plan after usage is available.

If output is unsafe:

- Record review as `reviewed_needs_changes` or `rejected`.
- Optionally block the queue item with `queue-block-item`.
- Do not complete, validate, commit, or push.

If the repo becomes dirty unexpectedly:

```powershell
git status -sb
git diff -- <changed-files>
```

Inspect manually. Do not commit until the diff is understood and explicitly approved.

If workspace artifacts were generated:

- Do not stage `workspace/`.
- Do not stage generated reports, logs, run plans, handoffs, queues, or planning artifacts.
- Keep generated workspace state local unless a separate docs task intentionally summarizes it.

## Success Criteria

The first real dry-run is successful if:

- real Codex launched only through an approved run plan and `--confirm-execute`
- `execute-preview` matched the intended executable, prompt, and target paths
- queue moved to `waiting_review`
- no source files changed unexpectedly
- report was imported or manually summarized
- review gate worked
- explicit queue completion worked only after review
- repo ended clean, or an expected docs-only diff was intentionally handled
- no workspace artifacts were committed
- no PersonalOS commands were run
- no backup, restore, scheduler, validation, commit, push, or delivery automation was triggered

## Next Decisions After Dry-Run

Possible follow-up tasks:

- TASK-DEVO-099: First real Codex supervised dry-run execution report.
- TASK-DEVO-100: Codex executable diagnostics and launch-failure hardening.
- Future: Delivery/commit safety design before automation.
- Future: Worker run recovery/pause polish.
- Future: Validation-result integration.

Do not proceed from the first real dry-run directly into commit/push automation. Treat the dry-run report as evidence for the next safety design decision.
