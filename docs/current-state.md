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

For a plain-language overview of the intended product shape, read `docs/devo-vision.md`, `docs/devo-company-model.md`, `docs/codex-worker-adapter-design.md`, `docs/remaining-roadmap.md`, `docs/current-capabilities.md`, `docs/agent-workflow.md`, `docs/usability-roadmap.md`, and `docs/personal-os-operating-model.md`.

Current strategic priority: improve Devo itself as a CLI-first, local-first product. PersonalOS is lower priority as a product target and should mainly be used as a real-world validation project for Devo workflows.

The working loop is:

1. ChatGPT helps plan, reason about risk, and choose the next safe step.
2. Codex implements DevOrchestrator changes, runs tests, commits, pushes, and records reports.
3. Devo persists project/run/task state, workflow decisions, policy gates, approval records, validation command metadata, and recovery artifacts.
4. The user gives final approval for risky work and handles manual operations when Codex approval policy blocks them.

## Latest State

- Latest completed source task: TASK-DEVO-086 planning pipeline operator guidance and input robustness
- Latest design task: TASK-DEVO-087 Codex CLI worker adapter design
- Latest docs task: TASK-DEVO-073B reprioritizes the remaining roadmap around brief intake, blueprint/backlog, batches, execution queue, Codex handoff, progress tracking, and review/resume.
- Latest completed workspace setup: TASK-030A approved DevOrchestrator itself as a Devo project
- Latest completed dogfood run: TASK-DEVO-085 end-to-end planning pipeline dogfood run on DevOrchestrator itself
- Latest PersonalOS dogfood milestone: warning cleanup completed with RZ10012 0, MUD0002 0, passing build, and 16 remaining generated Razor CS8669 warnings documented/ignored for now.
- Latest pushed commit before TASK-035 reliability work: `4987b30 docs: register DevOrchestrator validation commands`
- Next recommended action: continue toward TASK-DEVO-088 worker run/report data model, keeping actual Codex execution deferred until design, report import, visibility, and safety gates are ready.
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
- TASK-DEVO-062 adds `devo current` and current-context shortcuts so common project/work/visual commands can use the saved `devo use --project <project> [--run <runId>]` context when `--project` or `--run` are omitted.
- TASK-DEVO-063 adds UI-ready read models in `src/devo/read_models.py` for project, run, and work-package overviews, plus JSON output for `devo project overview`, `devo project activity`, `devo work status`, and `devo doctor`. This prepares the future dashboard/API layer without building UI yet.
- TASK-DEVO-064 adds `docs/ui-architecture.md` to document the local-first UI/API architecture, read-only dashboard v1 scope, controlled-action v2 scope, safety model, API endpoint preview, and phased UI implementation plan before any UI code is written.
- TASK-DEVO-065A adds `docs/ui-mvp-spec.md` to define the first read-only dashboard pages, reusable components, allowed/forbidden UI v1 actions, future UI v2/v3 actions, approval UI design notes, API/read-model mapping, wireframes, success criteria, and deferred scope.
- TASK-DEVO-065B adds a local-only FastAPI backend in `src/devo/api.py` plus `devo api serve` and `devo api routes`. The API binds to `127.0.0.1` by default, blocks non-local hosts for MVP, exposes read-only JSON endpoints backed by Devo read models, and does not run validation, build, test, restore, Git delivery, scheduler, target app, or model/API actions.
- TASK-DEVO-066 adds a React/Vite/TypeScript frontend scaffold under `ui/`. It is read-only, defaults to `http://127.0.0.1:8765` via `VITE_DEVO_API_BASE`, includes Projects and Health pages with live API calls, placeholder pages for Project Overview, Work Package, and Activity, and provides no approval/build/test/commit/push/restore/scheduler/model actions.
- TASK-DEVO-067 turns the scaffold into a useful read-only dashboard MVP. Projects, Project Overview, Work Package, Activity, and Health pages consume the local API/read models; the UI shows current context, project summaries, settings, Git, validation, backup, recent runs/work packages, lifecycle state, doctor checks, stop conditions, suggested next actions, optional JSON views, and copyable CLI commands only.
- TASK-DEVO-068 polishes the read-only dashboard layout and loading behavior. It removes the "Local-first control room" wording from visible UI, separates dashboard project selection from saved CLI current context, adds section-level slow-loading hints for overview/doctor/activity-backed views, reduces Activity path noise, improves the missing work-package empty state with safe CLI commands, and keeps UI v1 free of approval/build/test/commit/push/restore/scheduler/model actions. Read-model snapshot caching and deeper endpoint profiling remain deferred.
- TASK-DEVO-069 adds opt-in API timing breakdowns with `include_timing=true`, bounds slow optional doctor scheduled-task checks, adds a Git read timeout for non-mutating Git status calls, removes duplicate doctor work from project overview onboarding status, and reuses loaded run/validation data while building activity summaries. No DB/SQLite cache was added; persistent workspace JSON snapshot caching remains a future option if read-model performance still needs it.
- TASK-DEVO-070 adds read-only UI helper commands: `devo ui info`, `devo ui urls`, `devo ui status`, and `devo ui open`. These commands print local API/UI URLs, show manual start commands, check API/UI reachability with short timeouts, and open the UI only if it is already reachable. They do not start servers, mutate workspace state, run target commands, or add UI write actions.
- TASK-DEVO-071 adds `src/devo/ui_actions.py`, read-only API endpoints for UI action safety metadata, and an informational Action Safety dashboard page. UI v1 can show which actions are read-only, workspace-safe candidates, approval-required deferred actions, or dangerous blocked actions, but it still does not execute approvals, validation, build/test, commit/push, backup restore/delete, scheduler modification, target app runs, or model/API agents.
- TASK-DEVO-072 adds the first controlled UI v2 workspace-safe actions through `POST /api/actions/execute`. The only executable actions are generating a work scope template, generating a work-package visual, generating a project activity visual, and writing an onboarding report. Each requires explicit confirmation and writes Devo workspace artifacts only; target repositories, approvals, validation/build/test, Git delivery, backup restore/delete, scheduler controls, target app runs, and model/API agents remain unavailable in the UI.
- TASK-DEVO-073 adds `work.new.create` to the controlled UI action executor. The Action Safety page can now create a Devo run/work-package draft, use an explicit lane or project default lane, optionally generate the scope template, and return a resume command. This writes Devo workspace artifacts only and does not modify target repositories or add approval/build/test/commit/push/restore/scheduler/model controls.
- TASK-DEVO-073A adds `docs/devo-company-model.md` to define the long-term Devo vision as a local software-development company operating system around AI workers. It documents the company-role analogy, current deterministic responsibility model, future agent contract/worker backend model, Codex CLI default worker strategy, final brief-to-blueprint-to-backlog-to-batch-to-Codex workflow, and deferred AI API/general chat/SaaS scope.
- TASK-DEVO-073B adds `docs/remaining-roadmap.md` as the active remaining roadmap. It prioritizes Project Brief, Blueprint, Backlog, Batch, Progress, Execution Queue, and Codex handoff work before broader UI actions, direct API agents, or PersonalOS feature work.
- TASK-DEVO-074 adds deterministic Project Brief and Blueprint planning artifacts under `workspace/projects/<project>/planning/`, plus `devo project brief-*` and `devo project blueprint-*` commands, read-model planning summary fields, read-only API endpoints for brief/blueprint, and a read-only dashboard Planning card. This does not add backlog/tasks/batches, AI API calls, Codex CLI automation, or target project mutation.
- TASK-DEVO-075 adds deterministic Backlog and Task planning artifacts under `workspace/projects/<project>/planning/`, plus `devo project backlog-*` and `devo project task-*` read commands, read-model backlog counts, read-only API endpoints for backlog/tasks, and dashboard Planning card backlog counts. This does not add batches, execution queue, AI API calls, Codex CLI automation, implementation approval, or target project mutation.
- TASK-DEVO-076 adds `devo project backlog-prompt`, `devo project backlog-validate`, and `devo project backlog-import`. Devo can now generate a Codex-ready planning handoff prompt under `workspace/projects/<project>/planning/backlog-refinement-prompt.md`, validate refined backlog JSON, and import it as a draft backlog. This does not call Codex, call AI APIs, approve implementation, create batches, create an execution queue, or modify target projects.
- TASK-DEVO-077 adds Project Batch planning artifacts under `workspace/projects/<project>/planning/batches/`, plus `devo project batch-create`, `batch-suggest`, `batch-list`, `batch-show`, `batch-review`, and `batch-approve`. Batch selection is deterministic and workspace-only; batch approval is planning approval only and does not run Codex, create an execution queue, approve implementation, run validation, commit, push, or modify target projects.
- TASK-DEVO-078 adds deterministic planning progress summaries with `devo project progress` and `--json`, derived from Project Brief, Blueprint, Backlog/Task, and Batch artifacts. Progress reports count-based task completion, backlog readiness, blocked percentage, batch completion, milestone/epic rollups, read-model/API fields, and a read-only dashboard Progress card. Weighted scoring, execution queue progress, Codex execution tracking, AI/API automation, and target project mutation remain deferred.
- TASK-DEVO-079 adds execution queue state tracking under `workspace/projects/<project>/planning/queues/`, plus `devo project queue-create`, `queue-list`, `queue-show`, `queue-start`, `queue-next`, `queue-complete-item`, `queue-block-item`, `queue-pause`, and `queue-resume`. Queues are created from approved planning batches only and track deterministic state transitions without running Codex, running validation/Git commands, or modifying target project source.
- TASK-DEVO-080 adds Codex handoff prompt artifacts under `workspace/projects/<project>/planning/handoffs/`, plus `devo project handoff-next`, `handoff-task`, `handoff-batch`, `handoff-list`, `handoff-show`, and `handoff-mark-used`. Handoffs package queue/batch/task scope, acceptance criteria, validation expectations, safety boundaries, files not to stage, and final report expectations into a prompt the user manually pastes into Codex. Devo still does not run Codex, call AI APIs, execute target commands, run validation, commit, push, or modify target project source.
- TASK-DEVO-081 adds a read-only Planning Intake dashboard page. It shows the brief -> blueprint -> backlog -> batch -> queue -> handoff -> progress workflow as an operator-oriented pipeline with status/count summaries, artifact/path context when available, section-level loading/empty/error states, and copyable CLI commands. It does not create briefs from UI, run Codex, execute target commands, run validation, commit, push, restore, modify schedulers, or call model APIs.
- TASK-DEVO-082 adds read-only Blueprint and Backlog dashboard pages. Blueprint shows status, title, vision, architecture notes, risks, validation strategy, open questions, milestones, epics, linked epics, progress rollups, artifact paths, and copyable CLI guidance. Backlog shows counts, readiness/blocked percentages, refinement prompt status, task filters by status/lane/risk/search, and selected-task detail with summary, acceptance criteria, validation expectations, allowed/forbidden scope, dependencies, notes, and source. These pages do not create, approve, or import artifacts from UI; they do not run Codex, execute target commands, run validation, commit, push, restore, modify schedulers, or call model APIs.
- TASK-DEVO-083 adds read-only Batch, Queue, Handoff, and Progress dashboard pages. Batch shows batch counts, approval status, risk/lane summaries, dependency warnings, review notes, and task snapshots. Queue shows queue counts, item status, pause/resume metadata, acceptance criteria, validation expectations, and notes. Handoff shows Codex handoff metadata and prompt paths. Progress shows project/backlog/batch completion bars, task/batch/queue counts, milestone/epic progress, warnings, next action, and copyable CLI guidance. These pages do not create, approve, review, start, resume, execute, validate, commit, push, restore, modify schedulers, edit target files, run Codex, execute target commands, or call model APIs.
- TASK-DEVO-084 adds explicit planning Batch approval artifacts under `workspace/projects/<project>/planning/batches/approvals/`, plus `devo project batch-approval-request`, `batch-approval-show`, `batch-approval-list`, enhanced `batch-review --needs-changes`, enhanced `batch-approve --note`, and `batch-reject`. Approval artifacts record review status, decision notes, task/risk/lane/dependency/scope/validation summaries, and next action. Read models/API/UI visibility now expose approval counts and latest approval/review state, and the controlled UI action safety model supports confirmed workspace-only batch approval/review actions. Batch approval remains planning approval only and does not create queues, run Codex, execute target commands, run validation, commit, push, restore, modify schedulers, edit target files, or call model APIs.
- TASK-DEVO-085 dogfoods the full planning pipeline on DevOrchestrator itself and records the result in `docs/dogfood/devo-pipeline-dogfood-085.md`. The run validated brief, blueprint, backlog, batch suggestion, batch approval/review, queue state, handoff prompt generation, and progress reporting. It found several small operator-friction issues: BOM-prefixed brief input can crash Windows console output, `backlog-approve` next-action guidance is stale, and `queue-next` prints a placeholder handoff command instead of the actual project/queue ids. Generated planning artifacts remain workspace-only and were not committed.
- TASK-DEVO-086 fixes the main TASK-DEVO-085 dogfood friction: BOM-prefixed planning text inputs are handled safely for brief creation, starter backlog CLI/Markdown guidance now warns that deterministic backlogs are not implementation-ready by default, backlog approval points to real `batch-suggest --limit 10` commands, queue-next handoff guidance uses concrete project/queue ids, and UI verification docs clarify that `devo ui status` only checks reachability unless the local API/UI servers are running.
- TASK-DEVO-087 adds `docs/codex-worker-adapter-design.md` as the design-only plan for a future Codex CLI/Desktop worker adapter. It documents manual handoff as Mode 0, assisted handoff/report import, supervised local Codex runs, one-at-a-time queue worker integration, future multi-worker agents, worker run storage under `workspace/projects/<project>/workers/codex/`, conservative queue state transitions, separate planning/execution/delivery/safety approvals, usage-limit pauses, validation/review handling, proposed future CLI commands, UI visibility, rollout tasks, and deferred autonomous/API-agent scope.

