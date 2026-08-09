# Handoff
from: MAIN / ChatGPT ARCHITECT
To: LOCAL / Codex Luna xhigh
task_id: IDX-RUNTIME-PERF-EQUIVALENCE-RUN
branch: `perf/idx-research-runtime-v1`
substantive_code_head: `9d8c59b05a293bcb64d3391b939ddcc63b46f717`
scope: Run exactly one local full-panel legacy-vs-fast label equivalence/performance benchmark.

## Preconditions

- read `AGENTS.md` and `docs/checkpoints/2026-08-09_RESEARCH_RUNTIME_PERF_READY.md`;
- fetch/checkout/pull this branch with fast-forward only;
- working tree clean;
- exact numerical environment:
  - Python 3.13.5
  - NumPy 2.4.2
  - pandas 2.3.3
  - pyarrow 23.0.1
  - scikit-learn 1.8.0
- full local pytest must pass before benchmark;
- exact immutable panel path:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet`;
- panel SHA must equal
  `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- resolve the exact existing official-calendar artifact by SHA
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- do not recreate/redownload/substitute the calendar.

## Runtime

Use new empty output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809`

Run exactly once:

```bat
python -m idx_trade.research_label_equivalence_benchmark ^
  --panel "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet" ^
  --calendar "<EXACT_EXISTING_CALENDAR_PATH>" ^
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809" ^
  --code-commit "9d8c59b05a293bcb64d3391b939ddcc63b46f717"
```

The command already parallelizes the three legacy H5/H10/H20 runs in isolated
processes. Do not spawn another orchestration layer around this benchmark.

## Required PASS

The report must say exactly:

- `status=FULL_PANEL_LEGACY_FAST_EQUIVALENT`;
- `legacy_fast_equal=true`;
- horizons exactly `[5,10,20]`;
- all H5/H10/H20 semantic comparisons equal;
- exact frozen panel/calendar hashes;
- `fast_h10_labels_sha256` present.

If any mismatch/error occurs, STOP. Do not change semantic tolerances, labels,
barrier logic, or research definitions autonomously.

## Return facts

Report:

1. actual branch/HEAD;
2. exact environment;
3. pytest result;
4. panel/calendar paths and hashes;
5. benchmark status;
6. legacy H5/H10/H20 elapsed seconds and peak working set;
7. fast multi-horizon elapsed seconds and peak working set;
8. calculated wall-clock speed comparison (clearly distinguish legacy parallel
   benchmark wall time from sum of individual legacy runtimes);
9. all legacy/fast label artifact hashes;
10. `fast_h10_labels.parquet` exact path + SHA;
11. equivalence report exact path + SHA.

Do not run Ranking-V2 candidate outcomes. If equivalence passes, stop so the
frozen Ranking-V2 prepared cache can be built and reviewed next.
