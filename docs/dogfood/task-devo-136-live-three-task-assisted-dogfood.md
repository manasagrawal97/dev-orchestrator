# TASK-DEVO-136 Live Three-Task Assisted Dogfood

## Scenario Chosen

This dogfood used an isolated temporary project named `Dogfood136` under:

```text
E:\DevOrchestrator\pt-136-live-dogfood
```

The target project was a temporary local Git repository with three synthetic docs-only tasks:

- `T001`: update a temporary dogfood note file
- `T002`: update a temporary dogfood checklist
- `T003`: update a temporary dogfood summary file

No PersonalOS repository, real Codex CLI subprocess, AI/API call, UI control, background daemon change, parallel execution, direct delivery commit/push command, or manual `git add/commit/push` was used.

## Commands Run

Setup and planning commands:

```powershell
devo project add --name Dogfood136 --path E:\DevOrchestrator\pt-136-live-dogfood\target
devo project brief-create --project Dogfood136 --title "Dogfood136" --file E:\DevOrchestrator\pt-136-live-dogfood\brief.md
devo project brief-approve --project Dogfood136
devo project blueprint-create --project Dogfood136
devo project blueprint-approve --project Dogfood136
devo project backlog-import --project Dogfood136 --file E:\DevOrchestrator\pt-136-live-dogfood\refined-backlog.json
devo project backlog-approve --project Dogfood136
devo project batch-create --project Dogfood136 --title "Three task assisted dogfood" --tasks T001,T002,T003
devo project batch-review --project Dogfood136 --batch B001 --note "TASK-DEVO-136 sandbox batch review."
devo project batch-approve --project Dogfood136 --batch B001 --note "Approved for TASK-DEVO-136 sandbox dogfood." --approver Manas
devo project queue-create --project Dogfood136 --batch B001
devo project queue-start --project Dogfood136 --queue Q001
devo project execution-policy-create --project Dogfood136 --batch B001 --queue Q001 --title "TASK-DEVO-136 sandbox policy" --allowed-task T001 --allowed-task T002 --allowed-task T003 --allowed-file "docs/**" --forbidden-file ".env" --forbidden-file "*.secret" --validation-command "manual-validation-evidence" --max-tasks 3 --max-tasks-per-run 1 --max-changed-files-per-task 2
devo project execution-policy-request --project Dogfood136 --policy POL-0001 --note "Request TASK-DEVO-136 sandbox policy approval."
devo project execution-policy-approve --project Dogfood136 --policy POL-0001 --approver Manas --note "Approved for TASK-DEVO-136 sandbox dogfood only."
```

Assisted queue-worker commands for item 1:

```powershell
devo project queue-worker-loop --project Dogfood136 --policy POL-0001 --confirm-loop
devo project queue-worker-record-worker-result --project Dogfood136 --run QWR-0001 --status completed --summary "Task 1 temporary note file created." --commands-run "manual file edit only" --files-changed "docs/dogfood-note.md" --confirm-record
devo project queue-worker-loop --project Dogfood136 --policy POL-0001 --run QWR-0001 --confirm-loop
devo project queue-worker-record-review --project Dogfood136 --run QWR-0001 --status passed --summary "Task 1 note review passed." --files-changed "docs/dogfood-note.md" --confirm-record
devo project queue-worker-loop --project Dogfood136 --policy POL-0001 --run QWR-0001 --confirm-loop
devo project queue-worker-record-validation --project Dogfood136 --run QWR-0001 --status passed --summary "Manual validation passed for temporary note file." --commands-run "manual inspection" --files-changed "docs/dogfood-note.md" --confirm-record
devo project queue-worker-loop --project Dogfood136 --policy POL-0001 --run QWR-0001 --message "docs: dogfood temp note" --note "TASK-DEVO-136 sandbox item 1." --confirm-loop
```

Temp trusted runner check:

```powershell
devo delivery runner-run --project Dogfood136 --request REQ-0001 --approver "Manas" --confirm-runner-delivery
devo project queue-worker-loop --project Dogfood136 --policy POL-0001 --run QWR-0001 --confirm-loop
```

## Artifacts Created

- Batch: `B001`
- Queue: `Q001`
- Execution policy: `POL-0001`
- Queue-worker run: `QWR-0001`
- Handoff: `H001`
- Worker run: `WR001`
- Worker report evidence: `report-WR001`
- Review/validation evidence: `review-WR001`
- Delivery runner request: `REQ-0001`
- Delivery runner run: `RUN-20260822155459-req-0001`

## State Transitions Observed

Item 1 reached the full pre-delivery evidence chain:

```text
none
-> waiting_worker
-> worker evidence recorded
-> waiting_review
-> review evidence recorded
-> waiting_validation
-> validation evidence recorded
-> ready_for_delivery_request
-> delivery_requested
```

After the temp trusted runner failed during push, the loop correctly refused to continue:

```text
delivery_requested
-> blocked by unsafe linked delivery request status: failed
```

## Evidence Records Created

- Worker result: `completed`, summary `Task 1 temporary note file created.`
- Review: `passed`, summary `Task 1 note review passed.`
- Validation: `passed`, summary `Manual validation passed for temporary note file.`

The record commands were easy to use once the queue-worker run id was known. They did not advance the run by themselves; running `queue-worker-loop` after each evidence record advanced the next gate.

## Where The Loop Stopped

The first stop was expected:

- `waiting_worker`: missing worker result
- `waiting_review`: missing review
- `waiting_validation`: validation was only `provided`, so passing validation still needed to be recorded
- `delivery_requested`: waiting for trusted runner

The final stop was a real blocker:

- Trusted runner guarded commit succeeded in the temp repo.
- Guarded push failed with a Windows/Git shell permission error:

```text
C:\Program Files\Git\usr\bin\sh.exe: *** fatal error - couldn't create signal pipe, Win32 error 5
fatal: Could not read from remote repository.
```

Because delivery did not complete, Devo correctly did not complete `QI001` or start `QI002`.

## Whether Three Tasks Could Be Processed

No. One task could be processed through worker, review, validation, and delivery request creation. The flow could not safely proceed to task 2 because queue-worker continuation depends on completed trusted delivery for task 1, and the temp trusted runner push failed.

This is the right safety behavior. It also means a 3-task assisted batch currently needs a reliable local trusted runner push path or a documented docs-only/no-push dogfood mode before it feels smooth.

## What Worked Well

- Planning artifact creation worked through the CLI.
- One approved policy could cover all three task ids while still enforcing one task per run.
- `queue-worker-loop` selected only `QI001`.
- Evidence intake commands were straightforward and printed useful next actions.
- The loop consumed recorded evidence without bypassing gates.
- Failed delivery stopped the loop from starting the next item.

## What Was Awkward

- The approved policy output still used the phrase `autonomous queue worker loop` in one next-action line.
- The first `queue-worker-loop` next action after creating `QWR-0001` still pointed to lower-level worker-run inspection instead of the new record command.
- `waiting_validation` produced `unknown or unsafe state: waiting_validation` when validation evidence was `provided` but not `passed`; the state was safe, but the stop reason was confusing.
- Batch creation warned about in-batch dependencies for T002/T003, which is accurate but noisy for a same-batch sequence dogfood.
- Proceeding beyond item 1 required successful trusted delivery, so a temp project needs a reliable temp remote/push path.

## What Felt Unsafe

Nothing in the queue-worker loop felt unsafe. The unsafe condition was correctly detected after the delivery runner failed. Devo refused to treat the failed delivery request as completion evidence.

## Gaps Before Real 5-Task Assisted Usage

- Improve the `waiting_validation` stop reason when validation is present but not passed.
- Update stale `autonomous queue worker loop` wording.
- Make the initial waiting-worker next action point to `queue-worker-record-worker-result`.
- Provide a documented temp-project dogfood delivery setup that avoids Git shell permission issues.
- Decide whether there should be a no-push sandbox delivery mode for isolated dogfood only, without weakening real delivery.

## Verdict

- Ready for 3-5 task assisted dogfood: `partial`
- Ready for real Codex worker integration: `no`

Manas can approve small tasks and use Devo to move one task through manual worker, review, validation, and trusted delivery request creation. Multi-task continuation is safe but still depends on successful trusted delivery per item. Real Codex integration should wait until these operator and local Git delivery rough edges are smoother.

## Recommended Next Task

TASK-DEVO-137 should polish the queue-worker dogfood friction found here:

- clearer `waiting_validation` stop reason
- replace remaining `autonomous` wording with `assisted`
- make the first loop next action point to the evidence intake command
- document or improve temp-project trusted delivery setup before another multi-item dogfood

## Follow-Up Notes From TASK-DEVO-137

Temporary dogfood repositories that exercise trusted delivery should use a valid disposable remote when push behavior is in scope. A local bare remote is fine, but it must be initialized and reachable from the same shell context used by the trusted runner. If a temp push fails, treat it as a real safety stop and inspect the runner artifact before continuing the queue.

`runner-watch-latest` reports the latest watch artifact, while `runner-latest` reports the latest runner request. If the latest watch says `no_pending` but `runner-latest` shows a newer requested item, run `runner-watch` again or use the precise `runner-run --request <REQ-ID>` fallback. Do not bypass Devo delivery with manual Git commands during dogfood.
