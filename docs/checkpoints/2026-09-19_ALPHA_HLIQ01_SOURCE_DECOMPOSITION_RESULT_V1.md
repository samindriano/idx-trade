# H-LIQ-01 Source Decomposition — Independent Target-Free Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Scope: isolated research staging only; no protected target, outcome, provider,
cloud, incumbent-predictive, canonical, capture, or production access.

## Question

Does H-LIQ-01 retain a structurally distinct component after removing the
fixed C2 turnover-level component, or is the apparent novelty only a
participation/turnover transformation?

This is a target-free source-decomposition diagnostic. It does not estimate
IC, ICIR, OOS performance, P&L, incremental alpha, or candidate superiority.

## Frozen contract

- Population: the existing `eligible_decision_universe=true` surface.
- Time: the latest 600 official sessions, `2024-01-12` through `2026-07-31`.
- Baseline H-LIQ: rolling 20-session standard deviation of
  `log(close * volume)`.
- Removed component: cross-sectional percentile rank of
  `log(mean(turnover, 5) / median(turnover, 60))`.
- Residual: per-date OLS residual of percentile-ranked H-LIQ on
  percentile-ranked turnover level, with an intercept.
- Selection diagnostics: deterministic score-descending/ticker-ascending
  Top-30 selection; average ties for percentile ranks.

Inputs were the frozen panel, guarded Stage-A features, official sessions,
and tradability anchors. The generated artifact was written only under:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Results

| Diagnostic | Baseline H-LIQ | Level-residual | Interpretation |
|---|---:|---:|---|
| Mean daily Spearman vs C2 turnover-level | `0.1647556` | `0.0157646` | The removed level component explains most direct level dependence. |
| Mean daily Spearman vs full C2 | `0.0995506` | `0.0843185` | Residual still shares a modest participation relation. |
| Mean daily Spearman vs C1 | `-0.0452528` | `0.0007788` | No evidence of a new C1-linked direction from this diagnostic. |
| Mean daily Spearman vs C4 | `-0.1049832` | `-0.0438907` | C4 relation remains negative and structural only. |
| Selected bottom-value Q1 share | `39.6722%` | `50.3889%` | Residualization worsens the low-value exposure. |

The residual used all `600` frozen dates and `155,679` finite eligible rows.
Baseline versus residual Top-30 membership had:

- mean overlap: `72.0056%`;
- minimum overlap: `16.6667%`;
- mean turnover: `27.9944%`;
- q95 turnover: `73.3333%`;
- maximum turnover: `83.3333%`.

## Independent validation

`research/verify_alpha_hliq01_source_decomposition_v1.py` independently
recomputed the key decomposition, rank, overlap, and bottom-value metrics from
the four frozen inputs. The verifier result was `PASS`:

- all source hashes matched the artifact declarations;
- generator code hash matched;
- residual date/row support matched (`600` / `155,679`);
- turnover-level and full-C2 Spearman values matched;
- Top-30 mean/minimum overlap matched;
- baseline/residual bottom-value shares matched;
- outcome/provider/cloud/incumbent-predictive access flags were all false.

Artifact and verifier outputs:

- generated artifact:
  `alpha_hliq01_source_decomposition_v1.json`
  SHA-256 `352a422086d540318f0464aaec2b80b3eb427a87176caa0326559242dacfc35e`;
- independent verification:
  `alpha_hliq01_source_decomposition_independent_verification_v1.json`;
- generator code SHA-256:
  `be3880729cd5defc5509c7b7dd8bae06548b475e9305b73e0e9c112506576531`;
- verifier code SHA-256:
  `409a2b66e9bd99080007301d94dd2ab3b08dccf25b06a1fb46bf65ea528fdd66`.

## Disposition

This result supports the narrower disposition:

`STRUCTURAL_NONREDUNDANCY_VS_C2_LEVEL_ONLY`

It does **not** establish mechanism-level novelty, economic attractiveness,
PIT safety, corporate-action basis safety, executable capacity, or predictive
value. The residual's remaining relation to full C2 and its materially worse
bottom-value exposure leave H-LIQ-01 at:

`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`

No C5 ID was created. No candidate status, protected packet membership, or
future target-evaluation order changed.

## Next implication

The exact C2-level-only decomposition question is answered enough to avoid
repeating it. Further H-LIQ work is justified only if it tests a genuinely new
mechanism or an independently admissible liquidity/identity/PIT surface. The
current result does not justify opening protected targets or adding a provider.
