# Delivery Safety Design

Source/freshness: TASK-DEVO-104, after Codex worker reports/reviews, review-gated queue completion, and Codex launcher setup docs exist. This is design only; it does not implement commit/push automation.

## Purpose

Delivery safety is the layer after worker execution, report import, review, and queue completion.

Devo must not commit or push just because Codex exited successfully. A successful worker run means "Codex stopped and produced output"; it does not mean the diff is in scope, validation passed, review passed, or delivery is safe.

Delivery must be gated by scope checks, validation evidence, review evidence, branch/remote checks, and explicit safety approvals. The first implementation should be CLI-first, explicit, and boring: check and plan before any commit/push command exists.

## Current State

Relevant Devo capabilities already exist:

- Worker reports capture changed-file summaries, validation notes, safety warnings, blockers, and follow-ups.
- Worker reviews capture reviewer decisions and validation evidence.
- `devo project queue-complete-item` is review-aware for Codex-linked queue items.
- Git delivery concepts already exist through delivery checks and delivery reports for target repositories.
- `devo delivery check` now creates read-only delivery readiness summaries and optional JSON/Markdown artifacts under `workspace/projects/<project>/delivery/`.
- `devo delivery plan` and delivery approval commands now create read-only plan/approval artifacts from readiness checks without committing or pushing.
- `devo delivery report-prepare` now creates a pre-commit delivery report from an approved plan, re-checks current readiness, and proposes the commit message without staging, committing, or pushing.
- `devo delivery commit-preview` and guarded `devo delivery commit --confirm-commit` now provide the first CLI-only commit path. The command re-checks readiness, stages only eligible safe files, writes commit result artifacts, and still does not push.
- `devo delivery push-preview` and guarded `devo delivery push --confirm-push` now provide the first CLI-only push path after commit metadata exists. The command verifies remote/branch/commit containment, writes push result artifacts, and does not create commits.
- TASK-DEVO-110 dogfooded the full delivery lifecycle against an isolated temp repository and local bare remote. The flow is documented in `docs/dogfood/devo-delivery-dogfood-110.md`; no live DevOrchestrator delivery commit/push was run.
- TASK-DEVO-111 adds delivery operator polish and read-only Delivery dashboard visibility. Delivery reports label readiness as a report snapshot and mark it historical after commit or push. The UI shows delivery artifacts and copyable CLI commands only; commit/push execution remains CLI-only.
- TASK-DEVO-112 completed the first live DevOrchestrator docs-only delivery self-dogfood. DEL-0001 created commit `f0e8c0319c135f72973357776cd7c62d6cc8832b` and pushed it to `origin/main` through Devo delivery commands.
- TASK-DEVO-113 adds `devo delivery report-refresh` as the supported recovery path for retryable guarded commit failures. It refreshes the current readiness snapshot and can reopen a blocked report only when the previous commit failure is retryable, the linked plan and approval remain approved, no commit/push has already happened, and current readiness has no blockers.
- TASK-DEVO-114 adds `devo delivery commit-diagnostics` for read-only investigation of guarded commit failures. It surfaces Git executable/version, `.git` and `.git/index` state, `.git/index.lock` presence, ACL/attribute summaries when feasible, current changed-file state, retryable failure metadata, likely causes, and safe next actions before any retry.
- TASK-DEVO-115 documents the operating rule found by DEL-0001: run live guarded delivery commit/push from normal local PowerShell with `.\.venv\Scripts\devo.exe`; restricted Codex/sandbox contexts may fail to create `.git/index.lock`.
- Workspace artifacts under `workspace/` are intentionally runtime state and must not be committed.
- UI risky actions remain deferred; current UI should show status and copyable commands first.

The current blocker for real supervised Codex execution is launcher readiness: real execution should wait until `docs/runbooks/codex-launcher-setup.md` is complete and `devo worker codex doctor` reports a safe non-WindowsApps launcher. Delivery design can proceed while that is pending.

## Delivery Lifecycle

The intended lifecycle is:

