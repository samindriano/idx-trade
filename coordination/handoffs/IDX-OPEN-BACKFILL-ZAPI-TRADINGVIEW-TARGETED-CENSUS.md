# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-OPEN-BACKFILL-ZAPI-TRADINGVIEW-TARGETED-CENSUS-V1
model_used: Luna xhigh root, direct one-writer execution
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `1510585f6a11c52411edb47f08127b9ee3525685`
branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
head_commit: `dadc016`
scope: Frozen 38,819-row non-corporate-action Zapi TradingView census; reuse preserved cache first; fetch only 459 unique tickers lacking preserved usable chart responses.
files_changed: `src/idx_trade/zapi_tradingview_targeted_census.py`, `tests/test_zapi_tradingview_targeted_census.py`, `docs/checkpoints/2026-08-11_ZAPI_TRADINGVIEW_TARGETED_CENSUS_RUNTIME.md`

## Findings

- The authorized input was 38,819 rows from 49,476 residual rows; 10,657
  corporate-action rows were excluded.
- Preserved cache reuse covered 112 tickers fully and 66 partially before
  network. No prior successful ticker was refetched.
- 459 new unique tickers were requested under the unchanged
  `IDX:<ticker>`, Indonesia, 1D, 1000-candle contract.
- 458 new tickers succeeded; SMBR returned HTTP 520. The five preserved error
  tickers FREN, MASA, MFIN, RMBA, and TURI were not retried.
- Final audit: exact date coverage 23,240/38,819; exact certified H/L/C
  5,675/38,819; admissible Open candidates 5,675/38,819; unresolved 33,144.
- Candidate recovery: 3,664 `NO_PROVIDER_ROW`, 2,011
  `PROVIDER_HLC_MISMATCH_NO_VERIFIED_SPLIT_FACTOR`; no corporate-action rows.
- Immutable panel SHA stayed
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Decisions made

- No panel write or execution-grade promotion.
- No alternate symbol mapping, pagination, Investing, stock-history Open
  recovery, corporate-action repair, modelling, Ranking, or execution work.
- The 5,675 candidates remain counterfactual evidence only.

## Blocking risks

- 12,702 rows are outside the returned 1000-candle history window.
- 17,565 rows remain exact H/L/C disagreements.
- 2,877 rows remain identity/provider-error classified; final error tickers are
  FREN, MASA, MFIN, RMBA, SMBR, and TURI.
- Post-run quota probe was unavailable because the remote closed the connection;
  preflight Pro headers were confirmed.

## Validation

- Focused census tests: 5 passed.
- Full pytest: 263 passed; only the repository's existing 3 FutureWarning
  locations were reported.
- Runtime artifact manifest SHA-256:
  `d0f5899310f9bf37d9f2f726be440fa11a8dcbf7de6703dde068a18009290bf1`.
- External artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_targeted_census_v1_20260811`.

recommended_next_action: Independent ChatGPT review of the frozen evidence; do not start panel approval or the full residual census without a new authorization.
