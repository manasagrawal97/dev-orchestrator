# Recovery And Backup

This document summarizes how future ChatGPT/Codex sessions should reason about recovery and backups.

## Source Code

GitHub is the source-code backup for DevOrchestrator:

```text
https://github.com/manasagrawal97/dev-orchestrator
```

If source code is lost, clone from GitHub and inspect the latest Git log before continuing work.

## Workspace And Runtime Context

Devo's important runtime state lives under the local `workspace/` folder. This includes project registrations, planning artifacts, policies, queue-worker runs, Codex worker artifacts, validation evidence, delivery requests, runner records, and reports.

Workspace/context/runtime backups are stored under:

```text
G:\My Drive\Projects\Dev Orchestrator
```

Scheduled workspace backup exists and is the recovery path for Devo runtime context. Do not assume the Git repo alone contains all current queue/policy/runtime state.

## What Not To Do

- Do not manually edit backup folders unless a task explicitly asks.
- Do not run backup/restore commands unless explicitly approved.
- Do not treat old `.incomplete` backup folders as automatic blockers.
- Do not require a full source mirror to Google Drive; GitHub already covers source code.

## Recovery Order For A New Model

1. Read `docs/ai-handoff.md`.
2. Read `docs/current-state.md`, `docs/usability-roadmap.md`, `docs/how-to-use-devo.md`, and `docs/decision-log.md`.
3. Check the latest Git log.
4. Check repo status.
5. Inspect Devo queue/policy status for the active project.
6. If workspace state is missing or suspicious, inspect the latest successful Google Drive workspace backup.
7. Continue from the next approved/pending task only after current state is clear.

## Backup Health Notes

Normal backup behavior:

- scheduled backups run periodically
- successful backups are retained according to Devo retention policy
- `.incomplete` folders indicate interrupted or failed backup attempts
- newer successful backups are the important recovery signal

Manual backup is reserved for risky milestones or backup/recovery system changes. It is not required after every normal task.
