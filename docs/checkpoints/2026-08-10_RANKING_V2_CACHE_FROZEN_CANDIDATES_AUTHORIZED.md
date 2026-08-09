# Ranking V2 — Performance Gate PASS, Prepared Cache Frozen, Candidate Orchestra Authorized

Date: 2026-08-10 (Asia/Jakarta)
Branch: `research/idx-ranking-v2-spec-v1`
Reviewed by: ChatGPT architect

## Decision

**`RANKING_V2_CANDIDATE_ORCHESTRA_AUTHORIZED`**

The required performance/equivalence prerequisite has passed and the immutable Ranking-V2 prepared model table has been frozen. Historical-development candidate execution may now begin under the already-frozen `docs/RANKING_V2_RESEARCH_SPEC_V1.md` contract.

This authorization does not change any candidate definition, feature, fold, metric, eligibility gate, champion-selection rule, or research boundary.

## Performance-equivalence result

Performance branch:

- branch: `perf/idx-research-runtime-v1`
- runtime HEAD: `4f1f3af2c71cb49df7249a11d0c684cfef4aa9ca`
- repo-local pytest: **218 passed, 3 warnings**

Exact numerical environment:

- Python 3.13.5
- NumPy 2.4.2
- pandas 2.3.3
- pyarrow 23.0.1
- scikit-learn 1.8.0

Equivalence gate:

- status: `FULL_PANEL_LEGACY_FAST_EQUIVALENT`
- `legacy_fast_equal=true`
- horizons: `[5, 10, 20]`
- all frozen semantic comparisons matched
- H5 elapsed: `1567.8568 s`
- H10 elapsed: `1559.6417 s`
- H20 elapsed: `1592.5304 s`
- fast multi-horizon elapsed: `16.2132 s`
- approximate legacy parallel wall time: `1592.5304 s`
- benchmark engine speedup versus legacy parallel wall estimate: approximately `98.22x`

The speedup is a label-engine benchmark result, not a guarantee of equivalent end-to-end model-candidate speedup.

Peak-memory instrumentation in the report returned `null`; sampled legacy worker working sets were approximately 1.60-1.63 GB. Non-null peak-memory telemetry was not a semantic equivalence requirement and does not block promotion.

Label artifact SHA-256:

- H5: `321d311a...53269f6`
- H10 / `fast_h10_labels.parquet`: `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`
- H20: `64afaa7f...7dab6c9`

Equivalence report:

`D:\Documents\Project\idx-trade-data-gate-20260808v\research_label_equivalence_benchmark_20260809\research_label_full_panel_equivalence_report.json`

SHA-256:

`8f8865b2f133020a94ab8d2507fbb221f4b7f59bd1775b9da51fba2f4084d554`

## Prepared Ranking-V2 cache

Ranking-V2 branch at cache creation:

- branch: `research/idx-ranking-v2-spec-v1`
- reported HEAD: `8d3eb0c303cc25c2a6a5ebfb610c394d55be9f1e`
- repo-local pytest: **224 passed, 3 warnings**

Manifest status:

`RANKING_V2_PREPARED_CACHE_FROZEN`

Prepared table:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

Prepared-table SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Prepared-table facts:

- rows: `292633`
- tickers: `737`
- signal-session index: `20 -> 1250`
- positive rate: `0.3939849573`
- resolved primary H10 rows only
- immutable/read-only for candidate workers

Cache manifest:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json`

Manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

## Independent review

The prerequisite is accepted because:

1. the required equivalence status is exact;
2. `legacy_fast_equal=true`;
3. all three frozen horizons were compared;
4. fast H10 is hash-pinned;
5. the prepared-cache manifest has the required frozen status;
6. candidate workers can now consume one identical read-only cache rather than recomputing deterministic outcomes/features;
7. no Ranking-V2 candidate outcome was observed before this authorization.

The cache starting at session 20 is not itself anomalous: the prepared table contains resolved, feature-eligible primary H10 model rows rather than every raw panel session.

## Authorized next phase

Run exactly the frozen comparator/candidates on the same cache SHA:

- non-champion-eligible control: `V1_HGB_CONTROL`
- V2-A: `LOGISTIC_XS`
- V2-B: `HGB_XS`
- V2-C: `HGB_XS_MARKET`
- V2-D: `PAIRWISE_LOGISTIC_XS`

Each task must:

- read the same cache SHA `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- use isolated/new output directories;
- use the exact frozen numerical environment;
- make no code/spec/cache/hyperparameter/fold/feature changes;
- run all six frozen folds;
- stop after its assigned candidate completes;
- report exact metrics/artifact hashes.

After all five tasks finish, one metrics-only integrator may apply the frozen eligibility and champion-selection rules. It may not rerun, tune, rescue, add candidates, or use H5/H20 to select a champion.

## Still prohibited

- Stage-5 rerun or rescue;
- treating any data through `2026-07-31` as independent V2 validation;
- outcome-driven feature/model/hyperparameter changes;
- Probability V1/V2 calibration claims;
- Stage 6;
- `IDX-VAL-002`;
- execution-PnL claims;
- Kelly sizing;
- paper/live trading;
- merge to `main`.

Any selected candidate is a historical-development champion only. Fresh-forward independent evaluation requires data strictly after `2026-07-31` after the architecture is frozen.
