# TASK-DEVO-148: Prompt-File Codex Worker Dogfood

## Scenario

Dogfood project: `Dogfood148`

Temporary repo and remote:

- Work repo: `E:\DevOrchestrator\pt-148-dogfood\work`
- Bare remote: `E:\DevOrchestrator\pt-148-dogfood\remote.git`
- Branch/upstream: `main...origin/main`

Task attempted: 1
Task completed: 1

The dogfood used a disposable markdown-only project. It did not use PersonalOS and did not run Codex, Codex Desktop, or AI/API calls.

## Commands Run

High-level command sequence:

```powershell
devo project add --name Dogfood148 --path E:\DevOrchestrator\pt-148-dogfood\work
devo project brief-create --project Dogfood148 --title Dogfood148 --file .\pt-148-dogfood\brief.md
devo project brief-approve --project Dogfood148
devo project blueprint-create --project Dogfood148
devo project blueprint-approve --project Dogfood148
devo project backlog-create --project Dogfood148
devo project backlog-approve --project Dogfood148
devo project batch-create --project Dogfood148 --title "Dogfood148 prompt-file worker dogfood batch" --tasks T001
devo project batch-approve --project Dogfood148 --batch B001
devo project queue-create --project Dogfood148 --batch B001
devo project queue-start --project Dogfood148 --queue Q001
devo project execution-policy-create --project Dogfood148 --batch B001 --queue Q001 ...
devo project execution-policy-request --project Dogfood148 --policy POL-0001
devo project execution-policy-approve --project Dogfood148 --policy POL-0001 --approver Manas
devo project approved-queue-run --project Dogfood148 --policy POL-0001 --no-require-scheduler-healthy --confirm-auto-run
devo project codex-worker-prepare --project Dogfood148 --run QWR-0001 --confirm-prepare
devo project codex-worker-ingest --project Dogfood148 --run QWR-0001 --prepare CWP-20260825065816-QWR-0001 --result-file .\pt-148-dogfood\worker-result-qwr-0001.json --dry-run
devo project codex-worker-ingest --project Dogfood148 --run QWR-0001 --prepare CWP-20260825065816-QWR-0001 --result-file .\pt-148-dogfood\worker-result-qwr-0001.json --confirm-ingest
devo project approved-queue-run --project Dogfood148 --policy POL-0001 --run QWR-0001 --no-require-scheduler-healthy --confirm-auto-run
devo project queue-worker-record-review --project Dogfood148 --run QWR-0001 --status passed --confirm-record
devo project approved-queue-run --project Dogfood148 --policy POL-0001 --run QWR-0001 --no-require-scheduler-healthy --confirm-auto-run
devo project queue-worker-record-validation --project Dogfood148 --run QWR-0001 --status passed --confirm-record
devo project approved-queue-run --project Dogfood148 --policy POL-0001 --run QWR-0001 --message "docs: update dogfood note" --no-require-scheduler-healthy --confirm-auto-run
devo delivery runner-run --project Dogfood148 --request REQ-0001 --approver "Manas" --confirm-runner-delivery
devo delivery runner-recover-push --project Dogfood148 --request REQ-0001 --approver "Manas" --confirm-runner-push
devo project approved-queue-run --project Dogfood148 --policy POL-0001 --run QWR-0001 --no-require-scheduler-healthy --confirm-auto-run
```

The first execution-policy attempt used `--max-changed-files`; the CLI rejected it and suggested the correct `--max-changed-files-per-task` option. The corrected command succeeded.

## Preparation

- Queue-worker run: `QWR-0001`
- Preparation id: `CWP-20260825065816-QWR-0001`
- Prompt path: `E:\DevOrchestrator\workspace\projects\Dogfood148\codex-worker\preparations\CWP-20260825065816-QWR-0001\codex-worker-prompt.md`
- Result template: `E:\DevOrchestrator\workspace\projects\Dogfood148\codex-worker\preparations\CWP-20260825065816-QWR-0001\worker-result-template.json`

Prompt quality observations:

- It included project name, target repo path, queue-worker run id, queue item/task, handoff checklist, policy summary, allowed scope, forbidden scope, relevant files, acceptance criteria, required tests, worker boundaries, no commit/no push rules, worker output contract, and next Devo commands.
- The generated backlog task was a deterministic placeholder, so the objective and acceptance criteria were not as concrete as a real refined task would be.
- The generated prompt was usable enough to hand to Codex manually, but the original next-action text still referenced `queue-worker-record-worker-result` instead of `codex-worker-ingest`.

Small fix made:

