# TASK-DEVO-141 Worker Result Evidence Schema V1

## Why This Exists

`approved-queue-run` can only be useful if worker, review, and validation evidence are deterministic enough to consume safely. Earlier evidence intake worked, but the structured shape was spread across worker report and review fields.

TASK-DEVO-141 adds a small shared evidence record shape while preserving the existing queue-worker state machine.

## Evidence Schema V1

The shared record includes:

- `evidence_id`
- `project`
- `queue_worker_run_id`
- `queue_item_id`
- `task_id`
- `evidence_type`
- `status`
- `summary`
- `changed_files`
- `commands_run`
- `artifact_path`
- `risks`
- `recommended_next_action`
- `note`
- `created_at`
- `recorded_by`

Worker-result evidence is stored on the existing worker report artifact. Review evidence is stored on the existing worker review artifact. Validation evidence is stored inside the review artifact's validation evidence block.

## Command Behavior

The existing evidence commands keep their current options and now accept:

- `--risks`
- `--recommended-next-action`
- `--recorded-by`

The commands print the evidence id, evidence type, status, queue-worker run, queue item/task, changed files, commands run, risks, recommended next action, artifact path, and next Devo command.

## Compatibility

Older worker report/review artifacts without the new fields remain readable because the structured record fields are optional. Missing optional fields default to `none`, empty lists, or null-equivalent values. Missing or unknown statuses are still not treated as success.

## Safety And Approved Queue Consumption

`approved-queue-run` continues to consume the existing queue-worker evidence summary, now backed by the structured records written by the intake commands.

Only these states advance:

- worker result `completed`
- review `passed`
- validation `passed`

Non-success statuses such as `failed`, `blocked`, `not_run`, `provided`, `needs_changes`, `rejected`, and `usage_limit` stop or pause the loop and do not create trusted delivery requests.

## Still Blocking Real Codex Worker Integration

This task does not run real Codex, validation commands, runner-watch, commit, push, or multiple tasks automatically. Real worker integration still needs a safe launcher, bounded execution policy, stronger handoff checklist, and continued dogfood.

## Future-Scope Learnings

Recent exploratory ideas were documented as future scope only:

- Devo remains text-driven; there is no current plan for voice, Jarvis, gesture, or clap-triggered control.
- ECC / Everything Claude Code may be compared as a benchmark spike, but Devo should not copy ECC or become Claude-Code-only.
- Parallel review workers may be explored later as small read-only verification helpers; no "300 agents" or parallel editing agents now.
- Least-privilege role permissions are useful later after real worker roles exist.

## Recommended Next Task

TASK-DEVO-142: Lightweight handoff checklist v1.
