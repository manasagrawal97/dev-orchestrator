# Phase 1 Context And Workflow Efficiency Audit

## 1. Executive Summary

Verdict: `watch`.

Devo Phase 1 is healthy enough to proceed to the end-to-end dogfood, but it is close to becoming verbose for personal use. The core workflow is now useful: project intake, planning artifacts, queues, Codex handoffs, worker evidence, review gates, delivery checks, and trusted runner delivery all connect into one local-first operating path. The risk is not missing capability. The risk is operator fatigue from too many docs, commands, artifacts, and repeated safety context.

The trusted runner and intake helpers are doing the right job: they make long workflows easier to resume and reduce command-memory burden. The next step should not be another feature. The next step should be TASK-DEVO-123, a full Phase 1 dogfood, using the current workflow exactly as built.

## 2. Context And Prompt Size

Current task prompts are useful for safety, but they are too long for ordinary Phase 1 work. They often repeat:

- project path, target path, and repo status
- PersonalOS prohibitions even when the task is DevOrchestrator-only
- no backup/restore/scheduler/model/API warnings
- full validation and delivery boilerplate
- recent task history that is already in docs and Devo reports

This repetition protects boundaries, but it also causes delay and makes it harder for Codex to find the actual task. The prompts are still safer than short vague instructions, especially around delivery, PersonalOS, real Codex execution, and Windows/Git permission issues. The improvement should be standard structure, not removing safety.

Recommended remaining Phase 1 prompt structure:

1. Objective: one or two sentences.
2. Current state: only facts needed for this task.
3. Approved scope: exact files or artifact categories.
4. Safety boundaries: only boundaries relevant to this task.
5. Required commands: validation and delivery commands.
6. Stop conditions: when Codex must stop and report.
7. Final report: short required fields.

Avoid including long historical summaries unless the task is explicitly recovery or audit. Use Devo commands instead:

```powershell
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
.\.venv\Scripts\devo.exe project intake-status --project DevOrchestrator
.\.venv\Scripts\devo.exe report handoff --project DevOrchestrator
```

## 3. Documentation Overlap

Documentation is useful but duplicated. Some duplication is acceptable because each doc has a different recovery or operator role. The problem is that several docs now contain long task-history chains that can drift.

Canonical ownership:

| Doc | Canonical For | Audience |
| --- | --- | --- |
| `README.md` | entry point, install/use commands, high-level capabilities | operator and new reader |
| `docs/current-state.md` | current project state, latest completed work, next action | recovery and continuity |
| `docs/phase-1-mvp-closure-plan.md` | Phase 1 definition, acceptance criteria, remaining closure tasks | product checkpoint |
| `docs/remaining-roadmap.md` | active remaining task order | planning |
| `docs/roadmap.md` | broader historical roadmap and completed milestones | design/history |
| `docs/how-to-use-devo.md` | practical CLI workflows | operator |
| `docs/usability-roadmap.md` | UX/product direction and friction analysis | design |
| `docs/ui-mvp-spec.md` | UI scope and UI safety boundaries | UI design |
| `docs/delivery-safety-design.md` | delivery safety model and commit/push boundaries | safety design |

Acceptable duplication:

- safety boundaries in README and how-to docs
- current next task in current state and closure plan
- UI read-only warnings in UI docs and README
- delivery safety warnings in delivery docs and README

Duplication to reduce later:

- long completed task chains repeated in current state, roadmap, usability roadmap, and UI MVP spec
- detailed command examples repeated across README and how-to docs
- phase boundaries repeated in multiple docs instead of linking to the closure plan

Do not rewrite all docs before Phase 1 checkpoint. Add a later docs compaction task after TASK-DEVO-123 if the dogfood confirms the noise.

## 4. Artifact Noise

Devo has many workspace artifact categories:

- planning artifacts
- batch artifacts
- queue artifacts
- handoff artifacts
- worker run/report/review artifacts
- delivery checks/plans/reports/commits/pushes
- runner requests/runs
- backup artifacts
- visual reports

There are many artifacts, but most are useful because they are evidence, recovery points, or safety gates. The noisy part is not the existence of artifacts. The noisy part is navigation and indexing.

Useful artifacts:

- brief, blueprint, backlog, batch, queue, and handoff artifacts because they make planning replayable
- worker reports and reviews because they separate "Codex said it is done" from reviewed evidence
- delivery reports because they preserve commit/push safety decisions
- runner requests/runs because they bridge restricted Codex context to normal PowerShell
- backup inventory and incomplete backup markers because they explain recovery health

Noisy but acceptable artifacts:

- repeated delivery checks during the same work sequence
- visual reports that duplicate readable CLI summaries
- older runner requests after a run is delivered
- generated prompts once the corresponding task is complete

Deferred cleanup/indexing task:

- add an artifact activity/index view that groups by project, run/report id, status, and finality
- hide superseded or historical artifacts by default in UI
- keep all artifacts unless explicit retention/archival policy exists
- do not delete evidence automatically

## 5. Command Complexity

Devo has many command groups:

- project onboarding/current/intake
- planning brief/blueprint/backlog/batch/queue/handoff
- worker Codex commands
- worker review commands
- delivery latest/runner commands
- doctor/backup/status commands
- UI helpers

This is a lot, but the newest shortcuts reduce the everyday burden. The best current daily path is:

