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

For the plain-language product model, read:

- [Devo vision](devo-vision.md)
- [Current capabilities](current-capabilities.md)
- [Agent workflow](agent-workflow.md)
- [Usability roadmap](usability-roadmap.md)
- [PersonalOS operating model](personal-os-operating-model.md)

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

## Practical PersonalOS Flow

For current PersonalOS maintenance, use the simpler practical flow from [PersonalOS operating model](personal-os-operating-model.md):

1. user gives a goal
2. Codex/Devo creates a work package in the right lane
3. Codex imports exact scope into the work package
4. user approves the approval bundle when the scope is acceptable
5. Codex implements within scope
6. Codex validates with the registered command, commits, pushes, marks the work package complete, and gives a short final summary

The older two-stop flow, separate source approval followed by separate build approval, remains useful when a bundle is not available or the scope/risk changes.

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

## Work Packages

For small bounded batches, use the work-package flow instead of hand-assembling a run and approvals:

```powershell
devo work lanes
devo work start --project <name> --lane low-risk-ui-maintenance --goal "<goal>"
devo work import-scope --project <name> --run <runId> --file <scopeMarkdownFile>
devo work status --project <name> --run <runId>
devo work next --project <name> --run <runId>
devo work prompt --project <name> --run <runId> --phase implement
devo work request-approval-bundle --project <name> --run <runId> --task T001
devo approval bundle-status --project <name> --run <runId> --bundle <bundleId>
devo approval bundle-approve --project <name> --run <runId> --bundle <bundleId> --by Manas --note "Approved scope"
devo work complete --project <name> --run <runId> --commit <commitHash> --message "<summary>"
devo work list --project <name> --limit 10
devo work history --project <name> --limit 10
devo project activity --project <name> --limit 10
```

The scope Markdown must include selected items, exact files, allowed changes, forbidden changes, validation command, and delivery plan. Work-package artifacts stay under `workspace/`; target project files are changed only later by Codex after approval.

`devo work next` reads the package state and shows the next action, required command, stop conditions, and whether user approval is needed. `devo work prompt --phase <phase>` writes a phase-specific Codex operator prompt under the work-package artifacts folder. Supported phases are `scope`, `implement`, `validate`, `deliver`, and `complete`.

The final low-risk package flow is:

```text
work start -> import scope -> request approval bundle -> bundle approve -> prompt/implement -> prompt/validate -> prompt/deliver -> work complete -> final report
```

`devo work complete` records the delivered commit, delivery summary, latest validation run id/status when available, approval bundle status, final Git delivery status when available, and delivered timestamp. `devo work status` shows those fields with a compact next action and suggested next command so the final package state is obvious after a successful push.

Use `devo work list` to see recent open and delivered work packages with approval, validation, commit, and next-action fields. Use `devo work history` when you mainly want delivered work and commit summaries. Use `devo project activity` for a compact project-level view across recent runs, delivered packages, validation runs, context updates, reports, current Git state, and the suggested next action.

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
