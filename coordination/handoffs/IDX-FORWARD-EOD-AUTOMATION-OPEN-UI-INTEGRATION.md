# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-FORWARD-EOD-AUTOMATION-OPEN-UI-INTEGRATION
model_used: gpt-5.6-luna xhigh root with two bounded read-only Orchestra audits
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: latest integration commit containing this handoff
branch: `integration/forward-eod-automation-monitoring`
head_commit: see pushed branch HEAD

## Scope

Integrate the reviewed market/index capture on top of the latest frontend
lineage, add a headless catch-up runner and immutable Open/HLCV sidecar, and
make `/monitoring` read-only for model progress.

## Files changed

- `src/idx_trade/forward_ohlcv.py`
- `src/idx_trade/forward_eod_runner.py`
- `src/idx_trade/forward_monitoring.py`
- `scripts/run_forward_eod_catchup.ps1`
- `scripts/install_forward_eod_task.ps1`
- `apps/web/app/monitoring/page.tsx`
- `tests/test_forward_ohlcv.py`
- `tests/test_forward_eod_runner.py`
- `tests/test_forward_monitoring.py`
- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- `docs/checkpoints/2026-08-12_FORWARD_EOD_AUTOMATION_OPEN_UI_INTEGRATION_PRE_CAPTURE.md`

## Findings

External runtime root:
`D:\Documents\Project\idx-trade-data-gate-20260808v`.

Existing DATA_READY sessions are `2026-08-03` (831 active model rows) and
`2026-08-10` (837). Their `model_input.parquet` artifacts retain the frozen
seven-column schema and contain no Open. Existing local raw Yahoo/yfinance
files contain `raw_open` but end at `2026-07-31`, so local date/Open coverage
is exactly `0/831` and `0/837`. Legacy manifests show `downloaded_price_hits`
of 831 and 837, but those rows were not persisted with Open.

The existing Stockbit intraday and Forward Open Archive scheduled tasks were
inspected read-only and remain separate. No new task is installed yet.

## Decisions / boundaries

- `model_input.parquet` is never rewritten; Open lives in immutable
  `session_ohlcv.parquet`.
- Future captures fail closed when Open is absent/invalid and record provider
  evidence, hashes, and observed retrieval time without claiming historical
  publication time.
- Legacy recovery is local-first and opt-in network-only for missing rows;
  provider H/L/C/Volume must agree with the frozen session model input.
- One headless runner uses the existing capture engine and catches up in
  chronological order. Its second scheduled trigger is idempotent.
- The monitoring UI no longer exposes manual capture controls; the guarded
  backend route remains for emergency/local use.

## Validation / current blocker

- Focused forward/runtime/OHLCV/runner tests: passed.
- Full repository pytest and Next.js build: passed on the integrated tree.
- Current Jakarta time was before the mandatory 17:00 cutoff. No real
  headless capture or Open network recovery was performed, and the scheduler
  was not installed or enabled.

## Recommended next action

After 17:00 Asia/Jakarta, execute exactly one headless catch-up cycle with the
existing runtime root. Verify both legacy Open sidecars, the earliest missing
session's official Stock/Index completeness, all artifact hashes, H/L/C
agreement, unchanged model-input columns, and unchanged model fan-out. If and
only if the terminal result is successful, install the one Task Scheduler task
with the two idempotent triggers and verify its configuration read-only.
