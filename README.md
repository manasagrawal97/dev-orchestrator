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

## Development

Run tests:

```powershell
pytest
```
