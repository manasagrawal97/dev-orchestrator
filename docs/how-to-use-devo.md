# How To Use Devo

Devo is a local control plane for AI-assisted development. It keeps project memory, workflow state, task state, policy decisions, approvals, validation metadata, Git delivery evidence, reports, and recovery notes in one place.

Devo does not implement code by itself. It does not call AI by itself. It does not bypass Codex, OpenAI, GitHub, operating system, or user approval policy.

## Mental Model

- User and ChatGPT decide direction, risk, and the next safe step.
- Codex or another coding agent implements bounded changes.
- Devo records the control plane: project memory, workflow, task state, policy, approval, validation, Git delivery, reports, and recovery.
- Source code is protected by GitHub.
- Devo runtime artifacts live in `workspace/` and should not be committed.
- Devo workspace/context is protected by scheduled Google Drive backup.

Longer term, Devo should work like a local software-development company operating system: the user discusses a project with ChatGPT, pastes the final brief into Devo, Devo creates blueprint/backlog/tasks, the user approves a batch, Codex executes approved tasks, and Devo tracks progress, validation, commits, reports, and resume points.

For the plain-language product model, read:

- [Devo vision](devo-vision.md)
- [Company-model vision](devo-company-model.md)
- [Codex worker adapter design](codex-worker-adapter-design.md)
- [Delivery safety design](delivery-safety-design.md)
- [Codex launcher setup runbook](runbooks/codex-launcher-setup.md)
- [Real Codex supervised dry-run runbook](runbooks/real-codex-supervised-dry-run.md)
- [Remaining roadmap](remaining-roadmap.md)
- [Current capabilities](current-capabilities.md)
- [Agent workflow](agent-workflow.md)
- [Usability roadmap](usability-roadmap.md)
- [UI/API architecture](ui-architecture.md)
- [UI MVP specification](ui-mvp-spec.md)
- [PersonalOS operating model](personal-os-operating-model.md)

## Typical Lifecycle

1. Register the project.
2. Scan the project.
3. Generate and import discovery context.
4. Review and import context review.
5. Approve context.
6. Create a run.
7. Ask workflow for next/status.
8. Generate an agent prompt or perform a manual-assisted step.
9. Record implementation evidence.
10. Run validation or dry-run validation.
11. Review, audit, and close the task.
12. Run Git delivery-check/report.
13. Refresh project context.
14. Write a handoff report.
15. Close the run when all tasks are resolved.

## Practical PersonalOS Flow

For current PersonalOS maintenance, use the simpler practical flow from [PersonalOS operating model](personal-os-operating-model.md):

1. user gives a goal
2. Codex/Devo creates a work package in the right lane
3. Devo generates a lane-aware scope template
4. Codex fills and imports exact scope into the work package
5. user approves the approval bundle when the scope is acceptable
6. Codex implements within scope
7. Codex validates with the registered command, commits, pushes, marks the work package complete, and gives a short final summary

The older two-stop flow, separate source approval followed by separate build approval, remains useful when a bundle is not available or the scope/risk changes.

## Project Brief And Blueprint

The first planning pipeline artifacts are Project Brief, Blueprint, Backlog, Tasks, and planning Batches.

```powershell
devo project brief-create --project MyProject --title "My Project" --file E:\path\to\brief.md
devo project brief-show --project MyProject
devo project brief-approve --project MyProject
devo project blueprint-create --project MyProject
devo project blueprint-show --project MyProject
devo project blueprint-approve --project MyProject
```

The brief is the intake artifact: the final project summary distilled from discussion with ChatGPT or another advisor. The blueprint is the high-level deterministic plan derived from the brief. Both live under `workspace/projects/<project>/planning/`.

This flow is workspace-only. It does not create execution queues, does not call AI, does not call Codex CLI, and does not modify the target project.

## Backlog And Tasks

After a blueprint exists, create the starter backlog:

```powershell
devo project backlog-create --project MyProject
devo project backlog-show --project MyProject
devo project task-list --project MyProject
devo project task-show --project MyProject --task T001
devo project backlog-approve --project MyProject
```

The backlog is the structured task plan derived from the blueprint. TASK-DEVO-075 creates deterministic placeholder tasks from blueprint milestones/epics. TASK-DEVO-076 adds a Codex/manual prompt and safe import path for refined backlog JSON.

This remains workspace-only. It does not call AI, does not call Codex CLI, does not approve implementation, and does not modify the target project.

## Backlog Refinement Handoff

The starter backlog is intentionally deterministic. To refine it into better implementation-ready tasks, generate a planning handoff prompt:

```powershell
devo project backlog-prompt --project MyProject
```

This writes `workspace/projects/<project>/planning/backlog-refinement-prompt.md`. Paste that prompt into Codex/manual planning. The prompt includes the brief, blueprint, starter backlog, task schema, lane guidance, risk guidance, output JSON example, and explicit planning-only safety rules.

After Codex/manual planning produces refined backlog JSON:

```powershell
devo project backlog-validate --project MyProject --file E:\path\to\refined-backlog.json
devo project backlog-import --project MyProject --file E:\path\to\refined-backlog.json
```

Import validates required fields, duplicate task IDs, statuses, lanes, and risk levels, then writes the backlog as `draft` for safety. It does not approve implementation, create an execution queue, call Codex, call AI APIs, or modify the target project.

