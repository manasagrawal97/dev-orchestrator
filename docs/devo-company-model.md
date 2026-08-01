# Devo Company-Model Vision

## Devo Final Vision

Devo, or DevOrchestrator, is a local-first AI development orchestrator.

Devo is not intended to replace Codex, Cursor, Claude Code, or ChatGPT. Those tools are workers and advisors. Devo manages the software-development workflow around them: brief intake, planning, scope control, approvals, validation evidence, delivery evidence, progress state, recovery, and handoff.

The product shape is closer to a software-development company operating system for personal projects than to an AI chat or IDE clone. Devo should know what project is active, what plan has been approved, what batch is next, what Codex should do, what validation proves, what was delivered, and how work resumes after an interruption.

The product name remains Devo / DevOrchestrator.

The implementation order for the remaining company-model work is tracked in `docs/remaining-roadmap.md`.

## Company Analogy

Devo models the responsibilities of a small software company:

- User / owner: final decision maker, priority setter, and approval authority.
- ChatGPT, Claude, Cursor Chat, or similar chat tools: strategy and refinement advisors.
- Product Owner: project brief, requirements, and success criteria.
- Manager: workflow, batch, lane, queue, and progress manager.
- Architect: blueprint and architecture planner.
- Developer: Codex CLI implementer for local/personal development by default.
- Reviewer: feature and code review role.
- QA: validator that checks registered validation evidence.
- Security / Compliance: policy, risk, approval, and final audit roles.
- Release Manager: Git delivery, commit readiness, push guidance, and delivery reports.

Current Devo implements the structure and process for these roles through deterministic services, commands, templates, rules, and artifacts. Future Devo can attach AI workers to these roles, but the role contracts should remain stable and tool-agnostic.

## Current Devo Responsibility Model

Current Devo has responsibility separation, not true autonomous AI agents.

The current system is deterministic. It stores and evaluates state through coded modules and workspace artifacts, including:

- project onboarding
- context scanning and approval
- lanes
- work packages
- approval records and approval bundles
- validation registry and validation runs
- Git delivery checks and reports
- doctor health checks
- read models, local API, and dashboard
- generated visual reports
- backup and recovery support

These capabilities use rules, templates, schemas, CLI commands, and local files. They are not independent AI brains.

Today, intelligence comes from the user, ChatGPT, and Codex. Devo keeps the structure, memory, safety rails, and evidence trail around that intelligence.

## Future AI-Agent Model

A Devo agent should be understood as a contract:

- role
- allowed inputs
- expected output schema
- rules and stop conditions
- artifacts to read
- artifacts to write
- validation or approval gates

A worker backend is the execution mechanism attached to that contract. Worker backends may include:

- manual human/Codex operation
- Codex CLI
- ChatGPT API
- Claude API
- Gemini API
- local model adapters
- other future model or tool adapters

For personal/local development, the default future worker should be Codex CLI. It already works in the local repo, respects local files, and fits Devo's current CLI-first workflow.

Paid API/model agents are optional future scope. Devo should not require OpenAI, Claude, Gemini, or local model API tokens by default. Manual/Codex mode must remain first-class even if direct model adapters are added later.

Devo should stay model- and tool-agnostic: role contracts belong to Devo; specific AI workers are pluggable.

## Final Project Workflow

The intended end-to-end workflow is:

1. Discuss the project with ChatGPT or another advisor.
2. Paste the final project brief into Devo.
3. Devo stores the project brief.
4. Devo creates a blueprint, backlog, and tasks using templates and/or a Codex CLI planning worker.
5. The user approves the blueprint or the first implementation batch.
6. Codex executes approved tasks.
7. Devo tracks progress, validation, commits, reports, and evidence.
8. The user reviews completed batches when free.
9. Devo resumes the approved queue when Codex usage resets or the user returns.

This flow lets ChatGPT remain the high-level reasoning partner, Codex remain the local worker, and Devo remain the operating system that turns discussion into auditable, resumable development.

## Blueprint, Backlog, And Batch Concepts

Future Devo should introduce durable planning artifacts:

