# IDX V4-X Clean-Data Consolidation V1 — Claim

Date: 2026-08-20 (Asia/Jakarta)
Owner: `ChatGPT/V4-X-Clean-Data-Consolidation`
Branch: `data/v4-x-clean-data-consolidation-v1`
Status: `ACTIVE_PREPARED_WAITING_FOR_STAGE_A_RUNTIME_AND_FINAL_IDENTITY_ADJUDICATION`
Base main: `79d4d6c2a02eb3677aa8e1d90fa22eacbf2451b9`

## Owned scope

This lane owns only the offline consolidation of already accepted clean-data corrections and field-level provenance into an immutable candidate input lineage for later clean V4-X replay/refit.

Authorized Stage-A work:

- verify and apply the accepted 1,657-row H/L/C price-basis overlay to the pinned frozen panel;
- verify and apply the accepted 1,655-row Open overlay, with the two unsupported Open candidates remaining fail-closed/unavailable;
- prove Volume and Regular-Market Value remain unchanged;
- preserve the accepted official exchange calendar unchanged;
- materialize a separate field-level provenance sidecar and correction ledger;
- produce immutable external candidate artifacts and a hash-pinned manifest;
- stop before final clean-universe freeze, model work, or outcome access.

## Explicit non-ownership / collision boundary

The concurrent ACTIVE lane `PIT Security Identity / Listing-Domain V1 adversarial audit` on `audit/pit-security-identity-stage-c-v1` owns FREN/KOCI, listing-domain correctness, ticker inclusion/exclusion, universe remediation, and exact V4-X final-training support intersection.

This consolidation lane MUST NOT:

- decide whether FREN/KOCI or any ticker belongs in the final clean universe;
- add/drop/repair ticker identities or listing domains;
- reconstruct the final training support before independent identity adjudication;
- mutate that concurrent lane.

Stage A therefore preserves the frozen parent row identity. Final clean input/universe freeze is a later Stage B that may consume only an independently accepted identity/universe artifact.

## Other hard exclusions

No provider calls, target/return access, model fit, model scoring, model tuning, protected/fresh-forward outcome access, forward-counter reset, feature/window semantic change, primary-liquidity rule change, or parent-panel overwrite.

V4-X2 session-aligned work is separate and already frozen; this lane does not implement or execute it.
