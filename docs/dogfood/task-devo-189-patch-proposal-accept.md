# TASK-DEVO-189 Patch Proposal Accept Dogfood

## Purpose

TASK-DEVO-189 reduces the manual friction around Codex patch proposals.

When a Codex worker understands a change but cannot write the target files directly, Devo can preserve that work as a patch proposal. TASK-DEVO-189 adds a safe reviewed accept flow so the operator can move from patch proposal evidence to completed worker-result evidence without hand-joining every artifact.

The feature remains deliberately gated. Patch acceptance is not review, validation, delivery, commit, or push.

## Delivered slices

- T028/T029: `patch-proposal-accept` command shell
  - Commit: `6ce605a`
- T030/T031: safe patch accept service
  - Commit: `7b6bd0a`
- T032/T033: focused tests covered by the service commit
- T034/T035: this dogfood documentation

## Before workflow

Before TASK-DEVO-189, Codex could get blocked by write permissions and still provide a useful patch proposal.

The operator then had to manually:

- inspect the patch proposal
- run the patch check
- apply the patch
- inspect the resulting diff
- separately record worker-result evidence
- continue the queue-worker loop

That kept the flow safe, but it required many manual commands and made the operator mentally join patch evidence, apply evidence, worker evidence, and next queue-worker state.

## New workflow

The expected command flow is:

```powershell
devo project patch-proposal-show --project DevOrchestrator --run QWR-XXXX
devo project patch-proposal-check --project DevOrchestrator --run QWR-XXXX --confirm-check
devo project patch-proposal-accept --project DevOrchestrator --run QWR-XXXX --reviewed-by "Manas" --confirm-accept-patch
```

Whitespace-tolerant accept remains explicit:

```powershell
devo project patch-proposal-accept --project DevOrchestrator --run QWR-XXXX --reviewed-by "Manas" --confirm-accept-patch --ignore-whitespace --confirm-ignore-whitespace
```

After accept succeeds, the operator still continues through normal queue-worker gates: review evidence, validation evidence, delivery request, and trusted runner delivery.

## What patch-proposal-accept does

`patch-proposal-accept`:

- loads the queue-worker run
- verifies patch proposal evidence exists
- verifies policy, queue, and task linkage
- verifies a matching successful `patch-proposal-check`
- verifies patch hash and apply mode
- applies through the existing safe patch apply helper
- records completed worker-result evidence only after successful apply
- preserves provenance including original worker status, patch artifact path, patch check id, patch apply id, patch hash, apply mode, and reviewer

## What it deliberately does not do

`patch-proposal-accept` does not:

- record review
- record validation
- run validation
- create a delivery request
- approve delivery
- commit
- push

This keeps patch acceptance separate from the human review, validation, and trusted delivery gates.

## Safety gates

The command keeps these gates:

- `--confirm-accept-patch` is required for confirmed accept
- `--reviewed-by` is required for confirmed accept
- `--ignore-whitespace` requires `--confirm-ignore-whitespace`
- a matching successful patch check is required before accept
- patch hash and apply mode must match the successful check
- existing matching applied patch evidence blocks to avoid double-apply ambiguity

If any gate is uncertain, Devo blocks and tells the operator to inspect before continuing.

## Dogfood evidence

- QWR-0022 / REQ-0083 / commit `6ce605a` delivered the command shell
- QWR-0023 / REQ-0084 / commit `7b6bd0a` delivered the service
- Focused validation passed:
  - `patch_proposal_accept`: 7 passed
  - `patch_proposal`: 34 passed

The dogfood result is a pass. The workflow now removes the separate manual worker-result recording step after a reviewed patch proposal has been safely checked and applied.

## Remaining limitations

- Review and validation are still manual evidence steps.
- Validation is not yet automatically run and recorded by Devo.
- The next painkiller should be validation evidence automation.

