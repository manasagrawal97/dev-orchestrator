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
- Policy-gated queue-worker loop v1 for preparing one approved queue item, pausing at handoff/worker readiness, continuing through worker report/review/validation evidence, and creating trusted delivery runner requests safely
- Queue-worker evidence schema v1 for worker result, review, and validation records
- Queue-worker dogfood friction polish for evidence-intake next actions, non-passing validation wording, assisted-policy wording, temp dogfood remote guidance, and runner-watch/latest-request diagnostics
- Read-only UI Planning Intake page
- Read-only UI Blueprint and Backlog detail pages
- Read-only UI Batch, Queue, Handoff, and Progress detail pages
- Explicit workspace-only Batch approval/review artifacts and decisions
- Codex subprocess config and dry-run run-preview artifacts without launching Codex
- One-task Codex subprocess execution command with fake-command tests, plus a disposable `Dogfood152` real-run preparation that reaches preview and defers real Codex launch to normal PowerShell; TASK-DEVO-153 hardens the real Codex CLI command shape and strict JSON result boundary
- One-item Codex worker batch-run coordinator that selects an approved queue item, prepares a prompt package, runs one configured subprocess, ingests strict JSON, writes batch-run artifacts, and stops at review without automatic validation, delivery, commit, push, queue completion, or parallel work
- Real Codex multi-item continuation dogfood on disposable `Dogfood162`, proving two queue items can complete one at a time through real subprocess execution, strict JSON ingest, manual evidence gates, trusted runner delivery, and final all-completed guidance
- Real Codex batch-run readiness checkpoint defining safe disposable use, narrow DevOrchestrator use, PersonalOS deferral, manual gates, and trusted-runner-only delivery
- Live DevOrchestrator real batch-run dogfood on a narrow docs-only policy, plus a dogfooded read-only consolidated batch-position summary for policy/queue/worker/Codex/evidence/delivery/runner/commit/push state and one safe next command
- Patch-proposal fallback v1 for blocked/failed Codex worker results, preserving proposed `.patch`/`.diff` artifacts as manual-review evidence without automatic apply, validation, delivery, commit, or push; TASK-DEVO-170 dogfoods this with fake blocked evidence and explicit ingest/evidence/summary readouts
- Read-only patch proposal show/check commands that inspect proposal evidence and run explicit non-mutating checks with policy-scope, forbidden-path, clean-worktree, and `git apply --check` gates; TASK-DEVO-173 dogfoods the existing fake blocked evidence and improves summary guidance toward `patch-proposal-show`
- Reviewed patch-proposal apply v1, requiring a successful matching check artifact, explicit reviewer and confirmation, clean worktree, policy-scope rechecks, and audit artifacts while leaving files unstaged and avoiding review/validation/delivery/queue completion
- Inline patch proposal materialization during confirmed worker-result ingest, using canonical `patch_proposal_text`, so real Codex blocked results that include patch text but no `patch_artifact_path` can still flow through `patch-proposal-show` and `patch-proposal-check` as workspace `.patch` artifacts without becoming successful/applied evidence
- Reviewed patch-apply design and v1 explicit operator apply flow with dry-run apply preflight, policy-scope checks, clean-worktree requirements, strict or explicitly confirmed whitespace-tolerant apply modes, audit artifacts, and no commit/push or queue completion
- Sheetless rough-goal intake MVP: `devo project intake-plan` converts a rough Markdown goal file into workspace-only candidate tasks, draft batch/queue/policy suggestions, allowed file patterns, risk notes, and next commands without creating approvals or execution artifacts

