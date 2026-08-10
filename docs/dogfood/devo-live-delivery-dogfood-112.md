# TASK-DEVO-112 Live Delivery Dogfood Note

Source/freshness: TASK-DEVO-112 through TASK-DEVO-115. This note is the tiny docs-only change used for the first live DevOrchestrator delivery self-dogfood.

## Purpose

TASK-DEVO-112 validates Devo's guarded delivery flow on the live DevOrchestrator repository for the first time.

The target change is intentionally docs-only. Final commit and push for this task should be performed through Devo delivery commands, not through normal manual `git commit` or `git push`.

## Final Result

DEL-0001 completed successfully from normal local PowerShell using `.\.venv\Scripts\devo.exe`.

- Delivery id: `DEL-0001`
- Commit: `f0e8c0319c135f72973357776cd7c62d6cc8832b`
- Commit message: `docs: dogfood live delivery flow`
- Push target: `origin/main`
- Push result: succeeded
- Final Git status: clean on `main...origin/main`
- Workspace artifacts: not committed
- Manual Git bypass: not used for DEL-0001

## Recovery Note

The first guarded commit attempts failed before commit creation because the restricted Codex/sandbox context could not create `E:\DevOrchestrator\.git\index.lock` and Git reported permission denied.

TASK-DEVO-113 added delivery report recovery support through `devo delivery report-refresh` and `--reopen`. TASK-DEVO-114 added `devo delivery commit-diagnostics` plus the explicit `--index-lock-probe --confirm-probe` probe.

TASK-DEVO-112D showed that the restricted context could not create `.git/index.lock`, while the later normal PowerShell run as `MS\manas` could create/remove the lock and complete guarded commit/push through Devo.

## Operating Rule

Run live Devo delivery commit/push from normal local PowerShell as the normal Windows user, using the explicit executable prefix:

```powershell
.\.venv\Scripts\devo.exe
```

Do not run live guarded delivery commit/push from restricted Codex/sandbox context unless `devo delivery commit-diagnostics --index-lock-probe --confirm-probe` proves that context can create and remove `.git/index.lock`.

Do not bypass Devo delivery with manual `git add`, `git commit`, or `git push` during delivery dogfood unless the user explicitly approves that exceptional path.

If the `.git/index.lock` permission issue appears again:

1. Run `devo delivery commit-diagnostics --project <project> --report <deliveryId>`.
2. Run the index-lock probe only with `--index-lock-probe --confirm-probe`.
3. Fix the OS/security/context issue.
4. Run `devo delivery report-refresh --project <project> --report <deliveryId> --reopen --note "<reason>"`.
5. Run `devo delivery commit-preview --project <project> --report <deliveryId>`.
6. Run guarded commit/push from normal PowerShell if the preview is safe.

## Safety Boundaries

- Workspace artifacts must not be committed.
- No source code or UI source files should change.
- No PersonalOS files or commands should be touched.
- No real Codex CLI, backup, restore, scheduler, or AI API/model command should run.
- Devo delivery commit/push commands require explicit confirmation flags.

## Evidence

The delivery check, plan, approval, report, diagnostics, guarded commit, and guarded push results are recorded in Devo delivery artifacts under `workspace/projects/DevOrchestrator/delivery/`.
