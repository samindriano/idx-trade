# Price / Trend Forward Sidecar V1 — Independent Acceptance

Date: 2026-08-15 (Asia/Jakarta)

Reviewed branch: `integration/price-trend-state-forward-sidecar-v1`

Reviewed HEAD: `a4d19fd1615c4a9f9988ed16540c34f5efbe1b1a`

Review branch: `review/idx-price-trend-forward-sidecar-v1-acceptance`

Verdict: `PRICE_TREND_FORWARD_SIDECAR_V1_ACCEPTED_RUNTIME_CONTEXT_PIN_REQUIRED`

## Accepted engineering contract

The prospective sidecar implementation is accepted as decision-valid, deterministic, outcome-blind infrastructure for the already accepted Price / Trend / Confirmation State V1.

Accepted properties:

- exact frozen state implementation pin `a33863953b4521dd4549a3089f0da2cfdfb6dcd3`;
- canonical forward source is hash-pinned `model_input.parquet`, so Open semantics remain outside Price State;
- source `t` -> next official feature session `t+1` is structural and target-session data/directory is not required;
- historical and forward calendars remain separately pinned and are unioned only in memory;
- historical/forward HLCV overlap must agree exactly;
- all state calculation rows are clipped to `<= t`;
- output artifact/manifest pair is immutable;
- zero providers, zero model fit/scoring, zero outcome access, zero trade recommendation, zero counter changes;
- no Foreign Flow, HSC/free-float, O2, scheduler, ranking, or eligibility integration occurs.

## Strict verifier acceptance

Runtime/acceptance authority is:

`idx_trade.forward_price_trend_state_verifier.verify_prospective_price_trend_state_strict`

The strict verifier closes the reviewed fail-open surface by independently reconciling:

- exact output-column schema;
- row/ticker counts;
- state distributions;
- historical and forward calendar hashes;
- exact source `t` -> target `t+1` relation;
- combined-calendar first/last/count metadata;
- every canonical parent session through original DATA_READY, outcome-blind, canonical path, snapshot hash, and calendar hash gates;
- deterministic provenance fingerprint.

A consistently re-hashed but semantically modified parent/calendar/manifest therefore fails verification.

The lightweight verifier retained in `forward_price_trend_state.py` is not the runtime/acceptance authority and must not be used for deployment decisions.

## Validation evidence

Validation-only PR `#27`:

- focused Price State + producer + strict-verifier tests: `27 passed`;
- `git diff --check`: PASS;
- full repository pytest: `66 passed, 1 failed, 4 warnings`;
- sole failure is the known unrelated pre-existing storage assertion `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`, where two independent revision conflicts (`raw_close`, `vendor_adj_close`) are emitted while the old test expects one.

No Price State / sidecar test failed.

## Runtime blocker: historical context identity

The adapter intentionally accepts an externally supplied historical H/L/C/Volume panel and SHA-256. That is sufficient for immutable replay mechanics, but the Price State contract does not yet name one exact authoritative historical-panel identity/manifest.

Therefore **a real runtime materialization is not yet authorized**.

Before runtime wiring, a separate controlled integration checkpoint must:

1. select one exact historical HLCV panel and record its path, SHA-256, date coverage, schema, and scientific lineage;
2. preferably reuse the exact pinned historical market panel already used by the accepted Foreign Flow V2 prospective producer if its H/L/C/Volume semantics and coverage are sufficient, avoiding a second historical market lineage;
3. pin the exact historical calendar paired with that panel;
4. pin the current complete official forward calendar used by the canonical EOD source session;
5. confirm that all required official extension sessions from the historical cutoff through source `t` exist canonically and are hash-verified;
6. execute only a zero-provider mechanical smoke/materialization after those pins pass;
7. verify the result with the strict verifier.

If the exact historical parent cannot be established, fail closed rather than substituting a convenient local file.

## Next authorized boundary

`controlled runtime context pin + zero-provider hook/materialization verification`

Still prohibited:

- new scheduler/counter;
- provider calls or recapture;
- historical or prospective outcome evaluation;
- threshold tuning;
- Foreign Flow + Price State combination;
- WATCH / READY / ENTRY_ELIGIBLE;
- O2 changes;
- HSC/free-float integration.
