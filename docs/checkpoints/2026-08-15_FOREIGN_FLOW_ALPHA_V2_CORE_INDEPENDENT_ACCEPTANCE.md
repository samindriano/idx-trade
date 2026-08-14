# Foreign Flow V2 Core Alpha — Independent Acceptance

Date: 2026-08-15 (Asia/Jakarta)
Reviewer: ChatGPT/Foreign-Flow-V2-Core-Review
Reviewed branch: `research/idx-foreign-flow-alpha-v2-core`
Reviewed HEAD: `e81eddcf02f0ae0e164beedf917bf2a68d7c6880`
Verdict: `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR_ACCEPTED`

## Decision

The one-shot Foreign Flow V2 Core Alpha historical-development result is accepted as decision-valid. The exact preregistered eight-feature challenger does not survive against the accepted Clean V2 `HGB_XS_MARKET` control.

This acceptance closes the V2 Core Alpha lane. It does not authorize subset rescue, alternate windows, clipping/winsorization, target changes, model tuning, or another historical V2-core run.

## Frozen experiment identity

- Preregistration commit: `4adc9484bc33febf240752c3e904a93aca9bae82`
- Run implementation commit: `8140825643a24b39f7f4a2eb7d5cb88d3dfe754a`
- Final reviewed HEAD: `e81eddcf02f0ae0e164beedf917bf2a68d7c6880`
- Result root: `D:\Documents\Project\idx-trade-foreign-flow-alpha-v2-core-20260815-001`
- Result manifest SHA-256: `23275d2a673ac99dc0928a5a6c0956a0059c82c80a13eea83b4e5db4c4252852`
- Common support: 292,631 rows / 737 tickers / 1,231 sessions
- Support identity and temporal causality: PASS

## Accepted primary evidence

Paired PR-AUC deltas, challenger minus BASE:

- V2F1: `-0.004128`
- V2F2: `-0.002257`
- V2F3: `-0.004460`
- V2F4: `+0.003594`
- V2F5: `-0.005574`
- V2F6: `-0.004549`

Frozen gate results:

- median paired PR-AUC delta: `-0.0042937528` — FAIL;
- Q25 paired PR-AUC delta: `-0.0045263462` — FAIL;
- positive PR-AUC folds: `1/6` — FAIL;
- ranking guardrail: PASS.

The failure is broad rather than a single-fold accident: five of six paired PR-AUC deltas are negative. Secondary median ROC-AUC delta is also negative (`-0.0015457125`). The higher aggregate challenger median Q5−Q1 does not override the preregistered primary gate.

## Scientific interpretation

This result says the exact frozen eight-feature Foreign Flow V2 core block did not add incremental H10 classification alpha to Clean V2 on the reused historical-development folds. It does not prove that foreign flow contains no information at other horizons, under other targets, or after independently motivated supply normalization.

Foreign Flow V1 remains `FOREIGN_FLOW_V1_NO_SURVIVOR`; V2 Core is now independently accepted as `NO_SURVIVOR` as well. No post-result feature attribution, subset search, alternate horizon, or rescue is authorized from this result.

## Effective-supply boundary

The Free Float / Effective Supply hypothesis predates this V2-core outcome and is already tracked in a separate source lane. Therefore a separately frozen PIT-safe supply extension may still be evaluated later without being reclassified as a post-hoc V2-core rescue, provided:

1. its source/feature contract is frozen outcome-blind;
2. the formulas are not changed based on these V2 fold results;
3. it is run as one separately preregistered development experiment;
4. any same-fold result is treated as development evidence, not independent confirmation.

After that pre-existing supply extension, do not continue iterating Foreign Flow V3/V4 feature families on the same historical folds based on observed performance. Fresh/prospective data would be required for stronger confirmation.

## Validation boundary

Focused tests passed `4`; full pytest was `67 passed, 1 pre-existing unrelated storage expectation failure`; `git diff --check` passed. No provider calls, protected/fresh-forward outcomes, O2 changes, or free-float lane mutations occurred.

## Final status

`FOREIGN_FLOW_V2_CORE_NO_SURVIVOR_ACCEPTED`

V2 Core Alpha lane: `DONE`.
