# CA / Issuer Candidate-Exposure Completeness Result V1

Status: `PASS_BOUNDED_FORENSIC / GLOBAL_BASIS_BLOCKED`

This is an independent, outcome-blind review of whether the existing
corporate-action/issuer price-basis work is complete enough to certify
candidate safety. It does not repair prices, admit a source, open targets, or
change any candidate status.

## Evidence currently available

- Retained HLC overlay: 1,657 rows across 12 tickers and two event families;
  727 keys intersect the eligible universe and 1,227 eligible rows fall in
  the measured forward-window context.
- Residual non-stable-scale comparison: 188 keys across 19 tickers; none
  intersects the retained HLC overlay. The comparison `idx_close` values are
  forensic substitutes, not authoritative corrections.
- Official action inventory: 55 `stockSplit` rows across 52 tickers, with only
  39 numeric ratios. This is discovery inventory, not a complete transition
  ledger.
- Security-master evidence: every residual key has one active listing interval,
  but there is no issuer/ISIN transition chain or event-level effective-time
  authority.
- No population-wide historical-as-of or same-price-basis contract is present.

## Candidate-specific bounded stress

The existing attribution replay exactly reproduces stored C1/C2/C4 scores and
separately classifies changed keys inside the 188-row residual artifact versus
all other changed rows. That classification is not causal attribution.

| Surface | Direct changed rows | Spillover changed rows | Minimum Top-30 overlap |
|---|---:|---:|---:|
| C1 residual reversal | 66 | 82,291 | 36.667% |
| C2 participation confirmation | 66 | 457 | 83.333% |
| C4 path-efficiency reversal | 66 | 319 | 86.667% |
| H-LIQ diagnostic | 66 | 317 | 90.000% |

C1 is the most basis-sensitive under this bounded forensic stress. C2/C4/H-LIQ
appear more stable against this particular substitution, but that is not a
global safety claim.

## Completeness gaps

1. The 188 residual rows are not the full population of corporate actions,
   issuer changes, or mixed price bases.
2. Existing action summaries are counts/inventory; they do not join each event
   to candidate rows and feature windows with effective date, knowledge time,
   issuer/ISIN continuity, and basis status.
3. H-LIQ is included only in the residual-scale stress; it has no equivalent
   event-level overlay or stored-score reproduction. It remains a future
   hypothesis, not an admitted candidate.
4. There is no dedicated verifier that proves exposure completeness, event
   linkage, source authority, or equal candidate treatment.

Therefore the current evidence proves bounded sensitivity only. It does not
prove that C1/C2/C4/H-LIQ are safe across all corporate-action or issuer
transitions. The only decision-changing next action is an independently
admitted population-wide transition source capable of linking every finite
candidate row/window to event, issuer/ISIN, knowledge-time, and price-basis
status. Without that source, an offline replay would be redundant.

## Artifact provenance

- Exposure builder SHA-256: `6511be556ae0740db46b676d44511b7deab3cb24ddff7ff4be8b8cd7b560ebfb`
- Exposure output SHA-256: `432c6e99ec77fda6d352601969a8a17c435aa45744ca13f1a494e261bbc6d556`
- Basis builder SHA-256: `cec41fa24248eaa0e4fb3f3a5de465a6ba801e1ee0544a2dcd83cee8511ac2dc`
- Basis verifier SHA-256: `ac37fbd24214ad67c13b5955aa7def52a7dbc73e4e0d635cad61618f376d71cf`
- Basis output SHA-256: `3bc3efc9d991f211ae1e5be7d9751da89c14c993f88e8aed23489802a10b8b15`

Scope was read-only and target-free. No canonical data, target, outcome,
provider, network, cloud, or incumbent artifact was modified.
