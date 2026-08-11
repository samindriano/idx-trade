# OHLCV O2 Robustness / Provenance Audit Runtime

Date: 2026-08-12 (Asia/Jakarta)  
Branch: `research/idx-ranking-ohlcv-o2-robustness-v1`  
Starting HEAD: `42f3668e12fc891d5b564eb9cba5101543e0c80a`  
Recommendation: `O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED`

## Scope and boundary

This was a read-only audit of the accepted O2 historical-development runtime.
No model was retrained, no provider/network call was made, no fresh-forward
outcome was accessed, and no forward-outcome marker was written. No final refit,
new feature, O3 experiment, interaction, regime adaptation, or execution/PnL
work was started.

## Frozen inputs and identity preservation

- accepted O2 runtime artifact manifest:
  `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`;
- accepted Open provenance:
  `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687`;
- coverage-gate readiness artifact:
  `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242`;
- exact common-support rows: `278,168`;
- common-support key SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- persisted O2 predictions: `281,358` rows, equally split between baseline and
  O2, with six validation folds;
- all 10 O2 input artifact hashes were independently verified before audit.

The provenance join was one-to-one and preserved all `278,168` common-support
row identities. The prediction/provenance join was also complete.

## Metric reproduction

Fold and aggregate metrics were recomputed from persisted scores using the
existing evaluator. They match the accepted O2 runtime:

- fold metric rows reproduced: `12`;
- aggregate metric rows reproduced: `2`;
- maximum absolute fold metric difference: `9.367506770274758e-17`;
- maximum absolute aggregate metric difference: `7.979727989493313e-17`;
- `fold_metrics_match=true`;
- `aggregate_metrics_match=true`.

No model fitting was needed for this reproduction.

## Common-support Open provenance composition

| canonical provenance | rows | percent |
|---|---:|---:|
| `IMMUTABLE_PANEL|EXISTING_IMMUTABLE` | 189,541 | 68.139038% |
| `YAHOO_YFINANCE|DIRECT_RAW_HLC_EXACT` | 81,436 | 29.275833% |
| `YAHOO_YFINANCE|SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE` | 5,637 | 2.026473% |
| `ZAPI_TRADINGVIEW|TV_RECOVERY_CANDIDATE` | 1,554 | 0.558655% |

No unresolved provenance rows entered the exact common-support set.
`common_support_provenance_by_year.csv` and
`validation_provenance_by_fold_year.csv` contain the complete year/fold
composition. The important composition fact is that 2023-2024 are mostly
Yahoo-direct, while 2025-2026 are mostly/entirely immutable-panel rows; the
audit therefore does not treat provider composition as time-invariant.

## Geometry distributions and bounds

Full per-provenance distributions—including count, null/nonfinite, min, p01,
p05, median, p95, p99 and max—are persisted in
`geometry_distributions_by_provenance.csv`. All four provenance groups had
zero null/nonfinite values for all three geometry columns.

Bounds were evaluated with tolerance `1e-12`:

- `0 <= open_position <= 1`: zero below-zero and zero above-one violations;
- `open_to_high >= 0`: zero violations;
- `open_to_low <= 0`: zero violations;
- zero nonfinite geometry values.

## Algebraic redundancy check

For nonzero denominator, the exact relation is:

`open_position = -open_to_low / (open_to_high - open_to_low)`

On all `278,168` common-support rows:

- invalid/zero denominators: `0`;
- maximum absolute algebra error: `5.6066262743570405e-14`;
- rows exceeding tolerance: `0`.

This is a material minimality finding: the three O2 columns are algebraically
redundant, even though the fitted HGB can distribute split gains across them.

## Provenance and historical diagnostics

Descriptive validation-performance diagnostics are in
`performance_by_provenance.csv`; no new stratum survivor threshold was applied.
The paired PR-AUC deltas were:

| provenance | rows | paired PR-AUC delta |
|---|---:|---:|
| immutable panel | 90,189 | +0.005625 |
| Yahoo direct raw HLC exact | 48,800 | +0.004783 |
| Yahoo split-scale reconstructed | 1,343 | -0.004203 |
| TradingView recovery candidate | 347 | +0.005112 |

The split-scale stratum is small and has a negative descriptive delta, so it is
reported as a diagnostic rather than used to rescue or reject the overall
candidate. The two frozen provider-exclusion sensitivities below address it
without retraining.

Year-level paired PR-AUC deltas were:

