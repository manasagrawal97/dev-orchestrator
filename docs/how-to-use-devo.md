# How To Use Devo

Devo is a local control plane for AI-assisted development. It keeps project memory, workflow state, task state, policy decisions, approvals, validation metadata, Git delivery evidence, reports, and recovery notes in one place.

Devo does not implement code by itself. It does not call AI by itself. It does not bypass Codex, OpenAI, GitHub, operating system, or user approval policy.

## Mental Model

- User and ChatGPT decide direction, risk, and the next safe step.
- Codex or another coding agent implements bounded changes.
- Devo records the control plane: project memory, workflow, task state, policy, approval, validation, Git delivery, reports, and recovery.
- Source code is protected by GitHub.
- Devo runtime artifacts live in `workspace/` and should not be committed.
- Devo workspace/context is protected by scheduled Google Drive backup.

## Typical Lifecycle

1. Register the project.
2. Scan the project.
3. Generate and import discovery context.
4. Review and import context review.
5. Approve context.
6. Create a run.
7. Ask workflow for next/status.
8. Generate an agent prompt or perform a manual-assisted step.
9. Record implementation evidence.
10. Run validation or dry-run validation.
11. Review, audit, and close the task.
12. Run Git delivery-check/report.
13. Refresh project context.
14. Write a handoff report.
15. Close the run when all tasks are resolved.

## Project Setup

```powershell
devo project add --name <name> --path <path>
devo project scan <name>
devo project context-status <name>
```

After scanning, generate/import ProjectContextDiscoveryAgent output, generate/import ProjectContextReviewerAgent output, then approve context:

```powershell
devo agent prompt ProjectContextDiscoveryAgent --project <name>
devo agent import-output ProjectContextDiscoveryAgent --project <name> --file <discoveryOutputFile>
devo agent prompt ProjectContextReviewerAgent --project <name>
devo agent import-output ProjectContextReviewerAgent --project <name> --file <reviewOutputFile>
devo project approve-context <name>
```

## Daily Start

```powershell
devo report project --project <name>
devo report handoff --project <name>
devo workflow resume --project <name>  # planned future command, not implemented yet
```

Until `devo workflow resume` exists, use project/handoff reports plus `devo workflow status` for any known active run.

## Run Work

```powershell
devo run create --project <name> --goal "<goal>"
devo workflow status --project <name> --run <runId>
devo workflow next --project <name> --run <runId>
devo workflow batch --project <name> --run <runId>
```

When Devo asks for agent output, generate the prompt, produce the output with ChatGPT/Codex/manual assistance, then import it:

```powershell
devo agent prompt <AgentName> --project <name> --run <runId>
devo agent import-output <AgentName> --project <name> --run <runId> --file <agentOutputFile>
```

Implementation is performed outside Devo by a human or coding agent. Record completion evidence after the work is done:

```powershell
devo implementation report --project <name> --run <runId> --task <taskId> --file <completionReportFile>
```

## Safety

```powershell
devo policy classify --project <name> --run <runId> --task <taskId>
devo approval request --project <name> --run <runId> --task <taskId> --action <actionType>
devo approval approve --project <name> --run <runId> --approval <approvalId> --by Manas
```

A Devo approval is an audit/workflow record. It does not grant shell, GitHub, OS, Codex, OpenAI, or external-service permissions.

## Validation

```powershell
devo validation list --project <name>
devo validation suggest --project <name>
devo validation run --project <name> --id <id> --dry-run
devo validation history --project <name>
```

Registered validation commands are safer than ad hoc commands because Devo records risk, working directory, approval requirements, and execution history.

## Delivery

```powershell
devo git status --project <name>
devo git delivery-check --project <name>
devo git delivery-report --project <name> --run <runId> --message "<message>"
```

Delivery commands inspect Git state and write evidence. They do not stage, commit, push, or bypass GitHub policy.

## Context And Recovery

```powershell
devo project context-refresh --project <name> --run <runId> --write-draft
devo report run --project <name> --run <runId> --write
devo report handoff --project <name> --run <runId> --write
```

Use reports instead of re-explaining the project from memory. They are the preferred recovery trail after crashes, context loss, or a handoff between ChatGPT, Codex, and the user.

## What Not To Commit

Do not stage or commit generated runtime artifacts unless a task explicitly says to do so. In normal development, do not stage:

- `workspace/`
- `.venv/`
- `.env`
- `.pytest_cache/`
- `pt-*` folders
- backup folders
- restore-test folders
- target project files outside the approved task scope
