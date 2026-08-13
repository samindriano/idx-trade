# IDX Trade — Next-Model Runtime Optimization Notes

Date: 2026-08-10 (Asia/Jakarta)
Status: **MANDATORY FIRST-READ BEFORE THE NEXT MODEL/RUNTIME IMPLEMENTATION**

## Purpose

This note records the engineering/performance findings identified after the Ranking-V2 label-engine optimization and before/while the frozen Ranking-V2 candidate orchestra is running.

It is intentionally **not authorization to modify the currently running V2 control/A/B/C/D experiment**. The current historical-development V2 candidate run is frozen and must finish under its existing code/spec/cache contract.

Before implementing the next model architecture, next research generation, or an optimized fresh-forward V2 runtime, read this file together with `docs/CURRENT_STATUS.md`, the newest controlling checkpoint, and the relevant frozen research specification.

## Current performance lesson

The previous dominant bottleneck was deterministic label construction rather than model fitting. The new fast multi-horizon label engine changed the architecture from repeated H5/H10/H20 work to one vectorized future-path scan and proved full-panel semantic equivalence.

Observed benchmark:

- legacy parallel wall estimate: about `1592.53 s`;
- fast multi-horizon: about `16.21 s`;
- label-engine benchmark speedup: about `98.22x`.

This means the old runtime profile is no longer a reliable guide to the next bottleneck. Future optimization must **profile the post-cache candidate pipeline first** rather than assuming labels remain dominant.

## Mandatory rule for the current V2 run

Do **not** change any of the following while the frozen V2 candidate orchestra is in progress or after its outcomes have begun:

- candidate code;
- feature definitions;
- prepared cache contents;
- folds;
- model hyperparameters;
- pair budget/sampler;
- metrics;
- eligibility/champion rules;
- candidate concurrency solely to rescue a slow/weak candidate if that would alter the frozen execution contract.

No runtime experiment should compete for CPU/RAM with the active V2 control/A/B/C/D jobs.

## Post-V2 profiling plan

After the current control/A/B/C/D run and integration complete, capture wall-clock, CPU and memory by stage for at least:

1. prepared-cache read;
2. table normalization / validation;
3. fold split construction;
4. preprocessing fit/transform;
5. model fit per fold;
6. model scoring per fold;
7. within-date quintile/decile metrics;
8. pair construction for `PAIRWISE_LOGISTIC_XS`;
9. model/artifact serialization;
10. total candidate wall-clock;
11. total orchestra wall-clock under the actual concurrency used.

The next optimization target must be chosen from measured dominant costs.

## Candidate optimization opportunities

### 1. Resource-aware candidate scheduler

Running more Codex sessions/processes is not automatically faster. Multiple candidate processes plus BLAS/OpenMP/scikit-learn internal threads may oversubscribe CPU and memory bandwidth.

Benchmark bounded candidate concurrency such as 1, 2, 3, and the full candidate count, then choose the setting with the lowest total wall-clock under acceptable memory pressure.

Prefer explicit thread/process limits when needed so worker count is controlled rather than accidental.

### 2. One compute orchestrator instead of many Codex compute agents

For future research, prefer:

`one Codex/operator -> one deterministic Python orchestrator -> bounded process pool`

Codex should supervise, validate and document. Python processes should perform compute parallelism. Do not scale compute by simply opening one Codex chat per task when a bounded deterministic scheduler can do the same work more safely.

### 3. Fold-level parallelism

The six frozen chronological folds for a candidate are computationally independent once the prepared cache and fold boundaries are fixed.

A future optimized runner may execute folds in parallel, but only under a **global bounded scheduler**. Do not combine unrestricted candidate-level parallelism and unrestricted fold-level parallelism, which could create severe oversubscription.

Any parallel fold runner must preserve deterministic inputs, fold boundaries, preprocessing semantics, scores, metrics and artifact identity/provenance.

### 4. Column-projected Parquet reads

Future candidate workers should benchmark reading only:

- identity/target columns;
- the exact feature columns required by that candidate.

Avoid loading unused feature columns into every process if Parquet projection materially reduces I/O and memory without changing semantics.

### 5. Frozen fold-index cache

Consider materializing a small hashed fold-index manifest/cache that records exact train/gap/validation row indices for every frozen fold against an exact prepared-cache SHA.

Future runners can consume these immutable indices rather than repeatedly reconstructing the same splits. This is mainly a determinism/simplicity optimization and may also reduce repeated filtering work.

### 6. Pairwise-model optimization

`PAIRWISE_LOGISTIC_XS` is a likely special-case cost center because deterministic positive-negative pairs are constructed by date for every fold.

If profiling confirms pair generation is material, implement a semantic-preserving fast path using NumPy/preallocated/chunked arrays and deterministic index generation rather than DataFrame-heavy construction.

The selected pairs, transformed values, ordered positive/negative examples and resulting metrics must remain identical to the authoritative implementation before promotion.

### 7. Reuse immutable transformations where valid

Look for deterministic, outcome-independent transformations that are unnecessarily repeated across candidates/folds and can be cached safely.

Do not cache training-dependent preprocessing across folds. Median imputation/scaling/model preprocessing must remain fitted only on each fold's training rows where the frozen research contract requires it.

## Equivalence requirement for every future speed optimization

Performance engineering must not silently change research semantics.

For any optimized engine/runner:

1. retain the current implementation as the reference;
2. test fixtures and adversarial cases;
3. compare on deterministic real-data samples;
4. ideally compare one complete frozen workload;
5. require exact categorical/index/date equality and strict numerical tolerance for floats;
6. compare candidate/fold scores and every selection metric;
7. fail closed on any mismatch;
8. hash/version the optimized artifacts and environment;
9. only promote the optimized implementation **before** the outcomes of the evaluation it will be used on are inspected.

Do not weaken tolerances merely to obtain a performance PASS.

## Research-stage usage

The optimized runtime does not necessarily require a new model generation.

It may be used for a future fresh-forward evaluation of a frozen V2 architecture if:

- the optimization is engineering-only;
- semantic equivalence is established first;
- the optimized code is frozen before fresh-forward outcomes are inspected.

A V3/new-model research phase may of course adopt the optimized infrastructure from the start after its own contracts are frozen.

## Expected realistic gains

Do not assume another `98x` gain. That speedup came from eliminating a particularly inefficient repeated label-engine path.

A reasonable target for the next stage, pending profiling, is:

- `~1.5-2x` total improvement if current concurrency is oversubscribed;
- possibly `2-4x` from a combination of bounded scheduling, fold parallelism, lighter I/O and pairwise optimization;
- larger gains only if profiling reveals another pathological implementation bottleneck.

Measured end-to-end wall-clock is the optimization objective, not the raw number of workers.

## Mandatory handoff rule

Before any next-model/runtime implementation begins, the implementing agent must explicitly report that it has read this file and state which recommendations are relevant to the measured bottleneck.

Any future checkpoint/handoff that authorizes a new model implementation should include this file in its required read list:

`docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
