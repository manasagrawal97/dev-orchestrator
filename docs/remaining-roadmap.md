# Remaining Devo Roadmap

## Purpose

This document is the current source of truth for remaining Devo product work after TASK-DEVO-073A. It reprioritizes future tasks around the final desired workflow instead of around isolated CLI or dashboard conveniences.

Product name: Devo / DevOrchestrator.

Devo is not a replacement for Codex, Cursor, Claude Code, or ChatGPT. Devo is a local-first software-development company operating system around AI workers. Codex CLI/Desktop remains the default personal/local worker. Direct API/model agents are optional future scope, not the default path.

## Current Completed Capabilities

Devo already has:

- project registration, scanning, and context lifecycle
- runs and work packages
- lanes, scope templates, `work resume`, and `work new`
- approvals, approval bundles, and policy gates
- validation command registry and validation runner
- Git delivery checks and delivery reports
- project, run, handoff, history, and activity reports
- backup, recovery, and doctor health checks
- generated visual reports
- current project/run context shortcuts
- project settings and guided onboarding
- UI-ready read models and JSON output
- local read-only FastAPI API
- React dashboard MVP
- UI polish and API/read-model performance work
- UI helper commands for dashboard URLs/status/open
- UI action safety model
- limited workspace-safe UI actions
- company-model vision docs
- Project Brief and Blueprint planning artifacts
- Backlog and Task planning artifacts
- Backlog refinement handoff prompt and import validation
- Batch planning artifacts and deterministic batch selection
- Count-based planning progress summaries
- Execution queue state tracking
- Codex handoff prompt generation from queue, batch, and task artifacts
- Workspace-only Codex worker run tracking records
- Manual Codex worker report templates, validation, import, show, and list commands
- Read-only Worker Runs dashboard page
- Read-only Codex worker preflight checks and run-plan preview artifacts
- Supervised one-run Codex CLI execution prototype behind approved run plans and `--confirm-execute`
- Read-only UI Planning Intake page
- Read-only UI Blueprint and Backlog detail pages
- Read-only UI Batch, Queue, Handoff, and Progress detail pages
- Explicit workspace-only Batch approval/review artifacts and decisions

These capabilities make Devo a useful local control plane today. TASK-DEVO-085 completed the first full planning-pipeline dogfood run and showed the next gap is operator guidance/input robustness rather than more planning primitives.

## Final Target Workflow

The intended workflow is:

1. Discuss the project with ChatGPT or another advisor.
2. Paste the final project brief into Devo.
3. Devo stores the project brief.
4. Devo creates blueprint, backlog, and task artifacts using templates and/or Codex CLI planning handoff prompts.
5. The user approves the plan or a batch.
6. Codex executes approved tasks.
7. Devo tracks validation, delivery, commits, progress, reports, and evidence.
8. The user reviews completed batches when free.
9. Devo resumes the approved queue when Codex usage resets or the user returns.

This keeps ChatGPT as the strategy partner, Codex as the local worker, and Devo as the manager, memory, safety, and progress system.

## Reprioritized Phases

### Phase 1: Planning Pipeline Foundation

- Project Brief model
- Blueprint model
- Backlog/task model
- Dependency, risk, and lane mapping
- Batch model
- Progress model

### Phase 2: Codex Handoff And Execution Queue

- Codex handoff prompt generation
- task execution prompt generation
- batch execution prompt generation
- queue state machine
- pause/resume
- usage-limit pause reason
- blocked task handling

### Phase 3: UI Planning And Progress Pages

- Planning Intake page
- Blueprint page
- Backlog page
- Batch Queue page
- Progress dashboard
- Review Batch page

### Phase 4: Controlled Workflow Actions

- create brief from UI
- approve blueprint
- approve batch
- generate Codex prompt
- mark task or batch reviewed
- controlled request approval bundle
- controlled validation display
- no commit, push, build, or test buttons until the safety model matures

