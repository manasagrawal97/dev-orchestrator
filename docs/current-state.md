# DevOrchestrator Current State

## Project Identity

- Project name: DevOrchestrator
- Purpose: model/tool-agnostic AI development control plane
- Local path: `E:\DevOrchestrator`
- GitHub repo: `https://github.com/manasagrawal97/dev-orchestrator`
- Backup root: `G:\My Drive\Projects\Dev Orchestrator`

## Backup Policy

- Scheduled backups run every 6 hours.
- Keep the latest 3 normal backups.
- Older normal backups are auto-deleted only after a new backup is successfully created and verified.
- Protected backups are kept only when explicitly created with `-Protect` or `--protect`.
- Scheduled backup installs use hidden PowerShell mode; visible legacy backup windows should not be closed while running.
- `.incomplete` backup folders mean a backup was interrupted or failed and are not counted as successful/restorable backups.
- Manual backup after every task is not required.
- Manual backup is reserved for risky milestones or backup/recovery system changes.
- Source code is protected by GitHub.
- Devo workspace/runtime context is protected by Google Drive workspace backups.

## Current Operating Model

DevOrchestrator is a deterministic local control plane. It records project context, run state, task lifecycle state, policy decisions, approvals, validation command metadata, validation run evidence, and recovery information in the local `workspace/` folder. It does not call AI models, execute implementation, or bypass Codex/OpenAI/OS/GitHub security policy. Registered validation commands run only through Devo's safety gates, disabled-command handling, and explicit approval checks when required.

For a plain-language overview of the intended product shape, read `docs/devo-vision.md`, `docs/current-capabilities.md`, `docs/agent-workflow.md`, `docs/usability-roadmap.md`, and `docs/personal-os-operating-model.md`.

Current strategic priority: improve Devo itself as a CLI-first, local-first product. PersonalOS is lower priority as a product target and should mainly be used as a real-world validation project for Devo workflows.

The working loop is:

1. ChatGPT helps plan, reason about risk, and choose the next safe step.
2. Codex implements DevOrchestrator changes, runs tests, commits, pushes, and records reports.
3. Devo persists project/run/task state, workflow decisions, policy gates, approval records, validation command metadata, and recovery artifacts.
4. The user gives final approval for risky work and handles manual operations when Codex approval policy blocks them.

## Latest State

