# OHLCV O2 — Frozen Robustness / Provenance Audit Specification

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-robustness-v1`
Parent review commit: `982c92093d3125fbebd3f928570c27f25de35e66`
Decision: `O2_ROBUSTNESS_PROVENANCE_AUDIT_AUTHORIZED`

## Purpose

Audit whether the accepted `O2_OPEN_GEOMETRY` historical-development uplift is robust to Open provenance and historical-era composition before any candidate final refit or new forward contract is considered.

This is primarily a diagnostics/audit lane. It must not turn into feature search.

## Frozen inputs

Reuse the exact accepted O2 runtime artifacts from external manifest:
`cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`.

Use the exact 278,168-row common-support population and the accepted Open provenance artifact:
`90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687`.

No population recomputation from a different panel is allowed.

## Required audit

1. Independently re-hash and reproduce baseline/O2 fold and aggregate metrics from persisted O2 predictions.
2. Join exact row-level Open provenance without changing row identities.
3. Report common-support counts and percentages by canonical Open source/provenance and by fold/year.
4. Report distributions for `open_position`, `open_to_high`, `open_to_low` by provenance: count, null/nonfinite, min, p01, p05, median, p95, p99, max.
5. Verify expected geometry bounds/signs and explicitly count violations:
   - `0 <= open_position <= 1` within numerical tolerance;
   - `open_to_high >= 0` within tolerance;
   - `open_to_low <= 0` within tolerance.
6. Produce descriptive paired baseline-vs-O2 performance diagnostics by provenance where sample size/class support is sufficient. Do not invent a new survivor threshold from these strata.
7. Recompute the accepted overall/fold metrics from existing predictions after excluding, one at a time:
   - all `ZAPI_TRADINGVIEW` rows;
   - Yahoo rows that required verified split-scale reconstruction, if that provenance subclass is available;
   - any other explicitly small provider-specific subclass already represented in the provenance artifact.
   These are sensitivity diagnostics only; do not retrain models and do not optimize exclusions.
8. Report historical-era diagnostics using the same existing predictions, with particular attention to whether O2 uplift is confined to early lower-Open-coverage years.
9. Document the exact algebraic relationship:
   `open_position = -open_to_low / (open_to_high - open_to_low)`
   when the denominator is nonzero, and verify it numerically on common support.
10. Based on the evidence, emit exactly one factual recommendation:
   - `O2_ROBUSTNESS_PASS_MINIMALITY_AUDIT_RECOMMENDED`
   - `O2_ROBUSTNESS_PASS_FINAL_FREEZE_REVIEW_RECOMMENDED`
   - `O2_ROBUSTNESS_CONCERN_STOP`

## Decision guidance

A robustness concern exists if the accepted uplift materially disappears or reverses after removing a small provider-specific subset, if geometry distributions show unexplained provider discontinuities, if formula/bounds fail, or if the apparent improvement is overwhelmingly concentrated in a narrow historical/provider slice.

Do not create post-hoc numeric thresholds to rescue or kill O2. Report exact facts and use conservative judgment.

If robustness passes but redundancy appears material, recommend a separately frozen minimality ablation; do not execute it in this audit.

If robustness passes and there is no compelling need for minimality testing, recommend final-freeze review; do not perform the final refit here.

## Protected boundary

- no model retraining or tuning;
- no new Open features;
- no O3/interactions/regime feature search;
- no post-2026-07-31 fresh-forward outcome access;
- no forward-outcome marker;
- no remaining Open repair/provider calls;
- no canonical V3-B overwrite;
- no final refit;
- no execution/PnL, Path Risk, probability, payoff, reliability, paper/live or broker work.

## Output

Persist a dated runtime checkpoint plus immutable external audit artifacts/hashes. Run focused tests and full pytest, push fast-forward, then STOP for independent ChatGPT review.
