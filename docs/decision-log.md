# Decision Log

This log records durable product decisions a future ChatGPT/Codex model should preserve.

## Product Direction

- Devo exists to automate AI-assisted software development, not to be a generic dashboard product first.
- The first priority is reducing manual PowerShell, Codex, ChatGPT, evidence, validation, and delivery copy-paste work.
- The current worker path is Codex CLI/Desktop first. Direct model/API agents remain future scope.
- UI/dashboard work should stay behind the CLI automation path unless Manas explicitly redirects.

## Operating Model

- Devo is a local-first, deterministic control plane.
- Human approval remains required for bounded work, risky changes, delivery, and unusual recovery.
- Devo should process approved work sequentially before any parallel execution is considered.
- One queue item at a time is the default safe unit.
- The trusted delivery runner remains the only normal commit/push path for Devo-managed work.

## Planning And Scope

- Rough goal intake should become the front door for work.
- Intake materialization should create draft tasks, batch, queue, and policy artifacts without approving anything.
- `intake-next-slice` should recommend the safest narrow next slice.
- `intake-policy-create-next` should create a narrow draft policy from the recommended next slice.
- Broad materialized policies can remain draft while narrow policies are approved one at a time.

## Evidence And Automation

- Worker result, review, validation, delivery request, runner result, commit, and push evidence should remain visible and auditable.
- Automatic validation evidence is allowed only after approved policy, completed worker evidence, passed review, and policy/run linkage are present.
- Review evidence is still manual until a deterministic helper is designed and tested.
- Patch proposal evidence is not completed work until an explicit checked/apply/accept flow turns it into real working-tree changes and normal evidence gates pass.

## Safety Decisions

- Do not touch PersonalOS unless the user explicitly asks.
- Do not bypass trusted runner delivery.
- Do not stage, commit, or push manually for Devo-managed delivery unless a task explicitly says normal Git delivery is allowed.
- Stop on forbidden files, secret risk, failed validation, usage limit, unclear worker output, dirty repo ambiguity, scheduler drift, missing evidence, or policy mismatch.
- Keep policy scopes narrow and explicit.

## Backup Decisions

- GitHub is the source-code backup.
- Google Drive backs up Devo workspace/context/runtime state.
- Full source mirroring to Google Drive is not required.
- Old `.incomplete` backup folders are warnings to inspect, not automatic blockers when newer successful backups exist.

## Current Roadmap Decision

After TASK-DEVO-190, the next automation chain is:

1. TASK-DEVO-191: optional auto-validation in `queue-worker-loop`
2. TASK-DEVO-192: deterministic auto-review helper
3. TASK-DEVO-193: Codex worker auto-run/auto-ingest hardening
4. TASK-DEVO-194: bulk approve bounded safe queue/policy set
5. TASK-DEVO-195: supervised `auto-run-approved` sequential loop