```powershell
.\.venv\Scripts\devo.exe project intake-status --project DevOrchestrator
.\.venv\Scripts\devo.exe project intake-next --project DevOrchestrator
.\.venv\Scripts\devo.exe project handoff-next --project DevOrchestrator --queue <queueId>
.\.venv\Scripts\devo.exe delivery runner-request --project DevOrchestrator --message "<message>" --note "<task note>"
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
```

Then Manas runs the generated `runner-run` command from normal PowerShell.

Later naming/guidance improvements:

- make `delivery latest` the primary recovery command and keep `runner-latest` as a runner-specific shortcut
- make planning pages and CLI consistently call the same path "intake -> brief -> blueprint -> backlog -> batch -> queue -> handoff"
- consider one "project next" command after Phase 1 that delegates to onboarding, intake, work, delivery, or runner next actions
- keep low-level commands, but make every high-level status command show the next low-level command

## 6. Performance And Read Model Risk

TASK-DEVO-069 already optimized read-model/API performance by adding optional timing breakdowns, bounding slow optional checks, adding Git read timeouts, and reducing duplicate doctor work. That was the right level of Phase 1 performance work.

Remaining risks:

- workspace files will grow over time
- delivery and runner histories will grow quickly during dogfood
- UI pages may load too much project data at once
- read models may repeatedly scan folders instead of using compact indexes
- old artifacts may make "latest useful state" harder to identify

No urgent blocker was found. The right future maintenance task is not a database yet. It is a read-model/index compaction task:

- ensure each artifact family has a reliable index
- make read models prefer indexes over folder scans
- add pagination or limits to UI/API history views
- preserve raw artifacts for recovery
- add timing regressions only if the UI becomes slow again

## 7. Safety Versus Speed

Safety gates are still justified, but the runner made them operationally acceptable.

Keep:

- index-lock preflight
- secret-risk blockers
- documentation secret warnings
- forbidden path checks
- approval artifacts
- delivery reports
- commit-preview and push-preview
- runner confirmation from normal PowerShell

The index-lock incident proved that Git delivery from restricted contexts is risky. The current rule is good: Codex/sandbox prepares a trusted runner request; normal PowerShell performs guarded delivery. Do not bypass that with manual Git commit/push during dogfood.

Documentation secret warnings can be noisy, but they are warnings rather than blockers for docs/README language. That balance is acceptable.

## 8. Phase 1 Simplification Recommendations

Do now:

- proceed to TASK-DEVO-123 before adding more features
- use `intake-status`, `delivery latest`, and `runner-latest` as recovery shortcuts
- standardize shorter task prompts for remaining Phase 1 work
- keep final reports short and evidence-based

Keep:

- trusted runner delivery
- read-only UI
- current safety gates
- docs canonical map
- workspace artifacts as evidence

Defer:

- artifact cleanup/index compaction
- command alias redesign
- UI write actions beyond existing workspace-safe actions
- daemon/service/background worker
- Phase 2 AI/model agents
- direct Codex `.git` permission fixes from Devo

Avoid:

- adding new features before TASK-DEVO-123
- weakening delivery safety to save a few commands
- deleting or rewriting historical evidence before the checkpoint
- moving commit/push into the UI

## 9. Remaining Phase 1 Task Impact

TASK-DEVO-123 should remain the next task. It should dogfood the complete Phase 1 path on DevOrchestrator with a small safe change:

- intake/status check
- planning artifact or existing batch selection
- queue/handoff
- worker evidence/review if applicable
- delivery check/report
- trusted runner delivery
- clean final repo state

TASK-DEVO-124 should follow after TASK-DEVO-123 and create the Phase 1 checkpoint. It should not add new capability unless TASK-DEVO-123 exposes a true blocker.

## 10. Decision Table

| Area | Status | Keep / simplify / defer | Recommendation |
| --- | --- | --- | --- |
| Core Phase 1 workflow | OK | Keep | Use it in TASK-DEVO-123 before adding features. |
| Task prompt length | Watch | Simplify | Use a shorter standard prompt structure with links/commands for context. |
| Docs overlap | Needs later cleanup | Defer | Keep canonical map now; compact long repeated histories after dogfood. |
| Workspace artifacts | Watch | Defer | Keep evidence; later add indexing, filtering, and archival guidance. |
| Command count | Watch | Simplify later | Prefer `intake-status`, `intake-next`, `delivery latest`, and `runner-latest` for daily use. |
| Trusted runner | OK | Keep | Continue normal-PowerShell delivery through runner requests. |
| Read models/API/UI performance | Watch | Defer | Monitor during dogfood; add index/pagination task only if needed. |
| Safety gates | OK | Keep | Friction is justified after index-lock and secret-risk findings. |
| UI actions | Defer | Defer | Keep UI read-only or workspace-safe; no commit/push/build/test buttons. |
| Phase 2 AI agents | Defer | Defer | Do not start until Phase 1 dogfood/checkpoint is complete. |

## 11. Final Recommendation

Proceed to TASK-DEVO-123 end-to-end dogfood before building more features.

No blocker was found. The main risk is accumulating friction, not missing Phase 1 primitives. Use TASK-DEVO-123 to prove whether the current shortcuts are enough in real flow, then use TASK-DEVO-124 to checkpoint the stable Phase 1 state.
