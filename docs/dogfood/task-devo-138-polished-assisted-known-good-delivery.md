# TASK-DEVO-138 Polished Assisted Dogfood With Known-Good Delivery

## Goal

TASK-DEVO-138 reran the assisted queue-worker path after the TASK-DEVO-137 friction polish, using a disposable Git repository with a real local bare remote. The purpose was to prove the current safe Phase 2 operator loop:

```text
approved policy
-> queue-worker-loop
-> manual worker/review/validation evidence
-> trusted delivery runner request
-> known-good trusted local runner delivery
-> queue-worker completion detection
-> next item selected and stopped at worker boundary
```

This dogfood did not run real Codex, call AI APIs, touch PersonalOS, run backup/restore, change scheduler state, add UI controls, or bypass delivery safety.

## Setup

- Controller repository: `E:\DevOrchestrator`
- Disposable dogfood project: `E:\DevOrchestrator\pt-138-dogfood\work`
- Disposable bare remote: `E:\DevOrchestrator\pt-138-dogfood\remote.git`
- Dogfood Devo project: `Dogfood138`
- Initial temp project files:
  - `README.md`
  - `docs/dogfood-note.md`
- Refined backlog tasks:
  - `T001` update temp dogfood note
  - `T002` update temp dogfood checklist
  - `T003` update temp dogfood summary

The first temp `git push -u origin main` failed from the restricted/sandboxed context with a Windows Git shell permission error. Retrying that temp-repo-only push from the trusted context succeeded, which made the disposable remote a valid delivery target before Devo delivery was tested.

## Commands Run

Representative setup and planning commands:

```powershell
git init -b main
git add README.md docs/dogfood-note.md
git commit -m "initial dogfood project"
git init --bare E:\DevOrchestrator\pt-138-dogfood\remote.git
git remote add origin E:\DevOrchestrator\pt-138-dogfood\remote.git
git push -u origin main
.\.venv\Scripts\devo.exe project add --name Dogfood138 --path E:\DevOrchestrator\pt-138-dogfood\work
.\.venv\Scripts\devo.exe project brief-create --project Dogfood138 --title "Polished assisted dogfood" --file E:\DevOrchestrator\pt-138-dogfood\brief.md
.\.venv\Scripts\devo.exe project brief-approve --project Dogfood138
.\.venv\Scripts\devo.exe project blueprint-create --project Dogfood138
.\.venv\Scripts\devo.exe project blueprint-approve --project Dogfood138
.\.venv\Scripts\devo.exe project backlog-import --project Dogfood138 --file E:\DevOrchestrator\pt-138-dogfood\refined-backlog.json
.\.venv\Scripts\devo.exe project backlog-approve --project Dogfood138
.\.venv\Scripts\devo.exe project batch-create --project Dogfood138 --title "Polished assisted dogfood" --tasks T001,T002,T003
.\.venv\Scripts\devo.exe project batch-review --project Dogfood138 --batch B001 --note "Reviewed for dogfood."
.\.venv\Scripts\devo.exe project batch-approve --project Dogfood138 --batch B001 --note "Approved for dogfood."
.\.venv\Scripts\devo.exe project queue-create --project Dogfood138 --batch B001
.\.venv\Scripts\devo.exe project queue-start --project Dogfood138 --queue Q001
.\.venv\Scripts\devo.exe project execution-policy-create --project Dogfood138 --batch B001 --queue Q001 --title "Polished assisted dogfood policy" --allowed-task T001 --allowed-task T002 --allowed-task T003 --allowed-queue-item QI001 --allowed-queue-item QI002 --allowed-queue-item QI003 --allowed-file "docs/**" --forbidden-file ".env" --forbidden-file "*.secret" --validation-command "manual-validation-evidence" --max-tasks 3 --max-tasks-per-run 1 --max-changed-files-per-task 2 --auto-delivery --auto-push
.\.venv\Scripts\devo.exe project execution-policy-request --project Dogfood138 --policy POL-0001 --note "Ready for assisted dogfood."
.\.venv\Scripts\devo.exe project execution-policy-approve --project Dogfood138 --policy POL-0001 --approver "Manas" --note "Approved for assisted dogfood."
```

Representative assisted loop commands:

