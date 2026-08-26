# CA-Aware Feature-Basis Policy V1

Status: `FROZEN_POLICY_PENDING_IMPLEMENTATION`
Date: 2026-08-26
Owner lane: Research Integrity / Data QA Gate V1
Incident: `INC-001 — Historical CA / backward feature price-basis integrity`

## Purpose

This policy defines how backward-looking research/model features must behave when a corporate action may make pre-event and post-event market-price observations mechanically incompatible.

The default remediation is **quarantine/reset by compatible price-basis epoch**. It is deliberately not a generic historical price-adjustment policy.

The policy exists to prevent this failure mode:

```text
pre-event raw price basis
        ↓
structural corporate action
        ↓
post-event raw price basis
        ↓
rolling / lagged feature silently mixes both bases
```

The controlling principle is:

> A price-basis-sensitive feature is admitted only when every historical dependency used to compute that feature belongs to one source-backed compatible price-basis epoch.

## Scientific boundary

This policy is data/research-integrity remediation. It does not authorize any change to frozen V4-X1 economic hypotheses, feature formulas, hyperparameters, target definitions, Decision V2, Sizing V1, Execution V1, or prospective-evaluation rules.

Implementation under this policy must remain outcome-blind until a separate model decision is explicitly authorized.

## Definitions

### Compatible price-basis epoch

For one ticker, a **compatible price-basis epoch** is a contiguous sequence of official market sessions for which available evidence establishes that price-basis-sensitive historical observations may be compared by the frozen feature formulas without crossing an unresolved structural corporate-action transition.

An epoch boundary is created only by source-backed evidence and explicit event semantics. Calendar adjacency alone is not sufficient.

### Structural CA candidate

A corporate action is a structural CA candidate when it may mechanically change the economic/share basis of raw market prices or make a naive lag/rolling comparison across the event invalid.

### Transition session

The **transition session** is the first official trading session belonging to the new compatible price basis.

A record/listing/payment/announcement date is not automatically the transition session. The relevant date must be established by the event-family contract.

### Price-basis-sensitive dependency

A dependency is price-basis-sensitive when crossing a structural event can alter its meaning. Examples include raw-price returns, prior-close true range, rolling price extrema, price position, ATR-normalized price distances, and any cross-sectional/market transform derived from those quantities.

## Event-family semantics

No generic corporate-action multiplier is permitted across event families.

| Event family | Default basis policy | Generic split-style adjustment allowed? | Minimum requirement |
|---|---|---|---|
| `STOCK_SPLIT` | basis boundary candidate | only with source-backed ratio + resolved transition | official event identity, ratio, transition session |
| `REVERSE_SPLIT` | basis boundary candidate | only with source-backed ratio + resolved transition | official event identity, ratio, transition session |
| `STOCK_DIVIDEND` | basis boundary candidate | no generic split assumption | event-specific semantics + transition session |
| `BONUS_SHARES` | basis boundary candidate | no generic split assumption | event-specific semantics + transition session |
| `RIGHTS_HMETD` | basis boundary candidate | **no** | transition session; terms/TERP required only if an adjustment is later proposed |
| `MANDATORY_CONVERSION` | basis boundary candidate | **no** | event-specific semantics + transition session |
| `CAPITAL_RESTRUCTURING` | basis boundary candidate | **no** | event-specific semantics + transition session |
| `CASH_DIVIDEND` | not a basis reset by default | not applicable | raw-price economic gap is retained unless source adjustment regime itself changes |

Unknown/new event families default to `UNKNOWN` and cannot be silently treated as non-events.

## Required event evidence contract

A structural event used to create or reject a basis boundary must carry, at minimum:

```text
ticker
event_family
event_identity
effective_transition_state
transition_session or bounded transition interval
source_ref
evidence_id
evidence_sha256
```

When applicable, also require:

```text
ratio
subscription/offer price
rights ratio
conversion terms
record date
cum date
ex date
listing date
published_at / first-known semantics
```

### Effective transition state

Allowed states:

```text
RESOLVED
BOUNDED_UNRESOLVED
UNRESOLVED
NOT_BASIS_CHANGING
```

`RESOLVED` requires one exact official transition session.

`BOUNDED_UNRESOLVED` means the transition is known to fall inside an explicit official-session interval but the exact session is unresolved.

`UNRESOLVED` means the available evidence cannot safely bound the transition.

`NOT_BASIS_CHANGING` must be justified by event-family semantics, not absence of an observed price jump.