## Planning Batches

A planning Batch is a user-reviewable group of backlog tasks. Batch approval records planning intent only; it does not approve source edits, create an execution queue, call Codex, run validation, commit, push, or modify the target project.

Create a batch from explicit task IDs:

```powershell
devo project batch-create --project MyProject --title "First batch" --tasks T001,T002
```

Ask Devo for a deterministic suggestion:

```powershell
devo project batch-suggest --project MyProject
devo project batch-suggest --project MyProject --write
```

Inspect and approve the planning batch:

```powershell
devo project batch-list --project MyProject
devo project batch-show --project MyProject --batch B001
devo project batch-approval-request --project MyProject --batch B001 --note "Ready for planning review."
devo project batch-approval-show --project MyProject --batch B001
devo project batch-approval-list --project MyProject
devo project batch-review --project MyProject --batch B001 --note "Looks scoped."
devo project batch-review --project MyProject --batch B001 --note "Needs a smaller split." --needs-changes
devo project batch-approve --project MyProject --batch B001 --note "Approved for queue creation."
devo project batch-reject --project MyProject --batch B001 --note "Needs a safer split."
```

Batch artifacts live under `workspace/projects/<project>/planning/batches/` as `batch-<batch_id>.json`, `batch-<batch_id>.md`, and `batch-index.json`. Approval artifacts live under `workspace/projects/<project>/planning/batches/approvals/` as `batch-<batch_id>-approval.json` and `.md`. Approval artifacts summarize task scope, risks, lanes, dependencies, validation expectations, decision notes, and the next suggested command. Suggestions prefer selectable backlog tasks whose dependencies are completed or already included, with lower-risk tasks first.

Batch approval is planning approval only. It does not create a queue, run Codex, execute target commands, run validation/build/test/app commands, commit, push, restore/delete backups, modify schedulers, edit target files, or call model APIs. After approval, queue creation is still explicit:

```powershell
devo project queue-create --project MyProject --batch B001
```

## Planning Progress

Progress is derived from existing planning artifacts. It is deterministic and count-based; it does not use weighted scoring, execution queue state, Codex execution state, or AI/API calls.

```powershell
devo project progress --project MyProject
devo project progress --project MyProject --json
```

The summary includes Project Brief/Blueprint/Backlog status, task counts, active/completed/ready/approved/draft/blocked counts, project completion percent, backlog readiness percent, blocked percent, batch completion percent, latest batch, milestone progress, epic progress, warnings, and the next planning action.

For a real end-to-end example of this planning pipeline on DevOrchestrator itself, see `docs/dogfood/devo-pipeline-dogfood-085.md`. That report shows the exact brief -> blueprint -> backlog -> batch -> approval -> queue -> handoff -> progress command sequence, plus the operator-friction issues found during dogfood.

For the guarded delivery path, see `docs/dogfood/devo-delivery-dogfood-110.md`. That report dogfoods delivery check -> plan -> approval -> report -> commit-preview -> guarded commit -> push-preview -> guarded push against an isolated temporary repository and local bare remote. It proves the CLI-only commit/push path without running delivery commit or push against the live DevOrchestrator repository.

## Execution Queue State

Execution queues are deterministic state tracking artifacts created from approved planning batches. They do not run Codex, run validation, run Git commands, commit, push, or modify target project source.

```powershell
devo project queue-create --project MyProject --batch B001
devo project queue-list --project MyProject
devo project queue-show --project MyProject --queue Q001
devo project queue-start --project MyProject --queue Q001
devo project queue-next --project MyProject --queue Q001
```

Use queue state commands to track manual/Codex-adjacent progress:

```powershell
devo project queue-complete-item --project MyProject --queue Q001 --item QI001 --note "Completed manually."
devo project queue-block-item --project MyProject --queue Q001 --item QI002 --note "Needs review."
devo project queue-pause --project MyProject --queue Q001 --reason usage_limit --note "Resume when usage resets."
devo project queue-resume --project MyProject --queue Q001
```

Queue artifacts live under `workspace/projects/<project>/planning/queues/` as `queue-<queue_id>.json`, `queue-<queue_id>.md`, and `queue-index.json`. Completing or blocking a queue item can update the corresponding Devo backlog task status so progress reflects queue state, but it still does not edit the target repository.

## Codex Handoff Prompts

Codex handoff prompts are generated workspace artifacts that package one queue item, one backlog task, or one approved batch into a Codex-ready operator prompt. They are a safe manual bridge from Devo planning to Codex execution.

```powershell
devo project handoff-next --project MyProject --queue Q001
devo project handoff-task --project MyProject --task T001
devo project handoff-batch --project MyProject --batch B001
devo project handoff-list --project MyProject
devo project handoff-show --project MyProject --handoff H001
devo project handoff-mark-used --project MyProject --handoff H001
```

Handoff artifacts live under `workspace/projects/<project>/planning/handoffs/` as `handoff-<handoff_id>.json`, `handoff-<handoff_id>.md`, and `handoff-index.json`. The generated prompt includes project path, source queue/batch/task details, lane, risk, dependencies, acceptance criteria, validation expectations, allowed/forbidden scope, safety boundaries, files not to stage, and final report expectations.

