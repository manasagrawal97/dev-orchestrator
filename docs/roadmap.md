# DevOrchestrator Roadmap

## Current Priority

Devo itself is the main product priority now. PersonalOS is lower priority as an application target and should mainly be used as a real-world dogfood project for Devo workflows.

The near-term strategy is CLI-first and local-first:

- mature Devo's CLI workflow before starting a dashboard
- let Codex/Desktop/CLI remain the AI worker
- use Devo CLI for workflow, approvals, validation, delivery, reports, history, and generated visuals
- avoid requiring direct OpenAI, Claude, Gemini, or local model API tokens for current development
- keep manual/Codex mode supported even after future model adapters exist

The active remaining roadmap is now `docs/remaining-roadmap.md`. It supersedes older isolated task ordering and prioritizes the final workflow: project brief -> blueprint -> backlog -> batch -> execution queue -> Codex handoff -> validation/delivery/progress -> review/resume.

## Immediate Planned Tasks

- TASK-DEVO-088 Worker run/report data model

## Updated Roadmap Phases

### Phase 1: Planning Pipeline Foundation

Add durable Project Brief, Blueprint, Backlog/task, dependency, risk/lane mapping, Batch, and Progress models. This is the next foundation because Devo's final workflow starts with a user-approved brief and turns it into auditable planning artifacts.

### Phase 2: Codex Handoff And Execution Queue

Generate structured Codex handoff prompts, task prompts, and batch prompts from approved planning artifacts. Add the execution queue state machine, pause/resume, usage-limit pause reasons, and blocked task handling. Codex/Desktop/CLI remains the default worker.

The long-term agent model is documented in `docs/devo-company-model.md`, and the future Codex adapter safety design is documented in `docs/codex-worker-adapter-design.md`: Devo owns role contracts and workflow state, while worker backends such as manual operation, Codex CLI, API models, or local models can be attached later. Codex CLI should be the default personal/local worker.

### Phase 3: UI Planning And Progress Pages

Add Planning Intake, Blueprint, Backlog, Batch Queue, Progress dashboard, and Review Batch pages. These pages should visualize Devo's planning and queue state before adding dangerous UI actions.

### Phase 4: Controlled Workflow Actions

Add controlled workflow actions such as create brief, approve blueprint, approve batch, generate Codex prompt, mark task/batch reviewed, request approval bundle, and display validation evidence. Do not add commit, push, build, or test buttons until the safety model matures.

After TASK-DEVO-073B, the next product direction is documented in `docs/remaining-roadmap.md`: brief intake, blueprint/backlog/task generation, batch approval, execution queue, progress tracking, and pause/resume around Codex usage limits. These should extend Devo's company-model workflow rather than turn Devo into a general AI chat clone.

### Phase 5: Worker And Agent Architecture

Keep manual worker mode and Codex CLI handoff mode first-class. Design and add a Codex CLI worker adapter only after manual handoff is solid. Optional OpenAI, Claude, Gemini, local model, or other adapters remain later and cost-controlled.

### Phase 6: Future Polish And Advanced Capabilities

Add persistent read-model snapshots only if needed, better report viewing, better visuals/progress charts, backup page polish, packaging/start-stop improvements, notifications, mobile-friendly UI, and optional general planning chat.

## Readiness Target

DevOrchestrator is currently aimed at CLI product maturity, not "ready for PersonalOS feature work" as the main milestone. PersonalOS remains useful for dogfood validation when Devo needs a real target project.

CLI maturity means:

- Devo can start, guide, validate, complete, list, and recover work packages
- approvals and validation are clear without repeated long prompts
- generated reports and visuals make recent work understandable
- recovery/handoff after crashes is boring and deterministic
- target project work remains tightly scoped and auditable

## Rough Remaining Effort

- CLI product maturity remaining: around 12-25 focused hours.
- Dashboard and direct-agent phases: later, after CLI workflows are genuinely smooth.

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

### TASK-DEVO-053B Generated Visual Reports - Completed

Added `devo visual work-package` and `devo visual project-activity` to generate compact Mermaid Markdown artifacts under `workspace/` from structured Devo run, work-package, validation, approval, and delivery data. Static Mermaid docs remain for stable concepts; generated visual reports cover live/current activity and create a bridge toward a future dashboard that can reuse the same data model.

### TASK-DEVO-054A CLI-First Devo Roadmap - Completed

