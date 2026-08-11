# Stockbit Intraday Forward Capture — Live Pilot Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Base implementation checkpoint: `05087440ba7597570cf0ff6817c36bf76ac8d99e`

## Decision

`STOCKBIT_INTRADAY_BOUNDED_LIVE_PILOT_AUTHORIZED`

The collector implementation is ready for local validation and a small live post-close pilot. This experiment is only to verify the actual Zapi Stockbit chart payload, identity/session semantics, whole-session behavior, artifact integrity, and request/quota cost. It does not authorize recurring 300–500 ticker capture yet.

## Scope

1. Pull/switch to this branch and verify worktree/HEAD.
2. Read `AGENTS.md`, the forward-capture spec, and the implementation checkpoint.
3. Run focused tests and full pytest before any live call.
4. Fix implementation-only defects if tests reveal them, without widening the scientific/data scope.
5. Run a bounded live pilot on exactly these 12 liquid IDX tickers:
   `BBCA, BBRI, BMRI, BBNI, TLKM, ASII, AMRT, ICBP, INDF, UNTR, ANTM, MDKA`.
6. One Stockbit chart request per ticker under the implemented whole-session contract; bounded transient retry only.
7. The live run must occur after the collector's complete-session gate. Do not use `--allow-partial-session` for this pilot.

## Required validation

For each ticker report:
- request success/error status;
- returned provider identity/symbol;
- provider trading date/session date;
- first/last timestamp;
- point count;
- timestamp monotonicity and duplicate diagnostics;
- returned field schema;
- null/invalid point diagnostics;
- whether the session appears complete under the provider response contract;
- raw payload and normalized artifact hashes.

Across the pilot report:
- exact ticker set and deterministic ticker-list hash;
- requests/retries/429/errors;
- quota before/after from safe headers;
- successful ticker count;
- any stale/multi-session/identity/contract rejection;
- normalized row count;
- earliest/latest intraday timestamps observed;
- artifact manifest SHA;
- focused/full pytest results.

## Hard boundaries

- API key only from `ZAPI_API_KEY`; never print/persist/commit it.
- Do not call Open/TradingView census code from this branch.
- Do not touch PIT-sector work.
- Do not start recurring automation/capture.
- Do not expand beyond 12 tickers in this pilot.
- Do not synthesize OHLCV or fill missing minutes.
- Treat Stockbit chart as intraday price-path evidence only unless the live payload proves additional fields exist.
- Do not create alpha/path-risk/execution features yet.
- Preserve raw payloads outside Git in a new immutable artifact root.

## Stop gate

After the 12-ticker pilot, write a factual dated runtime checkpoint, push fast-forward, report remote HEAD and key metrics, then STOP for independent ChatGPT review before any recurring-universe authorization.
