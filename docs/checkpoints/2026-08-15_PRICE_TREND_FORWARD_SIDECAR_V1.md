# Price / Trend Forward Sidecar V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-state-forward-sidecar-v1`

Scientific parent acceptance: `review/idx-price-trend-confirmation-state-v1-acceptance@0c3b221fcecf035add4d0c7ce388ff4b9d6d27da`

Frozen state implementation pin: `a33863953b4521dd4549a3089f0da2cfdfb6dcd3`

Status: `IMPLEMENTED_VALIDATION_PENDING`

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

## Validation gate

Before this lane can move to REVIEW:

1. focused state + forward-sidecar tests pass;
2. target-session-directory independence passes;
3. idempotency and immutable-revision tests pass;
4. canonical parent/snapshot hash mutation fails closed;
5. pinned historical input mutation makes verification fail;
6. outcome-like historical schemas fail closed;
7. missing next official forward session fails closed;
8. `git diff --check` passes;
9. full repository pytest is recorded, with the known unrelated storage assertion reported separately if still present.

No real runtime materialization is authorized by this implementation checkpoint.