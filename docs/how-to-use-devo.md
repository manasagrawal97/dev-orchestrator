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

For the plain-language product model, read:

- [Devo vision](devo-vision.md)
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
```

The API is read-only in v1. It does not approve/reject, run validation/build/test/app commands, restore/delete backups, modify scheduler settings, commit, push, edit target files, or call model APIs. `devo api serve` blocks non-local hosts for MVP safety. Responses include an `X-Devo-Elapsed-Ms` header to help identify slow read-model endpoints during dashboard review.

For profiling slow local read models, add `include_timing=true` to selected endpoints:

```text
GET /api/projects/<project>/overview?include_timing=true
GET /api/projects/<project>/doctor?include_timing=true
GET /api/projects/<project>/activity?include_timing=true
```

The `_timing` object is omitted by default. This timing support is read-only and process-local; Devo has not added persistent DB or SQLite caching for dashboard data.

## React UI Scaffold

The first frontend scaffold is under `ui/`. It is read-only and uses the local API.

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

The frontend defaults to `http://127.0.0.1:8765` for the API. Override it with `VITE_DEVO_API_BASE` when needed. UI v1 includes read-only Projects, Project Overview, Work Package, Activity, and Health pages. It distinguishes dashboard selection from saved CLI current context, uses section-level loading hints for slower overview/doctor checks, keeps Activity evidence quieter by default, and can display read models and copy CLI commands. It does not approve/reject, run validation/build/test/app commands, commit, push, restore/delete backups, modify scheduler settings, edit target files, or call model APIs.

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
```

Delivery commands inspect Git state and write evidence. They do not stage, commit, push, or bypass GitHub policy.

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
