# Alpha CA Exposure Attribution — Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `PASS_STRUCTURAL_ONLY`

## Purpose

This is a bounded, outcome-blind attribution of the existing counterfactual
price-basis sensitivity audit. It asks whether changed `(ticker, date)` rows
fall directly inside the 188-row unresolved non-stable-scale comparison
artifact or outside it as cross-sectional spillover.

This does **not** identify a unique causal path. `direct_row` means only that
the changed row key is present in the unresolved comparison artifact;
`spillover_row` means that it is absent. The comparison remains a
non-admitted counterfactual: no price-basis correction was promoted.

## Reproduction and scope

- Active regular rows: `981,940`; eligible rows: `310,761`; eligible tickers:
  `711`; sessions: `1,260`.
- Unresolved comparison artifact: `188` rows across `19` tickers and `70`
  dates.
- Baseline and counterfactual score reproduction: exact for C1, C2, and C4;
  maximum absolute difference to stored baseline scores was `0.0` on all
  finite compared rows.
- Panel and features were not mutated; the replacement occurred in memory.
- No target, forward return, incumbent score, provider, network, cloud,
  capture, telemetry, or canonical dataset was accessed or modified.

## Exact attribution

| Candidate | Direct score-changed / rank-changed | Spillover score-changed / rank-changed | Direct Top-30 slots / spillover slots | Mean Top-30 overlap | Min overlap | Changed Top-30 dates |
|---|---:|---:|---:|---:|---:|---:|
| C1 residual reversal 5 | `66 / 65` | `82,291 / 31,281` | `18 / 1,172` | `98.2618%` | `36.6667%` | `118` |
| C2 participation confirmation 5 | `66 / 65` | `457 / 8,929` | `38 / 96` | `99.8140%` | `83.3333%` | `35` |
| C4 path-efficiency reversal 20 | `66 / 62` | `319 / 9,877` | `12 / 52` | `99.9112%` | `86.6667%` | `20` |
| H-LIQ-01 diagnostic | `66 / 63` | `317 / 10,247` | `16 / 174` | `99.7363%` | `90.0000%` | `54` |

Additional exact score-change totals are C1 `82,357`, C2 `523`, C4 `385`,
and H-LIQ-01 `383`. The direct rows are the same 66 finite changed rows for
each candidate; the rest of the score-change totals are outside the unresolved
artifact and therefore classified as spillover under this preregistration.

## Interpretation

1. C1's aggregate sensitivity is dominated by cross-sectional spillover:
   `82,291/82,357` score-changed rows are outside the 188-row artifact. This
   is consistent with C1's market-relative return and prior-beta structure;
   it does not make C1 price-basis-safe.
2. C2 and C4 have smaller aggregate score-change counts, with the same direct
   unresolved rows contributing materially to their changed rows. Their rank
   and Top-30 sensitivity still includes spillover, so it cannot be reduced to
   only 188 isolated observations.
3. The result narrows the failure mode but does not resolve PIT, corporate
   action, issuer continuity, or historical price-basis authority.
4. Candidate dispositions do not change: C1/C2/C4 remain
   `FUTURE_RESEARCH` (C4 also `ECONOMIC_CAUTION`), and H-LIQ-01 remains
   `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5 was created.

## Provenance

- Code: `research/alpha_ca_exposure_attribution_v1.py`
- Code SHA-256: `6511be556ae0740db46b676d44511b7deab3cb24ddff7ff4be8b8cd7b560ebfb`
- Output: external staged `alpha_ca_exposure_attribution_v1.json`
- Output SHA-256: `432c6e99ec77fda6d352601969a8a17c435aa45744ca13f1a494e261bbc6d556`
- Repository head: `5ff846e43eceeb63631682a923d01970cdc15b66`
- Manifest SHA-256: `27f62ac509284a6497bfacf41fd1e34cc9e352ba49f0ca2006ff8160cacf3d96`
- Guarded features SHA-256: `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel SHA-256: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official sessions SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability anchors SHA-256: `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`
- Unresolved-scale source SHA-256: `eaedba187a3645a83c06c3885dac2c819e818fb68636cfedf2d32e7792432743`

## Safe continuation

The research lane is not globally blocked. Safe continuation is limited to
bounded audits of already-admitted local evidence, especially issuer/CA/PIT
source-admission and capacity clarification. Historical target evaluation,
OOS/IC/ICIR, incumbent comparison, new-provider scraping, canonical mutation,
and model promotion remain prohibited until independent Data QA admission.
