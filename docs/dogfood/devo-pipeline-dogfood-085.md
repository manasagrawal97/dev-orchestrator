# TASK-DEVO-085 Dogfood: DevOrchestrator Planning Pipeline

Date: 2026-08-01

## Goal

Validate the current Devo planning pipeline end to end on DevOrchestrator itself, from project brief through blueprint, backlog, batch approval, execution queue, handoff prompt, and progress reporting.

This was an operational validation and documentation task. No target implementation handoff was executed, no Codex CLI automation was invoked, no AI/model API was called, and no target project source changes were made by the generated planning artifacts.

## Commands Run

Initial checks:

```powershell
git status -sb
.\.venv\Scripts\devo project context-status DevOrchestrator
.\.venv\Scripts\devo current
.\.venv\Scripts\devo project onboard --project DevOrchestrator
```

Brief:

```powershell
.\.venv\Scripts\devo project brief-create --project DevOrchestrator --title "Improve Devo planning workflow usability after first full pipeline" --file .\pt-085-brief\brief.md
.\.venv\Scripts\devo project brief-show --project DevOrchestrator
.\.venv\Scripts\devo project brief-approve --project DevOrchestrator
```

Blueprint:

```powershell
.\.venv\Scripts\devo project blueprint-create --project DevOrchestrator
.\.venv\Scripts\devo project blueprint-show --project DevOrchestrator
.\.venv\Scripts\devo project blueprint-approve --project DevOrchestrator
```

Backlog:

```powershell
.\.venv\Scripts\devo project backlog-create --project DevOrchestrator
.\.venv\Scripts\devo project backlog-show --project DevOrchestrator
.\.venv\Scripts\devo project task-list --project DevOrchestrator
.\.venv\Scripts\devo project backlog-prompt --project DevOrchestrator
.\.venv\Scripts\devo project backlog-approve --project DevOrchestrator
```

Batch:

```powershell
.\.venv\Scripts\devo project batch-suggest --project DevOrchestrator --limit 5
.\.venv\Scripts\devo project batch-suggest --project DevOrchestrator --limit 5 --write
.\.venv\Scripts\devo project batch-list --project DevOrchestrator
.\.venv\Scripts\devo project batch-show --project DevOrchestrator --batch B001
```

Batch approval:

```powershell
.\.venv\Scripts\devo project batch-approval-request --project DevOrchestrator --batch B001 --note "Dogfood approval request for first end-to-end planning pipeline validation."
.\.venv\Scripts\devo project batch-approval-show --project DevOrchestrator --batch B001
.\.venv\Scripts\devo project batch-review --project DevOrchestrator --batch B001 --note "Reviewed for dogfood validation only." --reviewer "Codex"
.\.venv\Scripts\devo project batch-approve --project DevOrchestrator --batch B001 --note "Approved for dogfood queue/handoff validation only." --approver "Codex"
```

Queue:

```powershell
.\.venv\Scripts\devo project queue-create --project DevOrchestrator --batch B001
.\.venv\Scripts\devo project queue-list --project DevOrchestrator
.\.venv\Scripts\devo project queue-show --project DevOrchestrator --queue Q001
.\.venv\Scripts\devo project queue-start --project DevOrchestrator --queue Q001
.\.venv\Scripts\devo project queue-next --project DevOrchestrator --queue Q001
```

Handoff:

```powershell
.\.venv\Scripts\devo project handoff-next --project DevOrchestrator --queue Q001
.\.venv\Scripts\devo project handoff-list --project DevOrchestrator
.\.venv\Scripts\devo project handoff-show --project DevOrchestrator --handoff H001
```

Progress and UI reachability:

```powershell
.\.venv\Scripts\devo project progress --project DevOrchestrator
.\.venv\Scripts\devo project progress --project DevOrchestrator --json
.\.venv\Scripts\devo ui status
```

## Generated Workspace Artifacts

These artifacts were generated under `workspace/projects/DevOrchestrator/planning/` and were intentionally not committed:

- `project-brief.json`
- `project-brief.md`
- `blueprint.json`
- `blueprint.md`
- `backlog.json`
- `backlog.md`
- `backlog-refinement-prompt.md`
- `batches/batch-B001.json`
- `batches/batch-B001.md`
- `batches/approvals/batch-B001-approval.json`
- `batches/approvals/batch-B001-approval.md`
- `queues/queue-Q001.json`
- `queues/queue-Q001.md`
- `handoffs/handoff-H001.json`
- `handoffs/handoff-H001.md`

