# TASK-DEVO-160 Multi-Item Fake-Worker Batch Continuation Dogfood

## Goal

Dogfood `devo project codex-worker-batch-run` across multiple queue items using a fake subprocess worker only.

This dogfood intentionally did not run real Codex. It used a disposable project to verify that Devo can safely continue from a completed queue item to the next eligible item, one item at a time, while still requiring manual review, manual validation evidence, and trusted-runner delivery.

## Disposable Project

- Project: `Dogfood160`
- Work repo: `E:\DevOrchestrator\pt-160-dogfood\work`
- Bare remote: `E:\DevOrchestrator\pt-160-dogfood\remote.git`
- Remote URL: `file:///E:/DevOrchestrator/pt-160-dogfood/remote.git`
- Batch: `B001`
- Queue: `Q001`
- Policy: `POL-0001`
- Allowed files: `note-a.md`, `note-b.md`, `note-c.md`
- Forbidden files: `.env`, `workspace/**`
- Max changed files per task: `1`
- Worker command: fake Python worker in `E:\DevOrchestrator\pt-160-dogfood\scripts\fake_worker.py`

The disposable repo was initialized with `main` tracking `origin/main`. The seed commit was `89630d2 chore: seed dogfood notes`.

## Scope

Three low-risk docs-only tasks were created:

- `T001` / `QI001`: update only `note-a.md`
- `T002` / `QI002`: update only `note-b.md`
- `T003` / `QI003`: update only `note-c.md`

The fake worker read the Devo-generated prompt from stdin, identified the selected `Task id`, modified only the expected note file, and wrote strict JSON to the expected result path. It did not commit or push.

## Commands Exercised

Setup and planning:

```powershell
git init
git branch -M main
git init --bare E:\DevOrchestrator\pt-160-dogfood\remote.git
git remote add origin file:///E:/DevOrchestrator/pt-160-dogfood/remote.git
git push -u origin main
.\.venv\Scripts\devo.exe project add --name Dogfood160 --path "E:\DevOrchestrator\pt-160-dogfood\work"
.\.venv\Scripts\devo.exe project scan Dogfood160
.\.venv\Scripts\devo.exe project brief-create --project Dogfood160 --title "Dogfood160 fake-worker continuation" --file .\pt-160-dogfood\inputs\brief.md
.\.venv\Scripts\devo.exe project brief-approve --project Dogfood160
.\.venv\Scripts\devo.exe project blueprint-create --project Dogfood160
.\.venv\Scripts\devo.exe project blueprint-approve --project Dogfood160
.\.venv\Scripts\devo.exe project backlog-validate --project Dogfood160 --file .\pt-160-dogfood\inputs\backlog.json
.\.venv\Scripts\devo.exe project backlog-import --project Dogfood160 --file .\pt-160-dogfood\inputs\backlog.json
.\.venv\Scripts\devo.exe project backlog-approve --project Dogfood160
.\.venv\Scripts\devo.exe project batch-create --project Dogfood160 --title "Fake-worker note continuation" --tasks T001,T002,T003
.\.venv\Scripts\devo.exe project batch-approval-request --project Dogfood160 --batch B001 --note "TASK-DEVO-160 fake-worker three-item continuation scope."
.\.venv\Scripts\devo.exe project batch-approve --project Dogfood160 --batch B001 --note "Approved for TASK-DEVO-160 disposable fake-worker continuation only."
.\.venv\Scripts\devo.exe project queue-create --project Dogfood160 --batch B001
.\.venv\Scripts\devo.exe project execution-policy-create --project Dogfood160 --batch B001 --queue Q001 --title "Fake-worker three-note continuation policy" --allowed-task T001 --allowed-task T002 --allowed-task T003 --allowed-file note-a.md --allowed-file note-b.md --allowed-file note-c.md --forbidden-file .env --forbidden-file workspace/** --validation-command manual-diff-review --max-tasks 3 --max-tasks-per-run 1 --max-changed-files-per-task 1 --auto-delivery --auto-push --note "TASK-DEVO-160 fake-worker continuation policy."
.\.venv\Scripts\devo.exe project execution-policy-request --project Dogfood160 --policy POL-0001 --note "TASK-DEVO-160 fake-worker policy approval request."
.\.venv\Scripts\devo.exe project execution-policy-approve --project Dogfood160 --policy POL-0001 --approver Manas --note "Approved for TASK-DEVO-160 disposable fake-worker continuation only."
.\.venv\Scripts\devo.exe project codex-worker-config-set --project Dogfood160 --command "E:\DevOrchestrator\.venv\Scripts\python.exe" --args-template "E:\DevOrchestrator\pt-160-dogfood\scripts\fake_worker.py `"{result_path}`"" --timeout-minutes 1 --recorded-by Manas --note "TASK-DEVO-160 fake worker; prompt passed through stdin; no real Codex." --confirm-config
```

The first dry-run was non-mutating:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood160 --policy POL-0001 --max-items 1 --max-cycles 1 --no-require-scheduler-healthy --dry-run
```

It selected `QI001/T001`, launched no subprocess, wrote no batch-run artifact, and left the disposable repo clean.

