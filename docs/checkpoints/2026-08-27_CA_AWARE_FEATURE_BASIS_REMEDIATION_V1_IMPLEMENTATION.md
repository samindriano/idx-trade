# CA-Aware Feature-Basis Remediation V1 — Implementation Checkpoint

Date: 2026-08-27 Asia/Jakarta
Branch: `data/ca-aware-feature-basis-remediation-v1`
Stacked PR: `#108` (base: `audit/research-integrity-data-qa-gate-v1`)
Controlling incident: `INC-001 — Historical CA / backward feature price-basis integrity`
Controlling policy: `docs/research_integrity/CA_AWARE_FEATURE_BASIS_POLICY_V1.md`

## Status

`IMPLEMENTATION_PRIMITIVES_VALIDATED_APPLICATION_BLOCKED_ON_SOURCE_SEMANTICS_AND_COVERAGE`

This checkpoint does not claim that historical V4-X1 inputs are remediated. It establishes the fail-closed implementation primitives required before any historical application is allowed.

## Implemented

### 1. Event transition contract

`src/idx_trade/ca_feature_basis_v1.py`

Supports explicit transition states:

- `RESOLVED`
- `BOUNDED_UNRESOLVED`
- `UNRESOLVED`
- `NOT_BASIS_CHANGING`

Resolved transitions require an exact official session. Bounded unresolved transitions require an explicit official-session interval. Unresolved transitions are not assigned inferred dates. Structural events declared `NOT_BASIS_CHANGING` require explicit justification. Cash dividends cannot create a V1 price-basis reset.

All events require source/evidence identity and SHA-256 provenance.

### 2. Exact frozen dependency geometry

The implementation models dependency positions as observed ticker rows, matching pandas `shift`/`rolling` semantics in the frozen historical feature builder rather than assuming calendar-day offsets.

Current H/L/C-derived V4 source-feature contracts include:

- `close_return_5`: `(t-5, t)`
- `close_return_20`: `(t-20, t)`
- `atr14_over_close`: full price dependency `t-14..t`
- rolling-20 price-position/distance features: `t-19..t`
- rolling-60 price-distance features: `t-59..t`

Therefore a resolved transition at `t0` has exact direct exposure counts, after full pre-event warmup, of:

- 5 rows for `close_return_5`;
- 14 rows for ATR14-derived features;
- 20 rows for `close_return_20`;
- 59 rows for `rolling(60)` H/L/C features.

The earlier audit's `60-session` wording was a conservative window label. The implementation now uses exact dependency geometry: the first rolling-60 row containing 60 entirely new-basis observations is `t0+59`.

Volume/value features are not silently classified as H/L/C price-basis-sensitive in this module. Their unit/economic comparability remains a separate data contract.

### 3. Basis epochs and feature admission

Resolved structural transitions create deterministic per-ticker basis epoch IDs.

Direct feature states are:

- `BASIS_SAFE`
- `BASIS_UNSAFE`
- `BASIS_UNKNOWN`
- `NOT_APPLICABLE`

A direct feature is unsafe when exact dependencies span a resolved epoch boundary. It is unknown when a bounded/unbounded unresolved transition could invalidate the dependency geometry.

No forward-fill, inferred adjustment, synthetic predecessor, or generic CA multiplier is introduced.

### 4. CA no-event coverage is mandatory

`src/idx_trade/ca_feature_basis_gate_v1.py`

A second fail-closed layer prevents this false inference:

```text
no event in event ledger
=> therefore no event occurred
```

The authorized V1 gate requires explicit per-session CA coverage evidence. Missing or explicitly unknown coverage converts an otherwise safe dependency to `BASIS_UNKNOWN`.

Coverage is checked across every official session between the earliest and latest exact dependency observations, including sessions where the ticker itself has no observation row.

This is required because the INC-001 audit found substantial market-wide no-event coverage gaps.

### 5. Event-family semantic certification

The application gate requires source-bound semantic certification before an event may be promoted from `UNRESOLVED` to a resolved/bounded/non-basis-changing transition state.

This prevents known taxonomy inconsistencies (for example voluntary-vs-mandatory conversion mappings) from silently becoming basis boundaries.

### 6. Safe adapters for current audit evidence

`src/idx_trade/ca_feature_basis_inputs_v1.py`

The existing strict CA census can be imported only as:

```text
SEMANTICS UNCERTIFIED
+ TRANSITION UNRESOLVED
```

Its `candidate_date` and source action labels are preserved as metadata but are never promoted to transition truth.

CA coverage intervals may be expanded to explicit official-session coverage. Missing intervals remain absent and are interpreted downstream as unknown; no gap filling occurs.

### 7. Downstream mask boundary

Direct unsafe/unknown/not-applicable source features may be masked only before downstream cross-sectional transformation. Stale historical ranks/market context must not be joined back after masking.

The current primitive intentionally does not refit models or recompute protected performance.

## Regression coverage

Synthetic/adversarial tests cover:

- resolved split crossing;
- exact 5/14/20/59 dependency recovery;
- bounded unresolved transition;
- unbounded unresolved transition;
- cash dividend non-reset semantics;
- rights/HMETD non-basis-changing claim requires explicit justification;
- multiple resolved structural events / multiple epochs;
- fail-closed model-row aggregation;
- direct feature masking;
- strict evidence SHA validation;
- missing CA coverage does not mean no event;
- explicit unknown coverage blocks dependency windows;
- missing intermediate official-session coverage blocks even if ticker observation is absent;
- resolved transition requires semantic certification;
- prior strict census import never promotes semantics/transition;
- coverage interval expansion is sparse/inclusive and rejects overlap/non-session boundaries.

## CI

PR #108 GitHub Actions run `32995968505`:

- full pytest: **282 passed, 0 failed**;
- warnings: 4 existing tradability deprecation warnings;
- conclusion: `success`.

An earlier run at pre-fix head failed one new test because the synthetic transition was placed before a full 60-observation pre-event warmup. The fixture was corrected to isolate recovery geometry; the feature-basis algorithm was not loosened to satisfy the test.

## Current blocker

Historical application remains `NO-GO` because the evidence needed to certify the transition graph is still incomplete:

1. the strict 26-event census remains effective-date unresolved;
2. event-family taxonomy contains unresolved inconsistencies;
3. market-wide structural-CA no-event coverage is incomplete;
4. source-bound BBCA event truth is not yet wired into a permanent repository fixture/ledger;
5. no clean historical feature recomputation has therefore been authorized.

## Next authorized work

Outcome-blind only:

```text
resolve source/event taxonomy
-> establish source-backed transition session or bounded interval
-> establish market-wide CA coverage intervals
-> build certified event + coverage ledgers
-> run basis admission
-> recompute direct H/L/C-derived source features
-> recompute cross-sectional ranks / market context from admitted direct values
-> quantify exact final-fit input delta
-> independent red-team
-> Research Integrity gate rerun
```

Until those evidence contracts are satisfied:

```text
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
MODEL_PROMOTION = NOT_EVALUATED
MODEL_REFIT = NOT_AUTHORIZED
PROSPECTIVE_COUNTER_RESET = NO
```

## Explicit non-actions

This implementation did not:

- infer any historical effective date;
- adjust historical H/L/C;
- call a provider;
- access target/outcome/protected evidence;
- fit/refit/score V4-X1;
- modify prospective counters;
- modify runtime/capture systems;
- overwrite canonical historical artifacts.