Documented the updated strategic priority: Devo itself is the main product focus, PersonalOS is primarily a real-world validation target, current work should stay CLI-first/local-first, dashboard/UI comes later, and direct API/model agents are optional future scope with manual/Codex mode preserved.

### TASK-DEVO-055 Doctor Health Checks - Completed

Added `devo doctor` and `devo doctor --project <project>` as compact read-only health checks. Doctor reports `OK`, `WARN`, `FAIL`, and `SKIP` categories for Devo workspace health, project registration/path/Git status, validation registry, recent work packages, latest validation, generated visuals, backup inventory, scheduled backup task status when safely checkable, overall status, and one suggested next action.

### TASK-DEVO-056 Work Package Scope Templates - Completed

Added `devo work scope-template` so draft work packages can generate lane-aware scope Markdown before import. The template includes required `import-scope` sections, `low-risk-ui-maintenance` allowed/forbidden defaults, validation command guidance that prefers registered `dotnet-build-personalos`, stop conditions, approval bundle notes, and final report expectations. `devo work next` and `devo work status` now suggest scope-template at draft stage, and `devo work scope-example --lane low-risk-ui-maintenance` provides a reference scope without requiring a real project.

### TASK-DEVO-057 Built-In Work Lanes - Completed

Added built-in lanes for `docs-only`, `warning-cleanup`, `small-bugfix`, `small-feature`, `test-only`, `backup-maintenance`, and `devo-internal-source` while preserving `low-risk-ui-maintenance`. Scope templates and examples now use lane-specific allowed/forbidden/default validation guidance, `devo work lanes` lists all lane rules, and `devo work lane-show --lane <lane>` shows one lane compactly. Lanes help prepare scope but do not bypass approval bundles, validation policy checks, or explicit risk approval.

### TASK-DEVO-058 Work Resume Guidance - Completed

Added `devo work resume --project <project> --run <runId>` as the compact continuation command for work packages. Resume reads package state, lane, imported scope, approval bundle status, latest validation evidence, and latest Git delivery evidence, then prints the next phase, recommended commands, Codex operator instructions, stop conditions, and final report expectations. The simplified package loop is now `work start -> work resume`, with resume guiding scope, approval, implementation, validation, delivery, and completion phases.

### TASK-DEVO-059 One-Command Work Bootstrap - Completed

Added `devo work new --project <project> --goal "<goal>" --lane <lane>` to create the run, start the work package, generate `scope-template.md` by default, and print the resume command in one flow. The simplified start path is now `work new -> fill scope template -> import-scope -> request approval bundle -> work resume`, while lower-level `run create`, `work start`, and `scope-template` remain available for manual control.

### TASK-DEVO-060 Project Workflow Settings - Completed

Added `devo project settings-show` and `devo project settings-set` so each registered project can store workflow defaults in Devo workspace metadata. Settings include default lane, default validation command, default full-test command, default branch, automatic scope-template behavior, delivery mode, and notes. `devo work new` now allows `--lane` to be omitted when `default_lane` is configured, and `devo doctor --project` checks settings readability, default lane validity, configured validation command IDs, and default branch mismatch when Git branch information is available.

### TASK-DEVO-061 Guided Project Onboarding - Completed

Added `devo project onboard --project <project>` as a read-only setup/status checklist. It reports registration, project path, scan, context status, validation registry, project settings, doctor summary, onboarding overall status, and the next setup command. `--suggest-settings` prints a suggested settings command without writing it, and `--write-suggestions` writes `workspace/projects/<project>/reports/onboarding-report.md` without modifying the target project. This reduces setup friction before `devo work new`.

### TASK-DEVO-062 Current Context Shortcuts - Completed

Added `devo current`, improved `devo use` output, and taught common project/work/visual commands to use saved current project/run context when `--project` or `--run` are omitted. Shortcuts now cover the prioritized work-package commands (`resume`, `status`, `next`, `scope-template`, `prompt`, `request-approval-bundle`, `complete`), `work new`, project onboarding/settings/activity, `doctor`, and generated visual reports. Commands print when current context is used and fail with clear `devo use` guidance when context is missing.

### TASK-DEVO-063 UI-Ready Read Models - Completed

