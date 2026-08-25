# TASK-DEVO-151 One-Task Codex Subprocess Execution V1

## Goal

TASK-DEVO-151 adds the first narrow subprocess execution path for a single approved queue-worker run. It builds on `codex-worker-prepare`, `codex-worker-ingest`, subprocess config, and dry-run preview.

This task intentionally supports one prepared run at a time. It does not add automatic queue execution, automatic ingest, automatic review, automatic validation, automatic delivery, commit, or push.

## Command Added

```powershell
devo project codex-worker-run --project <project> --run <QWR-ID> --prepare <CWP-ID> --confirm-codex-worker
```

Useful options:

```text
--timeout-minutes <minutes>
--result-file <path>
--recorded-by "Manas"
--note "..."
--dry-run
--confirm-codex-worker
```

`--dry-run` delegates to `codex-worker-run-preview` and does not spawn a subprocess.

## Preflight Checks

Before execution, Devo verifies:

- project and target repository exist
- queue-worker run exists
- run status is `waiting_worker`
- no delivery request is already attached to the run
- no successful worker evidence has already been imported
- execution policy exists and is approved
- preparation package exists and belongs to the same project/run
- prompt file and worker result template exist
- subprocess config exists and is valid
- configured command is resolvable
- timeout is valid
- target repository is clean before launch

Scheduler health is not required because this command does not deliver.

## Subprocess Artifacts

Run artifacts are workspace-only:

```text
workspace/projects/<project>/codex-worker/runs/<CWR-ID>/
```

Files:

- `codex-worker-run.json`
- `codex-worker-run.md`
- `stdout.txt`
- `stderr.txt`
- `prompt-used.md`
- `expected-result-path.json`
- `git-status-before.txt`
- `git-status-after.txt`
- `process-info.json`
- `planned-command.txt`

## Result States

The v1 command classifies:

- `completed_with_result`
- `completed_missing_result`
- `failed_process`
- `timeout`
- `scope_warning`
- `scope_violation`
- `blocked_preflight`

For `completed_with_result`, Devo prints the next `codex-worker-ingest` command. It still does not ingest automatically.

## Fake-Command Test Approach

Implementation and validation used fake local Python scripts only. The tests cover:

- missing/non-waiting run blockers
- missing/unapproved policy blockers
- missing/mismatched preparation blockers
- missing config blocker
- dirty repository blocker before launch
- dry-run no-spawn behavior
- fake command stdout/stderr/exit-code capture
- `completed_with_result`
- `completed_missing_result`
- `failed_process`
- `timeout`
- no automatic worker evidence ingest

## Real Codex Boundary

Real Codex was not launched during implementation. Codex Desktop was not called. No OpenAI or other AI/API call was made.

The next safe step is a disposable real-Codex dogfood run after the operator has a safe launcher and understands the stop conditions.

Recommended next task:

```text
TASK-DEVO-152: Real Codex subprocess dogfood for one safe disposable task
```
