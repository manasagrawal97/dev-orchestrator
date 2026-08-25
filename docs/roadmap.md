# DevOrchestrator Roadmap

## Current Priority

Devo itself is the main product priority now. PersonalOS is lower priority as an application target and should mainly be used as a real-world dogfood project for Devo workflows.

The near-term strategy is CLI-first and local-first:

- mature Devo's CLI workflow before starting a dashboard
- let Codex/Desktop/CLI remain the AI worker
- use Devo CLI for workflow, approvals, validation, delivery, reports, history, and generated visuals
- avoid requiring direct OpenAI, Claude, Gemini, or local model API tokens for current development
- keep manual/Codex mode supported even after future model adapters exist

Phase 1 MVP is complete and recorded in `docs/phase-1-mvp-checkpoint.md`. The active Phase 2 plan is now `docs/phase-2-autonomy-roadmap.md`. It prioritizes practical autonomy around approved batches, queue work, validation, and trusted local delivery rather than direct Codex/sandbox commits.

## Immediate Planned Tasks

- TASK-DEVO-131: worker-result continuation and delivery-request handoff - completed
- TASK-DEVO-132: queue-worker assisted end-to-end dogfood - completed
- TASK-DEVO-133: one-task assisted queue-worker step - completed
- TASK-DEVO-134: batch continuation loop for one task at a time - completed
- TASK-DEVO-137: queue-worker dogfood friction polish - completed
- TASK-DEVO-138: polished assisted dogfood with known-good delivery path - completed
- TASK-DEVO-139: scheduled runner reliability and health self-check - completed
- TASK-DEVO-139A: scheduler health environment-context clarification - completed
- TASK-DEVO-140: approved queue auto-run v1 - completed
- TASK-DEVO-141: worker result evidence schema v1 - completed
- TASK-DEVO-142: lightweight handoff checklist v1 - completed
- TASK-DEVO-143: live 3-5 task assisted queue dogfood - completed
- TASK-DEVO-144: assisted queue recovery and flow polish - completed
- TASK-DEVO-145: Codex worker launch/integration design - completed
- TASK-DEVO-148: Prompt-file Codex worker dogfood - completed
- TASK-DEVO-149: Codex subprocess execution design checkpoint - completed
- TASK-DEVO-150: Codex subprocess configuration and dry-run launcher v1 - completed
- Next: TASK-DEVO-151 One-task Codex subprocess execution v1
- Future live delivery dogfood should use normal PowerShell with `.\.venv\Scripts\devo.exe`; retry real Codex launcher only after readiness

## Updated Roadmap Phases

### Phase 1: Planning Pipeline Foundation - Complete

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

### Phase 1 MVP Checkpoint - Completed

TASK-DEVO-124 records the Phase 1 MVP checkpoint in `docs/phase-1-mvp-checkpoint.md`. After that docs commit is delivered through the trusted runner and the repository is clean, Manas should create and push the `phase-1-mvp` tag from normal PowerShell.

### Phase 2 Autonomy Roadmap - Active

