# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-MARKET-INDEX-BREADTH-V1-SOURCE-AUDIT
model_used: gpt-5.6-luna xhigh read-only source worker plus root integration
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `4efe5108398d772da5cb9711f7619e16bde853f4`
branch: `data/market-index-breadth-history-v1`
head_commit: see commit containing this handoff
scope: bounded official IDX/Zapi market/index/breadth source audit and reusable contract only
files_changed:
  - `src/idx_trade/market_index_breadth.py`
  - `tests/test_market_index_breadth.py`
  - `docs/MARKET_INDEX_BREADTH_HISTORY_V1_SPEC.md`
  - `docs/checkpoints/2026-08-12_MARKET_INDEX_BREADTH_SOURCE_AUDIT.md`
  - `docs/DATA_FOUNDATION_STATUS.md`
  - `docs/PROJECT_LEDGER.md`
findings:
  - official `TradingSummary/GetIndexSummary` and `TradingSummary/GetStockSummary` are reachable and historically sampled;
  - Zapi raw/index-summary parity was 100% on accepted fields for 2021, 2024, and 2026 samples;
  - Digital Statistic market-by-type provides regular/non-regular/total aggregates with million-scaled value/volume;
  - no official published breadth aggregate, publication timestamp, revision ID, or PIT snapshot was found;
  - 2021 stock-summary-to-rich-index aggregate reconciliation is not exact.
decisions_made:
  - accept index summary and stock summary as a conditional session-context foundation;
  - keep breadth buckets derived-only and explicitly non-official;
  - keep `knowledge_at` unresolved and fail closed for PIT;
  - do not bulk acquire, model, alter OPEN, or touch protected outcomes.
decisions_needed:
  - whether to pursue an official publication/versioned archive or forward EOD capture before PIT materialization;
  - breadth denominator and lifecycle contract if a later official breadth source is found.
blocking_risks:
  - no PIT timing or revision lineage;
  - no official breadth aggregate/denominator;
  - historical aggregate mismatch in the 2021 sample;
  - Digital Statistic aggregate value can differ from rich summary even when volume/frequency reconcile.
validation_run:
  - focused `tests/test_market_index_breadth.py`: 6 passed;
  - baseline full pytest before changes: 471 passed, 0 failed, 3 warnings, 22.03s;
  - final focused/full results are recorded in the final response and checkpoint update.
recommended_next_action: stop for ChatGPT review; do not bulk acquire or use this lane as PIT/model input yet.
