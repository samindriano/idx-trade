# TradingView V2.1 Step-2 Training-Basis Runtime V1.1

Date: 2026-08-20 (Asia/Jakarta)
Branch: `audit/tradingview-v2-1-training-basis-impact-v1`
Runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_training_basis_impact_v1_1_20260820`

## Boundary

Offline forensic only. No provider calls, model fitting, model scoring, historical performance recomputation, protected-forward access, panel mutation, or retraining authorization.

Parent v1.1 artifact manifest SHA-256:
`62562fa3f1d949c3e4f9e225aae13b116a5e2c00dffcceab6240ebb07ea422d6`

## Frozen panel vs current official IDX witness

- frozen panel rows: 981,940;
- official IDX rows loaded: 1,002,245;
- overlap: 981,940;
- exact HLC rows: 978,497;
- exact HLC rate: 99.6493676%;
- row-scale-consistent mismatches: 1,845;
- stable scale rows: 1,657;
- stable scale runs: 56;
- affected tickers: 12.

All 56 stable-run records emitted by the runtime carry `price_provenance=YAHOO_RAW`. Observed multiplicative factors include 2, 5, 10, 25 and 1.4800000553. The repeated run islands across different tickers indicate a provenance/basis seam problem must be considered before interpreting the broad downstream feature deltas.

## Clean V2 representation

The local reconstruction reproduced the immutable clean PIT-safe V2 prepared table exactly:

- rows: 292,631;
- parity changed rows: 0;
- parity changed cells: 0;
- immutable table SHA-256: `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`;
- stable key SHA-256 remains `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`.

Under the stable official-IDX HLC counterfactual:

- changed V2 prepared rows: 52,554 / 292,631 = 17.9591%;
- changed feature cells: 362,515.

The changes are dominated by cross-sectional ranks, market medians/breadth, and market-relative features. This can amplify a small number of direct price-basis defects to many otherwise unaffected ticker rows.

Runtime verdict: `V2_TRAINING_SCALE_BASIS_IMPACT_FOUND`.

## V4-X1 candidate training-date representation

The audit used the exact frozen V4-X feature/model-frame code but deliberately stopped before historical target materialization. On the outcome-free superset of final H5/H10 training rows:

- candidate rows: 277,194;
- changed rows: 63,295 = 22.8342%;
- changed feature cells: 435,286;
- PIT/listing diagnostics unchanged;
- open-price evidence counts unchanged;
- session geometry changes appeared in 960 rows for `session_body_signed_range` and `session_open_position_range`.

Runtime verdict: `V4_X1_POTENTIAL_TRAINING_SCALE_BASIS_IMPACT_FOUND`.

This is not yet the exact H5/H10 fit-row verdict because v1.1 audited a target-free superset.

## Interpretation correction

Do not read `52,554` or `63,295` as the number of raw bad-price rows. Only 1,657 stable scale rows were directly replaced. The much larger downstream counts are expected to include cross-sectional spillover because V2/V4 features rank securities and compute market context by date.

The next bounded audit is v1.2 and must answer three questions before any model remediation decision:

1. do stable runs create mechanically scale-explained return discontinuities at provenance seams;
2. how much downstream change is direct affected-ticker impact versus cross-sectional spillover;
3. do the exact frozen V4-X H5/H10 fit-row identities change, using only already-frozen support booleans and training dates, without target values.

Runner: `scripts/run_training_price_basis_impact_audit_v1_2.py`.

## Stop

No retraining, no model rescue/tuning, no prospective outcome access, and no full TradingView acquisition are authorized by v1.1.