- Latest completed source task: TASK-DEVO-061 guided project onboarding
- Latest docs task: TASK-DEVO-054A clarifies the CLI-first, local-first Devo roadmap and positions PersonalOS as a Devo validation target.
- Latest completed workspace setup: TASK-030A approved DevOrchestrator itself as a Devo project
- Latest completed dogfood run: TASK-030 end-to-end dogfood run on DevOrchestrator itself
- Latest PersonalOS dogfood milestone: warning cleanup completed with RZ10012 0, MUD0002 0, passing build, and 16 remaining generated Razor CS8669 warnings documented/ignored for now.
- Latest pushed commit before TASK-035 reliability work: `4987b30 docs: register DevOrchestrator validation commands`
- Next recommended action: continue delivery-signal noise reduction, then add interrupted-work recovery/resume and handoff prompt generation.
- PersonalOS validation registry exists in Devo workspace at `workspace/projects/PersonalOS/validation-commands.json`.
- PersonalOS validation commands are high risk, approval required, and disabled by default.
- DevOrchestrator validation registry exists in Devo workspace at `workspace/projects/DevOrchestrator/validation-commands.json`.
- DevOrchestrator has enabled focused validation commands for core py_compile, policy tests, approval tests, report tests, and git diff whitespace checks; full pytest is registered but disabled by default because it is heavier.
- Future DevOrchestrator dogfood runs can attach validation evidence from the registry instead of only relying on manually reported pytest output.
- No PersonalOS repo files were modified by TASK-022.
- TASK-023 added controlled validation execution, but PersonalOS validation/build/test/restore commands remain dry-run only unless explicitly approved.
- TASK-024 added non-mutating Git status, delivery-check, and delivery-report commands with risky-file and secret-signal checks.
- TASK-025 added deterministic context-summary, context-refresh, context-apply, and context-history commands for append-only project context updates.
- TASK-029 added deterministic project, run, and handoff reports for context recovery and work transfer.
- TASK-031 used Devo to complete one safe PersonalOS docs-only current-state task.
- TASK-034 improves docs-only target repository policy actions and records safety exclusions separately from matched risk signals.
- TASK-030B registered DevOrchestrator's own validation commands for future dogfood evidence.
- TASK-035 fixed Git delivery/status checks for registered repository paths with spaces and Git safe-directory ownership checks.
- TASK-037 aligned validation-runner approval matching so exact `target_command` approvals remain supported and safely scoped `target_repo_build`, `target_repo_test`, and `target_repo_validation` approvals can authorize matching registered validation commands without duplicate approval friction.
- TASK-DEVO-048A added plain-language product docs for what Devo is, how current agents work, what Devo can do today, how PersonalOS should be operated through Devo, and which usability improvements come next.
- TASK-DEVO-048B adds first-class work packages, the built-in `low-risk-ui-maintenance` lane, generated operator prompts, and approval bundles that create normal child approvals for scoped source edits and registered build validation.
- TASK-DEVO-049 makes future scheduled backup installs run with hidden PowerShell mode and reports `.incomplete` backup folders separately as likely interrupted/failed backups.
- TASK-DEVO-050 adds `devo work complete` and improves `devo work status` so delivered packages show approval bundle status, validation evidence, commit hash, delivery summary, final Git status, and next action.
- TASK-DEVO-051 adds `devo work next` and `devo work prompt --phase <phase>` for scoped phase prompts covering scope, implement, validate, deliver, and complete.
- TASK-DEVO-052 adds `devo work list`, `devo work history`, and `devo project activity` for compact recent work-package, delivery, validation, context/report, Git status, and next-action summaries.
- TASK-DEVO-053A adds `docs/visual-strategy.md` and a compact set of Mermaid diagrams for Devo architecture, agent workflow, work-package lifecycle, usability roadmap, and backup flow. Future dashboard visuals should be generated from Devo structured data/artifacts rather than manually maintained Mermaid.
- TASK-DEVO-053B adds `devo visual work-package` and `devo visual project-activity` to generate compact Mermaid workspace artifacts from live Devo work-package and project activity data.
- TASK-DEVO-054A documents the updated strategy: Devo is the main product priority, current development is CLI-first/local-first, PersonalOS is primarily a dogfood validation project, dashboard/UI is later, and direct AI/API agents are future optional scope.
- TASK-DEVO-055 adds `devo doctor` and `devo doctor --project <project>` for read-only Devo/project health checks covering workspace, project registration, Git, validation registry, work packages, latest validation, generated visuals, backup inventory, scheduled backup task status when safely checkable, overall status, and suggested next action.
- TASK-DEVO-056 adds `devo work scope-template` and `devo work scope-example --lane low-risk-ui-maintenance` so draft work packages can generate lane-aware scope Markdown with required import sections, allowed/forbidden defaults, validation command guidance, stop conditions, approval bundle notes, and final report expectations before scope import.
- TASK-DEVO-057 adds more built-in work lanes: `docs-only`, `warning-cleanup`, `small-bugfix`, `small-feature`, `test-only`, `backup-maintenance`, and `devo-internal-source`, plus `devo work lane-show --lane <lane>` for inspecting lane rules.
- TASK-DEVO-058 adds `devo work resume --project <project> --run <runId>` to generate a compact read-only operator plan from work-package state, lane rules, imported scope, approval bundle status, latest validation, latest Git delivery evidence, recommended next commands, stop conditions, and final report expectations.
- TASK-DEVO-059 adds `devo work new --project <project> --goal "<goal>" --lane <lane>` to create a run, start a work package, generate a scope template by default, and print resume guidance in one read-only bootstrap flow.
- TASK-DEVO-060 adds project workflow settings with `devo project settings-show` and `devo project settings-set`. Settings can store default lane, validation command, full-test command, branch, automatic scope-template behavior, delivery mode, and notes. `devo work new` can now omit `--lane` when a project default lane is configured, and `devo doctor --project` checks settings health.
- TASK-DEVO-061 adds `devo project onboard --project <project>` as a read-only setup checklist covering registration, path, scan, context, validation registry, project settings, doctor status, overall onboarding status, and the next setup command. Optional flags can print suggested settings or write a workspace-only onboarding report without modifying the target project.

## Readiness Estimate

- Practical CLI product maturity after TASK-DEVO-053B: around 75-80% complete.
- Long-term product vision, including dashboard and direct model adapters: around 50-55% complete.

