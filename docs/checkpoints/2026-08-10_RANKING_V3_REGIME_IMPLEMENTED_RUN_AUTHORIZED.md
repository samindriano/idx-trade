# Checkpoint — Ranking V3-C Regime Implemented / Local Run Authorized

Date: 2026-08-10 (Asia/Jakarta)

Status: **V3-C SPEC REVIEWED + IMPLEMENTED — LOCAL PREPARE/RUN AUTHORIZED UNDER FROZEN CONTRACT**

## Scope completed

V3-C Regime-Specialization has been frozen and implemented without viewing V3-C outcomes.

Controlling specification:

`docs/RANKING_V3_REGIME_SPEC_V1.md`

- frozen Git blob: `2a2f48d68f5d3df839c61191d4a11fa870470b00`.

Independent review addendum:

`docs/RANKING_V3_REGIME_SPEC_REVIEW_ADDENDUM_V1.md`

- frozen Git blob: `a13c5ae103908311968e38c6ded233b7a1cbd901`.

Implementation:

- `src/idx_trade/research_v3_regime.py` — outcome-blind causal NORMAL/STRESS regime builder;
- `src/idx_trade/ranking_v3_regime.py` — F1-F4-only immutable cache prepare + exact control + two-expert runner;
- `tests/test_ranking_v3_regime.py` — causal/coverage/sealed-fold/promotion guardrails.

Implementation lineage:

- `b92cb24367bcc675cd2bfba5bab636d239fa384a` — regime builder;
- `89ca64393d94bf294a1d437990242bd5d230c96f` — initial cache/runner;
- `7409bfc16914ce487fe39e393f1dd0bf62df4b29` — focused tests;
- `9c94678b970c271b6a9f85c8943e719a5b651bff` — pre-outcome market-context repeated-key alignment correction + expert class guards;
- `3406f835d9d6573bf320daee1edb058e14b1dd77` — regression test for repeated market-date target keys.

No regime outcome was viewed during these changes.

## Frozen candidate set

- ordinal `006`: `V3-C-REGIME-V1-CONTROL-006` — exact frozen V2 `HGB_XS_MARKET`;
- ordinal `007`: `V3-C-REGIME-V1-TWO-EXPERT-007` — one NORMAL expert + one STRESS expert.

Both experts use exact V2 25 features, preprocessing, HGB parameters, target and raw-logit score semantics. Regime state is routing metadata only.

V3-B Structure-Lite is intentionally not inherited into V3-C.

## Frozen regime state

For each session, thresholds use only the prior 252 official sessions with at least 126 valid observations:

- breadth-20 <= prior q25 → stress vote;
- median return-20 <= prior q25 → stress vote;
- median ATR/close >= prior q75 → stress vote.

`STRESS` requires at least two votes; otherwise `NORMAL`. Warmup remains explicit `MISSING_WARMUP` and is excluded from expert fitting.

## Outcome-blind fragmentation gate

Before model scoring, every F1-F4 fold must pass:

Training, each NORMAL/STRESS:

- >= 40 distinct dates;
- >= 5,000 rows.

Validation, each NORMAL/STRESS:

- >= 8 distinct dates;
- >= 500 rows;
- zero `MISSING_WARMUP` validation rows.

Failure blocks the experiment before specialist outcomes. Do not alter regime thresholds to rescue coverage.

## Discovery / sealed evidence

Outcome-bearing discovery folds: V2F1-V2F4 only.

The V3-C cache physically excludes prepared-model rows after signal session 984. V2F5/V2F6 remain sealed for the one final-V3 late-development confirmation. Reserved post-2026-07-31 V2 fresh-forward outcomes remain unread.

`FORWARD_OUTCOME_ACCESS_STARTED` must not be written by V3-C.

## Mandatory execution order

1. full repo pytest;
2. exact source-artifact SHA verification;
3. `prepare` outcome-independent regime cache;
4. inspect only regime coverage/context-equivalence/cache provenance;
5. if fragmentation gate fails: document BLOCKED and stop;
6. if coverage passes: freeze cache/manifest hashes;
7. run exact V2 control F1-F4;
8. prove control equivalence with immutable V2 reference;
9. only after PASS, fit/score NORMAL and STRESS experts;
10. apply absolute + overall paired + regime-specific frozen gates;
11. update ledger/checkpoint/handoff/status and stop for ChatGPT review.

## Local validation status

Full repository pytest and real cache preparation were **not executed in the ChatGPT connector runtime**, because the user's frozen Windows research store is not mounted here.

Therefore no claim is made yet about:

- actual regime coverage;
- cache SHA/row count;
- control equivalence;
- specialist metrics;
- V3-C verdict.

These must be produced by the authorized local run.

## Hard stop boundary

Do not start V3-D, V3-E, Structure+Regime integration, F5/F6, fresh-forward access, probability calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live, or main merge.