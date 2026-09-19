# H-LIQ-01 Size-Neutral Representation — Structural Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Diagnostic: `H-LIQ-01-SIZE-NEUTRAL-V1`  
Status: `PASS_STRUCTURAL_ONLY / NOVELTY_PENDING / ECONOMIC_CAUTION`

## Question

Does the low-market-value exposure of H-LIQ-01 come mainly from the raw scale of
`log(close * volume)`, or is it intrinsic to temporal variability?

The preregistered diagnostic compared the existing h20 score with one fixed
size-neutral representation: each date's H-LIQ percentile rank was regressed
on that date's `regular_market_value` percentile rank, and the residual was
ranked higher first. There was no horizon or parameter sweep and no target
access.

## Results

| Representation | Finite rows | Dates | Tickers | Top-30 turnover mean | Q10 / median / Q90 | Bottom-value Q25 share | Bottom-volume Q25 share |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline H-LIQ h20 | 155,679 | 600 | 583 | 10.306% | 3.333% / 10.000% / 16.667% | 39.672% | 27.578% |
| Size-neutral residual h20 | 155,679 | 600 | 583 | 20.785% | 10.000% / 20.000% / 30.000% | 14.983% | 13.872% |

Size neutralization substantially reduces the low-value and low-volume exposure,
but roughly doubles Top-30 turnover. It is therefore not a free economic
improvement.

## Relationship to existing families

| Pair | Daily Spearman | Mean Top-30 overlap |
|---|---:|---:|
| Baseline vs size-neutral H-LIQ | 0.9614 | 72.006% |
| Baseline H-LIQ vs C1 | -0.0453 | 8.967% |
| Size-neutral H-LIQ vs C1 | -0.0746 | 8.167% |
| Baseline H-LIQ vs C2 | 0.0996 | 31.339% |
| Size-neutral H-LIQ vs C2 | 0.0971 | 34.756% |
| Baseline H-LIQ vs C4 | -0.1050 | 12.478% |
| Size-neutral H-LIQ vs C4 | -0.1531 | 9.378% |

The two H-LIQ forms remain recognizably the same family: high score
correlation and 72% Top-30 overlap. Size neutralization does not create
evidence of a new mechanism or incremental predictive information.

## Disposition

The low-value exposure is **partly scale-related**, because one fixed
size-neutral representation reduces it materially. However, the turnover cost,
remaining proxy/PIT uncertainty, and high relationship to baseline mean the
variant is not promoted and no C5 ID is created.

Retain H-LIQ-01 as:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

The baseline and size-neutral forms may be carried as two explicitly labeled
future representations for later policy review, but neither enters the current
protected evaluation packet.

## Provenance

Staged output:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_hliq01_size_neutral_diagnostic_v1.json`

| Artifact | SHA-256 |
|---|---|
| Diagnostic code | `49d4557060cccecc59a85574a62bd949b6b007950ff66e5dddecfc44658ac185` |
| Output JSON | `e323634b1b1d86f9cb2b2f2ad5f3c3db91b44d1a907cd266029ad0d00bea9704` |
| Guarded Stage-A manifest | `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96` |
| Guarded features | `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4` |
| Frozen panel | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` |
| Official sessions | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| Tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |

The diagnostic code reports `PASS_STRUCTURAL_ONLY`. Its JSON access flags are
self-attested metadata, not process-level proof. No target, outcome, incumbent
score, provider, network, cloud, capture, scheduler, or production artifact was
accessed. The output is bound to repository head `8b4dbbce`, the guarded
Stage-A manifest hash above, the diagnostic code hash, and all four source
hashes.

## Limitations and next action

- `regular_market_value` and volume remain proxy fields, not historical ADV,
  spread, queue, or executable capacity.
- PIT/as-of, corporate-action basis, issuer continuity, survivorship, and
  population completeness remain unresolved.
- This is not an independent verifier of the diagnostic implementation; it is
  a preregistered structural experiment with hashes and a bounded output.

No further H-LIQ parameter search is justified until a new data contract or a
separate scientific question changes the evidence boundary.
