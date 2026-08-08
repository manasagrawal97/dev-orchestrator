# TASK-DEVO-101 Real Codex Supervised Dry-Run Retry Report

Source/freshness: TASK-DEVO-101, after TASK-DEVO-100 added `devo worker codex doctor`, WindowsApps launch blocking, and launch-failure handling.

## Summary

TASK-DEVO-101 attempted to prepare a retry of the first real Codex supervised dry-run using an explicit non-WindowsApps executable path or wrapper.

The retry did not proceed to planning, worker preparation, or real Codex execution because no safe explicit non-WindowsApps Codex executable or wrapper was discoverable. Devo's new doctor command correctly identified the currently detected Codex path as a WindowsApps app execution alias and blocked it for guarded execution.

No real Codex CLI process was launched. No worker run, queue item, report, review, validation, commit, push, backup, restore, scheduler action, PersonalOS command, or target-project mutation happened as part of this retry attempt.

## Approved Safe Worker Task

The intended worker task remained:

```text
Inspect README.md, docs/current-state.md, and docs/runbooks/real-codex-supervised-dry-run.md. Report whether the supervised worker instructions are understandable. Do not modify files. Do not run tests. Do not commit. Do not push. Final report only.
```

Because no safe explicit launcher path was found, this task was not handed to real Codex.

## Initial Repo State

From `E:\DevOrchestrator`:

```powershell
git status
```

Result:

- Branch: `main`
- Upstream: `origin/main`
- Working tree: clean
- No workspace artifacts staged

Git also printed the recurring local warning:

```text
warning: unable to access 'C:\Users\manas/.config/git/ignore': Permission denied
```

That warning did not indicate a repository change.

## Codex Doctor Result

Command:

```powershell
.\.venv\Scripts\devo worker codex doctor --project DevOrchestrator
```

Result summary:

- Project: `DevOrchestrator`
- Executable source: `path_detection`
- Detected executable path: `C:\Program Files\WindowsApps\OpenAI.Codex_26.803.5235.0_x64__2p2nqsd0c76g0\app\resources\codex.exe`
- Exists: `True`
- WindowsApps alias: `True`
- Launch risk: `blocked`
- Recommended next action: use `--codex-path` with a non-WindowsApps real executable or wrapper path

Doctor exited nonzero because the selected PATH candidate is blocked.

This is the intended TASK-DEVO-100 behavior.

## Explicit Path Search

The operator searched for a launchable Codex path outside WindowsApps using read-only inspection commands:

```powershell
Get-Command codex -All | Select-Object CommandType,Source,Definition,Path | Format-List
where.exe codex
Get-Command npm,npx,node,pnpm,bun -ErrorAction SilentlyContinue | Select-Object Name,CommandType,Source,Definition | Format-List
Get-ChildItem -Path "$env:APPDATA\npm" -Filter "codex*" -ErrorAction SilentlyContinue
Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\WindowsApps" -Filter "codex*" -ErrorAction SilentlyContinue
Get-ChildItem -Path "$env:LOCALAPPDATA\Programs","$env:ProgramFiles","${env:ProgramFiles(x86)}" -Recurse -Filter "codex*.exe" -ErrorAction SilentlyContinue
Get-ChildItem -Path "$env:USERPROFILE\.local\bin","$env:USERPROFILE\bin","$env:USERPROFILE\.codex\bin","$env:USERPROFILE\.cargo\bin","$env:USERPROFILE\AppData\Local\Programs","$env:USERPROFILE\AppData\Local\Microsoft\WinGet\Packages" -Filter "codex*" -Recurse -ErrorAction SilentlyContinue
Get-AppxPackage *Codex* | Select-Object Name,PackageFullName,InstallLocation | Format-List
```

Findings:

- `Get-Command codex -All` found only WindowsApps package paths:
  - `C:\Program Files\WindowsApps\OpenAI.Codex_26.803.5235.0_x64__2p2nqsd0c76g0\app\resources\codex.exe`
  - `C:\Program Files\WindowsApps\OpenAI.Codex_26.803.5235.0_x64__2p2nqsd0c76g0\app\resources\codex`
- `where.exe codex` found the same WindowsApps package paths.
- No `codex*` npm/global shim was found under `%APPDATA%\npm`.
- No `codex*.exe` was found in the common user-local or Program Files search locations.
- No useful Codex AppX package metadata was returned by `Get-AppxPackage *Codex*`.
- Node/npm exist, but no installed Codex npm shim was found.

No wrapper was created because there was no confirmed safe real executable target outside WindowsApps to wrap, and the task explicitly said not to use the WindowsApps alias.

## Commands Not Run

Because no safe explicit launcher was found, these steps were intentionally not run:

- planning brief/blueprint/backlog creation
- batch suggestion/approval
- queue creation/start
- worker preparation
- run-plan creation for a real worker
- `devo worker codex execute-preview`
- `devo worker codex execute --confirm-execute`
- report import/review
- queue completion

This avoided creating fresh runtime artifacts for a run that could not safely launch.

## Real Codex Execution Result

Real Codex CLI execution was not attempted in TASK-DEVO-101.

Reason:

- The only discoverable Codex executable remained the blocked WindowsApps app execution alias.
- No explicit non-WindowsApps executable path or wrapper was available.
- Continuing would have violated the task's "Do not use the WindowsApps alias" and "execute only if preview is safe" rules.

## Worker And Queue State Transitions

No new worker or queue state transitions occurred.

TASK-DEVO-099 artifacts remain the latest real-launch-attempt evidence:

- queue `Q003`
- item `QI001`
- handoff `H003`
- worker run `WR002`
- run plan `RP003`
- report/review marked failed/rejected after the WindowsApps launch failure

TASK-DEVO-101 did not create replacement queue/worker artifacts.

## Git Status And File Changes

Before the operational retry checks:

- DevOrchestrator was clean.

After the blocked retry investigation:

- No source files were modified by a worker.
- The only intended repository changes are this documentation report and small related docs updates.
- No workspace artifacts should be committed.

## Issues Found

1. The WindowsApps alias is correctly blocked now, but there is still no easy operator path to a launchable real Codex wrapper.
2. Devo can diagnose the problem, but it does not yet help create or validate a safe wrapper.
3. The real supervised dry-run remains blocked until a non-WindowsApps Codex launcher exists.

## Safety Gaps

The main remaining safety gap is not a source-execution issue; it is launcher ergonomics:

- An operator needs a documented, local, non-committed wrapper strategy.
- Devo should be able to create a wrapper template or store a local project setting pointing at an approved wrapper path.
- Devo should still never use `shell=True`.
- Devo should still refuse WindowsApps aliases for direct guarded execution.

## Recommendation

Recommended TASK-DEVO-102: add explicit Codex wrapper/launcher support before retrying real supervised execution again.

Suggested scope:

- Add a safe `devo worker codex wrapper-template --path <outputPath>` command, or equivalent documented helper.
- Keep generated wrappers outside committed source, for example under an ignored local workspace temp/operator path.
- Ensure the wrapper contains no secrets.
- Document how the operator should edit/test the wrapper manually.
- Allow `devo worker codex doctor --codex-path <wrapper>` to confirm the wrapper path is non-WindowsApps and launchable by path shape only, without running Codex.
- Retry the real dry-run only after a safe explicit wrapper exists.

Delivery/commit automation should remain deferred until a real Codex dry-run actually launches, produces a final report, and reaches `waiting_review` with human-reviewed evidence.