### Phase 5: Worker And Agent Architecture

- manual worker mode
- Codex CLI handoff mode
- Codex CLI worker adapter
- optional model/API adapters
- future actual AI agents by role

### Phase 6: Future Polish And Advanced Capabilities

- persistent read-model snapshot cache if needed
- better report viewer
- better visuals and progress charts
- backup page polish
- packaging and start/stop improvements
- notifications
- mobile-friendly UI
- optional general planning chat

## Specific Next Task Order

1. TASK-DEVO-074: Project Brief + Blueprint data model - completed.
2. TASK-DEVO-075: Backlog/task data model - completed.
3. TASK-DEVO-076: Blueprint-to-backlog planning handoff prompt - completed.
4. TASK-DEVO-077: Batch model and batch selection - completed.
5. TASK-DEVO-078: Progress calculation and project completion percent - completed.
6. TASK-DEVO-079: Execution queue state machine - completed.
7. TASK-DEVO-080: Codex handoff prompts for next task/batch - completed.
8. TASK-DEVO-081: UI Planning Intake page - completed.
9. TASK-DEVO-082: UI Blueprint/Backlog pages - completed.
10. TASK-DEVO-083: UI Batch Queue and Progress dashboard - completed.
11. TASK-DEVO-084: Batch approval/review workflow - completed.
12. TASK-DEVO-085: End-to-end workflow dogfood run on DevOrchestrator - completed.
13. TASK-DEVO-086: Planning pipeline operator guidance and input robustness - completed.
14. TASK-DEVO-087: Codex CLI worker adapter design doc - completed.
15. TASK-DEVO-088: Worker run/report data model - completed.
16. TASK-DEVO-089: Manual execution report import - completed.
17. TASK-DEVO-090: Worker run UI visibility and review affordance polish - completed.
18. TASK-DEVO-091: Codex CLI worker preflight and run-plan model - completed.
19. TASK-DEVO-092: Supervised Codex CLI adapter prototype - completed.
20. TASK-DEVO-093: Queue integration for one item at a time - completed.
21. TASK-DEVO-094: Validation/review evidence integration - completed.
22. TASK-DEVO-095: Review-gated queue completion safeguards - completed.
23. TASK-DEVO-096: Pause/resume and usage-limit recovery polish.
24. TASK-DEVO-097: Optional commit/push delivery integration after safety review.
25. TASK-DEVO-098+: optional API/model agents, notifications, packaging, advanced UI, and other polish.

## Intentionally Deprioritized Now

- PersonalOS feature work
- full AI chat inside Devo
- OpenAI, Claude, Gemini, or local model API agents
- replacing Codex, Cursor, Claude Code, or ChatGPT
- fully autonomous unapproved execution
- commit, push, build, or test buttons in the UI
- backup restore/delete UI
- scheduler modification UI
- public SaaS or multi-user deployment
- persistent DB/SQLite cache unless performance demands it

## Completion Estimate

Current estimate:

- Practical personal-use Devo: around 65-70% complete.
- Long-term ideal Devo: around 40-45% complete.

The completion target for returning more focus to other projects is:

- brief intake
- blueprint/backlog
- batch approval
- Codex handoff
- progress tracking
- UI progress visibility
- one dogfood end-to-end run

That dogfood point has now been reached. Devo can be considered around 80-85% complete for personal use, with the next work focused on making the proven manual pipeline smoother and less surprising.

## Decision Rules For Future Task Selection

- Prefer features that move toward the final brief -> blueprint -> backlog -> batch -> execution queue workflow.
- Avoid unrelated UI buttons.
- Avoid premature API-agent work.
- Keep Codex CLI/manual mode first-class.
- Every new workflow feature must preserve safety, audit trail, and target repository boundaries.
- UI actions must go through the action safety model.
- Workspace-safe actions are acceptable before target-mutating actions.
- Target-mutating actions require explicit approval and mature safety design.
