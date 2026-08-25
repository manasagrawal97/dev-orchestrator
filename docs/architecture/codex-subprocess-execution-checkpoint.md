# Codex Subprocess Execution Checkpoint

## 1. Current Readiness

TASK-DEVO-148 proved the prompt-file Codex worker loop is usable:

```text
codex-worker-prepare
-> manual worker result JSON
-> codex-worker-ingest
-> worker evidence
-> review evidence
-> validation evidence
-> trusted runner delivery
-> completion detection
```

Devo already has the pieces needed to consider a narrow subprocess step:

- `approved-queue-run`
- `queue-worker-loop`
- lightweight handoff checklist
- worker evidence schema v1
- `codex-worker-prepare`
- `codex-worker-ingest`
- review evidence
- validation evidence
- trusted runner delivery
- `runner-recover-push`
- 3-task assisted queue dogfood pass
- prompt-file Codex worker dogfood pass

These pieces make subprocess execution possible, but only under strict boundaries. The prompt package and result ingest contract are now proven; launching Codex remains the risky part.

## 2. Why Subprocess Execution Is Risky

Subprocess execution adds process, launcher, and repo-state risk that prompt-file mode avoids:

- Codex CLI command and non-interactive behavior may vary by installation/version.
- Windows launcher/path issues may happen.
- Codex may run in a sandbox context that cannot create `.git/index.lock`.
- Codex may hit usage limits mid-task.
- Codex may leave the repo dirty.
- Codex may change files outside allowed scope.
- Codex may not produce a clean result file.
- Codex output may be unclear or incomplete.
- Subprocess timeout/cancellation needs careful handling.
- Devo must not allow Codex to commit/push directly.

Known Devo history matters here: Codex/sandbox previously could not create `.git/index.lock`, while normal PowerShell delivery succeeded. Trusted runner remains the only safe commit/push path.

## 3. Non-Goals

This checkpoint does not approve:

- autonomous multi-task Codex batches
- parallel workers
- a 300-agent system
- voice/Jarvis/gesture/clap controls
- ECC adoption
- Claude-Code-only direction
- AI/API default path
- automatic review
- automatic validation
- Codex commit/push
- bypassing trusted runner delivery

## 4. Proposed Subprocess V1 Scope

Smallest safe v1:

- One approved queue-worker run only.
- Run must be `waiting_worker`.
- Policy must be approved.
- Handoff checklist must exist.
- Prompt package must be generated first.
- Codex subprocess receives the generated prompt file.
- Codex must write or return a result JSON.
- Devo does not treat execution as success until result ingest succeeds.
- Devo does not run review/validation/delivery automatically.
- Codex does not commit or push.