Devo still does not run Codex, call AI APIs, execute target repo commands, approve implementation, run validation, commit, push, or modify target project source. The user manually pastes the generated prompt into Codex and must request explicit trusted approval when a safety gate blocks work.

Prepare a supervised queue worker for exactly one current/pending queue item:

```powershell
devo worker codex prepare-next --project MyProject --queue Q001
devo worker codex queue-status --project MyProject --queue Q001
devo worker codex queue-status --project MyProject --queue Q001 --item QI001
devo worker codex flow-summary --project MyProject --queue Q001
```

`prepare-next` creates or reuses the queue handoff, creates a linked worker run, creates a run plan, and runs preflight. It stops before approval and execution. `queue-status` shows the linked worker/run-plan/execution/report/review state and the next safe CLI command without mutating anything. If the queue is already completed, it defaults to the most recently completed queue item so evidence is still visible. Use `--item` to inspect a specific item. `flow-summary` is the shorter read-only operator view for queue, handoff, worker, plan, report, review, completion readiness, and the next 1-3 commands.

Track a manual Codex worker attempt from an existing handoff:

```powershell
devo worker codex run-create --project MyProject --handoff H001
devo worker codex run-list --project MyProject
devo worker codex run-show --project MyProject --run WR001
devo worker codex run-status --project MyProject --run WR001 --status waiting_review --note "Manual session needs review."
devo worker codex run-mark-used --project MyProject --run WR001
```

Worker run artifacts live under `workspace/projects/<project>/workers/codex/` as `worker-run-<id>.json`, `worker-run-<id>.md`, and `worker-run-index.json`. They are tracking records only. They do not run Codex, call AI APIs, execute target commands, prove implementation complete, complete queue items, validate, commit, push, or modify target source.

Before any supervised worker execution, preflight the tracked worker run or write a run-plan preview:

```powershell
devo worker codex doctor --project MyProject
devo worker codex doctor --project MyProject --codex-wrapper E:\tools\codex-wrapper.cmd
devo worker codex wrapper-template --path E:\DevOrchestrator\workspace\tmp\codex-wrapper.cmd --type cmd
devo worker codex preflight --project MyProject --run WR001
devo worker codex preflight --project MyProject --run WR001 --codex-path E:\tools\fake-codex.cmd
devo worker codex preflight --project MyProject --run WR001 --codex-wrapper E:\tools\codex-wrapper.cmd
devo worker codex run-plan --project MyProject --run WR001
devo worker codex run-plan --project MyProject --run WR001 --codex-path E:\tools\fake-codex.cmd
devo worker codex run-plan --project MyProject --run WR001 --codex-wrapper E:\tools\codex-wrapper.cmd
devo worker codex run-plan-list --project MyProject
devo worker codex run-plan-show --project MyProject --plan RP001
devo worker codex run-plan-approve --project MyProject --plan RP001 --note "Planning reviewed."
```

Run-plan artifacts live under `workspace/projects/<project>/workers/codex/run-plans/`. Preflight checks the linked handoff/prompt, target repo path, worker run state, linked metadata, and optional Codex launcher readiness using safe detection only. `devo worker codex doctor` diagnoses the selected launcher without running Codex, including whether PATH resolves to a WindowsApps app execution alias, likely PATH/npm/global candidates, WSL availability, and exact `--codex-path`, `--codex-wrapper`, and `--codex-wsl` examples. Normal use can rely on PATH only when doctor/preflight do not warn; dogfood and fake-executable testing can pass `--codex-path`; operators can pass `--codex-wrapper` for a local wrapper that points at a real non-WindowsApps Codex executable. `wrapper-template` creates a local `.cmd` template and refuses committed source paths. The generated run-plan command is a preview string until the explicit guarded execute path is used. Run-plan approval is planning approval only; execution still requires `execute --confirm-execute` and does not authorize validation, delivery, queue completion, or target repository changes.

Execute one supervised Codex CLI run only after previewing and approving the run plan:

```powershell
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001 --codex-path E:\tools\fake-codex.cmd
devo worker codex execute-preview --project MyProject --run WR001 --plan RP001 --codex-wrapper E:\tools\codex-wrapper.cmd
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute --codex-path E:\tools\fake-codex.cmd
devo worker codex execute --project MyProject --run WR001 --plan RP001 --confirm-execute --codex-wrapper E:\tools\codex-wrapper.cmd
devo worker codex execute-log --project MyProject --run WR001
```

`execute` refuses to run without `--confirm-execute`, an approved run plan, passed/warnings preflight, existing prompt and target paths, and a supported launcher from the run plan, PATH, `--codex-path`, or `--codex-wrapper`. It uses explicit subprocess argument lists without `shell=True`; `.cmd`/`.bat` wrappers use `cmd.exe /d /c <wrapper>` explicitly. It captures logs under `workspace/projects/<project>/workers/codex/logs/` and updates the worker run to `waiting_review`, `failed`, `paused_usage_limit`, or `blocked_needs_approval`. When linked to a queue item, it also moves that item/queue to review, failure, or pause state without completing anything. It does not run validation, complete queue/task state, commit, push, or treat Codex output as proof. If process creation fails before Codex produces output, Devo catches `PermissionError`, `FileNotFoundError`, and other launch-time `OSError` failures, writes a clear log, marks the worker `failed`, and pauses the linked queue as `paused_failure`. After execution, review logs and use `report-template`/`report-import` before any queue or delivery update.