Added `src/devo/read_models.py` with read-only project, run, and work-package overview models that tolerate missing/older artifacts. Added JSON output for `devo project overview`, `devo project activity --json`, `devo work status --json`, and `devo doctor --json`. This creates a stable bridge for a future UI, local API server, or agent integration without building a dashboard yet. Future UI work should consume these read models/API responses rather than scraping raw workspace folders.

### TASK-DEVO-064 UI/API Architecture Plan - Completed

Added `docs/ui-architecture.md` to define the future UI/API architecture before UI implementation. The plan keeps Devo core in Python, recommends a local-only read-only FastAPI server before write actions, recommends a React/Vite dashboard after the API/read-model contract is stable, explains why Blazor should not be Devo's first UI stack, previews read-only endpoints backed by `ProjectOverview`, `RunOverview`, and `WorkPackageOverview`, and documents the safety model for future controlled actions.

### TASK-DEVO-065A UI MVP Specification - Completed

Added `docs/ui-mvp-spec.md` to define the first UI before implementation. The MVP is a local read-only dashboard with Projects, Project Overview, Work Package/Run Detail, Activity/History, and Health pages. It defines reusable status and summary components, maps pages to future read-model/API endpoints, includes simple wireframes, allows only read-only actions such as refresh/select/copy/open report paths, and explicitly defers approvals, build/test execution, commit/push, backup restore/delete, scheduler management, target project edits, autonomous agents, and cloud/multi-user scope.

### TASK-DEVO-065B Local Read-Only API Server - Completed

Added `src/devo/api.py` with a FastAPI app factory and local read-only JSON endpoints for health, current context, registered projects, project overview, project activity, doctor, run overview, and work-package overview. Added `devo api serve` with default host `127.0.0.1`, non-local host blocking for MVP safety, and `devo api routes` for endpoint discovery. This is the backend bridge for the future UI and does not add frontend code or write/action endpoints.

### TASK-DEVO-066 React UI Scaffold - Completed

Added the first React/Vite/TypeScript frontend scaffold under `ui/`. The scaffold consumes the local read-only API, defaults to `http://127.0.0.1:8765`, can be started with `npm run dev`, and includes a read-only dashboard shell with Projects, Project Overview, Work Package, Activity, and Health navigation. Projects and Health make live read-only API calls; the other pages are placeholders for the next dashboard implementation. No write/action UI, approval buttons, validation/build/test controls, commit/push controls, backup restore/delete controls, scheduler controls, target app execution, or model/API calls were added.

### TASK-DEVO-067 Read-Only Dashboard MVP - Completed

Expanded the React/Vite scaffold into a useful read-only dashboard. Projects, Project Overview, Work Package, Activity, and Health pages now consume the local API/read models, show loading/error/empty states, expose status badges, summary cards, current context, project settings, Git/validation/backup summaries, recent runs/work packages, activity/history, doctor checks, lifecycle state, stop conditions, suggested next actions, optional JSON details, and copyable CLI commands. The dashboard still has no approval buttons, validation/build/test execution, commit/push controls, backup restore/delete controls, scheduler controls, target project edits, app runs, or model/API calls.

### TASK-DEVO-068 Dashboard Loading And Layout Polish - Completed

Polished the read-only dashboard with calmer visual spacing, more readable section hierarchy, section-level loading hints for slow overview/doctor/activity-backed views, clearer dashboard selection versus CLI current context labels, quieter Activity report/context lists, and a better missing work-package empty state with safe CLI commands. The API now emits an `X-Devo-Elapsed-Ms` response header for lightweight endpoint timing during future profiling. DB-backed read-model caching and snapshot caching are intentionally deferred.

### TASK-DEVO-069 Read-Model/API Performance Profiling - Completed

Added opt-in `include_timing=true` JSON timing metadata for project overview, doctor, and activity endpoints while keeping default responses unchanged. Bounded optional doctor scheduled-task checks, added a timeout for non-mutating Git reads, removed a duplicate doctor call from project overview onboarding status, and reused loaded run/validation data during activity summary generation. Persistent DB/SQLite caching was not added; a future workspace JSON snapshot cache can be considered only if profiling shows it is still needed.

### TASK-DEVO-070 UI Launch And Status Helpers - Completed

Added `devo ui info`, `devo ui urls`, `devo ui status`, and `devo ui open` for safer local dashboard ergonomics. The helpers print local URLs, manual start commands, read-only safety notes, short-timeout reachability checks, and browser-open guidance. They do not start servers, stop processes, mutate workspace state, run validations/builds/tests, or add dashboard write actions. Start/stop scripts are deferred until process matching can be made narrow and boring.

