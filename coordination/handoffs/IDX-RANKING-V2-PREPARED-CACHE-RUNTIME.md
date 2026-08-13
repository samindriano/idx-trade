# Handoff
from: MAIN / ChatGPT ARCHITECT
to: LOCAL / Codex Luna xhigh
task_id: IDX-RANKING-V2-PREPARED-CACHE-RUNTIME
branch: `research/idx-ranking-v2-spec-v1`
substantive_code_head: `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`
scope: Build exactly one immutable Ranking-V2 prepared model-table cache after the performance equivalence gate passes.

## Preconditions

Do not run this task unless the separate performance report says exactly:

- `status=FULL_PANEL_LEGACY_FAST_EQUIVALENT`;
- `legacy_fast_equal=true`;
- horizons `[5,10,20]`;
- exact frozen panel/calendar hashes;
- `fast_h10_labels_sha256` present.

Read:

1. `AGENTS.md`;
2. `docs/CURRENT_STATUS.md`;
3. `docs/RANKING_V2_RESEARCH_SPEC_V1.md`;
4. `docs/checkpoints/2026-08-09_RANKING_V2_IMPLEMENTATION_READY.md`;
5. this handoff.

Use exact numerical environment:

- Python 3.13.5;
- NumPy 2.4.2;
- pandas 2.3.3;
- pyarrow 23.0.1;
- scikit-learn 1.8.0.

Full local pytest must pass before cache materialization.

## Frozen input hashes

- panel: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- security master: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`.

Panel exact path:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`

Resolve the exact existing calendar and security-master artifacts by the frozen
hashes. Do not recreate/download/substitute them.

H10 labels must be the exact `fast_h10_labels.parquet` emitted by the successful
performance-equivalence run; use its returned SHA as
`--expected-h10-labels-sha256`.

## Output

Use a new empty directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809`

Run exactly once:

```bat
python -m idx_trade.ranking_v2_prepare_cache ^
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" ^
  --calendar "<EXACT_EXISTING_CALENDAR_PATH>" ^
  --security-master "<EXACT_EXISTING_SECURITY_MASTER_PATH>" ^
  --h10-labels "<PERF_OUTPUT_DIR>\fast_h10_labels.parquet" ^
  --expected-h10-labels-sha256 "<FAST_H10_SHA_FROM_EQUIVALENCE_REPORT>" ^
  --equivalence-report "<PERF_OUTPUT_DIR>\research_label_full_panel_equivalence_report.json" ^
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809" ^
  --code-commit "5f2ed2f53aececfd7c338d3f9f65db1efae372b6"
```

## Required result

Cache manifest must say:

`status=RANKING_V2_PREPARED_CACHE_FROZEN`

Return:

1. actual branch/HEAD;
2. exact environment;
3. pytest result;
4. all frozen input paths/hashes;
5. equivalence report path/hash/status;
6. fast-H10 label path/hash;
7. prepared cache exact path;
8. prepared cache SHA-256;
9. cache rows, ticker count, first/last signal-session index, positive rate;
10. manifest exact path + SHA-256.

STOP after cache creation. Do not run `V1_HGB_CONTROL` or any V2-A/B/C/D
candidate yet. Do not edit candidate definitions, folds, features, metrics, or
champion rules.
