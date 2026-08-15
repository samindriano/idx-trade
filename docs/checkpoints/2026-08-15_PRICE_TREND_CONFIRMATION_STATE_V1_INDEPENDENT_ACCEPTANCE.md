# Price / Trend / Confirmation State V1 — Independent Acceptance

Date: 2026-08-15 (Asia/Jakarta)

Reviewed branch: `research/idx-price-trend-confirmation-state-v1`

Reviewed HEAD: `a33863953b4521dd4549a3089f0da2cfdfb6dcd3`

Review branch: `review/idx-price-trend-confirmation-state-v1-acceptance`

Verdict: `PRICE_TREND_CONFIRMATION_STATE_V1_ACCEPTED_PROSPECTIVE_SIDECAR_NEXT`

## Independent review scope

Reviewed the frozen contract, implementation, prospective helper, tests, and GitHub Actions evidence. No outcome/performance data were accessed and no threshold was changed.

## Accepted semantics

- Raw observed H/L/C/Volume only; no historical Open or adjusted-price dependency.
- Completed source session `t` maps only to the next official feature session `t+1`.
- Target/future rows are excluded from the single-source prospective path before HLCV and duplicate validation; malformed dates and outcome-like schemas still fail closed.
- Prior-20 breakout high excludes the current observation.
- Volume expansion uses current volume versus the previous 20-observation median.
- Volatility compares recent 5-observation median range with the prior non-overlapping 20-observation median.
- Swing structure compares recent 5 observations with the immediately preceding 5 observations.
- MA200 is an optional long-term context axis and does not gate the main trend state.
- Insufficient required rolling evidence produces `INDETERMINATE`; no forward fill or synthetic state is permitted.
- Trend, MA structure, swing structure, volume, volatility, and breakout confirmation remain separate descriptive axes.
- No score, probability, expected return, BUY/SELL recommendation, ranking change, O2 change, Foreign Flow change, or new counter is emitted.

## Threshold review

The broad engineering cutoffs are acceptable as descriptive V1 definitions because they were frozen without outcome optimization:

- volume expansion >= 1.50x;
- volume contraction <= 2/3x;
- volatility contraction <= 0.75x;
- volatility expansion >= 1.25x;
- near-breakout within 3% below prior 20 high;
- BASING: |MA20 5-observation slope| <= 1.5%, 20-observation range width <= 20%, |close-MA20| <= 8%, and volatility not expanding.

These thresholds are not alpha gates and must not be tuned after observing future outcomes.

## Validation evidence

Validation-only PR `#26` at reviewed HEAD:

- focused state + prospective isolation tests: `14 passed`;
- scoped `git diff --check`: PASS;
- repository CI: `53 passed, 1 failed, 4 warnings`;
- the sole failure is the known unrelated storage assertion `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`, where storage reports both `raw_close` and `vendor_adj_close` revision conflicts while the old test expects one.

No Price State test failed.

## Non-blocking interpretation note

Rolling windows are explicitly observation-count based rather than elapsed-calendar-day based. A ticker with trading/data gaps therefore uses its last N valid observed bars. This matches the written V1 contract and is accepted for the descriptive state engine. A future design may add separate suspension/staleness context, but that must not silently redefine V1.

## Next authorized boundary

A separate prospective sidecar/runtime adapter may now be implemented using the existing canonical EOD infrastructure. It must:

1. reuse the exact accepted V1 state implementation/thresholds;
2. consume only hash-verified canonical EOD H/L/C/Volume and official calendar context;
3. write immutable hash-pinned sidecar + manifest artifacts;
4. preserve source `t` -> feature `t+1` causality;
5. fail closed on missing/revised provenance;
6. create no scheduler, counter, model, score, outcome read, Foreign Flow merge, HSC/free-float integration, or ENTRY_ELIGIBLE logic.

Foreign Flow + Price State combination remains a later separately frozen contract after both prospective state streams are operational.