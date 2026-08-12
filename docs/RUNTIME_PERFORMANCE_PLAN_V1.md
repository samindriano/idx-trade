# IDX Trade — Runtime Performance Plan V1

Date: 2026-08-09 (Asia/Jakarta)
Status: DESIGN ONLY — SEMANTIC-PRESERVING PERFORMANCE TRACK

## Why Stage 5 was slow

The expensive part of the Stage-5 runtime was not fitting one HGB model. The current research pipeline repeatedly rebuilds deterministic derived data from the ~982k-row immutable signal panel:

1. `build_baseline_features(...)` rebuilds causal ATR and all rolling features;
2. `build_first_touch_labels(...)` rebuilds ATR again and then iterates in Python/Pandas over ticker -> signal row -> future horizon;
3. Stage 5 builds H5, H10, and H20 labels separately, repeating the same panel preparation and future-path work three times;
4. the final development refit also builds a separate development feature/label table before the full-holdout feature/label pass.

This means a nominal "one-model test" spends most of its wall-clock time recomputing deterministic features and labels rather than training the model.

## Performance objective

Future V2 research should separate **immutable deterministic derivation** from **model experimentation**.

The target architecture is:

`immutable panel -> one-time derived research cache -> repeated model trials`

A model trial must not rebuild first-touch labels or the full causal feature table when panel/calendar/security-master/label semantics have not changed.

No performance optimization is allowed to change research semantics.

## Phase P0 — profile before changing algorithms

On the frozen Stage-5 inputs, measure wall-clock and peak memory for:

- panel read/validation;
- `build_baseline_features`;
- ATR calculation;
- H5 label generation;
- H10 label generation;
- H20 label generation;
- primary-model-table construction;
- HGB fit;
- HGB scoring/metrics;
- artifact serialization.

Record exact dependency versions and machine CPU/RAM. This profile is diagnostic only.

## Phase P1 — immutable derived-data cache (highest ROI)

Materialize once, with hashes and semantic metadata:

- `research_features_v1.parquet`;
- `research_labels_h5_v1.parquet`;
- `research_labels_h10_v1.parquet`;
- `research_labels_h20_v1.parquet`;
- optionally frozen resolved primary model-table views.

Cache identity must include at minimum:

- source panel SHA-256;
- official calendar SHA-256;
- security-master SHA-256;
- feature-registry/version;
- label config: horizon, ATR window, SL ATR multiple, RR;
- code/semantic engine version;
- explicit no-Open dependency;
- row count/date boundaries and artifact SHA-256.

A model runner should fail closed on cache-key mismatch rather than silently rebuilding or mixing versions.

This is the most important optimization because model-family experiments should then read a few Parquet artifacts and fit/score only.

## Phase P2 — single-pass multi-horizon first-touch engine

The current `build_first_touch_labels` performs nested Python/Pandas loops and copies/slices future paths for each signal row. Replace or supplement it with a deterministic vectorized engine that preserves exact outputs.

Proposed per-ticker algorithm:

1. prepare/validate the panel once;
2. compute ATR14 once;
3. map observed bars to official-session integer indices;
4. process each ticker as NumPy arrays;
5. construct at most the next 20 future-bar positions once;
6. compare each row's future highs/lows against that row's TP/SL levels using vectorized arrays;
7. derive H5/H10/H20 from the same max-H20 future comparison surface;
8. preserve exact first-touch ordering and `AMBIGUOUS_SAME_BAR` semantics;
9. preserve `UNRESOLVED_PATH`, `UNRESOLVED_HORIZON_END`, MFE, MAE, terminal close return, and research-R exactly.

Process ticker-by-ticker or in bounded ticker chunks to avoid a market-wide N x 20 memory spike.

## Phase P3 — safe process parallelism

Only after deterministic single-process equivalence is proven, parallelize independent ticker chunks with a bounded process pool.

Do not use multiple Codex agents as compute workers. This is CPU/dataflow parallelism inside one deterministic program.

Requirements:

- stable input ordering;
- deterministic output sort by signal date/ticker;
- no shared mutable Pandas state;
- worker-count-independent artifact hash after canonical serialization where technically feasible;
- bounded memory;
- automatic fallback to one process for tests/debugging.

H5/H10/H20 can also run as independent processes in the legacy engine, but single-pass multi-horizon reuse is preferred because it removes duplicated work rather than merely running duplicated work concurrently.

## Phase P4 — feature-engine optimization

`build_baseline_features` currently loops by ticker and also computes a Python two-pointer 60-official-session liquidity window row-by-row.

Potential semantic-preserving improvements:

- compute ATR only once and pass/reuse it;
- reuse panel preparation rather than validating/copying repeatedly;
- represent official-session indices densely per ticker for the 60-session liquidity window;
- benchmark vectorized/dense rolling count and median alternatives;
- preserve the distinction between rolling observed ACTIVE bars for technical features and exact official-session-space liquidity windows.

Do not change the frozen feature definitions merely to gain speed.

## Mandatory equivalence gate

Before optimized artifacts may replace the legacy engine, run both engines on:

1. existing unit fixtures;
2. adversarial fixtures covering TP first, SL first, same-bar ambiguity, missing future official session, horizon end, invalid ATR/barrier, sparse ACTIVE histories;
3. a deterministic sample of real tickers/dates from the frozen 1260 panel;
4. ideally one full-panel equivalence run.

For label outputs require exact equality for categorical/date/binary fields and strict numerical tolerance for floats. Compare:

- row keys;
- label status;
- binary target;
- first barrier date;
- path completeness/unresolved date;
- TP/SL levels;
- MFE/MAE;
- normalized terminal return;
- research R.

For feature outputs compare every frozen feature and universe flag.

Any mismatch fails closed and the legacy engine remains authoritative.

## Expected workflow after optimization

### One-time derivation

`panel -> features + H5/H10/H20 labels -> hashed cache`

This can still be expensive, but happens once per immutable data/semantic version.

### Repeated model research

`hashed cache -> filter frozen train/validation windows -> fit candidate -> score -> metrics`

Thus trying another model architecture should no longer trigger the hour-scale label pipeline.

## Governance

This performance track is engineering-only. It does not authorize:

- Ranking V2 architecture selection;
- use of consumed Stage-5 holdout as independent validation;
- label/feature changes;
- Stage 6;
- Probability V2;
- `IDX-VAL-002`;
- execution-PnL, paper, or live trading;
- main merge.

Do not modify the currently running Stage-5 post-mortem branch/runtime. Implement and benchmark performance changes on a separate branch after the current post-mortem runtime completes.