```text
worker execution
-> waiting_review
-> report import
-> review/evidence
-> queue-complete-item
-> delivery readiness check
-> delivery plan
-> delivery approval
-> delivery report preparation
-> commit
-> push
-> delivery completion record
```

Queue completion is not the same as delivery. Queue completion says the queue item is accepted as done from a Devo workflow perspective. Delivery says the target repository diff is safe to commit and optionally push.

Delivery approval is separate from planning approval, batch approval, execution approval, run-plan approval, and review approval.

## Delivery Readiness Criteria

A delivery is ready only when checks show:

- target repo exists
- expected branch is checked out
- remote exists if push is requested
- Git status has been reviewed
- changed files are within allowed scope
- forbidden paths are not changed
- workspace artifacts are not staged
- secrets, `.env`, local settings, and private data are not staged
- generated artifacts are not staged unless explicitly approved
- validation evidence exists
- validation evidence is not failed
- worker review status is `reviewed_passed`
- queue item is completed or explicitly allowed for delivery before queue completion
- no unresolved blockers remain
- no PersonalOS changes exist unless the selected project is PersonalOS
- no backup, restore, scheduler, DB, migration, script, or appsettings changes exist unless explicitly approved

## Safety Stop Conditions

Stop delivery planning or execution if any of these are true:

- unexpected dirty files exist
- forbidden path changes exist
- secrets, `.env`, appsettings local files, local settings, or private user data are staged
- workspace artifacts are staged
- validation evidence is missing, failed, or ambiguous
- review evidence is missing, rejected, or needs changes
- branch or remote does not match the delivery plan
- generated files are unclear or unapproved
- user delivery approval is missing
- Codex output conflicts with the actual Git diff
- target project identity is ambiguous
- PersonalOS is dirty when the selected project is not PersonalOS
- backup/scheduler changes appear without explicit approval

When in doubt, stop and report the blocker instead of committing.

## Delivery Artifacts

Future delivery artifacts should live under:

```text
workspace/projects/<project>/delivery/
```

Suggested files:

- `delivery-index.json`
- `del-<id>.json`
- `del-<id>.md`
- `delivery-plan-<id>.json`
- `delivery-plan-<id>.md`
- `delivery-approval-<id>.json`
- `delivery-approval-<id>.md`
- `delivery-check-<id>.json`
- `delivery-report-<id>.json`
- `delivery-report-<id>.md`
- `delivery-commit-<id>.json`
- `delivery-commit-<id>.md`

### DeliveryPlan Fields

- `project`
- `delivery_id`
- `source_queue_id` optional
- `source_item_id` optional
- `source_worker_run_id` optional
- `source_review_id` optional
- `target_repo_path`
- `branch`
- `remote`
- `intended_commit_message`
- `changed_files`
- `staged_files`
- `allowed_scope`
- `forbidden_scope`
- `validation_evidence`
- `review_status`
- `readiness_status`: `draft`, `ready`, or `blocked`
- `blockers`
- `warnings`
- `approval_status`: `not_requested`, `requested`, `approved`, or `rejected`
- `created_at`
- `updated_at`
- `next_action`

TASK-DEVO-106 implements plan artifacts from written readiness checks. A blocked readiness check creates a blocked plan. A warnings-only check can create a planned plan that preserves warnings for approval review.

### DeliveryApproval Fields

TASK-DEVO-106 implements approval artifacts with:

- `project`
- `delivery_id`
- approval status: `not_requested`, `requested`, `approved`, or `rejected`
- request/review/approval/rejection timestamps
- reviewer and approver names
- decision note and approval notes
- readiness status
- blocker and warning counts
- changed and staged file counts
- validation evidence status
- review status
- next action

Delivery approval is separate from readiness. Blocked plans cannot be approved by default. Approval still does not commit or push.

### DeliveryCheck Fields

TASK-DEVO-105 implements the first check artifact with:

- `project`
- `delivery_id`
- optional queue/item/worker/review source ids
- `target_repo_path`
- `branch`
- `remote`
- `git_status_summary`
- changed, staged, unstaged, and untracked file lists
- forbidden changed/staged file lists
- workspace artifacts staged
- secret-risk files/signals
- validation evidence status
- review status
- queue item status
- readiness status: `ready`, `warnings`, or `blocked`
- blockers
- warnings
- next action
- timestamps

