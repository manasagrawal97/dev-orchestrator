# Devo UI MVP Specification

## UI MVP Goal

The first Devo UI is a local personal dashboard for Devo.

It helps the user inspect and understand Devo state:

- which projects exist
- whether a project is healthy
- what work is active
- what validation and delivery evidence exists
- what the next safe action is

It does not replace the CLI. It does not execute risky actions. UI v1 is read-only.

The longer-term UI should follow the company-model vision in `docs/devo-company-model.md`: project brief, blueprint, backlog, batches, queue, and progress views around Codex-powered execution. The implementation order for those planning/progress screens is tracked in `docs/remaining-roadmap.md`. It should not become a general chat clone.

After TASK-DEVO-074, Project Overview includes a read-only Planning card backed by `ProjectOverview` fields for brief status, blueprint status, milestone count, epic count, and the planning next action. TASK-DEVO-075 extends that card with backlog status, task count, ready count, blocked count, and completed count. TASK-DEVO-076 adds read-only refinement prompt metadata and a copyable CLI command. TASK-DEVO-077 adds read-only batch count/latest-batch metadata and a copyable `batch-suggest` command. TASK-DEVO-078 adds a read-only Progress card with count-based project completion, backlog readiness, blocked percentage, batch completion, latest batch status, and a copyable `devo project progress` command. TASK-DEVO-079 adds read-only queue count/latest queue/current item metadata and copyable queue inspection guidance. TASK-DEVO-080 adds read-only handoff count/latest handoff metadata and copyable handoff CLI guidance. TASK-DEVO-081 adds a dedicated read-only Planning Intake page that shows the full brief -> blueprint -> backlog -> batch -> queue -> handoff -> progress pipeline with section-level status summaries and copyable CLI commands. TASK-DEVO-082 adds read-only Blueprint and Backlog detail pages with milestone/epic rollups, task filters, and selected-task detail. TASK-DEVO-083 adds read-only Batch, Queue, Handoff, and Progress pages with selected-artifact detail, queue item detail, handoff metadata, progress bars, milestone/epic progress, and CLI guidance. TASK-DEVO-084 adds workspace-safe Batch approval/review planning actions and approval metadata visibility. TASK-DEVO-088 adds read-only worker-run count/latest state to Project Overview and worker-run tracking metadata to Handoffs. TASK-DEVO-089 adds read-only imported worker-report metadata and copyable report template/validate/import/show commands. TASK-DEVO-090 adds a dedicated read-only Worker Runs page with run list, selected run details, imported report details, related handoff/queue context, review guidance, and copyable CLI commands. TASK-DEVO-091 adds read-only Codex run-plan count/latest/preflight metadata to Project Overview and Worker Runs, plus safe preflight/run-plan CLI guidance. TASK-DEVO-092 adds read-only execution metadata/log-path visibility and copyable execute-preview/execute-log/guarded-execute CLI commands. UI execution controls, queue transitions from UI, validation/build/test, commit/push, restore, scheduler modification, and model/API calls remain future or blocked scope.

TASK-DEVO-087 documents future worker adapter UI expectations in `docs/codex-worker-adapter-design.md`. TASK-DEVO-090 adds the first Worker Runs page as read-only visibility: status, transcript/log paths when present, queue item links, report detail, resume/review guidance, and copyable CLI commands. TASK-DEVO-091 extends that page with run-plan preview and preflight status visibility. TASK-DEVO-092 adds execution metadata/log-path display and copyable CLI commands, but not UI execution buttons. Launching Codex from the UI, importing reports from the UI, running validation, committing, pushing, restoring, scheduler changes, target app runs, and model/API calls remain outside UI MVP scope.

## UI MVP Principles

- CLI remains first-class.
- UI consumes read models/API responses, not raw workspace scraping.
- UI is local-only.
- UI v1 is read-only.
- Dangerous actions are deferred.
- Clear status badges and next actions matter more than fancy design.
- Missing older artifacts should show `unknown`, `SKIP`, or a helpful empty state instead of breaking the page.
- Links to reports, visuals, and commands should help the user return to the CLI quickly.
- Slow sections should show local loading hints instead of blocking the full page.
- Raw artifact paths should remain accessible, but they should not dominate the first visual scan.