These capabilities make Devo a useful local control plane today. TASK-DEVO-085 completed the first full planning-pipeline dogfood run and showed the next gap is operator guidance/input robustness rather than more planning primitives. TASK-DEVO-162 shows the Phase 2 Codex-worker path can continue across multiple real disposable items while keeping review, validation, and trusted delivery gates explicit. TASK-DEVO-164 proves the same real Codex batch-run operating mode on a narrow live DevOrchestrator docs-only batch, TASK-DEVO-165 adds the consolidated read-only batch-position summary, and TASK-DEVO-166 proves that summary gives a clear terminal view for completed live policy `POL-0002`. TASK-DEVO-167 then found a safe blocker for live code edits: the Codex subprocess could inspect approved files but could not update existing files, so TASK-DEVO-168 records diagnostics, TASK-DEVO-169 adds patch-proposal fallback v1 for preserving proposed patches without applying them automatically, TASK-DEVO-170 dogfoods that fallback with fake blocked evidence, TASK-DEVO-171 designs reviewed patch apply, TASK-DEVO-172 adds safe show/check commands before any apply implementation, TASK-DEVO-173 proves those commands keep existing fake blocked patch evidence out of normal gates, TASK-DEVO-174 adds explicit reviewed apply without making it a completion or delivery signal, TASK-DEVO-175 proves reviewed apply with a fake safe patch, TASK-DEVO-176 closes the inline-patch artifact gap found by the first real patch-proposal fallback run, TASK-DEVO-177 adds the missing canonical `patch_proposal_text` contract field discovered by the real retry, TASK-DEVO-178 tightens that contract after proving materialized inline patches must be valid `git apply`-compatible unified diffs before they can enter reviewed apply, TASK-DEVO-179 adds an explicit audited whitespace-tolerant mode for patches that strict check rejects but Git can check/apply with whitespace tolerance, and TASK-DEVO-181 shifts the next usability push toward sheetless rough-goal planning so Manas can move from discussion to Devo intake artifacts without maintaining a manual spreadsheet.

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
53. TASK-DEVO-126: Trusted runner watch mode - completed.
54. TASK-DEVO-127: Windows scheduled/background trusted runner - completed.
55. TASK-DEVO-128: Batch execution policy and approval contract - completed.
56. TASK-DEVO-129: Autonomous queue worker loop - completed.
57. TASK-DEVO-130: Failure pause/resume and usage-limit handling - completed.
58. TASK-DEVO-131: Worker-result continuation and delivery-request handoff - completed.
59. TASK-DEVO-132: Queue-worker assisted end-to-end dogfood - completed.
60. TASK-DEVO-133: One-task assisted queue-worker step - completed.
61. TASK-DEVO-134: Batch continuation loop for one task at a time - completed.
62. TASK-DEVO-138: Polished assisted dogfood with known-good delivery path - completed.
63. TASK-DEVO-139: Scheduled runner reliability and health self-check - completed.
64. TASK-DEVO-139A: Scheduler health environment-context clarification - completed.
65. TASK-DEVO-140: Approved queue auto-run v1 - completed.
66. TASK-DEVO-141: Worker result evidence schema v1 - completed.
67. TASK-DEVO-142: Lightweight handoff checklist v1 - completed.
68. TASK-DEVO-143: Live 3-5 task assisted queue dogfood - completed.
69. TASK-DEVO-144: Assisted queue continuation polish after dogfood - completed.
70. TASK-DEVO-145: Codex worker launch/integration design - completed.
71. TASK-DEVO-146: Codex worker prepare/prompt-file mode v1 - completed.
72. TASK-DEVO-147: Codex worker result ingest v1 - completed.
73. TASK-DEVO-148: Prompt-file Codex worker dogfood - completed.
74. TASK-DEVO-149: Codex subprocess execution design checkpoint - completed.
75. TASK-DEVO-150: Codex subprocess configuration and dry-run launcher v1 - completed.
76. TASK-DEVO-151: One-task Codex subprocess execution v1 - completed.
77. TASK-DEVO-152: Real Codex subprocess dogfood for one safe disposable task - prepared through preview.
78. TASK-DEVO-153: Codex subprocess dogfood hardening and recovery polish - completed.
79. TASK-DEVO-154: Batch Codex-worker loop design - completed.
80. TASK-DEVO-155: Batch Codex-worker loop v1 implementation - completed.
81. TASK-DEVO-156: Batch-run fake-worker dogfood on disposable `Dogfood156` - completed.
82. TASK-DEVO-157: Batch-run dogfood polish and disposable delivery readiness - completed.
83. TASK-DEVO-158: Real Codex batch-run dogfood for one disposable item - completed.
84. TASK-DEVO-159: Real Codex batch-run readout polish - completed.
85. TASK-DEVO-160: Multi-item fake-worker batch continuation dogfood - completed.
86. TASK-DEVO-161: Batch continuation friction polish - completed.
87. TASK-DEVO-162: Real Codex multi-item batch dogfood on disposable `Dogfood162` - completed.
88. TASK-DEVO-163: Real Codex batch-run readiness checkpoint and polish - completed.
89. TASK-DEVO-164: DevOrchestrator real batch-run narrow internal dogfood - completed.
90. TASK-DEVO-165: Consolidated real-batch position summary - completed.
91. TASK-DEVO-166: Real batch position summary dogfood - completed.
92. TASK-DEVO-167/TASK-DEVO-168: First narrow real DevOrchestrator code-task batch-run blocked safely; write-access diagnostics and patch-proposal fallback guidance added.
93. TASK-DEVO-169: Patch-proposal fallback v1 - completed.
94. TASK-DEVO-170: Patch-proposal fallback dogfood - completed.
95. TASK-DEVO-171: Reviewed patch-apply design - completed.
96. TASK-DEVO-172: Patch-proposal show/check v1 - completed.
97. TASK-DEVO-173: Patch-proposal show/check dogfood - completed; existing fake blocked evidence is inspectable and checkable without applying patches or advancing gates.
98. TASK-DEVO-174: Reviewed patch-proposal apply v1 - completed.
99. TASK-DEVO-175: Patch-proposal apply dogfood with fake safe patch - completed.
100. Next: complete post-apply evidence/delivery continuation dogfood before live source-code use.
101. Post-Phase-1 polish: artifact/index compaction, docs consolidation, prompt simplification, progress/read-model polish, UI polish, optional API/model agents, notifications, packaging, advanced UI, and other polish.

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