The temporary source brief file was stored under `pt-085-brief/` and removed during cleanup.

## What Worked

- DevOrchestrator was clean, registered, scanned, context-approved, and onboarding-ready.
- Brief creation, show, and approval worked after the temporary brief file was rewritten without a BOM.
- Blueprint creation, show, and approval worked.
- Backlog creation produced a deterministic starter backlog with two tasks.
- Backlog prompt generation wrote a Codex/manual planning prompt and clearly stated that import remains manual.
- Batch suggestion selected the two ready medium-risk tasks and wrote batch `B001`.
- Batch approval request, show, review, and approve worked and produced the new approval artifact.
- Batch approval output clearly stated that approval is planning-only and did not create a queue or execute target work.
- Queue creation from approved batch `B001` worked and created queue `Q001`.
- Queue start and next-item inspection worked without marking implementation complete.
- Handoff generation created handoff `H001` and clearly stated that the user must paste the prompt into Codex manually.
- Progress output and JSON reflected approved brief/blueprint/backlog, one approved batch, and zero implementation completion.

## Awkward Or Confusing Findings

1. A UTF-8 BOM in the temporary brief file caused `brief-show` to crash with a Windows console `UnicodeEncodeError`.
   - This was triggered by PowerShell `Set-Content -Encoding UTF8` creating a BOM.
   - Rewriting the same brief as ASCII allowed the flow to continue.
   - Devo should tolerate BOM-prefixed brief files and render text safely on Windows terminals.

2. After `backlog-approve`, the suggested next command still said `batch creation is TASK-DEVO-077`.
   - Batch commands exist now, so this guidance is stale.
   - The next command should point to `devo project batch-suggest --project <project> --write` or `devo project batch-create`.

3. `queue-next` printed a generic handoff command with placeholders:
   - `devo project handoff-next --project <project> --queue <queueId>`
   - The command should include the actual project and queue id when available.

4. The deterministic starter backlog is useful for pipeline validation, but still too generic for real implementation.
   - The refinement prompt/import step remains necessary before most real work.
   - This is acceptable by design, but the CLI could remind the operator that approving an unrefined backlog creates placeholder implementation criteria.

5. Local API/UI page verification was skipped because `devo ui status` reported both API and UI as not reachable.
   - This task did not start servers.
   - The CLI status command behaved safely and did not mutate state.

## Safety Notes

- No PersonalOS commands were run.
- No backup, restore, or scheduler commands were run.
- No AI/model APIs were called.
- No Codex CLI automation was invoked.
- No generated handoff was pasted into Codex for implementation.
- Queue item `QI001` was started only to validate queue state behavior; it was not completed.
- Generated workspace planning artifacts were not staged for Git.

## Ready For Real Use?

The manual planning pipeline is ready for controlled dogfood use. It can safely record planning intent, batch approval, queue state, handoff prompts, and progress without executing implementation work.

It is not yet ready to feel frictionless. The next improvement should address CLI guidance polish and Windows input robustness before moving into worker adapter design.

## Recommended TASK-DEVO-086

TASK-DEVO-086 should be: improve planning pipeline operator guidance and input robustness.

Recommended scope:

- Normalize or strip UTF-8 BOM from brief/import text inputs before storing and printing.
- Make Rich/console output robust for brief/blueprint/backlog summaries on Windows terminals.
- Update stale `backlog-approve` next-action guidance to point to real batch commands.
- Fill actual project/queue ids in `queue-next` handoff command guidance.
- Add an optional planning status/resume command or improve existing project planning output so the operator can see the next step from brief through handoff.
- Add focused tests for these CLI guidance paths.

Keep Codex CLI worker adapter design as the next larger planning task after these dogfood friction fixes.

## TASK-DEVO-086 Follow-Up

TASK-DEVO-086 addressed the immediate friction from this dogfood run:

- BOM-prefixed planning text input is handled for brief creation.
- Starter backlog output now reminds operators that deterministic backlogs are not implementation-ready by default.
- `backlog-approve` points to real batch suggestion commands.
- `queue-next` prints concrete handoff commands with the selected project and queue id.
- UI verification docs now clarify that `devo ui status` is reachability-only and page review requires running the API/UI servers first.
