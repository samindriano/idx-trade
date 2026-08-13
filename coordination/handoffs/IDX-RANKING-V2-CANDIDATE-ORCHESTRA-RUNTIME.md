# Handoff

from: MAIN / ChatGPT ARCHITECT
to: LOCAL / Codex Luna xhigh
task_id: `IDX-RANKING-V2-CANDIDATE-ORCHESTRA-RUNTIME`
branch: `research/idx-ranking-v2-spec-v1`
frozen substantive code head: `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`
scope: Run the frozen Ranking-V2 control + four candidate historical-development evaluations from the immutable prepared cache, then run the metrics-only integrator if and only if every candidate task completes successfully.

## Authorization

ChatGPT independently reviewed the performance-equivalence result and prepared-cache freeze on 2026-08-10 and authorized candidate execution.

Read first:

1. `AGENTS.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/RANKING_V2_RESEARCH_SPEC_V1.md`
4. `docs/checkpoints/2026-08-10_RANKING_V2_CACHE_FROZEN_CANDIDATES_AUTHORIZED.md`
5. this handoff

Do not infer authorization from older checkpoints if they conflict with the 2026-08-10 checkpoint.

## Frozen prerequisite evidence

Equivalence:

- status: `FULL_PANEL_LEGACY_FAST_EQUIVALENT`
- `legacy_fast_equal=true`
- horizons: `[5, 10, 20]`
- equivalence report SHA-256: `8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554`
- exact fast-H10 SHA-256: `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`

Prepared cache:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

Required SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Manifest:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json`

Manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

Required manifest status:

`RANKING_V2_PREPARED_CACHE_FROZEN`

Prepared cache facts:

- rows `292633`
- tickers `737`
- signal-session index `20..1250`
- positive rate `0.3939849573`

## Environment and admission

Use exact numerical environment:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0

Before any candidate outcome run:

1. fetch branch and fast-forward only;
2. verify actual branch/HEAD and clean checkout;
3. verify the prepared-cache and manifest hashes above;
4. verify manifest status exactly;
5. run repo-local full pytest (`python -m pytest tests` is acceptable if workspace-root pytest discovery again escapes this repo); expected frozen suite is at least the existing 224 passing tests with no regression;
6. verify none of the five designated output directories already contains candidate output.

If any prerequisite fails, STOP. Do not repair/tune around it autonomously.

## Frozen candidate tasks

Run exactly these five assignments against the same cache:

1. CONTROL: `V1_HGB_CONTROL` — comparator only, never champion-eligible
2. V2-A: `LOGISTIC_XS`
3. V2-B: `HGB_XS`
4. V2-C: `HGB_XS_MARKET`
5. V2-D: `PAIRWISE_LOGISTIC_XS`

No additional model, feature family, pair budget, hyperparameter, fold, universe, threshold, calibration, or sensitivity candidate is authorized.

All runs use H10 only for candidate selection and the six frozen folds in `docs/RANKING_V2_RESEARCH_SPEC_V1.md`.

## Execution layout

Use one new root directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_candidate_orchestra_20260810`

Use isolated child directories exactly or equivalently named:

- `V1_HGB_CONTROL`
- `LOGISTIC_XS`
- `HGB_XS`
- `HGB_XS_MARKET`
- `PAIRWISE_LOGISTIC_XS`

Candidate tasks may run concurrently in isolated workers. Each candidate runner is itself the compute process; do not add nested process parallelism or let workers modify shared files. If local resource pressure makes five-way parallel execution unsafe, queue tasks without changing their definitions or outputs.

Command template for each assignment:

```bat
python -m idx_trade.ranking_v2_candidate ^
  --prepared-table "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet" ^
  --expected-cache-sha256 "522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5" ^
  --candidate "<EXACT_CANDIDATE_NAME>" ^
  --output-dir "D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_candidate_orchestra_20260810\<EXACT_CANDIDATE_NAME>" ^
  --code-commit "5f2ed2f53aececfd7c338d3f9f65db1efae372b6"
```

The actual checkout HEAD may be a docs-only descendant of the frozen substantive code head. Report both actual checkout HEAD and frozen substantive code head.

## Candidate completion contract

For every task require:

- `status=RANKING_V2_CANDIDATE_COMPLETE`
- exact candidate name
- exact prepared-cache path and SHA
- exact environment
- exact frozen feature list
- all six frozen folds
- finite scores/metrics
- predictions artifact
- fold metrics artifact
- quintile artifact
- decile artifact
- six serialized fold-model artifacts
- all artifact SHA-256 values
- pairwise diagnostics for `PAIRWISE_LOGISTIC_XS`
- `probability_claim=false`
- `independent_validation_claim=false`
- `historical_period_is_development_knowledge=true`

If any candidate errors, produces non-finite output, hash mismatch, wrong fold count, or writes outside its isolated directory, STOP the integration phase. Preserve completed independent outputs but do not rerun/tune/rescue without new ChatGPT authorization.

## Metrics-only integration

Only if all five candidate summaries complete successfully, run the existing frozen `idx_trade.ranking_v2_integrate` integrator exactly as implemented.

The integrator may read only the completed frozen candidate metrics/summaries required by its CLI. Resolve its exact CLI from the checked-out frozen code; do not modify the integrator to accommodate results.

It must apply the already-frozen rules:

Candidate eligibility requires all required metrics finite and all of:

- median `PR-AUC - prevalence > 0`
- positive PR delta in at least 4/6 folds
- median ROC-AUC > 0.50
- ROC-AUC > 0.50 in at least 4/6 folds
- Q5-Q1 > 0 in at least 4/6 folds

If no V2 candidate qualifies, result is exactly:

`RANKING_V2_NO_CHAMPION`

If candidates qualify, champion selection must follow the predeclared sequence in the frozen spec. `V1_HGB_CONTROL` is never champion-eligible.

Do not invent a rescue rule based on H5/H20, one favorable fold, top-decile behavior, model complexity, or visual inspection beyond the already-declared tie-breaks.

## Required final return to ChatGPT

Return one concise but complete runtime report containing:

1. actual branch/HEAD and clean-tree status;
2. frozen substantive code head;
3. exact environment and pytest result;
4. prepared-cache path/hash and manifest path/hash/status;
5. for CONTROL and V2-A/B/C/D: completion status + output directory + summary SHA;
6. a six-fold table for each candidate with prevalence, PR-AUC, PR delta, ROC-AUC, Q5-Q1, top-decile lift;
7. aggregated eligibility diagnostics for every V2 candidate:
   - median PR delta
   - 25th-percentile PR delta
   - positive PR-delta fold count
   - median ROC-AUC
   - ROC>0.5 fold count
   - positive Q5-Q1 fold count
   - median Q5-Q1
   - worst-fold PR delta;
8. descriptive same-fold comparison against `V1_HGB_CONTROL`;
9. integrator status and exact champion/no-champion decision;
10. all final comparison/integrator artifact paths and SHA-256 values;
11. confirmation that no probability calibration, Stage 6, fresh-forward validation, execution-PnL, paper/live trading, or main merge was performed.

STOP after the frozen historical-development integration result. Do not proceed into champion refit, fresh-forward validation, Probability V2, Stage 6, `IDX-VAL-002`, or trading without a new ChatGPT review/authorization.
