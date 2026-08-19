# Price-Basis Post-Remediation Guard V1 — Frozen Pre-Run Contract

Date: 2026-08-20 Asia/Jakarta  
Branch: `data/price-basis-remediation-v1`

## Parents

This guard is downstream of two immutable local results:

- H/L/C remediation manifest SHA-256 `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`;
- bounded repaired-population Volume/Value audit manifest SHA-256 `317c5cad8170b34b69c87eb43763b9afe4a368cbd9a3afaf94c5297aebeeb38f`.

The H/L/C remediation changed exactly 1,657 rows across 12 tickers and left all
non-H/L/C fields unchanged. The bounded Volume/Value audit found all 1,657 rows
`SAME_BASIS` for both Volume and Regular-Market Value.

## Why another guard exists

Two integrity questions remain before any clean model refit:

1. the previous Open-inside-H/L proof became stale when repaired H/L changed;
2. the bounded Volume/Value audit was exhaustive for the 1,657 repaired rows,
   but did not yet record whole-panel official overlap, year/provenance/seam
   diagnostics, or the exact effect of an official Volume/Value counterfactual
   on the liquidity source features.

## Frozen Open/HLC rule

On the repaired 1,657 ticker/date identities:

- reconstruct the exact V4-X accepted-Open lineage using the frozen derivative
  Open panel plus immutable recovery overlay fallback;
- compare every admitted/available accepted Open against corrected Low/High;
- if the corrected panel itself contains a finite `open`, audit that field as a
  secondary diagnostic too;
- missing/unadmitted Open is reported in the denominator and is not synthesized;
- any available Open outside `[corrected Low, corrected High]` is a hard block;
- any invalid corrected H/L envelope is a hard block.

No Open field may be repaired by this runner.

## Frozen broad Volume/Value rule

Compare the entire corrected 981,940-row research panel against the already
archived official IDX Stock Summary Volume and Regular-Market Value evidence.

The clean-refit gate is deliberately strict:

1. official ticker/date identity support must cover every corrected panel row;
2. official Volume and Value must be present on every corrected panel row;
3. panel Volume must equal official IDX Volume on every row;
4. panel `regular_market_value` must equal official IDX Regular-Market Value on
   every row;
5. the official Volume/Value counterfactual must change zero rows of
   `relative_volume_20`, `log_regular_value_relative_20`, and
   `universe_primary_liquid` under the frozen 60-session / Rp1B liquidity rule.

The runner also persists year/provenance, ticker/provenance, provider-seam, and
corporate-action-boundary diagnostics. These diagnostics do not weaken the hard
full-panel equality gate.

## Authorization verdict

Only

`POST_REMEDIATION_GUARDS_PASS_CLEAN_REFIT_PROTOCOL_READY`

allows the next step to be **protocol freezing** for a deterministic clean
V2/V4-X historical replay/refit. It still does not itself fit a model.

Any other verdict means stop for forensic review. No remediation, tolerance
relaxation, model fit, score comparison, or tuning is authorized from a failed
run.

## Guardrails

- no provider/network calls;
- no model fit, scoring, or tuning;
- no historical target-value access;
- no protected prospective-outcome access;
- no mutation/overwrite of parent panels or legacy models;
- no Volume/Value/Open repair;
- no TradingView full acquisition or Path Risk restart.
