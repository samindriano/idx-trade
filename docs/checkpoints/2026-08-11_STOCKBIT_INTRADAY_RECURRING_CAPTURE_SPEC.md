# Stockbit Intraday Recurring Capture V1 — Frozen Spec

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/stockbit-intraday-forward-capture-v1`
Decision: `RECURRING_CAPTURE_IMPLEMENTATION_AUTHORIZED_SCHEDULER_INSTALL_NOT_YET_RUN`

## Accepted evidence

The 2026-08-11 broad Stockbit census and one-call IDX traded-today audit are accepted as acquisition-infrastructure evidence:

- official current IDX universe: 962 tickers;
- Stockbit broad census: 832 SUCCESS / 130 HTTP_404;
- IDX stock-summary coverage: 962/962 canonical tickers;
- `volume > 0`, `value > 0`, `frequency > 0`, and their robust OR each produced TP=832, FP=0, FN=0, TN=130;
- no Stockbit provider/session/identity validation failure among returned payloads;
- traded-gate audit manifest SHA-256: `e41b23e2d9d2fdb7a2ccea472d24ad70197b31ea6e4b2b3ba9b9d3c699ee77eb`.

The gate is promising but one session is not sufficient evidence to permanently suppress requests. Rollout therefore begins in shadow mode.

## Daily pipeline

For each Asia/Jakarta weekday run after the complete-session gate:

1. Freeze the official current IDX active-stock universe for the exact session date.
2. Fetch exactly one broad `finance:idx/stock-summary` snapshot for that date.
3. Persist the complete raw summary payload and safe quota headers **before parsing**.
4. Parse exact canonical four-character tickers and exact session date.
5. Define `traded_today = volume > 0 OR value > 0 OR frequency > 0`.
6. A ticker missing from an otherwise non-truncated summary is treated conservatively as **fetch Stockbit**, never as no-trade.
7. Capture Stockbit `timeframe=today` chart data using the existing immutable, resumable, per-ticker artifact layout.
8. Never refetch a same-day SUCCESS on resume.
9. Preserve raw payloads, normalized price-path rows, statuses, gate decisions, quota headers, hashes, and final manifest.

No synthetic minute data, interpolation, forward fill, OHLCV invention, model feature generation, or trading is authorized here.

## Shadow-to-enforce rollout

The first **3 new completed sessions** after this spec run in `SHADOW` mode:

- compute the IDX traded-today gate;
- still request the complete frozen current IDX universe from Stockbit;
- compare the hypothetical gate against actual Stockbit outcomes;
- count a false negative when the gate would skip a ticker whose Stockbit chart is SUCCESS.

A shadow session is certification-eligible only when:

- the frozen universe is complete;
- the IDX summary is non-truncated and exact-session validated;
- the Stockbit run has no unfinished ticker;
- gate-vs-chart comparison is complete.

Promotion rule:

- after 3 consecutive certification-eligible shadow sessions with **0 false negatives**, future sessions enter `ENFORCE` mode.
- false positives do not block safety promotion, but are reported because they reduce savings.
- any false negative resets the consecutive-shadow counter to zero.

## Enforce mode

In `ENFORCE` mode:

- exact summary rows with `traded_today=false` receive terminal status `SKIPPED_IDX_NO_ACTIVITY` and do not consume a Stockbit chart call;
- summary-missing tickers are fetched conservatively;
- previously written same-day SUCCESS/skip evidence is not overwritten on resume;
- `--retry-errors` may retry provider/request errors but must never convert gate skips back into pending calls.

## Periodic drift audit

Every **10 completed enforced sessions**, run one full-universe `SHADOW_RECHECK` session instead of filtering.

- If the recheck has 0 false negatives, remain in ENFORCE mode and reset the recheck counter.
- If any false negative appears, immediately revert future sessions to SHADOW mode and require 3 new consecutive zero-FN sessions before re-promotion.

This protects against Stockbit or IDX provider semantics drifting after the one-day audit.

## Quota policy

- Keep a hard monthly Zapi reserve of **3,000** requests.
- Stop new Stockbit calls fail-closed when the observed remaining-month header reaches the reserve.
- Persist the first/last safe quota headers available from each daily run.
- Never embed or persist `ZAPI_API_KEY`.

Observed 2026-08-11 gated burden would have been 832 Stockbit calls + 1 IDX summary call/session. This is planning evidence only; actual daily counts remain data-dependent.

## Local automation target

The intended first production mechanism is Windows Task Scheduler under the user's interactive account.

Proposed weekday triggers (local machine must be Asia/Jakarta timezone):

- primary: **16:35**;
- recovery/resume: **17:30**.

The second run reuses the same date root and must not refetch same-day successes. Multiple concurrent task instances are forbidden.

The scheduler installer must:

- refuse to embed the API key in task arguments or files;
- require a persistent User/Machine `ZAPI_API_KEY` environment variable;
- require/verify Asia/Jakarta-compatible Windows timezone unless explicitly overridden;
- write operational stdout/stderr logs outside immutable market-data artifacts;
- run only Monday-Friday; exchange holidays fail closed at the exact-session gate and must not trigger Stockbit chart calls.

## Operational state

A small mutable operational policy-state file may live outside immutable per-session artifact roots and contain only rollout counters/mode, never market data or secrets.

Every policy transition must record:

- prior mode;
- new mode;
- session date;
- reason;
- shadow false-negative count;
- supporting daily artifact manifest SHA when available.

## Explicitly not authorized

- historical intraday backfill;
- model/alpha/Path-Risk feature research from this data;
- execution/trading;
- Open/TradingView work;
- PIT-sector work;
- silently weakening identity/session/gate validation;
- permanent full-universe suppression based only on the 2026-08-11 one-day audit.

## Next gate

Implement the daily orchestrator, policy state, tests, and Windows scheduler scripts. Do not install the scheduled task or perform a new live capture until local focused/full pytest passes and a separate local-install authorization is issued.
