# Ranking V4-A Participation First-Pass Run Authorized

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED — ONE ATOMIC HISTORICAL-DEVELOPMENT RUN ONLY**

## Decision

`V4_A_FIRST_PASS_ATOMIC_RUN_AUTHORIZED`

The outcome-blind V4-A cache/data audit passed its pre-outcome review. The frozen first-pass experiment may now be executed exactly once as an atomic/parallel-equivalent comparison of:

- ordinal `012`: exact final V3-B 33-feature HGB control;
- ordinal `013`: exact V3-B + frozen A1 Impact/Absorption bundle;
- ordinal `014`: exact V3-B + frozen A2 Persistent Directional Participation bundle.

No A1+A2 integration candidate is authorized in this run.

## Why the audit is sufficient

Frozen prepared cache:

- status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`.

Outcome-blind audit:

- status: `RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`;
- all seven V4-A features finite at least `98.5785%`;
- no constant feature;
- no feature below 80% finite coverage;
- no absolute Spearman correlation `>=0.95`;
- highest observed absolute correlation was `0.8942494476` between `v4a_value_persistence_fraction_5` and `v4a_value_acceleration_log_5v20`;
- `mechanical_review_required=false`;
- `binary_target_loaded=false` and `outcome_columns_loaded=false` in the official audit;
- no V4-A candidate model was fitted or scored.

The `0.8942494476` A2 within-bundle correlation is noted but is not a mechanical defect and does not justify changing the already-frozen A2 definition. Altering the bundle now would increase researcher degrees of freedom without outcome-independent evidence of a specification error.

## Frozen experiment contract

Controlling spec:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

Frozen spec Git blob:

`e32fa69596291f418ae797613da219bd0d3cf69c`

Runner:

`src/idx_trade/ranking_v4_participation_run.py`

The run must:

1. use the exact frozen V4-A cache above;
2. load exact frozen V3-B F1-F4 and F5-F6 reference artifacts and verify their pinned SHA-256 identities;
3. fit/score the exact V3-B control over V2F1..V2F6;
4. prove score and metric equivalence to the frozen V3-B references at absolute tolerance `1e-12`;
5. only after control equivalence passes, fit/score both A1 and A2 within the same invocation with no mid-run adaptation;
6. apply the frozen per-challenger PASS/FAIL gates from the spec;
7. emit mandatory top-decile overlap diagnostics;
8. stop without running integration, redesign, rescue, or any later V4 family.

## Frozen challenger gate

For each of A1 and A2 independently:

Absolute sanity requires:

- all reported metrics finite on all six folds;
- `PR-AUC - prevalence > 0` on all six folds;
- `Q5-Q1 > 0` on all six folds.

Paired versus exact V3-B requires:

- PR-AUC improvement `>=0` on at least `5/6` folds;
- median paired PR-AUC improvement `>= +0.0015`;
- q25 paired PR-AUC improvement `>=0`;
- worst paired PR-AUC improvement `>= -0.0030`;
- median paired ROC-AUC change `>= -0.0020`;
- median paired Q5-Q1 change `>=0`;
- Q5-Q1 change `>=0` on at least `4/6` folds;
- for V2F5/V2F6, each paired PR-AUC change `>= -0.0030` and their median paired PR-AUC change `>=0`.

Top-decile lift and top-decile membership overlap are diagnostic only.

Allowed result for each challenger is exactly `PASS` or `FAIL`. No rescue variant is permitted after outcome access.

## Interpretation after the run

- both A1/A2 FAIL -> V4-A family is closed with no survivor;
- exactly one PASS -> that challenger is the sole V4-A survivor; no within-family integration run exists;
- both PASS -> the result may authorize design of exactly one separately preregistered A1+A2 integration candidate, but **does not execute or automatically authorize that integration run**.

The historical folds are development evidence only. F1-F6 are already known development periods and are not independent validation for V4.

## Hard boundaries

This authorization does **not** authorize:

- changing A1/A2 features, windows, formulas, model parameters, gates, or candidate identities;
- running one challenger, reviewing it, then deciding whether/how to run the other;
- A1+A2 integration in the same first-pass invocation;
- session `1225+` materialization/scoring;
- post-2026-07-31 fresh-forward outcome access;
- writing `FORWARD_OUTCOME_ACCESS_STARTED`;
- V4-B or later-family execution;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live, or main merge.

## Next action

Execute only the local Windows procedure in:

`coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-FIRST-PASS-RUN.md`

After result documentation is committed/pushed, STOP and return the complete result for ChatGPT review.