## Readiness Estimate

- Practical personal-use Devo after TASK-DEVO-073B: around 65-70% complete.
- Long-term ideal Devo, including dashboard maturity and optional worker/model adapters: around 40-45% complete.

The latest personal-use completion target was brief intake, blueprint/backlog, batch approval, Codex handoff, progress tracking, UI progress visibility, and one dogfood end-to-end run. That target is now dogfooded; Devo is around 80-85% complete for personal use, with the next gap being operator guidance polish rather than new planning primitives.

DevOrchestrator can execute registered low/medium validation commands with safety gates, dry-run high-risk target commands, summarize Git delivery readiness, refresh project context, generate project/run/handoff reports, run read-only doctor and project onboarding checks, store project workflow defaults, save/show current project/run context, bootstrap scoped work packages across multiple built-in lanes, generate lane-aware scope templates, resume work packages with compact operator plans, bundle related approvals without bypassing child approval records, generate next-action and phase-specific work-package prompts, mark work packages delivered with final commit/validation/git evidence, summarize recent work/project activity, generate Codex-ready handoff prompts from planning queue/batch/task artifacts without running Codex, expose UI-ready JSON read models and a local read-only API server, provide a polished read-only React/Vite dashboard MVP with read-only Planning Intake, Blueprint, Backlog, Batch, Queue, Handoff, and Progress pages, document the future local UI/API architecture and first read-only dashboard MVP, generate Mermaid workspace visual reports from structured data, and complete a manual-assisted end-to-end dogfood run.