## UI MVP Pages

### A. Projects Page

Shows all registered projects and enough state to choose where to work.

Fields:

- registered project name
- project path
- onboarding status
- doctor status
- Git status
- default lane
- latest activity
- suggested next action

Primary user question: "Which project needs attention?"

### B. Project Overview Page

Shows a single project's `ProjectOverview`.

Sections:

- settings summary
- validation registry summary
- Git summary
- backup summary
- recent runs
- recent work packages
- suggested next command

Primary user question: "Is this project ready, and what should I do next?"

### B2. Planning Intake Page

Shows the planning workflow from Project Brief through Progress.

Sections:

- workflow pipeline / stepper
- Project Brief status and artifact context
- Blueprint milestone/epic counts
- Backlog counts and refinement prompt status
- Batch counts/latest batch
- Queue counts/latest queue/current item
- Handoff counts/latest handoff/path
- Progress percentages and warnings
- copyable CLI commands for each stage

Primary user question: "Where am I in the Devo planning workflow, and which CLI command should I run next?"

This page is read-only. It does not create briefs from the UI, approve artifacts, run Codex, execute target commands, run validation/build/test, commit, push, restore backups, modify schedulers, edit target files, or call model APIs.

### B3. Blueprint Page

Shows the stored Project Blueprint in detail.

Sections:

- status, title, and vision summary
- architecture notes
- risk summary
- validation strategy
- open questions
- milestones with linked epics and progress rollups
- epics with milestone links and progress rollups
- artifact path and copyable CLI commands

Primary user question: "What plan did Devo approve, and how does it map to progress?"

This page is read-only. It does not create or approve blueprint artifacts from the UI.

### B4. Backlog Page

Shows the stored Backlog and Tasks in detail.

Sections:

- backlog status and counts
- readiness and blocked percentages
- refinement prompt availability
- task filters by status, lane, risk, and text search
- task list
- selected task detail with summary, dependencies, acceptance criteria, validation expectations, allowed scope, forbidden scope, notes, and source
- artifact path and copyable CLI commands

Primary user question: "Which task should I inspect or prepare next?"

This page is read-only. It does not create, import, approve, execute, or mutate backlog/task artifacts from the UI.

### B5. Batches Page

Shows stored planning Batches in detail.

Sections:

- batch count, approved count, latest batch, and batch completion percentage
- batch list with batch id, title, status, approval status, task counts, blocked/completed counts, risk summary, and lane summary
- selected batch detail with summary, source backlog reference, dependencies, dependency warnings, review notes, and task snapshots
- approval request/review/decision metadata when available
- copyable CLI commands for `batch-list`, `batch-show`, `batch-approval-request`, `batch-approval-show`, `batch-suggest`, `batch-suggest --write`, `batch-review`, `batch-approve`, and `batch-reject`

Primary user question: "Which batch is ready or approved, and what does it contain?"

This page is primarily inspection and operator guidance. Controlled Batch approval/review actions may be exposed only through the Action Safety model with explicit confirmation. Those actions write Devo planning artifacts only; they do not create queues, run Codex, execute target commands, run validation, commit, push, restore backups, modify schedulers, edit target files, or call model APIs.

### B6. Queues Page

Shows stored execution Queues in detail.

Sections:

- queue count, latest queue, latest status, current item, and aggregate item counts
- queue list with source batch, status, item counts, pause reason, and resume hint
- selected queue detail with items, item status, task id, lane, risk, dependencies, acceptance criteria, validation expectations, and notes
- copyable CLI commands for `queue-list`, `queue-show`, `queue-create`, `queue-start`, `queue-next`, `queue-pause`, and `queue-resume`

Primary user question: "What is queued, paused, blocked, or completed?"

This page is read-only. It does not create queues, start queues, resume queues, pause queues, advance queue items, run Codex, or mutate queue artifacts from the UI.

### B7. Handoffs Page

Shows stored Codex handoff metadata and read-only worker-run tracking metadata.

Sections:

- handoff count, latest handoff id, latest type, and latest status
- worker run count, latest worker run id, and latest worker status
- latest imported worker report status, summary, changed-file count, validation count, safety warnings, and next action
- handoff list with source queue, batch, item, task, prompt path, and status
- selected handoff metadata
- latest worker run source handoff, report status, and next action
- copyable CLI commands for `handoff-list`, `handoff-show`, `handoff-next`, `handoff-task`, `handoff-batch`, and `handoff-mark-used`
- copyable CLI commands for `worker codex run-create`, `run-list`, `run-show`, and `run-status`
- copyable CLI commands for `worker codex report-template`, `report-validate`, `report-import`, `report-show`, and `report-list`

Primary user question: "Which Codex handoff prompt exists, what source artifact produced it, and has a manual worker run been tracked?"

This page is read-only. Worker run/report metadata does not run Codex, import reports from the UI, prove implementation complete, complete queue items, execute validation, commit, push, restore backups, modify schedulers, edit target files, or call model APIs.

This page is read-only. It does not generate prompts, mark prompts used, invoke Codex, call AI APIs, or execute target commands from the UI.

### B8. Worker Runs Page

Shows Codex worker run, imported report, and run-plan preview visibility for assisted manual handoff and future supervised execution readiness.

Sections:

- worker run count, latest worker run id/status, latest report status, run-plan count, latest preflight status, and latest next action
- worker run list with run id, status, mode, source handoff/queue/item/task, report status, run-plan id/status, timestamps, and next action
- selected worker run detail with worker type, mode, prompt/transcript/report/execution log paths, target repo path, execution exit code, allowed/forbidden scope, validation expectations, safety boundaries, status note, and next action
- imported report detail with status reported by worker, summary, changed files, validation attempted/results, tests run, commands run, optional commit hash, safety warnings, blockers, follow-up needed, notes, and imported/reported timestamps
- selected run-plan preview with preflight status, approval status, proposed working directory, safe command preview, preflight checks, blocked reasons, warnings, allowed/forbidden scope, validation expectations, safety boundaries, and next action
- related handoff and queue context when available
- copyable CLI commands for `worker codex prepare-next`, `queue-status`, `run-list`, `run-show`, `run-status`, `preflight`, `run-plan`, `run-plan-list`, `run-plan-show`, `execute-preview`, guarded `execute --confirm-execute`, `execute-log`, `report-template`, `report-validate`, `report-import`, `report-show`, `report-list`, plus post-review `queue-next` and `queue-complete-item` guidance
- read-only queue-worker linkage fields: linked worker run, linked run plan, current item review status, latest execution status, and next CLI command

Primary user question: "What did the manual Codex worker run report, is a future supervised run ready to plan, and what should I review before touching queue/task state?"

This page is read-only. It does not run Codex from the UI, import/upload reports from the UI, approve execution, execute target commands, run validation/build/test, commit, push, restore backups, modify schedulers, edit target files, call model APIs, or complete queue/task items.

### B9. Progress Page

Shows planning and workflow progress in one dashboard.

Sections:

- project completion, backlog readiness, blocked percentage, and batch completion progress bars
- task counts by draft, ready, approved, active, completed, and blocked
- batch counts by total, approved, active, and completed
- queue counts by total, latest status, pending, running, completed, blocked, and failed
- milestone progress groups
- epic progress groups
- warnings and next action
- copyable CLI command for `devo project progress`

Primary user question: "How far through the plan is this project, and where is the next bottleneck?"

This page is read-only. It does not recalculate by running target commands, execute queues, validate, commit, push, restore backups, edit target files, or call model APIs.

### C. Work Package / Run Detail Page

Shows `RunOverview` and `WorkPackageOverview` for one run.

Sections:

- goal
- lane
- current phase
- scope status
- approval status
- validation status
- delivery status
- commit hash
- stop conditions
- next command
- work-package lifecycle visual

Primary user question: "Where is this work package, and how do I continue safely?"

### D. Activity / History Page

Shows recent project activity in one place.

Sections:

- recent runs
- delivered work packages
- validations
- Git deliveries
- reports
- generated visuals
- context updates

Primary user question: "What happened recently?"

### E. Health Page

Shows Devo/project health from doctor-style summaries.

Sections:

- doctor summary
- workspace health
- project settings health
- backup health
- scheduled task status
- validation health
- warnings and failures
- suggested fix command