TASK-DEVO-125 adds `docs/phase-2-autonomy-roadmap.md`. TASK-DEVO-126 adds one-shot trusted runner watch mode. TASK-DEVO-127 adds scheduled/background trusted runner management with read-only planning/status, dry-run install, disabled-by-default real installation, and explicit enable/disable/run-now/remove confirmations. TASK-DEVO-128 adds bounded batch execution policies as approval contracts for future queue work. TASK-DEVO-129 adds the first policy-gated queue worker loop, limited to one item and pausing at handoff/worker readiness. TASK-DEVO-130 adds queue-worker lifecycle controls for status, pause, resume, fail, retry, cancel, missing evidence, and policy/item rechecks without adding real Codex automation or delivery bypasses. TASK-DEVO-131 adds evidence-gated queue-worker continuation plus trusted delivery runner request creation after completed worker report, passed review, and passed validation evidence. TASK-DEVO-132 dogfoods that assisted path in a temp project and shows the next gap is command/order ergonomics, not delivery safety. TASK-DEVO-133 adds `devo project queue-worker-step` as a one-command assisted loop that performs exactly one safe queue-worker transition and stops. TASK-DEVO-134 adds `devo project queue-worker-loop`, which repeats those one-step transitions until it reaches worker/review/validation evidence boundaries, pending trusted delivery, policy blockers, terminal states, no eligible item, or max steps. TASK-DEVO-135 adds explicit worker/review/validation evidence intake commands so the loop can be fed without dropping to lower-level worker artifact commands. TASK-DEVO-136 shows partial readiness for a three-task sandbox flow and identifies delivery/wording friction before broader 3-5 task assisted use. TASK-DEVO-137 polishes that friction with clearer evidence next actions, non-passing validation wording, assisted policy language, temp dogfood remote guidance, and runner-watch/latest-request diagnostics. TASK-DEVO-138 reruns the polished flow against a disposable repo with a real local bare remote, proves trusted runner delivery and next-item selection, and records the remaining friction in `docs/dogfood/task-devo-138-polished-assisted-known-good-delivery.md`. TASK-DEVO-139 adds scheduler health classification and drift repair guidance so approved queue auto-run can rely on clear trusted-runner status. TASK-DEVO-139A clarifies that a restricted Codex/sandbox process may report drift even when normal PowerShell reports scheduler healthy, and says to record that as environment visibility mismatch instead of reinstalling repeatedly. TASK-DEVO-140 adds `devo project approved-queue-run`, a policy-first wrapper around the one-task queue-worker loop that requires explicit confirmation, supports dry-run, checks trusted runner scheduler health by default, and still stops at worker/review/validation/delivery/failure boundaries without running real Codex, validation, runner-watch, commit, or push. TASK-DEVO-141 adds a shared worker/review/validation evidence schema so only completed worker evidence plus passed review and validation evidence can advance. TASK-DEVO-142 adds a lightweight worker-boundary checklist that shows scope, acceptance, validation expectations, risk notes, and the worker-result evidence command. TASK-DEVO-143 dogfoods that path across three disposable delivered tasks, and TASK-DEVO-144 adds push-only runner recovery, `approved-queue-run --continue-next`, clearer validation evidence wording, and latest/default `flow-summary` behavior. Phase 2 should continue with CLI dogfood and carefully gated UI controls, not direct AI-agent workers, ECC adoption, parallel editing agents, voice/Jarvis controls, or sandbox commit/push.

TASK-DEVO-145 adds the design-only Codex worker launch/integration plan in `docs/architecture/codex-worker-launch-integration-design.md`. TASK-DEVO-146 implements prompt-file assisted worker preparation for one `waiting_worker` queue-worker run without running Codex, calling AI APIs, recording evidence automatically, validating, committing, pushing, or modifying target repositories. TASK-DEVO-147 adds JSON worker result ingest that preserves the raw result file and records queue-worker worker evidence schema v1 without running Codex, review, validation, delivery, commit, or push. TASK-DEVO-148 dogfoods that prompt-file/manual loop on disposable project `Dogfood148`, proving the prepare -> filled JSON result -> dry-run ingest -> confirmed ingest -> review evidence -> validation evidence -> trusted runner delivery path. TASK-DEVO-149 records the subprocess execution checkpoint and concludes Devo is ready only for a very narrow one-task subprocess v1. TASK-DEVO-150 adds workspace-only subprocess config and `codex-worker-run-preview`, which validates the planned command and preflight state without launching Codex, calling AI APIs, ingesting, reviewing, validating, delivering, committing, or pushing. The recommended next step is TASK-DEVO-151: one-task Codex subprocess execution v1.

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

### TASK-DEVO-107 Delivery Report Preparation - Completed

Added pre-commit delivery report preparation after delivery plan approval. `devo delivery report-prepare` creates JSON/Markdown report drafts from an approved plan, re-checks current readiness, records blocker/warning/safety/validation/review summaries, and proposes the commit message. `devo delivery commit-message` prints only that proposed message for manual use. Read models and read-only API endpoints expose delivery report status, but Devo still does not stage, validate, commit, push, run Codex, run target commands, or modify target repositories through this flow.

### TASK-DEVO-108 Guarded Delivery Commit - Completed