TASK-DEVO-121 added that smoother intake layer with `devo project intake-status`, `intake-next`, `intake-template`, and `intake-prompt`. TASK-DEVO-122 then audited context size, artifact noise, operator repetition, and documentation overlap with a `watch` verdict. TASK-DEVO-123 dogfooded the current path and found no checkpoint blocker. TASK-DEVO-124 records the final checkpoint and the `phase-1-mvp` tag now exists. TASK-DEVO-125 moves active focus to practical Phase 2 autonomy. TASK-DEVO-126 adds one-shot trusted runner watch mode. TASK-DEVO-127 adds scheduled/background trusted runner management around that watch mode, with real install/enable still explicit and local. TASK-DEVO-128 adds bounded batch execution policies. TASK-DEVO-129 adds the first policy-gated queue worker loop. TASK-DEVO-130 adds lifecycle status, pause, resume, fail, retry, and cancel controls for those queue-worker runs without adding real Codex automation. TASK-DEVO-131 adds evidence-gated continuation through worker report, review, validation, and trusted delivery runner request creation. TASK-DEVO-132 dogfoods that assisted path end to end in a temp project. TASK-DEVO-133 adds a one-task `queue-worker-step` command that chooses the next safe queue-worker transition and stops before any real Codex, validation execution, runner-watch, commit, push, or queue completion. TASK-DEVO-134 adds `queue-worker-loop`, which repeats that one-step behavior until the next safe stop condition and still avoids full autonomous development. TASK-DEVO-135 adds explicit queue-worker evidence intake commands for worker result, review, and validation records so the loop can be fed without running automation. TASK-DEVO-136 records a partial live three-task sandbox dogfood: item 1 reached delivery request, but failed temp trusted push blocked continuation safely. TASK-DEVO-138 proves the polished known-good temp delivery path. TASK-DEVO-139 makes scheduled runner status health explicit before approved queue auto-run depends on auto-delivery. TASK-DEVO-139A clarifies that Codex/sandbox drift can be environment visibility mismatch when normal PowerShell reports healthy. TASK-DEVO-140 adds `approved-queue-run` as a policy-first, scheduler-aware wrapper for the one-task queue-worker loop. TASK-DEVO-141 adds a shared worker/review/validation evidence schema so queue advancement can rely on one conservative shape. TASK-DEVO-142 adds a lightweight handoff checklist at the worker boundary before result evidence is recorded. TASK-DEVO-143 proves the approved queue run path across three disposable delivered tasks. TASK-DEVO-144 adds push-only runner recovery, `approved-queue-run --continue-next`, validation evidence wording polish, and latest/default `flow-summary` behavior. TASK-DEVO-145 designs the future Codex worker launch/integration path, TASK-DEVO-146 implements prompt-file assisted preparation before subprocess execution, TASK-DEVO-147 adds JSON result ingest so filled worker result files can become queue-worker evidence without running Codex, review, validation, delivery, commit, or push, TASK-DEVO-148 dogfoods that prompt-file loop end to end on a disposable project, TASK-DEVO-149 records the subprocess design checkpoint, TASK-DEVO-150 adds subprocess config/preview, TASK-DEVO-151 adds one-task subprocess execution, TASK-DEVO-152 prepares a real disposable Codex dogfood through preview, TASK-DEVO-153 hardens the command/output boundary before another real retry, TASK-DEVO-154 designs the batch Codex-worker loop, TASK-DEVO-155 implements the one-item fake-tested batch-run coordinator, TASK-DEVO-156 dogfoods it on disposable `Dogfood156`, TASK-DEVO-157 polishes its disposable delivery-readiness and option-discoverability friction, TASK-DEVO-158 proves one real disposable Codex batch-run item end to end through trusted runner delivery, TASK-DEVO-159 polishes the usage-limit, validation evidence, and completed-run readouts, TASK-DEVO-160 proves fake-worker continuation across three disposable items, TASK-DEVO-161 polishes the stale retry/completed-queue friction from that dogfood, TASK-DEVO-162 proves two-item real Codex continuation on disposable `Dogfood162`, TASK-DEVO-163 checkpoints the operating mode, TASK-DEVO-164 proves narrow live DevOrchestrator docs-only use, TASK-DEVO-165 adds a consolidated read-only batch-position summary, TASK-DEVO-166 dogfoods that summary against completed live policy `POL-0002`, TASK-DEVO-167/TASK-DEVO-168 records the first live code-task blocker where real Codex could inspect approved files but could not update existing files, TASK-DEVO-169/TASK-DEVO-170 preserve and dogfood patch-proposal evidence, TASK-DEVO-171 designs reviewed patch apply, TASK-DEVO-172 adds read-only show/check commands, TASK-DEVO-173 dogfoods those commands against existing fake blocked evidence, TASK-DEVO-174 adds explicit reviewed patch apply, and TASK-DEVO-175 dogfoods apply with a fake safe patch. The next safe step is completing the post-apply evidence/delivery continuation before live source-code use, without adding parallelism or weakening delivery safety.

Recent AI-workflow inspiration remains future-only: compare ECC / Everything Claude Code as a benchmark, keep Devo text-driven for now, defer voice/Jarvis/gesture/clap controls, avoid "300 agents" or parallel editing agents, and revisit least-privilege role permissions only after real worker roles exist.

## Decision Rules For Future Task Selection

- Prefer features that move toward the final brief -> blueprint -> backlog -> batch -> execution queue workflow.
- Avoid unrelated UI buttons.
- Avoid premature API-agent work.
- Keep Codex CLI/manual mode first-class.
- Every new workflow feature must preserve safety, audit trail, and target repository boundaries.
- UI actions must go through the action safety model.
- Workspace-safe actions are acceptable before target-mutating actions.
- Target-mutating actions require explicit approval and mature safety design.
