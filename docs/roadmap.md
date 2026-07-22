# DevOrchestrator Roadmap

## Immediate Planned Tasks

- TASK-030C continue delivery secret-signal noise reduction
- TASK-033 interrupted work recovery/resume command
- TASK-038 Codex handoff prompt generator
- TASK-039 global Devo status/dashboard command
- TASK-036 run templates for common task types

## Immediate Readiness Target

DevOrchestrator is considered 90-95% ready for PersonalOS work when it has:

- task selection
- policy classification
- approval gates
- validation registry
- safe validation runner
- git delivery workflow
- context update workflow
- project/run/handoff report commands
- one end-to-end dogfood run

## Rough Remaining Effort

- Practical readiness remaining: around 8-18 focused hours.
- Full long-term product vision: 80-150+ hours.

## Near-Term Direction

### TASK-DEVO-048A Vision And Workflow Documentation - Completed

Added plain-language docs for Devo's vision, current capabilities, agent workflow, usability roadmap, and PersonalOS operating model. These docs explain that Devo is the manager/guard/record keeper, not the AI; that current agents are prompt roles, not autonomous bots; and that the next usability layer should focus on work packages, lanes, approval bundles, operator prompts, short final reports, and later dashboard/model adapters.

### TASK-DEVO-048B Work Packages And Approval Bundles - Completed

Added first-class work packages and approval bundles. A work package captures one approved batch of related work, limited by scope, risk, and validation method rather than file count. The MVP includes the `low-risk-ui-maintenance` lane, `work-package.json`, `work-package.md`, `operator-prompt.md`, scope import, and bundled approval commands. Approval bundles create normal child approval records for scoped source edit and registered build validation, so exact `target_command` approval remains supported and the validation runner still checks category, command id, command text, task, run, and project before execution.

### TASK-DEVO-050 Work Package Completion Status - Completed

Added `devo work complete` and compact final delivery status for work packages. The command records delivered timestamp, commit hash, delivery summary, latest validation run id/status when available, approval bundle status, and final Git delivery status when available. The documented low-risk work-package flow is now `work start -> import scope -> request approval bundle -> bundle approve -> implement/build/commit -> work complete -> final report`.

### TASK-DEVO-051 Work Package Next Actions And Phase Prompts - Completed

Added `devo work next` and `devo work prompt --phase <phase>` so Devo can generate compact next-action guidance and phase-specific Codex operator prompts for `scope`, `implement`, `validate`, `deliver`, and `complete`. `devo work status` now includes a suggested next command when one is available.

### TASK-DEVO-052 Work History And Project Activity Summaries - Completed

Added `devo work list`, `devo work history`, and `devo project activity` so recent work packages, delivered commits, approval bundle status, latest validation state, context/report artifacts, current Git status, and suggested next actions are visible without hand-inspecting workspace files. The commands tolerate older runs that do not have work-package artifacts or newer delivery fields.

### TASK-DEVO-053A Visual Strategy And Core Diagrams - Completed

Added `docs/visual-strategy.md` plus a small set of high-value Mermaid diagrams for stable Devo concepts: architecture/control-room boundaries, manual-assisted agent workflow, work-package lifecycle, usability roadmap, and scheduled backup flow. The strategy keeps Mermaid as documentation support, while future dashboard visuals should be generated from structured Devo data/artifacts.

### TASK-023 Safe Validation Runner

Add controlled execution for registered validation commands. It should require policy checks, approval where required, disabled-command handling, output capture, timeout limits, and clear evidence recording. This is the first step that can execute commands, so safety and approval behavior matter more than convenience.

### TASK-024 Git Delivery Workflow - Completed

Added non-mutating Git status, delivery-check, and delivery-report commands. Devo now reports branch/upstream state, changed files, forbidden staged paths, secret-like changed-file signals, validation evidence, approval evidence, and exact manual commit/push guidance without force-pushing or bypassing approval policy.

### TASK-025 Project Context Update / Enrichment Workflow - Completed

