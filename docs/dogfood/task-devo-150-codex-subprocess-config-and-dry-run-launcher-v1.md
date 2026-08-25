# TASK-DEVO-150 Codex Subprocess Config And Dry-Run Launcher V1

## Goal

TASK-DEVO-150 adds the safe foundation for future Codex CLI subprocess execution without actually launching Codex. The intended future path is:

```text
approved queue item
-> queue-worker run waiting_worker
-> codex-worker-prepare creates prompt package
-> codex-worker-run-preview validates command/config
-> later task launches Codex subprocess
-> codex-worker-ingest records result
-> approved-queue-run continues
```

This task implements configuration and dry-run preview only.

## Commands Added

```powershell
devo project codex-worker-config-show --project <project>
devo project codex-worker-config-set --project <project> --command "codex" --timeout-minutes 30 --confirm-config
devo project codex-worker-config-validate --project <project>
devo project codex-worker-run-preview --project <project> --run <QWR-ID> --prepare <CWP-ID>
```

## Config Fields

The workspace-only config is stored at:

```text
workspace/projects/<project>/codex-worker/config/codex-worker-config.json
```

The v1 fields are:

- `project`
- `command`
- `args_template`
- `timeout_minutes`
- `result_file_name`
- `recorded_by`
- `note`
- timestamps and warnings

The default planned command shape is:

```text
codex run --prompt-file "{prompt_path}" --output-file "{result_path}"
```

TASK-DEVO-153 supersedes this historical default. Current recommended guidance is `codex exec -s workspace-write --output-last-message "{result_path}"`, with Devo passing the generated prompt content on stdin.

That default is only a planned command shape. It does not prove the operator's installed Codex CLI supports those exact arguments.

## Run-Preview Preflight

`codex-worker-run-preview` checks that:

- the project and target repository exist
- the queue-worker run exists and is `waiting_worker`
- the execution policy exists and is approved
- the Codex worker preparation exists and belongs to the same project/run
- `codex-worker-prompt.md` and `worker-result-template.json` exist
- subprocess config exists and has no config blockers
- the target repository Git state can be captured and is clean before preview
- there is no pending delivery request or successful worker evidence for the run

Preview does not require scheduler health because it does not deliver.

## Preview Artifacts

Preview artifacts are workspace-only and are not committed:

```text
workspace/projects/<project>/codex-worker/run-previews/<CWRP-ID>/
```

Minimum files:

- `codex-worker-run-preview.json`
- `codex-worker-run-preview.md`
- `prompt-used.md`
- `planned-command.txt`
- `planned-stdout-path.txt`
- `planned-stderr-path.txt`
- `planned-result-path.txt`
- `git-status-before.txt`
- `process-info.json`

The command records the planned working directory, prompt path, result path, stdout/stderr paths, branch/upstream/head where available, and current Git cleanliness.

## Safety Behavior

- Codex launched: `False`
- AI/API called: `False`
- Mutation occurred: `True` only for preview artifact creation
- No subprocess execution is implemented
- No automatic ingest, review, validation, delivery, commit, or push is implemented
- No UI controls or delivery safety bypasses are added

## What Remains Before Real Execution

The next task should add a very narrow, fake-tested execution path for one prepared run only. It should still preserve explicit confirmation, clean-repo preflight, stdout/stderr capture, no `shell=True`, no automatic queue completion, no automatic validation, and trusted-runner-only delivery.

Recommended next task:

```text
TASK-DEVO-151: One-task Codex subprocess execution v1
```
