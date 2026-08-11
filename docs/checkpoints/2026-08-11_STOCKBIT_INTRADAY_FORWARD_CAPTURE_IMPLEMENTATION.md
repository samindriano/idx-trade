# Stockbit Intraday Forward Capture — Implementation Checkpoint

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Base: `dda3cb1ca7ed455e1cb932c093639723e4d3ea82`
Status: `IMPLEMENTED_NOT_LIVE_RUN`

## Implemented

Added `src/idx_trade/stockbit_intraday_capture.py` as an isolated forward collector for Zapi Stockbit chart data.

The collector:

- accepts explicit ticker lists/files;
- defaults to dry-run and requires `--execute` for network calls;
- reads the secret only from `ZAPI_API_KEY`;
- requests `finance:stockbit/chart` with `symbol=<ticker>` and deliberately omits `count` to request the whole documented session;
- has bounded request/retry behavior and records safe quota headers;
- defaults to a 500-request run ceiling;
- blocks complete-session capture before 16:15 Asia/Jakarta unless `--allow-partial-session` is explicit;
- defaults the expected provider session to the current Asia/Jakarta date;
- rejects stale/non-current sessions, identity/contract mismatches, multi-session payloads, trading-date metadata mismatches, invalid points, and conflicting duplicate timestamps;
- never fills missing minutes or synthesizes minute OHLC/volume fields;
- preserves successful raw payloads and normalized price-path rows in a new immutable artifact root;
- writes ticker statuses, run summary, and SHA-256 artifact manifest.

The normalized provider fields are limited to evidence actually returned by the documented Stockbit chart contract: minute timestamp, price, change, changePercent, and session-level previousClose plus provenance metadata.

## Offline tests authored

Added `tests/test_stockbit_intraday_capture.py` covering:

- ticker normalization/deduplication;
- exact current-session parsing;
- explicit partial-session status;
- stale-session rejection;
- exact identity contract;
- conflicting duplicate timestamp rejection;
- before-close fail-closed gate;
- request-budget guard;
- proof that the chart request omits `count` and therefore does not intentionally truncate the session.

No billable Stockbit request was made as part of this implementation checkpoint. A Codex/local pytest run and bounded live pilot remain separate steps.

## Next gate

1. run focused and full pytest on this branch;
2. fix implementation-only defects if needed without widening scope;
3. independently review the diff;
4. separately authorize a small live pilot (suggested 10–20 liquid tickers, one post-close call each);
5. only after pilot review freeze the recurring universe size (e.g. selective 300–500 vs full universe).

Historical Open recovery remains independent and untouched.