### TASK-DEVO-071 Controlled UI Action Safety Model - Completed

Added `src/devo/ui_actions.py` with UI action categories for `read_only`, `workspace_safe`, `approval_required`, and `dangerous_deferred`. The local API now exposes read-only action metadata through `/api/actions`, `/api/actions/allowed`, and `/api/actions/{action_id}`, and the dashboard has an informational Action Safety page. UI v1 still does not execute actions; it only explains which actions are available as read-only views, which workspace-only actions may be UI v2 candidates, and which approval, validation, Git delivery, restore/delete, scheduler, target app, and model/API actions are deferred or blocked.

### TASK-DEVO-072 First Workspace-Safe UI Actions - Completed

Added `POST /api/actions/execute` for four confirmed workspace-only actions: generate work scope template, generate work-package visual, generate project activity visual, and write onboarding report. The Action Safety dashboard page now exposes controls only for those actions, requires project/run inputs where needed, and requires confirmation that the action writes Devo workspace artifacts only. Approval, validation/build/test, commit/push, backup restore/delete, scheduler modification, target app run, and model/API actions remain blocked or deferred.

### TASK-DEVO-073 UI Work Bootstrap Action - Completed

Added `work.new.create` to the controlled UI action executor. The dashboard can now create a Devo run/work-package draft from the Action Safety page, using an explicit lane or the project's default lane, and can generate the initial scope template unless the user disables it. The action returns the run id, lane, optional scope-template path, and `devo work resume` command. It writes Devo workspace artifacts only and does not modify target repositories or add approval, validation/build/test, Git delivery, restore/delete, scheduler, target app, or model/API execution.

### TASK-DEVO-073A Company-Model Vision - Completed

Added `docs/devo-company-model.md` to define Devo as a local software-development company operating system around AI workers, not a Codex/Cursor/Claude Code replacement. The doc maps company roles to Devo roles, explains current deterministic responsibility separation, defines future agent contracts versus worker backends, records Codex CLI as the default personal/local worker strategy, describes the final brief-to-blueprint-to-backlog-to-batch-to-Codex workflow, and explicitly defers general AI chat, paid API agents by default, autonomous unapproved execution, and public SaaS/multi-user deployment.

### TASK-DEVO-073B Remaining Roadmap Reprioritization - Completed

Added `docs/remaining-roadmap.md` as the durable source of truth for the remaining product sequence. The roadmap centers Devo on project brief intake, blueprint/backlog/task models, batch selection, execution queue state, Codex handoff prompts, progress tracking, planning/progress UI pages, and later worker adapters. It intentionally deprioritizes PersonalOS feature work, general AI chat, direct API agents, autonomous unapproved execution, risky UI action buttons, scheduler/backup mutation UI, public SaaS, and persistent DB caching unless performance demands it.

### TASK-DEVO-074 Project Brief And Blueprint Planning - Completed

Added the first planning pipeline artifacts: Project Brief and Blueprint. Devo can now create, show, and approve a brief from a local Markdown/text file, create a deterministic draft blueprint from that brief, show and approve the blueprint, expose planning status in ProjectOverview/read-only API responses, and show a read-only Planning card in the dashboard. This stores Devo workspace artifacts only and does not implement backlog/tasks/batches, direct AI/API calls, Codex CLI automation, or target repository mutation.

### TASK-DEVO-075 Backlog And Task Planning - Completed

Added deterministic Backlog and Task planning artifacts derived from blueprint milestones/epics. Devo can now create, show, and approve a backlog, list backlog tasks, show one task, expose backlog/task JSON through read-only API endpoints, include backlog counts in ProjectOverview, and show those counts in the dashboard Planning card. This is a template-based starter backlog only; TASK-DEVO-076 should add a Codex handoff prompt for intelligent backlog refinement. Batches and execution queue remain future work.

### TASK-DEVO-076 Backlog Refinement Handoff - Completed

Added `devo project backlog-prompt` to write a Codex-ready planning prompt containing the project brief, blueprint, current backlog, lane/risk guidance, task schema, output JSON example, and explicit planning-only safety rules. Added `devo project backlog-validate` and `devo project backlog-import` so refined backlog JSON can be checked and imported as a draft backlog. ProjectOverview and the read-only API expose prompt metadata, and the dashboard Planning card shows whether the refinement prompt exists. Devo still does not call Codex, call AI APIs, approve implementation, create batches, create an execution queue, or modify target repositories.