- Project Brief: the user's final summary of what the project is and what should be built.
- Blueprint: the high-level product and architecture plan.
- Milestones: larger outcome groups.
- Epics: related work areas inside a milestone.
- Tasks: implementable units of work.
- Dependencies: ordering and blocking relationships.
- Risk levels: low, medium, high, or critical safety classification.
- Lanes: execution modes such as docs-only, low-risk UI maintenance, small bugfix, small feature, test-only, or Devo internal source.
- Batches: reviewed and planning-approved groups of tasks that can be executed together after a separate queue step.
- Execution Queue: ordered approved work waiting for Codex or another worker.
- Progress percent: transparent progress across blueprint, backlog, milestone, batch, and task levels.
- Batch review: user review of delivered work and evidence.
- Resume / pause: stop and continue around user availability, worker failures, and Codex usage limits.

These concepts should build on existing Devo work packages, lanes, approvals, validation, work history, reports, read models, and UI action safety.

TASK-DEVO-074 adds the first two durable planning artifacts: Project Brief and Blueprint. TASK-DEVO-075 adds deterministic Backlog and Task artifacts from the blueprint. TASK-DEVO-076 adds a Codex-ready planning handoff prompt plus refined-backlog validation/import, while still avoiding direct Codex or AI API execution. TASK-DEVO-077 adds planning Batch artifacts and deterministic batch selection. TASK-DEVO-078 adds count-based progress summaries across tasks, milestones, epics, and batches. TASK-DEVO-079 adds execution queue state tracking. TASK-DEVO-080 adds Codex-ready handoff prompts for queue items, tasks, and batches. TASK-DEVO-084 adds explicit Batch approval/review artifacts and decisions. Batch approval is planning approval only: queue creation, Codex handoff, validation, delivery, and target project edits stay separate. Direct worker automation and AI/API execution models remain future work.

## Codex CLI Worker Strategy

Codex CLI/Desktop should be Devo's default intelligence and implementation worker for local personal development.

Devo should generate structured handoff prompts for Codex:

- project context
- current brief or blueprint
- approved batch scope
- allowed files and changes
- forbidden files and changes
- validation commands
- stop conditions
- final report expectations

TASK-DEVO-080 implements this as manual prompt generation under `workspace/projects/<project>/planning/handoffs/`. The user still pastes the generated prompt into Codex; Devo does not invoke Codex CLI or run target project commands.

Later, Devo may support controlled Codex CLI worker integration. That integration should remain bounded by Devo approvals, lanes, validation commands, Git delivery checks, and policy rules.

If Codex hits usage limits, errors, or availability limits, Devo should pause the queue honestly and preserve the next resume point. When usage resets or the user returns, Devo should resume from the approved queue without requiring the user to reconstruct context from chat history.

Devo should not require OpenAI API tokens by default.

## Chat And Intake Strategy

Devo should not build a general AI chat clone first.

The first product feature should be Project Brief / Planning Intake:

- user discusses the project in ChatGPT, Claude, Cursor Chat, or another preferred advisor
- user pastes the final distilled brief into Devo
- Devo stores the brief and turns it into planning artifacts
- Devo creates or helps create blueprint/backlog/tasks
- Devo queues approved batches for Codex execution

Later, Devo may support Codex-powered planning sessions or optional direct AI chat/API planning. That should remain future scope until the brief, blueprint, backlog, batch, queue, approval, and resume model is solid.

## Success Criteria

Devo reaches the intended personal-use goal when:

- the user can create or import a project brief
- Devo creates blueprint, backlog, and task artifacts
- the user can approve batches
- Codex can execute approved tasks
- Devo tracks progress, validation, delivery, commits, reports, and evidence
- the UI shows project, blueprint, batch, queue, and task progress
- work can pause and resume around Codex usage limits or user availability

The goal is not maximum autonomy. The goal is controlled, resumable, auditable AI-assisted development.

## Deferred Scope

Explicitly deferred:

- full general AI chat inside Devo
- paid AI API agents as the default mode
- replacing Codex, Cursor, Claude Code, or ChatGPT
- autonomous execution without approvals
- public SaaS or multi-user deployment
- unbounded target repository mutations from the UI
- build/test/commit/push/restore/scheduler/model actions without explicit Devo safety design