Added the first controlled delivery commit command. `devo delivery commit-preview` shows eligible and blocked files without staging. `devo delivery commit --confirm-commit` requires an approved delivery plan, ready delivery report, fresh blocker-free readiness check, eligible safe files, and explicit confirmation before staging only those files and running `git commit -m`. It writes `delivery-commit-<id>.json` and `.md`, updates the delivery report with the commit hash, and exposes commit metadata through read models/API. It does not push, run validation, run Codex, complete queue/task/worker state, add UI commit buttons, or modify PersonalOS.

### TASK-DEVO-109 Guarded Delivery Push - Completed

Added the first controlled delivery push command. `devo delivery push-preview` shows commit hash, branch, remote, push target, blockers, and warnings without running `git push`. `devo delivery push --confirm-push` requires prior guarded commit metadata, verified remote/branch, commit containment in the current branch, no push blockers, and explicit confirmation before running `git push <remote> <branch>`. It writes `delivery-push-<id>.json` and `.md`, updates the delivery report with push metadata, and exposes push metadata through read models/API. It does not commit, run validation, run Codex, complete queue/task/worker state, add UI push buttons, or modify PersonalOS.

### TASK-DEVO-110 Guarded Delivery Dogfood - Completed

Dogfooded the full delivery flow against `DeliveryDogfood110`, an isolated temporary Git repository with a local bare `origin` remote. The run completed delivery check -> plan -> approval -> report -> commit-preview -> guarded commit -> push-preview -> guarded push. The guarded commit created temp-repo commit `8aff2e40b75881bc147d71641659c028e05a8148`, and the guarded push delivered it to the local bare remote. No delivery commit or delivery push command was run against the live DevOrchestrator repo. The result is documented in `docs/dogfood/devo-delivery-dogfood-110.md`; TASK-DEVO-111 resolves the operator-guidance and readiness-snapshot labeling issues found there.

### TASK-DEVO-111 Delivery Operator Polish And UI Visibility - Completed

Fixed the dogfood friction from TASK-DEVO-110. Delivery next-action text now points from guarded commit to `push-preview` and guarded `push`, and from pushed delivery to `push-show`. Delivery reports now expose readiness snapshot status/time/currentness/note, and committed or pushed reports label the readiness data as historical. The known unreadable global Git ignore warning is kept visible but does not downgrade readiness when Git status and diff checks pass. Added a read-only dashboard Delivery page and Project Overview delivery card showing checks, plans, approvals, reports, commit and push result metadata, blockers, warnings, next actions, and copyable CLI commands only. No UI commit, push, stage, unstage, validation, restore, scheduler, Codex, or target command buttons were added.

### TASK-DEVO-113 Delivery Report Recovery - Completed

Added `devo delivery report-refresh` to recover safely from retryable guarded commit failures. Guarded commit failures now classify common Git errors such as `.git/index.lock` permission denial or stale lock, preserve raw stderr, record retryability on the commit artifact and report, and show recovery guidance in `commit-preview`. `report-refresh` updates the current readiness snapshot without staging or committing; with `--reopen`, it can restore a blocked report to commit-ready only when the linked plan and approval remain approved, current readiness has no blockers, and the report has not already committed or pushed.

### TASK-DEVO-114 Delivery Commit Diagnostics - Completed

Added `devo delivery commit-diagnostics` for read-only investigation of guarded commit failures. Diagnostics reports Git executable/version, target repo, branch/upstream, `.git` and `.git/index` state, `.git/index.lock` presence, current staged/unstaged/untracked files, delivery report/approval status, last failure category/message/retryability, likely causes, and safe next actions. Retryable index-lock failures now point operators to diagnostics first, then `report-refresh --reopen` only after the OS/Git issue is understood or fixed. Optional `--index-lock-probe --confirm-probe` is double-gated and cleans up after itself in isolated diagnostics.

### TASK-DEVO-115 Live Delivery Dogfood Closure - Completed

