# TASK-DEVO-152 Real Codex Subprocess Dogfood

## Scenario

TASK-DEVO-152 dogfooded the one-task Codex subprocess runner setup path against a disposable repository only.

Disposable target:

- Project: `Dogfood152`
- Work repo: `E:\DevOrchestrator\pt-152-dogfood\work`
- Bare remote: `E:\DevOrchestrator\pt-152-dogfood\remote.git`
- Task: update `dogfood-note.md` with one short line proving Codex subprocess execution.

DevOrchestrator was used only as the controller and documentation repo. It was not used as the Codex subprocess target.

## Prerequisite Check

The initial DevOrchestrator checks showed:

- `git status`: clean.
- `delivery latest --project DevOrchestrator`: latest runner request `REQ-0039` completed and pushed.
- `delivery runner-latest --project DevOrchestrator`: `REQ-0039` completed with commit `0c2bc5805e1fd8f5db44e75742db424fe335dabf`.
- `codex-worker-run`, `codex-worker-run-preview`, and `codex-worker-config-show` commands exist.
- Scheduler checks from the Codex/sandbox context still reported drift, which matches the known environment visibility mismatch. No scheduler repair was attempted.

## Disposable Repo Setup

Created `E:\DevOrchestrator\pt-152-dogfood\work` with:

- `README.md`
- `dogfood-note.md`

Created `E:\DevOrchestrator\pt-152-dogfood\remote.git` as a local bare remote.

Initial disposable commit:

- `7f338f8 chore: initialize dogfood repo`

The first local push from the restricted context failed with a Git-for-Windows shell permission error:

```text
C:\Program Files\Git\usr\bin\sh.exe: fatal error - couldn't create signal pipe, Win32 error 5
```

Retrying the disposable repo push outside the sandbox succeeded:

