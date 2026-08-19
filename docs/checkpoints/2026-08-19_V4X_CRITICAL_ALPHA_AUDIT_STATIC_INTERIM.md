# V4-X critical alpha audit — static interim

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/v4x-critical-alpha-audit-v1`
Status: `STATIC_REVIEW_COMPLETE_LOCAL_FROZEN_ARTIFACT_AUDIT_REQUIRED`

## Purpose

Independent red-team review of whether the V4-3R Geometry3 historical IC evidence carried into V4-X/V4-X1 is invalidated or materially inflated by causal leakage, target contamination, universe look-ahead, price-scale error, fold overlap, or evaluation/reporting mistakes.

No V4-X1 model bytes, targets, gates, or fresh-forward outcomes are modified by this audit.

## Static conclusions so far

### 1. No direct feature-time future leakage found

The V4 control feature builder is backward/same-session only:

- ATR uses previous close and backward rolling windows;
- return features use positive lags (`shift(5)`, `shift(20)`), not future shifts;
- rolling highs/lows/volume/value are backward windows;
- same-date cross-sectional ranks and market-context medians are formed from EOD-t information;
- listing-domain invalid rows are removed before sequential and cross-sectional features.

Geometry3 uses only admitted exact-session `Open_t`, `High_t`, `Low_t`, `Close_t` and therefore is available after EOD t, while the target entry is Open(t+1).

### 2. Fold/target overlap check is structurally safe

The frozen purge is 10 official sessions. For each fold:

`max_training_signal_session_index = validation_start - 10 - 1`.

Therefore the H10 terminal of the last training signal is exactly `validation_start - 1`, and H5 ends earlier. No training target crosses into the validation fold under the frozen indexing contract.

### 3. No preprocessing leakage found

The median imputers are inside the sklearn pipeline and are fit only on the fold training frame. HGBR is then fit on that training frame. Validation predictions are generated separately before target-based evaluation.

### 4. No future-target-filtered scoring universe found

This was treated as a critical hypothesis because the parent file is named `v4_3_full_target_support_rows_idx_combined.csv`.

The generation code proves the row identity is not filtered to successful future targets:

1. `rebuild_decision_support()` builds the decision universe from the PIT/listing-safe feature table and `universe_primary_liquid`, before target values are materialized.
2. Future Open/Close availability is attached only as boolean support fields.
3. `combine_target_support()` left-merges CA support and retains every decision row; it adds `h5_full_target_support`, `h10_full_target_support`, and consensus booleans rather than filtering rows.
4. The historical model frame uses the combined row identity but again applies the current/PIT `universe_primary_liquid` flag; it does not filter by the target-support booleans.

Therefore there is no evidence that the model was allowed to know which stocks would later have observable targets before scoring.

### 5. Target indexing is structurally correct

The frozen target implementation uses:

- entry = Open at official session t+1;
- H5 terminal = Close at t+5;
- H10 terminal = Close at t+10;
- corporate-action continuity must be resolved;
- market state and endpoint observability fail closed.

No t/t+1 or t+5/t+10 off-by-one error was found statically.

### 6. Historical raw-price design does not intentionally overwrite OHLC with adjusted close

Repository canonicalization explicitly keeps raw observed OHLC as raw execution fields and stores vendor adjusted close separately. Adjustment-factor changes are not assumed to be splits. Frozen panel provenance still needs the local exact-file audit below; static code intent alone is not sufficient proof of the bytes.

### 7. Accepted Open has a trust-boundary weakness that requires exact-file validation

The V4 runner trusts the hash-pinned derivative/overlay admission process. At the final execution layer, derivative support is essentially finite/positive Open, and target materialization does not independently repeat the source HLC-parity/range proof. Geometry3 itself rejects Open outside same-session [Low, High], but target entry would still trust a positive Open.

Upstream Yahoo/TradingView and CA-scale reconstruction contracts explicitly require HLC parity and Open inside the canonical range. The frozen exact files must therefore be audited to prove zero violations. This is a critical fail condition if any finite admitted Open lies outside canonical [Low, High].

### 8. Row-lag semantics are causal but may drift from exact official-session horizons

Ticker features use ticker-row shifts/rolling windows. If a ticker is missing rows for official sessions, `shift(5)` can span more than five official sessions. This is not future leakage, but frequent drift would mean the feature names/semantics are not exact session horizons. The local market-input audit measures the rate and tail severity.

### 9. Absolute IC is conditional on future target observability

Scores are created without target visibility, but daily IC is evaluated only on rows whose future target is certified/observable and on admitted dates. This is not direct model leakage; however, the absolute historical IC is a conditional estimand. If future-unobservable stocks are systematically harder, `~0.098` can be optimistic relative to the full live universe.

Geometry3-vs-Control paired evidence is less vulnerable because both models share the same observable target support, but missingness can still interact differently with their rank geometry.

### 10. Frozen evaluator is not exactly common-support Spearman when rows are missing

Model alpha is percentile-ranked on the full scored universe. After future-unobservable target rows are removed, the evaluator computes Pearson correlation between those retained full-universe alpha percentiles and target ranks constructed on the observable subset. It does not re-rank alpha on the common observable subset.

This preserves ordering but not uniform rank spacing. It can therefore differ from the standard Spearman rank correlation calculated after both variables are restricted and re-ranked on common support. This is a methodological issue, not future leakage. The consumed-result audit now recomputes true common-support Spearman without fitting or rescoring any model and reports the difference.

### 11. Historical development / researcher-selection bias is real

Geometry3 was preregistered before V4 target access, but its hypothesis lineage came after historical V1/V2/V3/O2 work in which historical outcomes were already consumed. Repo forensic checkpoints explicitly classify the six historical folds as correlated development evidence and require genuinely fresh prospective confirmation.

Therefore V4-3R IC `~0.098` must not be described as a pristine untouched holdout OOS estimate. It is historical-development evidence and can carry multiple-testing/researcher-selection optimism even if the code is causally clean.

### 12. Reporting cross-check is required

The postmortem's stated consensus `+0.013593997891865855` equals the difference between challenger and control absolute medians. The actual paired-delta summarizer separately computes the median of per-fold paired IC deltas. These are different estimands.

Frontend fold values previously introduced are not supported by a repository source search and must not be trusted until the immutable result artifact is re-aggregated. This is currently classified as a possible reporting/frontend issue, not a model-alpha invalidation.

## Adversarial tests added

`tests/test_v4x_critical_alpha_audit.py`:

- future market mutation invariance for all V4 control features;
- future Open/HLC mutation invariance for Geometry3;
- same-session Open sensitivity sanity check;
- exact H10 purge boundary check;
- exact target entry/terminal formula and indexing check.

`tests/test_v4x_critical_alpha_audit_contract.py` protects audit scripts from model fit/scoring/provider calls and checks pinned consumed inputs.

## Read-only frozen-artifact audits added

### `scripts/audit_v4x_frozen_market_inputs.py`

Checks exact frozen hashes, canonical HLC validity, Open range/identity consistency, derivative-overlay conflicts, row-lag official-session drift, and descriptive `regular_market_value` semantics. It does not access targets/outcomes or run models.

### `scripts/audit_v4x_consumed_result_consistency.py`

Reads only already-consumed V4-3R result artifacts. It re-aggregates fold/paired statistics, checks recorded IC reproduction, reports coverage-conditioned IC, compares difference-of-medians vs median-of-paired-deltas, and recomputes true common-support Spearman from the immutable stored validation scores/target ledger. It never refits or rescores a model and never touches fresh-forward data.

## Current severity state

- Confirmed critical alpha-invalidating error: **none yet**.
- Confirmed direct future leakage: **none found**.
- Confirmed training/validation target overlap: **none found**.
- Confirmed future-target-filtered scoring universe: **rejected by code lineage**.
- Confirmed research-process caveat: **yes — historical development is not pristine untouched OOS**.
- Material unresolved checks: **exact frozen Open scale/range, ticker-row horizon drift, observability-conditioning magnitude, common-support Spearman deviation, reporting paired-delta consistency**.

Do not upgrade V4-X historical evidence to `VERIFIED` until the exact local frozen-artifact audits and adversarial tests pass.