```powershell
.\.venv\Scripts\devo.exe project queue-worker-loop --project Dogfood138 --policy POL-0001 --confirm-loop
.\.venv\Scripts\devo.exe project queue-worker-record-worker-result --project Dogfood138 --run QWR-0001 --status completed --summary "Task 1 temporary note file updated." --commands-run "manual temp docs edit plus git diff --check" --files-changed "docs/dogfood-note.md" --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-review --project Dogfood138 --run QWR-0001 --status passed --summary "Task 1 temp note review passed." --files-changed "docs/dogfood-note.md" --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-record-validation --project Dogfood138 --run QWR-0001 --status passed --summary "Manual validation passed for temp note after git diff --check." --commands-run "git diff --check" --files-changed "docs/dogfood-note.md" --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-loop --project Dogfood138 --policy POL-0001 --run QWR-0001 --message "docs: dogfood polished temp note" --note "TASK-DEVO-138 temp item 1." --confirm-loop
.\.venv\Scripts\devo.exe delivery runner-run --project Dogfood138 --request REQ-0001 --approver "Manas" --confirm-runner-delivery
.\.venv\Scripts\devo.exe project queue-worker-loop --project Dogfood138 --policy POL-0001 --run QWR-0001 --confirm-loop
.\.venv\Scripts\devo.exe project queue-worker-loop --project Dogfood138 --policy POL-0001 --confirm-loop
```

## State Transitions

- `QWR-0001` was created for `QI001` / `T001` and stopped at `waiting_worker`.
- Manual worker evidence was recorded as completed for `docs/dogfood-note.md`.
- Review evidence was recorded as passed.
- Validation evidence was recorded as passed after `git diff --check`.
- `queue-worker-loop` created trusted delivery runner request `REQ-0001`.
- Trusted runner delivery completed through Devo runner delivery:
  - Runner run: `RUN-20260822174545-req-0001`
  - Delivery report: `DEL-0001`
  - Commit: `5887f66a900e90f496947401e24617733ba18a2a`
  - Push: succeeded to `origin/main`
- A follow-up loop observed the trusted delivery and completed `QWR-0001`.
- Queue state advanced:
  - `QI001` completed
  - `QI002` running
  - `QI003` pending
- A final loop without `--run` created `QWR-0002` for `QI002` and stopped at `waiting_worker`.

## What Worked Well

- The TASK-DEVO-137 next-action polish was useful: worker, review, and validation stops now point directly to the evidence intake commands.
- The trusted runner path worked when the temp repo had a real local bare remote and the runner was executed from the trusted context.
- Delivery completion detection worked: after the runner completed, the queue-worker loop recognized the completed request and moved the run to `completed`.
- The next item selection path worked: after item 1 delivery completed, a loop without a specific run created `QWR-0002` for `QI002` and stopped safely at the worker-result boundary.
- Devo did not run Codex, validation, review, runner-watch, commit, push, or parallel work from the queue-worker loop.

## Friction Found

- The queue-level `queue-show` wording still says "Completion ready" for the current running item in a way that can be misread when the active worker run has not produced evidence yet.
- The scheduler status for DevOrchestrator reported `Installed: False` while `Enabled: True`, which is worth a separate operational cleanup because it makes automatic delivery status less clear.
- A newly observed validation state had `status=provided` after review evidence but before explicit validation evidence. `queue-worker-loop` initially described that as an unknown unsafe state. TASK-DEVO-138 includes a tiny fix so `provided` is reported as a clear non-passing validation status with the `queue-worker-record-validation` next action.

## Dogfood Verdict

The polished assisted queue-worker loop is ready for cautious CLI use on small approved batches. The workflow is not full autonomy, but it now supports a comfortable one-task-at-a-time rhythm:

```text
loop
-> record worker result
-> loop
-> record review
-> loop
-> record validation
-> loop creates runner request
-> trusted runner delivers
-> loop observes completion and starts the next item
```

This is a credible Phase 2 assisted operation point. The remaining work should focus on reducing wording ambiguity and making the trusted runner/scheduler status clearer before adding broader UI queue controls or real Codex worker execution.

## Recommended Next Task

Recommended next task: TASK-DEVO-139 queue-state and scheduler-status polish.

Suggested scope:

- Clarify queue current-item completion wording when the queue item is running but the linked queue-worker run is waiting for worker evidence.
- Explain scheduler `Installed: False` plus `Enabled: True` mismatch and add a safe repair/status recommendation if needed.
- Keep it CLI/read-only or small text polish unless the implementation is clearly mechanical.
