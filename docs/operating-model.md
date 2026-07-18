# DevOrchestrator Operating Model

DevOrchestrator is the persistent control plane for local AI-assisted development. It keeps state and decisions durable, while humans and tools continue to perform the work explicitly.

## ChatGPT Role

ChatGPT helps with:

- planning
- architecture
- next-task decisions
- Codex prompt generation
- review
- risk reasoning
- explaining tradeoffs
- keeping the roadmap coherent

ChatGPT should not be treated as the durable source of truth. Important state, roadmap decisions, deferred scope, and operating rules should be persisted in GitHub docs and Devo workspace artifacts.

## Codex Role

Codex handles:

- implementation
- tests
- local file edits
- local commits
- pushes when allowed
- generated reports
- evidence collection

Codex must respect the repository, filesystem, OS, GitHub, and OpenAI approval layers. Codex should not bypass approval policy, force-push, expose secrets, or modify target projects outside the current approved scope.

## Devo Role

DevOrchestrator handles persistent state and workflow control:

- registered project metadata
- project context lifecycle
- run lifecycle
- task selection
- task ledgers and closure records
- policy gates
- approval ledger
- validation command registry
- recovery and backup state
- environment snapshots

Devo records what should happen and what happened. It should not pretend that work, validation, review, delivery, or approval occurred unless an artifact records it.

## User Role

The user remains the final authority for:

- final approval
- deciding when to proceed with risky work
- manual push when Codex approval policy blocks a push
- running recovery scripts when needed
- restoring local secrets or machine-specific configuration
- choosing whether deferred scope should be promoted into active scope

## Important Safety Notes

- The Devo approval ledger does not bypass Codex/OpenAI/OS/GitHub security policy.
- A Devo approval record is an audit and workflow artifact only.
- Source code is protected by GitHub.
- Devo context is protected by Google Drive workspace backups.
- The active workspace stays local at `E:\DevOrchestrator\workspace`.
- Google Drive is backup storage, not the active workspace.

## Operating Principles

- Deterministic control plane first.
- AI/model integration later.
- No target project modification without explicit task scope.
- No secrets in docs, prompts, reports, or backups.
- Prefer small safe steps with evidence.
- Keep generated workspace state out of Git.
- Commit project direction and recovery instructions when they become important.