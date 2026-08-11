# Yahoo Census Residual Breakdown — Diagnostic Result

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/idx-open-backfill-yahoo-census-v1`  
HEAD: `12a84e50597557ded2f5c3a6c0d5645d7a308e2b`

## Scope and decision

This is an offline diagnostic of the completed Yahoo Open census. It did not
refetch Yahoo, modify the immutable panel, promote execution-grade data,
change Ranking V1/V2, run Stage 5, or start modelling.

Residual is defined deterministically as a row where the immutable panel
`Open` is null and neither `direct_admissible` nor `split_admissible` is true.

Decision: **NO strict full-universe usable window is established.** The 2024
slice has the best broad candidate completeness, but residuals remain and the
result is diagnostic only.

## Immutable inputs

- Panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- Panel rows/tickers: `981,940` / `945`
- Panel dates: `2021-04-29` through `2026-07-31`
- Panel SHA-256 before/after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- Initial missing Open: `446,843`
- Residual Open: `49,476` rows / `669` tickers

## Residual breakdown

| class | rows | tickers | share | interpretation |
|---|---:|---:|---:|---|
| `PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR` | 32,103 | 624 | 64.886% | Provider row exists, but H/L/C is not exact and no usable official split factor is available. Not proven to be a corporate action. |
| `CORPORATE_ACTION_ADJACENT_INCOMPLETE_OFFICIAL_EVIDENCE` | 8,804 | 14 | 17.794% | H/L/C mismatch adjacent to an official-action period whose evidence is incomplete; no reconstruction admitted. |
| `NO_PROVIDER_ROW` | 3,840 | 53 | 7.761% | No Yahoo row for the ticker/date, excluding the five ticker-level provider errors below. |
| `PROVIDER_ERROR_OR_SYMBOL_RESOLUTION_FAILURE` | 2,876 | 5 | 5.813% | Yahoo returned no row after repeated provider diagnostics: `FREN`, `MASA`, `MFIN`, `RMBA`, `TURI`. This is a provider/symbol-resolution blocker, not an identity conclusion. |
| `CORPORATE_ACTION_SCALE_MISMATCH_VERIFIED_FACTOR_FAILED` | 1,853 | 14 | 3.745% | An official cumulative factor existed, but reconstructed H/L/C was still not exact; no fill admitted. |

The raw rejection histogram is `HLC_MISMATCH_* = 42,760` rows
(`HIGH 42,200`, `LOW 346`, `CLOSE 214`) and `NO_PROVIDER_ROW = 6,716`.

Provider/identity and corporate-action classes are therefore separated. The
32,103-row no-factor H/L/C class remains an unresolved provider-vs-scale
diagnostic; it is not relabelled as a corporate-action mismatch without
independent evidence.

## Ticker concentration

The largest residual tickers are:

| ticker | residual rows | dominant class |
|---|---:|---|
| RISE | 953 | provider H/L/C mismatch, no verified split factor |
| FREN | 952 | provider/symbol-resolution failure; unresolved PIT identity |
| MEGA | 949 | provider H/L/C mismatch, no verified split factor |
| SPMA | 928 | provider H/L/C mismatch, no verified split factor |
| MFIN | 915 | provider/symbol-resolution failure |
| BEEF | 896 | provider H/L/C mismatch, no verified split factor |
| CLEO | 875 | provider H/L/C mismatch, no verified split factor |
| KEJU | 873 | provider H/L/C mismatch, no verified split factor |
| UFOE | 858 | provider H/L/C mismatch, no verified split factor |
| WGSH | 840 | provider H/L/C mismatch, no verified split factor |

Concentration by rank: top 5 = `4,697` rows / `9.4935%`; top 10 =
`9,039` / `18.2695%`; top 20 = `16,737` / `33.8285%`; top 50 =
`32,797` / `66.2887%`; top 100 = `46,318` / `93.6171%`.

Provider error residuals by ticker are `FREN 952`, `MFIN 915`, `MASA 717`,
`TURI 227`, and `RMBA 65`. The largest verified-factor reconstruction
failures are `MLPT 781`, `DSSA 422`, `RAJA 288`, and `RMKE 145`. The largest
incomplete-action groups are `MSIN 820`, `KDSI 800`, `ALDO 767`, `INDS 754`,
and `PBID 743`.

## PIT and tradability cross-check

The immutable census panel was treated as the existing PIT/tradable-universe
baseline. Yahoo row presence was not used to infer `ACTIVE`. The security
master was used only for listing-interval consistency, and the merged legal
interval file was used only to detect known suspension overlap.

- Panel tickers missing from `security_master.csv`: `FREN` only.
- Panel rows missing a security-master identity: `952`.
- Residual rows missing a security-master identity: `952` (`FREN`,
  `2021-04-29` through `2025-04-14`).
- Panel rows outside a listing interval: `953`.
- Residual rows outside a listing interval: `952` (the FREN rows).
- Residual rows overlapping a known legal suspension interval: `0`.
- Residual rows inside a listing interval and without known suspension overlap:
  `48,524`.

The one additional panel row outside a listing interval is `KOCI` on
`2023-10-06`; it was a direct-admissible Open row and is not a residual. Its
security master `listed_from` is `2023-10-07`, so it remains a separate PIT
boundary inconsistency to reconcile before any certification claim.

## Candidate window diagnostics

Candidate completeness means original non-null Open plus admitted direct or
verified split-scale candidate Open. `strict_full_window_usable` requires zero
residual rows; no inference is made from a high percentage.

| window | panel rows | tickers | residual | candidate Open complete | clean tickers / total | strict |
|---|---:|---:|---:|---:|---:|---|
| 2022 | 174,888 | 777 | 16,290 | 90.6855% | 644 / 777 | NO |
| 2023 | 185,138 | 856 | 11,035 | 94.0396% | 418 / 856 | NO |
| 2024 | 196,046 | 891 | 6,830 | 96.5161% | 450 / 891 | NO |
| 2022 → 2026-07-31 | 870,308 | 938 | 34,783 | 96.0034% | 283 / 938 | NO |
| 2023 → 2026-07-31 | 695,420 | 932 | 18,493 | 97.3407% | 297 / 932 | NO |
| 2024 → 2026-07-31 | 510,282 | 925 | 7,458 | 98.5385% | 479 / 925 | NO |

The clean-ticker counts are a diagnostic subset only; removing residual
tickers would change the universe contract and was not done.

## External diagnostic artifacts

All runtime diagnostics remain outside Git under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

- `residual_open_detail.csv` SHA-256:
  `26cd2319991aa5dc2fcce78d7f256f31fb1762b4510c0623fcd16fb87b66fd02`
- `residual_by_ticker_year_reason.csv` SHA-256:
  `7da614086b548ea47d4e7227e20697516993aa3c326cfb9a14dad56f620e6bf2`
- `residual_ticker_concentration.csv` SHA-256:
  `c41b764050850099a243827044b6673d0976c94cf735a53d85da71dd8760eef0`
- `residual_problem_class_summary.csv` SHA-256:
  `d5cf300f2a56ca11f32d81d3ea1a0fd2d86ca3e6935c5ed704d01bc8aa6d4b8b`
- `residual_pit_tradability_crosscheck.csv` SHA-256:
  `f5518b63f835e682b46bfcf6161deabfbcae32060203557806f299dcb4f9fcf5`
- `candidate_window_diagnostics.csv` SHA-256:
  `b7715117a58f0deadfae33163d284451d8ca01aae47f7340389445fafc42dd7d`
- `residual_diagnostic_summary.json` SHA-256:
  `2905caf64e810cb64fe675e0580f60aff5ef530974613a13ecc5daeca1f41ed5`
- artifact manifest SHA-256:
  `1f305f16ffa52a537251db119032834cc9cff80a72524a389efc12e267366586`

## Validation and stop condition

- No source or test code changed.
- The prior full pytest result remains `236 passed, 3 warnings`; a new test run
  was not necessary for this external-artifact-only diagnostic.
- Immutable panel SHA before/after is unchanged.
- No model, Stage 5, execution-grade promotion, or downstream validation was
  started.

Stop for independent ChatGPT review. The next safe action is evidence repair
for FREN/KOCI PIT identity boundaries and separately scoped investigation of
the no-factor H/L/C mismatch class; do not silently promote this candidate.
