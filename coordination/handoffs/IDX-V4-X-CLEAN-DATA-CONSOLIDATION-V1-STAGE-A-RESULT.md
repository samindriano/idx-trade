# Handoff — V4-X Clean-Data Consolidation V1 Stage A Result

from: Codex
to: ChatGPT independent review
task_id: IDX-V4-X-CLEAN-DATA-CONSOLIDATION-V1-STAGE-A-RUNTIME
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: `samindriano/idx-trade`
source_commit: `04b295a9443c2926782d4cebff532ee6e81238c3`
branch: `data/v4-x-clean-data-consolidation-v1`
head_commit: `TBD_AFTER_RESULT_DOCUMENTATION`
scope: One execution-only offline Stage-A HLC/Open/provenance consolidation; no Stage B, identity adjudication, refit, or outcome access.

## Required return

- final branch: `data/v4-x-clean-data-consolidation-v1`
- runtime HEAD before result docs: `04b295a9443c2926782d4cebff532ee6e81238c3`
- focused test: `8 passed`
- runtime status: `STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION`
- manifest path: `D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820\MANIFEST.json`
- manifest SHA-256: `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969`
- rows/tickers: `981,940 / 945`
- HLC repair rows/tickers: `1,657 / 12`
- Open official primary: `1,216`
- Open CA-factor fallback: `439`
- Open fail-closed: `2`
- identity parity: parent identity preserved; no universe/listing repair performed
- Volume parity: PASS, unchanged
- Regular-Market Value parity: PASS, unchanged
- implementation-only fix: none

## Output artifact hashes

- clean candidate panel: `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`
- provenance parquet: `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28`
- provenance CSV: `91cf615a9ab533a1478fbc1aecc5084341647070d091d85d5a7ee53a2ad4ccf3`
- correction ledger: `6f883aaae54b3180bc3c38a2836b88b9cb983ed215dbb61246329a869138e125`
- summary: `28c61dfa6ae6c145a2186e8b8f197038e019d48fad469e958a18cbd74ee8c7fc`

## Guardrails and stop boundary

Provider calls, model/score/tuning, targets/returns/ranks, protected/fresh-
forward outcomes, forward counters, parent overwrite, calendar/session change,
volume/value repair, universe/listing repair, primary-liquidity change, and
V4-X2 execution were not performed. The candidate is not final clean input and
is not authorized for refit. Stop at the independently owned PIT Security
Identity / Listing-Domain adjudication boundary.
