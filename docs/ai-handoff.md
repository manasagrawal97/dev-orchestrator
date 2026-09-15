# AI Handoff

This is the first document a new ChatGPT/Codex model should read when taking over DevOrchestrator.

## Owner Intent

Manas is building Devo to automate AI-assisted software development safely. The core product is not a dashboard first; it is a local, CLI-first control plane that reduces manual PowerShell, Codex, ChatGPT, evidence, validation, and delivery copy-paste work.

The priority is supervised automation first:

- convert rough goals into scoped planning artifacts
- approve bounded work explicitly
- run one approved item at a time through Codex and Devo gates
- record evidence automatically where safe
- stop on blockers instead of guessing
- deliver only through the trusted runner

UI/dashboard polish remains useful, but it is not the main priority until the Codex CLI automation path is smoother.

## Target Workflow

The desired operating loop is:

1. Human creates or refines a rough goal.
2. Devo turns the goal into intake, backlog, batch, queue, and execution policy artifacts.
3. Human approves bounded work.
4. Devo runs approved work sequentially through Codex worker execution.
5. Devo ingests worker output and records worker evidence.
6. Human or deterministic helper reviews evidence.
7. Devo runs approved validation commands and records validation evidence.
8. Devo creates a trusted delivery request only after evidence gates pass.
9. Trusted runner commits and pushes.
10. Devo reconciles delivery, marks queue progress, and stops or continues to the next safe item.

Devo should stop on forbidden files, secret risk, failed validation, usage limits, unclear worker output, missing evidence, dirty repo ambiguity, scheduler/runner drift, or policy mismatch.

## Current Implemented Workflows

The important implemented workflows are:

- rough goal intake with `devo project intake-plan`
- intake materialization with `devo project intake-materialize`
- safe next slice recommendation with `devo project intake-next-slice`
- narrow draft policy creation with `devo project intake-policy-create-next`
- queue-worker evidence flow for worker result, review, and validation
- patch proposal show/check/apply/accept helpers for blocked Codex write paths
- automatic validation evidence recording with `devo project queue-worker-run-validation`
- trusted delivery runner request/watch/run/reconciliation path
- scheduled workspace backup to Google Drive

Recent completed milestones:

- TASK-DEVO-187: `intake-policy-create-next`
- TASK-DEVO-189: safe `patch-proposal-accept`
- TASK-DEVO-190: `queue-worker-run-validation`

## Current Manual Pain

The remaining pain is still in the middle of the supervised loop:

- worker execution and ingest need more hardening
- review evidence is still mostly manual
- `queue-worker-loop` does not yet auto-call the validation runner
- bulk approval of bounded safe policies is not ready
- the final supervised `auto-run-approved` sequential loop is not ready

The next automation goal is TASK-DEVO-191: optional auto-validation integration in `queue-worker-loop`.

## Active Pending State

TASK-DEVO-191 is planned/approved as `POL-0029` / `QWR-0027` and is in `waiting_worker`.

It should implement optional `queue-worker-loop --auto-validation` behavior. It was intentionally paused so this model-migration handoff could be hardened first.

## Safety Boundaries

Default boundaries for future model sessions:

- do not touch PersonalOS unless explicitly asked
- do not bypass human approval
- do not bypass the trusted delivery runner
- do not manually stage, commit, or push outside the approved delivery flow
- keep policy scopes narrow
- prefer docs/tests/source changes only within the approved task scope
- stop on forbidden files, secret risk, failed validation, usage limit, unclear worker output, or ambiguous state
- do not add UI or product polish when the active priority is Codex CLI automation

## Backup And Recovery

Source code is backed up by GitHub.

Devo workspace/context/runtime state is backed up under:

```text
G:\My Drive\Projects\Dev Orchestrator
```

Scheduled workspace backup exists. A full source mirror to Google Drive is not required because GitHub is the source-code backup. Old `.incomplete` backup folders are not automatically blockers; they usually mean an interrupted or failed backup attempt and should be interpreted with the latest successful backup.

## Roadmap

The next supervised automation sequence should stay narrow:

1. TASK-DEVO-191: `queue-worker-loop --auto-validation`
2. TASK-DEVO-192: deterministic auto-review helper
3. TASK-DEVO-193: Codex worker auto-run/auto-ingest hardening
4. TASK-DEVO-194: bulk approve bounded safe queue/policy set
5. TASK-DEVO-195: supervised `auto-run-approved` sequential loop

## New Model Starting Instructions

When a new model starts:

1. Read this file first.
2. Then read `docs/current-state.md`, `docs/usability-roadmap.md`, `docs/how-to-use-devo.md`, `docs/decision-log.md`, and `docs/recovery-and-backup.md`.
3. Inspect the latest Git log.
4. Inspect current Devo queue/policy status.
5. Continue from the next approved/pending task unless Manas redirects.
6. Preserve safety boundaries even if the conversation context is incomplete.
