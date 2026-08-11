# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-OPEN-BACKFILL-ZAPI-TRADINGVIEW-DERIVATIVE-APPLICATION-V1
model_used: Luna xhigh root, direct one-writer execution
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `9ffa1b9738f8fc77bd8fb8b29e3aed42ad6cd941`
branch: `data/idx-open-backfill-zapi-tradingview-targeted-census-v1`
head_commit: `4558d2998f4bc9ce5f71c717bb96639cb26db4ba` (application commit; this handoff metadata is the subsequent docs-only publication)
scope: Apply exactly 5,675 independently accepted non-corporate-action TradingView Open candidates to the accepted Yahoo derivative, preserving existing non-null Open values and row-level provenance.
files_changed: `src/idx_trade/zapi_tradingview_derivative.py`, `tests/test_zapi_tradingview_derivative.py`, `docs/checkpoints/2026-08-11_ZAPI_TRADINGVIEW_DERIVATIVE_APPLICATION_RUNTIME.md`, `coordination/handoffs/IDX-OPEN-BACKFILL-ZAPI-TRADINGVIEW-DERIVATIVE.md`

## Findings

- The derivative application filled exactly 5,675 additional null Open values.
- Existing non-null Open values overwritten: 0.
- Yahoo derivative null Open decreased from 49,476 to 43,801.
- All 5,675 applied rows carry `ZAPI_TRADINGVIEW` canonical provenance and
  preserved TradingView census/source fields.
- Non-candidate Yahoo provenance rows were unchanged.
- The immutable certified panel remained unchanged at SHA-256
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- Open coverage increased from 932,464 / 981,940 (94.9614%) to 938,139 /
  981,940 (95.5393%).
- Remaining null Open values are 33,144 non-corporate-action residuals plus
  10,657 corporate-action residuals.

## Decisions made

- Used the accepted Yahoo derivative as the only base.
- Applied only the already authorized 5,675 TradingView candidates.
- Kept `execution_grade_promoted=false`.
- Did not start another provider, corporate-action repair, panel write,
  modelling, Ranking/PIT-sector work, or execution PnL.

## Blocking risks

- The derivative remains research evidence, not execution-grade data.
- 43,801 Open values remain unresolved, including 10,657 corporate-action
  residuals.
- No claim of execution-PnL readiness is supported.

## Validation

- Focused derivative tests: **3 passed**.
- Full pytest: **266 passed**.
- External artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_tradingview_derivative_v1_20260811`.
- Derivative panel SHA-256:
  `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab`.
- Derivative provenance SHA-256:
  `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687`.
- Artifact manifest SHA-256:
  `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14`.

recommended_next_action: Independently review the factual checkpoint and external manifest. Do not authorize further data-source work or execution-grade promotion from this derivative alone.
