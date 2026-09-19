# Alpha Research Program — Data Admission Remediation Contract V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `REMEDIATION_SPEC_ONLY — NOT AN ADMISSION`

## Purpose

This document records the exact evidence still required before the frozen
alpha protocol may open historical target rows. It is derived from the
authoritative `origin/main:docs/research_integrity/DATA_QA_ORCHESTRATION_V1.md`
and the current lane admission audit. It does not change the authoritative
Data QA verdict, open protected outcomes, or authorize a provider probe.

## Current gate

| Gate | Current verdict | Consequence |
|---|---|---|
| `DATA_ADMISSION` | `UNKNOWN` / effectively blocked for this lane | No historical target, IC/ICIR, OOS, economics, or survivor claim may be produced. |
| `RESEARCH_ADMISSION` | `NOT_EVALUATED` | Stage A remains structural-only. |
| `MODEL_PROMOTION` | `NOT_EVALUATED` | No production or prospective action is authorized. |
| `MATERIALITY` | `INDETERMINATE` | Population and as-of authority are not proven. |
| `REMEDIATION_REQUIRED` | `YES` | A separately reviewed admission package is required. |

## Required admission package

All rows below must be satisfied by the same-science source package. A partial
pass on one source, a page-1/category sample, or a complete-looking parquet
file is not sufficient.

### 1. Source semantics and contract

- Identify the authoritative provider/endpoint or immutable file release.
- Define raw versus adjusted price basis, units, market/session scope, and
  regular-market versus other-market semantics.
- Define ticker/security identity, ISIN or equivalent mapping, listing,
  suspension, relisting, delisting, and corporate-action behavior.
- Establish first-known/publication time and the revision/vintage policy for
  every field used by a feature or target.
- Define missing, zero, stale, duplicate, and correction semantics.
- Preserve the exact source contract, retrieval timestamp, source release or
  query identity, and credential-free provenance metadata.

### 2. Population and structural closure

- Prove the population scope for the complete historical interval, not only a
  sample or current snapshot.
- Prove unique `(ticker, date)` identity and deterministic row-key closure.
- Prove membership in the official session calendar, including missing and
  duplicate session handling.
- Reconcile listing/tradability/security-master coverage as-of each decision
  date; a current universe or top-N substitute is not admissible.
- Validate OHLCV domains, value/volume units, arithmetic identities, zero-open
  behavior, and coverage breaks through time.
- Independently recompute key coverage and identity counts from raw evidence;
  do not rely only on a provider summary or production helper.

### 3. PIT and causal provenance

- Bind every feature field to a decision cutoff at EOD `t` and prove that its
  knowledge time is no later than that cutoff.
- Bind financial rows to publication/knowledge time and revision/vintage; a
  period end or report date alone is not enough.
- Prove that the historical universe is not contaminated by current listings,
  future status, or post-decision corrections.
- Hash every immutable input, schema, code/commit, manifest, and generated
  artifact; retain the exact join and filtering contract.
- Record the independent recomputation and adversarial falsification result.

### 4. Economic and event semantics

- Reconcile corporate-action and price-basis treatment separately for splits,
  reverse splits, rights/HMETD, bonus shares, dividends, suspensions,
  relistings, and delistings.
- Do not treat a listing date, record date, distribution date, price jump, or
  share-count quotient as proof of an effective market transition.
- Classify unresolved event rows as `UNKNOWN` or quarantine them; do not infer
  a transition to obtain more coverage.

### 5. Frozen target and common-support closure

After the package above is independently admitted, and only then, it must
bind to the already frozen lane protocol without changing it:

- target: `CANONICAL_V4_X1_REALIZED_CONSENSUS_OPEN_T1_CLOSE_H5_H10_V1`;
- H5/H10: `Close_(t+5) / Open_(t+1) - 1` and
  `Close_(t+10) / Open_(t+1) - 1`;
- universe: `V4_PRIMARY_LIQUID_CAUSAL_V1`;
- six chronological 100-session folds over the fixed last 600 sessions;
- ten official-session purge and the existing minimum-date rule;
- incumbent and each candidate scored on exactly the same admitted
  `(ticker,date)` rows and dates;
- no H5-only substitution, shifted cutoff, variant, rescue, or retry.

The package must prove both target horizons are observable under the same
population and as-of rules. It must not be used to widen the current clean
panel's authorization.

## Current source disposition

| Source/lane | Current classification | Missing evidence that blocks admission |
|---|---|---|
| Clean OHLCV research panel | `PARTIAL — FROZEN_ONLY` | Population-wide historical-as-of contract and authorization for new-alpha scoring. |
| Official sessions and tradability anchors | `PARTIAL — FROZEN_ONLY` | They establish ordering/mask inputs, not source population or target admission. |
| Financial PIT bundle | `PARTIAL` / parked | Population completeness, authoritative publication/revision contract, and same-science admission. |
| Zapi/IDX/TradingView/Investing/Stockbit probes | `PARTIAL`, `BLOCKED`, or `UNKNOWN` | Stable source identity, historical completeness, PIT/vintage, and event/price-basis authority. Do not reopen solely to improve a result. |
| Foreign-flow archive | `BLOCKED` | The expected admitted representation/provenance path is absent. |
| Protected prospective outcome vault/counter | `BLOCKED` | Explicitly out of scope for this historical discovery lane. |

## Re-entry rule

Re-entry is allowed only after a separately reviewed admission artifact proves
all required rows above, preserves this lane's frozen protocol, and receives a
new explicit `DATA_ADMISSION=PASS`. Until then, the current candidates remain:

- C1/C2/C4: `FUTURE_RESEARCH` structural capability only;
- C3: `BLOCKED` due partial/late PIT coverage;
- no target access, no IC/ICIR, no OOS verdict, no friction result, and no
  `RESEARCH_SURVIVOR`.

No canonical, incumbent, capture/runtime, cloud/R2, scheduler, counter, or
protected-data mutation is part of this remediation contract.
