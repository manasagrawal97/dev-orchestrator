# Phase 1 MVP Closure Plan

## 1. Phase 1 Definition

Devo Phase 1 is a local-first development operating system that can onboard projects, capture plans, create backlog/tasks/batches/queues, prepare Codex handoffs, track worker runs/reviews, validate delivery readiness, and safely deliver changes through guarded commit/push.

Phase 1 does not mean Devo is fully autonomous. Phase 1 means Devo can reliably manage the workflow around Codex/manual execution. ChatGPT and Manas still choose direction, Codex still implements bounded work, and Devo records the operating state, safety gates, evidence, delivery artifacts, and recovery trail.

## 2. Current Completed Capabilities

Completed Phase 1 capabilities include:

- Project onboarding, registration, settings, doctor checks, and current-context shortcuts.
- Scanner/context lifecycle with approved project context, refresh drafts, and context summaries.
- Agent and prompt registry for discovery, review, handoff, and deterministic operator prompts.
- Planning pipeline for Project Brief, Blueprint, backlog, tasks, batches, and progress summaries.
- Batch selection, batch approval/review artifacts, work packages, approval bundles, and built-in lanes.
- Execution queue state tracking, Codex handoff prompts, and queue-first worker preparation.
- Worker run tracking, manual worker report import, worker review tracking, validation evidence, and review-gated queue completion.
- Delivery readiness checks, delivery plans, delivery approvals, delivery reports, guarded commit, guarded push, delivery latest status, and the trusted local delivery runner.
- Read-only API and UI dashboards for projects, planning, workers, queues, delivery, health, and activity.
- Backup/status/doctor utilities, scheduled backup health guidance, generated visual reports, and recovery runbooks.

## 3. Proven Workflow After TASK-DEVO-118

The proven local delivery workflow is:

```text
ChatGPT/Manas decide next task
-> Codex implements and validates
-> Codex creates delivery runner request
-> Manas runs one runner command from normal PowerShell
-> Devo performs guarded delivery
-> repo returns clean
```