Primary user question: "Is anything broken or risky?"

### F. Action Safety Page

Shows UI action safety metadata without executing actions.

Sections:

- current UI mode
- read-only actions available now
- workspace-safe candidates for a future UI v2
- approval-required deferred actions
- dangerous blocked/deferred actions
- reason and risk level for each action

Primary user question: "What could the UI safely do later, and what is intentionally blocked?"

## Sections And Components

Reusable UI components:

- `StatusBadge`: `OK`, `WARN`, `FAIL`, `SKIP`, `PENDING`, `READY`
- `ProjectCard`
- `SummaryCard`
- `NextActionCard`
- `GitStatusCard`
- `ValidationSummaryCard`
- `BackupSummaryCard`
- `WorkLifecycleStepper`
- `ActivityTimeline`
- `CommandCopyBox`
- `ReportLinkList`
- `VisualReportPreview`

Components should prefer dense, readable operational status over decorative layout. Long commands and paths should be copyable.

## Allowed UI v1 Actions

Allowed read-only actions:

- refresh dashboard
- select project
- select run/work package
- copy CLI command
- open or copy artifact/report path
- view generated visual reports
- view JSON/read-model data when useful
- check UI/API reachability from the CLI with `devo ui status`
- open the already-running local dashboard with `devo ui open`
- view action safety metadata
- generate approved workspace-only artifacts after confirmation:
  - work-package draft
  - work scope template
  - work-package visual report
  - project activity visual report
  - onboarding report

The artifact-generation actions mutate Devo workspace artifacts only. They do not mutate target projects, Git, backups, scheduler configuration, approval records, validation state, or model/API state.

## Forbidden UI v1 Actions

Explicitly forbidden in UI v1:

- approve or reject
- run build/test
- commit or push
- restore backup
- delete backup
- modify scheduler
- modify project settings
- modify target project files
- run target app
- call OpenAI, Claude, Gemini, or other model APIs
- execute autonomous agents

If a user needs one of these actions, the UI should show the CLI command or explain that the action is deferred.

## Future UI v2/v3 Actions

Possible UI v2 actions:

- start work package draft - added in TASK-DEVO-073
- generate scope template - added in TASK-DEVO-072
- generate workspace visual reports - added in TASK-DEVO-072
- write onboarding report - added in TASK-DEVO-072
- open reports/visuals
- run safe refresh actions

Possible UI v3 actions:

- request approval bundle
- approve/reject through Devo approval system
- run approved validation commands
- mark work complete
- generate reports
- perform controlled write actions with explicit confirmation

All future write actions must route through Devo's policy, approval, validation, and evidence model.

TASK-DEVO-071 adds a backend action metadata registry for this boundary. TASK-DEVO-072 adds `POST /api/actions/execute` for the first confirmed workspace-safe artifact generation actions. TASK-DEVO-073 adds the controlled `work.new.create` work bootstrap action. Approval-required and dangerous/deferred actions still must not execute from the UI.

## Approval UI Design

A future approval page should show:

- approval id
- risk level
- project/run
- lane
- scope fingerprint
- allowed files/actions
- forbidden files/actions
- validation command
- delivery rules
- stop conditions
- approve/reject/copy CLI command

Approval buttons are not part of UI v1. UI v1 may show approval state and copyable CLI commands only.

## Data/API Mapping

Future endpoints should use the read models from TASK-DEVO-063.

API health:

- `GET /api/health`

Projects page:

- `GET /api/projects`
- `GET /api/projects/{project}/overview`

Project Overview:

- `GET /api/projects/{project}/overview`
- `GET /api/projects/{project}/activity`
- `GET /api/projects/{project}/doctor`

Project Overview should render the selected project shell immediately and fill in slower sections independently. Doctor, backup, Git, and activity-backed summaries may take longer on large workspaces, so section-level loading states should explain that some health checks can take longer.

Work Detail:

- `GET /api/projects/{project}/runs/{run}/overview`
- `GET /api/projects/{project}/runs/{run}/work-package`

Activity:

- `GET /api/projects/{project}/activity`

Health:

- `GET /api/projects/{project}/doctor`

Action Safety:

