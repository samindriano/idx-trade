# Price / Trend Forward Sidecar V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-state-forward-sidecar-v1`

Scientific parent acceptance: `review/idx-price-trend-confirmation-state-v1-acceptance@0c3b221fcecf035add4d0c7ce388ff4b9d6d27da`

Frozen state implementation pin: `a33863953b4521dd4549a3089f0da2cfdfb6dcd3`

Status: `REVIEW`

Verdict: `PRICE_TREND_FORWARD_SIDECAR_V1_IMPLEMENTED_REVIEW_REQUIRED`

## Purpose

Materialize the accepted deterministic Price / Trend / Confirmation State V1 prospectively for the next official session without requiring target-session data.

For completed canonical source session `t`:

`pinned historical HLCV + verified canonical model_input through t -> accepted state V1 -> prospective artifact for t+1`

This lane does not combine Price State with Foreign Flow and does not emit eligibility, ranking, probability, expected return, or trade instructions.

## Canonical source choice

The adapter deliberately consumes canonical `model_input.parquet`, not `session_ohlcv.parquet`.

Reason: accepted Price State V1 needs H/L/C/Volume only. `model_input.parquet` already freezes those fields and is hash-pinned by the DATA_READY session manifest. This avoids importing historical/current Open semantics into the state layer.

Each forward source session must pass:

- exact canonical session-directory path identity;
- `manifest.json.status == DATA_READY`;
- exact `session_date`;
- `outcome_blind == true`;
- `forward_outcomes_accessed == false`;
- exact canonical `model_input.parquet` path;
- model-input SHA-256 equal to the parent manifest pin;
- parent calendar path/SHA equal to the separately supplied forward calendar pin.

No provider fallback exists.

## Historical warm-up

Rolling state needs more history than the prospective EOD archive currently contains. V1 therefore accepts one explicit historical H/L/C/Volume panel only when:

- the panel file exists and matches an externally supplied SHA-256;
- its historical calendar exists and matches an externally supplied SHA-256;
- every panel date belongs to the pinned historical calendar;
- no outcome-like column exists;
- H/L/C/Volume semantics and ticker/date identities validate.

The historical calendar and canonical forward calendar are kept separate and unioned only in memory. The union is accepted only when it preserves the forward calendar's exact next-session identity for source `t`.

Historical and forward duplicate `(ticker, session)` rows must agree exactly on H/L/C/Volume; conflicting overlap fails closed.

## Timing

- Source `t` must itself exist as a verified canonical forward DATA_READY session.
- Target `t+1` must be the next date in the pinned forward official calendar.
- The target session directory and target-session market data are not required.
- All market rows are clipped to `<= t` before the accepted state builder runs.

## Output

Prospective target directory:

`forward_monitoring/prospective/price_trend_confirmation_state_v1/<t+1>/`

Files:

- `price_trend_confirmation_state_v1.parquet`
- `price_trend_confirmation_state_v1.manifest.json`

The manifest pins:

- frozen accepted state commit;
- source and feature sessions;
- artifact hash;
- exact historical panel/calendar hashes;
- exact forward calendar hash;
- each consumed canonical parent-manifest and model-input hash;
- deterministic input fingerprint;
- row/ticker counts and descriptive state distributions;
- explicit zero-provider / outcome-blind / no-model / no-trade flags.

Artifact and manifest are immutable. Existing complete pairs must be semantically identical; partial pairs or revisions fail closed.

## Strict verification

Runtime/acceptance verification must use:

`idx_trade.forward_price_trend_state_verifier.verify_prospective_price_trend_state_strict`

The strict verifier additionally:

- requires exact manifest `output_columns` parity with the frozen sidecar schema;
- recomputes state distributions from the parquet and reconciles them to the manifest;
- re-reads both pinned calendars and recomputes exact source `t` -> target `t+1` semantics;
- rechecks combined-calendar first/last/count metadata;
- re-opens every stored canonical forward source through the original DATA_READY, outcome-blind, path-identity, snapshot-hash, and calendar-hash gates;
- recomputes the deterministic provenance fingerprint.

This prevents a consistently re-hashed but semantically modified parent/calendar/manifest from being treated as valid.

## Validation result

Draft validation PR: `#27`.

Final validation at implementation HEAD before this documentation-only update:

- focused Price State + producer + strict-verifier tests: **27 passed**;
- `git diff --check`: **PASS**;
- full repository pytest: **66 passed, 1 failed, 4 warnings**;
- sole full-suite failure remains the unrelated pre-existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts` assertion (storage emits independent `raw_close` and `vendor_adj_close` conflicts while the old test expects one).

Focused coverage includes:

- target-session-directory independence;
- idempotency and immutable-revision rejection;
- canonical snapshot hash mutation rejection;
- pinned historical input mutation rejection;
- outcome-like historical schema rejection;
- missing next official session rejection;
- exact output-schema and state-distribution reconciliation;
- re-hashed parent semantic tamper rejection;
- calendar semantic tamper rejection.

No Price State / sidecar focused test failed.

## Prohibited

- provider/network calls;
- scheduler creation/change;
- forward counter changes;
- O2 changes;
- outcome/label/TP/SL access;
- historical performance evaluation;
- threshold tuning;
- Foreign Flow merge;
- HSC/free-float/effective-supply integration;
- score/probability/expected-return generation;
- WATCH/READY/ENTRY_ELIGIBLE logic.

## Next boundary

Independent sidecar review only. No real runtime materialization or scheduler/post-capture hook is authorized from this checkpoint.

If independently accepted, the next milestone is a controlled zero-provider runtime hook/materialization using the same frozen producer + strict verifier. Foreign Flow + Price State combination remains later and separately frozen.