Runner command pattern:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project DevOrchestrator --request <REQ-ID> --approver "Manas" --confirm-runner-delivery
```

The runner does not bypass safety. It re-runs delivery readiness, compares the current changed files to the request snapshot, creates a plan, records approval, prepares a report, previews the commit, runs guarded commit, previews push, and runs guarded push.

## 4. What Phase 1 Is Not

Phase 1 is not:

- A Codex/Cursor/Claude Code clone.
- A fully autonomous AI developer.
- A background daemon.
- A webhook automation system.
- A cloud SaaS product.
- An API-token-first agent framework.
- A system that bypasses human approval.
- A system that commits or pushes without guarded delivery.

## 5. Remaining Phase 1 Tasks

### TASK-DEVO-120: Operator Workflow Polish After Trusted Runner - Completed

Goal: Make the everyday post-Codex operator flow smoother now that the trusted runner exists.

Why it matters: The runner removed the longest manual delivery sequence, but operators still need clear handoff text, status checks, and recovery guidance around it.

Expected scope: Docs, command wording, operator prompts, small status/read-model polish, and possibly delivery runner list/show output improvements.

What not to touch: No new delivery safety behavior, no daemon/service, no UI commit/push buttons, no AI-agent implementation, no PersonalOS changes.

Done criteria: A normal post-Codex handoff clearly tells Manas what changed, what passed, which runner request exists, and the exact one-command delivery instruction.

Result: `delivery latest` and `delivery runner-latest` now surface runner request/run/commit/push state and the exact pending normal PowerShell command. `runner-request` output includes changed/warning/blocker counts and artifact path context, while successful `runner-run` output clearly reports completion, commit hash, push target, and the next `git status` check.

### TASK-DEVO-121: Vision-To-Batch Intake Polish

Goal: Make it easier to move from a human project idea into Project Brief, Blueprint, backlog, and approved batch artifacts.

Why it matters: Phase 1 should feel like a usable local operating system, not a pile of separate planning commands.

Expected scope: Scope-template guidance, brief/backlog/batch command wording, docs, examples, and deterministic intake prompts.

What not to touch: No AI API calls, no direct autonomous planning agents, no target repo source edits outside approved work packages.

Done criteria: A user can start with a short project idea and follow a clear local-first path to an approved implementation batch.

Result: `devo project intake-status`, `intake-next`, `intake-template`, and `intake-prompt` now give a compact rough-idea -> Project Brief -> Blueprint -> Backlog -> Batch -> Queue -> Handoff guide. Template/prompt writes stay under Devo workspace planning artifacts and remain planning-only.

### TASK-DEVO-122: Phase 1 Context And Workflow Efficiency Audit

Goal: Audit whether Phase 1 has become too verbose, artifact-heavy, or repetitive before adding Phase 2 intelligence.

Why it matters: AI workers and users both suffer when context is noisy. Phase 1 should be sturdy but not burdensome.

Expected scope: Read docs, generated artifacts, prompts, read models, API/UI summaries, and common operator flows; produce recommendations.

What not to touch: No source behavior changes unless separately approved, no Phase 2 implementation, no cleanup that deletes evidence.

Done criteria: A concise audit identifies what to simplify, what to keep, what to archive/document, and what should wait.

Result: `docs/phase-1-context-workflow-efficiency-audit.md` records a `watch` verdict. Phase 1 is healthy enough to proceed, but task prompts, duplicated docs, artifact navigation, and command-count friction should be simplified after the end-to-end dogfood rather than adding more features now.

### TASK-DEVO-123: End-To-End Phase 1 Dogfood On DevOrchestrator

Goal: Run a representative Devo self-development task through the full Phase 1 workflow.

Why it matters: Phase 1 should be proven by using Devo to manage Devo from planning through delivery.

Expected scope: Use existing planning, batch, queue, worker, review, validation, delivery, and runner features on a small safe task.

What not to touch: No PersonalOS changes, no real Codex CLI unless separately approved, no backup/restore/scheduler work, no Phase 2 agents.

Done criteria: A complete dogfood record shows planning, approval, implementation evidence, validation, review, runner delivery, and clean repo state.

### TASK-DEVO-124: Phase 1 MVP Tag/Checkpoint

Goal: Mark Phase 1 as complete with a clear Git/docs checkpoint.

Why it matters: A checkpoint lets Phase 2 start from a known product state instead of a blurry transition.

Expected scope: Docs, release/checkpoint notes, tag guidance, current-state update, and final acceptance checklist.

What not to touch: No new feature work, no Phase 2 agents, no UI action expansion.

Done criteria: Phase 1 acceptance criteria are met, docs agree, the repo is clean, and the checkpoint is easy to recover from.

## 6. Phase 1 Acceptance Criteria

Phase 1 is complete when:

- A new task can be planned clearly.
- A batch can be approved.
- Codex can receive a scoped handoff.
- Worker output can be tracked.
- Review/validation can be recorded.
- Delivery can be safely completed through the trusted runner.
- The repo ends clean after delivery.
- User manual work is reduced to planning/review plus one delivery command.
- All major docs agree on the current workflow.

## 7. Manual Intervention Reduction

Before the trusted runner:

- Delivery required many commands.
- The operator had to remember the sequence.
- The next action could be unclear after validation.
- There was a higher risk of accidentally skipping a safety gate.

After the trusted runner:

- The operator runs one runner command from normal PowerShell.
- Devo performs the delivery sequence.
- Safety gates are preserved.
- Status artifacts are retained.

## 8. Phase 2 Boundary

Phase 2 means attaching AI brains/workers to the existing Devo role contracts and workflow states.

Examples of Phase 2 work include:

- AI-assisted Project Brief refinement.
- AI-assisted Blueprint generation.
- AI-assisted backlog/task generation.
- AI worker adapter registry.
- Multiple AI role workers.
- Local/API model adapters.
- Agent review loops.

These are deferred until Phase 1 closure. Phase 1 should prove that the workflow skeleton is useful, safe, and understandable before Devo starts adding more intelligence.

## 9. Token/Context/Workflow Efficiency Audit

TASK-DEVO-122 should explicitly review:

- Whether docs are too many or too verbose.
- Whether Codex prompts are too long.
- Whether tasks need too much repeated context.
- Whether Devo generated artifacts are becoming noisy.
- Whether the current workflow creates unnecessary files.
- Whether read models/API/UI are becoming slow.
- Whether the system is over-engineered for personal use.

The audit should preserve useful evidence while reducing repeated context and operator fatigue.

## 10. Risks And Open Questions

Current risks and open questions:

- Documentation drift across many docs.
- Too many artifacts for simple personal tasks.
- Over-building before enough dogfooding.
- Manual planning still depends on ChatGPT.
- The runner is explicit, not a daemon.
- Codex sandbox still cannot commit directly.
- The UI is still mostly read-only.
- Phase 2 AI integration could make the system more expensive or less predictable if added too early.

## 11. Recommended Next Task

Recommended next task:

```text
TASK-DEVO-122: Phase 1 context and workflow efficiency audit
```

Now that the delivery runner workflow and vision-to-batch intake path are easier to inspect and resume, the next value is checking whether Phase 1 has become too verbose, artifact-heavy, or repetitive before adding more intelligence.
