# Research Runtime Performance — Full-Panel Equivalence Ready

Date: 2026-08-09 (Asia/Jakarta)
Branch: `perf/idx-research-runtime-v1`
Substantive performance code HEAD before this documentation: `9d8c59b05a293bcb64d3391b939ddcc63b46f717`

## Status

**`PERFORMANCE_EQUIVALENCE_RUNTIME_READY`**

The performance candidate is ready for one local full-frozen-panel benchmark.
This is computational validation only. It must not change research semantics or
rerun/rescue Stage 5.

GitHub CI on the substantive performance HEAD: **218 passed, 0 failed**.

## Candidate optimization

The candidate fast label engine:

- computes ATR once;
- processes each ticker with NumPy arrays rather than a Python/Pandas loop per
  signal row and future bar;
- reuses one future-path scan for H5/H10/H20;
- leaves the legacy label engine authoritative until this full-panel gate passes.

## One-time full-panel gate

Runner:

`python -m idx_trade.research_label_equivalence_benchmark`

Frozen inputs:

- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`;
- environment: Python 3.13.5, NumPy 2.4.2, pandas 2.3.3, pyarrow 23.0.1,
  scikit-learn 1.8.0.

The benchmark runs legacy H5/H10/H20 in three isolated processes in parallel,
then the fast multi-horizon implementation once. It writes all outputs and
compares:

- row counts;
- ticker/session/horizon/status/path-complete fields exactly;
- signal/first-barrier/unresolved dates exactly;
- signal-reference/ATR/barriers/targets/excursions/research-R numeric fields at
  `rtol=0`, `atol=1e-12`, including NaN/inf patterns.

Only this status permits promotion:

`FULL_PANEL_LEGACY_FAST_EQUIVALENT`

with:

- `legacy_fast_equal=true`;
- exact horizons `[5, 10, 20]`;
- exact frozen panel/calendar hashes;
- a recorded `fast_h10_labels_sha256`.

Any mismatch blocks the fast engine. Do not weaken comparison tolerances or
silently accept a semantic difference.

## Performance output

Use a new empty external directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809`

Expected key artifact:

`research_label_full_panel_equivalence_report.json`

The report also records wall-clock and process peak-working-set diagnostics.

## Downstream boundary

If and only if equivalence passes, the exact `fast_h10_labels.parquet` artifact
and its SHA may be consumed by the frozen Ranking-V2 cache builder on branch
`research/idx-ranking-v2-spec-v1`.

The expensive legacy full-panel benchmark should not become part of routine
model experimentation. It is a one-time equivalence proof. Future model workers
must consume the immutable prepared cache instead of rebuilding labels/features.

## Safety

- Ranking V1 remains FAILED;
- Stage-5 holdout remains consumed;
- Probability V1 remains `PROBABILITY_V1_NOT_READY_DEFERRED`;
- no Ranking-V2 outcome model run in this performance gate;
- no Stage 6;
- no `IDX-VAL-002`;
- no execution-PnL;
- no paper/live trading;
- no main merge.
