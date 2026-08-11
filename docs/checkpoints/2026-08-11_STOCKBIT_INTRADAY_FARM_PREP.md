# Stockbit Intraday Farm Preparation Checkpoint

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Status: `IMPLEMENTED_AWAITING_LOCAL_TEST_AND_BROAD_RUN`

## Reason for this implementation step

The 12-ticker live pilot proved the endpoint and parser, but the pilot collector was intentionally bounded and not designed as a resilient ~full-universe daily farm. Before widening network scope, two infrastructure gaps were addressed:

1. exact per-day capture-universe freezing/provenance;
2. crash-safe resumability so a partial large run does not require refetching successful tickers.

## Added

### `src/idx_trade/stockbit_intraday_universe.py`

- deterministic ticker-list SHA-256;
- as-of-date active listing snapshot helper from a certified security master;
- immutable universe CSV + metadata freeze utility;
- input source hashes.

### `src/idx_trade/stockbit_intraday_farm.py`

- official current IDX active-stock list as the default forward-capture universe source;
- exact frozen day universe and ticker hash;
- per-ticker atomic raw/rows/status artifacts;
- restart/resume semantics;
- successful tickers are skipped on resume;
- explicit optional error retry rather than silent refetch;
- today-only expected-date gate;
- post-close complete-session gate;
- configurable max-new-ticker ceiling (default 1,200);
- configurable monthly quota reserve (default 3,000);
- quota-reserve stop remains resumable;
- consolidated day outputs and recursive manifest.

### `tests/test_stockbit_intraday_farm.py`

Offline tests were authored for:

- current universe canonicalization;
- duplicate ticker fail-closed behavior;
- frozen-universe hash tampering;
- pending/resume semantics;
- proof that successful tickers are not refetched;
- clean quota-reserve stopping;
- today-only date protection;
- final summary/manifest consistency.

These new tests have not yet been executed in the GitHub-only implementation environment. Local Codex execution is required before the broad run and is authorized to fix implementation-only defects exposed by the tests.

## Next authorized action

Follow `docs/checkpoints/2026-08-11_STOCKBIT_INTRADAY_BROAD_CENSUS_SPEC.md`.

Because the Stockbit contract is `timeframe=today`, the 2026-08-11 broad census is time-sensitive. If the provider has already rolled to another session date, fail closed rather than changing the frozen expected date.
