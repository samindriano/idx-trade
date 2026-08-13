# Checkpoint — Ranking V3-B Structure-Lite Implemented / Local Run Authorized

Date: 2026-08-10 (Asia/Jakarta)

Status: **V3_B_STRUCTURE_LITE_IMPLEMENTED — LOCAL PREPARE + F1-F4 RUN AUTHORIZED UNDER FROZEN CONTRACT**

## Decision

The frozen V3-B Structure-Lite specification is accepted after an outcome-blind implementation review and the feature/cache/runner implementation is complete. A local run may now proceed only under the exact frozen spec + review addendum and only on V2F1-V2F4.

No V3-B model score or outcome was inspected while implementing this code.

## Controlling research contract

Original frozen spec:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_V1.md`

- reported spec SHA-256: `1bf046e98f0d0e92c0981ff4120dc5a54e74f2082b84b8c9d8f4ca281cdf1051`;
- Git blob: `0392ab506aa451355697327d416f8f2b2ea21d4f`.

Independent review addendum:

`docs/RANKING_V3_STRUCTURE_LITE_SPEC_REVIEW_ADDENDUM_V1.md`

- Git blob: `717871707e833ab9818c249d52aae5b234334fc4`;
- addendum creation commit: `6e1dccf285b5415628693b3330e4cb017d760005`.

The addendum clarifies that V3-B uses the exact H/L/C/Volume research frame already consumed by the V2 baseline, official-session windows do not compress suspension gaps, and the discovery cache must physically exclude V2 rows after session 984.

## Implemented candidate

Exact V2 control plus one fixed candidate only.

V3-B Structure-Lite appends these eight columns after exact `V2_FULL_FEATURE_COLUMNS`:

1. `structure_support_distance_atr`
2. `structure_resistance_distance_atr`
3. `structure_support_touch_count_60`
4. `structure_resistance_touch_count_60`
5. `structure_nearest_level_age_sessions`
6. `structure_role_reversal_count_120`
7. `structure_breakout_retest_state`
8. `structure_breakout_volume_confirmed`

No alternate feature bundle, ablation grid, parameter search, model search, threshold search, recency rescue, or second Structure-Lite variant exists.

## Implementation lineage

- `d451befd10e32711fdaf7f468f6038e2e58f0376` — causal Structure-Lite geometry feature engine;
- `837e5ce42e90825451b019517022db7d79a7bf81` — V3-B immutable cache preparation + F1-F4 candidate runner;
- `c06f1a32068e3b8ad7c09385709a7f80258d11b4` — focused Structure-Lite contract tests;
- `885430ef9d2dbacd85af71fa1119be4a96c34752` — correct retest test fixture at the frozen level-band boundary.

Primary code:

- `src/idx_trade/research_v3_structure_lite.py`
- `src/idx_trade/ranking_v3_structure_lite.py`
- `tests/test_ranking_v3_structure_lite.py`

## Implementation properties

Feature engine:

- left-only five-official-session pivot logic;
- official-session gap breaks a pivot window rather than compressing time;
- deterministic same-side connected-component level clustering using the frozen ATR tolerance;
- prior-session level inventory only; current bar cannot create the level it breaks;
- separated prior OHLC touch count;
- nearest-level age in official sessions;
- historical causal role-reversal count;
- current breakout / later retest state `{-2,-1,0,+1,+2}`;
- triggering-breakout volume confirmation from prior-only volume baseline;
- exact existing causal ATR implementation over the frozen research H/L/C frame;
- label/outcome columns rejected by the structure builder;
- no Open dependency.

Cache preparation:

- verifies frozen panel/calendar/security-master/V2-cache/V2-manifest hashes;
- reads V2 prepared Parquet with `signal_session_index <= 984` predicate;
- bounds HLCV feature construction at official session 984;
- joins Structure-Lite by exact ticker/date to the immutable V2 subset;
- preserves all existing V2 columns/row order;
- writes a separate immutable V3-B discovery cache + manifest;
- records coverage/missingness and feature-order hashes;
- declares `v2f5_v2f6_materialized=false` and `outcome_metrics_computed=false`.

Outcome runner:

- accepts only the frozen discovery cache;
- hard-blocks V2F5/V2F6;
- runs exact V2 `HGB_XS_MARKET` control first;
- uses the existing immutable V2 HGB_XS_MARKET F1-F4 reference artifacts;
- requires exact row/order and `1e-12` score/metric control equivalence before Structure-Lite can be interpreted;
- runs exactly one Structure-Lite candidate after equivalence PASS;
- uses exact frozen V2 metrics plus the same absolute/paired robustness gates as V3-A;
- writes metrics, predictions, models, paired comparison, coverage, aggregate, verdict, runtime, ledger rows and SHA inventory;
- never gives calibrated-probability or independent-validation semantics.

## Verification performed before authorization

No repo-local full pytest can be run from the ChatGPT container because the user's checkout/data store are not mounted here.

The final Python sources were syntax-checked. An isolated focused execution of the geometry helpers passed checks for:

- future append does not change prior left-only pivot identity;
- official-session gap breaks a five-session pivot window;
- adjacent OHLC touches are collapsed by the 3-session separation rule;
- volume confirmation uses a prior-only baseline;
- bullish breakout then causal retest yields `+1` then `+2` under the frozen level band.

The local run must still run the full repository pytest suite before any cache preparation or scoring. Failure means stop.

## Authorized local sequence

1. Fetch/pull this branch and verify clean state.
2. Run full repo pytest.
3. Locate and hash-verify the frozen panel/calendar/security-master/V2 prepared table/V2 manifest/V2 HGB_XS_MARKET reference artifacts.
4. Run `python -m idx_trade.ranking_v3_structure_lite prepare ...` into a new empty output directory.
5. Inspect only outcome-independent cache/coverage/provenance diagnostics; verify cache contains no row after session 984.
6. Freeze/report the new cache and manifest hashes. Do not edit code/spec after this point.
7. Run `python -m idx_trade.ranking_v3_structure_lite run ...` into another new empty output directory.
8. Exact control equivalence must PASS before candidate interpretation.
9. Apply only the frozen gates and deterministic decision.
10. Update ledger ordinals 004-005, checkpoint, handoff and CURRENT_STATUS; commit/push; stop for ChatGPT review.

## Hard boundaries

Not authorized:

- any V3-B parameter/feature tweak after score;
- any V3-B second variant or rescue;
- V3-A rescue;
- V2F5/V2F6 materialization/scoring/summarization;
- reserved post-2026-07-31 V2 forward outcome access;
- writing `FORWARD_OUTCOME_ACCESS_STARTED`;
- V3-C/D/E outcome work;
- V3 integration/final confirmation;
- probability calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live, or main merge.

## Expected result states

- `V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`; or
- `V3_B_STRUCTURE_LITE_KILL_KEEP_V2_CONTROL`.

A failure in test/data/provenance/control equivalence is a blocked/failed run, not evidence for or against the Structure-Lite hypothesis.
