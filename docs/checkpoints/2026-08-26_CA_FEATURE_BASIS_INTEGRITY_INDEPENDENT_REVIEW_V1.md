# Corporate-Action Feature-Basis Integrity — Independent Review V1

Date: 2026-08-26
Review lane: Research Integrity / Data QA Gate V1
Reviewed audit branch: `audit/ca-feature-basis-integrity-v1`
Reviewed audit HEAD: `c18cbfee7dfbb8b16f15d8a4ca27c2f68041abb2`
Reviewed audit manifest SHA-256: `b9a37511fd92a8f4bfc9e7e7e16597a720523523c2ae87f9ae135e872dab89d3`

## Independent verdict

`PASS_WITH_REVIEW_FIXES`

The audit is substantively accepted as evidence of a real backward-looking corporate-action feature-basis integrity defect class. It does **not** establish that the frozen V4-X1 model must immediately be refit, that historical/prospective performance is invalid, or that the prospective evaluation counter must be reset.

Explicit independent verdicts:

```text
STRUCTURAL_BACKWARD_CA_RISK = PROVEN
BBCA_2021_FEATURE_EXPOSURE = PROVEN
BBCA_2021_DIRECT_FINAL_FIT_IMPACT = NONE_EXCLUDED_BEFORE_FIT
ACCEPTED_OVERLAY_EXACT_INPUT_DELTA = PROVEN
DIRECT_EXACT_FIT_DELTA = 681_ROWS
CROSS_SECTIONAL_SPILLOVER = 55921_ROWS
PERFORMANCE_MATERIALITY = NOT_PROVEN
MARKET_WIDE_CA_COMPLETENESS = NOT_PROVEN_INCOMPLETE
DATA_POLICY_REMEDIATION = REQUIRED
MODEL_REFIT = NOT_YET_AUTHORIZED_OR_PROVEN_REQUIRED
PROSPECTIVE_COUNTER_RESET = NO
```

## What is accepted

### 1. Backward-window risk is real

The frozen V4 feature builder computes sequential raw-price-derived quantities including lagged returns, ATR14, 20-session extrema, and 60-session extrema/history before cross-sectional ranks and market context. The reviewed audit found no general CA-aware basis reset/quarantine in that backward feature path.

The separate target-continuity machinery protects the **future H5/H10 target interval**. It does not establish that a feature row's backward dependencies remain on one compatible price basis.

Therefore the defect class is structural, not a notebook-only visualization issue.

### 2. BBCA 2021 is a valid exposure witness but not a final-fit contamination witness

The audit traces the recorded BBCA `1:5` split around `2021-10-13` and demonstrates raw pre/post basis discontinuity plus 5/14/20/60-session backward exposure.

However, all reviewed BBCA combined-support rows have H5/H10 support false and exact final-fit membership is zero for both heads. The independent review therefore accepts:

`BBCA_2021_VERDICT=EXCLUDED_BEFORE_FIT`.

This distinction must remain explicit in future documentation and tests.

### 3. The accepted-overlay input delta is material enough to remediate/revalidate

The audit reconstructs exact-fit feature-change identities as:

| scope | rows |
|---|---:|
| exact-fit union | 241,724 |
| changed union | 56,602 |
| direct | 681 |
| cross-sectional/market spillover | 55,921 |

The 56,602 changed identities are approximately 23.4% of the exact-fit union, but 98.8% of changed identities are spillover rather than direct ticker-basis changes.

Existing diagnostics show nonzero and sometimes large feature/rank deltas, so the result cannot be dismissed as floating-point noise. This proves model-input change exposure. It does **not** prove performance materiality because the audit intentionally did not access outcomes or refit/score models.

## Review fix 1 — provenance wording for the 56,602-row reconstruction

The audit runner verifies both accepted v1.1 and v1.2 manifests. However, the actual feature-impact CSV consumed by `build_exact_fit_impact(...)` is:

`v1.1/v4_x1_candidate_training_feature_impact_rows.csv`.

Those changed identities are then intersected with frozen exact H5/H10 final-fit support.

Accordingly, the precise provenance description is:

> exact-final-fit support reconstruction from the accepted v1.1 feature-impact rows, with v1.1/v1.2 accepted lineage manifests verified.

The current audit's shorthand `v1.2 exact-fit support-only reconstruction` should not be interpreted as meaning that the 56,602 identities were directly read from a v1.2 feature-impact CSV. Before incident closure, either:

1. document the exact v1.1 -> v1.2 contract proving that this reconstruction is the accepted v1.2 meaning; or
2. rename the source label to reflect the actual consumed artifact.

This is a provenance/labeling correction, not evidence that the 56,602-row reconstruction is numerically wrong.

## Review fix 2 — BBCA golden-case source binding

The current audit runner carries the BBCA trace defaults as code-level constants (`split_date='2021-10-13'`, ratio `1:5`). The checkpoint cites official evidence and SHA-256 values, but the event date/ratio are not yet parsed end-to-end from a source-bound golden-case input inside the audit runner.

Therefore BBCA may be used as the permanent regression golden case only after the test fixture/contract binds at minimum:

- ticker;
- event family;
- effective/transition-session state;
- ratio/terms when applicable;
- official source/evidence reference;
- evidence SHA-256;
- deterministic event/golden-case ID.

The regression must fail closed if those provenance fields are absent or inconsistent. A hard-coded expected event may remain as a test assertion, but it must not be the sole source of event truth.

## Remediation direction accepted by this review

The safe default is **basis-epoch quarantine/reset**, not broad historical price adjustment.

A structural event ends one compatible price-basis epoch and starts another only when the relevant market transition session is resolved from source-backed evidence. A backward-looking feature is research-admissible only when all of its price-basis-sensitive dependencies belong to one compatible epoch.

This approach avoids inventing generic multiplicative adjustments for event families whose economics differ materially, especially rights/HMETD, bonus shares, mandatory conversions, and capital restructurings.

The detailed frozen policy is specified separately in:

`docs/research_integrity/CA_AWARE_FEATURE_BASIS_POLICY_V1.md`.

## What remains explicitly unauthorized

This independent review does not authorize:

- protected outcome access;
- historical performance recomputation;
- V4-X1 tuning or rescue research;
- model refit;
- prospective counter reset/mutation;
- retroactive score/trade/fill creation;
- canonical artifact overwrite;
- production capture/runtime change;
- generic market-wide price adjustment.

## Required closure sequence for INC-001

1. Freeze CA-aware feature-basis policy.
2. Bind event evidence and effective-transition semantics fail-closed.
3. Implement basis-safe backward dependency admission.
4. Recompute affected feature inputs outcome-blind.
5. Re-measure direct and spillover exact-fit deltas independently.
6. Add source-bound golden/adversarial cases and regression tests.
7. Re-run the Research Integrity gate.
8. Only then decide, under a separate authorization boundary, whether a clean same-science model refit is required.

## Review boundary

`INC-001` is confirmed but not closed. The current frozen V4-X1 scientific definition is not changed by this review. This checkpoint accepts the defect class and remediation direction while preserving the distinction between **input integrity**, **model artifact integrity**, and **performance materiality**.