Added deterministic context-summary, context-refresh, context-apply, and context-history commands. Context updates are append-only Devo workspace records sourced from scans, validation metadata, environment snapshots, runs, delivery reports, and approval ledgers; they do not modify target repositories or overwrite approved context automatically.

### TASK-029 Project/Run Report And Handoff Summary Commands - Completed

Added deterministic project, run, and handoff reports. Devo now summarizes project context, recent runs, workflow next actions, task resolution, policy/approval/validation/git-delivery evidence, warnings, suggested actions, and recovery handoff commands without mutating target projects or workflow state.

### TASK-030 End-To-End Dogfood Run

Completed. DevOrchestrator ran a docs-only task through its own file-backed workflow, including manual-assisted agent artifacts, policy approval, implementation evidence, validation review, code review, final audit, task closure, run closure, delivery report, context refresh draft, and handoff report.

### TASK-031 Resume PersonalOS Through Devo - Completed

Used Devo to execute one safe real PersonalOS task: a docs-only update to `docs/current-state.md`, with no code, database, restore/build/test, migration, script, secret, generated-file, or local-settings changes.

### TASK-030B Register DevOrchestrator Validation Commands - Completed

Registered DevOrchestrator validation commands in its Devo workspace registry: core py_compile, focused policy tests, focused approval tests, focused report tests, git diff whitespace checks, and a disabled-by-default full pytest command. Future dogfood runs can cite Devo validation run evidence directly.

### TASK-030C Reduce Policy And Secret-Signal Noise - Partially Completed By TASK-034

Refine policy and delivery checks using dogfood findings. TASK-034 completed the policy portion by separating safety-boundary wording from positive risk evidence and by adding explicit target repository action hints. Delivery scanning for documented secret-signal names remains future work.

### TASK-035 Git Delivery Path Reliability - Completed

Fixed Devo Git status and delivery-check handling for registered repository paths that contain spaces and for Git safe-directory ownership checks. The Git subprocess wrapper now uses argument lists with a per-command `safe.directory` override for the registered repository path, preserves non-git/subdirectory failures, and reports a clearer diagnostic when a registered path is inside a Git work tree but is not the repository root.

### TASK-032 Project Memory Handling - Current

Persist durable project memory, user-facing operating guidance, token-usage expectations, and future improvement plans so they survive chat context loss and can be recovered from GitHub plus workspace backups.

### TASK-033 Interrupted Work Recovery/Resume Command

Add a read-only command that summarizes interrupted work and recommends the safest resume point.

### TASK-034 Docs-Only Target Policy/Action Handling - Completed

Added explicit target repository action types, including medium-risk `target_repo_docs_edit` and high-risk target code/config/validation/build/test/run/migration/database/script actions. Policy classification now records safety exclusions such as "no DB/migrations/build/test/restore/secrets" separately from matched risk signals so docs-only scopes do not inherit misleading database risk.

### TASK-038 Codex Handoff Prompt Generator

Generate compact Codex-ready prompts from approved context, run state, task scope, policy, validation, and delivery evidence.

### TASK-039 Global Devo Status/Dashboard Command

Show registered projects, active runs, warnings, approvals, validation state, and next actions in one command.

### TASK-036 Run Templates For Common Task Types

Provide deterministic templates for docs-only tasks, safe bugfixes, validation-only work, recovery work, and larger feature planning.

### TASK-037 Approval UX Improvements - Completed

Reduced duplicate approval friction in the validation runner. Exact `target_command` approval remains supported for maximum precision, and safely scoped `target_repo_build`, `target_repo_test`, and `target_repo_validation` approvals now authorize matching registered validation commands only when the category/action and exact command scope match.

## Guiding Constraints

- Keep Devo deterministic first.
- Preserve target project safety.
- Avoid AI API integration until file-based workflows are proven.
- Avoid web UI until CLI workflows are stable.
- Prefer explicit approval records and evidence over implicit automation.
- Reduce user friction with work packages, lanes, approval bundles, and compact operator prompts before adding direct model adapters.