## Basis-epoch construction

### Resolved event

For a resolved structural event:

```text
... epoch N ... | transition session | ... epoch N+1 ...
```

No price-basis-sensitive dependency may cross that boundary.

The implementation should assign a deterministic `basis_epoch_id` to each admitted ticker/session row. The exact hash/encoding is implementation-defined, but it must be reproducible from immutable event evidence and session ordering.

### Bounded unresolved event

If the transition is known only within `[L, U]`, any candidate feature row whose historical dependency set could intersect both sides of any transition session in that interval is `UNKNOWN` and research-blocked.

The implementation must not choose the most convenient date inside the interval.

### Unresolved event

If no safe transition interval can be established, the affected scope remains `UNKNOWN`. The implementation must fail closed rather than infer a listing/record date or reconstruct a factor from the observed price jump.

The exact blocked interval must be documented by the application/audit using the strongest source-backed bounds available; if it cannot be bounded, the incident remains unresolved for that ticker/event scope.

## Feature dependency admission

The policy is dependency-based, not a blanket arbitrary `N`-day deletion rule.

For every price-basis-sensitive source feature `f` at ticker `i`, session `t`, define the exact historical dependency set `D(i,t,f)` under the frozen formula.

Admission rule:

```text
BASIS_SAFE(i,t,f) =
    all price-basis-sensitive observations in D(i,t,f)
    carry the same compatible basis_epoch_id
    AND no required dependency is UNKNOWN
```

If false or unknown:

```text
feature value = not research-admitted
basis_integrity_state = FAIL or UNKNOWN
```

The implementation must not forward-fill, splice, rescale, or substitute an alternate historical observation to make the feature available.

## Current V4-X1 dependency families

The frozen V4 control representation includes at least these relevant backward dependency families:

```text
close_return_5
close_return_20
ATR14 / atr14_over_close
rolling-20 high/low derived features
rolling-60 high/low derived features
relative_volume_20
log_regular_value_relative_20
60-session liquidity qualification/history
cross-sectional ranks derived from source features
market breadth / medians derived from source features
stock-minus-market relative features
```

Not every family is equally sensitive to a price-basis event. Implementation must classify each dependency explicitly rather than marking all rolling data as contaminated by association.

For example, raw traded `regular_market_value` may remain economically comparable across a split even when raw share price and volume scale change. That conclusion must come from field semantics and tests, not from assuming all 60-session windows share one risk.

## Reset semantics for sequential features

A correct implementation may recompute sequential features independently inside each compatible epoch.

Examples:

- lagged return: lag lookup may not leave the epoch;
- prior-close true range: `previous_close` may not come from a prior epoch;
- rolling extrema: the rolling set must contain only same-epoch prices;
- ATR: all true-range observations used by the rolling ATR must themselves be basis-safe;
- normalized price-distance features inherit all dependencies of both the price/extrema and ATR components.

The first post-event row does not receive a synthetic adjusted predecessor merely to preserve continuity.

## Model-row admission

A model/research row is CA-basis-admitted only when every required frozen feature for that row is available under its own basis-integrity contract.

For the frozen V4-X1 representation, the model-row recovery point after a resolved event is therefore determined by the **maximum exact dependency geometry among required features**, not by a hand-written fixed number of days.

The current representation contains dependencies reaching approximately 60 official sessions, so a structural event can affect a long post-event interval. The implementation must derive the actual safe boundary from the frozen dependency graph and official-session indexes.

## Cross-sectional and market spillover policy

Directly invalid source-feature values must be removed from the corresponding cross-sectional transformation before ranks/medians/breadth are computed.

Rules:

1. cross-sectional ranks operate only on finite, basis-admitted values for that source feature;
2. market medians and breadth operate only on finite, basis-admitted values for their exact source feature;
3. stock-minus-market features use the recomputed basis-safe market statistic;
4. an invalid direct ticker may therefore create legitimate deterministic spillover in other tickers' rank/context features;
5. direct and spillover changes must be reported separately;
6. universe membership/count semantics are not changed merely because a price-derived feature is invalid, unless the universe feature's own input contract is independently affected.

No stale pre-remediation rank/context column may be joined back after direct feature quarantine.

## Missingness semantics

CA-basis invalidity is not ordinary missing data.

Required states:

```text
BASIS_SAFE
BASIS_UNSAFE
BASIS_UNKNOWN
NOT_APPLICABLE
```

A later model/data layer may map unsafe/unknown feature values to NaN for computation, but the semantic reason must remain separately observable in the audit lineage.

