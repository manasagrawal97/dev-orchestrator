# Codex Launcher Setup Runbook

Source/freshness: TASK-DEVO-103, after TASK-DEVO-102 added launcher diagnostics, `--codex-wrapper`, wrapper templates, WSL preview, and WindowsApps blocking.

## Purpose

This runbook helps the operator get a safe launcher for Devo supervised Codex execution.

It exists because WindowsApps `codex.exe` app execution aliases can look like real executables, pass simple path checks, and still fail under Python `subprocess`/Windows `CreateProcess`. Devo blocks those aliases for guarded execution.

Use this runbook before retrying a real supervised Codex worker run.

## Supported Launcher Options

Devo supports these launcher strategies:

- Normal PATH detection, when `devo worker codex doctor` resolves a real non-WindowsApps Codex CLI.
- Explicit executable path with `--codex-path <path>`.
- Explicit local wrapper path with `--codex-wrapper <path>`.
- WSL launcher route with `--codex-wsl <distributionName>`, currently for preview/planning only unless a later task enables guarded WSL execution.

The safest next retry should use either a known real executable path or a reviewed local wrapper path.

## WindowsApps Warning

Do not use a WindowsApps Codex alias as the launcher.

Blocked examples include paths shaped like:

```text
C:\Program Files\WindowsApps\...\codex.exe
C:\Program Files\WindowsApps\...\codex
```

Do not use `shell=True` as a workaround. Devo intentionally constructs explicit subprocess argument lists so command shape remains auditable.

Do not pass the WindowsApps alias to `--codex-path`.

## npm CLI Setup Checklist

Devo does not install packages automatically. The operator must do installation and account/auth setup outside Devo.

Checklist:

1. Manually verify Node/npm availability outside Devo.
2. Manually install or locate the Codex CLI using the supported Codex installation path for the operator's environment.
3. Confirm the resolved Codex command path is outside `WindowsApps`.
4. Run:

```powershell
devo worker codex doctor --project DevOrchestrator
```

5. If PATH is still ambiguous, pass the known executable explicitly:

```powershell
devo worker codex doctor --project DevOrchestrator --codex-path <realCodexPath>
```

Readiness requires no launch blockers.

## WSL Setup Checklist

Use this route only if the operator normally runs Codex successfully inside WSL.

Checklist:

1. Manually verify the WSL distro exists.
2. Manually install and run Codex inside that WSL distro first.
3. Record the distro name.
4. Understand the working-directory mapping from the Windows project path to the WSL path.
5. Confirm the command path that works inside WSL.
6. Use Devo's WSL flag only for preview/planning in this version:

```powershell
devo worker codex doctor --project DevOrchestrator --codex-wsl <distributionName>
devo worker codex preflight --project DevOrchestrator --run <workerRunId> --codex-wsl <distributionName>
devo worker codex run-plan --project DevOrchestrator --run <workerRunId> --codex-wsl <distributionName>
```

Guarded WSL execution remains deferred until implemented and fake-tested. Devo would need the distro name, safe command shape, and reliable working-directory mapping before enabling it.

## Wrapper Setup Checklist

Use a wrapper when a real Codex CLI exists, but PATH resolution is unreliable or points at WindowsApps.

1. Create a local wrapper template in an ignored local path:

```powershell
devo worker codex wrapper-template --path E:\DevOrchestrator\workspace\tmp\codex-wrapper.cmd --type cmd
```

2. Edit the wrapper manually.
3. Set `CODEX_REAL_COMMAND` to the known working non-WindowsApps Codex executable.
4. Do not include secrets, tokens, local settings values, or account data.
5. Do not commit the wrapper.
6. Verify Devo can inspect the wrapper without running Codex:

```powershell
devo worker codex doctor --project DevOrchestrator --codex-wrapper E:\DevOrchestrator\workspace\tmp\codex-wrapper.cmd
```

7. If doctor is not available in an older checkout, use preflight/run-plan with the wrapper:

```powershell
devo worker codex preflight --project DevOrchestrator --run <workerRunId> --codex-wrapper <wrapperPath>
devo worker codex run-plan --project DevOrchestrator --run <workerRunId> --codex-wrapper <wrapperPath>
```

The template command does not run Codex. Preflight and run-plan do not run Codex.

## Readiness Criteria

A launcher is ready for the next real supervised retry only when all of these are true:

- The launcher is not a WindowsApps alias.
- The explicit path or wrapper exists and is a file.
- `devo worker codex doctor` shows no launch blockers.
- Preflight passes or has warnings only.
- `execute-preview` shows the expected command, target repo path, prompt path, and launcher.
- The operator understands the stop conditions in `docs/runbooks/real-codex-supervised-dry-run.md`.
- No wrapper contains secrets.
- No wrapper or workspace artifact is staged for commit.

## Next Real Retry Sequence

After readiness is satisfied, follow:

```text
docs/runbooks/real-codex-supervised-dry-run.md
```

The first retry should still be no-op or docs-only, target DevOrchestrator first, and stop before automatic validation, queue completion, commit, push, or delivery automation.

## Troubleshooting

### Only WindowsApps Found

Do not continue to guarded execution. Use a real executable path, create a wrapper, or use manual Codex handoff until a safe launcher exists.

### npm Shim Path Not Found

Verify the CLI installation manually. Devo should not install packages automatically. If a working executable is found later, pass it with `--codex-path` or wrap it with `--codex-wrapper`.

### Wrapper Path Missing

Recreate the wrapper template or correct the path:

```powershell
devo worker codex wrapper-template --path <safeLocalPath> --type cmd
```

### PermissionError

Treat this as a launcher failure. Inspect `devo worker codex execute-log`, run doctor again, and do not complete queue items from a failed launch.

### FileNotFoundError

The executable or wrapper path no longer exists, or the wrapper points at a missing real command. Fix the launcher manually, rerun doctor, then recreate the run plan.

### WSL Path Mapping Confusion

Do not use WSL execution yet. Use WSL only for preview/planning until Devo has a fake-tested WSL execution implementation with clear path mapping.