On this machine, TASK-DEVO-101 found no launchable Codex path outside the blocked WindowsApps package path. TASK-DEVO-102 added wrapper support, and TASK-DEVO-103 added `docs/runbooks/codex-launcher-setup.md`. The real retry should still wait until that setup checklist is complete and `devo worker codex doctor --codex-path <path>` or `devo worker codex doctor --codex-wrapper <path>` reports no blockers. `--codex-wsl <distributionName>` is currently preview/planning only; guarded WSL execution is deferred.

After the user runs Codex manually, create and import a structured worker report:

```powershell
devo worker codex report-template --project MyProject --run WR001
devo worker codex report-validate --project MyProject --run WR001 --file report-WR001.json
devo worker codex report-import --project MyProject --run WR001 --file report-WR001.json
devo worker codex report-show --project MyProject --run WR001
devo worker codex report-list --project MyProject
```

Imported reports live under `workspace/projects/<project>/workers/codex/reports/` as JSON and Markdown. They record what the worker claimed happened: status, summary, changed files, validation attempted/results, tests, commands, optional commit hash, safety warnings, blockers, follow-ups, and notes. Importing a report does not execute Codex, call AI APIs, run target commands, trust the report as proof, complete queue/tasks, run validation, commit, push, or modify target source. A completed worker report moves the worker run into a review-oriented state so the user can verify evidence before any queue or delivery update.

Record review and validation evidence after worker execution/report import:

```powershell
devo worker codex review-template --project MyProject --run WR001
devo worker codex review-attach-evidence --project MyProject --run WR001 --status provided --summary "<validation summary>"
devo worker codex review-record --project MyProject --run WR001 --status reviewed_passed --reviewer "<name>" --note "<note>"
devo worker codex review-show --project MyProject --run WR001
devo worker codex review-list --project MyProject
```

Review artifacts live under `workspace/projects/<project>/workers/codex/reviews/`. They are the bridge between worker output and queue completion: checklist notes, validation evidence, changed-file review, safety review, follow-up items, reviewer decision, and next action. They do not run validation, complete queue/task state, commit, push, or modify target source.

Queue completion is now review-aware for Codex-linked or waiting-review items. `devo project queue-complete-item` refuses completion by default when the linked worker review is missing, `reviewed_needs_changes`, `rejected`, or has failed validation evidence. A `reviewed_passed` review allows the explicit completion command. `--confirm-without-review` is an emergency/manual override only; it requires a note and records a warning.

The fake-worker dogfood report for this path is `docs/dogfood/devo-supervised-worker-dogfood-096.md`.

Supervised Codex CLI worker execution is intentionally single-run and queue-linked only when explicitly prepared. Read `docs/codex-worker-adapter-design.md` before worker adapter work. Manual handoff remains supported, and every worker mode must preserve explicit execution approval, queue pause/resume state, validation/review evidence, and delivery safety checks.

Before the first real supervised Codex launch, read `docs/runbooks/codex-launcher-setup.md` and `docs/runbooks/real-codex-supervised-dry-run.md`. The first real run should target DevOrchestrator, use no-op/docs-only scope, and prove the approval/preview/execution/report/review gate. It should not touch PersonalOS, run target commands, trust validation automatically, commit, push, or complete queue/task state without explicit review.

The TASK-DEVO-099 first real launch attempt is documented in `docs/dogfood/devo-real-codex-dry-run-099.md`. It reached the approved guarded launch step but Windows denied `CreateProcess` for the detected WindowsApps Codex executable path before Codex produced output. TASK-DEVO-100 hardened launch diagnostics and failure handling. TASK-DEVO-101 is documented in `docs/dogfood/devo-real-codex-dry-run-retry-101.md`; it stopped before execution because no safe non-WindowsApps launcher was available. TASK-DEVO-102 adds the wrapper/template path for that missing launcher setup, and TASK-DEVO-103 documents the operator setup checklist; neither task retries real Codex.

Delivery after worker review is a separate safety layer. Read `docs/delivery-safety-design.md` before adding any commit/push workflow. Queue completion is not delivery. Current delivery readiness checks inspect scope, validation evidence, review evidence, branch/remote state, staged files, forbidden paths, and secret-risk signals before any future delivery plan, approval, commit, or push.

Source/freshness: this diagram reflects the current low-risk work-package flow as of TASK-DEVO-053A. Update it when work packages add new required phases or when bundle semantics change.

```mermaid
flowchart LR
    Start["work start"] --> Template["scope-template"]
    Template --> Scope["fill and import scope"]
    Scope --> Bundle["request approval bundle"]
    Bundle --> Approve["bundle approved"]
    Approve --> Implement["implement approved scope"]
    Implement --> Validate["registered validation"]
    Validate --> Commit["commit and push"]
    Commit --> Complete["work complete"]
    Complete --> History["work list/history/activity"]
```

## Project Setup

```powershell
devo project add --name <name> --path <path>
devo project onboard --project <name>
devo project scan <name>
devo project context-status <name>
devo project settings-show --project <name>
devo project settings-set --project <name> --default-lane <lane> --default-validation-command <commandId> --default-branch <branch>
```

After scanning, generate/import ProjectContextDiscoveryAgent output, generate/import ProjectContextReviewerAgent output, then approve context:

