# Codex Worker Launch Integration Design

## 1. Purpose

Codex worker integration is the next major step after the current assisted queue stack:

- `approved-queue-run`
- `queue-worker-loop`
- lightweight handoff checklist v1
- worker evidence schema v1
- trusted runner delivery
- push-only recovery
- 3-task approved queue dogfood pass

The goal is to move from manual/Codex-assisted implementation toward a safe one-task worker flow:

```text
approved queue item
-> lightweight handoff checklist
-> Codex worker receives task context
-> Codex works on one task
-> Devo captures worker result
-> worker evidence schema v1
-> review evidence
-> validation evidence
-> trusted runner delivery
```

This design intentionally comes before implementation. It defines the safety model, state boundaries, future command shapes, result contract, and test plan for a later Codex-worker execution task.

## 2. Non-Goals

This work is not:

- a Codex, Cursor, Claude Code, or ChatGPT clone
- AI API integration by default
- voice, Jarvis, gesture, or clap control
- ECC adoption
- parallel workers
- a 300-agent system
- least-privilege role permission implementation
- autonomous commit/push by Codex
- a bypass around review, validation, evidence, policy, or trusted delivery gates

Devo remains the manager, state machine, and safety record. Codex remains a worker backend that may be manual, prompt-file assisted, or later launched for one approved task.

## 3. Worker Launch Modes

### Mode A: Manual Handoff Mode

Devo writes a handoff prompt/checklist and the user manually opens Codex, pastes the prompt, and later imports worker output.

This is the safest early mode because Devo does not launch a subprocess and does not need to solve Codex CLI reliability, output capture, or usage-limit detection.

### Mode B: Prompt-File Assisted Mode

Devo writes a complete prompt package and command guidance for one queue-worker run. The package includes the exact worker objective, safety boundaries, expected output schema, and result-file path. The user still launches Codex manually, but no longer has to assemble context by hand.

TASK-DEVO-146 implements the first version of this mode. TASK-DEVO-147 adds JSON result ingest so a filled worker result file can become queue-worker worker evidence while preserving manual launch control. TASK-DEVO-148 dogfoods the full prompt-file loop on a disposable project and confirms the mode is usable before subprocess execution is added. TASK-DEVO-149 adds the focused checkpoint in `docs/architecture/codex-subprocess-execution-checkpoint.md`.

### Mode C: Codex CLI Subprocess Mode

A future Devo command launches Codex CLI for exactly one approved queue-worker run. Devo supplies the prompt package, captures output/logs, and expects a worker result file.

This is future scope after Mode B proves the prompt package and output contract. It requires launcher readiness, timeout handling, subprocess output capture, usage-limit detection, and strong guardrails.

## 4. Proposed Future Commands

### Prepare

```powershell
.\.venv\Scripts\devo.exe project codex-worker-prepare --project <project> --run <QWR-ID> --confirm-prepare
```

Purpose: generate a Codex-ready prompt/input package for one queue-worker run.

Expected behavior:

- read the queue-worker run, queue item, task, policy, handoff checklist, and current Git status
- write a prompt package under the Devo workspace
- write JSON and Markdown worker result templates
- print the prompt path and manual launch guidance
- not launch Codex
- not record evidence automatically
- not modify the target repo

