# TASK-DEVO-190 Validation Evidence Automation

## Purpose

TASK-DEVO-190 adds the first supervised auto-mode slice: Devo can run approved policy validation commands and record validation evidence for a queue-worker run after worker and review gates have already passed.

This removes one repetitive manual evidence step without broadening autonomy. Devo still does not create delivery, run the trusted runner, stage, commit, push, approve anything, or start another queue item from this command.

## Command

Preview:

```powershell
devo project queue-worker-run-validation --project DevOrchestrator --policy POL-0001 --run QWR-0001
```

Confirmed:

```powershell
devo project queue-worker-run-validation --project DevOrchestrator --policy POL-0001 --run QWR-0001 --confirm-run-validation
```

## Behavior

Preview mode loads the project, policy, queue-worker run, and existing worker/review/validation evidence. It prints the validation commands that would run and exits without executing commands or writing evidence.

Confirmed mode requires:

- an approved execution policy
- a matching queue-worker run, queue item, and task
- completed worker-result evidence
- passed review evidence
- validation commands on the policy
- an existing target repo path

It runs each policy validation command from the target repo root, captures exit code plus bounded stdout/stderr tails, and records validation evidence as passed only when all commands pass. The first failing command records failed validation evidence and stops the validation run.

## Safety

The command records validation evidence only. It deliberately does not:

- create delivery requests
- run trusted delivery
- run Codex
- record review evidence
- approve policies or queues
- start another queue-worker run
- stage files
- commit
- push

Policy validation commands that look like delivery or Git mutation commands are blocked before execution.

## Dogfood Notes

Focused tests cover preview/no-run behavior, unapproved policy blocking, missing worker result blocking, missing passed review blocking, policy/run mismatch blocking, failed validation evidence recording, and passed validation evidence recording without delivery.

The implementation keeps manual review intact while reducing the operator work needed after review passes. The next safe slices are:

- TASK-DEVO-191: optional queue-worker-loop integration that can call this command at the validation gate when explicitly confirmed
- TASK-DEVO-192: deterministic auto-review helper for narrow policy-scoped changes
- TASK-DEVO-193: Codex worker auto-run and auto-ingest hardening
- TASK-DEVO-194: bounded safe queue/policy approval ergonomics
- TASK-DEVO-195: supervised auto-run-approved sequential loop

## Verdict

TASK-DEVO-190 is a small but meaningful operator-efficiency step. It automates validation evidence recording only after prior gates are satisfied, while preserving trusted-runner-only delivery and human review boundaries.