### TASK-DEVO-077 Batch Model And Selection - Completed

Added Project Batch planning artifacts under `workspace/projects/<project>/planning/batches/`, with JSON/Markdown batch files and `batch-index.json`. Devo can create a draft batch from explicit task ids, suggest ready lower-risk tasks from the backlog, optionally write the suggestion as a draft batch, list/show/review/approve batches, expose batch summary fields in `ProjectOverview`, expose read-only batch API endpoints, and show batch counts in the dashboard Planning card. Batch approval is planning approval only; Devo still does not create an execution queue, call Codex, call AI APIs, approve implementation execution, run validation, commit, push, or modify target repositories.

### TASK-DEVO-078 Planning Progress Summaries - Completed

Added deterministic count-based progress summaries derived from Project Brief, Blueprint, Backlog/Task, and Batch artifacts. `devo project progress` and `--json` report task completion, backlog readiness, blocked percentage, batch completion, milestone progress, epic progress, warnings, and next action. ProjectOverview, the read-only API, and the dashboard Project Overview page expose progress summary fields. Weighted scoring, execution queue progress, Codex execution tracking, direct AI/API usage, and target repository mutation remain deferred.

### TASK-DEVO-079 Execution Queue State Machine - Completed

Added execution queue artifacts under `workspace/projects/<project>/planning/queues/`, with JSON/Markdown queue files and `queue-index.json`. Queues are created from approved planning batches only and support deterministic state transitions for ready, running, paused for usage limits, paused for failure/review, blocked, and completed work. `devo project queue-*` commands can create, list, show, start, inspect next item, complete items, block items, pause, and resume queues. This is state tracking only: Devo still does not run Codex, call AI APIs, execute generated prompts, run validation/Git commands, commit, push, or modify target repositories.

### TASK-DEVO-080 Codex Handoff Prompts - Completed

Added Codex handoff artifacts under `workspace/projects/<project>/planning/handoffs/`, with JSON/Markdown handoff files and `handoff-index.json`. `devo project handoff-next`, `handoff-task`, and `handoff-batch` generate Codex-ready prompts from queue items, backlog tasks, or planning batches, while `handoff-list`, `handoff-show`, and `handoff-mark-used` provide read/workspace-only tracking. Handoff prompts include project path, source queue/batch/task details, lane/risk, dependencies, acceptance criteria, validation expectations, allowed/forbidden scope, safety boundaries, files not to stage, and final report expectations. Devo still does not run Codex, call AI APIs, execute target commands, run validation, commit, push, or modify target repositories.

### TASK-DEVO-081 UI Planning Intake Page - Completed

Added a read-only Planning Intake page to the React/Vite dashboard. The page visualizes the brief -> blueprint -> backlog -> batch -> queue -> handoff -> progress workflow as a pipeline, shows status/count summaries from existing read-only API endpoints, surfaces artifact/path context when available, and provides copyable CLI commands for each stage. It has section-level loading, empty, and error states and does not add UI controls for creating briefs, approving artifacts, running Codex, executing target commands, validation/build/test, commit/push, backup restore/delete, scheduler modification, target source edits, or model/API calls.

### TASK-DEVO-082 UI Blueprint And Backlog Pages - Completed

Added dedicated read-only Blueprint and Backlog pages to the React/Vite dashboard. Blueprint uses existing API responses to show blueprint status, vision, architecture notes, risks, validation strategy, open questions, milestones, linked epics, and milestone/epic progress rollups. Backlog shows backlog counts, readiness and blocked percentages, refinement prompt status, task filters by status/lane/risk/search, and a selected-task detail panel with acceptance criteria, validation expectations, allowed/forbidden scope, dependencies, notes, and source. The pages add copyable CLI guidance only and do not create, approve, import, execute, validate, commit, push, restore, modify schedulers, edit target files, or call model APIs.

### TASK-DEVO-083 UI Batch Queue And Progress Dashboard - Completed