Each completed item then used the same evidence and delivery pattern:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood160 --policy POL-0001 --max-items 1 --max-cycles 1 --no-require-scheduler-healthy --confirm-codex-batch-run
git diff -- note-a.md note-b.md note-c.md
.\.venv\Scripts\devo.exe project queue-worker-record-review --project Dogfood160 --run <QWR-ID> --status passed --summary "<summary>" --files-changed <note-file> --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-loop --project Dogfood160 --policy POL-0001 --run <QWR-ID> --confirm-loop
.\.venv\Scripts\devo.exe project queue-worker-record-validation --project Dogfood160 --run <QWR-ID> --status passed --summary "<summary>" --commands-run "git diff -- note-a.md note-b.md note-c.md" --files-changed <note-file> --confirm-record
.\.venv\Scripts\devo.exe project approved-queue-run --project Dogfood160 --policy POL-0001 --run <QWR-ID> --no-require-scheduler-healthy --confirm-auto-run
.\.venv\Scripts\devo.exe delivery runner-run --project Dogfood160 --request <REQ-ID> --approver "Manas" --confirm-runner-delivery
.\.venv\Scripts\devo.exe delivery runner-recover-push --project Dogfood160 --request <REQ-ID> --approver "Manas" --confirm-runner-push
.\.venv\Scripts\devo.exe project approved-queue-run --project Dogfood160 --policy POL-0001 --run <QWR-ID> --no-require-scheduler-healthy --confirm-auto-run
```

## Results

### Item 1

- Queue item: `QI001`
- Task: `T001`
- Successful queue-worker run: `QWR-0003`
- Preparation: `CWP-20260826165700-QWR-0003`
- Codex worker subprocess run: `CWR-20260826165737-QWR-0003`
- Ingest: `CWI-20260826165737-QWR-0003`
- Delivery request: `REQ-0001`
- Trusted runner push recovery run: `RUN-20260826165901-req-0001`
- Commit: `79249be6ef1ca631c0baccd9abda53ffb81fd2b3`
- Changed file: `note-a.md`
- Final item state: completed

### Item 2

- Queue item: `QI002`
- Task: `T002`
- Queue-worker run: `QWR-0004`
- Preparation: `CWP-20260826170019-QWR-0004`
- Codex worker subprocess run: `CWR-20260826170019-QWR-0004`
- Ingest: `CWI-20260826170020-QWR-0004`
- Delivery request: `REQ-0002`
- Trusted runner push recovery run: `RUN-20260826170127-req-0002`
- Commit: `97f5de1ad53b30299970dbc8843263cbe62ddd97`
- Changed file: `note-b.md`
- Final item state: completed

### Item 3

- Queue item: `QI003`
- Task: `T003`
- Queue-worker run: `QWR-0005`
- Preparation: `CWP-20260826170155-QWR-0005`
- Codex worker subprocess run: `CWR-20260826170155-QWR-0005`
- Ingest: `CWI-20260826170156-QWR-0005`
- Delivery request: `REQ-0003`
- Trusted runner push recovery run: `RUN-20260826170259-req-0003`
- Commit: `3c47c43befd396fdbba25be9500d35e1bab5af50`
- Changed file: `note-c.md`
- Final item state: completed

Final queue state:

- Queue `Q001`: completed
- Items: total `3`, completed `3`, pending `0`, blocked `0`, failed `0`
- Final disposable repo status: clean on `main...origin/main`

## What Worked

- `codex-worker-batch-run --dry-run` selected the first eligible item and stayed non-mutating.
- The fake worker subprocess ran once per successful item.
- Each successful run created a distinct queue-worker run, preparation, subprocess run, and ingest artifact.
- Strict JSON ingest worked for all three successful fake-worker results.
- Batch-run stopped at the review gate and did not auto-review, auto-validate, create delivery, run the trusted runner, commit, push, complete queue items, or start parallel work.
- Manual review and validation evidence gates worked for each item.
- `approved-queue-run --no-require-scheduler-healthy` created trusted delivery requests for the disposable direct-runner project.
- Trusted runner committed each item separately and push recovery completed each file-remote push outside the restricted sandbox context.
- Queue progression selected `QI002` after `QI001` completion and `QI003` after `QI002` completion.

## Friction For TASK-DEVO-161

1. The first fake worker selector failed because the prompt includes all allowed policy task ids later in the prompt. Fake or scripted workers should parse the explicit `Task id:` line, not scan for any task id.
2. `codex-worker-batch-run` has no `--run` option, so targeted retry of a specific queue-worker run is awkward.
3. A failed/blocked worker attempt left `WR001` and stale retry runs `QWR-0001`/`QWR-0002` in states that blocked later item selection until they were manually superseded/cancelled through Devo.
4. `queue-worker-retry` created `QWR-0002` without a linked worker run; subsequent batch-run execution could create a result but ingest blocked because the queue-worker run had no linked worker run.
5. After all items completed, `queue-worker-plan` correctly reported `no_ready_item`, but the next action says to review queue state and policy scope. For a fully completed queue, a clearer "No action needed; queue completed" message would be nicer.
6. Direct trusted runner push to the local bare `file:///...` remote still fails inside the restricted Codex/sandbox context with Git-for-Windows `sh.exe` signal pipe permission errors. Devo push recovery succeeds outside the sandbox.
7. Review evidence output still uses the generic `Evidence artifact` label for review files, while validation evidence now uses the clearer shared validation evidence label from TASK-DEVO-159.

## Verdict

PASS.

TASK-DEVO-160 proves multi-item fake-worker continuation across all three disposable queue items. Devo processed each item one at a time, stopped at review and validation gates, required trusted-runner delivery, and completed the queue without real Codex execution, PersonalOS changes, parallel workers, or direct worker commit/push.

Recommended next task: TASK-DEVO-161 should polish stale retry/run selection and completed-queue next-action wording before larger real Codex continuation dogfood.
