# TASK-DEVO-158 Real Codex Batch-Run One-Item Dogfood

## Goal

Dogfood `devo project codex-worker-batch-run` with a real Codex subprocess for exactly one disposable queue item.

This dogfood used only the disposable `Dogfood158` project. Real Codex was not run against DevOrchestrator source, PersonalOS, or any non-disposable target. Codex was not allowed to commit or push; trusted delivery remained the only committer and pusher.

## Disposable Project

- Project: `Dogfood158`
- Work repo: `E:\DevOrchestrator\pt-158-dogfood\work`
- Remote: `file:///E:/DevOrchestrator/pt-158-dogfood/remote.git`
- Policy: `POL-0001`
- Batch: `B001`
- Queue: `Q001`
- Queue item: `QI001`
- Task: `T001`
- Allowed file: `dogfood-note.md`
- Forbidden paths: `.env`, `**/.env`, `workspace/**`

## Commands And Setup

The disposable repository was initialized with a local bare remote and verified upstream:

```powershell
git init E:\DevOrchestrator\pt-158-dogfood\work
git init --bare E:\DevOrchestrator\pt-158-dogfood\remote.git
git remote add origin file:///E:/DevOrchestrator/pt-158-dogfood/remote.git
git push -u origin main
git branch -vv
git remote -v
```

The initial push failed inside the restricted Codex/sandbox context with the known Git-for-Windows shell permission error. Running only that disposable setup push from normal PowerShell succeeded and established `main -> origin/main`.

Devo planning artifacts were then created for one low-risk docs-only task:

```powershell
.\.venv\Scripts\devo.exe project add --name Dogfood158 --path "E:\DevOrchestrator\pt-158-dogfood\work"
.\.venv\Scripts\devo.exe project scan Dogfood158
.\.venv\Scripts\devo.exe project brief-create --project Dogfood158 --title "Dogfood158 real Codex batch" --file E:\DevOrchestrator\pt-158-dogfood\brief.md
.\.venv\Scripts\devo.exe project brief-approve --project Dogfood158
.\.venv\Scripts\devo.exe project blueprint-create --project Dogfood158
.\.venv\Scripts\devo.exe project blueprint-approve --project Dogfood158
.\.venv\Scripts\devo.exe project backlog-validate --project Dogfood158 --file E:\DevOrchestrator\pt-158-dogfood\refined-backlog.json
.\.venv\Scripts\devo.exe project backlog-import --project Dogfood158 --file E:\DevOrchestrator\pt-158-dogfood\refined-backlog.json
.\.venv\Scripts\devo.exe project backlog-approve --project Dogfood158
.\.venv\Scripts\devo.exe project batch-create --project Dogfood158 --title "Real Codex one note update" --tasks T001
.\.venv\Scripts\devo.exe project batch-approval-request --project Dogfood158 --batch B001 --note "TASK-DEVO-158 disposable real Codex one-item batch scope."
.\.venv\Scripts\devo.exe project batch-approve --project Dogfood158 --batch B001 --note "Approved for disposable real Codex one-item dogfood preparation only."
.\.venv\Scripts\devo.exe project queue-create --project Dogfood158 --batch B001
.\.venv\Scripts\devo.exe project execution-policy-create --project Dogfood158 --batch B001 --queue Q001 --title "Real Codex one note policy" --allowed-task T001 --allowed-file dogfood-note.md --forbidden-file .env --forbidden-file "**/.env" --forbidden-file "workspace/**" --validation-command manual-note-check --max-tasks 1 --max-tasks-per-run 1 --max-changed-files-per-task 1 --auto-delivery --auto-push --note "TASK-DEVO-158 real Codex one-item dogfood policy."
.\.venv\Scripts\devo.exe project execution-policy-request --project Dogfood158 --policy POL-0001
.\.venv\Scripts\devo.exe project execution-policy-approve --project Dogfood158 --policy POL-0001 --approver Manas
.\.venv\Scripts\devo.exe project codex-worker-config-set --project Dogfood158 --command "C:\Users\manas\AppData\Roaming\npm\codex.cmd" --args-template "exec -s workspace-write --output-last-message `"{result_path}`"" --timeout-minutes 10 --recorded-by Manas --note "TASK-DEVO-158 real Codex subprocess config; prompt is passed through stdin by Devo." --confirm-config
```

Dry-run was executed from Codex/sandbox and stayed non-mutating:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood158 --policy POL-0001 --max-items 1 --max-cycles 1 --no-require-scheduler-healthy --dry-run
```

