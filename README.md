# DevOrchestrator

DevOrchestrator is an initial Python CLI for registering local software projects and producing safe, bounded project scan summaries.

This version intentionally does not include autonomous agents, AI API integration, or a web UI.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Install

From the repository root:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Usage

Show CLI help:

```powershell
devo --help
```

Register a project:

```powershell
devo project add --name MyProject --path E:\path\to\project
```

List registered projects:

```powershell
devo project list
```

Scan a registered project:

```powershell
devo project scan MyProject
```

List available agent definitions:

```powershell
devo agent list
```

Show an agent definition:

```powershell
devo agent show ProjectContextDiscoveryAgent
```

Generate a ready-to-paste Project Context Discovery prompt:

```powershell
devo agent prompt ProjectContextDiscoveryAgent --project MyProject
```

Import Project Context Discovery output:

```powershell
devo agent import-output ProjectContextDiscoveryAgent --project MyProject --file E:\path\to\discovery-output.md
```

Generate a ready-to-paste Project Context Reviewer prompt:

```powershell
devo agent prompt ProjectContextReviewerAgent --project MyProject
```

Import Project Context Reviewer output:

```powershell
devo agent import-output ProjectContextReviewerAgent --project MyProject --file E:\path\to\review-output.md
```

Show context lifecycle status:

```powershell
devo project context-status MyProject
```

Approve reviewed project context:

```powershell
devo project approve-context MyProject
```

Registered projects are stored under:

```text
workspace/projects/<projectName>/project.json
```

Scan results are stored under:

```text
workspace/projects/<projectName>/scan-result.json
```

The registered path must exist and must be a directory. DevOrchestrator records whether the directory looks like a software project by checking for `.git`, `.sln`, `.csproj`, `package.json`, `pyproject.toml`, or `README.md`.

The scanner walks the registered project in read-only mode and records bounded metadata only: paths, categories, counts, and safe Git summary information when available. It skips generated folders, caches, virtual environments, secret-like files, large files, and common media/binary files.

## Agent Concept

Agents are prompt-only role definitions in this version. Each agent is a YAML contract that describes its purpose, allowed inputs, expected outputs, workflow rules, approval requirements, and next state. DevOrchestrator can list these definitions, show their details, and generate a bounded ProjectContextDiscoveryAgent prompt from `scan-result.json`.

No AI model is called yet. No autonomous agent workflow, Codex integration, code modification, or web UI is implemented.

## Context Lifecycle

Project context moves through a manual approval lifecycle:

```text
REGISTERED -> SCANNED -> CONTEXT_DRAFTED -> CONTEXT_REVIEWED -> CONTEXT_APPROVED
```

After scanning a registered project, generate a ProjectContextDiscoveryAgent prompt and paste it into your AI tool of choice. Import the resulting Markdown with `devo agent import-output ProjectContextDiscoveryAgent --project MyProject --file <file>`. This stores the draft under `workspace/projects/<projectName>/context/drafts/` and records lifecycle metadata in `context/context-state.json`.

Discovery imports must include all required sections in order: `project-profile.md`, `architecture-map.md`, `module-map.md`, `data-model-summary.md`, `validation-profile.md`, `risk-profile.md`, and `unknowns.md`. DevOrchestrator refuses incomplete or truncated discovery drafts before generating reviewer prompts.

Next, generate the ProjectContextReviewerAgent prompt. It uses `project.json`, the bounded `scan-result.json` summary, and the imported discovery draft. Import the reviewer output with `devo agent import-output ProjectContextReviewerAgent --project MyProject --file <file>`. Once both discovery and review artifacts exist, approve the context with `devo project approve-context MyProject`.

Approval creates `workspace/projects/<projectName>/approvals/context-approval.json` and promotes the reviewed artifacts into `workspace/projects/<projectName>/context/approved/`. DevOrchestrator does not modify the scanned project.

## Development

Run tests:

```powershell
pytest
```
