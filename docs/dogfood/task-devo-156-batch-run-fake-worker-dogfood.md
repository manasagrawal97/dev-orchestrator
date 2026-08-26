# TASK-DEVO-156 Batch-Run Fake Worker Dogfood

## Goal

Dogfood `devo project codex-worker-batch-run` on a disposable project with a fake subprocess worker only.

The purpose was to prove the new v1 coordinator can select one approved queue item, create or reuse worker preparation, run one configured subprocess, ingest strict JSON worker output, and stop at the next human evidence gate without running real Codex, parallel workers, automatic review, automatic validation, direct commit/push, or PersonalOS work.

## Disposable Project

- Project: `Dogfood156`
- Target path: `E:\DevOrchestrator\pt-156-dogfood\work`
- Disposable repo files:
  - `README.md`
  - `note-a.md`
  - `note-b.md`
  - `note-c.md`
- Fake worker script: `E:\DevOrchestrator\pt-156-dogfood\fake-worker.py`

The fake worker read the generated prompt from stdin, detected the selected task id, modified only the matching note file, wrote strict JSON to Devo's expected result path, and did not commit or push.

## Commands Run

Readiness:

```powershell
git status --short
.\.venv\Scripts\devo.exe delivery runner-latest --project DevOrchestrator
.\.venv\Scripts\devo.exe delivery latest --project DevOrchestrator
git log --oneline -n 5
```

Disposable setup and planning:

```powershell
.\.venv\Scripts\devo.exe project add --name Dogfood156 --path "E:\DevOrchestrator\pt-156-dogfood\work"
.\.venv\Scripts\devo.exe project scan Dogfood156
.\.venv\Scripts\devo.exe project brief-create --project Dogfood156 --title "Dogfood156 fake worker batch" --file E:\DevOrchestrator\pt-156-dogfood\brief.md
.\.venv\Scripts\devo.exe project brief-approve --project Dogfood156
.\.venv\Scripts\devo.exe project blueprint-create --project Dogfood156
.\.venv\Scripts\devo.exe project blueprint-approve --project Dogfood156
.\.venv\Scripts\devo.exe project backlog-validate --project Dogfood156 --file E:\DevOrchestrator\pt-156-dogfood\refined-backlog.json
.\.venv\Scripts\devo.exe project backlog-import --project Dogfood156 --file E:\DevOrchestrator\pt-156-dogfood\refined-backlog.json
.\.venv\Scripts\devo.exe project backlog-approve --project Dogfood156
.\.venv\Scripts\devo.exe project batch-create --project Dogfood156 --title "Fake worker note updates" --tasks T001,T002,T003
.\.venv\Scripts\devo.exe project batch-approval-request --project Dogfood156 --batch B001 --note "TASK-DEVO-156 disposable fake-worker batch scope."
.\.venv\Scripts\devo.exe project batch-approve --project Dogfood156 --batch B001 --note "Approved for disposable fake-worker dogfood only."
.\.venv\Scripts\devo.exe project queue-create --project Dogfood156 --batch B001
.\.venv\Scripts\devo.exe project execution-policy-create --project Dogfood156 --batch B001 --queue Q001 --title "Fake worker notes policy" --allowed-task T001 --allowed-task T002 --allowed-task T003 --allowed-file note-a.md --allowed-file note-b.md --allowed-file note-c.md --forbidden-file .env --forbidden-file "**/.env" --validation-command manual-note-check --max-tasks 3 --max-tasks-per-run 1 --max-changed-files-per-task 1 --auto-delivery --auto-push --note "TASK-DEVO-156 fake-worker dogfood policy."
.\.venv\Scripts\devo.exe project execution-policy-request --project Dogfood156 --policy POL-0001
.\.venv\Scripts\devo.exe project execution-policy-approve --project Dogfood156 --policy POL-0001 --approver Manas
.\.venv\Scripts\devo.exe project codex-worker-config-set --project Dogfood156 --command "E:\DevOrchestrator\.venv\Scripts\python.exe" --args-template '"E:\DevOrchestrator\pt-156-dogfood\fake-worker.py" "{result_path}"' --timeout-minutes 1 --confirm-config
```

