# Devo UI/API Architecture

## Purpose

Devo's future UI is a personal, local control surface for inspecting and operating Devo. It is not a hosted product, and it should not replace the CLI.

The UI should make Devo easier to understand at a glance:

- what projects are registered
- what the current project and run are
- whether a project is ready for work
- what work package is active
- what validation and delivery evidence exists
- what the next safe action is

The CLI remains first-class. Every important workflow must continue to work from the CLI even after a UI exists.

The first read-only dashboard scope is defined separately in `docs/ui-mvp-spec.md`.

## Recommended Architecture

Devo core should stay Python. The CLI, future local API server, and future UI should all use the same Devo workflow, policy, approval, validation, report, and read-model logic.

The UI should not scrape raw `workspace/` files directly. It should consume structured read models or API responses built from:

- `ProjectOverview`
- `RunOverview`
- `WorkPackageOverview`

Those read models were added as the bridge between CLI artifacts and future UI/API surfaces.

Current backend bridge:

- `devo api serve`
- FastAPI app factory in `src/devo/api.py`
- default URL `http://127.0.0.1:8765`
- read-only JSON endpoints over Devo read models
- non-local hosts blocked for MVP safety
- lightweight `X-Devo-Elapsed-Ms` response header for spotting slow read-model endpoints
- opt-in `include_timing=true` JSON timing breakdowns for overview, doctor, and activity endpoints

Recommended future backend direction:

- local-only FastAPI server
- bind to `127.0.0.1` by default
- read-only first
- reuse Devo Python modules directly
- expose read-model endpoints before any write/action endpoints

Recommended future frontend:

- React/Vite dashboard
- simple read-only status views first
- React Flow or XYFlow later for interactive work-package and activity diagrams
- Mermaid rendering may remain useful for documentation and generated Markdown previews

Blazor should not be the first Devo UI choice. Devo is Python-based, so FastAPI can reuse the existing modules directly. Blazor would add cross-stack complexity to Devo itself. PersonalOS can remain a separate Blazor/MudBlazor app.

Current frontend bridge:

- React/Vite/TypeScript scaffold in `ui/`
- default dev URL `http://127.0.0.1:5173`
- default API base `http://127.0.0.1:8765`
- override API base with `VITE_DEVO_API_BASE`
- read-only dashboard MVP with Projects, Project Overview, Work Package, Activity, and Health pages
- helper commands: `devo ui info`, `devo ui urls`, `devo ui status`, and `devo ui open`

## UI v1: Read-Only Dashboard

UI v1 should be read-only. It should make current Devo state visible without letting the browser mutate projects, approvals, Git, backups, or target repositories.

Suggested pages or sections:

- projects overview
- current project/run context
- project onboarding status
- doctor health summary
- project settings summary
- active work package
- recent activity and work history
- validation summary
- Git delivery status
- backup health summary
- generated visual report links and previews

Explicitly exclude from UI v1:

- approval buttons
- commit or push buttons
- backup restore
- delete operations
- scheduler modification
- running target app/build/test commands
- direct AI/API agents

## UI v2: Controlled Actions

After the read-only dashboard is useful, controlled actions can be considered. Good candidates are actions that already have safe CLI workflows:

- start a work package
- generate a scope template
- import a scope file
- request an approval bundle
- open generated reports
- run safe read-only refresh/status commands

Write actions must go through Devo's safety and approval model. A UI button should not bypass the same approval, validation, policy, and evidence checks that the CLI uses.

TASK-DEVO-071 adds the first controlled UI action safety model before any executable UI buttons. Actions are classified as:

- `read_only`: available in UI v1 for viewing state or copying commands.
- `workspace_safe`: possible UI v2 candidates that may write Devo workspace artifacts only, such as scope templates or generated visuals.
- `approval_required`: deferred actions that need explicit approval and audit design, such as requesting approvals or running validation.
- `dangerous_deferred`: blocked/deferred actions such as commit, push, backup restore/delete, scheduler modification, target app run, or model/API agent execution.

The dashboard may display this metadata, but UI v1 must not execute these actions.

TASK-DEVO-072 starts UI v2 with the smallest workspace-safe execution set. The only browser-triggered actions currently enabled are:

