# DevOrchestrator Deferred Scope

This document captures intentionally deferred scope. Deferred does not mean rejected; it means not needed before Devo proves itself on real PersonalOS work.

## Deferred Or Not Yet Implemented

- UI/dashboard
- database backend instead of file workspace
- n8n notifications or automation
- direct OpenAI/API integration
- multi-agent worker adapters for Codex/Claude/Cursor/OpenHands
- mobile-first control interface
- parallel multi-project execution
- Google Drive API integration
- backup encryption
- advanced approval UI/signatures
- automatic external git push bypass
- full scheduler/orchestrator service
- actual PersonalOS feature implementation
- AI Content Studio continuation
- full autonomous implementation loop

## Why Deferred

- Avoid overengineering before Devo is proven on real PersonalOS work.
- Preserve safety while the workflow, policy, approval, validation, and delivery model hardens.
- Avoid API cost and secrets complexity until the deterministic control plane is useful without AI integration.
- Keep Devo as a deterministic control plane first.
- Prefer auditable local files, explicit approvals, and bounded command execution before adding services or agents.

## Revisit Criteria

Deferred scope can be reconsidered after:

- TASK-023 safe validation runner is working.
- TASK-024 Git delivery workflow is working.
- TASK-025 context update workflow is working.
- DevOrchestrator completes one dogfood run on itself.
- PersonalOS completes at least one safe real task through Devo.