# V4-X Historical Alpha Critical Audit — Final Record

Date: 2026-08-19 (Asia/Jakarta)

Branch: `research/v4x-critical-alpha-audit-v1`

Status: `HISTORICAL_ALPHA_AUDIT_PASS_NO_CRITICAL_ERROR_FOUND`

Scientific boundary: historical-development evidence only. This document does **not** convert V4-X1 into a prospectively validated model. V4-X1 remains frozen and its fresh-forward outcome performance remains unknown until the preregistered forward gate opens.

## Executive verdict

V4-X historical alpha survived the dedicated red-team audit. No critical future leakage, train/validation contamination, target-timing error, frozen-input corruption, Open/HLC inconsistency, metric-reproduction failure, chance/null explanation, or material target-observability selection mechanism was found.

The most defensible single historical headline metric is:

- **mean daily common-support Spearman RankIC = `0.09545975125676774` across 600 chronological historical validation sessions**.

Two additional values must be retained with it:

- frozen V4-3R median-of-six-fold mean consensus IC = `0.09775243938276076`;
- conservative exact-feature-window-support mean daily RankIC = `0.08327323251280924`.

The `0.09775` value is valid for the frozen protocol but is **not** the preferred externally stated generic RankIC because it is a median of fold means. The `0.09546` common-support Spearman is the preferred comparable historical RankIC.

## Frozen artifact identity

Historical V4-3R result manifest SHA-256:

`05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`

Frozen panel SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Frozen official-session calendar SHA-256:

`661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

Open derivative panel SHA-256:

`a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`

Open overlay parquet SHA-256:

`2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41`

No provider calls, model fitting, model scoring, protected-forward outcome access, or V4-X1 mutation was permitted by these audit scripts.

## Audit sequence and results

### 1. Synthetic causal / future-mutation attack

Command:

```powershell
python -m pytest -q `
  tests/test_v4x_critical_alpha_audit_contract.py `
  tests/test_v4x_critical_alpha_audit.py
