# Zapi TradingView + Investing Open Audit — Implementation Checkpoint

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`

## Status

**`ZAPI_ALT_ENDPOINTS_AUDIT_IMPLEMENTED_LOCAL_VALIDATION_REQUIRED`**

A bounded runtime for the currently documented Zapi TradingView chart and Investing historical endpoints is implemented under the frozen spec:

`docs/OPEN_BACKFILL_ZAPI_ALT_ENDPOINTS_AUDIT_V1.md`

No provider runtime has been executed from this branch yet.

## Historical-documentation finding

Searches across repository files, branches, and commits found no persisted historical IDX-Trade artifact explicitly documenting an older Investing.com/investpy or TradingView Open-backfill experiment. Cross-chat context retrieval also did not recover a factual old rejection reason. The user's memory of an older attempt is therefore preserved as an undocumented prior attempt, not treated as evidence of source acceptance or rejection.

## Why these endpoints remain worth a bounded test

Current Zapi documentation differs materially from the already-rejected IDX stock-summary endpoint:

- TradingView chart explicitly returns daily OHLCV for `IDX:<ticker>` / `market=indonesia`, with up to 1000 candles per request;
- Investing historical explicitly returns OHLCV with `period=max`, and allows an internal `pairId` obtained through a separate search/identity step.

The runner therefore tests endpoint-specific semantics rather than reopening the rejected `finance:idx/stock-summary` result.

## Implemented safety boundaries

- exact prior 240-row sample manifest is reused and SHA-gated;
- no sample reselection;
- TradingView symbol must resolve exactly to `IDX:<ticker>`, `exchange=IDX`, `market=indonesia`;
- Investing must have exactly one defensible Indonesian identity candidate before historical data is requested;
- TradingView uses `1D`, `count=1000`;
- Investing uses verified `pairId`, `1d`, `period=max`, `pointscount=1500`;
- provider timestamps are converted to Asia/Jakarta session dates before exact matching;
- exact panel H/L/C + finite positive in-range Open remains mandatory;
- dates outside a successful provider history range are separated as history-window limitations rather than price-semantic failures;
- no panel modification or Open fill is performed;
- no network parallelism or quota bypass.

## Local validation required before runtime

Codex/local runner must:

1. fetch this branch and verify clean remote alignment;
2. verify `ZAPI_API_KEY` visibility without printing it;
3. run `pytest -q tests/test_zapi_alt_open_audit.py`;
4. run full `pytest`;
5. if tests expose a concrete wiring/runtime bug, apply only the smallest semantics-preserving fix and rerun tests;
6. only then execute the frozen bounded runtime;
7. write factual runtime checkpoint and stop for ChatGPT review.

No full-universe TradingView/Investing backfill is authorized.