DevOrchestrator can execute registered low/medium validation commands with safety gates, dry-run high-risk target commands, summarize Git delivery readiness, refresh project context, generate project/run/handoff reports, run read-only doctor and project onboarding checks, store project workflow defaults, bootstrap scoped work packages across multiple built-in lanes, generate lane-aware scope templates, resume work packages with compact operator plans, bundle related approvals without bypassing child approval records, generate next-action and phase-specific work-package prompts, mark work packages delivered with final commit/validation/git evidence, summarize recent work/project activity, generate Mermaid workspace visual reports from structured data, and complete a manual-assisted end-to-end dogfood run.

The next product step should focus on Devo CLI maturity. PersonalOS should be used occasionally for controlled dogfood batches that validate Devo behavior, not as the main development focus.

## Completed Work

- TASK-001 CLI + project registry
- TASK-002 safe project scanner
- TASK-003 agent registry + ProjectContextDiscoveryAgent prompt
- TASK-004 project context lifecycle/import/reviewer prompt/approval gate
- TASK-004A context completeness validation / no truncated prompt
- TASK-005 run creation and goal lifecycle
- TASK-006 run-level IdeaAnalystAgent + RequirementsAgent workflow
- TASK-007 PlannerAgent + PlanReviewerAgent workflow
- TASK-008 TaskDecomposerAgent workflow
- Manual scanner fix for `.slnx` categorization
- TASK-009 ImplementationCoordinatorAgent workflow
- TASK-010 implementation completion record workflow
- TASK-011 ValidatorAgent workflow
- TASK-012 CodeReviewerAgent workflow
- TASK-013 FinalAuditorAgent workflow
- TASK-014 task closure workflow
- TASK-015 task disposition / ledger reconciliation workflow
- TASK-016 run closure workflow
- TASK-026 workspace backup/export workflow
- TASK-027 tech stack / environment snapshot workflow
- TASK-028 backup automation and disaster recovery scripts
- TASK-028A backup wrapper path detection hotfix
- TASK-017 workflow status / next / advance commands
- TASK-018 workflow batch runner
- TASK-019 deterministic task selection
- TASK-020 risk classification + policy gates
- TASK-021 approval request and approval ledger system
- TASK-021B backup schedule/retention policy + repo rename housekeeping
- TASK-022 validation command registry
- TASK-023 safe validation runner
- TASK-024 Git delivery workflow
- TASK-025 project context update / enrichment workflow
- TASK-029 project/run report and handoff summary commands
- TASK-030A DevOrchestrator self-onboarding as an approved Devo project
- TASK-030 end-to-end DevOrchestrator dogfood run
- TASK-031 PersonalOS current-state docs-only dogfood task
- TASK-034 docs-only target policy/action handling
- TASK-030B DevOrchestrator validation registry setup
- TASK-035 Git delivery path reliability for registered repositories with spaces
- TASK-037 validation approval matching for target build/test actions
- TASK-DEVO-048A Devo vision, capability, agent workflow, usability roadmap, and PersonalOS operating model docs
- TASK-DEVO-048B work packages and approval bundles MVP
- TASK-DEVO-049 scheduled backup visibility and incomplete reporting
- TASK-DEVO-050 work-package completion status and final delivery summary
- TASK-DEVO-051 work-package next-action and phase prompt commands
- TASK-DEVO-052 work history and project activity summary commands
- TASK-DEVO-053A visual strategy and essential Mermaid diagrams
- TASK-DEVO-053B generated visual reports for work packages and project activity
- TASK-DEVO-054A CLI-first Devo roadmap and project-priority clarification
- TASK-DEVO-055 doctor health-check command
- TASK-DEVO-056 work scope templates
- TASK-DEVO-057 built-in work lanes
- TASK-DEVO-058 work resume guidance
- TASK-DEVO-059 one-command work bootstrap
- TASK-DEVO-060 project workflow settings
- TASK-DEVO-061 guided project onboarding

## Recovery Pointers

If chat context is lost, start here:

1. Read this file.
2. Read `docs/devo-vision.md`.
3. Read `docs/current-capabilities.md`.
4. Read `docs/agent-workflow.md`.
5. Read `docs/roadmap.md`.
6. Read `docs/operating-model.md`.
7. Run `scripts/recovery/check-devo-recovery-status.ps1` from `E:\DevOrchestrator`.
8. Run `devo report handoff --project DevOrchestrator` or `devo report project --project DevOrchestrator` for a compact state summary.
9. For active work, run `devo report run --project DevOrchestrator --run <runId>` when a run id is known.
10. Continue from the latest planned next task.