- Updated prompt/next-action guidance to point to `codex-worker-prepare` and `codex-worker-ingest`.
- Updated dry-run ingest wording so it says the mapping passed instead of implying evidence was already ingested.

## Worker Result

Result JSON file used:

`E:\DevOrchestrator\pt-148-dogfood\worker-result-qwr-0001.json`

Summary:

- Status: `completed`
- Changed files: `dogfood-note.md`
- Commands run: `git status --short`, `git diff --check`
- Risks: disposable repo only; manual worker simulation; no Codex subprocess used

Validation commands in the disposable repo:

```powershell
git -C .\pt-148-dogfood\work status --short
git -C .\pt-148-dogfood\work diff --check
```

`git diff --check` passed. Git printed a CRLF warning for the markdown file.

## Ingest

- Ingest id: `CWI-20260825065854-QWR-0001`
- Ingest artifact: `E:\DevOrchestrator\workspace\projects\Dogfood148\codex-worker\ingests\CWI-20260825065854-QWR-0001\codex-worker-ingest.json`
- Raw result copy: `E:\DevOrchestrator\workspace\projects\Dogfood148\codex-worker\ingests\CWI-20260825065854-QWR-0001\raw-result-copy.json`
- Worker evidence id: `qwr-0001-worker-result`
- Worker report path: `E:\DevOrchestrator\workspace\projects\Dogfood148\workers\codex\reports\report-WR001.json`

Result ingest behavior:

- `--dry-run` validated and mapped the JSON without mutation.
- Confirmed ingest preserved the raw result copy.
- Confirmed ingest recorded worker evidence schema v1.
- Confirmed ingest did not auto-run review, validation, delivery, commit, or push.

## Review And Validation

Review evidence:

- Status: `passed`
- Evidence id: `qwr-0001-review`
- Summary: reviewed disposable note update; scope limited to `dogfood-note.md`

Validation evidence:

- Status: `passed`
- Evidence id: `qwr-0001-validation`
- Summary: `git status --short` showed only `dogfood-note.md`; `git diff --check` passed

Both records were workspace evidence only. Devo did not run review or validation automatically.

## Delivery

- Delivery request: `REQ-0001`
- Delivery id: `DEL-0001`
- Commit: `2370b1b05e9c8552dd31952301297259a0b5d9a8`
- Commit message: `docs: update dogfood note`
- Final runner status: completed
- Pushed: true

The first trusted runner attempt committed successfully but failed to push because the restricted context hit the known Git shell permission issue:

```text
couldn't create signal pipe, Win32 error 5
```

The Devo push-only recovery path succeeded:

```powershell
devo delivery runner-recover-push --project Dogfood148 --request REQ-0001 --approver "Manas" --confirm-runner-push
```

After recovery, `approved-queue-run` detected the completed delivery and marked `QWR-0001` completed. Queue `Q001` became completed with one completed item.

## Completion And Next Item Behavior

Completion detection worked:

- `QWR-0001`: `completed`
- `Q001`: `completed`
- target repo: clean

There was no next item because the batch intentionally contained one task. The next-action text said to start the next eligible item, while `queue-show` correctly showed the queue completed.

## What Worked

- End-to-end prompt-file worker path worked on a disposable project.
- `codex-worker-prepare` produced a complete prompt package.
- `codex-worker-ingest` successfully turned a filled JSON result into worker evidence.
- Existing `approved-queue-run` gates advanced correctly through worker, review, validation, delivery request, and delivery completion.
- Trusted runner delivery committed safely.
- Push-only recovery worked when the restricted context could not push.

## What Was Awkward

- Starter backlog tasks are generic placeholders unless refined, so real work needs better intake/backlog refinement before batching.
- Some next-action text still pointed to older manual evidence commands before this task's small fix.
- The sandbox scheduler drift forced `--no-require-scheduler-healthy` despite normal PowerShell evidence being healthy.
- The restricted context could commit but could not push to the local bare remote; push-only recovery in normal context fixed it.

## What Felt Unsafe

Nothing bypassed Devo gates. The only uncomfortable part was the restricted-context Git push failure, but Devo stopped safely and provided a push-only recovery command.

## Remaining Manual Steps

- The operator still launches Codex manually or simulates the worker.
- The operator fills the JSON result file.
- Review evidence is manual.
- Validation evidence is manual.
- Trusted runner delivery remains explicit.

## Verdicts

- Prompt-file Codex worker mode usable: yes, with minor guidance friction fixed in this task.
- Ready for Codex subprocess execution design: yes.
- Ready for Codex subprocess execution implementation: no.

## Recommended Next Task

TASK-DEVO-149: Codex subprocess execution design checkpoint.
