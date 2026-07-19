# DevOrchestrator Roadmap

## Immediate Planned Tasks

- TASK-030 end-to-end dogfood run on DevOrchestrator itself - current
- TASK-031 resume PersonalOS through Devo with one safe real task
- TASK-032 improve docs/current-state/project memory handling

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

### TASK-023 Safe Validation Runner

Add controlled execution for registered validation commands. It should require policy checks, approval where required, disabled-command handling, output capture, timeout limits, and clear evidence recording. This is the first step that can execute commands, so safety and approval behavior matter more than convenience.

### TASK-024 Git Delivery Workflow - Completed

Added non-mutating Git status, delivery-check, and delivery-report commands. Devo now reports branch/upstream state, changed files, forbidden staged paths, secret-like changed-file signals, validation evidence, approval evidence, and exact manual commit/push guidance without force-pushing or bypassing approval policy.

### TASK-025 Project Context Update / Enrichment Workflow - Completed

Added deterministic context-summary, context-refresh, context-apply, and context-history commands. Context updates are append-only Devo workspace records sourced from scans, validation metadata, environment snapshots, runs, delivery reports, and approval ledgers; they do not modify target repositories or overwrite approved context automatically.

### TASK-029 Project/Run Report And Handoff Summary Commands - Completed

Added deterministic project, run, and handoff reports. Devo now summarizes project context, recent runs, workflow next actions, task resolution, policy/approval/validation/git-delivery evidence, warnings, suggested actions, and recovery handoff commands without mutating target projects or workflow state.

### TASK-030 End-To-End Dogfood Run

Run DevOrchestrator on itself using its own workflows. The goal is to prove the control plane before relying on it for deeper PersonalOS work. The dogfood target should stay small and safe, with report/handoff artifacts used as the recovery trail.

### TASK-031 Resume PersonalOS Through Devo

Use Devo to select and execute one safe real PersonalOS task after validation runner and delivery workflow exist.

### TASK-032 Project Memory Handling

Improve durable project memory so completed/deferred/planned work survives chat context loss and can be recovered from GitHub plus workspace backups.

## Guiding Constraints

- Keep Devo deterministic first.
- Preserve target project safety.
- Avoid AI API integration until file-based workflows are proven.
- Avoid web UI until CLI workflows are stable.
- Prefer explicit approval records and evidence over implicit automation.
