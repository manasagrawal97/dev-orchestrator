# PersonalOS Operating Model

## Purpose

This document describes how to use Devo for PersonalOS maintenance and development.

PersonalOS is a real target project with user data, database access, secrets, appsettings, migrations, backups, external integrations, and generated files. Devo should keep work scoped and recoverable.

## One-Time Project Setup Expectations

Before normal work:

1. PersonalOS is registered as a Devo project.
2. Safe scan exists.
3. Project context is approved.
4. Validation commands are registered.
5. High-risk validation commands are disabled by default.
6. Git delivery-check can inspect the repo.
7. Reports and handoffs can recover state.

This setup is already in place.

## Normal Low-Risk Batch Flow

Current bundled flow:

1. User gives a goal.
2. Codex creates a Devo work package in the `low-risk-ui-maintenance` lane.
3. Codex imports exact scope into the work package.
4. User approves the approval bundle when the exact scope is acceptable.
5. Codex implements inside scope.
6. Codex runs safe pre-build checks.
7. Codex runs the registered Devo build validation when the bundle's child validation approval matches.
8. If validation passes, Codex reports, commits, and pushes.
9. User receives a short final summary.

Fallback practical flow when a bundle is not appropriate:

1. Codex requests source-edit approval.
2. User approves source edit.
3. Codex implements inside scope.
4. Codex requests build approval.
5. User approves build.
6. Codex validates, reports, commits, pushes, and summarizes.

## Risky Work Flow

Risky work needs a fuller plan and narrower approvals.

Examples:

- DB changes
- migrations
- appsettings or config changes
- auth or security changes
- scripts
- backups
- generated files or user data
- app run
- external API calls
- broad refactors
- behavior changes in finance, investments, broker sync, document intake, Ask AI, or ownership

For this work, Devo should produce requirements, a plan, a plan review, task decomposition, approval requests, validation requirements, and stop conditions before Codex changes files.

## User Inputs Normally Expected

For low-risk batches:

- goal
- approval of the proposed approval bundle

For risky work:

- goal
- design decisions when needed
- source approval
- validation approval
- possible DB/migration/script/app-run approval only if truly needed

## How Many Approvals Should Be Normal

Normal current target:

- one bundled approval for a scoped low-risk batch
- final summary

Fallback when scope or tool support requires it:

- one source-edit approval
- one build approval

More approvals are appropriate only when scope expands or risk changes.

## What Codex Should Stop For

Codex should stop when:

- Git is dirty before start and the dirtiness is not expected
- the work needs DB or migrations
- the work needs appsettings, secrets, local settings, or `.env`
- the work needs scripts, backups, or scheduler changes
- the work touches generated files or user data
- the work requires running the app
- the work calls external APIs
- auth/security/ownership risk appears
- build/test/validation fails
- a source file outside the approved scope is needed
- the approved risk category changes
- the fix needs a behavior refactor instead of the approved mechanical/small change

## What Codex Should Not Stop For After Approval

After approval, Codex should not stop just because:

- more than five files are touched inside the approved work package
- multiple same-pattern warnings exist
- a batch has 3 to 5 related small tasks
- one feature touches multiple files within the approved scope
- validation produces already-known unrelated warnings
- Devo reports are verbose but non-blocking

Codex should continue through implementation, approved validation, reporting, commit, push, and final summary unless a hard stop condition appears.

## Normal Low-Risk Batch Example

Goal: "Improve PersonalOS operational guidance UI."

Work package:

- backup heartbeat guidance in admin diagnostics
- non-secret API source status text
- valuation update prompt using existing UI data
- Finance Accounts empty/help state

Rules:

- UI-only
- no DB
- no migrations
- no appsettings or secrets
- no scripts or backups
- no app run
- no external APIs
- registered build validation only after approval

Normal approval bundle flow:

1. one package approval
2. final summary

Fallback approval flow:

1. source approval
2. build approval
3. final summary
