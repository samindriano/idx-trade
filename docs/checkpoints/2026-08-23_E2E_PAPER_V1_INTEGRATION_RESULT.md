# IDX-Trade E2E Paper V1 Integration Result

Date: 2026-08-23
Branch: `integration/idx-e2e-baseline-paper-v1`
Source implementation commit before this checkpoint: `c282b42330383795c4459711de8d988a6895bd6d`

## Decision

`CA_SOURCE_LIFECYCLE_READY_E2E_OFFLINE_VALIDATED`

The corporate-action/dividend source and lifecycle layer is ready for the
offline E2E paper orchestrator. The implementation is not a live trading or
outcome-validation approval. A real provider capture was intentionally not
run in this lane; scheduler registration was not changed.

## CA evidence and lifecycle

The accepted offline V1.2 batch evidence is external and immutable:

`D:\\Documents\\Project\\idx-e2e-forward-dividend-acquisition-batch-smoke-20260823-v6`

The accepted POST_EOD journal is:

`dividend_acquisition_v1/journals/2026-08-22_POST_EOD.json`

Journal SHA-256:
`e8ee29fa6f04d3261a6caafd620b18943637912c9693f575dc69e590593c4e53`

The offline verifier passed. The accepted batch contains 11 candidate
dispositions, with 1 current certified-live event, 6 historical-observed, 2
corroborating-only, 2 superseded, and no unresolved live blockers. The journal
has 3 required tickers, 1 current certified event, 1 retained certified-history
event, 0 blockers, and 1 explicit blocker resolution entry.

The corrected live BBCA identity is:

`CASH_DIVIDEND_BBCA_0ba8da55aac01313f2174243`

Evidence SHA-256:
`0ba8da55aac01313f2174243d9aa47ab44cf9423a12b46b7f434297f93a4f41f`

The superseded invalid identity `8c3ace...` is not restored. Historical V1.1
BBCA evidence remains separately identified as:

`CASH_DIVIDEND_BBCA_6bb86334ebe6902946743804`

## E2E paper orchestration

The new orchestration composes the existing verified components and does not
create a second provider, score, execution, or scheduler hierarchy:

- T0 bootstraps the initial NAV and empty runtime state atomically and is
  idempotent.
- POST_EOD verifies score, EOD, decision, sizing, execution, and CA parent
  identities before preparing an immutable next-session package.
- PREOPEN requires the certified official Open contract, exact parent hashes,
  and the CA evidence binding before executing the existing execution path.
- JSON/runtime artifacts use partial-file staging, fsync, immutable conflict
  checks, and restart recovery.
- Pending orders remain explicit when Open is missing; they are not inferred or
  silently dropped.
- Dividend entitlement, receivable, and settlement lifecycle is exercised in
  the offline replay.
- Existing-execution replay revalidates full dividend evidence, not only event
  IDs, before returning `ALREADY_COMPLETE`.
- A CA parent may be extended only with an explicit same-window evidence-bound
  extension; unrelated or altered parent evidence fails closed.

## Synthetic replay

One fresh, synthetic-only five-session replay passed at:

`D:\\Documents\\Project\\idx-e2e-paper-v1-integration-acceptance-20260823-v7`

Acceptance summary SHA-256:
`b5681dfa5047fba8b34e71c27067e74c0c632e8437709636e54129402518f88f`

The replay exercised 5 sessions, a missing-Open pending order and subsequent
resolution, CA evidence extension, dividend entitlement/receivable/settlement,
atomic recovery, and an exact rerun returning `ALREADY_COMPLETE`. It recorded
`provider_calls=false` and `protected_outcomes_accessed=false`.

After the final authority-token and non-payable-blocker guards were added, a
fresh replay was run at:

`D:\\Documents\\Project\\idx-e2e-paper-v1-integration-acceptance-20260823-v8`

Final synthetic acceptance summary SHA-256:
`86523749bab0ad0dda20a70b7492caa764fbba2350e45337af4b1a6f7f1a2392`

## Validation

- Focused CA/dividend/E2E/Decision V2 adapter suite: PASS.
- Focused suite result: 178 passed.
- Python compile for changed source/scripts/tests: PASS.
- Full repository pytest: 646 passed, 0 failed, 3 existing warnings.
- `git diff --check`: PASS.

The independent review P1 items were addressed: active blocker transitions now
require evidence-bound resolution, live journal bindings include
`review_filename`, existing execution rechecks exact dividend evidence, and a
paired replacement whose sell peer was already sold is no longer treated as a
live dependency. Prior-blocker transitions to non-payable historical or
corroborating classifications now fail closed unless a distinct explicit
resolver exists. CA reconciliation and dividend evidence authority tokens are
checked before an existing execution can return `ALREADY_COMPLETE`. A
checked-in crash-recovery regression covers missing execution and snapshot
artifacts.

## Boundaries

No provider call, protected/fresh-forward outcome access, model refit/rescore,
real capture, or scheduler mutation occurred in this lane. The official Open
scheduler remains outside this change. The next live step, if separately
authorized, is a controlled runtime smoke with no historical backfill or
outcome inspection.
