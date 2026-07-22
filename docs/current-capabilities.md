# Current Capabilities

## Summary

Devo is a local CLI control plane for AI-assisted development. It does not call AI models and does not implement code by itself. It records project state, workflow state, approvals, validation evidence, Git delivery evidence, reports, and recovery information.

## Project Registration

Devo can register local projects by name and path. Registered project metadata is stored in the Devo `workspace/` folder.

It records whether the path exists, whether it looks like a software project, and basic safe project markers such as README files, solution files, project files, and package files.

## Safe Project Scanning

Devo can scan a registered project in read-only mode. The scanner records bounded metadata such as file paths, categories, counts, dependency markers, and a safe Git summary.

It skips common secret files, local settings, generated folders, caches, dependency folders, virtual environments, binary/media files, and large files.

## Approved Project Context

Devo has a project context lifecycle:

```text
REGISTERED -> SCANNED -> CONTEXT_DRAFTED -> CONTEXT_REVIEWED -> CONTEXT_APPROVED
```

Context is created from bounded scan evidence and manually imported agent output. Devo checks that required sections exist before review and approval.

Approved context gives later runs a stable baseline.

## Agent Prompt Registry

Devo stores agent role definitions and can generate prompts for them.

Current agents are prompt templates and workflow roles, not separate running bots. ChatGPT or Codex acts as the agent and imports the result back into Devo.

## Run Lifecycle

Devo can create a run for one goal. A run stores:

- the goal
- run state
- prompts
- agent outputs
- tasks
- approvals
- validation records
- reports
- handoff artifacts

Runs make multi-step work recoverable.

## Task Lifecycle

Devo supports task decomposition, task ledgers, task status, task disposition, task closure, validation review, code review, and final audit artifacts.

This is useful when a plan changes or one implementation covers more than one task.

## Policy And Risk Checks

Devo classifies work into risk levels and action types. It can distinguish read-only work, docs-only target edits, source edits, build/test validation, scripts, database work, migrations, config changes, Git delivery, and critical/destructive actions.

Policy checks do not replace human judgement. They make risk explicit and repeatable.

## Approval System

Devo can create approval requests, record approvals/rejections, store approval ledgers, and compare later actions against the approved scope.

Approvals are workflow evidence only. They do not grant operating system, GitHub, Codex, OpenAI, shell, or external-service permission.

## Validation Registry

Devo can register known validation commands for a project, including command id, command text, working directory, category, risk, approval requirement, and enabled/disabled state.

This is safer than ad hoc command execution because the command is known before it runs.

## Validation Runner

Devo can run registered validation commands with safety gates:

- disabled commands require explicit opt-in
- high-risk commands require matching approval
- critical commands stay blocked
- command output is captured
- timeouts are enforced
- artifacts are written under the project or run

The runner now recognizes safely scoped `target_repo_build`, `target_repo_test`, and `target_repo_validation` approvals when they match the registered command category and scope. Exact `target_command` approval is still supported for maximum precision.

## Git Delivery Checks

Devo can inspect registered project Git state without staging, committing, or pushing.

It reports branch, upstream, ahead/behind state, clean/dirty state, changed files, forbidden staged paths, secret-like changed-file signals, `git diff --check`, validation evidence, approval evidence, and suggested next action.

## Reports, Handoffs, And Context Updates

Devo can write deterministic project reports, run reports, handoff reports, and context update drafts.

These are the main recovery tools after a crash or context loss. They let ChatGPT, Codex, or the user resume from evidence instead of memory.

## Backup And Recovery

Devo has workspace backup and recovery commands plus wrapper scripts. Backups protect Devo runtime state under `workspace/`, not target project source code.

Source code is protected by GitHub. Devo workspace state is protected by scheduled Google Drive Desktop backup when configured.

## Dogfooding On DevOrchestrator

DevOrchestrator is registered as a Devo project and has been used to manage its own tasks. This has validated the core workflow: context approval, run creation, task planning, policy checks, approvals, validation registry, validation runs, delivery reports, context refresh, and handoff reports.

## Real PersonalOS Usage So Far

Devo has also managed real PersonalOS work with explicit scope and validation:

- added PersonalOS `docs/current-state.md`
- fixed friendly Gemini/Ask AI timeout handling
- validated the PersonalOS build through Devo
- fixed RZ10012 Razor warnings
- fixed direct MUD0002 `Title`/`title` warnings
- fixed remaining non-Title MUD0002 warnings
- documented that remaining CS8669 warnings are generated Razor warnings from `Reconcile_razor.g.cs`

Current PersonalOS milestone:

- Gemini timeout handling fixed
- RZ10012 warnings: 0
- MUD0002 warnings: 0
- current build passes
- remaining warnings: CS8669 generated Razor warnings, documented and ignored for now

## What Devo Cannot Do Smoothly Yet

Devo is still too manual in these areas:

- agent outputs are manually produced and imported
- work packages are not first-class yet
- approval bundles are not implemented yet
- repeated safety text is still common
- reports are useful but sometimes verbose
- there is no dashboard UI
- Devo does not directly run model agents
- Devo does not implement code by itself

These are product/workflow improvements, not reasons to bypass the current safety model.

