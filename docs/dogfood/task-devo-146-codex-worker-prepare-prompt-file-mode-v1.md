# TASK-DEVO-146 Codex Worker Prepare Prompt-File Mode V1

## Why Prompt-File Mode Is First

Prompt-file mode is the safest first Codex-worker integration step because it improves the handoff package without launching Codex, calling AI APIs, or trusting worker output automatically. The operator still controls the actual Codex session.

## Command Added

```powershell
.\.venv\Scripts\devo.exe project codex-worker-prepare --project <project> --run <QWR-ID> --confirm-prepare
```

Optional helpers:

- `codex-worker-prepare-show`
- `codex-worker-prepare-latest`
- `codex-worker-prepare-list`

## Generated Artifacts

Prompt packages are workspace-only artifacts under:

```text
workspace/projects/<project>/codex-worker/preparations/<CWP-ID>/
```

Each package contains:

- `codex-worker-prompt.md`
- `worker-result-template.json`
- `worker-result-template.md`
- `codex-worker-prepare.json`
- `codex-worker-prepare.md`

## Preflight Checks

The command requires:

- registered project and existing target path
- existing queue-worker run
- queue-worker run status `waiting_worker`
- linked execution policy exists and is `approved`
- selected queue item and task are identifiable
- handoff checklist exists or can be built from current queue-worker state
- current Git status is captured
- no delivery request state is already attached to the queue-worker run

## Prompt Contents

The generated prompt includes:

- identity and one-task objective
- target repo path, branch, upstream, and Git status summary
- lightweight handoff checklist
- policy summary
- worker boundaries such as one task only, no commit, no push, no secrets, no broadening scope
- validation expectations
- worker output contract
- next Devo evidence-recording commands

## Result Templates

The JSON template is valid JSON and includes:

- `status`
- `summary`
- `work_performed`
- `changed_files`
- `commands_run`
- `risks`
- `recommended_next_action`
- `artifact_path`
- `dirty_repo_status`
- `usage_limit_details`
- `failure_details`
- `recorded_by`
- `created_at`

The Markdown template provides the same fields in a form that is easy for a human or Codex session to fill.

## Manual Use

The operator gives `codex-worker-prompt.md` to Codex manually. After Codex finishes, the operator records worker evidence with `queue-worker-record-worker-result`, then continues the approved queue through `approved-queue-run`.

## Still Manual

This task does not run Codex, ingest worker results, review output, run validation, create delivery requests, commit, or push.

## Why Subprocess Execution Is Future

Direct subprocess execution still needs launcher readiness, output capture, timeout handling, usage-limit recovery, and result ingestion. Prompt-file mode proves the package and contract first.

## Recommended Next Task

TASK-DEVO-147: Codex worker result ingest v1.
