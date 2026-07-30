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

These actions do not mutate Devo state, target projects, Git, backups, scheduler configuration, or approval records.

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

- generate scope template
- start work package draft
- request approval bundle
- open reports/visuals
- run safe refresh actions

Possible UI v3 actions:

- approve/reject through Devo approval system
- run approved validation commands
- mark work complete
- generate reports
- perform controlled write actions with explicit confirmation

All future write actions must route through Devo's policy, approval, validation, and evidence model.

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

Current context:

- `GET /api/current`

The browser should receive `ProjectOverview`, `RunOverview`, and `WorkPackageOverview` responses rather than parse raw files.

The first backend is available through `devo api serve` at `http://127.0.0.1:8765` by default. UI v1 should treat it as read-only and must not depend on write/action endpoints.

The first frontend dashboard is available under `ui/`. Start it with `npm run dev` from that folder after the API is running. It includes API-backed Projects, Project Overview, Work Package, Activity, and Health pages. UI v1 remains read-only and exposes only selection/navigation, optional JSON details, report/path viewing where available, and copyable CLI commands. The dashboard distinguishes selected dashboard project/run from saved CLI current context so the user can inspect one project without accidentally implying that `devo use` has changed.

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