The next product step should focus on the planning pipeline in `docs/remaining-roadmap.md`. PersonalOS should be used occasionally for controlled dogfood batches that validate Devo behavior, not as the main development focus.

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
- TASK-DEVO-062 current-context shortcuts
- TASK-DEVO-063 UI-ready read models
- TASK-DEVO-064 UI/API architecture and safety model
- TASK-DEVO-065A UI MVP specification
- TASK-DEVO-065B local read-only API server
- TASK-DEVO-066 React/Vite UI scaffold
- TASK-DEVO-067 read-only dashboard MVP
- TASK-DEVO-070 UI launch/status helpers
- TASK-DEVO-071 controlled UI action safety model
- TASK-DEVO-072 first workspace-safe UI actions
- TASK-DEVO-073 controlled UI work bootstrap action
- TASK-DEVO-073A Devo company-model vision
- TASK-DEVO-073B remaining roadmap reprioritization
- TASK-DEVO-074 Project Brief and Blueprint planning artifacts
- TASK-DEVO-075 Backlog and Task planning artifacts
- TASK-DEVO-076 backlog refinement handoff prompt
- TASK-DEVO-077 planning batch model and selection
- TASK-DEVO-078 planning progress summaries
- TASK-DEVO-079 execution queue state machine
- TASK-DEVO-080 Codex handoff prompts for next task/batch
- TASK-DEVO-081 UI Planning Intake page
- TASK-DEVO-082 UI Blueprint and Backlog pages
- TASK-DEVO-083 UI Batch Queue and Progress dashboard
- TASK-DEVO-084 batch approval/review workflow
- TASK-DEVO-085 end-to-end planning pipeline dogfood run
- TASK-DEVO-086 planning pipeline guidance and input robustness
- TASK-DEVO-087 Codex CLI worker adapter design

## Recovery Pointers

If chat context is lost, start here:

1. Read this file.
2. Read `docs/devo-vision.md`.
3. Read `docs/devo-company-model.md`.
4. Read `docs/remaining-roadmap.md`.
5. Read `docs/codex-worker-adapter-design.md` before worker adapter work.
6. Read `docs/current-capabilities.md`.
7. Read `docs/agent-workflow.md`.
8. Read `docs/ui-architecture.md` when continuing UI/API planning.
9. Read `docs/ui-mvp-spec.md` when continuing dashboard MVP planning.
10. Read `docs/roadmap.md`.
11. Read `docs/operating-model.md`.
12. Run `scripts/recovery/check-devo-recovery-status.ps1` from `E:\DevOrchestrator`.
13. Run `devo report handoff --project DevOrchestrator` or `devo report project --project DevOrchestrator` for a compact state summary.
14. For active work, run `devo report run --project DevOrchestrator --run <runId>` when a run id is known.
15. Continue from the latest planned next task.
