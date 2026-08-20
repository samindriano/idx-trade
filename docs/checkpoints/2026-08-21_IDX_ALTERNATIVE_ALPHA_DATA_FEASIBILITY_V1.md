# IDX Alternative Alpha Data Feasibility V1 — Checkpoint

Status: `CONDITIONAL_SOURCE_READY_NO_HISTORICAL_ALPHA_YET`
Branch: `research/idx-alternative-alpha-data-feasibility-v1`
Scope: one-shot source census; no model/outcome access

## Exact evidence

- Zapi account: Pro/active.
- Pre-probe quota: 3,888/25,000 used, 21,112 remaining.
- Independent live bounded probes: 20 GETs; no 429/retry; observed monthly
  remaining moved 21,087 → 21,070.
- Stockbit stream: AADI/CUAN/SMBR returned 30/30/29 rows for requested count
  50, source dates 2026-08-20/21; BBCA small probe returned 3 unique posts
  with `createdAt` 2026-08-21 00:24:38–02:03:26 WIB; one separate BBCA count=50
  response had schema-empty data and is classified as an anomaly.
- Yahoo analysts: CUAN.JK and SMBR.JK explicit no-coverage; BBCA.JK had
  analystCount=25 and four trend periods in the independent probe.
- Yahoo earnings: BBCA.JK had four quarterly/four annual/four estimate rows;
  CUAN/SMBR bounded responses were annual-heavy with zero quarterly items.
- Yahoo historical: BBCA.JK 2,463 daily candles from 2016-08-22 through
  2026-08-19 for `range=10y,interval=1d`.
- IDX Stock Summary: 2026-07-31 `recordsTotal=963`; page 0 AADI/AALI/ABBA and
  page 1 ABDA/ABMM/ACES. The `code=BBCA,length=1` filter was ignored and
  returned all 963 rows; this source path fails closed for filtered acquisition.
- IDX Stock History: BBCA 28 rows from 2026-07-01 through 2026-08-07.
- IDX current snapshot: 962 companies and 962 securities.
- IDX broker summary: 3/88 brokers on 2026-07-31; market-wide only.
- IDX UMA: 7 rows but nested `ResultCount=0`, an internal count mismatch.
- IDX SBL/lendable: BBCA HTTP200, total=293, one filtered row.
- IDX derivatives: three BBCA contracts dated 2026-08-20 with many zero fields.

## Decisions

- `GO_PROSPECTIVE_CAPTURE_ONLY`: Stockbit Stream; IDX SBL/lendable.
- `GO_BOUNDED_PILOT`: Stockbit per-ticker broker flow; official IDX
  disclosure/events; Bank Indonesia macro.
- `WAIT_FOR_MORE_EVIDENCE`: IDX derivatives/open interest; Yahoo earnings and
  analyst coverage.
- `DROP_REDUNDANT` / `DROP_LOW_VALUE`: generic OHLCV/intraday and current
  Yahoo summaries/holders.

## Strongest blocker

No new source has yet demonstrated the complete combination of historical
coverage, knowledge-time semantics, revision lineage, identity completeness,
and immutable source bytes required for V4-X1 integration. Stockbit Stream is
useful only prospectively. Stockbit broker flow is promising but private and
unvalidated with the user's account. Official IDX event data is bounded by
public retention and must remain separate from existing lanes.

## Preserved artifacts

- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/source_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/github_repo_inventory.csv`
- `docs/artifacts/idx_alternative_alpha_data_feasibility_v1/bounded_probe_results.csv`

No raw provider response, key, token, cookie, user-content archive, large
download, or runtime artifact is committed.

## Stop

Stop for ChatGPT independent review. Do not start a broker-flow backfill,
Stockbit archive, SBL archive, event corpus, feature design, or model run from
this checkpoint alone.
