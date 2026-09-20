# Candidate Era and Authority Dependency Census V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_MAP_ONLY / NO ERA OR POLICY ADMITTED`

## Question

Can natural calendar-year support strata and candidate-specific formula
dependencies narrow the authority surface without selecting an era, changing
the eligibility policy, or opening protected predictive outcomes?

## Scope and boundary

This is an outcome-blind descriptive census over the frozen Stage-A feature
artifact, official session calendar, structural panel keys, and regular-market
tradability anchors. It reads no target, forward return, IC/ICIR, OOS, PnL,
incumbent result, provider, cloud, capture, telemetry, or production state.

No candidate status, population, eligibility policy, or era was selected. The
protected boundary remains closed.

## Result

The calendar covers 1,260 official sessions from `2021-04-29` through
`2026-07-31`.

| Candidate | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 partial | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| C1 | 48.4942% | 99.5817% | 99.4769% | 99.5731% | 99.5522% | 99.4217% | Broad finite support from 2022; 2021 is warm-up-limited |
| C2 | 100.0000% | 100.0000% | 100.0000% | 100.0000% | 100.0000% | 100.0000% | Broad structural support across all observed years |
| C3 | 0% | 0% | 0% | 0% | 22.6348% | 39.4084% | Financial capability island beginning 2025-04-25 |
| C4 | 99.9600% | 99.8371% | 99.7546% | 99.8589% | 99.9135% | 99.8951% | Broad finite support across all observed years |

C3's first finite date is `2025-04-25`; its latest finite date is
`2026-07-17`. This confirms a timing/capability boundary, not a predictive
failure or a reason to impute or backfill financial values.

## Panel versus active-anchor boundary

- Structural panel: `981,940` rows and `945` tickers.
- ACTIVE regular-market anchors: `982,398` rows.
- Panel keys with an ACTIVE anchor: `981,940`.
- Panel keys with a NO_TRADE anchor: `0`.
- Panel keys without an ACTIVE anchor: `0`.
- ACTIVE anchor rows absent from the panel: `458`, all in 2021–2024
  (`150 + 217 + 80 + 11`).

Thus every observed panel key overlaps an ACTIVE anchor in this artifact pair,
but the extra ACTIVE-anchor rows show that panel coverage and anchor coverage
are not identical. This is structural overlap evidence only; it does not prove
population completeness, delisted/relisted handling, ticker reuse, or issuer
continuity.

## Candidate-specific authority dependencies

| Candidate | Direct formula inputs | Candidate-specific authority gates |
|---|---|---|
| C1 | Close, regular market value, eligibility mask, official sessions | Eligibility policy, PIT population, issuer/security identity, CA price basis, executable capacity |
| C2 | Close, volume, regular market value, eligibility mask, official sessions | All C1 gates plus price/volume basis, historical liquidity semantics, executable capacity |
| C3 | Five financial values, reporting knowledge time, period date, bundle provenance, eligibility mask | PIT population, identity, publication/available-at timing, revision/vintage semantics, eligibility policy |
| C4 | Close, regular market value, eligibility mask, official sessions | Eligibility policy, PIT population, issuer/security identity, CA price basis, executable capacity |

C1/C4 do not directly consume the financial bundle, although their upstream
eligibility mask still depends on liquidity/active-anchor semantics. C3 does
not directly consume close or volume, but inherits that same upstream mask.

## Adjudication

| Gate | Result |
|---|---|
| Calendar-year support map | `PASS_STRUCTURAL_ONLY` |
| Candidate-specific dependency map | `PASS_STRUCTURAL_ONLY` |
| Era admission | `NO` |
| Eligibility policy selection | `NO` |
| Candidate status change | `NO` |
| Population/PIT/identity/CA authority | `UNKNOWN / BLOCKED` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |

The global admission block can be decomposed by candidate, but it cannot be
removed merely because C1/C2/C4 have broad structural support. C3's late
support is a concrete capability constraint, not evidence that a restricted
era should be selected. The 458-row anchor surplus must not be interpreted as
missing listings or survivorship evidence without lifecycle authority.

## Reproducibility

- Code: `research/alpha_candidate_era_authority_v1.py`
- Code SHA-256:
  `1952850c517a8a6126b10d8f51f29594ef56aa93aec53550466dc139723dae06`
- Result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_candidate_era_authority_v1.json`
- Result SHA-256:
  `16d0455d9579ab837ed83774a59f07e6c595aa87a6dc66b5ec722932d7a87457`
- Focused tests: `2/2` passing.
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Panel input SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Tradability-anchor input SHA-256:
  `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e`

All output remained in the isolated staging root. No canonical, incumbent,
cloud, capture, telemetry, scheduler, or production artifact was modified.