Closed the first live DevOrchestrator self-delivery dogfood. DEL-0001 delivered the docs-only dogfood note through Devo delivery commands, producing commit `f0e8c0319c135f72973357776cd7c62d6cc8832b` with message `docs: dogfood live delivery flow` and pushing it to `origin/main`. The earlier failures were tied to restricted Codex/sandbox context being unable to create `.git/index.lock`; normal PowerShell as `MS\manas` using `.\.venv\Scripts\devo.exe` could create/remove the lock and complete guarded commit/push. The operating rule is now documented: live delivery commit/push should run from normal PowerShell unless diagnostics prove the current context can create `.git/index.lock`.

### TASK-DEVO-116 Guarded Commit Context Preflight - Completed

Added an automatic `.git/index.lock` preflight inside `devo delivery commit` before staging eligible files. Guarded commit now blocks before `git add` when the lock already exists, when the current process cannot create it, or when cleanup after the probe fails, and records retryable failure metadata with diagnostics, report-refresh, normal-PowerShell, commit-preview, and guarded retry guidance. `commit-preview` remains read-only and UI commit/push buttons remain deferred.

### TASK-DEVO-116A Delivery Secret-Risk False Positive Reduction - Completed

Refined delivery secret-risk classification so documentation files such as `README.md` and `docs/*.md` can mention secret-safety terms, placeholders, redacted examples, `.env`, API keys, and tokens without blocking delivery. High-confidence secret values in docs and secret-bearing paths such as `.env`, `.pem`, `.key`, `.pfx`, and appsettings-like files remain blockers.

### TASK-DEVO-117 Delivery Latest Status Command - Completed

Added `devo delivery latest --project <project>` as a read-only delivery status shortcut. It summarizes current Git status, latest delivery check, latest meaningful non-empty check, latest plan/approval/report, latest commit/push result, latest pushed delivery, and next recommended action. Empty clean checks no longer look like work to deliver; they are reported as no delivery needed.

### TASK-DEVO-118 Trusted Local Delivery Runner - Completed

Added `devo delivery runner-request`, `runner-list`, `runner-show`, and `runner-run`. The request command lets Codex/sandbox write a workspace-only delivery request with an expected changed-file snapshot and one normal PowerShell runner command. The runner command is explicit and confirmation-gated, reuses delivery check, plan, approval, report, commit-preview, guarded commit, push-preview, and guarded push, and blocks on snapshot drift, forbidden paths, secret-risk blockers, staged workspace artifacts, index-lock preflight failures, commit failures, or push failures. It reduces live delivery handoff friction without adding UI commit/push buttons, background services, webhooks, or safety bypasses.

### TASK-DEVO-119 Phase 1 MVP Closure Plan - Completed

Added `docs/phase-1-mvp-closure-plan.md` as the canonical Phase 1 closure definition. The plan summarizes completed capabilities, the proven runner-based delivery workflow, what Phase 1 is not, remaining closure tasks through TASK-DEVO-124, acceptance criteria, manual-intervention reduction, Phase 2 boundaries, audit concerns, risks, and the recommended next task.

### TASK-DEVO-120 Operator Workflow Polish After Trusted Runner - Completed

Enhanced the post-Codex trusted runner handoff. `devo delivery latest` now includes latest runner request/run/commit/push state and runner next action, `devo delivery runner-latest` shows the newest request without manually copying IDs from `runner-list`, `runner-request` prints changed/warning/blocker counts and the exact normal PowerShell command, and successful `runner-run` output clearly reports completion, commit hash, push target, and the next `git status` check.

### TASK-DEVO-121 Vision-To-Batch Intake Polish - Completed

Added planning intake helpers for the rough idea -> Project Brief -> Blueprint -> Backlog -> Batch -> Queue -> Handoff path. `devo project intake-status` gives a compact whole-pipeline status and next command, `intake-next` prints only the next action, `intake-template` prints or writes a standard intake Markdown template, and `intake-prompt` prints or writes a copyable planning prompt seeded with the rough idea and current Devo planning state. These are workspace-only helpers and do not call AI, approve implementation, create queues, run Codex, validate, commit, push, or modify target repositories.

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

### TASK-DEVO-088 Codex Worker Run Tracking - Completed

