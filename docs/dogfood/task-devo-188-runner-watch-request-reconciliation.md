# TASK-DEVO-188: Runner-watch request reconciliation dogfood

## Summary

TASK-DEVO-188 fixed a delivery state-linking bug where a trusted `runner-watch`
delivery could successfully commit and push a selected runner request, but the
runner request and queue-worker state could still appear incomplete.

The bug was discovered while delivering TASK-DEVO-187 / T018.

## Original problem

QWR-0016 created delivery request REQ-0077.

The scheduled trusted runner-watch selected REQ-0077 and completed delivery
DEL-0158 with commit `5404b84b001d2b49afc5a08cef1c7eb507533d29`.

The repository became clean and the commit was pushed, but REQ-0077 still showed
`requested`.

A later manual `runner-run` for REQ-0077 then blocked because the expected
changed files were no longer present in the working tree. That was expected
because the files had already been committed by runner-watch.

The result was confusing:

- the code was already delivered
- the repo was clean
- the commit was pushed
- but QWR-0016 stayed stuck in `delivery_requested`

## Fix delivered

The core fix was delivered in commit `fde2100`.

The implementation added reconciliation so completed runner-watch evidence can
be used as trusted delivery evidence for the selected runner request.

A runner-watch completion is trusted only when it has:

- completed watch status
- selected runner request id
- delivery id
- commit hash
- pushed=true

The delivery resolver now prefers trusted completed runner-watch evidence when a
later per-request runner-run artifact is missing, stale, or blocked.

The affected views and flow now use the reconciled delivery evidence:

- delivery latest
- runner latest
- runner show
- runner list
- codex worker batch summary
- queue-worker delivery completion detection

## Regression coverage

Regression tests cover the stale request case:

- runner request remains `requested`
- completed runner-watch exists with commit and pushed=true
- later manual runner-run is blocked
- latest/show output still recognizes the watched delivery as completed
- queue-worker-loop can complete the linked queue-worker run from trusted
  runner-watch evidence

## Dogfood result

REQ-0078 delivered the reconciliation fix successfully.

QWR-0017 completed after trusted delivery, and the batch summary showed the
delivered commit and pushed status correctly.

T024, T025, and T026 were tracking-completed because the reviewed, validated,
and pushed T023 reconciliation commit already included the related latest/show,
queue-worker completion, and regression-test work.

## Safety notes

The fix does not create fake delivery success.

It does not mark delivery completed without commit hash and pushed=true evidence.

It does not bypass worker result evidence, review evidence, validation evidence,
or trusted runner delivery.

It only reconciles existing trusted runner-watch delivery evidence with the
runner request and queue-worker state.