`BASIS_UNKNOWN` blocks required Research Admission checks.

## Adjustment policy

V1 does **not** authorize historical price adjustment as the remediation mechanism.

No implementation may manufacture adjusted H/L/C using inferred factors from adjacent prices.

A future explicit adjustment contract would need separate source/event-family proof for:

- adjustment factor/terms;
- exact transition session;
- H/L/C treatment;
- Open treatment;
- volume/share-count treatment;
- value/turnover treatment;
- rounding/tick effects;
- multi-event compounding;
- PIT/revision semantics.

Until such a contract exists, quarantine/reset is authoritative.

## BBCA golden-case rule

BBCA 2021 is the first intended golden regression case, but it is not fully promoted as a source-bound golden case merely because code contains `2021-10-13` and `1:5` constants.

Promotion requires a fixture or immutable input that binds the expected event identity to canonical evidence, including evidence SHA-256 and transition semantics.

The golden case must prove both:

1. the backward feature path cannot cross the event boundary; and
2. historical exact final-fit membership remains separately evaluated rather than inferred from feature exposure.

## Required adversarial/golden regression cases

Before `INC-001` can close, regression protection must cover at least:

1. **resolved split** — raw pre/post scale discontinuity cannot enter one backward price feature;
2. **unknown transition date** — fails closed; no record/listing-date inference;
3. **rights/HMETD** — cannot be processed by a generic split multiplier;
4. **cross-sectional spillover** — quarantining one direct source value deterministically recomputes affected ranks/context;
5. **cash dividend** — does not create a price-basis reset solely because of an ex-dividend price gap;
6. **multiple structural events** — produces distinct deterministic epochs and cannot bridge across either boundary;
7. **source-bound BBCA case** — event truth comes from pinned evidence, not only hard-coded test constants;
8. **no outcome dependency** — basis admission result is identical without loading targets/outcomes.

## Outcome-blind remediation sequence

The authorized implementation sequence is:

```text
immutable CA evidence
        ↓
source/event semantics
        ↓
transition-state resolution
        ↓
basis epochs / UNKNOWN scopes
        ↓
backward dependency admission
        ↓
recompute direct source features
        ↓
recompute cross-sectional + market context
        ↓
recompute exact feature-input identity deltas
        ↓
independent red-team + Research Integrity gate
```

Do not insert model performance or protected outcomes into this sequence.

## Required remediation artifacts

A future implementation/application must preserve at minimum:

```text
ca_basis_event_ledger.csv
ca_basis_epoch_ledger.csv
feature_basis_admission.csv or equivalent auditable state
basis_anomaly_census.csv
exact_input_delta_direct.csv
exact_input_delta_spillover.csv
input_manifest.json
result_summary.json
MANIFEST.json
```

Names may differ, but the evidence content must be equivalent and immutable/hash-pinned.

## Model decision boundary

A nonzero change to exact historical training inputs does not automatically authorize a refit in this lane.

After clean input recomputation, report separately:

```text
EXACT_FINAL_FIT_INPUT_CHANGE = NONE | PRESENT | UNKNOWN
MODEL_ARTIFACT_INTEGRITY = PASS | FAIL | UNKNOWN | NOT_EVALUATED
PERFORMANCE_MATERIALITY = NOT_EVALUATED unless separately authorized
```

If a clean same-science refit is later required, it must use the exact frozen model/science contract and occur under a separate explicit authorization. It must not become an opportunity for retuning/rescue search.

## Prospective boundary

This policy does not reset, rewrite, or reinterpret existing prospective counters/evidence.

Any later decision to create a replacement model generation must define its own prospective evaluation boundary explicitly. No automatic retroactive score replacement or counter migration is permitted.

## Incident closure gate

`INC-001` may reach `CLOSED_REGRESSION_PROTECTED` only when all are true:

```text
root cause documented
blast radius bounded under the frozen policy
transition semantics source-bound
basis-safe implementation validated
permanent golden/adversarial tests pass
independent red-team passes
Research Integrity gate rerun passes
coordination status updated
```

A simple data patch is insufficient for closure.

## Explicit non-authorizations

This policy does not authorize:

- protected outcome access;
- historical performance review;
- V4-X1 refit/tuning;
- model-selection rescue;
- prospective counter mutation/reset;
- retroactive trade/fill reconstruction;
- generic market-wide price adjustment;
- canonical artifact overwrite;
- provider writes or production runtime changes.
