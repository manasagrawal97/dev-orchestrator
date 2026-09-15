# Model Migration Handoff Hardening

## Purpose

This docs-only task hardens DevOrchestrator for future ChatGPT/Codex model migration. The risk is that a future model could lose project intent, priorities, workflow state, and safety decisions if it only reads recent chat context.

The mitigation is a durable handoff path in repo docs.

## Handoff Entry Point

Future models should start with:

```text
docs/ai-handoff.md
```

Then read:

- `docs/current-state.md`
- `docs/usability-roadmap.md`
- `docs/how-to-use-devo.md`
- `docs/decision-log.md`
- `docs/recovery-and-backup.md`

## Captured Intent

The owner intent is now explicit:

- Devo exists to automate AI-assisted software development.
- The first priority is reducing manual PowerShell/Codex/ChatGPT copy-paste work.
- UI and dashboard polish come later.
- Supervised automation comes first.
- Codex CLI/Desktop remains the current worker path.

## Captured Workflow

The target workflow is now summarized as:

```text
rough goal
-> intake/materialized planning artifacts
-> bounded human approval
-> sequential Codex worker execution
-> worker evidence
-> review evidence
-> validation evidence
-> delivery request
-> trusted runner commit/push
-> reconciliation
```

Devo should stop on blockers instead of guessing.

## Captured Current State

The docs now call out these recent milestones:

- TASK-DEVO-187: `intake-policy-create-next`
- TASK-DEVO-189: `patch-proposal-accept`
- TASK-DEVO-190: `queue-worker-run-validation`

The docs also record that TASK-DEVO-191 is planned/approved as `POL-0029` / `QWR-0027`, currently `waiting_worker`, and intentionally paused until model migration docs were hardened.

## Safety Verdict

This was docs-only. No source code, tests, UI, workspace artifacts, PersonalOS files, commits, pushes, or delivery runner internals were modified.

## Recommended Next Step

Resume TASK-DEVO-191: optional `queue-worker-loop --auto-validation` integration.
