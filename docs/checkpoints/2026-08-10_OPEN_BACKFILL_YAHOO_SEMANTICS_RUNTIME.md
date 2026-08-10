# Yahoo Historical Open Semantics + Broad Coverage Audit — Runtime

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-semantics-v1`
Implementation commit: `6cc3c35`

## Decision

**`OPEN_BACKFILL_YAHOO_SEMANTICS_AUDIT_COMPLETE_STOP_FOR_INDEPENDENT_REVIEW`**

This was the separately authorized bounded Yahoo semantics and broad-coverage
audit only. It does not authorize bulk Open backfill, execution-grade
promotion, execution-PnL analysis, modelling, Stage 5, Ranking V2 changes,
paper/live trading, or a merge to `main`.

## Immutable panel and baseline

- input panel:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`
- SHA-256 before runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- SHA-256 after runtime:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- baseline unresolved Open rows: `446,843`
- existing non-null Open values were not modified
- `execution_grade_promoted=false`

## Deterministic sample

The sample was selected from the immutable panel, preserved Wildan
diagnostics, official 1260-session split/reverse-split evidence, security
master, and tradability evidence before Yahoo was queried.

- fixed seed: `20260810`
- rows: `300`
- unique tickers: `270`
- sample SHA-256:
  `fc5a6f73e36ddf4ab2e52e3dcce82f310379ff54b4d4ff0c01990f8a575c0147`
- role counts:
  - known existing Open: `172`
  - missing Open with Wildan row: `103`
  - missing Open with no Wildan row: `25`
- official split-evidence stratum: `52` tickers / `69` rows
- non-split stratum: `218` tickers / `231` rows
- temporal strata: early `82`, mid `85`, late `133`
- required names FREN, MASA, MFIN, BBCA, BBRI were retained where present
- sample selection is provider-outcome-independent: `true`

## Yahoo / yfinance audit

Yahoo was queried with raw OHLC semantics through `auto_adjust=False`.
`Adj Close`, dividends, and vendor adjustment fields were retained separately
and were never used as execution prices.

- access status: `YAHOO_YFINANCE_ATTEMPTED`
- credential/plan status: `NOT_APPLICABLE / PERSONAL_RESEARCH_ONLY_UNOFFICIAL`
- requests: `270` ticker-bounded requests
- provider rows returned: `12,028`
- unique tickers returned: `266 / 270` (`98.5185%`)
- exact sample ticker/date rows: `296 / 300`
- direct raw H/L/C exact: `280 / 296` (`94.5946%`)
- direct known-Open exact: `170 / 172` (`98.8372%`)
- direct admissible missing-Open rows: `110 / 128`
- duplicate provider keys: `0`
- adjusted/raw separation: `true`

Direct rejection diagnostics:

- `EXISTING_OPEN_PRESERVED`: `170`
- `FROZEN_CONTRACT_PASS`: `110`
- `HLC_MISMATCH`: `2`
- `HLC_MISMATCH_HIGH`: `14`
- `NO_PROVIDER_ROW`: `4`

Provider errors/gaps were retained explicitly:

- FREN: `YFTzMissingError` / no timezone
- MASA: HTTP 404 plus `YFTzMissingError` / no timezone
- MFIN: `YFTzMissingError` / no timezone
- PURE: `YFPricesMissingError` / no price data for the sampled date

Named provider result:

- FREN: sampled, `0` provider rows, `0` direct admissible, `0`
  split-reconstructed admissible
- MASA: sampled, `0` provider rows, `0` direct admissible, `0`
  split-reconstructed admissible
- MFIN: sampled, `0` provider rows, `0` direct admissible, `0`
  split-reconstructed admissible

## Split-scale diagnostic

Factors came only from the pre-existing authoritative IDX 1260-session
Stock Split / Reverse Stock artifact. No factor was fitted from Yahoo ratios.
One cumulative factor had to transform Open/High/Low/Close consistently, and
transformed H/L/C still had to equal the certified panel exactly.

- direct split-scale mismatches: `16`
- rows with an official factor available: `297`
- independently verified reconstructable rows: `4`
- reconstructed H/L/C exact: `4`
- reconstructed known-Open exact: `2`
- reconstructed admissible missing-Open: `2`
- official-vs-Yahoo split cross-check: `39 MATCH`, `0 MISMATCH`, `4 YAHOO_ONLY`

The exact reconstructed rows were BBCA `2021-08-03`, CUAN `2024-12-12`, and
SAMF `2021-09-17` plus `2023-02-03`. BBCA's official factor was `5`; CUAN's
was `10`; SAMF's was `2`. Existing Open rows remained preserved and were not
admitted as replacements. The two SAMF rows were missing-Open rows admissible
only under the separately classified
`SPLIT_SCALE_RECONSTRUCTABLE_EVIDENCE` path.

## Early / mid / late coverage

| stratum | sample rows | returned | direct H/L/C exact |
|---|---:|---:|---:|
| early | 82 | 79 | 71 |
| mid | 85 | 84 | 77 |
| late | 133 | 133 | 132 |

No potential-recovery estimate was extrapolated to the 446,843-row gap because
the sample was deliberately stratified by split evidence, Open role, edge
cases, and date. Existing Open rows remain immutable and no panel derivative
was written.

## Runtime artifacts

All artifacts remain outside Git at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_semantics_v1_20260810`

Artifact SHA-256:

- `audit_summary.json`: `eabadd4e38234deeba78e77e41c8b7c6e73cb89aaef457716f1aeba54c307bfe`
- `yahoo_candidate_rows.csv`: `31034c018c7b95234cced87af35755808fe6bea8f134580934662472f10affb7`
- `yahoo_semantics_row_audit.csv`: `55a1dc3cb18115cd3029100b6d9440655613cb83f1d587fca7c1a1e558a79352`
- `yahoo_semantics_sample_manifest.csv`: `fc5a6f73e36ddf4ab2e52e3dcce82f310379ff54b4d4ff0c01990f8a575c0147`
- `yahoo_semantics_sample_manifest.json`: `12233d56b6a292706dd84ca1b475a6fd5bbe9dcce6db27a1021a13fde8105dc4`
- `yahoo_semantics_summary.json`: `ea85aab2f40d69cf509244893d8886218aae3167e96e8c3c086e94085b4713c5`
- `yahoo_split_cross_check.csv`: `29ab71a7b9b8467663cdcf88eca91180b04178b5dc83a245f9716f1680ed4f96`
- `artifact_manifest.json`: `bcfad37fe38f0983f60ba5fd86319ee24a6bacc031441f0ab4bdac18a09d5783`

## Validation and stop boundary

- full pytest before implementation: `226 passed, 3 warnings`
- focused new/related tests: `12 passed`
- full pytest after final implementation: `229 passed, 3 warnings`
- no runtime artifact or immutable panel was added to Git
- stop for independent ChatGPT review before any bulk write