| year | validation rows | paired PR-AUC delta |
|---|---:|---:|
| 2023 | 23,003 | +0.005907 |
| 2024 | 39,881 | +0.003786 |
| 2025 | 44,811 | +0.007560 |
| 2026 | 32,984 | +0.014133 |

The uplift is therefore not confined to the early lower-Open-coverage years;
the largest descriptive uplift is in 2026, while 2023-2025 remain positive.
These are historical-development diagnostics, not fresh-forward validation.

## Frozen provider-exclusion sensitivities

These are score-only diagnostics from the persisted predictions:

| exclusion | mean paired delta | median paired delta | minimum fold delta | positive folds |
|---|---:|---:|---:|---:|
| exclude all `ZAPI_TRADINGVIEW` | +0.007451 | +0.007282 | +0.000504 | 6/6 |
| exclude Yahoo split-scale reconstructed | +0.007540 | +0.007398 | +0.000774 | 6/6 |

The accepted uplift does not disappear or reverse under either frozen
provider-exclusion diagnostic. No additional small provider-specific subclass
was represented in the common-support provenance beyond the two explicitly
audited classes above.

## Single recommendation

`O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED`

Basis: bounds and algebra pass; metrics reproduce exactly; both provider
exclusion sensitivities retain positive uplift in every fold; year-level uplift
is not confined to the early provider-composition slice; and the three geometry
features satisfy an exact algebraic redundancy relation.

This recommendation authorizes only a separately frozen minimality audit for
review. It does not authorize that ablation, final refit, fresh-forward
evaluation, or any new Open feature in this run.

## Validation

- focused pytest: `4 passed` (`tests/test_ohlcv_o2_robustness_audit.py`);
- full pytest: `286 passed, 5 warnings`;
- model retraining: `false`;
- provider calls: `false`;
- fresh-forward access: `false`.

## External audit artifacts

Root: `D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_robustness_v1_20260812`

| file | SHA-256 |
|---|---|
| `audit_contract.json` | `644c390bccf09a6049e884f8ca2ae627bae41e305db217a373c60289e2f0faa0` |
| `audit_summary.json` | `82818a2f852a0ea4957754764acafa039ed2ae4c0ab2db3185ad966f38c92983` |
| `common_support_provenance_by_year.csv` | `dda1bbb77b1f9c1c2c3879397230f34861704459185408688ccb04819e3bb898` |
| `common_support_provenance_counts.csv` | `a4058051c65bf1ea713e32e718dc0fea951ddfe993b85ae79583e2a4192c2a43` |
| `geometry_bounds_algebra.json` | `7e667821a6506c2e80ef60563040b768b248002216012554f05bd7d8f7586f09` |
| `geometry_distributions_by_provenance.csv` | `9737036177927052c40785422769ffa13ce812dd1683786c50e5032ba3291cc4` |
| `metric_reproduction.json` | `fed8fa53c852f0bd3dbb9fd961352aff0e63783d0b4a08c205fef9ad6cb81ae9` |
| `performance_by_provenance.csv` | `c5b96de005b941fbd837fbfe0311b89a108402d7727ec91aa425178599b7fed2` |
| `performance_by_year.csv` | `b2cdb9d4051e611acd183d9cd94d11d99afd4c0e7a37aca2877c79c70adaef91` |
| `provider_exclusion_sensitivity_aggregate.csv` | `566cd1447c5961e14eb97d1c5a4b636b1f90978792e84e0995e11a2cda16a3f0` |
| `provider_exclusion_sensitivity_by_fold.csv` | `8ea5c47c3bdcf423dd287d201442675d69882c52905e666d7a1577ba244ba619` |
| `recommendation.json` | `8236db786456e409c63d1f31420cfe3ab8c84c55a8ce3e83ba608c572344bad2` |
| `reproduced_aggregate_metrics.csv` | `66ed45fd756b9b8a43372f44c83bacf3f301af68bed779667144839a50a754db` |
| `reproduced_fold_metrics.csv` | `0f469c28da0a859596a990cc1cb29d65e4ea780fec13d1f2e45cb50a1727430e` |
| `validation_provenance_by_fold_year.csv` | `1a7c998871ec82b5984b217e63127813bf3d287bd49950cd0fb48e48417f2c3f` |
| `artifact_manifest.json` | `ba685239991ad820c45955c2116f56dd00a077b54a8d052c49adb2f97be438bd` |

The external audit manifest contains 15 artifacts and all 15 internal hashes
were independently verified after runtime.
