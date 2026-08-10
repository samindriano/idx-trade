# Yahoo Full-Universe Historical Open Census — Implementation Ready

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-yahoo-census-v1`

## Decision

**`YAHOO_CENSUS_IMPLEMENTATION_READY_LOCAL_RUNTIME_REQUIRED`**

ChatGPT implemented the full-universe Yahoo historical Open recovery census in GitHub. The remaining task is local runtime execution against the immutable 1260-session panel and the previously used authoritative split/reverse-split evidence on the user's Windows machine.

Codex is now a local runtime/verifier only for this stage. It must not redesign the methodology, select a new source, relax admission rules, or rewrite the implementation unless a concrete local-runtime bug is first demonstrated.

## Implementation

Authoritative runtime entry point:

`python -m idx_trade.yahoo_open_census_runtime`

Core implementation:

- `src/idx_trade/yahoo_open_census.py`
  - resumable per-ticker Yahoo raw cache;
  - cache identity includes ticker, requested range, frozen raw semantics, and yfinance version;
  - successful cache artifacts are SHA-verified before reuse;
  - provider errors remain explicit and retryable;
  - serial bounded requests/retries/backoff;
  - vectorized full-panel direct H/L/C admission audit;
  - full known-existing-Open audit;
  - official-factor-only split/reverse-split reconstruction;
  - year/rejection/temporal diagnostics.

- `src/idx_trade/yahoo_open_census_runtime.py`
  - authoritative orchestration wrapper;
  - derivative begins from the complete immutable panel schema and preserves every original column;
  - existing non-null Open is immutable;
  - only direct or independently verified split-scale evidence may fill null Open;
  - provenance is emitted separately;
  - artifact manifest excludes itself and the final summary to avoid circular/stale hashes;
  - `execution_grade_promoted=false` remains fixed.

## Frozen inputs and gates

Immutable panel:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Window:

`2021-04-29 -> 2026-07-31`

Baseline unresolved Open:

`446,843`

Direct admission remains exact ticker/date + exact raw Yahoo H/L/C agreement + finite positive in-range raw Open.

Split-scale admission remains allowed only with independently verified pre-existing official split/reverse-split factors. No Yahoo/panel ratio may be used to invent a factor. No Adj Close, dividend adjustment, previous Close, interpolation, forward fill, source averaging, or synthetic Open is allowed.

## Runtime output root

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_yahoo_census_v1_20260810`

The runner is resumable through `raw_cache/`. A successful ticker cache is not re-downloaded if identity, SHA, and raw semantics still validate. Provider-error tickers remain explicit rather than being converted to market state.

## Tests

New focused coverage includes:

- frozen direct H/L/C admission;
- known Open preservation/agreement;
- adjusted/dividend fields cannot substitute raw execution prices;
- independently verified split reconstruction;
- missing/unverified split rejection;
- full derivative preserves every original panel column;
- cache resume/idempotence;
- provider-error retention;
- deterministic ticker-sorted cache manifest;
- row-level provenance for accepted evidence.

GitHub CI must remain green before local runtime begins.

## Stop boundary

After the local census finishes, write factual runtime documentation only and STOP for independent ChatGPT review.

Do not promote execution grade, run execution-PnL, rerun Stage 5, alter Ranking V1/V2, paper/live trade, integrate a broker, add Zapi/another source, scrape IDX, or merge to `main`.