- `GET /api/actions`
- `GET /api/actions/allowed`
- `GET /api/actions/{action_id}`
- `POST /api/actions/execute`

Current context:

- `GET /api/current`

The browser should receive `ProjectOverview`, `RunOverview`, and `WorkPackageOverview` responses rather than parse raw files.

The first backend is available through `devo api serve` at `http://127.0.0.1:8765` by default. The original dashboard endpoints are read-only. The action safety GET endpoints are metadata. `POST /api/actions/execute` is the only action execution endpoint and is limited to confirmed workspace-only work bootstrap and artifact generation.

The first frontend dashboard is available under `ui/`. Start it with `npm run dev` from that folder after the API is running. It includes API-backed Projects, Project Overview, Work Package, Activity, Health, and Action Safety pages. The dashboard exposes selection/navigation, optional JSON details, action safety metadata, confirmed workspace-only work bootstrap/artifact generation controls, report/path viewing where available, and copyable CLI commands. The dashboard distinguishes selected dashboard project/run from saved CLI current context so the user can inspect one project without accidentally implying that `devo use` has changed.

Use `devo ui info` for local URLs and start commands, `devo ui status` to check whether the API/UI are reachable, and `devo ui open` to open the already-running UI. These helpers do not start servers automatically and do not add write actions.

## Wireframe-Style Layout

Projects page:

```text
+---------------------------------------------------------------+
| Devo Projects                              Current: PersonalOS |
+---------------------------------------------------------------+
| Project        Health   Git       Lane              Next       |
| DevOrchestrator OK      clean     devo-internal     work new   |
| PersonalOS     WARN    clean     ui-maintenance    doctor     |
+---------------------------------------------------------------+
| Recent activity                                              |
| - PersonalOS delivered UI polish: b3d4880                    |
| - DevOrchestrator added UI-ready read models                 |
+---------------------------------------------------------------+
```

Project overview page:

```text
+---------------------------------------------------------------+
| PersonalOS Overview                         Status: WARN       |
+---------------------------------------------------------------+
| Settings        | Validation       | Git        | Backup       |
| lane: ui-maint  | build configured | clean      | OK           |
+---------------------------------------------------------------+
| Suggested next command: devo work new --goal "..."            |
+---------------------------------------------------------------+
| Recent runs                  | Recent work packages            |
| 2026-... delivered           | UI polish delivered             |
| 2026-... validated           | warning cleanup delivered       |
+---------------------------------------------------------------+
```

Work package detail page:

```text
+---------------------------------------------------------------+
| Work Package: Operational UI polish                           |
| Run: 2026-...        Lane: low-risk-ui-maintenance             |
+---------------------------------------------------------------+
| Scope: imported | Approval: approved | Validation: passed      |
| Delivery: pushed | Commit: b3d4880                             |
+---------------------------------------------------------------+
| Lifecycle: start > scope > approval > implement > validate > done |
+---------------------------------------------------------------+
| Stop conditions                                               |
| - scope change                                                |
| - build failure                                               |
| - forbidden file needed                                       |
+---------------------------------------------------------------+
| Next command: devo project activity --project PersonalOS      |
+---------------------------------------------------------------+
```

Health page:

```text
+---------------------------------------------------------------+
| Health                                                        |
+---------------------------------------------------------------+
| Overall: WARN                                                 |
| Workspace: OK                                                 |
| Project settings: OK                                          |
| Validation registry: OK                                       |
| Backup: WARN - incomplete backup folders found                |
| Scheduled task: OK                                            |
+---------------------------------------------------------------+
| Suggested fix: devo backup list --dest "<backup-root>"        |
+---------------------------------------------------------------+
```

## MVP Success Criteria

The UI MVP is successful if the user can quickly answer:

- Which projects exist?
- Is the current project healthy?
- What is the current active work?
- What is the next action?
- Did validation pass?
- What was recently delivered?
- Is backup healthy?
- Where are reports and visuals?

## Deferred Scope

Deferred from UI v1:

- full interactive workflow
- approval buttons
- build/test execution
- commit/push
- backup restore/delete
- scheduler management
- API/model agents
- multi-user/auth/cloud hosting
- mobile-first UI

These can be reconsidered only after the read-only dashboard proves the data model, local API shape, and safety boundaries.
