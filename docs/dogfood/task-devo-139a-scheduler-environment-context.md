# TASK-DEVO-139A Scheduler Environment Context

## Context

After TASK-DEVO-139, normal PowerShell reported the scheduled trusted runner as healthy:

```text
Installed: True
Enabled: True
Health: healthy
Doctor result: scheduler is healthy
```

The Codex/sandbox environment still reported:

```text
Installed: False
Enabled: False
Health: drift
Doctor result: scheduler metadata drift detected
```

That is not necessarily a broken scheduler. It can mean the current process cannot see or query Windows scheduled tasks even though the normal Windows user environment can.

## Change

`runner-schedule-status` and `runner-schedule-doctor` now include environment context:

- process user
- working directory
- task query source
- task query result
- environment note

When Devo metadata says the scheduler is enabled but task lookup cannot confirm the Windows task, output now says the scheduled task may be missing or the current process may not be able to see Windows scheduled tasks.

## Operating Guidance

Do not repeatedly reinstall the scheduler when normal PowerShell reports healthy.

If Codex/sandbox reports `Health: drift`, verify from normal PowerShell:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-status --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery runner-schedule-doctor --project DevOrchestrator
```

If normal PowerShell is healthy, record it as an environment visibility mismatch and proceed only when the task being attempted explicitly accepts that evidence.

If normal PowerShell is also unhealthy, repair with install and enable:

```powershell
.\.venv\Scripts\devo.exe delivery runner-schedule-install --project DevOrchestrator --approver "Manas" --confirm-install
.\.venv\Scripts\devo.exe delivery runner-schedule-enable --project DevOrchestrator --confirm-enable
```

## TASK-DEVO-140 Readiness

TASK-DEVO-140 should not keep reinstalling the scheduler if normal PowerShell shows healthy and Codex/sandbox cannot see the task. It can proceed only if normal PowerShell health evidence is available and the operator accepts direct trusted runner delivery as the fallback if needed.

This does not weaken runtime safety. Devo still does not mark a missing task as healthy from a restricted process, and `approved-queue-run` can still require scheduler health in normal use.
