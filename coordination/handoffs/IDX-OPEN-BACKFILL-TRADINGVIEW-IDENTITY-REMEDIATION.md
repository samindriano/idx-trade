# Handoff

from: Codex
to: Independent ChatGPT review
task_id: IDX-OPEN-BACKFILL-TRADINGVIEW-IDENTITY-REMEDIATION
model_used: Codex direct executor
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `a8f4c2fb4c8be02405b5d00ce9272b91459daf9e`
branch: `data/idx-open-backfill-tradingview-identity-remediation-v1`
head_commit: `89b7540`

## scope

Executed only the frozen 2,877-row TradingView identity/provider remediation
audit. Offline identity evidence was evaluated first. One unchanged canonical
`IDX:SMBR` retry was performed because the preserved prior result was HTTP 520.
No alternate symbol was tested because no concrete historical/current alias
relationship was evidenced. No other provider, bucket, panel, derivative,
model, Ranking/PIT, or execution work was started.

## files_changed

- `src/idx_trade/tradingview_identity_remediation.py`
- `tests/test_tradingview_identity_remediation.py`
- `docs/checkpoints/2026-08-12_TRADINGVIEW_IDENTITY_PROVIDER_REMEDIATION_RUNTIME.md`
- `coordination/handoffs/IDX-OPEN-BACKFILL-TRADINGVIEW-IDENTITY-REMEDIATION.md`

## findings

- Frozen target: 2,877 rows; source SHA
  `1c05a53155ed52783f112f58babc363e4ee081180542be71a9dfa1bd3ba4c5cd`.
- Target tickers: FREN 952, MASA 717, MFIN 915, RMBA 65, SMBR 1, TURI 227.
- No explicit ticker aliases were found in preserved security-master,
  curated-identity, official Stock Summary, or ticker-history evidence.
- SMBR canonical retry returned HTTP 200 with 1,000 candles and produced one
  exact ticker/date + H/L/C + positive/in-range Open candidate on 2023-03-14.
- FREN, MASA, MFIN, RMBA, and TURI remain unresolved with their preserved
  prior provider-error evidence; no retries were made for them.
- Immutable panel SHA remained
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- Accepted Yahoo+TradingView derivative remained unchanged; see checkpoint
  for both file hashes.
- External artifact manifest SHA:
  `ace16c99a14cf805cf1b48b8407d7f8e6ab9d90116264d2267e12c39ed56d669`.

## decisions_made

- Keep exact request and admission contracts unchanged.
- Do not infer aliases from company-name variation.
- Preserve the single SMBR row as an external `TV_RECOVERY_CANDIDATE`; do not
  write it into the immutable panel or accepted derivative.
- Corrected only the response-shape reporting for the already-preserved raw
  SMBR payload offline: wrapper keys are `data`, `project`, `timestamp`; the
  unwrapped chart contains 1,000 candles and the expected chart identity.

## decisions_needed

- Independent review must decide whether the single external SMBR candidate is
  eligible for any separately authorized derivative application.
- No approval is implied for retrying the five 404 tickers, alternate symbols,
  bulk backfill, or execution-grade promotion.

## blocking_risks

- 2,876 of 2,877 target rows remain unresolved.
- No alternate-symbol relationship is evidenced for the five 404 tickers.
- A provider candidate is external evidence only until separately reviewed and
  authorized; panel and derivative immutability was preserved.

## validation_run

- Focused pytest: 10 passed.
- Full pytest: 271 passed; 6 existing `FutureWarning` locations; 0 failures.
- External raw and audit artifacts were preserved under the required D: drive
  runtime root; the API key was not printed, persisted, or committed.

## recommended_next_action

Stop for independent ChatGPT review. Do not start another provider, another
TradingView census, corporate-action repair, modelling, Ranking/PIT-sector
work, execution-grade promotion, or execution PnL.
