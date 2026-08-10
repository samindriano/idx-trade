# Ranking V4 Final Alpha Hypothesis Ledger V1

Date: 2026-08-10 (Asia/Jakarta)
Status: **V4-A CLOSED / V4-B 015..017 PRE-OUTCOME / V4-C 018..019 PRE-OUTCOME / 3 V4 CANDIDATES VIEWED**

V4 is the final alpha-generation program. The final V3 historical-development architecture `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005` is the immutable common benchmark.

The seven-family design arena is frozen in `docs/RANKING_V4_FINAL_ALPHA_ARENA_V1.md`. A family enters this ledger only when a concrete candidate ordinal is reserved.

The cumulative historical evaluated-candidate count entering V4 was `9`: V3 ordinals `001..007` and `010..011` were viewed; V3-D ordinals `008..009` remain blocked/unviewed. V4-A later viewed ordinals `012..014`, so the current cumulative historical evaluated count remains `12` until another separately authorized outcome run occurs.

## V4-A first-pass ordinals — CLOSED

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 012 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-CONTROL-012` | exact frozen V3-B 33-feature HGB control | `FIRST_PASS_COMPLETE` | `true` | `CONTROL_EQUIVALENCE_PASS` |
| 013 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-IMPACT-013` | exact V3-B + frozen A1 3-feature Impact/Absorption bundle | `FIRST_PASS_COMPLETE` | `true` | `FAIL` |
| 014 | `V4-A-PARTICIPATION-V1` | `V4-A-PARTICIPATION-V1-PERSIST-DIRECTION-014` | exact V3-B + frozen A2 4-feature Persistent Directional Participation bundle | `FIRST_PASS_COMPLETE` | `true` | `FAIL` |

No A1+A2 integration ordinal exists. V4-A is closed and may not be rescued.

Controlling result:

`docs/checkpoints/2026-08-10_RANKING_V4_A_PARTICIPATION_FIRST_PASS_RESULT.md`

## V4-B reserved first-pass ordinals — PRE-OUTCOME

Hypothesis: `V4-B-PRICE-PATH-V1`.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 015 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-CONTROL-015` | exact frozen V3-B 33-feature HGB control | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 016 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-COHERENCE-016` | exact V3-B + B1 Path Coherence / Jump Concentration | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 017 | `V4-B-PRICE-PATH-V1` | `V4-B-PRICE-PATH-V1-RANGE-ACCEPTANCE-017` | exact V3-B + B2 Range Acceptance / Rejection | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |

Frozen spec:

`docs/RANKING_V4_B_PRICE_PATH_SPEC_V1.md`

Git blob: `a750c28831b95b1c88640c5879289da5f2c05446`.

No B1+B2 integration ordinal exists. One may be designed only if 016 and 017 both independently PASS under a separate future specification/review.

V4-B implementation is complete pre-outcome. Its next permitted step is only the Windows-local cache preparation + outcome-blind audit in:

`coordination/handoffs/IDX-RANKING-V4-B-PRICE-PATH-CACHE-AUDIT.md`

## V4-C reserved first-pass ordinals — PRE-OUTCOME

Hypothesis: `V4-C-CROSS-SECTIONAL-CONTEXT-V1`.

V4-C was frozen while V4-B still had no viewed outcome. Its definition therefore may not be adapted to any later V4-B result.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 018 | `V4-C-CROSS-SECTIONAL-CONTEXT-V1` | `V4-C-CROSS-SECTIONAL-CONTEXT-V1-CONTROL-018` | exact frozen V3-B 33-feature HGB control | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |
| 019 | `V4-C-CROSS-SECTIONAL-CONTEXT-V1` | `V4-C-CROSS-SECTIONAL-CONTEXT-V1-DISPERSION-019` | exact V3-B + frozen 4-feature cross-sectional opportunity-dispersion context | `IMPLEMENTATION_PRE_OUTCOME` | `false` | `UNVIEWED_RESERVED` |

Frozen appended context features:

1. `v4c_market_return_iqr_5`;
2. `v4c_market_return_iqr_20`;
3. `v4c_market_atr_iqr`;
4. `v4c_market_close_position_iqr_20`.

The context is computed per signal date from the **full causal primary-liquid universe** using existing V2 baseline-feature semantics, minimum 50 finite cross-sectional observations and linear IQR quantiles. It is not computed from label-resolved/model rows.

There is only one V4-C challenger. No alternate dispersion estimator/quantile-band candidate and no within-family integration candidate exists.

Controlling files:

- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_EXPERIMENT_MAP_V1.md`;
- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_V1.md`;
- frozen spec Git blob `43f222f31c7c0ea15e870d22b066aae95858c81f`;
- `docs/RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_SPEC_REVIEW_ADDENDUM_V1.md`;
- implementation checkpoint `docs/checkpoints/2026-08-10_RANKING_V4_C_CROSS_SECTIONAL_CONTEXT_IMPLEMENTED_PRE_OUTCOME.md`.

V4-C implementation + focused tests are complete pre-outcome. Its next permitted step is only the Windows-local cache preparation + outcome-blind audit in:

`coordination/handoffs/IDX-RANKING-V4-C-CROSS-SECTIONAL-CONTEXT-CACHE-AUDIT.md`

## Shared V4 gate and outcome-access boundary

V4-B and V4-C inherit the exact same challenger gate frozen for V4-A. No family receives easier thresholds after observing previous failures.

At this ledger state:

- V4-A results viewed: `true` for ordinals `012..014`;
- V4-B results viewed: `false` for `015..017`;
- V4-C results viewed: `false` for `018..019`;
- V4 evaluated-candidate count remains `3`;
- cumulative historical evaluated-candidate count remains `12`;
- V2F1..V2F6 are historical-development knowledge, not independent V4 validation;
- sessions `1225+` remain sealed from V4 historical-development materialization;
- post-2026-07-31 fresh-forward outcomes remain unaccessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten;
- no calibration, Stage 6, `IDX-VAL-002`, execution/PnL, Kelly, paper/live or main merge is authorized.

## Permanent accounting rule

Once an ordinal's outcome is viewed it remains in the denominator permanently. A mechanical/spec/data/provenance block before scoring does not count as an evaluated result and must remain documented as a block rather than fabricated as a model failure.