```powershell
devo agent prompt ProjectContextDiscoveryAgent --project <name>
devo agent import-output ProjectContextDiscoveryAgent --project <name> --file <discoveryOutputFile>
devo agent prompt ProjectContextReviewerAgent --project <name>
devo agent import-output ProjectContextReviewerAgent --project <name> --file <reviewOutputFile>
devo project approve-context <name>
```

## Daily Start

```powershell
devo doctor
devo doctor --project <name>
devo current
devo use --project <name>
devo use --project <name> --run <runId>
devo report project --project <name>
devo report handoff --project <name>
devo workflow resume --project <name>  # planned future command, not implemented yet
```

`devo project onboard --project <name>` is the compact setup checklist. It is read-only by default and reports registration, project path, scan, context approval, validation registry, project settings, doctor status, and the next setup command. Use `--suggest-settings` to print a suggested `settings-set` command without writing it. Use `--write-suggestions` to write `workspace/projects/<project>/reports/onboarding-report.md`; this still does not modify the target project.

`devo project settings-set` stores project workflow defaults in Devo workspace metadata, not in the target repo. Useful defaults include `default_lane`, `default_validation_command`, `default_full_test_command`, `default_branch`, automatic scope-template behavior, delivery mode, and notes.

Examples:

```powershell
devo project settings-set --project DevOrchestrator --default-lane devo-internal-source --default-branch main
devo project settings-set --project PersonalOS --default-lane low-risk-ui-maintenance --default-validation-command dotnet-build-personalos --default-branch master
```

`devo doctor` checks Devo-level health. `devo doctor --project <name>` also checks the registered project path, Git status, project settings, validation registry, recent work packages, latest validation, generated visuals, and backup health where available. Doctor is read-only: it does not run build/test, backup/restore, app commands, migrations, scheduler updates, or external APIs.

`devo use` saves the current project and optional run in `workspace/current.json`; `devo current` shows what is selected and whether the project/run still exists. Common commands such as `devo work resume`, `devo work status`, `devo work next`, `devo work new`, `devo project activity`, `devo project onboard`, and `devo visual work-package` can use saved context when `--project` or `--run` are omitted.

For project setup, use `devo project onboard --project <name>` before `work new`. Until `devo workflow resume` exists, use doctor plus project/handoff reports and `devo workflow status` for any known active run.

## Run Work

```powershell
devo run create --project <name> --goal "<goal>"
devo workflow status --project <name> --run <runId>
devo workflow next --project <name> --run <runId>
devo workflow batch --project <name> --run <runId>
```

When Devo asks for agent output, generate the prompt, produce the output with ChatGPT/Codex/manual assistance, then import it:

```powershell
devo agent prompt <AgentName> --project <name> --run <runId>
devo agent import-output <AgentName> --project <name> --run <runId> --file <agentOutputFile>
```

Implementation is performed outside Devo by a human or coding agent. Record completion evidence after the work is done:

```powershell
devo implementation report --project <name> --run <runId> --task <taskId> --file <completionReportFile>
```

## Work Packages

For small bounded batches, use the work-package flow instead of hand-assembling a run and approvals:

```powershell
devo work lanes
devo work lane-show --lane low-risk-ui-maintenance
devo work new --project <name> --goal "<goal>"
devo work new --project <name> --lane low-risk-ui-maintenance --goal "<goal>"
devo work start --project <name> --lane low-risk-ui-maintenance --goal "<goal>"
devo work resume --project <name> --run <runId>
devo work scope-template --project <name> --run <runId>
devo work import-scope --project <name> --run <runId> --file <scopeMarkdownFile>
devo work status --project <name> --run <runId>
devo work next --project <name> --run <runId>
devo work prompt --project <name> --run <runId> --phase implement
devo work request-approval-bundle --project <name> --run <runId> --task T001
devo approval bundle-status --project <name> --run <runId> --bundle <bundleId>
devo approval bundle-approve --project <name> --run <runId> --bundle <bundleId> --by Manas --note "Approved scope"
devo work complete --project <name> --run <runId> --commit <commitHash> --message "<summary>"
devo work list --project <name> --limit 10
devo work history --project <name> --limit 10
devo project activity --project <name> --limit 10
devo visual work-package --project <name> --run <runId>
devo visual project-activity --project <name> --limit 10
devo work scope-example --lane low-risk-ui-maintenance
```

After selecting context, the same flow can be shorter:

```powershell
devo use --project DevOrchestrator
devo work new --goal "Add project settings command"
devo use --project DevOrchestrator --run <runId>
devo work resume
devo work status
devo work next
devo project activity
devo doctor
```

Use `devo work new` for normal new work. It creates a run, starts the work package, generates `scope-template.md`, and prints the resume command. When `--lane` is omitted, it uses the project's configured `default_lane`; if no default lane exists, Devo asks for `--lane` instead of guessing. Use `--no-template` to skip template generation, or `--template` to force it when project settings disable automatic templates. Use `devo work start` plus `devo work scope-template` only when you need the lower-level steps separately. The filled scope Markdown must include selected items, exact files, allowed changes, forbidden changes, validation command, and delivery plan. Work-package artifacts stay under `workspace/`; target project files are changed only later by Codex after approval.

Built-in lanes:

