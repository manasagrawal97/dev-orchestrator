# TASK-DEVO-181 Rough Goal Intake MVP

## Goal

Reduce Manas's manual planning and sheet work by turning one rough Markdown goal file into a deterministic, workspace-only intake planning bundle.

This task intentionally did not add AI/API calls, UI, automatic approvals, automatic batch/queue/policy creation, Codex execution, validation execution, delivery creation, commit, or push.

## Implementation Summary

Added:

- `devo project intake-plan --project <project> --from-file <goal.md>`
- `devo project intake-plan --project <project> --from-file <goal.md> --confirm-create`

The command reads rough Markdown and prefers these optional headings:

- `# Goal`
- `# Context`
- `# Scope`
- `# Tasks`
- `# Allowed files`
- `# Do not touch`
- `# Validation`
- `# Delivery notes`

Without `--confirm-create`, the command previews the intake plan only. With `--confirm-create`, it writes:

- `workspace/projects/<project>/planning/intakes/<INTAKE-ID>/intake-plan.json`
- `workspace/projects/<project>/planning/intakes/<INTAKE-ID>/intake-plan.md`

## Dogfood

Created a temporary workspace-only rough goal file:

- `workspace/tmp/task-devo-181-rough-goal.md`

Ran:

```powershell
.\.venv\Scripts\devo.exe project intake-plan --project DevOrchestrator --from-file workspace\tmp\task-devo-181-rough-goal.md --confirm-create
```

Result:

- Intake id: `INTAKE-0001`
- Suggested batch: `B008`
- Suggested queue: `Q008`
- Suggested policy: `POL-0006`
- Candidate tasks: `3`
- Suggested allowed files:
  - `src/devo/project_planning.py`
  - `src/devo/main.py`
  - `tests/test_project_planning.py`
  - `README.md`
  - `docs/**`

Generated artifact:

- `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0001/intake-plan.md`
- `workspace/projects/DevOrchestrator/planning/intakes/INTAKE-0001/intake-plan.json`

These generated workspace artifacts are not committed.

## Safety Verdict

PASS.

The command created a reviewable intake bundle and stopped. It did not create real backlog tasks, batches, queues, policies, approvals, worker runs, validation evidence, delivery requests, commits, or pushes. It did not modify PersonalOS.

## Friction Found

- Draft batch/queue/policy IDs are useful, but they are only suggestions. The output must continue to say that the operator must review and translate candidate tasks into real Devo planning artifacts before approval.
- The next larger slice can add an explicit command to convert a reviewed intake into draft backlog/task artifacts, but that should remain gated and non-executing.

## Recommendation

TASK-DEVO-182 should add a reviewed intake-to-backlog draft path, or a clearer intake review command, so Manas can move from rough goal bundle to real task artifacts without manual spreadsheet work.