Added workspace-only Codex worker run records under `workspace/projects/<project>/workers/codex/`, plus `devo worker codex run-create`, `run-list`, `run-show`, `run-status`, and `run-mark-used`. Worker records snapshot source handoff/queue/item/batch/task metadata, allowed/forbidden scope, validation expectations, safety boundaries, status, next action, and placeholder report metadata. Read models, the local API, and the Handoffs dashboard show worker-run summary state read-only. This does not run Codex, call AI APIs, execute target commands, import reports, trust worker output, complete queue/tasks, validate, commit, push, or modify target projects.

### TASK-DEVO-089 Manual Codex Worker Report Import - Completed

Added `devo worker codex report-template`, `report-validate`, `report-import`, `report-show`, and `report-list`. Reports live under `workspace/projects/<project>/workers/codex/reports/` and capture worker-reported status, summary, changed files, validation/tests/commands, optional commit hash, safety warnings, blockers, follow-ups, and notes. Import updates worker-run report metadata and conservative review-oriented next actions only; it does not run Codex, call AI APIs, execute target commands, trust completion, complete queue/tasks, validate, commit, push, or modify target projects. ProjectOverview, the local API, and the Handoffs dashboard expose report status and guidance read-only.

### TASK-DEVO-090 Worker Runs UI Visibility - Completed

Added a dedicated read-only Worker Runs dashboard page. It shows worker run counts, latest state, run list, selected run detail, allowed/forbidden scope, validation expectations, safety boundaries, imported report detail, reported changed files/tests/commands, safety warnings, blockers, follow-ups, related handoff/queue context, and copyable CLI guidance. It adds no Codex execution, report upload/import buttons, target command execution, validation/build/test, commit/push, restore, scheduler controls, model/API calls, or queue/task completion buttons.

### TASK-DEVO-091 Codex Worker Preflight And Run Plans - Completed

Added read-only Codex worker preflight checks and workspace-only run-plan artifacts under `workspace/projects/<project>/workers/codex/run-plans/`. The new `devo worker codex preflight`, `run-plan`, `run-plan-list`, `run-plan-show`, and planning-only `run-plan-approve` commands check linked handoff/prompt readiness, target path existence, worker status, linked metadata, and optional Codex executable presence using safe `PATH` detection only. Run plans store blocked reasons, warnings, safe command previews, approval/preflight state, scope, validation expectations, and next-action guidance. ProjectOverview/read models, API endpoints, and the Worker Runs dashboard expose run-plan/preflight metadata read-only. This still does not run Codex, call AI APIs, execute target commands, validate, commit, push, complete queue/tasks, or modify target projects.

### TASK-DEVO-092 Supervised Codex CLI Execution Prototype - Completed

Added a guarded one-run Codex CLI execution path with `devo worker codex execute-preview`, `devo worker codex execute --confirm-execute`, and `devo worker codex execute-log`. Execution is refused unless the worker run and run plan exist, the run plan is approved, preflight is passed or warnings-only, prompt and target paths exist, Codex is found on `PATH`, and explicit confirmation is supplied. The executor uses `subprocess.run` without `shell=True`, passes the prompt through stdin, writes stdout/stderr logs under `workspace/projects/<project>/workers/codex/logs/`, and updates the worker run cautiously. Successful exit moves the worker to `waiting_review`; output that looks like usage limits or safety/approval blocks maps to paused/blocked states. It does not complete queue/tasks, run validation, commit, push, or trust Codex output as delivery proof. API/read-model/UI updates expose execution metadata read-only and add copyable CLI commands, not UI execute buttons.

### TASK-DEVO-093 Queue-Integrated Codex Worker Flow - Completed

Added `devo worker codex prepare-next --project <project> --queue <queueId>` and read-only `devo worker codex queue-status`. `prepare-next` prepares exactly one current running or next pending queue item by creating/reusing its handoff, creating a linked worker run, creating a run plan, and running preflight without approving or executing anything. Guarded execution now updates linked queue state conservatively: successful exit moves the worker, queue item, and queue to `waiting_review`; failures pause as failure; usage-limit output pauses as usage limit; safety/approval output blocks the item and waits for review. Completion remains explicit with `devo project queue-complete-item` only after review and validation evidence. Read models, API, and read-only UI pages expose linked worker/run-plan/queue status and copyable commands without UI execute buttons.

### TASK-DEVO-094 Worker Review Tracking - Completed

