# Ranking V4 Final Alpha Hypothesis Ledger V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **V4-A A1/A2 FIRST-PASS RUN AUTHORIZED / 0 V4 CANDIDATES VIEWED**

V4 is the final alpha-generation program. The final V3 historical-development architecture `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` is the immutable common benchmark.

The seven-family design arena is frozen in `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`. A family enters this ledger only when a concrete candidate ordinal is reserved.

The cumulative historical evaluated-candidate count entering V4 is `9`: V3 ordinals `001..007` and `010..011` were viewed; V3-D ordinals `008..009` remain blocked/unviewed and therefore are not counted as evaluated results.

## Reserved V4-A first-pass ordinals

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 012 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-CONTROL-012` | exact frozen V3-B 33-feature HGB control | `FIRST_PASS_RUN_AUTHORIZED` | `false` | `UNVIEWED_RESERVED` |
| 013 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-IMPACT-013` | exact V3-B + frozen 3-feature Impact/Absorption bundle | `FIRST_PASS_RUN_AUTHORIZED` | `false` | `UNVIEWED_RESERVED` |
| 014 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` | exact V3-B + frozen 4-feature Persistent Directional Participation bundle | `FIRST_PASS_RUN_AUTHORIZED` | `false` | `UNVIEWED_RESERVED` |

No A1+A2 integration ordinal is reserved. One integration candidate may be designed only after both ordinals `013` and `014` independently pass their frozen first-pass gates and receives a separate specification/review/authorization.

## V4-A frozen identities

Controlling specification:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

Git blob identity at freeze: `e32fa69596291f418ae797613da219bd0d3cf69c`.

First-pass architecture set is exactly:

1. ordinal `012` exact V3-B control;
2. ordinal `013` A1 Impact/Absorption;
3. ordinal `014` A2 Persistent Directional Participation.

A1 and A2 were completely specified and implemented before either V4 outcome result was inspected. Their first run is atomic/parallel-equivalent on the same V2F1..V2F6 historical-development folds.

## Outcome-blind V4-A cache audit — 2026-08-10

The authorized cache preparation and restricted feature audit completed before any candidate outcome access.

- cache status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- all seven V4-A features have finite rate at least `98.5785%`;
- no constant or below-80%-finite feature;
- no absolute Spearman correlation `>=0.95`;
- highest absolute correlation: `0.8942494476` between `v4a_value_persistence_fraction_5` and `v4a_value_acceleration_log_5v20`;
- audit status: `RANKING_V4_A_PARTICIPATION_OUTCOME_BLIND_AUDIT_COMPLETE`;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`;
- official audit: `binary_target_loaded=false`, `outcome_columns_loaded=false`, `outcome_metrics_computed=false`;
- no V4-A candidate was fitted/scored and no ordinal result was viewed;
- cumulative evaluated-candidate count remains `9`.

The `0.8942` A2 within-bundle redundancy is documented but is below the frozen mechanical-review threshold and is not a causal/specification defect. The already-frozen A2 definition is therefore unchanged.

## First-pass authorization — 2026-08-10

Pre-outcome review completed with decision:

`V4_A_FIRST_PASS_ATOMIC_RUN_AUTHORIZED`

Controlling authorization checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RUN_AUTHORIZED.md`

Execution handoff:

`coordination/handoffs/IDX-RANKING-V4-A-PARTICIPATION-FIRST-PASS-RUN.md`

The authorized scope is exactly one runner invocation containing control + A1 + A2 over F1-F6, with mandatory exact V3-B control equivalence before challenger interpretation. A1 and A2 use their frozen independent PASS/FAIL gates. No integration is executed in the first-pass run.

## Outcome-access boundary

At this ledger state:

- V4-A result viewed: `false` for all three reserved ordinals;
- V4 evaluated-candidate count remains `0`;
- cumulative historical evaluated-candidate count remains `9` until the authorized first-pass result is actually viewed;
- V2F1..V2F6 are known historical-development periods and are not independent validation for V4;
- sessions `1225+` are sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no V4-A integration candidate exists;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge is authorized.

## Permanent accounting rule

Once an ordinal's V4 outcome is viewed, it remains in the denominator permanently. A mechanical/spec/data/provenance block before candidate scoring does not count as an evaluated result and must remain documented as a block rather than fabricated as a model failure.
