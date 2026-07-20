# Devo Future Improvements

This plan captures likely next improvements so they survive chat or task context loss. It is a planning document only; it does not approve work or change the current safety model.

## Immediate And Near-Term Tasks

### TASK-031: Resume PersonalOS Through Devo

- Purpose: Use Devo to manage one safe current-state documentation task in PersonalOS.
- Why it matters: Proves Devo on the original target project without jumping straight into risky implementation.
- Rough scope: Generate or refresh project reports, select a low-risk docs task, record evidence, validate safely, and use Git delivery checks.
- Priority: blocker for deeper PersonalOS work.

### TASK-030B: Register DevOrchestrator Validation Commands

- Purpose: Add DevOrchestrator's normal validation commands to its Devo validation registry.
- Why it matters: Future runs should be able to reference registered validation evidence instead of only manually reported pytest output.
- Rough scope: Suggest/write validation commands for focused pytest, full pytest, and possibly py_compile with appropriate risk metadata.
- Priority: important.

### TASK-030C: Reduce Policy And Secret-Signal Noise

- Purpose: Refine deterministic checks that produced noisy dogfood warnings.
- Why it matters: TASK-030 showed useful false positives when safety-boundary wording triggered high-risk policy signals and README documentation triggered secret-signal warnings.
- Rough scope: Improve policy parsing for out-of-scope wording and improve delivery scanning for documented signal names without weakening real secret detection.
- Priority: important.

### TASK-033: Interrupted Work Recovery/Resume Command

- Purpose: Add a command that summarizes interrupted or active work and recommends the safest resume point.
- Why it matters: Crash recovery and context loss are common high-friction moments.
- Rough scope: Inspect current project/run status, Git status, latest reports, open tasks, validation evidence, and workspace warnings; print a bounded resume summary.
- Priority: important.

### TASK-034: Codex Handoff Prompt Generator

- Purpose: Generate a compact Codex-ready prompt from approved context, run state, selected task, policy, validation, and delivery evidence.
- Why it matters: Reduces token use and lowers the chance of missing constraints when handing work to Codex.
- Rough scope: Add a deterministic command that writes a bounded prompt artifact and includes explicit safety/staging rules.
- Priority: important.

### TASK-035: Global Devo Status/Dashboard Command

- Purpose: Show a single CLI dashboard for registered projects, active runs, approvals, validation status, backup freshness, and suggested next actions.
- Why it matters: The user needs quick orientation without opening multiple reports.
- Rough scope: Aggregate project context status, run status, warnings, and recovery pointers in a read-only command.
- Priority: important.

### TASK-036: Run Templates For Common Task Types

- Purpose: Provide reusable run/task shapes for docs-only work, safe bugfixes, validation-only work, recovery work, and larger feature planning.
- Why it matters: Reduces repetitive manual prompt/output structure while keeping Devo deterministic.
- Rough scope: Add template docs or commands that seed goals, task decomposition guidance, validation expectations, and safety boundaries.
- Priority: nice-to-have.

### TASK-037: Approval UX Improvements

- Purpose: Make approval requests easier to inspect, approve, reject, and reconcile.
- Why it matters: Dogfood showed approvals can be correct but still a bit clunky when policy is noisy.
- Rough scope: Better approval summaries, clearer pending approval commands, optional grouping by task/action, and improved explanation of matched risk signals.
- Priority: nice-to-have.

## Deferred Larger Ideas

- UI/dashboard: A visual control surface for projects, runs, approvals, validation, delivery, and recovery.
- n8n notifications: Optional notifications for blocked runs, pending approvals, completed backups, or stale context.
- Direct OpenAI/API integration: Devo could call models directly in the future, but only after file-based workflows stay reliable.
- Multi-agent adapters: Codex, Claude, Cursor, OpenHands, and Roo adapters could consume Devo prompts and return structured artifacts.
- Mobile control interface: Lightweight review/approval/status flows from a phone.
- Database backend: Replace or complement file-backed workspace state when concurrency, query, or scale needs justify it.
- Parallel project execution: Coordinate multiple active projects or runs while preserving safety gates.
- Google Drive API integration: Manage backups through API calls instead of relying only on Drive Desktop.
- Backup encryption: Protect workspace backups at rest with explicit key handling.
- Advanced approvals: Expiry, scopes, signatures, delegated reviewers, and stronger audit trails.
- Scheduler/orchestrator service: A long-running service for monitoring, scheduled work, and integrations.