- `docs-only`: documentation and Mermaid changes only; default validation is `git diff --check` and no build by default.
- `low-risk-ui-maintenance`: Razor UI help text, empty states, mechanical warning fixes, and display-only prompts using already-loaded data.
- `warning-cleanup`: exact mechanical warning/analyzer cleanup, usually build-verified.
- `small-bugfix`: one small focused fix with minimal tests when existing.
- `small-feature`: one small approved feature or requirement inside approved files/modules.
- `test-only`: tests and test helpers, without production source unless explicitly scoped.
- `backup-maintenance`: Devo backup/recovery code, scripts, docs, and temp-directory tests; no real backup/restore by default.
- `devo-internal-source`: DevOrchestrator source, tests, and docs; no PersonalOS changes or workspace artifacts in commits.

Lanes describe the normal safe shape for a package. They do not bypass approval bundles, child approval records, validation command policy checks, or explicit stop conditions.

`devo work resume` is the preferred continuation command after a work package exists. It combines current state, lane rules, imported scope, approval bundle status, latest validation status, Git delivery evidence, exact next commands, Codex operator instructions, stop conditions, and final report expectations. It is read-only.

`devo work next` reads the package state and shows a smaller next action, required command, stop conditions, and whether user approval is needed. In draft state it suggests `devo work scope-template`. `devo work prompt --phase <phase>` writes a phase-specific Codex operator prompt under the work-package artifacts folder. Supported phases are `scope`, `implement`, `validate`, `deliver`, and `complete`.

The final low-risk package flow is:

```text
work new -> fill scope template -> import scope -> request approval bundle -> work resume
```

The lower-level equivalent remains:

```text
run create -> work start -> scope-template -> work resume
```

`devo work complete` records the delivered commit, delivery summary, latest validation run id/status when available, approval bundle status, final Git delivery status when available, and delivered timestamp. `devo work status` shows those fields with a compact next action and suggested next command so the final package state is obvious after a successful push.

Use `devo work list` to see recent open and delivered work packages with approval, validation, commit, and next-action fields. Use `devo work history` when you mainly want delivered work and commit summaries. Use `devo project activity` for a compact project-level view across recent runs, delivered packages, validation runs, context updates, reports, current Git state, and the suggested next action.

Use `devo visual work-package` to write a Mermaid lifecycle artifact for one run at `workspace/runs/<project>/<runId>/artifacts/visuals/work-package-flow.md`. Use `devo visual project-activity` to write a compact recent activity diagram at `workspace/projects/<project>/visuals/project-activity.md`. These are generated workspace artifacts for current state, not hand-maintained docs.

## UI-Ready JSON Summaries

Devo has a read-only read-model layer for UI/API work. It powers the local dashboard and does not mutate target projects.

```powershell
devo project overview --project <name>
devo project overview --project <name> --json
devo project activity --project <name> --json
devo work status --project <name> --run <runId> --json
devo doctor --project <name> --json
```

The read models summarize projects, runs, and work packages with UI-friendly fields such as onboarding status, doctor status, settings, Git status, validation registry, recent work packages, approval/validation/delivery state, next phase, next command, and stop conditions. Dashboard work should consume these read models through CLI JSON or the local API, not scrape raw workspace folders directly. The local UI/API plan is documented in [UI/API architecture](ui-architecture.md), and the first dashboard scope is documented in [UI MVP specification](ui-mvp-spec.md): read-only dashboard first, controlled actions later, and no bypass around Devo approval/policy checks.

## Local Read-Only API

The dashboard consumes the same read models through a local-only FastAPI backend:

```powershell
devo api routes
devo api serve
```

Default URL:

```text
http://127.0.0.1:8765
```

Useful MVP endpoints:

```text
GET /api/health
GET /api/current
GET /api/projects
GET /api/projects/{project}/overview
GET /api/projects/{project}/activity
GET /api/projects/{project}/doctor
GET /api/projects/{project}/runs/{run_id}/overview
GET /api/projects/{project}/runs/{run_id}/work-package
GET /api/actions
GET /api/actions/allowed
GET /api/actions/{action_id}
POST /api/actions/execute
```

The original API surface is read-only. UI v2 adds one controlled workspace-safe execution endpoint for four approved actions only. It does not approve/reject, run validation/build/test/app commands, restore/delete backups, modify scheduler settings, commit, push, edit target files, or call model APIs. `devo api serve` blocks non-local hosts for MVP safety. Responses include an `X-Devo-Elapsed-Ms` header to help identify slow read-model endpoints during dashboard review.

The action metadata endpoints describe UI safety boundaries. `/api/actions/allowed` returns read-only actions plus the workspace-safe actions enabled in controlled UI mode. `/api/actions` also includes planned/deferred/blocked approval, validation, Git, backup, scheduler, target app, and model/API actions. `POST /api/actions/execute` requires `confirm: true` and is limited to `work.new.create`, `work.scope_template.generate`, `visual.work_package.generate`, `visual.project_activity.generate`, and `onboarding.report.write`.

For profiling slow local read models, add `include_timing=true` to selected endpoints:

```text
GET /api/projects/<project>/overview?include_timing=true
GET /api/projects/<project>/doctor?include_timing=true
GET /api/projects/<project>/activity?include_timing=true
```

The `_timing` object is omitted by default. This timing support is read-only and process-local; Devo has not added persistent DB or SQLite caching for dashboard data.

