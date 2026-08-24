# TASK-DEVO-145 Codex Worker Launch Integration Design

## Why This Is Design-Only

TASK-DEVO-145 intentionally does not implement or run a real Codex worker. The current assisted queue flow is ready for the next step, but subprocess execution adds launcher, output-capture, usage-limit, timeout, and repo-state risks. Those should be designed before any source changes.

## Current Devo Readiness After TASK-DEVO-144

TASK-DEVO-144 delivered:

- push-only runner recovery with `delivery runner-recover-push`
- `approved-queue-run --continue-next`
- clearer validation evidence wording
- `worker codex flow-summary` and `project flow-summary` defaulting to a uniquely latest queue
- passing focused and full test suites

The repo was clean before this design task, and `REQ-0032` was completed and pushed. This Codex/sandbox process still reports scheduler drift, but normal PowerShell evidence has already shown scheduler health; that remains an environment visibility mismatch, not a reason to reinstall repeatedly.

## Proposed Launch Modes

1. Manual handoff mode: Devo writes handoff context and the user manually runs Codex.
2. Prompt-file assisted mode: Devo writes a complete prompt package and result contract, but the user still launches Codex.
3. Codex CLI subprocess mode: a future Devo command launches Codex CLI for exactly one approved queue-worker run.

Mode A and Mode B are the safer early path. Mode C should wait until the prompt package and ingestion contract are proven.

## Recommended First Implementation Path

1. TASK-DEVO-146: Codex worker prepare/prompt-file mode v1
2. TASK-DEVO-147: Codex worker ingest result v1
3. TASK-DEVO-148: Codex CLI subprocess execution v1 for one safe task
4. TASK-DEVO-149: Codex worker failure/usage-limit recovery
5. TASK-DEVO-150: Batch Codex-worker loop for approved queue items

Final recommendation: start with `codex-worker-prepare` prompt-file mode before direct Codex CLI subprocess execution.

## Major Risks

- Codex CLI may not be reliable non-interactively on Windows.
- WindowsApps aliases and sandbox restrictions can break subprocess launches.
- Usage limits may not be reported in a stable machine-readable form.
- Codex may produce unclear or missing result files.
- A worker can dirty the repo unexpectedly or touch files outside scope.
- Treating worker completion as delivery would weaken Devo safety.

## Final Recommendation

Build prompt-file mode first. It gives Devo the right input package and output contract without adding launcher risk. Only after that should Devo add result ingestion, then fake-executable-tested subprocess mode, then failure recovery and broader batch continuation.

No real Codex CLI execution, AI/API calls, UI controls, delivery commits, or delivery pushes were performed for this task.
