# Ranking V3-B Structure-Lite Specification — Independent Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **INDEPENDENT REVIEW PASS WITH PRE-OUTCOME IMPLEMENTATION CLARIFICATIONS**

This addendum reviews `docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md` before any V3-B model fit or score. No V3-B outcome, V2F5/V2F6 outcome, or reserved post-2026-07-31 V2 forward outcome was inspected. The frozen candidate bundle, constants, metrics, gates and ledger slots are unchanged.

Frozen spec identity:

- reported SHA-256: `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- Git blob at review: `0392ab506aa451355697327d416f8f2b2ea21d4f`.

## 1. Review conclusion

PASS. The single fixed eight-feature Structure-Lite candidate is narrow enough to test one incremental geometry hypothesis and remains clearly separated from the legacy outcome-conditioned scoring layer.

No second variant, ablation grid, level-parameter search, model search or rescue candidate is authorized.

## 2. Clarification A — technical price/volume source

Where the frozen spec refers to the same split-consistent technical-price frame, the V3-B implementation must use the exact `high`, `low`, `close`, and `volume` research columns consumed by the existing frozen baseline/V2 feature pipeline from the hash-pinned signal-research panel.

V3-B must **not** introduce a new adjusted-price series, reconstructed split history, synthetic OHLC, vendor-specific chart series, or alternate volume field. ATR14 must be obtained through the existing causal ATR implementation over that same frozen H/L/C frame.

This clarification preserves equivalence with the V2 research data contract; it is not a claim that raw chart geometry is execution-PnL ready.

## 3. Clarification B — official-session windows on sparse ACTIVE rows

All P/L/R/S/B/V session windows in the frozen spec are official IDX session distances. A ticker row missing on an official session does not silently compress time.

For a five-session left-only pivot, all five required official sessions must have valid rows/HLC/ATR for that ticker. A suspension/data gap breaks that pivot window. Likewise touch/reversal/event horizons use official session-index differences, not simple row-number differences.

This prevents a 60-row observed window from spanning materially more than 60 official sessions after suspensions.

## 4. Clarification C — discovery cache must physically exclude F5/F6 rows

The V3-B discovery prepared cache may contain only exact V2 eligible rows with `signal_session_index <= 984`.

When reading the immutable V2 prepared Parquet for cache construction, the implementation should use a predicate on `signal_session_index <= 984` rather than materializing later candidate rows and filtering after the fact. Whole-file SHA verification is allowed; parsing/loading V2F5/V2F6 candidate rows is not.

The raw outcome-independent HLCV panel may be hash-verified as a whole, but Structure-Lite feature construction for this discovery cache must be bounded at the official date corresponding to session 984. No later HLCV row may influence a feature through pivot/cluster/event state.

## 5. Clarification D — control and outcome order

The implementation task may build and hash-freeze the outcome-independent V3-B discovery cache and implement tests/runner, but it must stop before candidate scoring.

A later local run must:

1. verify the new cache/manifest and frozen spec/addendum identities;
2. fit exact V2 control on F1-F4;
3. prove row/feature/score/metric equivalence against immutable V2 artifacts;
4. only after equivalence PASS, fit/score the one Structure-Lite candidate;
5. apply only the frozen absolute and paired gates;
6. update ledger ordinals 004-005 and stop.

## 6. Unchanged hard boundaries

- exact 8 Structure-Lite output columns and order: unchanged;
- P=5, L=60, R=120, S=3, B=10, V=20: unchanged;
- cluster/touch/volume thresholds: unchanged;
- V2 model/H10/universe/score/metrics: unchanged;
- V2F1-F2-F3-F4 only for discovery;
- V2F5/F6 sealed;
- V3-A remains closed;
- reserved V2 forward outcomes remain unread;
- `FORWARD_OUTCOME_ACCESS_STARTED` must not be written;
- no V3-C/D/E, integration, calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live or main merge.
