# Ranking V4 Final Alpha Hypothesis Ledger V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **V4-A A1/A2 RESERVED / PRE-OUTCOME — 0 V4 CANDIDATES VIEWED**

V4 is the final alpha-generation program. The final V3 historical-development architecture `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` is the immutable common benchmark.

The seven-family design arena is frozen in `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`. A family enters this ledger only when a concrete candidate ordinal is reserved.

The cumulative historical evaluated-candidate count entering V4 is `9`: V3 ordinals `001..007` and `010..011` were viewed; V3-D ordinals `008..009` remain blocked/unviewed and therefore are not counted as evaluated results.

## Reserved V4-A first-pass ordinals

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 012 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-CONTROL-012` | exact frozen V3-B 33-feature HGB control | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 013 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-IMPACT-013` | exact V3-B + frozen 3-feature Impact/Absorption bundle | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 014 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` | exact V3-B + frozen 4-feature Persistent Directional Participation bundle | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |

No A1+A2 integration ordinal is reserved. One integration candidate may be created only after both ordinals `013` and `014` independently pass their frozen first-pass gates.

## V4-A frozen identities

Controlling specification:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

Git blob identity at freeze: `e32fa69596291f418ae797613da219bd0d3cf69c`.

First-pass architecture set is exactly:

1. ordinal `012` exact V3-B control;
2. ordinal `013` A1 Impact/Absorption;
3. ordinal `014` A2 Persistent Directional Participation.

A1 and A2 must be completely specified and implemented before either V4 outcome result is inspected. Their first run is atomic/parallel-equivalent on the same V2F1..V2F6 development folds.

## Outcome-access boundary

At this ledger state:

- V4-A result viewed: `false` for all three reserved ordinals;
- cumulative evaluated-candidate count remains `9`;
- V2F1..V2F6 outcomes are known historical-development information from earlier research, but no V4-A candidate has yet been fitted/scored against them;
- sessions `1225+` are sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no V4-A integration candidate exists;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge is authorized.

## Permanent accounting rule

Once an ordinal's V4 outcome is viewed, it remains in the denominator permanently. A mechanical/spec/data/provenance block before candidate scoring does not count as an evaluated result and must remain documented as a block rather than fabricated as a model failure.
