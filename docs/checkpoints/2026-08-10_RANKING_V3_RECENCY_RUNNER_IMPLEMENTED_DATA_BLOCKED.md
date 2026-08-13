# Ranking V3-A Recency Runner — Implementation Checkpoint

Date: 2026-08-10 (Asia/Jakarta)

Status: **RANKING_V3_RECENCY_RUNNER_IMPLEMENTED — F1-F4 OUTCOME RUN BLOCKED IN CHATGPT RUNTIME BY LOCAL DATA UNAVAILABILITY**

## Scope completed

The authorized V3-A implementation has been added on branch `research/idx-ranking-v2-spec-v1` without changing the frozen V2 model semantics or opening any sealed outcome set.

Implementation:

- `src/idx_trade/ranking_v3_recency.py`
- `tests/test_ranking_v3_recency.py`

Latest implementation commit at this checkpoint:

`3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`

The runner implements exactly three preregistered slots:

1. exact uniform V2 `HGB_XS_MARKET` control;
2. H=252 official-session recency weighting;
3. H=504 official-session recency weighting.

Only V2F1-V2F4 are reachable by the V3-A scoring loop. V2F5/V2F6 are explicitly rejected by the fold guard and remain sealed for the later final-V3 late-development confirmation.

## Implemented research contract

The implementation preserves:

- exact 25 V2 `HGB_XS_MARKET` features and order;
- exact H10 target/universe/table semantics inherited from the frozen prepared cache;
- exact HGB preprocessing and hyperparameters;
- exact logit ranking-score semantics;
- exact V2 PR-AUC / ROC-AUC / within-date Q5-Q1 / top-decile metrics;
- half-lives exactly 252 and 504 official sessions;
- `age = train_end - signal_session_index`;
- `raw_weight = 2 ** (-age / H)`;
- fold-local normalization to mean weight 1.0 within `1e-12`;
- no class weighting, clipping, floors/caps, resampling, added features, model family, threshold, ensemble, or rescue search.

## Mandatory control-equivalence gate

The uniform V3-A control is fitted first using the exact unweighted V2 fit call. Before either recency variant can be fitted, the runner requires equivalence against the immutable historical `HGB_XS_MARKET` prediction artifact for V2F1-V2F4:

- exact row identity/order;
- row-level score equality under absolute tolerance `1e-12`, `rtol=0`;
- prevalence;
- PR-AUC;
- PR-AUC minus prevalence;
- ROC-AUC;
- Q1/Q5 TP rate and Q5-Q1 spread;
- top-decile TP rate/lift.

The reference V2 summary and prediction artifact are SHA-256 checked. The prediction Parquet is materialized with a V2F1-V2F4 predicate only. V2F5/V2F6 outcome rows are not materialized or summarized by the V3-A runner.

If control equivalence fails, the runner raises and stops before H=252/H=504 fitting; it does not weaken tolerance or interpret variant results.

## Discovery gates and deterministic decision

The implementation uses only the frozen discovery absolute-sanity and paired-promotion rules. It reports median/q25/worst PR-delta, ROC behavior, Q5-Q1, top-decile diagnostics, paired improvements, and V3D4/V2F4 behavior.

A variant that fails absolute sanity is `KILL`; a clean candidate that passes absolute sanity but fails the paired promotion gate is `KEEP_DIAGNOSTIC`; a candidate passing both is `PROMOTE_FOR_NEXT_RESEARCH_STEP`.

If both variants pass, the frozen deterministic tie rule applies and may carry forward only one recency component. If neither passes, the global result is `V3_A_RECENCY_KILL_KEEP_V2_CONTROL`.

## Artifacts produced by an authorized local outcome run

The runner will write a new immutable output directory containing:

- control-equivalence JSON;
- F1-F4 fold metrics CSV;
- F1-F4 prediction Parquet;
- paired-comparison CSV;
- aggregate JSON;
- deterministic verdict JSON;
- recency weight-statistics CSV;
- runtime/profiling JSON;
- executed ledger-row JSON;
- fold model joblib artifacts;
- summary JSON and SHA-256 inventory.

No F5/F6 metric artifact is defined by this runner.

## Tests performed in ChatGPT runtime

GitHub has no automatic workflow run for these branch commits, so push status was not treated as a test result.

A focused isolated test harness was executed in the ChatGPT container using the exact final `ranking_v3_recency.py` source and frozen V2 model/metric semantics needed by the tests, while filesystem/environment-only repo dependencies were isolated. Result:

**12 passed in 0.63 s**

Covered checks include:

- age definition / newest-row age zero;
- H=252 and H=504 formula;
- same-session identical weights;
- finite positive weights and mean-1 normalization;
- sample weight passed only to recency variants;
- exact V2 feature order and HGB parameters;
- exact V2F1-V2F4 discovery fold set;
- V2F5/V2F6 rejection;
- provenance mismatch fail-closed behavior;
- deterministic candidate order/tie preference;
- preregistered ledger rows cannot fabricate viewed results;
- control-equivalence pass for identical artifacts and fail for score drift.

This is **not** a substitute for the repo-local full pytest suite on the user's machine and is not an outcome run.

## Outcome-run blocker in this environment

The ChatGPT execution container does not mount the user's local Windows research store. In particular, the frozen resources under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\...`

and the immutable historical V2 `HGB_XS_MARKET` candidate prediction artifact are not available in this runtime.

Therefore the authorized V2F1-V2F4 control-equivalence and H=252/H=504 score run **was not executed here**. No result, metric, winner, or ledger outcome was fabricated.

The code is ready for the same branch to execute locally against the frozen resources. The local run must use commit `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f` or a later documentation-only descendant that does not change the implementation.

## Safety / sealed evidence

- V2F5/V2F6 recency outcomes: **not accessed**;
- post-2026-07-31 reserved V2 fresh-forward outcomes: **not accessed**;
- `FORWARD_OUTCOME_ACCESS_STARTED`: **not written**;
- V3-B Structure-Lite: **not started**;
- probability calibration / Stage 6 / IDX-VAL-002 / execution-PnL / paper/live / main merge: **not started**.

## Next action

Run the implemented V3-A runner locally only after verifying the exact prepared-cache/manifest and locating the frozen historical V2 `HGB_XS_MARKET` summary + prediction Parquet. Run full repo pytest first. Then execute F1-F4 only, commit the immutable result documentation/ledger update, and return for independent review.