- generate work scope template
- generate work-package visual report
- generate project activity visual report
- write onboarding report

Each goes through `POST /api/actions/execute`, requires `confirm: true`, validates the registered project and run when needed, and writes Devo workspace artifacts only. Target repositories are not modified.

## Safety Model

The UI must stay local-first.

Safety rules:

- bind local services to `127.0.0.1` by default
- keep UI launch helpers local-only and read-only
- use the UI action metadata layer for future actions instead of ad hoc browser-side file mutations
- do not bypass CLI approval checks
- require explicit confirmation and Devo approval records for dangerous actions
- call a Devo service/read-model layer instead of mutating workspace files directly
- never expose secrets, `.env` values, appsettings secrets, local settings values, or private user data
- keep target project source modifications human/Codex-controlled for now
- do not run target app/build/test commands from UI v1
- do not add direct AI/API agent execution in UI v1

The browser should be a visibility layer first. Devo remains the control plane, and the CLI remains the reliable recovery path.

## API Shape Preview

MVP read-only API endpoints return the read models added in TASK-DEVO-063 or thin wrappers around them.

Current endpoints:

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

Early endpoints should be read-only and tolerant of older or missing workspace artifacts. Prefer `unknown`, `null`, or `SKIP` style values over server errors for optional fields.

The `/api/actions*` GET endpoints are metadata endpoints. They describe read-only actions available now, workspace-only actions available through the controlled executor, approval-required deferred actions, and dangerous blocked actions. `POST /api/actions/execute` executes only the four approved workspace-safe artifact generation actions and returns a structured `OK`, `WARN`, `FAIL`, or `BLOCKED` result.

Some read models can be slower because they aggregate doctor checks, Git status, backup inventory or scheduled-task checks, activity scanning, and overview summaries. UI v1 should handle that with section-level loading states and slow-check hints. TASK-DEVO-069 added timing breakdowns and request-local duplicate-work reductions before any persistent cache. Read-model snapshot caching or DB-backed caching remains deferred until the slow paths are profiled more deliberately.

## Implementation Phases

Phase A: architecture docs

- document the UI/API architecture and safety model
- keep the implementation docs-only

Phase B: local read-only API server

- added a local FastAPI server
- exposed read-model endpoints
- bind to `127.0.0.1` by default
- no write endpoints

Phase C: frontend scaffold

- added a minimal React/Vite app
- connected Projects and Health to local read-only endpoints
- keep the CLI as the primary workflow

Phase D: read-only dashboard MVP

- expanded the scaffold to show projects, current context, doctor, activity, work package lifecycle, validation, Git, backup, recent work, and copyable CLI commands
- polished dashboard layout, section-level loading, quieter activity evidence, and dashboard-selection versus CLI-context labels
- added helper commands for info/status/open without automatic server start or process stop
- follow the page and component scope in `docs/ui-mvp-spec.md`

Phase E: visual diagrams and activity timeline

- render generated Mermaid reports or richer diagrams from read-model data
- consider React Flow/XYFlow, D3, Cytoscape.js, Graphviz/DOT, or Mermaid depending on the view

Phase F: controlled write actions

- add narrowly scoped actions only after read-only views are stable
- route writes through Devo approval and policy checks
- keep action execution behind the UI action safety model
- start with confirmed workspace-safe artifact generation actions only
- keep approval, validation, Git delivery, restore/delete, scheduler, target app, and model/API actions deferred until their UI safety and audit model is designed

Phase G: optional API/model agents

- add direct model adapters only after manual/Codex mode remains smooth and cost-controlled

## Risks And Open Questions

- final UI stack decision
- packaging and start command for local use
- local-only access and whether lightweight auth is needed later
- performance on large workspaces
- whether read-model snapshot caching is needed after profiling
- how to render Mermaid and generated visual reports cleanly
- how to keep UI actions aligned with Devo approval records
- how much write access belongs in UI v2
- how to prevent accidental exposure of local secrets or private target-project data

## Current Decision

The current UI direction is:

1. keep Devo CLI-first and local-first
2. keep UI v1 read-only
3. improve dashboard clarity, loading behavior, and read-model performance
4. defer read-model snapshot caching until slow paths are profiled
5. defer controlled write actions until the approval/policy model is preserved in the UI
