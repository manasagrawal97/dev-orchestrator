# TASK-DEVO-194: Bounded Execution-Policy Approval Bundle

## Objective

Reduce repeated approval commands for several already-materialized execution policies without creating new work or widening any policy's authority.

## Implemented Slice

The CLI now provides a preview-first workflow:

```powershell
devo project execution-policy-approval-bundle-request --project <project> --policy <POL-1> --policy <POL-2> --max-policies 2
devo project execution-policy-approval-bundle-request --project <project> --policy <POL-1> --policy <POL-2> --max-policies 2 --note "Reviewed materialized policies." --confirm-request
devo project execution-policy-approval-bundle-show --project <project> --bundle <PAB-ID>
devo project execution-policy-approval-bundle-check --project <project> --bundle <PAB-ID>
devo project execution-policy-approval-bundle-approve --project <project> --bundle <PAB-ID> --approver "<name>"
devo project execution-policy-approval-bundle-approve --project <project> --bundle <PAB-ID> --approver "<name>" --note "Approved pinned scopes." --confirm-approve
```

The first request command and the unconfirmed approval command are read-only previews. `--confirm-request` creates one workspace artifact; it does not approve a policy. `--confirm-approve` rechecks the complete bundle before updating the normal approval fields on every referenced child policy.

## Eligibility And Bounds

A request is accepted only when all of these conditions hold:

- two through ten distinct existing policies are named and the count does not exceed `--max-policies`;
- every policy is already `requested` and has exactly low risk;
- every source batch is approved;
- every policy explicitly references an existing queue, allowed tasks, and matching allowed queue items whose status is still `pending`;
- allowed and forbidden file patterns and validation commands are present;
- task and changed-file limits are positive and allowed task count does not exceed `max_tasks`;
- worker review and validation evidence remain required; and
- expiry and auto-push/auto-delivery consistency checks pass.

Medium, high, and critical risk policies require individual approval. Running, waiting-review, paused, blocked, failed, completed, skipped, superseded, or otherwise non-pending queue items are not actionable bundle members. The bundle cannot be used to turn draft policies into requested policies or to invent tasks, queue items, batches, queues, or policies.

## Audit And Drift Protection

The `PAB-*` artifact records the exact policy ids, per-policy task ids and queue-item ids, a SHA-256 fingerprint of each approval-relevant policy scope, the policy-count bound, and aggregate maximum tasks and changed files. JSON and Markdown are written under:

```text
workspace/projects/<project>/planning/execution-policies/approval-bundles/
```

Before approval, Devo reloads every child and repeats eligibility/reference checks. A changed status, expiry, missing artifact, changed task or queue-item reference, changed file/validation/limit/delivery/review setting, fingerprint mismatch, or changed aggregate bound blocks the whole operation before any child is updated.

## Safety Boundary

Approval records a human decision on existing child policies. It does not run Codex or another worker, perform review, run validation, start or complete a queue item, create a delivery request, invoke trusted delivery, stage files, commit, or push. All downstream worker, review, validation, and trusted-delivery gates remain required.

## Focused Verification

Focused tests cover the non-mutating previews, bounded request artifact, pinned task/queue references, normal child-policy approvals, target-repository non-mutation, minimum policy count, and all-or-nothing scope-drift blocking.
