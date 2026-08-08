# TASK-DEVO-099 Real Codex Supervised Dry-Run Report

Source/freshness: TASK-DEVO-099, following `docs/runbooks/real-codex-supervised-dry-run.md`.

## Summary

TASK-DEVO-099 attempted the first real Codex supervised worker dry-run through Devo against DevOrchestrator itself.

The dry-run did not successfully launch a real Codex process. Devo reached the approved guarded execution step and attempted to start the detected WindowsApps Codex executable, but Windows denied `CreateProcess` with `PermissionError: [WinError 5] Access is denied` before Codex produced stdout/stderr or a final report.

This is still useful operational validation: the runbook preconditions, planning path, run-plan approval, preview, failure evidence import, review gate, and blocked queue state all worked without source changes, PersonalOS access, commit/push, backup/restore, scheduler changes, target command execution, or workspace artifact staging.

## Scope

Approved worker task:

```text
Inspect README.md, docs/current-state.md, and docs/runbooks/real-codex-supervised-dry-run.md. Report whether the supervised worker instructions are understandable. Do not modify files. Do not run tests. Do not commit. Do not push. Final report only.
```

The refined Devo backlog task preserved that scope:

- Project: `DevOrchestrator`
- Batch: `B003`
- Queue: `Q003`
- Queue item: `QI001`
- Handoff: `H003`
- Worker run: `WR002`
- Run plan: `RP003`
- Review: `REV-WR002`

## Preconditions Checked

- `git status --short`: clean before the worker path.
- `devo doctor --project DevOrchestrator`: overall `OK`.
- `devo project context-status DevOrchestrator`: `CONTEXT_APPROVED`.
- Target project: `DevOrchestrator`.
- PersonalOS was not touched.
- Backup/restore and scheduler commands were not run.
- The runbook was read before execution.

Doctor notes:

- Backup root discovery was skipped because no backup root was discoverable through doctor.
- Scheduled task check timed out after 2 seconds and was skipped as optional.
- Project Git status was clean on `main`, ahead `0`, behind `0`.

## Commands Run

Initial checks:

```powershell
git status --short
devo doctor --project DevOrchestrator
devo project context-status DevOrchestrator
```

Planning setup:

```powershell
devo project brief-create --project DevOrchestrator --title "First real Codex supervised dry-run" --file E:\DevOrchestrator\workspace\tmp\real-codex-dry-run-brief.md
devo project brief-show --project DevOrchestrator
devo project brief-approve --project DevOrchestrator
devo project blueprint-create --project DevOrchestrator
devo project blueprint-show --project DevOrchestrator
devo project blueprint-approve --project DevOrchestrator
devo project backlog-create --project DevOrchestrator
devo project backlog-show --project DevOrchestrator
devo project task-list --project DevOrchestrator
devo project task-show --project DevOrchestrator --task T001
devo project backlog-validate --project DevOrchestrator --file E:\DevOrchestrator\workspace\tmp\real-codex-dry-run-backlog.json
devo project backlog-import --project DevOrchestrator --file E:\DevOrchestrator\workspace\tmp\real-codex-dry-run-backlog.json
devo project backlog-show --project DevOrchestrator
devo project task-show --project DevOrchestrator --task T001
devo project backlog-approve --project DevOrchestrator
devo project batch-suggest --project DevOrchestrator --limit 1 --write
devo project batch-approval-request --project DevOrchestrator --batch B003 --note "First real Codex supervised dry-run; no-op/docs-only scope." --reviewer Codex
devo project batch-approval-show --project DevOrchestrator --batch B003
devo project batch-review --project DevOrchestrator --batch B003 --note "Reviewed for first real Codex no-op/docs-inspection dry-run; scope is read-only and DevOrchestrator-only." --reviewer Codex
devo project batch-approve --project DevOrchestrator --batch B003 --note "Approved for first real Codex supervised no-op/docs-inspection dry-run only." --approver Codex
devo project queue-create --project DevOrchestrator --batch B003
devo project queue-start --project DevOrchestrator --queue Q003
```

