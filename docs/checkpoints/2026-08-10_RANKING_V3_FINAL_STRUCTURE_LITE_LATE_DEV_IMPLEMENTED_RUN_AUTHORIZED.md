# Ranking V3 Final Structure-Lite Late-Development Confirmation — Implemented / Run Authorized

Date: 2026-08-10 (Asia/Jakarta)

Status: **IMPLEMENTED PRE-OUTCOME — ONE-SHOT V2F5/V2F6 LOCAL RUN AUTHORIZED**

## Research closure before this checkpoint

- V3-A Recency: killed;
- V3-B Structure-Lite: promoted on V2F1-V2F4 and is the only surviving Tier-1 component;
- V3-C Regime-Specialization: killed;
- V3-D Sector-Relative: parked at `BLOCKED_PIT_SECTOR_HISTORY`, outcomes untouched;
- V3-E True Ranking: killed after exact F1-F4 run;
- cumulative architecture-candidate count: `9`.

Because only one Tier-1 component survives, the optional integration experiment is skipped. There is no second surviving component to combine without violating the roadmap.

## Frozen one-shot confirmation contract

Spec:

`docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_SPEC_V1.md`

- SHA-256 `c1acbe99656b0a0a0adabc7840ad779ee0553b59b7441a24607a53322d1b369f`;
- Git blob `08eba22b5f36efb160cc01abbfb5cb82d079f36e`;
- commit `1767c7b3de25a42745c53e390885dc69523c03ad`.

Review addendum:

`docs/RANKING_V3_FINAL_STRUCTURE_LITE_LATE_DEV_CONFIRM_REVIEW_ADDENDUM_V1.md`

- SHA-256 `fa6c856f6cc45714b8ba5b4817a06fab2f9141fe66be7982c0c2a30ee1fd799e`;
- Git blob `8ae7147af61c9aeaf9993576cac198c8ab8c9387`;
- commit `71be8ed17ea546e2b29d58f40ffce637a6ff6e3a`.

Exact late folds:

- V2F5 train 1..984 / purge 985..1004 / validation 1005..1104;
- V2F6 train 1..1104 / purge 1105..1124 / validation 1125..1224.

No F1-F4 rescoring and no session 1225+ scoring are authorized.

## Architecture identity

No new architecture was created.

Comparator remains exact V2 `HGB_XS_MARKET`.

Candidate remains exact existing V3-B ordinal 005:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

with the exact frozen 25 V2 features + exact frozen eight causal Structure-Lite features, same HGB estimator, parameters, seed, imputation and ranking-score semantics.

The cumulative candidate denominator remains `9` after this confirmation because ordinals 004/005 are reused; no new ordinal is created.

## Implementation

New module:

`src/idx_trade/ranking_v3_final_late_dev.py`

Implementation lineage:

- `01b241cc99d2bb80def0fd7a35a58f2ff10ceec4` — initial one-shot prepare/run implementation;
- `8109e8ebf893e26efd56bf2ed681ad664fdca3ce` — normalized text identity hardening for Windows CRLF checkout;
- `f84760b691dcd256d207374bf5d3739dd111564d` — focused late-development tests.

The implementation reuses the existing frozen V3-B Structure-Lite feature builder and model constructor rather than reimplementing geometry formulas.

## Prepare boundary

`prepare` is outcome-independent and may:

- hash frozen sources;
- physically read V2 prepared rows through session 1224 only;
- physically read panel rows only through the official date for session 1224;
- compute the frozen Structure-Lite features through 1224;
- join/preserve exact V2 row identity and columns;
- compute feature coverage/missingness;
- freeze cache and manifest hashes.

It may not compute F5/F6 target-performance metrics.

## Run boundary

After full pytest PASS and successful cache prepare, `run` performs one atomic F5/F6 confirmation:

1. read only frozen late cache;
2. read immutable V2 reference predictions only for F5/F6;
3. execute exact V2 control F5/F6;
4. prove exact control equivalence at `1e-12`;
5. only after equivalence PASS, execute exact Structure-Lite F5/F6;
6. apply frozen binary confirmation gates;
7. write metrics/diagnostics/verdict and stop.

Allowed final decisions only:

- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_PASS`;
- `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`.

There is no MIXED/rescue/second attempt.

## Frozen gates

Absolute sanity requires on both F5 and F6:

- finite required metrics;
- PR delta > 0;
- ROC > 0.5;
- Q5-Q1 > 0.

Paired confirmation requires:

- PR improvement >=0 on both folds;
- median paired PR improvement >=+0.001;
- median ROC change >=-0.005;
- Q5-Q1 change >=0 on both folds.

Top-decile lift remains diagnostic only.

## Current access state

At this checkpoint:

- V2F5/V2F6 Structure-Lite outcomes: **NOT ACCESSED**;
- final late-development cache: **NOT BUILT IN CHATGPT RUNTIME**;
- sessions 1225+: not accessed by this task;
- reserved post-2026-07-31 fresh-forward outcomes: untouched;
- `FORWARD_OUTCOME_ACCESS_STARTED`: not written;
- calibration / Stage 6 / execution / paper/live / main merge: not authorized.

ChatGPT does not claim full local pytest because the user's frozen Windows artifacts/runtime are not mounted here. The local Codex operator must run full pytest before prepare/run.