```text
To file:///E:/DevOrchestrator/pt-152-dogfood/remote.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

This affected only the ignored disposable repo and local bare remote.

## Planning And Queue Artifacts

Registered project:

- `Dogfood152`

Planning chain:

- Project Brief: created and approved.
- Blueprint: created and approved.
- Backlog: refined to one task and approved.
- Batch: `B001`, approved by Manas.
- Queue: `Q001`, started.
- Queue item: `QI001`.
- Backlog task: `T001`.
- Execution policy: `POL-0001`, requested and approved by Manas.

Policy bounds:

- Allowed task: `T001`
- Allowed file: `dogfood-note.md`
- Forbidden files: `.env`, `workspace/**`
- Validation command recorded: `git status --short`
- Max tasks: 1
- Max tasks per run: 1
- Max changed files per task: 1

## Queue Worker Run

Command path used:

```powershell
.\.venv\Scripts\devo.exe project approved-queue-run --project Dogfood152 --policy POL-0001 --confirm-auto-run --no-require-scheduler-healthy
```

Result:

- Queue-worker run: `QWR-0001`
- Worker run: `WR001`
- Status: `waiting_worker`
- Stop reason: worker result missing
- Blockers: none
- Warnings: none

The `--no-require-scheduler-healthy` flag was used because this Codex/sandbox context reports trusted-runner scheduler drift while normal PowerShell evidence is known healthy. No delivery was attempted.

## Preparation

Preparation id:

- `CWP-20260825120009-QWR-0001`

Artifacts:

- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\codex-worker-prepare.json`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\codex-worker-prepare.md`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\codex-worker-prompt.md`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\worker-result-template.json`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\worker-result-template.md`

Preparation status:

- Target repo: clean
- Branch: `main`
- Upstream: `origin/main`
- Warnings: none

## Codex Worker Config

Config used:

```text
command: codex
args_template: run --prompt-file "{prompt_path}" --output-file "{result_path}"
timeout_minutes: 30
result_file_name: codex-worker-result.json
```

Config artifact:

- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\config\codex-worker-config.json`

The default args were not proven against real Codex in this run. They were only previewed.

## Run Preview

Preview id:

- `CWRP-20260825120021-QWR-0001`

Preview artifacts:

- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\run-previews\CWRP-20260825120021-QWR-0001\codex-worker-run-preview.json`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\run-previews\CWRP-20260825120021-QWR-0001\codex-worker-run-preview.md`
- `E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\run-previews\CWRP-20260825120021-QWR-0001\planned-command.txt`

Planned command:

```powershell
codex run --prompt-file E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\preparations\CWP-20260825120009-QWR-0001\codex-worker-prompt.md --output-file E:\DevOrchestrator\workspace\projects\Dogfood152\codex-worker\run-previews\CWRP-20260825120021-QWR-0001\codex-worker-result.json
```

Preview result:

- Codex launched: false
- AI/API called: false
- Current git status: clean
- Warnings: none
- Blockers: none
- Mutation occurred: true, workspace preview artifact only

## Real Subprocess Execution

Real Codex subprocess launched: no.

Reason: this run is executing inside a Codex/sandbox context. Launching real Codex from inside this task is unsafe/recursive/unclear, and the task instructions explicitly said not to force it in that situation.

Exact normal PowerShell command for Manas:

```powershell
cd E:\DevOrchestrator
.\.venv\Scripts\devo.exe project codex-worker-run --project Dogfood152 --run QWR-0001 --prepare CWP-20260825120009-QWR-0001 --recorded-by "Manas" --note "TASK-DEVO-152 normal PowerShell real Codex subprocess run." --confirm-codex-worker
```

After that command, inspect the emitted `CWR-*` run artifact. If it writes the expected result JSON, continue with:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-ingest --project Dogfood152 --run QWR-0001 --result-file <codex-worker-result.json> --confirm-ingest
```

Then continue the normal explicit gates: review evidence, validation evidence, approved queue run, trusted runner request, and trusted delivery only if safe.

## Result State

Because real Codex subprocess execution was not launched:

- Run id/path: not reached.
- stdout summary: not reached.
- stderr summary: not reached.
- exit code: not reached.
- result state: not reached.
- result JSON existed: no.
- ingest result: not reached.
- review evidence result: not reached.
- validation evidence result: not reached.
- delivery request/result: not reached.
- completion detection behavior: not reached.

The queue remains at `waiting_worker` for `QWR-0001`.

## What Worked

- Disposable project registration worked.
- Brief, blueprint, refined one-task backlog, batch, queue, and policy setup worked.
- `approved-queue-run` created exactly one queue-worker run and stopped at the worker-evidence boundary.
- `codex-worker-prepare` produced a focused prompt package for the disposable repo.
- `codex-worker-config-set` recorded a conservative default subprocess config.
- `codex-worker-run-preview` produced readable planned-command/stdout/stderr/result paths with no blockers.
- The disposable `pt-*` folder is ignored by DevOrchestrator Git.

## What Was Awkward

- Creating a one-task refined backlog required hand-writing JSON rather than a small "one task" helper.
- TASK-DEVO-153 resolves the stale preview wording: preview now points to `codex-worker-run --confirm-codex-worker` as the explicit one-run path instead of saying execution is not implemented.
- Scheduler health remains noisy inside Codex/sandbox despite normal PowerShell evidence being healthy.
- The first local bare-remote push from the restricted context hit the same Windows process/security family of issue as earlier Git operations.

## What Felt Unsafe

- Launching real Codex from inside this Codex task would be recursive and unclear.
- Running delivery or queue completion without real worker output would fabricate evidence.

## Manual Smoke

Safe DevOrchestrator smoke after the Dogfood152 preview showed:

- `project codex-worker-run --help`: command exists.
- `project codex-worker-run-preview --help`: command exists.
- `project codex-worker-config-show --project DevOrchestrator`: no DevOrchestrator config found; read-only.
- `project approved-queue-run --project DevOrchestrator --policy POL-0001 --dry-run`: blocked because `POL-0001` is draft, as expected.
- `delivery runner-schedule-status --project DevOrchestrator`: reports scheduler drift from this Codex/sandbox context.
- `delivery runner-schedule-doctor --project DevOrchestrator`: read-only drift report; no scheduler changes made.

The scheduler result matches the known restricted-context visibility mismatch. It was not treated as a reason to reinstall the scheduler.

## Small Fixes Made

No source-code fixes were made.

Docs were updated to record the dogfood state and operator continuation command.

## Remaining Manual Steps

1. Manas runs the real subprocess command from normal PowerShell.
2. Inspect the `CWR-*` run artifact.
3. If result JSON exists and is valid, run `codex-worker-ingest`.
4. Record review evidence.
5. Record validation evidence.
6. Use `approved-queue-run` to request trusted delivery if safe.
7. Deliver the disposable repo change through the trusted runner only.
8. Run `approved-queue-run` again to observe completion.

## Readiness Verdicts

- Real Codex subprocess dogfood attempted: no.
- Real Codex subprocess completed task: no.
- Result JSON produced automatically: no.
- Ingest path worked: not reached.
- Ready for recovery hardening: no. Run one real normal-PowerShell subprocess attempt first.
- Ready for batch Codex-worker loop: no.

## Recommended Next Task

Recommended next task:

- `TASK-DEVO-152A: Run the prepared Dogfood152 real Codex subprocess command from normal PowerShell and record the result`, after applying the TASK-DEVO-153 default command-shape hardening.

After that succeeds or fails with concrete `CWR-*` artifacts, continue to:

- `TASK-DEVO-153: Codex subprocess recovery hardening`
