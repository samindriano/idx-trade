# TradingView Historical Intraday Remediation V1 — Preregistered

Status: `PREREGISTERED_BEFORE_NETWORK`

This checkpoint freezes the bounded remediation experiment. It does not alter
the previous audit artifacts, canonical panel, model inputs, or any protected
outcome.

## Lineage and immutable inputs

- Remediation branch: `data/tradingview-historical-intraday-remediation-v1`
- Prior reviewed branch/head: `data/tradingview-historical-intraday-audit-v1` at
  `fb5a6384a49ce2a3c80c07ae2b79134de2f584bb`
- Prior artifact manifest SHA-256:
  `ebd5d86dfb673e5a86aef51b11cc4724f5c9a5831b99782e272c683cdd1d4602`
- Prior sample manifest SHA-256:
  `768c1f1db4d999c97f6cbfbbd1babd490c7bb21a2c180cea01efa8263a79d9c4`
- New external artifact root:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_remediation_v1_20260814_retry1`
- New frozen sample manifest SHA-256:
  `966b164182218816a24a2f535c48ee9fae01d80e93ec979b2ce4bdd4b14578cf`
- Canonical panel SHA-256 before network:
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- Official calendar SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- Security-master SHA-256:
  `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- Config SHA-256 at preparation:
  `a4fa26c0d4df04e2343faf5a0d6637e9d68ec681e8d1e0647dc38de5b6d53161`

The old artifact root is read-only. The preparation run verified its manifest
and sample hashes and set `network_started=false` before creating the new
sample plan.

## Frozen upstreams and access boundary

- Mathieu2301/TradingView-API: exact commit
  `5baea86c8c7e576f13464919c86c3b4c4b0ecf4c`, package `3.5.2`.
- endenwer/tradingview-ws: exact commit
  `97c743c8230f732e5a49646dd8f0f44c5981a458`.
- Anonymous only; no credentials, cookies, or session tokens.
- Mathieu servers: `data` and `prodata`, paired with the same symbol/date
  requests.
- Symbols: `IDX:<ticker>`.
- No alternate symbol mapping, source substitution, adjustment inference, or
  request widening.

## Frozen sample and request counts

The sample is the same 20 ticker/era set as the prior audit, with deterministic
seed `20260814`:

`BBCA BBRI BMRI TLKM ASII ANTM MDKA DSSA PTBA INDF UNTR GOTO BUKA AMMN AADI WSKT GTBO ZINC BOAT MFIN`.

Eras are the fixed July windows for 2018, 2020, 2022, 2024, and 2026. The
pre-network manifest contains:

- Mathieu phase 1 paired requests: 200 (20 tickers × 5 eras × 2 servers);
- Mathieu phase 2 pagination requests: 50 (5 tickers × 5 eras × 2 servers);
- Mathieu phase 3 TV1D reconciliation requests: 20 (5 tickers × 4 eras,
  `prodata`);
- endenwer independent-client requests: 20 (5 tickers × 4 eras,
  `prodata`).

Mathieu phase 1/2 uses `timeframe=60`, `session=regular`,
`adjustment=none`, initial range 500, and bounded `fetchMore` steps. Phase 1
allows one step; phase 2 allows ten steps with batch 5 and the frozen wait and
timeout values in the JSON config. Phase 3 uses `timeframe=1D`, no pagination,
and `adjustment=none`.

The endenwer wrapper is pinned to a maximum request batch of 5,000 and a
maximum of three pages / 13,000 candles for this 20-request cross-check. Its
upstream hard-coded split adjustment is quarantined from raw numeric fidelity
claims; it is used for transport, completion, depth, and overlapping-period
diagnostics only.

## Frozen result rules

The status taxonomy is fixed to:

`AVAILABLE`, `SERIES_COMPLETED_EMPTY`, `SYMBOL_ERROR`, `TRANSPORT_TIMEOUT`,
`TRANSPORT_ERROR`, `ENTITLEMENT_OR_PERMISSION_ERROR`, `PROVIDER_ERROR`, and
`UNCLASSIFIED_NO_DATA`.

Only observable provider/client events determine the taxonomy. Entitlement is
not inferred from an empty result or timeout. Raw epochs are retained and
normalized explicitly to Asia/Jakarta; no timestamp shifting is allowed. The
08:00–16:00 WIB session band is used for session admissibility, with no
invented official 2018/2020 calendar.

The frozen analyses are:

1. offline non-corporate volume-ratio distribution, without rescaling;
2. paired `data` versus `prodata` depth and completion behavior;
3. bounded repeated pagination for the five liquid tickers;
4. endenwer protocol/event cross-check, with adjustment quarantine;
5. bounded TV60 versus TV1D versus canonical daily reconciliation for
   OHLC/Open/Volume separately;
6. raw, listing-aware, and (only where preserved official sessions exist)
   certified-session denominators.

No canonical panel write, bulk backfill, model/feature work, Path Risk/O2 work,
forward/outcome access, or authenticated experiment is authorized. If
authenticated access appears necessary, classify the result as
`AUTHENTICATED_ACCESS_EXPERIMENT_WARRANTED` and stop.

## Offline forensic baseline

The immutable prior audit contains 172 matched daily rows, of which 162 are
non-corporate-action rows. Their volume ratio (`provider_volume /
canonical_volume`) is fixed for this experiment at:

- min/max/mean: `0.5513419093 / 1.0208202401 / 0.9794315455`;
- q01/q05/q25/q50/q75/q95/q99:
  `0.7978736632 / 0.9282391500 / 0.9802290535 / 0.9920428330 /
   0.9982896321 / 1.0000000000 / 1.0000152027`;
- within ±0.5%, ±1%, ±2%, ±5%, ±10%: `66/162`, `88/162`, `121/162`,
  `147/162`, `156/162`;
- multiplicative clusters within ×1.5 of `0.01/0.1/1/10/100`: `0/0/161/0/0`.

The old timeout rows are also frozen as a diagnostic baseline: 55 rows, all
with market information, zero periods, and no persisted old websocket/event
trace; the prior adapter therefore cannot distinguish completion from timeout
without the new bounded event observation.

## Validation before network

- Focused remediation tests: `5 passed`.
- Python compilation and adapter JavaScript syntax checks: passed.
- Mathieu and endenwer dependency installation/build: passed.
- Repository-local full pytest was run from this worktree: `43 passed, 1
  pre-existing failure` in `tests/test_storage.py` because the existing
  revision-mode fixture emits both `raw_close` and `vendor_adj_close` conflicts
  while the test expects one. No storage test/code was changed by this lane.
- An initial shell-level pytest accidentally ran from the parent workspace and
  produced unrelated collection errors; it is not counted as repository
  validation.

The network phase may begin only after this checkpoint and its sample manifest
are committed and pushed.
