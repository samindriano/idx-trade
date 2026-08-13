# Handoff — IDX Ranking V3-C Regime Local Prepare + F1-F4 Run

Date: 2026-08-10 (Asia/Jakarta)

Status: **AUTHORIZED — EXECUTE FROZEN V3-C LOCALLY; NO REDESIGN**

## Objective

Execute the already-frozen, independently reviewed, and implemented V3-C Regime-Specialization experiment against the exact local research artifacts.

This is execution/documentation only. Do not redesign the regime definition, add variants, change thresholds, blend experts, inherit Structure-Lite, or alter gates.

## Required reads

Pull/fetch the latest `research/idx-ranking-v2-spec-v1`, then read:

1. `docs/CURRENT_STATUS.md`
2. `docs/RANKING_V3_REGIME_SPEC_V1.md`
3. `docs/RANKING_V3_REGIME_SPEC_REVIEW_ADDENDUM_V1.md`
4. `docs/checkpoints/2026-08-10_RANKING_V3_REGIME_IMPLEMENTED_RUN_AUTHORIZED.md`
5. `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_REVIEW_PASS.md`
6. `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
7. `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`
8. `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`
9. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
10. `src/idx_trade/research_v3_regime.py`
11. `src/idx_trade/ranking_v3_regime.py`
12. `tests/test_ranking_v3_regime.py`

The review addendum controls where it clarifies the original spec.

## Frozen candidate set

Exactly:

- ordinal 006: exact V2 global `HGB_XS_MARKET` control;
- ordinal 007: one frozen two-state specialist with NORMAL and STRESS exact-V2 HGB experts.

No Structure-Lite features are included in ordinal 007.

## Frozen source hashes

Locate exact artifacts and fail closed if missing or ambiguous:

- signal-research panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- security master SHA-256: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- V2 prepared table SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`
- V2 prepared manifest SHA-256: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`
- frozen V2 HGB summary SHA-256: `24cd9c6d1a978b35126955802fcf4852e1f3d50a489540b761052a9221a5327d`
- frozen V2 HGB predictions SHA-256: `5a9df1c66a34c0d54760015c49ccb356be984703935c96ee8218ae863c47b179`

Frozen V3-C spec identities:

- spec Git blob: `2a2f48d68f5d3df839c61191d4a11fa870470b00`
- review-addendum Git blob: `a13c5ae103908311968e38c6ded233b7a1cbd901`

## Phase 1 — preflight

1. Verify branch and HEAD; working tree must be clean before execution.
2. Run full repository pytest from the explicit repo root.
3. Record passed/failed/warnings/duration.
4. If tests fail, do **not** build cache or score models.

A purely engineering correction is permitted only before cache/outcome work, only when required to make the frozen specification executable, and must not change regime definitions/candidate/gates. Commit such a correction, rerun full pytest, and explicitly report it. If the required change touches research semantics, stop for ChatGPT review instead.

## Phase 2 — outcome-independent regime cache

Use the existing module:

`python -m idx_trade.ranking_v3_regime prepare`

with exact paths for panel/calendar/security-master/V2 prepared/V2 manifest/spec/addendum, the exact current implementation commit, and a **new empty output directory**.

The prepare step must not compute target-performance metrics.

Required cache checks:

- manifest status `RANKING_V3_C_REGIME_DISCOVERY_CACHE_FROZEN`;
- exact V2 rows/order/25-feature prefix preserved;
- max signal session <= 984;
- `v2f5_v2f6_materialized=false`;
- `outcome_metrics_computed=false`;
- recomputed market-context max abs differences <= `1e-12` for all three regime source fields;
- state values only NORMAL/STRESS/MISSING_WARMUP;
- stress votes only 0/1/2/3 when observed;
- no duplicate/orphan/misaligned rows;
- record cache SHA + manifest SHA.

### Fragmentation gate

Inspect only outcome-independent counts/dates from the prepare manifest.

For every F1-F4 fold:

Training, each NORMAL/STRESS:

- >=40 dates;
- >=5,000 rows.

Validation, each NORMAL/STRESS:

- >=8 dates;
- >=500 rows;
- MISSING_WARMUP rows = 0.

If any gate fails:

- do **not** run control or specialist outcomes;
- document `V3_C_REGIME_BLOCKED_KEEP_V2_CONTROL`;
- do not modify quantile windows/votes/thresholds;
- update checkpoint/handoff/status and stop.

If all pass, freeze the new cache/manifest hashes and continue.

## Phase 3 — exact control then specialist

Use:

`python -m idx_trade.ranking_v3_regime run`

with the frozen V3-C cache/manifest, immutable V2 HGB reference directory, frozen spec/addendum, exact implementation commit, and another new empty output directory.

Mandatory order inside the runner:

1. exact V2 control on F1-F4;
2. exact control equivalence against immutable V2 predictions/metrics;
3. if equivalence FAIL, stop; do not interpret specialist;
4. if PASS, fit NORMAL and STRESS experts;
5. route each validation date to its frozen market-wide expert;
6. compute exact overall V2 metrics + per-regime metrics;
7. apply absolute, overall-paired, and regime-specific frozen gates;
8. no rescue/variant/rescaling/blending.

## Promotion gates

The code/spec controls exact rules. Report at minimum:

### Overall

- median/q25/worst PR-delta improvement;
- PR-not-below-control fold count;
- median ROC change;
- median Q5-Q1 change;
- top-decile diagnostic.

### By regime

For NORMAL and STRESS separately:

- fold rows/dates/prevalence;
- median/q25/worst paired PR-delta improvement;
- nonnegative fold count;
- median ROC change;
- median Q5-Q1 change;
- median top-decile lift change;
- F4 behavior.

Promotion additionally requires the frozen regime gate, especially STRESS median PR improvement >= +0.001 and bounded NORMAL/worst-cell degradation.

## Deterministic decisions

Possible final states:

- `V3_C_REGIME_BLOCKED_KEEP_V2_CONTROL`
- `V3_C_REGIME_KILL_KEEP_V2_CONTROL`
- `V3_C_REGIME_PROMOTE_TWO_STATE_EXPERTS`

No alternative state/threshold/expert formulation may be tried under this hypothesis after outcomes are viewed.

## Documentation after run

If actual V3-C outcomes are scored:

- update ledger ordinals 006/007 and cumulative count to 7;
- add dated F1-F4 result checkpoint;
- add result handoff;
- update `CURRENT_STATUS.md`;
- record cache/manifest/metrics/prediction/regime-metrics/paired/model/runtime/verdict hashes;
- commit + push;
- verify working tree clean and branch synchronized;
- stop for ChatGPT review.

If blocked before any candidate outcome, keep cumulative evaluated count at 5 and record why.

## Hard prohibitions

Do not:

- include V3-B Structure-Lite in V3-C;
- reopen V3-A or alter V3-B;
- change the 252/126/q25/q75/2-of-3 regime definition;
- add a third state or second candidate;
- z-score, percentile-normalize, calibrate, align, or blend expert scores;
- score/load/summarize V2F5/V2F6;
- inspect reserved post-2026-07-31 V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-D, V3-E, integration, F5/F6, calibration, Stage 6, IDX-VAL-002, execution-PnL, Kelly, paper/live, or main merge.
