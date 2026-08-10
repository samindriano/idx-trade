# Ranking V4-C Cross-Sectional Context — Spec Review Addendum V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **PRE-OUTCOME DESIGN REVIEW PASS**

## Review decision

`V4_C_CONTEXT_SPEC_REVIEW_PASS_IMPLEMENTATION_ALLOWED`

The frozen V4-C specification is sufficiently narrow and mechanically distinct from existing V3-B context to proceed to implementation and outcome-blind audit.

This review does **not** authorize model outcome scoring.

## Independence from V4-B

V4-C is frozen while V4-B remains pre-outcome. No V4-B model result has been viewed. This ordering is intentional: the V4-C feature family must not be adapted to whichever Price-Path hypothesis later performs well or poorly.

## Overlap review against V3-B

Existing V3-B date-level market context includes:

- `market_primary_liquid_count`;
- `market_breadth_return_5_positive`;
- `market_breadth_return_20_positive`;
- medians of 5/20 return, ATR/close, close-position, relative volume and traded-value-relative activity.

V4-C adds IQR dispersion, not another median or breadth threshold. The intended incremental question is therefore mechanically distinct:

> not “where is the market center?” but “how spread out is the opportunity set around that center?”

The blind audit must still test empirical redundancy. Any absolute date-level Spearman `>=0.95` versus an existing date-level V3-B context feature triggers mechanical review before scoring.

## Candidate-budget review

Only one challenger is permitted:

- ordinal `018` exact V3-B control;
- ordinal `019` V3-B + four frozen dispersion features.

No separate return-dispersion, volatility-dispersion, winner-loser, MAD, standard-deviation or quantile-band candidates are allowed. This avoids another feature-family tournament after the cumulative historical candidate count has already reached 12.

## Data/provenance review

The context must be constructed from the full causal primary-liquid universe using existing V2 baseline-feature semantics before model-row/outcome filtering.

This is a key requirement. Computing dispersion only over label-resolved/model rows would create a potentially outcome-dependent cross-section and is prohibited.

The implementation should therefore:

1. physically read only the bounded raw signal-panel columns required by the exact V2 baseline feature builder;
2. reconstruct causal baseline features and `universe_primary_liquid` without labels/outcomes;
3. compute one date-level four-feature context table;
4. join that table onto the exact frozen V3-B cache rows by signal date;
5. prove all existing V3-B columns/row order are unchanged.

## Runtime-note compliance

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` remains controlling.

For V4-C, the likely additional cost is baseline-feature reconstruction from the bounded signal panel, not the single HGB challenger itself. Implementation should use:

- physical date/column projection when reading Parquet;
- one deterministic context construction pass;
- no uncontrolled candidate/fold parallelism;
- no caching of training-dependent preprocessing;
- exact V3-B control equivalence before any future challenger interpretation.

No performance optimization may change the existing V2 baseline semantics.

## Gate review

The challenger gate remains unchanged from V4-A/V4-B. This is deliberate. V4-C does not receive an easier promotion rule because earlier V4 candidates failed.

## Review conclusion

Implementation + blind cache audit may proceed for the exact frozen spec Git blob:

`43f222f31c7c0ea15e870d22b066aae95858c81f`

Outcome scoring remains separately gated.