Implemented helper commands:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-prepare-list --project <project>
.\.venv\Scripts\devo.exe project codex-worker-prepare-latest --project <project>
.\.venv\Scripts\devo.exe project codex-worker-prepare-show --project <project> --prepare <CWP-ID>
.\.venv\Scripts\devo.exe project codex-worker-ingest --project <project> --run <QWR-ID> --result-file <path> --confirm-ingest
.\.venv\Scripts\devo.exe project codex-worker-ingest-latest --project <project>
```

### Run

```powershell
.\.venv\Scripts\devo.exe project codex-worker-run --project <project> --run <QWR-ID> --confirm-codex-worker
```

Purpose: future one-task Codex CLI launch for exactly one approved queue-worker run.

Expected behavior:

- run safety preflight
- launch only after explicit confirmation
- capture logs and expected result file
- stop after one queue-worker run
- never commit or push

### Ingest

```powershell
.\.venv\Scripts\devo.exe project codex-worker-ingest --project <project> --run <QWR-ID> --result-file <path> --confirm-ingest
```

Purpose: convert a Codex worker result file into worker evidence schema v1.

Expected behavior:

- parse and validate the result file
- preserve raw output as a supporting artifact
- record worker evidence only when status is explicit and valid
- never treat unknown or missing status as success

### Status

```powershell
.\.venv\Scripts\devo.exe project codex-worker-status --project <project> --run <QWR-ID>
```

Purpose: show prompt package status, launcher readiness, latest worker result, and next action for one run.

## 5. Worker Input Package

Codex should receive only the minimum task context needed for one approved queue-worker run. It should not receive the entire Devo workspace blindly.

Minimum package fields:

- project name
- target repo path
- current branch
- queue item id
- queue-worker run id
- task objective
- lightweight handoff checklist
- approved policy summary
- allowed scope
- forbidden scope
- relevant files
- acceptance criteria
- required tests
- expected worker evidence schema
- delivery rules
- do-not-touch boundaries
- current Git status

The package should include source file paths only when relevant to the approved task. It must not include secrets, local settings values, `.env` contents, private user data, backup contents, or unrelated workspace artifacts.

## 6. Worker Output Contract

Codex should produce a structured result file that maps cleanly to worker evidence schema v1.

Minimum fields:

```yaml
status: completed | failed | blocked | usage_limit
summary: string
work_performed:
  - string
changed_files:
  - path
commands_run:
  - command
risks:
  - string
