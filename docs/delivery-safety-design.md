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
-> commit
-> push
-> delivery report
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

- `delivery_id`
- `commit_hash` optional
- `pushed`: true or false
- `push_remote` optional
- `push_branch` optional
- `validation_summary`
- `safety_scan_summary`
- `final_status`
- `created_at`

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
devo delivery commit --project <project> --delivery <deliveryId> --confirm-commit
devo delivery push --project <project> --delivery <deliveryId> --confirm-push
devo delivery report --project <project> --delivery <deliveryId>
```

The readiness, plan, and approval commands exist now and are workspace-artifact only. Commit and push remain future commands and must require explicit confirmation flags. UI commit/push buttons remain deferred.

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
- Commit only after delivery readiness passes.
- Push only after branch and remote are verified.
- Commit messages should reference the task, batch, queue item, worker run, or review when possible.
- Existing user preference for approved commit/push can be supported later only under strict delivery checks and standing rules.
- Generated workspace artifacts must never be committed.

Commit/push automation should not be connected directly to worker success. It should be connected to delivery readiness, approval, and explicit confirmation.

## UI Roadmap

Future UI can show delivery visibility before actions:

- Delivery page
- delivery readiness summary
- changed-file scope summary
- blockers and warnings
- validation and review evidence summary
- copyable CLI commands first

Do not add commit/push buttons until the delivery safety model is mature. A read-only Delivery page should come before controlled delivery actions.

## Rollout Plan

Recommended next tasks:

1. TASK-DEVO-105: Delivery readiness data model and check command - completed
2. TASK-DEVO-106: Delivery plan and approval workflow - completed
3. TASK-DEVO-107: Delivery report and commit message preparation
4. TASK-DEVO-108: Controlled commit command with `--confirm-commit`
5. TASK-DEVO-109: Controlled push command with `--confirm-push`
6. TASK-DEVO-110: Delivery UI visibility
7. TASK-DEVO-111: Delivery dogfood on docs-only change

## Deferred Scope

Explicitly deferred:

- automatic commit/push
- UI commit/push buttons
- delivery without review evidence
- delivery without validation evidence
- multiple parallel deliveries
- public SaaS or multi-user delivery workflows
- any PersonalOS delivery unless selected and approved