Added workspace-only review artifacts under `workspace/projects/<project>/workers/codex/reviews/` and the commands `devo worker codex review-template`, `review-attach-evidence`, `review-record`, `review-show`, and `review-list`. Reviews record validation evidence, changed-file review, safety review, acceptance criteria review, follow-up items, reviewer decision, and next queue guidance. `review-record --status reviewed_passed` does not complete queue items or backlog tasks; it only records the decision and prints the explicit `queue-complete-item` command. Read models, API endpoints, Queues UI, and Worker Runs UI expose review/validation status read-only.

### TASK-DEVO-095 Review-Gated Queue Completion - Completed

Made `devo project queue-complete-item` review-aware for Codex-linked or waiting-review queue items. Completion is refused by default unless the linked worker review is `reviewed_passed` and validation evidence is not failed. Missing reviews, needs-changes/rejected reviews, and failed validation evidence print review guidance instead of mutating queue/task state. The explicit `--confirm-without-review` override is discouraged, requires a note, and records a warning. Queue status/read models/API/UI now expose completion readiness and blockers read-only.

### TASK-DEVO-096 Supervised Worker Dogfood - Completed

Dogfooded the supervised worker flow against DevOrchestrator with a fake no-op `codex.cmd`, proving the planning -> batch -> queue -> handoff -> worker run -> run plan -> guarded fake execution -> report import -> review evidence -> review-gated completion path end to end. No real Codex CLI was executed and no source files were changed through the worker. The dogfood report is `docs/dogfood/devo-supervised-worker-dogfood-096.md`; follow-ups include fake executable ergonomics, completed queue item evidence visibility, and shorter operator summary commands.

### TASK-DEVO-097 Worker Flow Operator Polish - Completed

Added explicit `--codex-path` support to `devo worker codex preflight`, `run-plan`, `execute-preview`, and guarded `execute --confirm-execute` so controlled dogfood/fake executable runs no longer depend on fragile PATH injection. Run plans now store executable path/source/resolution notes. `queue-status` can inspect a specific `--item` and defaults to the most recently completed item after queue completion, preserving linked worker/report/review evidence visibility. Added read-only `devo worker codex flow-summary` plus API/UI status fields for the compact queue -> handoff -> worker -> run-plan -> report -> review -> completion-readiness view. This still does not run real Codex in tests, add UI execute buttons, auto-run validation, auto-complete queue/task state, commit, push, or modify target projects.

### TASK-DEVO-098 Real Codex Supervised Dry-Run Checklist - Completed

Added `docs/runbooks/real-codex-supervised-dry-run.md`, a safety checklist and operator playbook for the first real Codex supervised worker dry-run through Devo. The runbook requires DevOrchestrator as the first target, no-op/docs-only scope, clean repo and backup health preconditions, explicit preflight/run-plan approval, `execute-preview`, guarded `execute --confirm-execute`, report import, review-gated completion, recovery steps, and success criteria. It documents `PATH` versus `--codex-path` guidance and explicitly excludes PersonalOS, target commands, backup/scheduler changes, validation trust, automatic completion, commit, push, and delivery automation.

### TASK-DEVO-099 First Real Codex Supervised Dry-Run Report - Completed

Attempted the first real Codex supervised worker dry-run through Devo and documented it in `docs/dogfood/devo-real-codex-dry-run-099.md`. The run used a refined DevOrchestrator-only no-op/docs-inspection task, approved batch `B003`, queue `Q003`, handoff `H003`, worker run `WR002`, and run plan `RP003`. Preflight and preview passed, but guarded execution failed before Codex launched because Windows denied `CreateProcess` for the detected WindowsApps Codex executable path. Report import marked WR002 failed, review `REV-WR002` was rejected with failed validation evidence, queue item `QI001` was blocked, and no source files or PersonalOS files were modified. Next work should harden launch path resolution and launch-exception handling before retrying real Codex or designing delivery automation.

### TASK-DEVO-100 Codex Launch Diagnostics - Completed