recommended_next_action: string
artifact_path: optional path
dirty_repo_status: clean | dirty | unknown
usage_limit_details: optional string
failure_details: optional string
```

The result should be human-readable and machine-parseable. JSON is likely the best first format because Devo already validates JSON artifacts.

## 7. Safety Preflight

Before launching Codex, Devo should check:

- project exists
- target repo exists
- queue-worker run exists
- run is in `waiting_worker`
- execution policy is approved
- handoff checklist exists
- working tree is clean, unless an explicit future dirty-state exception is approved
- branch/upstream match expected values
- no pending trusted delivery request exists for the same run
- run is not paused, failed, cancelled, completed, or blocked
- scheduler health is checked if delivery automation depends on it

Failure at preflight should produce a clear blocker and should not launch Codex.

## 8. Runtime Guardrails

Runtime must enforce:

- one queue-worker run at a time
- no parallel editing
- no automatic commit
- no automatic push
- no PersonalOS work unless the target project is explicitly PersonalOS
- no secrets
- no editing Devo workspace artifacts unless task scope explicitly allows docs/artifacts
- no broad refactors unless task scope allows them
- respect allowed/forbidden scope
- stop on ambiguity
- stop on usage limit
- stop on dirty or unexpected repo state

Mode C should use subprocess without `shell=True`, block WindowsApps aliases, require explicit path/wrapper readiness, and capture stdout/stderr/log paths without assuming Codex always returns structured output.

## 9. Failure States

| State | Meaning | May `approved-queue-run` continue? | Required user action | Evidence status |
| --- | --- | --- | --- | --- |
| `completed` | Worker says requested work is complete and result is valid. | Not directly; review and validation are still required. | Review the changes, record review evidence, run/record validation. | `completed` |
| `failed` | Worker attempted work and failed. | No. | Inspect failure, retry or mark run failed. | `failed` |
| `blocked` | Worker could not proceed due to missing info or scope uncertainty. | No. | Clarify scope or unblock dependency. | `blocked` |
| `usage_limit` | Worker stopped because usage/session limit was reached. | No. | Resume/retry after limit resets. | `blocked` or dedicated `usage_limit` if added |
| `timeout` | Devo subprocess timeout expired. | No. | Inspect partial logs; retry only if safe. | `blocked` |
| `dirty_repo_unexpected` | Repo dirty before/after worker in an unexpected way. | No. | Inspect Git status and changed files. | `blocked` |
| `scope_violation` | Worker changed forbidden/out-of-policy files. | No. | Revert/fix only with explicit approval. | `failed` |
| `missing_result` | Expected result file is absent. | No. | Inspect logs and import manually if available. | `blocked` |
| `unclear_result` | Result exists but status/schema is missing or ambiguous. | No. | Fix/import a valid result file. | `blocked` |

Unknown states must never be treated as success.

## 10. Result Ingestion Design

`codex-worker-ingest` should:

- parse the worker result file
- validate required fields and allowed statuses
- preserve raw Codex output as a supporting artifact
- record worker evidence schema v1
- not treat unknown or missing status as success
- not advance without explicit `completed` status
- show the next action

Passing worker evidence should still lead to review evidence, not delivery. Failed, blocked, usage-limit, timeout, missing-result, or unclear-result evidence should stop the queue safely.

## 11. Review And Validation Remain Separate

Codex worker completion does not mean the task is done.

The required sequence remains:

1. worker evidence
2. review evidence
3. validation evidence
4. trusted runner delivery
5. queue completion observation

This preserves the current safety model and avoids confusing "worker finished" with "task delivered."

## 12. Commit/Push Model

Codex worker must never commit or push directly.

Trusted runner remains the only delivery path. Codex/sandbox can prepare changes and evidence, then Devo creates a runner request. Normal PowerShell/trusted runner performs guarded delivery.

If a trusted runner commit succeeds but push fails, `runner-recover-push` is the recovery path. It requires a clean tree and `HEAD` matching the recorded delivery commit.

## 13. Suggested First Implementation Path

Recommended order:

1. TASK-DEVO-146: Codex worker prepare/prompt-file mode v1 - completed
2. TASK-DEVO-147: Codex worker ingest result v1 - completed
3. TASK-DEVO-148: prompt-file Codex worker dogfood - completed
4. TASK-DEVO-149: Codex subprocess execution design checkpoint - completed
5. TASK-DEVO-150: Codex subprocess configuration and dry-run launcher v1 - completed
6. TASK-DEVO-151: one-task Codex subprocess execution v1 - completed
7. TASK-DEVO-152: real Codex subprocess dogfood for one safe disposable task

Prompt-file mode should come before subprocess mode. It proves the input package, result schema, and ingestion flow without adding launcher/process risk.

## 14. Test Plan

Future tests should cover:

- prepare blocks without approved policy
- prepare blocks when run is not `waiting_worker`
- prepare writes prompt package
- prompt includes handoff checklist
- prompt includes allowed/forbidden scope
- prompt includes expected worker result schema
- ingest rejects missing status
- ingest rejects unknown status
- ingest records completed worker evidence
- `codex-worker-run` refuses dirty repo unless allowed
- `codex-worker-run` does not commit/push
- usage-limit result stops queue safely

Subprocess tests should use fake executables only. No real Codex CLI should run in unit tests.

## 15. Open Questions

- Which Codex CLI command/form should be used?
- Can Codex CLI reliably run non-interactively on Windows?
- How should Devo capture Codex output and result files cleanly?
- Should Devo run Codex in the target repo root or a generated worktree?
- Should the first version be prompt-file/manual instead of subprocess? The recommended answer is yes.
- How can Devo detect usage limits robustly?
- How can Devo avoid Codex/sandbox Git index-lock restrictions?
- Should result files be JSON only, or Markdown plus fenced JSON?
- How much source context is enough without overloading prompts?
- Should prompt packages include hashes of relevant files to detect stale context?
