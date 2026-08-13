# Ranking V4-B + V4-C Historical First-Pass Outcome Authorization

Date: 2026-08-10 (Asia/Jakarta)
Status: **AUTHORIZED — FROZEN HISTORICAL-DEVELOPMENT OUTCOME RUNS ONLY**

## Authorization decision

`V4_B_C_FIRST_PASS_HISTORICAL_OUTCOME_RUN_AUTHORIZED`

Both remaining main V4 families were fully frozen and outcome-blind audited before either family opened candidate outcomes:

- V4-B Price-Path blind-audit review: PASS;
- V4-C Cross-Sectional Context blind-audit review: PASS.

It is now authorized to execute the already-implemented first-pass historical-development runners for both families with no design changes, no rescue, and no integration.

This authorization opens only already-consumed V2F1..V2F6 historical-development evidence. It is not independent validation and does not authorize fresh-forward access.

## Frozen V4-B identity

Hypothesis: `V4-B-PRICE-PATH-V1`

Ordinals:

- `015` exact V3-B control;
- `016` B1 Path Coherence / Jump Concentration;
- `017` B2 Range Acceptance / Rejection.

Pinned identities:

- spec Git blob: `a750c28831b95b1c88640c5879289da5f2c05446`;
- cache SHA-256: `8c59200d284e73867a3ff3566473f7dc7dd4aa0a2bfd42917ef4e08c761d1c68`;
- cache-manifest SHA-256: `d30c7e4f0841bbddd479fdc0b8c62b1028dcf8f107277b5a8a250d9725243b2f`;
- blind-audit SHA-256: `b8facff42be8231e263c261f97e4c02d6b9db92e64ceee831d9ff27b5c7586d6`;
- blind-audit review: `docs/checkpoints/2026-08-10_RANKING_V4_B_PRICE_PATH_AUDIT_REVIEW_PASS.md`.

The run must execute exact control+B1+B2 atomically through `python -m idx_trade.ranking_v4_price_path_cli run`. No B1+B2 integration may be materialized by this authorization.

## Frozen V4-C identity

Hypothesis: `V4-C-CROSS-SECTIONAL-CONTEXT-V1`

Ordinals:

- `018` exact V3-B control;
- `019` frozen four-feature opportunity-dispersion challenger.

Pinned identities:

- spec Git blob: `43f222f31c7c0ea15e870d22b066aae95858c81f`;
- cache SHA-256: `480f09488c89128859921abe0617e51d04ac05d0ddfc42fb8f4d0c063f2b255e`;
- cache-manifest SHA-256: `33ba2b39ce10476bea0566b2d240806a9d258ebe8c5f1b61733a539a397b7737`;
- blind-audit SHA-256: `913b0cf4462d762a6514d20d5ccaf4903210111def7f68aa3532f904c205ce78`;
- blind-audit review: `docs/checkpoints/2026-08-10_RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_AUDIT_REVIEW_PASS.md`.

The run must execute exact control+019 atomically through `python -m idx_trade.ranking_v4_cross_sectional_context_cli run`.

## Frozen V3-B references required by both runners

Both runners must use the same exact frozen V3-B reference artifacts:

- F1-F4 metrics SHA-256: `0a6919a22669c14db272cc12ff70081d50ea53139f591c7faf2be2c43d321357`;
- F1-F4 predictions SHA-256: `c7761dd0bd93340381b28234537bf7a42e829eae0f214ec8173d8bc1f6f2e4e1`;
- F5-F6 metrics SHA-256: `5e758e468cf883212fdb11c64d63f8ab3cf86c20a04a60edbc651205bc8f6d25`;
- F5-F6 predictions SHA-256: `64cf1c04640740c5906db03e1ba86290790904daca2971e61c00212de893715b`.

Each family must independently prove exact V3-B control equivalence before challenger interpretation. Score and metric tolerance remain `1e-12` as implemented.

## Fixed execution sequencing

To prevent any midstream adaptation between the two frozen families:

1. preflight and SHA verification must occur before either run;
2. execute V4-C first with stdout redirected to a file and do **not inspect its result**;
3. if V4-C exits successfully, execute V4-B with stdout redirected to a separate file and do **not inspect V4-C artifacts/results in between**;
4. only after both family runners exit successfully may their outputs be opened and summarized;
5. neither result may alter the already-frozen definition, gate, feature bundle, model, or execution of the other family.

If an execution error or control-equivalence failure occurs, stop and report exactly what was materialized/viewed. Do not repair or rerun after inspecting challenger outcomes without a new review.

## Frozen promotion gates

Both V4-B challengers and the V4-C challenger use the unchanged V4-A gate already encoded in their runners:

- all metrics finite on all six folds;
- absolute `PR-AUC - prevalence > 0` on 6/6;
- absolute `Q5-Q1 > 0` on 6/6;
- paired PR nonnegative on at least 5/6;
- median paired PR improvement `>= +0.0015`;
- q25 paired PR improvement `>= 0`;
- worst paired PR improvement `>= -0.0030`;
- median paired ROC change `>= -0.0020`;
- median paired Q5-Q1 change `>= 0`;
- Q5-Q1 nonnegative on at least 4/6;
- F5 and F6 PR changes each `>= -0.0030`;
- median F5/F6 PR change `>= 0`.

Top-decile lift and membership overlap remain diagnostics only.

## Accounting

Before this authorization:

- cumulative historical evaluated-candidate count: `12`;
- V4-B ordinals `015..017`: unviewed;
- V4-C ordinals `018..019`: unviewed.

If both first-pass runners complete and their outcomes are viewed, ordinals `015..019` become permanently evaluated and the cumulative historical evaluated-candidate count becomes `17`, regardless of PASS/FAIL outcomes.

If a family is blocked before challenger outcome is materialized, document the partial state precisely rather than fabricating an evaluated result.

## Required stop after results

After both first-pass results are captured:

- update the permanent V4 ledger and current status;
- create dated result checkpoint(s) and a result handoff;
- report exact per-fold and paired metrics, gate details, control-equivalence result, survivors, runtimes, and artifact hashes;
- STOP for ChatGPT review.

Do not automatically create or run:

- B1+B2 integration, even if both B challengers PASS;
- V4-B/V4-C cross-family integration;
- any rescue or alternate feature variant;
- any additional V4 family;
- sessions `1225+`;
- post-2026-07-31 fresh-forward validation;
- `FORWARD_OUTCOME_ACCESS_STARTED`;
- calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, portfolio construction, paper/live, or main merge.
