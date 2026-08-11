# Handoff: Foreign Flow V1 Source Audit

from: Codex
to: ChatGPT reviewer
task_id: IDX-FOREIGN-FLOW-V1-SOURCE-AUDIT
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `de9346bdf42a219358b3ac6da74f4c490da9c04f`
branch: `data/foreign-flow-v1`
scope: bounded official IDX/Zapi foreign-flow source audit only

## Files changed

- `src/idx_trade/foreign_flow.py` — minimal validation-order fix only.
- `docs/checkpoints/2026-08-12_FOREIGN_FLOW_V1_SOURCE_AUDIT.md`
- `coordination/handoffs/IDX-FOREIGN-FLOW-V1-SOURCE-AUDIT.md`

No contract redesign, feature work, model work, outcome access, or other data-lane changes.

## Source resolution

- Zapi wrapper: `GET /v1/finance:idx/foreign-flow`.
- Zapi raw path: `TradingSummary/GetStockSummary` through `/v1/finance:idx/raw`.
- Direct official endpoint: `https://www.idx.co.id/primary/TradingSummary/GetStockSummary`.
- Wrapper fields `foreignBuyShares`, `foreignSellShares`, `netForeignShares` map to official `ForeignBuy`, `ForeignSell`, and buy-minus-sell.
- Unit: `SHARES`; no lots/IDR conversion.

## Six-session result

Sessions: 2021-01-04, 2022-06-24, 2023-06-22, 2024-06-21, 2025-06-30, 2026-07-31.

Rows per session: 717, 790, 871, 930, 960, 963 respectively.

For every session: wrapper rows = Stock Summary rows = raw rows = direct official rows; duplicate count 0; ticker-set difference 0; net identity errors 0; direct foreign-field mismatches 0; checked raw fields (`Date`, `StockCode`, `ForeignBuy`, `ForeignSell`, `Volume`, `Value`, `Frequency`) had 0 mismatches.

Zero foreign-flow rows ranged 304–438. Zero-volume rows ranged 81–133. Therefore zero flow is not equivalent to no trade; missing future rows remain unknown.

## PIT and revision result

- Official rows have session date but no publication/update timestamp.
- Zapi top-level timestamp is access time, not source publication time.
- Repeated 2022-06-24 wrapper first page and raw full snapshot were byte-stable in two captures.
- This does not prove immutable historical values or first-knowable timing.
- In-memory contract smoke passed with capture-time upper bounds as `knowledge_at`; no `published_at` was claimed.

## Tests

- Focused: `python -m pytest tests/test_foreign_flow.py -q` → **7 passed**.
- Full: `python -m pytest -q -rA` → **478 passed, 0 failed, 3 warnings, 30.86s**.

## Decision

`SOURCE_AND_UNIT_USABLE_BUT_PIT_TIMING_UNRESOLVED_COVERAGE_INCOMPLETE`.

Source discovery and unit semantics pass. Exact historical PIT timing, market-wide historical completeness, and bulk-acquisition readiness do not pass. Keep raw captures outside Git at `D:\Documents\Project\idx-trade-foreign-flow-20260812`; the Zapi API key was read only from `ZAPI_API_KEY` and was not persisted.

Recommended next action: ChatGPT review should decide whether to authorize a separate capture-time diagnostic lane or require an official IDX timing/release source before any PIT acquisition.