The check command is still read-only. It does not stage, unstage, validate, commit, push, complete queue items, run Codex, run target commands, or modify target repositories.

### DeliveryReport Fields

- `project`
- `delivery_id`
- `source_delivery_plan_id`
- source delivery, queue, queue item, worker run, and review ids when available
- `target_repo_path`
- `branch`
- `remote`
- `intended_commit_message`
- `proposed_commit_message`
- changed, staged, unstaged, and untracked file summaries
- `validation_summary`
- `review_summary`
- `safety_scan_summary`
- blocker and warning summaries
- `approval_status`
- `delivery_readiness_status`
- `commit_ready`
- `push_ready`
- `commit_hash` optional
- `pushed`: true or false
- `final_status`: `draft`, `ready`, `blocked`, or `superseded`
- recovery metadata: status, reason, operator note, history, refreshed timestamp, last commit failure category, last commit failure message, and retryable flag
- `created_at`
- `updated_at`
- `next_action`

TASK-DEVO-107 implements draft report preparation. Reports are stored as `delivery-report-<id>.json` and `.md`, are indexed in `delivery-index.json`, and intentionally stop before staging, committing, pushing, validation execution, target command execution, or Codex execution.

TASK-DEVO-113 adds report refresh/recovery metadata. A refresh without `--reopen` updates only the report's current readiness snapshot and recovery history, then reports whether reopening would be allowed. A refresh with `--reopen` can restore `final_status: ready` and `commit_ready: true` only for retryable guarded commit failures where current readiness passes and the linked delivery plan/approval remain approved. Reports that already have a commit hash or are already pushed are never reopened for commit.

### DeliveryCommit Fields

TASK-DEVO-108 implements commit result artifacts with:

- `project`
- `delivery_id`
- `status`: `committed`, `blocked`, or `failed`
- `commit_hash` optional
- `commit_message`
- `eligible_files`
- Git stdout/stderr and return code
- failure category and retryable flag for failed/blocked commits
- timestamps
- `next_action`

The commit result records what the guarded CLI commit did. It is not push evidence.

Known commit failure categories include `index_lock_permission_denied`, `index_lock_exists`, `git_commit_failed`, `no_eligible_files`, and `unknown`. Index lock failures are considered retryable after the operator checks that no Git process is active, no stale `.git/index.lock` remains, and permissions are understood. Devo keeps raw Git stderr in the commit artifact; it does not hide or rewrite the failure.

### DeliveryPush Fields

TASK-DEVO-109 implements push result artifacts with:

- `project`
- `delivery_id`
- `source_delivery_report_id`
- `source_commit_hash`
- `target_repo_path`
- `branch`
- `remote`
- `push_remote`
- `push_branch`
- `push_status`: `preview`, `blocked`, `pushed`, or `failed`
- `pushed`
- `pushed_at` optional
- Git push exit code/stdout/stderr summaries
- blockers and warnings
- timestamps
- `next_action`

The push result records a guarded CLI push. It is not validation evidence, queue completion evidence, or proof that external release/deployment tasks are done.

## Command Roadmap

Commands are added in layers:

```powershell
devo delivery check --project <project>
devo delivery check --project <project> --queue <queueId> --item <itemId> --write
devo delivery plan --project <project> --delivery <deliveryCheckId> --message "<commit message>"
devo delivery plan-list --project <project>
devo delivery show --project <project> --delivery <deliveryId>
devo delivery plan-show --project <project> --plan <deliveryId>
devo delivery approval-request --project <project> --plan <deliveryId> --note "<note>"
devo delivery approval-show --project <project> --plan <deliveryId>
devo delivery approval-list --project <project>
devo delivery approve --project <project> --plan <deliveryId> --approver "<name>" --note "<note>"
devo delivery reject --project <project> --plan <deliveryId> --reviewer "<name>" --note "<note>"
devo delivery report-prepare --project <project> --plan <deliveryId>
devo delivery report-list --project <project>
devo delivery report-show --project <project> --report <deliveryId>
devo delivery report-refresh --project <project> --report <deliveryId> --note "<reason>"
devo delivery report-refresh --project <project> --report <deliveryId> --reopen --note "<reason>"
devo delivery commit-message --project <project> --plan <deliveryId>
devo delivery commit-diagnostics --project <project> --report <deliveryId>
devo delivery commit-diagnostics --project <project> --report <deliveryId> --index-lock-probe --confirm-probe
devo delivery commit-preview --project <project> --report <deliveryId>
devo delivery commit --project <project> --report <deliveryId> --confirm-commit
devo delivery commit-show --project <project> --delivery <deliveryId>
devo delivery push-preview --project <project> --report <deliveryId>
devo delivery push --project <project> --report <deliveryId> --confirm-push
devo delivery push-show --project <project> --delivery <deliveryId>
```

The readiness, plan, approval, report-preparation, report-refresh, commit-message, commit-diagnostics, commit-preview, guarded commit, push-preview, and guarded push commands exist now. Preview and default diagnostics commands are read-only. `report-refresh` does not stage, unstage, commit, push, validate, run Codex, or modify target repo files; with `--reopen` it only changes Devo's delivery report state when reopening is safe. `commit-diagnostics --index-lock-probe --confirm-probe` is an explicit diagnostic probe that attempts to create and immediately remove `.git/index.lock` and should be used only after the operator confirms no Git process is active. `commit` is CLI-only and requires `--confirm-commit`; before staging it runs an automatic index-lock preflight and records a retryable blocked result if the current process cannot create/remove `.git/index.lock`. `push` is CLI-only and requires `--confirm-push`. UI commit/push buttons remain deferred.

## Recovery After Guarded Commit Failure

If `devo delivery commit --confirm-commit` fails, Devo writes `delivery-commit-<id>.json` and marks the delivery report blocked. The guarded commit path checks `.git/index.lock` before staging; if the lock exists, cannot be created, or cannot be removed after the probe, Devo blocks before `git add`, classifies the result as `index_lock_exists`, `index_lock_permission_denied`, or `index_lock_probe_failed`, and keeps the retry path explicit. Retryable failures such as `.git/index.lock` permission denial or stale lock errors include a recovery next action.

The safe recovery sequence is:

```powershell
devo delivery report-show --project <project> --report <deliveryId>
devo delivery commit-preview --project <project> --report <deliveryId>
devo delivery commit-diagnostics --project <project> --report <deliveryId>
devo delivery report-refresh --project <project> --report <deliveryId> --note "<diagnosis>"
devo delivery report-refresh --project <project> --report <deliveryId> --reopen --note "<diagnosis>"
devo delivery commit-preview --project <project> --report <deliveryId>
```

Only after diagnostics point to a resolved OS/Git issue and the refreshed preview is clean should an operator run the guarded commit again. Retryable means Devo can safely preserve recovery state; it does not mean immediate retry is safe. Do not manually bypass Devo delivery after a guarded failure unless the user explicitly approves that exceptional path.

## Secret-Risk Classification

Delivery readiness treats secret-bearing paths and high-confidence credential values as blockers. Examples include `.env`, `.env.*`, private key/certificate files, appsettings-like files, private-key block markers, real-looking API keys, tokens, passwords, and connection strings with passwords.

Documentation-only safety language is different. `README.md` and `docs/*.md` may mention `.env`, API keys, tokens, placeholders, redacted values, dummy values, or secret-handling rules as warnings rather than blockers. These docs are still blocked if they contain high-confidence secret values, so README/docs are not blanket-allowlisted.

## Approval Separation

Delivery needs distinct approvals:

- Planning approval: approves project intent.
- Batch approval: approves a scoped group of planned work.
- Execution approval: approves running a worker for one item.
- Run-plan approval: approves the exact worker run plan/launcher/prompt shape.
- Review approval: accepts worker output and validation evidence.
- Delivery approval: approves committing and optionally pushing a specific diff.
- Safety override approval: records exceptional trusted approval when a safety gate blocks.