```

Observed result: **11 tests passed**.

The suite intentionally mutates future market values and verifies that features before the cutoff do not change. It also verifies the Geometry3 same-session boundary, target construction, and purge/timing invariants.

Covered failure hypotheses:

- future H/L/C/V/value leaking into pre-cutoff features;
- future Open leaking into pre-cutoff Geometry3;
- target endpoint mistakes;
- H10 training target overlap into validation;
- causal-feature invariance failure.

Verdict: `PASS`.

### 2. V4/V4-3R core regression and contract suite

Command covered:

- `test_ranking_v4_3_features.py`
- `test_ranking_v4_3_preregistration.py`
- `test_ranking_v4_3_target_execution.py`
- `test_ranking_v4_3_model_eval.py`
- `test_ranking_v4_3_evaluator_ties.py`
- `test_ranking_v4_3_ca_training_domain.py`
- `test_ranking_v4_3r_model_eval.py`
- `test_ranking_v4_3r_support.py`
- `test_v4_3r_ca80_prefit_support_gate_contract.py`
- `test_v4_3r_execution_freeze_contract.py`
- `test_v4_3r_historical_one_shot_contract.py`

Observed result: **59 tests passed**.

Verdict: `PASS`.

### 3. Frozen market/Open forensic audit

Script:

`scripts/audit_v4x_frozen_market_inputs.py`

Observed status:

`V4X_FROZEN_MARKET_INPUT_AUDIT_PASS`

Critical counts:

- invalid canonical HLC rows: `0`;
- derivative Open outside canonical Low/High: `0`;
- overlay Open outside canonical Low/High: `0`;
- derivative/overlay finite Open conflicts: `0`;
- finite Open rows missing canonical panel identity: `0`;
- non-positive finite accepted Open rows: `0`.

`regular_market_value` behaved like same-session traded value rather than shares-outstanding market capitalization: median `regular_market_value / (close × volume) = 1.0`.

The forensic audit also exposed a real but non-leaking feature-semantics caveat: V4 control uses ticker-row shifts/rolling windows. Some tickers have missing official-session rows, so a row lag can span more official sessions than its nominal name.

Observed raw-panel row-lag census:

| Row lag | Longer than intended | Rate | p99 official-session span |
|---|---:|---:|---:|
| 5 | 39,979 | 4.0911% | 9 |
| 20 | 84,470 | 8.7710% | 37 |
| 60 | 137,945 | 14.9042% | 111 |

This is **not future leakage**. It is a horizon/continuity semantics issue and was attacked separately below.

### 4. Reproduction of consumed historical IC

Script:

`scripts/audit_v4x_consumed_result_consistency.py`

The stored V4-3R daily metrics were recomputed from the already-consumed immutable score and target artifacts.

Maximum absolute errors when reproducing recorded daily IC were approximately `1e-16`, i.e. floating-point noise.

This rules out a reporting/aggregation mismatch between the stored daily artifacts and reported IC.

#### Frozen aggregate evidence

Challenger Geometry3 consensus fold means:

- F1 `0.09227078711981862`
- F2 `0.06625356936830823`
- F3 `0.10323409164570287`
- F4 `0.029696513400161217`
- F5 `0.12931364086270403`
- F6 `0.16348225628388718`

Median of fold means: `0.09775243938276074`.

All 6 challenger consensus folds are positive.

### 5. True common-support Spearman attack

The frozen evaluator first ranked alpha on the full scored cross-section and then evaluated only target-observable names. The audit therefore recomputed a stricter conventional metric:

1. restrict alpha and realized target to the identical observable names for a date;
2. rerank both variables on that common support;
3. compute Spearman correlation;
4. average daily IC across the 600 historical validation sessions.

Challenger results:

| Head | Frozen-formula mean IC | Common-support Spearman |
|---|---:|---:|
| H5 | `0.07468185743463863` | `0.07493424533009098` |
| H10 | `0.09181246454865954` | `0.09185167971133042` |
| Consensus | `0.09737514311343039` | **`0.09545975125676774`** |

Consensus common-support correction: `-0.001915391856662633` mean IC.

Control common-support consensus Spearman: `0.08979323509925058`.

Therefore the evaluator detail does **not** explain the historical signal.

### 6. Incremental Geometry3 interpretation correction

The earlier `+16.15%` relative-lift headline came from subtracting two independently aggregated medians:

- challenger median fold mean `0.09775244`;
- control median fold mean `0.08415844`;
- difference of medians `0.013593997891865842`.

That quantity is mathematically valid but is **not** the preferred paired incremental estimand.

Paired consensus fold deltas were:

- F1 `+0.010685407762013583`
- F2 `+0.007773675209904724`
- F3 `+0.016502588021718095`
- F4 `+0.002219705464555424`
- F5 `-0.007154457248388149`
- F6 `+0.004798994024111119`

Thus Geometry3 wins **5/6 paired folds**, not 6/6.

Preferred incremental summaries:

- mean paired daily consensus IC delta: `+0.005804318872319132`;
- median paired fold-mean delta: `+0.0062863346170079215`;
- common-support mean consensus difference: `0.09545975125676774 - 0.08979323509925058 = +0.00566651615751716`.

Future documentation/UI must not present `+16.15%` as the primary Geometry3 incremental result.

### 7. Within-date permutation/null attack

Script:

`scripts/audit_v4x_consumed_result_nulls.py`

No model was refit or rescored. Stored frozen alpha scores were held fixed and the target association was shuffled within date 1,000 times.

Challenger:

| Head | Observed common-support RankIC | Null std | Null q99.9 | z vs null | Empirical one-sided p |
|---|---:|---:|---:|---:|---:|
| H5 | `0.07493425` | `0.00268840` | `0.00867758` | `27.82` | `0.000999...` |
| H10 | `0.09185168` | `0.00262882` | `0.00757319` | `34.87` | `0.000999...` |
| Consensus | **`0.09545975`** | `0.00259022` | `0.00647637` | **`36.86`** | `0.000999...` |

The empirical p-value is resolution-limited by 1,000 permutations; it should be interpreted as **0 of 1,000 shuffled runs matching/exceeding the observed result**, not as an exact true p-value of 0.001.

Control consensus also strongly rejects the null:

- observed common-support RankIC `0.08979324`;
- z `34.13`;
- empirical p resolution `0.000999...`.

Verdict: the observed signal is not plausibly explained by the tested chance/metric-null mechanism.

### 8. Last-mile Attack A — exact official-session feature support

Script:

`scripts/audit_v4x_last_mile_support_selection.py`

Purpose: determine whether the high IC depends on rows where ticker-row lags/rolling windows cover more official sessions than their nominal horizon.

Challenger consensus results:

| Support filter | Retained observable rows | Mean daily common-support RankIC | Positive folds |
|---|---:|---:|---:|
| All common support | 100.00% | `0.09545975` | 6/6 |
| Exact shift-5 | 99.38% | `0.09572508` | 6/6 |
| Exact shift-5 + shift-20 | 97.24% | `0.09715106` | 6/6 |
| Exact endpoint 5/20/60 | 89.80% | `0.08303489` | 6/6 |
| **Strict actual feature-window continuity** | **89.97%** | **`0.08327323`** | **6/6** |

Strict actual-feature-window support requires the relevant shift-5, shift-20, ATR14, rolling-20, and rolling-60 history to be contiguous on the official-session calendar.

The strict filter reduces challenger consensus IC by `-0.01218652`, so sparse/irregular-history population effects are material enough to document.

However, the same strict filter reduces the control almost identically:

- control all-common-support consensus: `0.08979324`;
- control strict consensus: `0.07760894`;
- challenger strict consensus: `0.08327323`.

The strict-support incremental Geometry3 advantage remains approximately **`+0.00566429`**, essentially unchanged from the all-common-support `+0.00566652`.

Therefore irregular ticker history does not explain Geometry3's incremental improvement. Even the conservative strict-support V4-X consensus RankIC remains `~0.0833`.

Head-specific strict challenger results:

- H5 `0.06709909`, 6/6 positive folds;
- H10 `0.07875555`, 5/6 positive folds;
- consensus `0.08327323`, 6/6 positive folds.

### 9. Last-mile Attack B — future target-observability selection

The audit measured whether future target availability is systematically associated with frozen alpha rank.

Challenger consensus:

- overall observable rate: `0.882688013`;
- observable pooled mean alpha rank: `0.49912654`;
- unobservable pooled mean alpha rank: `0.50657216`;
- pooled observable-minus-unobservable rank gap: `-0.00744562`;
- mean daily alpha/observability correlation: `-0.00870151`;
- pooled KS distance: `0.02046630`;
- top-decile observable rate: `0.88506367`;
- bottom-decile observable rate: `0.88425701`.

Top- and bottom-decile target availability are both very close to overall coverage, so there is no visible tail-selection mechanism large enough to explain an IC near `0.095`.

Missingness is not literally random by failure subtype:

- `PRICE_CONTINUITY_UNRESOLVED`: 10.68% of score rows, mean alpha rank about `0.525`;
- `TARGET_DATA_UNOBSERVABLE`: 1.05% of score rows, mean alpha rank about `0.319`.

This remains a caveat because missing realized outcomes cannot be reconstructed. The aggregate selection pressure, however, is small and similar for challenger and control.

Verdict: `NO_MATERIAL_OBSERVABILITY_SELECTION_MECHANISM_FOUND`.

### 10. Repository test-suite note

The first post-audit full `pytest` run found one failure in `tests/test_storage.py`:

`test_explicit_revision_mode_returns_audit_conflicts`

The fixture changed both `raw_close` and `vendor_adj_close` while expecting only one conflict. `src/idx_trade/storage.py` intentionally audits both columns, so two conflicts are correct. The stale test expectation was corrected without changing storage implementation, model code, features, data, targets, or scientific artifacts.

After the fix, focused verification:

```powershell
python -m pytest -q `
  tests/test_v4x_last_mile_support_selection_audit_contract.py `
  tests/test_storage.py