Worker preparation and preview:

```powershell
devo worker codex prepare-next --project DevOrchestrator --queue Q003
devo worker codex flow-summary --project DevOrchestrator --queue Q003
devo worker codex preflight --project DevOrchestrator --run WR002
devo worker codex run-plan-show --project DevOrchestrator --plan RP003
git status --short
devo worker codex run-plan-approve --project DevOrchestrator --plan RP003 --note "Approved first real Codex no-op/docs-inspection dry-run only."
devo worker codex execute-preview --project DevOrchestrator --run WR002 --plan RP003
```

Guarded launch attempt:

```powershell
devo worker codex execute --project DevOrchestrator --run WR002 --plan RP003 --confirm-execute
```

Post-failure recovery and review:

```powershell
git status --short
devo worker codex run-show --project DevOrchestrator --run WR002
devo worker codex flow-summary --project DevOrchestrator --queue Q003
devo worker codex execute-log --project DevOrchestrator --run WR002
devo worker codex report-template --project DevOrchestrator --run WR002
devo worker codex report-validate --project DevOrchestrator --run WR002 --file E:\DevOrchestrator\workspace\tmp\real-codex-dry-run-WR002-report.json
devo worker codex report-import --project DevOrchestrator --run WR002 --file E:\DevOrchestrator\workspace\tmp\real-codex-dry-run-WR002-report.json
devo project queue-complete-item --project DevOrchestrator --queue Q003 --item QI001 --note "Attempt completion before reviewed_passed evidence."
devo worker codex review-template --project DevOrchestrator --run WR002
devo worker codex review-attach-evidence --project DevOrchestrator --run WR002 --status failed --summary "First real Codex dry-run launch failed before Codex produced output; no source changes expected."
devo worker codex review-record --project DevOrchestrator --run WR002 --status rejected --reviewer "Codex" --note "First real Codex dry-run launch failed with Windows CreateProcess access denied before Codex output; do not complete queue item."
devo project queue-block-item --project DevOrchestrator --queue Q003 --item QI001 --note "First real Codex dry-run launch failed before Codex output: Windows CreateProcess access denied for WindowsApps codex.exe path."
devo worker codex flow-summary --project DevOrchestrator --queue Q003
devo project queue-show --project DevOrchestrator --queue Q003
devo project progress --project DevOrchestrator
```

## Run Plan And Preview

Run plan `RP003` passed preflight and had no blockers.

Detected executable:

```text
C:\Program Files\WindowsApps\OpenAI.Codex_26.803.5235.0_x64__2p2nqsd0c76g0\app\resources\codex.EXE
```

Preview result:

- Ready: `True`
- Working directory: `E:\DevOrchestrator`
- Prompt path: `E:\DevOrchestrator\workspace\projects\DevOrchestrator\planning\handoffs\handoff-H003.md`
- Approval status: `approved`
- Preflight status: `passed`
- Blocked reasons: none
- Warning: Devo reported that execution used an explicit executable path from the stored run plan and asked the operator to confirm that controlled operation was intended.

The preview was correct for the approved DevOrchestrator no-op/docs-inspection scope.

## Launch Result

The guarded launch failed before Codex started:

```text
PermissionError: [WinError 5] Access is denied
```

The traceback came from Python `subprocess.run([preview.executable_path], ...)` while calling Windows `CreateProcess` for the detected WindowsApps `codex.exe` path.

No Codex final output was produced. No stdout/stderr worker logs were created.

## State Transitions

Observed state transitions:

- Queue `Q003`: `ready` -> `running` -> `waiting_review`
- Queue item `QI001`: `pending` -> `running` -> `blocked`
- Worker run `WR002`: `planned` -> `running` -> `failed`
- Report status: `missing` -> `validated`
- Review `REV-WR002`: `draft` -> `rejected`
- Validation evidence: `provided` from report template -> `failed`
- Backlog task `T001`: `ready` -> `blocked`

