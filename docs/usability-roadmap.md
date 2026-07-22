# Usability Roadmap

## Current Usability Problem

Devo has many of the backend/control features it needs, but the user experience is still too manual.

The pain points are:

- too much ChatGPT/Codex back-and-forth
- too many approval gates for small work
- too much repeated prompt text
- too much output and reporting
- manual agent output imports
- first-class work packages exist, but they are still MVP CLI flows
- no saved working modes
- no dashboard UI
- no direct model/agent adapters

This makes Devo safe but not yet smooth.

## Target Improvements

### Work Packages - MVP Added

A work package is one approved batch of related work.

It is limited by scope, risk, and validation method, not by file count.

A work package can contain:

- 3 to 5 related tasks, issues, bugs, or requirements
- one complete same-pattern cleanup group
- one feature or requirement that touches multiple files

Examples:

- all direct MudBlazor `Title` to `title` warning fixes
- one UI maintenance batch across related screens
- one docs-only project context update
- one small feature with source edit plus build validation

The package should include:

- goal
- allowed files or areas
- exact allowed patterns when known
- exclusions
- validation command
- stop conditions
- delivery expectations

The MVP writes `work-package.json`, `work-package.md`, and `operator-prompt.md` under the run workspace artifacts folder.

### Saved Lanes - MVP Added

A lane is a saved working mode.

Example: `low-risk-ui-maintenance`

The lane would store rules once:

- allowed: existing Razor UI components
- allowed: text/help-state/UI polish
- forbidden: DB, migrations, appsettings, secrets, scripts, backups, app run, external APIs
- validation: `git diff --check`, focused diff, delivery-check, registered build
- delivery: commit and push after validation passes

Then the user can say, "Use the low-risk UI maintenance lane," instead of repeating all rules.

The first built-in lane is `low-risk-ui-maintenance`.

### Approval Bundles - MVP Added

An approval bundle lets one user approval cover a scoped group of actions:

- source edit within the work package
- build validation for the registered command
- optionally Git delivery after validation passes

Child approvals still exist in Devo's records. A bundle is not a safety bypass. It is a better user interface for approving related steps at once.

If the scope changes, the bundle should stop matching.

### Operator Prompts

An operator prompt is a compact Codex-ready prompt generated from Devo state.

It should include:

- project
- run id
- task id
- approved scope
- allowed files
- forbidden areas
- validation commands
- stop conditions
- final report requirements

This reduces repeated chat instructions.

### Short Final Reports

Final reports should be brief by default:

- what changed
- validation result
- commit hash
- push result
- final status
- next recommended step

Detailed reports should remain available as Devo artifacts, not pasted into every chat response.

### One-Command Style Workflow

The current MVP command group is:

```powershell
devo work start --project PersonalOS --lane low-risk-ui-maintenance --goal "Improve operational UI guidance"
devo work import-scope --project PersonalOS --run <runId> --file <scopeMarkdownFile>
devo work request-approval-bundle --project PersonalOS --run <runId> --task T001
devo approval bundle-approve --project PersonalOS --run <runId> --bundle <bundleId> --by Manas
```

Devo should guide the user through the package rather than requiring them to remember every lower-level command.

### Dashboard Or UI

A future dashboard should show:

- registered projects
- active runs
- pending approvals
- validation history
- Git delivery readiness
- latest handoff
- next recommended action

The CLI should stay complete, but a UI would make Devo easier to operate.

### Direct Model And Agent Adapters

Later, Devo may run agents directly through model adapters.

That should come after:

- work packages
- lanes
- approval bundles
- operator prompts
- reliable validation and recovery

Direct agent execution should use the same policy, approval, validation, and evidence model. It should not be a bypass around it.

## Near-Term Priority

The best next usability improvements are:

1. Expand work-package lanes for docs-only, validation-only, and recovery work.
2. Make operator prompts and final report expectations tighter.
3. Add global status/dashboard command.
4. Add interrupted-work recovery/resume command.
5. Add direct model adapters later.