## React UI Scaffold

The read-only dashboard is under `ui/` and uses the local API.

Show URLs and start guidance:

```powershell
devo ui info
devo ui urls
```

Check whether the local API/UI are already running:

```powershell
devo ui status
```

`devo ui status` is only a short reachability check. It does not start servers and it does not verify dashboard pages unless the local API and UI dev server are already running. For a browser/page smoke review, start the API and UI first, then open `http://127.0.0.1:5173`.

Open the UI in the default browser when the UI dev server is reachable:

```powershell
devo ui open
```

The UI helpers are read-only. They do not start servers, stop processes, run validation/build/test/app commands, restore/delete backups, modify scheduler settings, commit, push, edit target files, or call model APIs.

Start the API:

```powershell
devo api serve
```

Start the UI:

```powershell
cd ui
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The frontend defaults to `http://127.0.0.1:8765` for the API. Override it with `VITE_DEVO_API_BASE` when needed. The dashboard includes Projects, Project Overview, Planning Intake, Blueprint, Backlog, Batches, Queues, Handoffs, Worker Runs, Progress, Work Package, Activity, Health, and Action Safety pages.

Planning Intake is a read-only operator guide for brief, blueprint, backlog, batch, queue, handoff, worker run, and progress state; it shows status/count summaries and copyable CLI commands. Blueprint and Backlog are read-only inspection pages for planning artifacts, milestone/epic rollups, task filters, and task details. Batches, Queues, Handoffs, Worker Runs, and Progress are read-only inspection pages for the later planning-to-Codex handoff stages: batch risk/lane summaries, queue item state, handoff prompt metadata, worker run/report/run-plan/execution review evidence, preflight status, progress bars, milestone/epic rollups, warnings, and next actions.

These pages do not import reports from the UI, start/resume workers, execute target commands, validate, commit, push, restore/delete backups, modify scheduler settings, edit target files, run Codex, complete queue items, or call model APIs from the UI. Batch approval controls, when surfaced through the controlled Action Safety model, are workspace-safe planning actions only: request approval, record review notes, approve planning, or reject planning. They do not create queues or execute target work. The pages also provide copyable CLI commands so the user can continue through the safer CLI/Codex workflow. The Action Safety page can create a new Devo run/work-package draft and execute the approved workspace-safe artifact generation actions after explicit confirmation.

## Safety

```powershell
devo policy classify --project <name> --run <runId> --task <taskId>
devo approval request --project <name> --run <runId> --task <taskId> --action <actionType>
devo approval approve --project <name> --run <runId> --approval <approvalId> --by Manas
```

A Devo approval is an audit/workflow record. It does not grant shell, GitHub, OS, Codex, OpenAI, or external-service permissions.

## Validation

```powershell
devo validation list --project <name>
devo validation suggest --project <name>
devo validation run --project <name> --id <id> --dry-run
devo validation history --project <name>
```

Registered validation commands are safer than ad hoc commands because Devo records risk, working directory, approval requirements, and execution history.

## Delivery

```powershell
devo git status --project <name>
devo git delivery-check --project <name>
devo git delivery-report --project <name> --run <runId> --message "<message>"
devo delivery check --project <name>
devo delivery check --project <name> --queue <queueId> --item <itemId> --write
devo delivery list --project <name>
devo delivery show --project <name> --delivery <deliveryId>
devo delivery plan --project <name> --delivery <deliveryId> --message "<commit message>"
devo delivery plan-list --project <name>
devo delivery plan-show --project <name> --plan <deliveryId>
devo delivery approval-request --project <name> --plan <deliveryId> --note "<note>"
devo delivery approval-show --project <name> --plan <deliveryId>
devo delivery approval-list --project <name>
devo delivery approve --project <name> --plan <deliveryId> --approver "<name>" --note "<note>"
devo delivery reject --project <name> --plan <deliveryId> --reviewer "<name>" --note "<note>"
devo delivery report-prepare --project <name> --plan <deliveryId>
devo delivery report-list --project <name>
devo delivery report-show --project <name> --report <deliveryId>
devo delivery report-refresh --project <name> --report <deliveryId> --note "<reason>"
devo delivery report-refresh --project <name> --report <deliveryId> --reopen --note "<reason>"
devo delivery commit-message --project <name> --plan <deliveryId>
devo delivery commit-diagnostics --project <name> --report <deliveryId>
devo delivery commit-diagnostics --project <name> --report <deliveryId> --index-lock-probe --confirm-probe
devo delivery commit-preview --project <name> --report <deliveryId>
devo delivery commit --project <name> --report <deliveryId> --confirm-commit
devo delivery commit-show --project <name> --delivery <deliveryId>
devo delivery push-preview --project <name> --report <deliveryId>
devo delivery push --project <name> --report <deliveryId> --confirm-push
devo delivery push-show --project <name> --delivery <deliveryId>
```

Git delivery commands inspect Git state and write Git-focused evidence. Delivery readiness commands inspect the post-worker delivery gate and can write JSON/Markdown artifacts under `workspace/projects/<project>/delivery/`.

