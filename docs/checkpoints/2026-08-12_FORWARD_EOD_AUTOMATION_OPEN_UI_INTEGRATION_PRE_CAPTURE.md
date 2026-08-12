# Forward EOD Automation / Open Sidecar / Monitoring UI Integration

Date: 2026-08-12 (Asia/Jakarta)
Branch: `integration/forward-eod-automation-monitoring`
Status: `IMPLEMENTED_PRE_CAPTURE_CUTOFF`

## Lineage

The branch starts from reviewed frontend HEAD
`5cbe1b9602b4740269fd9f0f0bc5e1e8ecee0bb7` and carries the reviewed
market/index capture commits `e327be28da62cba50a152c133e67765d39af5b8b`
and `8c94f56b0025ad68b254476aaddb73be81bfb0bc` without reverting newer
frontend work.

## Existing DATA_READY Open audit

Runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`

| Session | Model rows | Model-input schema | Local raw files | Local date/Open rows |
|---|---:|---|---:|---:|
| 2026-08-03 | 831 | ticker/date/high/low/close/volume/regular_market_value | 831 | 0/831 |
| 2026-08-10 | 837 | ticker/date/high/low/close/volume/regular_market_value | 837 | 0/837 |

Both sessions are legacy `DATA_READY`, have no `open` column, and retain their
original model/evidence/manifest artifacts. The local raw price directory has
922 Parquet files with `raw_open`, but the latest raw date is `2026-07-31`;
there are no raw rows for either forward session. The existing capture
manifests show `local_price_hits=0` and `downloaded_price_hits=831/837`,
confirming that Yahoo/yfinance rows were used in memory and Open was discarded
before the legacy model-input artifact was written.

The accepted provider lineage is the existing Yahoo/yfinance daily provider
with `auto_adjust=False`, raw OHLC preserved, and vendor-adjusted fields kept
separate. Existing raw files were not changed. The later recovery timestamp is
never treated as the session's historical publication time.

## Implemented changes

- `src/idx_trade/forward_eod_runner.py`: headless chronological catch-up over
  the existing `forward_monitoring_runtime`; no second database, recorder,
  scheduler framework, API, or session hierarchy. It enforces the 17:00 local
  cutoff, stops on the first failure, and writes compact external run logs.
- `src/idx_trade/forward_ohlcv.py`: immutable sibling OHLCV artifact and
  local-first legacy enrichment. Missing rows may be fetched only when the
  caller explicitly opts in; H/L/C/Volume must reconcile with the frozen
  model input, and no row is synthesized or averaged.
- `src/idx_trade/forward_monitoring.py`: future captures write
  `session_ohlcv.parquet` with Open/H/L/C/Volume and provenance while selecting
  the unchanged frozen model-input columns. Stale recovery verifies a declared
  OHLCV artifact; old pre-extension DATA_READY sessions remain compatible.
- `scripts/run_forward_eod_catchup.ps1` and
  `scripts/install_forward_eod_task.ps1`: auditable headless runner and one
  Task Scheduler definition with 17:05 and 17:30 idempotent triggers,
  StartWhenAvailable, and IgnoreNew. Installation is intentionally not run
  before controlled real validation.
- `apps/web/app/monitoring/page.tsx`: removed manual date selection, Capture
  EOD submission, and interactive capture controls. `/monitoring` now shows
  read-only automation health, session states, O2/V3-B progress, paired
  artifacts, failures, and the locked outcome vault. The backend capture route
  remains available as a guarded emergency interface.

## Controlled-capture boundary

At checkpoint time local Jakarta time was before 17:00. Therefore this run did
not execute a real EOD capture, did not network-recover the 1,668 missing
legacy Open rows, did not install/enable a scheduler, and did not touch
outcomes, `FORWARD_OUTCOME_ACCESS_STARTED`, O2/V3-B training/refit, Path Risk,
Stockbit intraday automation, historical PIT work, or execution/PnL.

The next authorized step is one post-17:00 headless catch-up cycle through the
existing runtime. It must first attempt the two legacy Open sidecars, then
capture the earliest missing official session, stop on any failure, and only
after a successful terminal result may the single scheduled task be installed.
