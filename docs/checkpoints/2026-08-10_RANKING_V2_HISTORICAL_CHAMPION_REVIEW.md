# Ranking V2 — Independent Historical-Champion Review

Date: 2026-08-10 (Asia/Jakarta)
Status: **`RANKING_V2_HISTORICAL_CHAMPION_REVIEW_PASS`**
Reviewed by: ChatGPT architect

## Decision

The frozen Ranking-V2 historical-development candidate orchestra and metrics-only integration are accepted.

Integrator decision:

`RANKING_V2_HISTORICAL_CHAMPION_SELECTED`

Historical-development champion:

`HGB_XS_MARKET`

This is **not independent validation**, does not authorize calibrated probability claims, and does not authorize Stage 6, `IDX-VAL-002`, execution-PnL, paper trading, live trading, Kelly sizing, or merge to `main`.

## Reproducibility / frozen state

Reported runtime state:

- branch: `research/idx-ranking-v2-spec-v1`;
- runtime HEAD: `76573e8484e468d37dd79f53502718642e0945d3`;
- frozen substantive code head: `5f2ed2f53aececfd7c338d3f9f65db1efae372b6`;
- git tree: clean;
- Python `3.13.5`;
- NumPy `2.4.2`;
- pandas `2.3.3`;
- pyarrow `23.0.1`;
- scikit-learn `1.8.0`;
- repo-local pytest: **224 passed, 3 warnings**.

Prepared cache SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Prepared-cache manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

Manifest status:

`RANKING_V2_PREPARED_CACHE_FROZEN`

All five candidate summaries completed and all 50 candidate artifacts were independently hash-verified with zero mismatches.

## Frozen candidate result

Eligibility aggregate:

| candidate | median PR delta | q25 PR delta | positive PR folds | median ROC | ROC >0.5 folds | positive Q5-Q1 folds | eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| `HGB_XS_MARKET` | `0.0238795` | `0.0194015` | 6/6 | `0.524410` | 5/6 | 6/6 | yes |
| `HGB_XS` | `0.0184815` | `0.0155045` | 6/6 | `0.515711` | 6/6 | 6/6 | yes |
| `PAIRWISE_LOGISTIC_XS` | `0.0106700` | `0.00926625` | 6/6 | `0.508343` | 6/6 | 6/6 | yes |
| `LOGISTIC_XS` | `0.0093715` | `0.0051135` | 6/6 | `0.506269` | 5/6 | 5/6 | yes |
| `V1_HGB_CONTROL` | `0.0223480` | `0.01684875` | 6/6 | `0.519010` | 5/6 | 6/6 | control only / ineligible by contract |

The control is intentionally not champion-eligible under the pre-outcome frozen specification.

## Independent selection-rule verification

The frozen champion rule first requires eligibility, then compares median PR-AUC delta, with a `0.002` practical-tie tolerance before q25 PR-delta, median Q5-Q1, and finally complexity.

`HGB_XS_MARKET` has the highest median PR-delta among eligible V2 candidates:

- `HGB_XS_MARKET`: `0.0238795`;
- next V2 candidate, `HGB_XS`: `0.0184815`;
- difference: `+0.0053980`.

Because `0.0053980 > 0.002`, no tie-break stage is required. `HGB_XS_MARKET` is therefore the deterministic champion under the frozen rule.

Even descriptively against the non-eligible V1 control, the champion has:

- median PR-delta improvement: about `+0.0015315`;
- q25 PR-delta improvement: about `+0.0025528`;
- median ROC improvement: `+0.005400`;
- median Q5-Q1 improvement: about `+0.0201875`;
- worst-fold PR-delta `0.008789` versus control `0.000785`.

The q25 and worst-fold comparisons are important: they support a robustness improvement rather than a result driven only by one unusually strong fold.

## Interpretation

The result supports the V2 design hypothesis that same-date cross-sectional stock representation plus explicit continuous market-state / stock-relative-to-market context is more robust than the other frozen V2 alternatives over the historical-development folds.

The strongest evidence is not a huge average edge. It is the combination of:

- positive PR-delta in all 6 folds;
- positive Q5-Q1 in all 6 folds;
- median PR-delta higher than every eligible V2 alternative;
- q25 PR-delta above the V1 control;
- substantially stronger median Q5-Q1 than the V1 control;
- a materially better worst PR-delta than the V1 control.

Do **not** overstate the result. The champion's median PR-delta advantage versus the V1 control is only about `0.00153`, so V2-C does not dominate V1 on every metric/fold.

In particular, V2F6 has ROC-AUC `0.493102` even though its PR-delta remains positive (`0.018643`) and Q5-Q1 remains positive (`0.044856`). This metric disagreement is a real caution and makes fresh-forward validation essential.

## Integrator artifacts

- all fold metrics SHA-256: `24ab1a7fe22b6c590ebed248655c41c5673d24f1e14e7a90b62b7290f1363670`;
- candidate aggregate SHA-256: `a2fcbba42738f19fd489512d3ec80c3eac8a796735fe0f0f642a9795221b0bfa`;
- control comparison SHA-256: `94f885a6270a3247bbcaf7a133730c836dd1b9522fb1192a401e2d977715ea4e`;
- integration summary SHA-256: `3facb4468caafab8cf19f368cf5ef04f36dac052089d2ecb810b683c851ec705`.

## Research boundary

All history through `2026-07-31` is development/research knowledge because Stage-5 outcomes informed V2 architecture selection. None of these V2 folds can be upgraded to independent validation after the fact.

Independent Ranking-V2 validation requires fresh data strictly after `2026-07-31`, under an architecture/final-fit/forward-validation contract frozen **before** inspecting those fresh-forward outcomes.

## Next authorized scope

The next phase is **champion freeze / forward-validation contract preparation only**.

Before any fresh-forward outcome evaluation:

1. freeze `HGB_XS_MARKET` as the sole Ranking-V2 historical-development champion;
2. freeze an exact final-development refit protocol using the same 25 frozen features and exact existing HGB hyperparameters, with no new tuning;
3. freeze the exact fresh-forward data/feature/universe/label maturity and evaluation protocol;
4. preserve a clear boundary that fresh-forward data strictly after `2026-07-31` is the only independent evaluation source;
5. read `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` before implementing any optimized final-fit or forward runtime;
6. do not inspect fresh-forward outcomes until that contract is committed and frozen.

No probability calibration or deployment phase is authorized by this review.
