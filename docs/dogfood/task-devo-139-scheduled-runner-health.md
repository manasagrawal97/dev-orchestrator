# TASK-DEVO-139 Scheduled Runner Health

## Problem

TASK-DEVO-138 proved the polished assisted queue-worker path, but the final smoke check showed confusing scheduled runner state:

```text
Installed: False
Enabled: True
```

That means Devo workspace metadata said the runner should be enabled, while the actual Windows scheduled task was missing. Auto-delivery cannot be trusted in that state.

## Change

Devo scheduled runner status now classifies health explicitly:

- `healthy`: scheduled task exists and is enabled.
- `disabled`: scheduled task exists but is disabled.
- `not_installed`: no schedule config or no installed task with disabled metadata.
- `drift`: Devo metadata says enabled but the task is missing.
- `unknown`: scheduler state cannot be safely determined.

`devo delivery runner-schedule-status --project <project>` now prints `Health: ...`, repair commands when unhealthy, and does not claim enabled auto-delivery when the Windows task is missing.

TASK-DEVO-139 also adds:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-doctor --project DevOrchestrator
```

The doctor is read-only. It diagnoses config, task presence, latest watch state, health, warnings, and repair commands without modifying scheduler state.

## Repair Guidance

For `not_installed` or `drift`, repair from normal local PowerShell:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-install --project DevOrchestrator --approver "Manas" --confirm-install
.\.venv\Scripts\devo.exe delivery runner-schedule-enable --project DevOrchestrator --confirm-enable
.\.venv\Scripts\devo.exe delivery runner-schedule-status --project DevOrchestrator
```

If scheduler health is unclear, direct trusted runner delivery remains the safe fallback:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request <REQ-ID> --approver "Manas" --confirm-runner-delivery
```

## Why It Matters

The target Phase 2 loop is:

```text
approved queue
-> queue-worker-loop
-> delivery request
-> scheduled trusted runner delivers automatically
```

That loop should not depend on ambiguous scheduler state. Drift must be visible before Devo relies on scheduled auto-delivery.

## Recommended Next Task

Recommended next task: TASK-DEVO-140 approved queue auto-run v1.

Only start it after scheduled runner status is healthy or the operator accepts direct trusted runner delivery as the fallback for the dogfood.
