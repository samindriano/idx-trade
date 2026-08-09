# Runtime Handoff — Tier-1 Historical Open Backfill

Use Luna xhigh. This is a deterministic local-data execution task.

## Repository

`C:\Users\Sam\OneDrive\Documents\Project\idx-trade`

Branch:

`data/idx-open-backfill-v1`

Read first:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/OPEN_BACKFILL_POLICY_V1.md`
4. `docs/checkpoints/2026-08-10_OPEN_BACKFILL_WILDAN_READY.md`
5. this handoff

## Frozen input panel

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Required SHA-256:

`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

Do not modify this file.

## External source

Clone the existing public dataset repository normally; do not scrape `idx.co.id`.

Recommended external directory:

`D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX`

Commands:

```powershell
git clone https://github.com/wildangunawan/Dataset-Saham-IDX.git "D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX"
cd "D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX"
git rev-parse HEAD
```

If the directory already exists, do not silently update it. Record its current `git rev-parse HEAD`; use exactly that pinned snapshot for the run.

The exact commit SHA must be passed to the runner.

## Tests

From the project repository:

```powershell
python -m pytest
```

All tests must pass before runtime. If they fail, stop.

## Output directory

Use a new empty directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_wildan_v1_20260810`

Do not reuse a partially populated directory from a failed attempt without reporting it.

## Run

```powershell
python -m idx_trade.wildan_open_backfill `
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" `
  --wildan-root "D:\Documents\Project\idx-trade-external\Dataset-Saham-IDX" `
  --wildan-commit "<EXACT_GIT_REV_PARSE_HEAD>" `
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\open_backfill_wildan_v1_20260810" `
  --expected-panel-sha256 "67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76"
```

## Forbidden actions

Do not:

- scrape/crawl IDX directly;
- synthesize Open;
- use previous close as Open;
- average disagreeing sources;
- overwrite any existing panel Open;
- overwrite the immutable input panel;
- use TradingView/Investing automated extraction;
- automatically add Zapi or Yahoo in this run;
- claim execution-grade PASS;
- run execution PnL;
- paper/live trade;
- merge to main.

## Required report to ChatGPT

Return:

1. project branch and final HEAD;
2. external Wildan repository commit SHA;
3. pytest result;
4. exact input panel SHA;
5. `source_info_last_update`;
6. `source_observed_last_date`;
7. source ticker/file coverage;
8. known-existing-Open overlap rows + HLC exact rate + Open exact rate;
9. initial null Open rows;
10. source candidate target rows;
11. accepted backfill rows;
12. rejected/unresolved rows with diagnostic breakdown;
13. final null Open rows and percentage;
14. all output hashes + summary SHA;
15. confirmation `execution_grade_promoted=false`.

After successful runtime, documentation-only result commits are allowed on this branch. Do not change `src/` or `tests/` after seeing runtime outcome without returning to ChatGPT first.