```

Observed result: **7 tests passed**.

A final full-repository post-fix `python -m pytest -q` rerun remains a housekeeping validation item until its output is recorded. It is not an alpha-science blocker because the only prior full-suite failure was independently traced to the stale storage test expectation.

## Preferred public / frontend wording

Preferred concise wording:

> V4-X achieved a historical mean daily cross-sectional Spearman RankIC of approximately **0.095** across **600 chronological walk-forward validation sessions**. Under a stricter exact-session feature-support filter, RankIC remained approximately **0.083**. These are historical-development results; V4-X1 prospective performance remains unknown until the forward gate matures.

Do not say simply `IC = 0.098` without definition.

Do not present the old `+16.15%` difference-of-medians as the primary incremental Geometry3 result.

Preferred incremental wording:

> Geometry3 added approximately **+0.0057 mean daily consensus RankIC** versus the same 25-feature V4 control on common support; the paired fold delta was positive in **5 of 6 folds**.

## Final scientific assessment

`V4X_HISTORICAL_ALPHA_AUDIT_PASS_NO_CRITICAL_ERROR_FOUND`

What has been ruled out to a high practical standard:

- obvious future feature leakage;
- target overlap into validation;
- target endpoint logic error;
- frozen panel/Open corruption detectable by the audited contracts;
- evaluator artifact sufficient to explain headline IC;
- result-file aggregation mismatch;
- within-date chance/null explanation;
- Geometry3 dependence on sparse-history rows;
- material alpha-tail selection from future target observability.

What remains unresolved by design:

1. researcher/model-selection bias from the broader historical research process;
2. true performance on never-before-seen prospective sessions;
3. unknown returns for genuinely unobservable historical targets.

These cannot be fixed by further slicing the same consumed historical outcomes. The next scientific judge is the frozen V4-X1 prospective block.

## Stop rule

Do not continue historical feature hunting, threshold tuning, metric slicing, or model replacement using these consumed V4-3R outcomes merely to improve the historical result.

V4-X1 stays frozen. Any new alpha hypothesis belongs to a separately identified future research generation and must not rewrite this historical evidence.