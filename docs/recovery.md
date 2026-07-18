# DevOrchestrator Recovery Guide

DevOrchestrator recovery is intentionally split across GitHub and Google Drive Desktop:

- GitHub stores DevOrchestrator source code and committed recovery scripts.
- Google Drive Desktop stores DevOrchestrator `workspace/` backups.
- The active workspace stays local at `E:\DevOrchestrator\workspace`.
- Google Drive is backup storage only, not the active workspace.

## Normal Manual Backup

Run from the repository root:

```powershell
.\scripts\recovery\backup-devo-workspace.ps1
```

The script creates a backup, verifies it, and then runs retention cleanup only after verification succeeds.

## Protected Milestone Backup

Use protected backups for important checkpoints that retention cleanup must never delete:

```powershell
.\scripts\recovery\backup-devo-workspace.ps1 -Label "before-major-personalos-work" -Protect
```

The script passes `--protect` to `devo backup create`, and the manifest stores `protected: true`.

## Install Scheduled Backup

```powershell
.\scripts\recovery\install-devo-backup-task.ps1
```

Default scheduled policy:

- frequency: every 12 hours
- label: `scheduled`
- retention: keep latest 10 normal backups
- protected: false

## Check Recovery Health

```powershell
.\scripts\recovery\check-devo-recovery-status.ps1
```

The status script checks the Git repo, current branch and commit, `.venv`, `devo`, active workspace, latest backup, latest backup verification, scheduled task presence, latest backup age, normal retained backups, and protected backups.

## Disaster Recovery On A New Or Clean Machine

```powershell
git clone https://github.com/manasagrawal97/dev-orchestrator.git E:\DevOrchestrator
cd E:\DevOrchestrator
.\scripts\recovery\restore-devo-workspace.ps1
```

The restore script creates `.venv` if needed, installs DevOrchestrator, locates the latest valid backup under Google Drive Desktop, verifies it, moves aside any existing non-empty active workspace as `workspace.pre-restore-YYYYMMDD-HHMMSS`, restores the backup into `E:\DevOrchestrator\workspace`, and reinstalls the scheduled backup task by default.

## Reinstall Scheduler Manually

The restore script should reinstall the scheduler automatically. To reinstall it manually:

```powershell
.\scripts\recovery\install-devo-backup-task.ps1
```

To remove it:

```powershell
.\scripts\recovery\uninstall-devo-backup-task.ps1
```

## Backup Policy

- Scheduled backups run every 12 hours by default.
- Keep the latest 10 normal backups.
- Auto-delete older normal backups only after a new backup is successfully created and verified.
- Protected backups are created only with `-Protect` in PowerShell or `--protect` in the CLI.
- Protected backups are never auto-deleted.
- Cleanup deletes only valid Devo backup folders with readable `backup-manifest.json` files.
- Cleanup skips unknown folders and folders with missing or invalid manifests.
- If backup verification fails, cleanup does not run.

Normal backups include scheduled, manual, and milestone labels unless explicitly protected.

## What Is Protected

Workspace backups include:

```text
workspace/projects/**
workspace/runs/**
workspace/environment/**
workspace/current.json
```

## What Is Not Protected

Workspace backups do not include:

```text
.venv
.git
target project repositories
PersonalOS app data
secrets
caches
```

Use environment snapshots to record tool and dependency metadata separately from workspace backups. Use Git to recover source code. Restore local secrets manually on the machine that owns them.