The real subprocess run was executed by Manas from normal PowerShell:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood158 --policy POL-0001 --max-items 1 --max-cycles 1 --no-require-scheduler-healthy --recorded-by "Manas" --note "TASK-DEVO-158 real Codex batch-run dogfood for one item." --confirm-codex-batch-run
```

## Result

- Batch run: `CWBR-0001`
- Queue-worker run: `QWR-0001`
- Preparation: `CWP-20260826131732-QWR-0001`
- Codex worker run: `CWR-20260826131732-QWR-0001`
- Ingest: `CWI-20260826131802-QWR-0001`
- Delivery request: `REQ-0001`
- Runner run: `RUN-20260826135756-req-0001`
- Commit: `3eff3c36515063a65de6283032364e2df467b540`
- Commit message: `feat: complete Update dogfood note`
- Pushed: `True`
- Final disposable repo state: clean

`codex-worker-batch-run` launched the real Codex subprocess once, processed exactly one disposable queue item, created/reused queue-worker preparation, captured stdout/stderr/result artifacts, ingested strict JSON, and stopped at the review gate.

Codex modified only `dogfood-note.md`:

```text
TASK-DEVO-158 real Codex batch-run dogfood note.
```

Codex did not commit or push. Manual review and validation evidence were recorded afterward, delivery request `REQ-0001` was created through Devo, and the trusted runner committed and pushed the disposable repository.

## Evidence Artifacts

- Batch-run artifact: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\batch-runs\CWBR-0001\codex-worker-batch-run.md`
- Queue-worker run: `E:\DevOrchestrator\workspace\projects\Dogfood158\planning\queue-worker-runs\queue-worker-run-QWR-0001.md`
- Preparation: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\preparations\CWP-20260826131732-QWR-0001\codex-worker-prompt.md`
- Codex worker run: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\runs\CWR-20260826131732-QWR-0001\codex-worker-run.md`
- Result JSON: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\runs\CWR-20260826131732-QWR-0001\codex-worker-result.json`
- Stdout: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\runs\CWR-20260826131732-QWR-0001\stdout.txt`
- Stderr: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\runs\CWR-20260826131732-QWR-0001\stderr.txt`
- Ingest artifact: `E:\DevOrchestrator\workspace\projects\Dogfood158\codex-worker\ingests\CWI-20260826131802-QWR-0001\codex-worker-ingest.md`
- Delivery runner request: `E:\DevOrchestrator\workspace\projects\Dogfood158\delivery\runner-requests\runner-request-req-0001.md`
- Delivery runner run: `E:\DevOrchestrator\workspace\projects\Dogfood158\delivery\runner-requests\runner-run-req-0001.md`

## What Worked

- Real Codex subprocess execution worked from normal PowerShell with `C:\Users\manas\AppData\Roaming\npm\codex.cmd`.
- Prompt content was passed through stdin and `--output-last-message` produced the expected JSON result file.
- The worker changed only the allowed disposable file.
- The v1 batch coordinator processed one item and stopped at review.
- Worker result ingest produced queue-worker evidence.
- Devo required manual review and validation evidence before delivery.
- Trusted runner delivery committed and pushed successfully.
- The disposable repo ended clean.

## Friction For TASK-DEVO-159

1. `usage_limit_detected` appeared as a warning even though the run completed successfully, wrote a valid result file, and ingested `status=completed`. This looks like a false positive in subprocess output classification.
2. Validation evidence artifact output still uses names like `review-WR001.json` and `review-WR001.md`, which is confusing for validation evidence.
3. Some completed-run next-action wording may still mention an explicit operator step after completion. The main completed output is better, but the older wording remains visible in some artifacts.

## TASK-DEVO-159 Follow-Up

TASK-DEVO-159 keeps the successful Dogfood158 result intact and polishes the readouts found during the run:

- Usage-limit detection now ignores echoed worker-result schema/prompt text such as `usage_limit` and `usage_limit_details`; explicit `status=usage_limit` result evidence and strong subprocess failure messages still stop safely.
- Validation evidence output now labels the files as shared queue-worker review/evidence artifacts instead of implying a validation-only artifact.
- Completed queue-worker delivery now records the final next action as `No action needed; trusted delivery completed.`

The next expansion should be a multi-item continuation dogfood that still runs one queue item at a time. Parallel workers, automatic review, automatic validation, and direct Codex commit/push remain out of scope.

## Verdict

PASS.

TASK-DEVO-158 proves the first real one-item `codex-worker-batch-run` dogfood through disposable real Codex execution, strict JSON ingest, review gate, manual evidence gates, trusted runner delivery, push, and completed queue-worker state. No PersonalOS files were modified, no real Codex work was run against DevOrchestrator source, and Codex did not commit or push.

Recommended next task: run a continuation dogfood that proves the next eligible disposable queue item can proceed after a completed trusted delivery, still one task at a time.