These approvals are separate because each one answers a different question. A batch can be a good idea while a diff is unsafe. A worker can finish successfully while validation is missing. A review can accept the result while push should wait for branch/remote review.

## Commit And Push Policy

Initial policy:

- No automatic commit/push.
- Commit only after delivery readiness passes, delivery plan/report approval is present, a report is ready, and `--confirm-commit` is supplied.
- Push only after guarded commit metadata exists, branch and remote are verified, the commit is contained in the current branch, and `--confirm-push` is supplied.
- Commit messages should reference the task, batch, queue item, worker run, or review when possible.
- Existing user preference for approved commit/push can be supported later only under strict delivery checks and standing rules.
- Generated workspace artifacts must never be committed.

Commit/push automation should not be connected directly to worker success. It should be connected to delivery readiness, approval, and explicit confirmation.

## Live Delivery Operating Context

DEL-0001 showed that Devo's delivery logic can be correct while the execution context cannot create `.git/index.lock`. Guarded commit failed from the restricted Codex/sandbox context with:

```text
fatal: Unable to create 'E:/DevOrchestrator/.git/index.lock': Permission denied
```

The same delivery later succeeded from normal local PowerShell as `MS\manas` using:

```powershell
.\.venv\Scripts\devo.exe
```

Operational rule:

- Run live Devo delivery commit/push from normal local PowerShell as the normal Windows user.
- Use the explicit `.\.venv\Scripts\devo.exe` prefix for live delivery dogfood.
- Do not run live guarded delivery commit/push from restricted Codex/sandbox context unless `commit-diagnostics --index-lock-probe --confirm-probe` proves that context can create and remove `.git/index.lock`.
- Do not bypass Devo delivery with manual `git add`, `git commit`, or `git push` during dogfood unless explicitly approved.
- If index-lock permission failure appears, diagnose/fix the OS/security/context issue first, then run `report-refresh --reopen`, `commit-preview`, guarded commit, push-preview, and guarded push.
- If guarded commit preflight fails, no target files should have been staged; inspect the commit artifact and diagnostics before retrying.

## UI Roadmap

Future UI can show delivery visibility before actions:

- Delivery page
- delivery readiness summary
- changed-file scope summary
- blockers and warnings
- validation and review evidence summary
- copyable CLI commands first

Do not add commit/push buttons until the delivery safety model is mature. A read-only Delivery page should come before controlled delivery actions. TASK-DEVO-108 and TASK-DEVO-109 add only CLI commit/push; the UI may show copyable commands plus commit/push result metadata, but not execute commit or push.

TASK-DEVO-111 adds that read-only Delivery page. It does not add commit, push, stage, unstage, validation, restore, scheduler, Codex, or target command execution controls.

## Rollout Plan

Recommended next tasks:

1. TASK-DEVO-105: Delivery readiness data model and check command - completed
2. TASK-DEVO-106: Delivery plan and approval workflow - completed
3. TASK-DEVO-107: Delivery report and commit message preparation - completed
4. TASK-DEVO-108: Controlled commit command with `--confirm-commit` - completed
5. TASK-DEVO-109: Controlled push command with `--confirm-push` - completed
6. TASK-DEVO-110: End-to-end guarded delivery dogfood on isolated temp repo - completed
7. TASK-DEVO-111: Delivery operator polish and read-only Delivery UI - completed
8. TASK-DEVO-113: Delivery report recovery and refresh after retryable commit failures - completed
9. TASK-DEVO-114: Delivery commit diagnostics and index.lock failure hardening - completed
10. TASK-DEVO-115: Close live delivery dogfood and document normal-PowerShell delivery operating rule - completed

## Deferred Scope

Explicitly deferred:

- automatic commit/push
- UI commit/push buttons
- delivery without review evidence
- delivery without validation evidence
- multiple parallel deliveries
- public SaaS or multi-user delivery workflows
- any PersonalOS delivery unless selected and approved
