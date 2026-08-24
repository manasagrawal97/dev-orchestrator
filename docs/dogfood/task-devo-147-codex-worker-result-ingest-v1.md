# TASK-DEVO-147: Codex Worker Result Ingest V1

## Goal

TASK-DEVO-147 adds the safe next step after TASK-DEVO-146 prompt-file preparation:

1. Devo prepares a Codex worker prompt package.
2. A human/Codex worker fills a JSON result file from the template.
3. Devo ingests that result file.
4. Devo validates the result status and useful detail.
5. Devo records queue-worker worker evidence schema v1.

This keeps the prompt-file/manual Codex loop auditable without launching Codex automatically.

## Command Added

```powershell
devo project codex-worker-ingest --project <project> --run <QWR-ID> --result-file <path> --confirm-ingest
```

Optional helpers:

```powershell
devo project codex-worker-ingest --project <project> --run <QWR-ID> --result-file <path> --dry-run
devo project codex-worker-ingest --project <project> --run <QWR-ID> --prepare <CWP-ID> --result-file <path> --confirm-ingest
devo project codex-worker-ingest-list --project <project>
devo project codex-worker-ingest-latest --project <project>
devo project codex-worker-ingest-show --project <project> --ingest <CWI-ID>
```

## Supported Result Format

V1 supports JSON files matching `worker-result-template.json`.

Markdown result ingest remains future scope. The Markdown template is still useful for human notes, but JSON is the canonical ingest input for v1.

## Preflight Checks

Ingest verifies:

- project exists
- target repo path exists
- queue-worker run exists
- queue-worker run is `waiting_worker`
- execution policy exists and is `approved`
- worker report/evidence is not already imported
- result file exists and is readable JSON
- status is present and one of `completed`, `failed`, `blocked`, or `usage_limit`
- completed results include summary plus useful detail
- optional preparation id exists and belongs to the same project/run

## Evidence Mapping

The JSON result maps into existing queue-worker worker evidence:

- `status` -> worker evidence status
- `summary` -> evidence summary
- `changed_files` -> evidence changed files
- `commands_run` -> evidence commands
- `risks` -> evidence risks
- `recommended_next_action` -> evidence next action
- `artifact_path` -> supporting artifact when provided
- raw result file -> preserved copy in ingest artifacts

Extra fields such as `work_performed`, `dirty_repo_status`, `usage_limit_details`, and `failure_details` are preserved in the ingest artifact.

## Status Behavior

- `completed`: records completed worker evidence; next action is `approved-queue-run` for the review gate.
- `blocked`: records non-success worker evidence; the queue must not advance as successful work.
- `failed`: records non-success worker evidence; inspect and retry or cancel.
- `usage_limit`: records non-success worker evidence; wait for usage reset or retry later.

Unknown or missing statuses are blocked.

## Dry Run

`--dry-run` reads and validates the result file, shows the mapped evidence fields, and writes nothing.

```text
Mutation occurred: False
```

## Artifacts

Ingest artifacts are workspace-only and must not be committed:

```text
workspace/projects/<project>/codex-worker/ingests/<CWI-ID>/
  codex-worker-ingest.json
  codex-worker-ingest.md
  raw-result-copy.json
```

The canonical worker report/evidence remains in the existing worker report artifact path so existing queue-worker review, validation, and delivery gates continue to work.

## Still Manual

This task does not:

- run Codex
- call Codex Desktop
- call OpenAI or any AI/API
- run review
- run validation
- create delivery
- commit or push
- bypass policy, handoff, evidence, review, validation, or trusted delivery gates

## Recommended Next Task

TASK-DEVO-148: Prompt-file Codex worker dogfood.