Added detailed read-only Batch, Queue, Handoff, and Progress pages to the React/Vite dashboard. Batch pages show batch lists, selected batch detail, approval status, risk/lane summaries, dependency warnings, review notes, and task snapshots. Queue pages show queue lists, selected queue detail, item state, pause/resume metadata, acceptance criteria, validation expectations, and notes. Handoff pages show handoff metadata, source queue/batch/task/item fields, prompt paths, and handoff CLI guidance. Progress shows project/backlog/batch progress bars, task/batch/queue counts, milestone/epic progress, warnings, and next action. These pages remain inspection/operator guidance only and do not create/approve/review/start/resume queues, run Codex, execute target commands, validate, commit, push, restore, edit target files, modify schedulers, or call model APIs.

### TASK-DEVO-084 Batch Approval And Review Workflow - Completed

Added explicit workspace-only Batch approval artifacts under `workspace/projects/<project>/planning/batches/approvals/`. Devo can request batch approval, show/list approval artifacts, record reviewed or needs-changes notes, approve planning with decision notes, and reject planning without deleting batches or mutating backlog/tasks. Approval artifacts summarize task scope, high-risk task count, dependency warnings, risk/lane counts, validation expectations, decision notes, and next suggested command. ProjectOverview/read-model/API responses expose latest batch approval/review status and approval counts, the Batches UI shows approval metadata, and the controlled UI action safety model supports confirmed workspace-safe batch approval/review actions only. Batch approval remains planning approval; queue creation, Codex handoff, validation, commit, push, target project edits, restore, scheduler changes, and model/API calls remain separate or deferred.

### TASK-DEVO-085 End-To-End Planning Pipeline Dogfood - Completed

Ran the current planning pipeline on DevOrchestrator itself and documented the results in `docs/dogfood/devo-pipeline-dogfood-085.md`. The dogfood run created and approved a Project Brief, Blueprint, Backlog, suggested Batch `B001`, Batch approval artifact, execution Queue `Q001`, Codex handoff `H001`, and progress summary. Generated planning artifacts stayed under `workspace/` and were not committed. Findings: BOM-prefixed brief input can trigger Windows console rendering failures, `backlog-approve` still prints stale batch guidance, `queue-next` prints placeholder handoff commands, and the deterministic starter backlog needs clearer reminders before real implementation. TASK-DEVO-086 should address these operator-friction issues before a larger Codex CLI worker adapter design task.

### TASK-DEVO-086 Planning Pipeline Guidance And Input Robustness - Completed

Fixed the main TASK-DEVO-085 dogfood friction before adding new workflow features. Brief creation now reads planning text with UTF-8 BOM handling and strips BOM markers before storing/rendering summaries. Starter backlog CLI output and generated `backlog.md` now warn that deterministic backlogs are not implementation-ready by default and point to `backlog-prompt`/`backlog-import` before batch creation. `backlog-approve` now suggests concrete `batch-suggest --limit 10` commands, and `queue-next` now prints actual project/queue/task handoff commands instead of placeholders. UI verification docs now clarify that `devo ui status` is a reachability check and browser page review requires the local API/UI servers to be running.

### TASK-DEVO-087 Codex CLI Worker Adapter Design - Completed

Added `docs/codex-worker-adapter-design.md` to define the future Codex CLI/Desktop worker adapter before implementation. The design keeps manual handoff as Mode 0, then stages assisted report import, supervised local Codex worker runs, one-at-a-time queue worker integration, and later multi-worker adapters. It defines conceptual worker input/output fields, workspace-only storage under `workspace/projects/<project>/workers/codex/`, conservative queue state mapping, usage-limit pause handling, validation/review requirements, separate planning/execution/delivery/safety approvals, proposed future CLI commands, UI visibility, rollout tasks TASK-DEVO-088 through TASK-DEVO-095, and explicitly deferred autonomous/API-agent scope.

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

- Devo product maturity comes before PersonalOS feature work.
- Keep Devo deterministic first.
- Stay CLI-first and local-first until the workflow is smooth.
- Preserve target project safety.
- Avoid AI API integration until CLI/manual workflows are proven and cost controls are clear.
- Keep web UI read-only until CLI workflows, generated reports, structured data, and endpoint performance are stable.
- Build toward project brief, blueprint, backlog, task, batch, queue, and progress concepts before general chat or direct API agents.
- Prefer explicit approval records and evidence over implicit automation.
- Reduce user friction with work packages, lanes, approval bundles, compact operator prompts, history, activity, and recovery before adding direct model adapters.