`devo delivery check` reports target repo path, branch, remote/upstream, Git status summary, changed/staged/unstaged/untracked files, forbidden changed/staged paths, workspace artifacts staged, secret-risk files/signals, linked queue item status, linked worker review status, linked validation evidence status, blockers, warnings, and next action. Linked queue checks block when the queue item is not completed, when the linked worker review is missing/not `reviewed_passed`, or when validation evidence failed. If Git prints the known unreadable global ignore warning but status/diff still pass, Devo keeps it visible as a non-blocking warning.

`devo delivery plan` creates a plan from a written readiness check and records the intended future commit message. `approval-request` records that the plan needs delivery review. `approve` approves only non-blocked plans; warnings can be approved but remain visible in the artifact. `reject` records rejection without deleting artifacts.

After a plan is approved, `devo delivery report-prepare` writes `delivery-report-<id>.json` and `.md`, re-checks current readiness, summarizes blockers/warnings/validation/review/safety state, and marks whether the report is commit-ready. Readiness fields in delivery reports are snapshots from report preparation; after commit or push they are labeled historical, and `devo delivery check --write` should be run again if current repository state matters. `devo delivery commit-message` prints only the proposed commit message. `devo delivery commit-preview` shows exactly which files a guarded commit would stage and commit without changing anything.

Use `devo delivery latest --project <name>` when delivery artifacts feel confusing. It is read-only and summarizes the current Git status, latest check, latest meaningful non-empty check, latest plan/approval/report, commit result, push result, pushed delivery, and next command. If the latest check is an empty clean check, it says no delivery is needed instead of recommending a plan.

If a guarded commit fails for a transient Git issue such as `.git/index.lock` permission denial or a stale lock, Devo records the failure category and retryability on the delivery report and commit artifact. Guarded commit now checks index-lock write capability before staging; if the check fails, Devo blocks before `git add` and no target files should be staged by that attempt. Use `devo delivery report-refresh --project <name> --report <deliveryId> --note "<reason>"` to refresh the current readiness snapshot without reopening. If it reports reopening is allowed, use `devo delivery report-refresh --project <name> --report <deliveryId> --reopen --note "<reason>"`, then run `devo delivery commit-preview` again. Refresh/reopen does not stage, unstage, commit, push, validate, run Codex, or modify target repo files.

Before retrying a blocked report, run `devo delivery commit-diagnostics --project <name> --report <deliveryId>`. Diagnostics is read-only by default and shows Git executable/version, `.git`/`.git/index` state, `.git/index.lock` presence, staged/unstaged/untracked files, last failure category/message, likely causes, and safe next actions. For index lock permission failures, check for active Git operations, stale locks, `.git` ACLs, antivirus/Controlled Folder Access, terminal/user mismatches, and read-only/protected directories. The optional `--index-lock-probe --confirm-probe` is explicit and attempts to create/remove `.git/index.lock` only for diagnostics; do not use it unless you understand the probe and no Git process is active.

For live DevOrchestrator delivery dogfood, run guarded delivery commit/push from normal local PowerShell as the normal Windows user with the explicit prefix `.\.venv\Scripts\devo.exe`. DEL-0001 showed why: restricted Codex/sandbox context could not create `.git/index.lock`, while normal PowerShell completed commit `f0e8c0319c135f72973357776cd7c62d6cc8832b` and pushed it to `origin/main` through Devo delivery commands. Do not bypass Devo delivery with manual `git add`, `git commit`, or `git push` unless explicitly approved.

`devo delivery commit --confirm-commit` is the only delivery command that may create a Git commit. It is CLI-only, requires a ready approved delivery report, re-runs safety checks, verifies the process can create and remove `.git/index.lock`, stages only eligible files, writes a commit result artifact, and updates the delivery report with the commit hash. It does not push, run validation, complete queue items, run Codex, run target commands, modify workspace artifacts for commit, or bypass GitHub policy.

Secret-safety documentation is warning-only when it stays documentation-only. `README.md` and `docs/*.md` can mention `.env`, API keys, tokens, placeholders, redacted values, and safety rules without blocking delivery. Actual secret-like values and secret-bearing files still block readiness.

`devo delivery push-preview` is read-only and shows the intended remote/branch, commit hash, blockers, and warnings. `devo delivery push --confirm-push` is the only delivery command that may run `git push`; it is CLI-only, requires prior guarded commit metadata, verifies the remote/branch and commit containment, writes a push result artifact, and updates the delivery report with push metadata. It does not commit, run validation, complete queue items, run Codex, run target commands, or bypass GitHub policy. UI commit/push buttons remain unavailable.

The dashboard Delivery page is read-only. It shows checks, plans, approvals, reports, commit results, push results, blockers, warnings, readiness snapshot labels, next action, and copyable CLI commands. It does not stage, unstage, validate, commit, push, restore, edit schedulers, run Codex, or run target commands.

## Context And Recovery

```powershell
devo project context-refresh --project <name> --run <runId> --write-draft
devo report run --project <name> --run <runId> --write
devo report handoff --project <name> --run <runId> --write
```

Use reports instead of re-explaining the project from memory. They are the preferred recovery trail after crashes, context loss, or a handoff between ChatGPT, Codex, and the user.

## What Not To Commit

Do not stage or commit generated runtime artifacts unless a task explicitly says to do so. In normal development, do not stage:

- `workspace/`
- `.venv/`
- `.env`
- `.pytest_cache/`
- `pt-*` folders
- backup folders
- restore-test folders
- target project files outside the approved task scope
