# Token Usage

This document explains when AI tokens are used while working with Devo.

## What Does Not Use AI Tokens

Devo CLI commands are local deterministic Python commands. They do not consume AI tokens by themselves.

These command areas are local and deterministic:

- project registration and scanning
- context status and context import
- run creation and workflow status/next/batch
- importing agent output
- validation registry, validation history, and validation dry-runs
- Git status, delivery-check, and delivery-report
- project/run/handoff reports
- context refresh/update artifacts

Devo agent prompts are just text until they are pasted into an AI tool. Importing an agent output file into Devo does not consume AI tokens.

## What Uses AI Tokens

Tokens are consumed by ChatGPT, Codex, Claude, Cursor, or similar tools when they read, reason, write, summarize, generate prompts, generate code, or review artifacts.

For example:

- Asking ChatGPT to plan a run uses tokens.
- Asking Codex to edit files or run through a task uses tokens.
- Pasting a Devo agent prompt into an AI tool uses tokens in that tool.
- Asking an AI tool to review Devo artifacts uses tokens.

## Future API Integration

Direct future OpenAI/API integration would consume API credits only if that feature is implemented later and a command actually calls the API. The current Devo CLI does not do this.

## Best Low-Token Workflow

1. Use Devo report/handoff commands to get state.
2. Ask ChatGPT for one compact Codex prompt.
3. Let Codex do one bounded task.
4. Use Devo reports instead of re-explaining context manually.
5. Commit and push the source/docs changes.
6. Refresh context and write a handoff report.

This keeps durable state in files, keeps prompts smaller, and reduces repeated explanation.
