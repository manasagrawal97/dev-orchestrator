# DevOrchestrator Roadmap

## Immediate Planned Tasks

- TASK-025 project context update / enrichment workflow
- TASK-029 run/report summary command
- TASK-030 end-to-end dogfood run on DevOrchestrator itself
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
- one end-to-end dogfood run

## Rough Remaining Effort

- Practical readiness remaining: around 8-18 focused hours.
- Full long-term product vision: 80-150+ hours.

## Near-Term Direction

### TASK-023 Safe Validation Runner

Add controlled execution for registered validation commands. It should require policy checks, approval where required, disabled-command handling, output capture, timeout limits, and clear evidence recording. This is the first step that can execute commands, so safety and approval behavior matter more than convenience.

### TASK-024 Git Delivery Workflow - Completed

Added non-mutating Git status, delivery-check, and delivery-report commands. Devo now reports branch/upstream state, changed files, forbidden staged paths, secret-like changed-file signals, validation evidence, approval evidence, and exact manual commit/push guidance without force-pushing or bypassing approval policy.

### TASK-025 Project Context Update / Enrichment Workflow

Support updating approved project context artifacts from safe enrichment runs without modifying target project source. This is needed for PersonalOS context enrichment findings.

### TASK-029 Run/Report Summary Command

Create a concise command that summarizes a run, task state, validation registry state, approvals, artifacts, and recommended next action.

### TASK-030 End-To-End Dogfood Run

Run DevOrchestrator on itself using its own workflows. The goal is to prove the control plane before relying on it for deeper PersonalOS work.

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