No queue item or backlog task was completed.

## Git Status And File Changes

Git status before the worker path was clean.

Git status after the failed launch was clean.

No source files were changed by the worker. The only files changed for this task are the docs committed after the operational report was written.

Generated workspace artifacts were left under `workspace/` and were not staged or committed.

## Report Import Result

Imported report:

```text
E:\DevOrchestrator\workspace\projects\DevOrchestrator\workers\codex\reports\report-WR002.json
E:\DevOrchestrator\workspace\projects\DevOrchestrator\workers\codex\reports\report-WR002.md
```

Report summary:

- Worker reported status: `failed`
- Changed files: `0`
- Validation attempted: `false`
- Validation results: clean post-failure Git status; no logs because launch failed before process start
- Blockers: Windows denied `CreateProcess` for the WindowsApps Codex executable path; a safer real launch path is needed

The report was operator-generated because no Codex final report existed.

## Review Gate Result

Before review, `queue-complete-item` refused completion:

```text
Linked worker run WR002 has no worker review artifact.
```

After report import, the review was recorded as `rejected` with failed validation evidence. The queue item was explicitly blocked instead of completed.

Final `flow-summary` showed:

- Queue: `Q003 | status=waiting_review`
- Item: `QI001 | status=blocked`
- Worker run: `WR002 | status=failed`
- Report: `failed`
- Review: `rejected | validation=failed`
- Completion ready: `no`
- Completion blockers:
  - Worker review status is rejected, not reviewed_passed.
  - Worker review validation evidence status is failed.

## Issues Found

1. Real Codex executable path detection found a WindowsApps package executable that passed `Path.exists()`/`is_file()` checks but could not be launched by `subprocess.run`.
2. Devo's guarded execution path set the worker run to `running` before the launch attempt and did not catch `PermissionError`; the worker stayed `running` until report import corrected it.
3. No failure logs were written for launch exceptions that happen before `subprocess.run` returns.
4. `flow-summary` after a rejected/failed review still suggests `review-record --status reviewed_passed`; it should prefer blocker/retry guidance when validation is failed or review is rejected.

## Safety Gaps

- The first real run needs an accessible real Codex launch path, likely a stable shim or explicit executable path that is not the WindowsApps package target.
- Devo should catch launch-time `OSError`/`PermissionError`, mark the worker and queue failed/paused, and write failure logs automatically.
- The runbook should mention WindowsApps executable access as a known possible failure mode after this dogfood.
- Delivery/commit automation should remain deferred until a real Codex dry-run actually reaches `waiting_review` with a clear final report.

## What Worked

- The runbook kept the task no-op/docs-only and DevOrchestrator-only.
- Placeholder backlog scope was rejected and replaced with a refined one-task backlog before approval.
- Batch approval and queue creation stayed explicit.
- Preflight and preview clearly showed the executable, prompt path, target path, and blockers.
- The review gate blocked completion before review.
- Report import and rejected review preserved evidence without completing queue/task state.
- Queue item was blocked after failure instead of completed.
- Workspace artifacts were not staged or committed.
- PersonalOS was not modified or commanded.

## Recommendation

Recommended TASK-DEVO-100: harden the real Codex launch path and failure handling before retrying real supervised execution.

Suggested scope:

- Add an explicit configured real Codex launcher path or shim guidance for Windows.
- Catch `OSError`/`PermissionError` around `subprocess.run` and record failure logs.
- Ensure worker/queue state transitions to failed/paused when launch fails before process start.
- Improve `flow-summary` next commands for failed/rejected review states.
- Update the real dry-run runbook with WindowsApps path guidance.

Delivery/commit safety design should come after a successful real Codex dry-run produces a real final report and reaches `waiting_review`.
