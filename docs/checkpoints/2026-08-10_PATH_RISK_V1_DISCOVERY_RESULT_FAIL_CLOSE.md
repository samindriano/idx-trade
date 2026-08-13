# Path Risk V1 — PR-001 F1-F4 Discovery Result

Date: 2026-08-10 (Asia/Jakarta)

Status: **`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`**

## Decision

The frozen Path Risk V1 discovery experiment is complete and closed.

Candidate:

`PATH-RISK-A-Q75-HGB-001`

The candidate failed the exact preregistered F1-F4 discovery gate in `docs/PATH_RISK_V1_SPEC.md`. There is no MIXED state and no rescue, alternate quantile, alternate target, model swap, feature pruning, fold exclusion, or threshold relaxation after result access.

Path Risk V1 therefore produces **no promoted risk model** and does **not** proceed to F5/F6 confirmation or alpha+risk integration.

The final alpha ranker remains unchanged:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

## Execution identity

- branch: `research/idx-ranking-v2-spec-v1`;
- code HEAD/upstream: `878898b70e930269e11cf00e18e263735fd3928c`;
- working tree before/after local run: clean and synchronized;
- pytest: `381 passed, 0 failed, 3 warnings` in `30.14s`;
- `idx_trade.__file__`: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade\src\idx_trade\__init__.py`;
- runner module: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade\src\idx_trade\path_risk_v1_discovery_run.py`.

This confirms the corrected `src`-layout import path was used. The earlier import-path block consumed no Path Risk outcome and is not a candidate result.

## Frozen input identities

- discovery feature cache SHA-256: `74c300390dce542dad95ae204dd7663f5f780b09dd33c3514c5dd264f15cca08`;
- feature-cache manifest SHA-256: `054ccff7676a744871b1f82a5b263898f9fa53c2d1ae1ac20a5659485466bed0`;
- H10 labels SHA-256: `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`;
- signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.

All frozen input checks passed.

## Target / join population

Target rows: `660,721`.

Target status composition:

- `SL_FIRST`: `328,926`;
- `TP_FIRST`: `211,546`;
- `NO_BARRIER_HIT`: `112,921`;
- `AMBIGUOUS_SAME_BAR`: `7,328`.

Feature cache rows: `254,383`.

Joined model rows: `252,198`.

Feature-to-target join coverage: `99.1411%`.

Feature rows without an eligible target: `2,185`.

## Frozen per-fold results

| Fold | Train rows | Validation rows | Baseline pinball | Model pinball | Relative improvement | Spearman | q75 coverage | q75 error | Q5-Q1 realized AE spread | Q1 stop-touch | Q5 stop-touch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | 132,593 | 27,053 | 0.217266 | 0.216339 | +0.004267 | 0.108963 | 0.751488 | 0.001488 | 0.244352 R | 0.449739 | 0.564898 |
| V2F2 | 164,771 | 24,464 | 0.244888 | 0.242128 | +0.011273 | 0.103342 | 0.724820 | 0.025180 | 0.295120 R | 0.444856 | 0.570734 |
| V2F3 | 194,733 | 24,546 | 0.232372 | 0.229105 | +0.014061 | 0.101864 | 0.751772 | 0.001772 | 0.272392 R | 0.425257 | 0.550596 |
| V2F4 | 224,050 | 23,112 | 0.261531 | 0.270282 | -0.033463 | 0.098905 | 0.650182 | 0.099818 | 0.242508 R | 0.486687 | 0.595704 |

Validation dates/tickers:

- V2F1: `100 / 359`;
- V2F2: `100 / 331`;
- V2F3: `100 / 305`;
- V2F4: `100 / 314`.

Prediction finite rate was `100%` on every fold.

Unique prediction counts:

- V2F1: `27,052`;
- V2F2: `24,460`;
- V2F3: `24,543`;
- V2F4: `23,111`.

## Exact gate evaluation

1. required metrics/predictions finite: **PASS**;
2. target/data/provenance gates: **PASS**;
3. nonnegative relative pinball improvement on at least 3/4 folds: **PASS**, `3/4`;
4. median relative pinball improvement >= `+0.02`: **FAIL**, approximately `+0.00777`;
5. q25 relative pinball improvement >= `0`: **FAIL**, approximately `-0.00517`;
6. worst relative pinball improvement >= `-0.01`: **FAIL**, `-0.033463`;
7. positive Spearman on at least 3/4 folds: **PASS**, `4/4`;
8. median Spearman >= `+0.10`: **PASS**;
9. positive realized Q5-Q1 adverse-excursion spread on at least 3/4 folds: **PASS**, `4/4`;
10. median realized Q5-Q1 spread >= `+0.10 R`: **PASS**.

Frozen verdict:

`PATH_RISK_A_DISCOVERY_FAIL_CLOSE`

## Interpretation boundary

The model shows some cross-sectional ordering information: Spearman is positive in all four folds and realized adverse excursion rises from low- to high-predicted-risk quintiles in all four folds.

However, the primary proper-scoring objective is not robust. Median pinball improvement is far below the frozen `+2%` requirement, q25 is negative, and F4 degrades pinball loss by roughly `3.35%`. F4 also shows material q75 undercoverage (`0.650182` versus nominal `0.75`), although coverage itself was diagnostic rather than a promotion gate.

It would be post-result reinterpretation to rescue PR-001 as a pure ordering/risk-score model after the quantile-regression experiment failed its frozen proper-scoring gate. That is prohibited.

Therefore:

- PR-001 is permanently `VIEWED / FAIL_CLOSE`;
- Path Risk V1 is closed;
- no F5/F6 Path Risk confirmation is authorized;
- no risk-veto or alpha+risk integration rule is authorized;
- no alternate q50/q90/q75 rescue is authorized;
- no model/feature/target/fold/gate retuning is authorized from this result.

## Runtime artifacts

Local output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\path_risk_v1_discovery_run_20260810_001`

SHA-256:

- targets: `dc0407db557641969d3489adab473b7f416dbda9ac4f4c0e511b032631fc4d01`;
- model table: `b66fc7e40f18940ae9db418331a421e0f36d23b86597500b1d3ba73a8e3777fe`;
- metrics: `090145eb67fd0d707b8de19263bfd8d3436f2d18c55f27809f789a9e99c3f76a`;
- predictions: `17564373067a3cdff88ae6a0a0c1445adcc51f074a0c296811d21b300be39704`;
- summary: `0ee5134107d2c7f41f75ecdf22716e85d82bb9c4f96501a5ac9eeda719d5258f`;
- V2F1 model: `483459cba05c77ad152ed0f79d142e7a25d21352e8b3e76886b0b3eba3d34814`;
- V2F2 model: `8b11ab1a969130fef8c667ebe1d9db8795a2c5246c4f3632d81df1b66a94451f`;
- V2F3 model: `0dfb512a5dd1af7e5928204e7616d02714e05da86a36e20895241f478c00691e`;
- V2F4 model: `a80faf8e5b0ae1eb2519e728df1317128bd8b27f454dab77869608619ba526d0`.

Runtime total: `644.834s`.

Fold runtimes:

- V2F1: `5.056s`;
- V2F2: `4.363s`;
- V2F3: `4.812s`;
- V2F4: `5.176s`.

## Protected boundaries confirmed

- only Path Risk F1-F4 outcomes were materialized/evaluated;
- Path Risk F5/F6 remained unaccessed;
- post-2026-07-31 fresh-forward outcomes remained unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remained unwritten;
- final V3-B ranker was unchanged;
- no rescue, risk-veto, or alpha+risk integration was created.
