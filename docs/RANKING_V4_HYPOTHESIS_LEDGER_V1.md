# Ranking V4 Final Alpha Hypothesis Ledger V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **V4-A CLOSED / V4-B 015..017 RESERVED PRE-OUTCOME / 3 V4 CANDIDATES VIEWED**

V4 is the final alpha-generation program. The final V3 historical-development architecture `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` is the immutable common benchmark.

The seven-family design arena is frozen in `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`. A family enters this ledger only when a concrete candidate ordinal is reserved.

The cumulative historical evaluated-candidate count entering V4 is `9`: V3 ordinals `001..007` and `010..011` were viewed; V3-D ordinals `008..009` remain blocked/unviewed and therefore are not counted as evaluated results.

## V4-A first-pass ordinals — CLOSED

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 012 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-CONTROL-012` | exact frozen V3-B 33-feature HGB control | `FIRST_PASS_COMPLETE` | `true` | `CONTROL_EQUIVALENCE_PASS` |
| 013 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-IMPACT-013` | exact V3-B + frozen 3-feature Impact/Absorption bundle | `FIRST_PASS_COMPLETE` | `true` | `FAIL` |
| 014 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` | exact V3-B + frozen 4-feature Persistent Directional Participation bundle | `FIRST_PASS_COMPLETE` | `true` | `FAIL` |

No A1+A2 integration ordinal exists. Both challengers failed their frozen gates; V4-A is closed with no survivor and may not be rescued.

### V4-A frozen identity/result

Controlling specification:

`docs/RANKING_V4_A_PARTICIPATION_QUALITY_SPEC_V1.md`

Git blob identity at freeze: `e32fa69596291f418ae797613da219bd0d3cf69c`.

Outcome-blind audit completed before any V4-A fit/score:

- cache status: `RANKING_V4_A_PARTICIPATION_CACHE_FROZEN_PRE_OUTCOME`;
- cache rows/tickers/sessions: `286,453 / 737 / 20..1224`;
- cache SHA-256: `a487e14625942cba849b499730113cf8d0f9b3f08e866177c79642079cef6aab`;
- manifest SHA-256: `b9f15e5363e2ea0a2f912fe31a563fc45ebf7ed4788ee524540b1cdb41d308cc`;
- audit SHA-256: `c89a19d1cce390b4734dc1de8c2cc08994217248478fd2e8025d94e90f93d31a`.

First-pass result:

- exact control equivalence PASS;
- A1 ordinal `013`: FAIL;
- A2 ordinal `014`: FAIL;
- survivors `[]`;
- integration not authorized/executed;
- cumulative historical evaluated-candidate count after V4-A: `12`.

Result checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`

Closure checkpoint:

`docs/checkpoints/2026-08-10_RANKING_V4_A_REVIEW_CLOSED_V4_B_SPEC_AUTHORIZED.md`

## V4-B reserved first-pass ordinals — PRE-OUTCOME

Hypothesis:

`V4-B-PRICE-PATH-V1`

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 015 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-CONTROL-015` | exact frozen V3-B 33-feature HGB control | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 016 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-COHERENCE-016` | exact V3-B + frozen B1 3-feature Path Coherence / Jump Concentration bundle | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 017 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017` | exact V3-B + frozen B2 3-feature Range Acceptance / Rejection bundle | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |

No B1+B2 integration ordinal exists. One integration candidate may be designed only if ordinals `016` and `017` both independently PASS their frozen first-pass gates and receive separate specification/review/authorization.

### V4-B frozen identities

Experiment map:

`docs/RANKING_V4_B_PRICE_PATH_EXPERIMENT_MAP_V1.md`

Controlling specification:

`docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md`

Frozen spec Git blob:

`a750c28831b95b1c88640c5879289da5f2c05446`

Review addendum:

`docs/RANKING_V4_B_PRICE_PATH_SPEC_REVIEW_ADDENDUM_V1.md`

First-pass architecture set is exactly:

1. ordinal `015` exact V3-B control;
2. ordinal `016` B1 Path Coherence / Jump Concentration;
3. ordinal `017` B2 Range Acceptance / Rejection.

B1 and B2 must be completely implemented/frozen before either outcome result is inspected. Their first score, if separately authorized after the outcome-blind audit, must be atomic/parallel-equivalent over V2F1..V2F6.

The V4-B promotion gate is inherited unchanged from V4-A. No gate relaxation or alternate lookback/model/feature rescue is allowed after outcome access.

## Outcome-access boundary

At this ledger state:

- V4-A result viewed: `true` for ordinals `012..014`;
- V4-B result viewed: `false` for ordinals `015..017`;
- V4 evaluated-candidate count remains `3`;
- cumulative historical evaluated-candidate count remains `12`;
- V2F1..V2F6 are known historical-development periods and are not independent validation for V4;
- sessions `1225+` are sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no V4-B integration candidate exists;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge is authorized.

## Permanent accounting rule

Once an ordinal's V4 outcome is viewed, it remains in the denominator permanently. A mechanical/spec/data/provenance block before candidate scoring does not count as an evaluated result and must remain documented as a block rather than fabricated as a model failure.
