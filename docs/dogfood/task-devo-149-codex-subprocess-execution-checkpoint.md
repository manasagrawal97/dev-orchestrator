# TASK-DEVO-149: Codex Subprocess Execution Checkpoint

## Why This Is Design-Only

TASK-DEVO-149 answers whether Devo is ready to move from prompt-file/manual Codex worker mode toward direct Codex CLI subprocess execution. It does not launch Codex, call Codex Desktop, call AI/API models, implement subprocess execution, or change CLI behavior.

## What TASK-DEVO-148 Proved

TASK-DEVO-148 proved that prompt-file worker mode is usable on a disposable project:

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

The dogfood also showed that push-only recovery and trusted runner delivery remain important when the current process context has Windows/Git restrictions.

## Risks Before Subprocess Execution

Direct Codex subprocess execution remains riskier than prompt-file mode because launcher behavior, non-interactive CLI behavior, Windows path/alias issues, usage limits, timeout handling, unclear output, dirty repo state, missing result files, and scope violations all become Devo's responsibility to detect and stop safely.

Codex must not commit or push. Trusted runner delivery remains the only safe commit/push path.

## Recommended Subprocess V1 Scope

The recommended v1 is deliberately narrow:

- one approved queue-worker run only
- run must be `waiting_worker`
- approved policy required
- handoff checklist and prompt package required
- Codex receives the generated prompt package
- Codex writes an expected JSON result file
- Devo captures stdout/stderr/process metadata/Git status
- result ingest remains explicit
- review, validation, and delivery remain separate explicit gates
- no Codex commit/push

Suggested future command shape:

```powershell
.\.venv\Scripts\devo.exe project codex-worker-run --project <project> --run <QWR-ID> --prepare <CWP-ID> --confirm-codex-worker
```

## Recommended Next Task

TASK-DEVO-150: Codex subprocess configuration and dry-run launcher v1.

This should design and implement only configuration/dry-run launcher behavior. It should use fake-executable tests and must not run real Codex.

## Final Verdict

- Prompt-file mode: usable.
- Direct subprocess execution: not implemented.
- Subprocess readiness verdict: ready only for a very narrow one-task subprocess v1, after this design checkpoint.
- Next safe step: subprocess configuration + dry-run launcher, not full execution.