Batch-run dogfood:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood156 --policy POL-0001 --dry-run --no-require-scheduler-healthy
.\.venv\Scripts\devo.exe project codex-worker-batch-run --project Dogfood156 --policy POL-0001 --no-require-scheduler-healthy --confirm-codex-batch-run
git -C .\pt-156-dogfood\work status --short
Get-Content .\pt-156-dogfood\work\note-a.md
.\.venv\Scripts\devo.exe project queue-worker-status --project Dogfood156
.\.venv\Scripts\devo.exe project queue-worker-record-review --project Dogfood156 --run QWR-0001 --status passed --summary "Reviewed fake-worker result; only note-a.md changed with the expected TASK-DEVO-156 marker." --commands-run "Get-Content note-a.md, git status --short" --files-changed note-a.md --recorded-by Manas --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-continue --project Dogfood156 --run QWR-0001 --confirm-continue
.\.venv\Scripts\devo.exe project queue-worker-record-validation --project Dogfood156 --run QWR-0001 --status passed --summary "Docs-only disposable validation passed by inspecting note-a.md and git status; no build/test/run executed." --commands-run "Get-Content note-a.md, git status --short" --files-changed note-a.md --recorded-by Manas --confirm-record
.\.venv\Scripts\devo.exe project queue-worker-continue --project Dogfood156 --run QWR-0001 --confirm-continue
.\.venv\Scripts\devo.exe project approved-queue-run --project Dogfood156 --policy POL-0001 --run QWR-0001 --message "docs: update dogfood note a" --note "TASK-DEVO-156 disposable fake-worker item T001." --no-require-scheduler-healthy --confirm-auto-run
```

Validation for this docs-only task:

```powershell
git diff --check
git diff --cached --check
```

## Observations

- `codex-worker-batch-run --dry-run` selected `QI001` / `T001`, wrote no batch-run artifact, did not spawn the fake worker, and reported `Mutation occurred: False`.
- Confirmed execute mode created the queue-worker run `QWR-0001`.
- Confirmed execute mode created preparation `CWP-20260826062007-QWR-0001`.
- Confirmed execute mode ran the fake subprocess once as `CWR-20260826062008-QWR-0001`.
- Confirmed fake worker wrote valid JSON to the expected result path.
- Confirmed strict JSON ingest created `CWI-20260826062008-QWR-0001`.
- Confirmed the run advanced to `waiting_review` and stopped with `Stop reason: worker review missing`.
- Confirmed no automatic review or automatic validation occurred.
- Confirmed no delivery was created until review and validation evidence were recorded.
- Confirmed `approved-queue-run` created trusted delivery request `REQ-0001` after worker, review, and validation evidence existed.
- Confirmed no direct commit or push was run by the worker loop.

## Evidence Artifacts

- Batch-run artifact: `E:\DevOrchestrator\workspace\projects\Dogfood156\codex-worker\batch-runs\CWBR-0001\codex-worker-batch-run.md`
- Queue-worker run: `E:\DevOrchestrator\workspace\projects\Dogfood156\planning\queue-worker-runs\queue-worker-run-QWR-0001.md`
- Raw ingest copy: `E:\DevOrchestrator\workspace\projects\Dogfood156\codex-worker\ingests\CWI-20260826062008-QWR-0001\raw-result-copy.json`
- Delivery runner request: `E:\DevOrchestrator\workspace\projects\Dogfood156\delivery\runner-requests\runner-request-req-0001.md`

## What Worked Well

- The new command removed the old manual sequence of queue-worker run creation, prompt preparation, subprocess execution, result lookup, and ingest.
- The dry-run behavior was clear and non-mutating.
- The v1 one-item limit was visible in output.
- The stop at review gate was loud and correct.
- The fake worker path proved stdin prompt passing and expected-result-path output without invoking real Codex.
- The follow-up state was recoverable through existing evidence commands and `approved-queue-run`.

## Friction

- Disposable repo setup still requires care. In this sandbox, the initial local push to a disposable bare remote failed with a Git-for-Windows shell permission error, so the disposable repo had no upstream branch.
- `execution-policy-create` option memory is still easy to miss: the actual option is `--max-changed-files-per-task`, not `--max-changed-files`.
- `approved-queue-run` created a delivery request even though delivery readiness had a no-upstream warning. This is safe because the trusted runner is still a separate gate, but the output should make "delivery request created, runner may still block on upstream" especially obvious.
- The review evidence output showed validation state as `provided` before independent validation evidence was recorded. That is technically traceable, but it can read as noisier than necessary.

## Delivery Runner Path

The trusted delivery request path was reached safely:

- Request: `REQ-0001`
- Status: `requested`
- Next command printed by Devo:

```powershell
.\.venv\Scripts\devo.exe delivery runner-run --project Dogfood156 --request REQ-0001 --approver "Manas" --confirm-runner-delivery
```

The trusted runner was not executed for the disposable project because the target repo lacked a configured upstream after the sandbox-local push failure. This was treated as not safe enough to force inside this task. The live DevOrchestrator docs delivery should still use the normal trusted runner request flow.

TASK-DEVO-157 follows up on this caveat by making disposable dogfood setup guidance explicit: use a local bare remote with a `file:///...` URL when practical, run the initial `git push -u origin main`, and verify `git branch -vv` plus `git remote -v` before treating a disposable repo as ready for trusted runner delivery.

## Verdict

PASS with delivery-runner caveat.

The core TASK-DEVO-155 v1 behavior is dogfooded successfully: at least one disposable queue item reached worker-evidence-ingested, stopped at the review gate, then advanced through manual review and validation evidence to a trusted delivery request. No real Codex CLI was run, no PersonalOS commands were run, no parallel worker behavior was used, and no direct commit/push was done by the worker loop.

## Recommended TASK-DEVO-157

TASK-DEVO-157 should polish batch-run dogfood friction:

- Add clearer delivery-readiness wording when a trusted delivery request exists but the target repo has no upstream.
- Add a tiny `execution-policy-create` UX hint or docs example using `--max-changed-files-per-task`.
- Consider a disposable-dogfood setup checklist that explicitly verifies upstream before attempting runner delivery.
- Consider reducing noisy "worker-reported validation" wording after review evidence when independent validation is still intentionally pending.

TASK-DEVO-157 scope keeps this as polish only. It should not add real Codex batch dogfood, parallel workers, UI actions, PersonalOS changes, or delivery safety weakening.
