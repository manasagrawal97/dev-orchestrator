# DevOrchestrator

DevOrchestrator is an initial Python CLI for registering local software projects and producing safe, bounded project scan summaries.

This version intentionally does not include agents, AI API integration, or a web UI.

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

## Development

Run tests:

```powershell
pytest
```
