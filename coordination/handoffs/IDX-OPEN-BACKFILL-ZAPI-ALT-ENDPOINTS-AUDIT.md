# Handoff

from: ChatGPT independent reviewer / implementation owner  
to: Codex local runtime verifier  
task_id: IDX-OPEN-BACKFILL-ZAPI-ALT-ENDPOINTS-AUDIT  
branch: `data/idx-open-backfill-zapi-alt-endpoints-audit-v1`

## Read first

- `AGENTS.md`
- `docs/OPEN_BACKFILL_ZAPI_ALT_ENDPOINTS_AUDIT_V1.md`
- `docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_ALT_ENDPOINTS_AUDIT_IMPLEMENTATION.md`
- `src/idx_trade/zapi_alt_open_audit.py`
- `tests/test_zapi_alt_open_audit.py`

## Purpose

Run only the already-frozen bounded comparison of two separate Zapi upstreams:

1. `finance:tradingview/chart`
2. `finance:investing/search` + `finance:investing/historical`

This does not reopen `finance:idx/stock-summary`, which remains rejected for Open recovery.

## Exact local inputs

Frozen sample manifest from the completed stock-summary audit:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811\zapi_targeted_sample_manifest.csv`

Required SHA-256:

`9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`

New output root must be absent or empty:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811`

`ZAPI_API_KEY` should already exist in the Windows user/process environment. Verify presence only; never print, hash, persist, or commit the value.

## Preflight

1. Fetch remote and switch to this exact branch.
2. Confirm worktree clean and note remote HEAD.
3. Confirm `ZAPI_API_KEY` is visible to the running Codex process without revealing it.
4. Confirm the sample file exists and its SHA matches the frozen SHA.
5. Run:
   - `pytest -q tests/test_zapi_alt_open_audit.py`
   - full `pytest`
6. If a concrete implementation wiring bug is found, fix only the smallest semantics-preserving issue. Do not alter provider, sample, quota, endpoint parameters, admission rules, or classification design.

## Runtime

Run:

`python -m idx_trade.zapi_alt_open_audit --sample-manifest "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_residual_audit_v1_20260811\zapi_targeted_sample_manifest.csv" --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811"`

Use the worktree `src` on `PYTHONPATH` if necessary; do not persist a package-path workaround.

## Frozen network scope

TradingView:

- one request per unique sample ticker maximum;
- `symbol=IDX:<ticker>`;
- `market=indonesia`;
- `resolution=1D`;
- `count=1000`.

Investing:

- one `/search` request per unique sample ticker maximum;
- only exact, defensible Indonesian identity candidates advance;
- one `/historical` request per verified ticker maximum;
- `pairId=<verified>`;
- `interval=1d`;
- `period=max`;
- `pointscount=1500`.

Maximum intended total requests: `618` plus bounded retries already implemented.

If `pointscount=1500` is rejected as an invalid parameter, STOP and report it. Do not silently retry with a different point count.

If access/plan is gated, stop that provider cleanly. Do not substitute another source.

## Required factual report

For TradingView and Investing separately return:

- access and plan status;
- requests/retries/rate limits/errors;
- identities attempted/verified/ambiguous/not found where applicable;
- provider rows;
- exact sample ticker/date coverage;
- history-window unavailable count;
- H/L/C exact count/rate;
- known-control H/L/C exact;
- known-control Open exact;
- missing-Open recovery candidates;
- provider-class/rejection histogram;
- among the 120 Yahoo H/L/C mismatch sample, count supporting certified panel vs Yahoo vs disagreement.

Also return:

- overlap rows covered by both providers;
- exact raw OHLC agreement between providers;
- artifact hashes and final manifest SHA;
- confirmation that no panel was modified and:
  - `execution_grade_promoted=false`
  - `bulk_backfill_authorized=false`
  - `corporate_action_repair_performed=false`

## Stop boundary

Write a dated factual runtime checkpoint and update this handoff with the result. Commit/push normal fast-forward, then STOP for independent ChatGPT review.

Do not start a full-universe backfill, another source, corporate-action repair, model/ranking work, execution PnL, or main merge.

## Runtime result — 2026-08-11

Final runtime checkpoint:
`docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_ALT_ENDPOINTS_AUDIT_RUNTIME.md`

The frozen 240-row sample was reused unchanged with SHA
`9704fcba50ad8c19367025bdac0d5c12e0745425590425f166f619248a52a344`.
The immutable panel SHA remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

Focused tests passed 6/6 and full pytest passed 248 tests with 5 existing
warnings. A small shared-classifier fix changed HTTP 404 from `ACCESS_DENIED`
to `REQUEST_ERROR`, because a symbol-level 404 is not a credential/plan gate;
the added regression test confirms the next sorted TradingView ticker is still
audited.

Final runtime summary:

- TradingView: `ACCESSIBLE`, 206 ticker attempts, 348 requests, 142 retries,
  213 rate-limit events, 130,044 provider rows, 101/240 exact sample dates,
  84 H/L/C exact, 23/40 known-control Open exact, and 61 recovery candidates.
- Investing: `ACCESSIBLE`, but all 206 search identities were rate-limited;
  618 requests, 412 retries, 618 rate-limit events, zero verified identities,
  zero historical calls, and zero recovery candidates.
- Provider overlap: 0 rows and 0 exact raw-OHLC agreements.
- Final artifact manifest SHA:
  `b5008e9942ca8681499f544c98a8bccda9c1e03b82ceb46ba1fbc45d3b1a6a80`.

The first pre-404-fix runtime was preserved outside Git at
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811_pre_404_fix`.
The final runtime is outside Git at
`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_zapi_alt_endpoints_audit_v1_20260811`.

`execution_grade_promoted=false`, `bulk_backfill_authorized=false`, and
`corporate_action_repair_performed=false`. Stop for independent ChatGPT
review; do not start bulk backfill or downstream research.

## Quota-aware follow-up result — 2026-08-11

Final checkpoint:
`docs/checkpoints/2026-08-11_OPEN_BACKFILL_ZAPI_ALT_ENDPOINTS_FOLLOWUP_RUNTIME.md`

The existing 61 TradingView candidates were first broken down offline:
37 `RESIDUAL_PROVIDER_GAP`, 24 `RESIDUAL_HLC_MISMATCH`; years 2021=10,
2022=18, 2023=20, 2024=13; HKMU was the largest ticker concentration with 5.

The quota-aware follow-up selected only the prior 71 terminal
`RATE_LIMITED` TradingView tickers and refetched 0 prior successes. The first
selected ticker (`MAIN`) returned HTTP 429 without a JSON `window`; the runner
captured `remaining_minute=100`, `remaining_month=0`, no Retry-After, and no
plan-expired header, then stopped with `UNKNOWN_QUOTA_WINDOW`. The remaining
70 selected tickers were not called. Investing was skipped because quota
status was not clear.

The frozen sample SHA and immutable panel SHA remained unchanged. Combined
TradingView evidence therefore remains 130,044 provider rows, 101/240 exact
sample dates, 84/240 H/L/C exact, 23/40 known-control Open exact, and 61
recovery candidates. The follow-up manifest SHA is
`87e40d23e02f7557d8a90120577ff68fd3e3567ee339c856386c141fdb61802d`.

Focused tests passed 9/9 and full pytest passed 251 tests with 5 existing
warnings. Stop for independent ChatGPT review; do not infer the unknown 429
window, retry the remaining tickers, call Investing, or start bulk backfill
without a new authorization.
