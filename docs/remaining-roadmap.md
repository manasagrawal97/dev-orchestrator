# Remaining Devo Roadmap

## Purpose

This document tracks post-Phase-1 Devo product work. The Phase 1 MVP checkpoint is `docs/phase-1-mvp-checkpoint.md`; the active Phase 2 autonomy plan is `docs/phase-2-autonomy-roadmap.md`.

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
- Codex launcher diagnostics, WindowsApps blocking, explicit path support, and local wrapper support
- Codex launcher setup and real supervised dry-run runbooks
- Delivery safety design before commit/push automation
- Delivery readiness checks before delivery plan/approval automation
- Delivery plan and approval artifacts before commit/push automation
- Delivery report, commit-message preparation, guarded CLI commit, guarded CLI push, isolated delivery dogfood, and read-only Delivery UI visibility
- Delivery latest status and trusted local delivery runner for one-command normal-PowerShell delivery after Codex validation
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
23. TASK-DEVO-096: End-to-end supervised worker dogfood - completed.
24. TASK-DEVO-097: Worker flow operator polish - completed.
25. TASK-DEVO-098: Real Codex supervised dry-run checklist - completed.
26. TASK-DEVO-099: First real Codex supervised dry-run execution report - completed.
27. TASK-DEVO-100: Harden real Codex launch path and launch-failure handling - completed.
28. TASK-DEVO-101: Retry real Codex dry-run with explicit launcher path - blocked by missing non-WindowsApps launcher.
29. TASK-DEVO-102: Codex wrapper/launcher support before real retry - completed.
30. TASK-DEVO-103: Codex launcher setup runbook and readiness checklist - completed.
31. TASK-DEVO-104: Delivery and commit safety design - completed.
32. TASK-DEVO-105: Delivery readiness data model and check command - completed.
33. TASK-DEVO-106: Delivery plan and approval workflow - completed.
34. TASK-DEVO-107: Delivery report and commit message preparation - completed.
35. TASK-DEVO-108: Controlled commit command with `--confirm-commit` - completed.
36. TASK-DEVO-109: Controlled push command with `--confirm-push` - completed.
37. TASK-DEVO-110: End-to-end guarded delivery dogfood on isolated temp repo - completed.
38. TASK-DEVO-111: Delivery operator polish and read-only Delivery UI - completed.
39. TASK-DEVO-113: Delivery report recovery and refresh after retryable guarded commit failure - completed.
40. TASK-DEVO-114: Delivery commit diagnostics and index.lock failure hardening - completed.
41. TASK-DEVO-115: Live delivery dogfood closure and normal-PowerShell operating rule - completed.
42. TASK-DEVO-116: Guarded commit context preflight before staging - completed.
43. TASK-DEVO-116A: Delivery README/docs secret-risk false-positive reduction - completed.
44. TASK-DEVO-117: Delivery latest status command - completed.
45. TASK-DEVO-118: Trusted local delivery runner - completed.
46. TASK-DEVO-119: Phase 1 MVP closure plan - completed.
47. TASK-DEVO-120: Operator workflow polish after trusted runner - completed.
48. TASK-DEVO-121: Vision-to-batch intake polish - completed.
49. TASK-DEVO-122: Phase 1 context and workflow efficiency audit - completed.
50. TASK-DEVO-123: End-to-end Phase 1 dogfood on DevOrchestrator - completed.
51. TASK-DEVO-124: Phase 1 MVP tag/checkpoint - completed.
52. TASK-DEVO-125: Phase 2 autonomy roadmap and trusted execution model - completed.
53. TASK-DEVO-126: Trusted runner watch mode - next recommended task.
54. Post-Phase-1 polish: artifact/index compaction, docs consolidation, prompt simplification, progress/read-model polish, UI polish, optional API/model agents, notifications, packaging, advanced UI, and other polish.

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

That dogfood point has now been reached and recorded in the Phase 1 MVP checkpoint. Devo can be considered around 80-85% complete for personal use, with the next work focused on post-Phase-1 polish and carefully bounded Phase 2 planning.

TASK-DEVO-121 added that smoother intake layer with `devo project intake-status`, `intake-next`, `intake-template`, and `intake-prompt`. TASK-DEVO-122 then audited context size, artifact noise, operator repetition, and documentation overlap with a `watch` verdict. TASK-DEVO-123 dogfooded the current path and found no checkpoint blocker. TASK-DEVO-124 records the final checkpoint and the `phase-1-mvp` tag now exists. TASK-DEVO-125 moves active focus to practical Phase 2 autonomy, with TASK-DEVO-126 trusted runner watch mode as the recommended next step.

## Decision Rules For Future Task Selection

- Prefer features that move toward the final brief -> blueprint -> backlog -> batch -> execution queue workflow.
- Avoid unrelated UI buttons.
- Avoid premature API-agent work.
- Keep Codex CLI/manual mode first-class.
- Every new workflow feature must preserve safety, audit trail, and target repository boundaries.
- UI actions must go through the action safety model.
- Workspace-safe actions are acceptable before target-mutating actions.
- Target-mutating actions require explicit approval and mature safety design.