Recommended future command shape:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-run --project <project> --run <QWR-ID> --prepare <CWP-ID> --confirm-codex-worker
```

Optional future flags to design, not implement in this checkpoint:

- `--timeout-minutes 30`
- `--dry-run`
- `--result-file <path>`
- `--recorded-by "Manas"`
- `--note "..."`

## 5. Required Subprocess Preflight Checks

The future command must block unless all required checks pass:

- project exists
- target repo exists
- queue-worker run exists
- run is `waiting_worker`
- policy exists and is approved
- prepare package exists
- prepare package belongs to the same project/run
- prompt file exists
- result template exists
- working tree is clean before launch
- branch/upstream captured
- no pending delivery request for the same run
- no existing successful worker evidence for the run
- Codex executable/launcher configuration exists
- timeout is configured
- output/result path is configured

## 6. Execution Model

Recommended v1 model:

- Devo runs Codex from the target repo root.
- Devo passes the generated prompt file content or prompt file path.
- Devo sets an expected result JSON output path.
- Devo captures stdout/stderr to workspace artifacts.
- Devo captures process exit code.
- Devo captures timeout/cancellation.
- Devo snapshots Git status before and after.
- Devo does not commit or push.
- Devo requires result ingest after execution.

Exact Codex CLI syntax is an implementation detail to confirm during TASK-DEVO-150.

## 7. Output Artifacts

Future subprocess runs should create workspace-only artifacts under:

```text
workspace/projects/<project>/codex-worker/runs/<CWR-ID>/
```

Expected artifacts:

- `codex-worker-run.json`
- `codex-worker-run.md`
- `stdout.txt`
- `stderr.txt`
- `prompt-used.md`
- `expected-result-path.json`
- `git-status-before.txt`
- `git-status-after.txt`
- `process-info.json`

Do not stage or commit these workspace artifacts.

## 8. Result Handling

Recommended v1 handling:

- If Codex writes valid result JSON: run `codex-worker-ingest` manually or as a separate explicit command.
- If Codex completes but no result JSON exists: mark subprocess run `missing_result`; do not record completed evidence.
- If Codex exits non-zero: mark subprocess run `failed_process`; operator decides whether to record failed evidence.
- If Codex hits usage limit: mark `usage_limit`; `approved-queue-run` must not continue as success.
- If repo is dirty: preserve status details; do not commit/push; operator reviews.
- If scope violation is detected: mark `scope_violation`; block continuation.

For v1, prefer explicit ingest after subprocess, not automatic ingest, unless a later task proves automatic ingest safe.

## 9. State Classification

Suggested subprocess states:

| State | Meaning | Allows continuation? |
| --- | --- | --- |
| `prepared` | Subprocess run artifact exists but has not started. | No. |
| `running` | Process is currently running. | No. |
| `completed_process` | Process exited zero, result not yet verified. | No. |
| `completed_with_result` | Process exited and result file exists. | Ingest may proceed. |
| `failed_process` | Process exited non-zero. | No. |
| `timeout` | Timeout expired. | No. |
| `cancelled` | Operator cancelled. | No. |
| `usage_limit` | Output/result indicates usage limit. | No. |
| `missing_result` | Expected result JSON is absent. | No. |
| `dirty_repo_unexpected` | Repo state was dirty before launch or unexpectedly dirty after launch. | No. |
| `scope_violation` | Changed files violate policy/scope. | No. |
| `ingest_ready` | Result JSON is ready for explicit ingest. | Ingest may proceed. |
| `ingested` | Worker evidence was recorded through `codex-worker-ingest`. | Review gate may proceed. |
| `blocked` | Any conservative blocker. | No. |

Only `completed_with_result` / `ingest_ready` should lead to result ingest, and only `ingested` should allow normal review/validation gates.

## 10. Usage-Limit Handling

If usage limit is detected or reported:

- stop worker run safely
- preserve stdout/stderr/result if any
- do not retry automatically in v1
- print exact retry/manual next action
- allow a later explicit retry task

Automatic retry is not part of subprocess v1.

## 11. Dirty Repo Handling

Clean repo before subprocess is preferred and should be required for v1.

After subprocess, a dirty repo is expected if Codex changed files. That dirty repo must be inspected before worker evidence is considered completed. Unexpected dirty repo before launch blocks. Unexpected changes outside allowed scope block. Commit/push remains trusted runner only.

## 12. Scope Checking

Lightweight v1 scope check:

- compare changed files after subprocess against allowed/relevant files and forbidden scope
- block obvious forbidden paths
- warn when allowed scope is broad or unspecified
- do not overbuild least-privilege permissions yet

This is a safety check, not a full role-permission system.

## 13. Manual Override Model

Any override must be explicit. Devo should not hide auto-continue behavior after unsafe subprocess states.

Prefer separate commands for retry, ingest, review, validation, and delivery.

## 14. Recommended Implementation Sequence

Recommended next tasks:

1. TASK-DEVO-150: Codex subprocess configuration and dry-run launcher v1 - completed.
2. TASK-DEVO-151: Codex subprocess execution v1 for one safe run - completed.
3. TASK-DEVO-152: Real Codex subprocess dogfood for one safe disposable task.
4. TASK-DEVO-153: Usage-limit and retry handling v1.
5. TASK-DEVO-154: Batch Codex-worker loop design.

TASK-DEVO-150 is complete and remains conservative: it adds workspace-only config plus dry-run preview artifacts without launching Codex or calling AI/API. TASK-DEVO-151 is complete and adds a one-task subprocess execution command with fake-command tests. Real Codex execution remains a separate dogfood task.

## 15. Final Checkpoint Verdict

- Prompt-file mode: usable.
- Direct subprocess execution: implemented only as a one-task explicit-confirmation command.
- Readiness verdict: ready for one disposable real-Codex dogfood run, not full autonomous execution.
- Next safe step: real Codex subprocess dogfood for one safe disposable task.