Hardened the supervised Codex launch path after TASK-DEVO-099. Devo now has `devo worker codex doctor` for read-only executable diagnostics, blocks WindowsApps app execution aliases for guarded execution, stores launch risk/blocker/warning fields in run plans, shows launch diagnostics in preflight and execute-preview, and catches launch-time `PermissionError`, `FileNotFoundError`, and `OSError` failures into failed worker runs with logs and linked queue `paused_failure` state. Tests use fake executables only; no real Codex run was retried.

### TASK-DEVO-101 Real Codex Explicit-Path Retry - Blocked

Attempted to retry the first real Codex supervised dry-run using `devo worker codex doctor` and an explicit non-WindowsApps launcher path. The retry stopped safely before planning/worker execution because every discoverable Codex command still resolved to the blocked WindowsApps package path and no npm/global shim, user-local executable, or Program Files executable was found. The result is documented in `docs/dogfood/devo-real-codex-dry-run-retry-101.md`. This led directly to TASK-DEVO-102 wrapper/launcher support.

### TASK-DEVO-102 Codex Launcher Wrapper Support - Completed

Added an explicit launcher strategy for supervised Codex worker execution. `devo worker codex doctor`, `preflight`, `run-plan`, `execute-preview`, and guarded `execute --confirm-execute` now understand PATH detection, explicit executable paths, local wrapper paths, blocked WindowsApps aliases, and WSL preview/planning. `devo worker codex wrapper-template --path <path> --type cmd` writes a local no-secrets wrapper template without running Codex and refuses committed source paths unless the target is an ignored workspace-local area. Wrapper execution uses explicit subprocess argument lists without `shell=True` and is covered with fake-wrapper tests only. WSL execution remains deferred; real supervised retry should wait until doctor reports a safe real executable or wrapper launcher.

### TASK-DEVO-103 Codex Launcher Setup Runbook - Completed

Added `docs/runbooks/codex-launcher-setup.md`, an operator checklist for obtaining a safe non-WindowsApps Codex launcher before retrying real supervised execution. The runbook documents supported launcher options, WindowsApps blocking, npm/global CLI setup, WSL preview/planning, wrapper template setup, readiness criteria, the next real retry sequence, and troubleshooting for missing shims, wrapper paths, `PermissionError`, `FileNotFoundError`, and WSL path mapping confusion. This task did not run real Codex, install packages, modify PersonalOS, or create execution artifacts.

### TASK-DEVO-104 Delivery Safety Design - Completed

Added `docs/delivery-safety-design.md`, the design for delivery after worker execution, report import, review evidence, and queue completion. The design separates queue completion from commit/push delivery, defines readiness criteria and stop conditions, proposes delivery artifacts under `workspace/projects/<project>/delivery/`, sketches future `devo delivery ...` commands, separates planning/batch/execution/run-plan/review/delivery/safety-override approvals, and defers auto commit/push plus UI commit/push buttons. No source code, UI code, delivery automation, real Codex execution, or target repo commands were added.

### TASK-DEVO-105 Delivery Readiness Checks - Completed

Added the first implemented delivery safety layer with read-only `devo delivery check`, `devo delivery list`, and `devo delivery show`. Delivery checks store JSON/Markdown under `workspace/projects/<project>/delivery/` only when `--write` is supplied, summarize target repository status, forbidden changed/staged paths, workspace artifacts staged, secret-risk files/signals, linked queue item status, linked worker review status, validation evidence status, blockers, warnings, and next action. Project overview read models and local API endpoints expose the latest delivery readiness state. This still does not stage, unstage, validate, commit, push, complete queues, run Codex, run target commands, or modify target repositories.

### TASK-DEVO-106 Delivery Plan Approvals - Completed

Added delivery plan and delivery approval artifacts under `workspace/projects/<project>/delivery/`, plus `devo delivery plan`, `plan-list`, `plan-show`, `approval-request`, `approval-show`, `approval-list`, `approve`, and `reject`. Plans copy readiness evidence from written delivery checks and record the intended future commit message. Approval requests are separate from readiness; blocked plans cannot be approved by default, warning plans can be approved while preserving warnings, and rejection preserves artifacts. Read models and API endpoints expose plan/approval state read-only. No staging, unstaging, validation execution, commit, push, queue completion, Codex execution, target commands, or target repo mutation was added.

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
