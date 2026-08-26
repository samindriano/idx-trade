# Research Integrity Incident Ledger

This ledger records material scientific/data-integrity incidents that must leave permanent regression protection.

An incident is not closed merely because the immediate rows or code were changed.

## Status vocabulary

- `OPEN_AUDIT` — suspected defect; blast radius and root cause unresolved.
- `CONFIRMED` — defect proven; remediation may still be pending.
- `REMEDIATED_PENDING_REGRESSION` — immediate correction exists but durable protection is incomplete.
- `CLOSED_REGRESSION_PROTECTED` — root cause, blast radius, remediation/quarantine, invariant/golden case, and regression protection are all verified.
- `FALSE_ALARM` — suspicion falsified with durable evidence.

## Incident template

```text
Incident ID:
Status:
Detected:
Domain:

Symptom:
Root cause:
Affected lineage:
Blast radius:
Scientific/runtime materiality:

Remediation/quarantine:
Permanent invariant:
Golden/adversarial case:
Regression test:
Independent red-team:
Gate rerun:

Evidence refs / hashes:
Closure verdict:
```

---

## INC-001 — Historical CA / backward feature price-basis integrity

Status: `CONFIRMED`

Detected: 2026-08-26

Domain: historical EOD price basis / corporate actions / backward-looking feature construction

### Symptom

Human notebook inspection showed an apparent raw historical BBCA pre/post-stock-split discontinuity. The subsequent independent audit established that the relevant defect class is broader: backward-looking raw-price feature dependencies can cross structural corporate-action basis transitions because the feature path has no general CA-aware basis reset/quarantine.

### Confirmed root cause

The frozen V4 feature path computes sequential raw-price-derived features before cross-sectional ranks and market context. Existing CA continuity protection is target-window oriented and does not certify that backward feature dependencies remain on one compatible price basis.

Therefore a structural event can contaminate direct lag/rolling feature values and then create deterministic cross-sectional/market spillover even when the affected ticker itself is later excluded from exact target/final-fit support.

### BBCA 2021 witness

The reviewed audit traces BBCA around the recorded `1:5` split on `2021-10-13` and demonstrates 5/14/20/60-session backward feature exposure.

However, BBCA is **not** evidence of exact final-fit contamination: all reviewed BBCA combined-support rows have H5/H10 support false and exact final-fit membership is H5 `0`, H10 `0`.

Permanent documentation/tests must preserve this distinction:

```text
feature-layer exposure != exact final-fit membership
```

### Bounded accepted-overlay blast radius

The reviewed audit reconstructed the accepted-overlay exact-fit input delta as:

```text
exact-fit union:        241,724 rows
changed union:           56,602 rows
changed tickers:            486
changed dates:              290
direct changed rows:         681
spillover changed rows:   55,921
```

The large majority of changed identities are cross-sectional/market spillover rather than direct ticker-basis changes.

Existing descriptive diagnostics establish nontrivial feature/rank deltas, so the change cannot be dismissed as numerical epsilon. Performance materiality remains **not evaluated/proven** because the audit was outcome-blind and did not refit/score models.

### Independent review

Independent review verdict:

`PASS_WITH_REVIEW_FIXES`

Checkpoint:

`docs/checkpoints/2026-08-26_CA_FEATURE_BASIS_INTEGRITY_INDEPENDENT_REVIEW_V1.md`

The review accepts the defect class and blast-radius reconstruction while recording two required provenance fixes before incident closure:

1. the 56,602-row impact source should be described precisely as an exact-final-fit reconstruction from the accepted v1.1 feature-impact rows with v1.1/v1.2 lineage manifests verified, unless the exact v1.1 -> v1.2 semantic contract is separately proven;
2. BBCA may become a permanent golden case only after event date/ratio/transition truth is bound to pinned canonical evidence rather than supplied solely by code constants.

### Frozen remediation policy

Policy:

`docs/research_integrity/CA_AWARE_FEATURE_BASIS_POLICY_V1.md`

Status:

`FROZEN_POLICY_PENDING_IMPLEMENTATION`

Default remediation is **compatible price-basis epoch quarantine/reset**, not broad historical price adjustment.

Permanent invariant:

> A price-basis-sensitive feature is admitted only when every historical dependency used to compute that feature belongs to one source-backed compatible price-basis epoch.

Structural event families must retain event-specific semantics. Rights/HMETD, stock dividends, bonus shares, mandatory conversions, and capital restructurings cannot be silently treated as generic splits. Cash dividends do not create a basis reset merely because raw price gaps ex-dividend.

### Required permanent protection

At minimum:

- source-bound event-family-specific CA semantics;
- deterministic compatible basis epochs / fail-closed unknown scopes;
- backward dependency admission for every price-basis-sensitive feature;
- direct source feature quarantine before cross-sectional/market recomputation;
- source-bound BBCA split golden case;
- unresolved-transition fail-closed case;
- rights/HMETD non-split adversarial case;
- cash-dividend non-basis-reset case;
- deterministic spillover recomputation case;
- explicit regression test preventing incompatible pre/post-event bases from entering an admitted feature row;
- independent recomputation/red-team evidence;
- Research Integrity gate rerun.

### Current authorization boundary

Still **not authorized**:

- protected outcome access;
- historical performance recomputation;
- V4-X1 refit/tuning/rescue;
- prospective counter mutation/reset;
- retroactive score/trade/fill reconstruction;
- generic market-wide price adjustment;
- canonical artifact overwrite;
- production capture/runtime change.

A model refit decision is deferred until the frozen CA-aware policy is implemented outcome-blind, affected feature inputs are recomputed, exact training-input deltas are independently measured, and the Research Integrity gate is rerun.

### Evidence refs / hashes

Primary audit:

- branch: `audit/ca-feature-basis-integrity-v1`
- HEAD: `c18cbfee7dfbb8b16f15d8a4ca27c2f68041abb2`
- audit manifest SHA-256: `b9a37511fd92a8f4bfc9e7e7e16597a720523523c2ae87f9ae135e872dab89d3`

Primary audit artifact root (external, immutable for that run):

`D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v4`

### Current closure verdict

`NOT_CLOSED_POLICY_FROZEN_IMPLEMENTATION_AND_REGRESSION_PENDING`

### Phase-2 audit update — 2026-08-27

Root cause is confirmed for the audited historical lineage: the frozen
feature construction computes backward-looking H/L/C-derived windows directly
from the observed price series without a CA-aware reset or quarantine. The
target-window continuity guard does not certify those backward feature
windows. The audit also found unresolved market-effective dates and a
conversion taxonomy mismatch, so ambiguous event evidence cannot be promoted
to a generic adjustment rule.

Bounded evidence and blast radius:

- The pinned audit root is
  `D:\Documents\Project\idx-ca-feature-basis-integrity-audit-20260826-v4`.
- Its `audit_manifest.json` SHA-256 is
  `b9a37511fd92a8f4bfc9e7e7e16597a720523523c2ae87f9ae135e872dab89d3` and
  its `input_manifest.json` SHA-256 is
  `41e12116637f1cd1df190a4f8ea53c1048d6ab0eff8d263a05db470f893d5b40`.
- The strict CA census has 26 rows across STOCK_SPLIT, STOCK_DIVIDEND,
  BONUS_SHARES, RIGHTS_HMETD, MANDATORY_CONVERSION, and
  CAPITAL_RESTRUCTURING; all 26 have unresolved price-continuity effective
  dates.
- The accepted support-only overlay changes 56,602 UNION exact-fit identities
  across 486 tickers and 290 dates: 681 direct rows and 55,921 spillover rows.
  H5 is 56,514 rows and H10 is 56,221 rows.
- BBCA 2021 has 5/14/20/60 backward lookback exposures, while exact BBCA
  final-fit identities are H5=0 and H10=0. This is feature-layer exposure,
  not a claim that BBCA entered the exact fit.

The independent QA gate reports are preserved externally under
`D:\Documents\Project\idx-research-integrity-inc001-gate-20260827-v1`.
`DATA_ADMISSION` is `FAIL` and `RESEARCH_ADMISSION` is `FAIL`; required
`UNKNOWN` is blocking. `MODEL_PROMOTION` is `NOT_EVALUATED` because no model
or protected evidence was opened.

Remediation is not authorized by this audit. Closure requires family-specific
effective-date and knowledge-time evidence, explicit price-basis policy,
backward-window quarantine/reset semantics, a BBCA and other event-family
golden suite, independent recomputation, red-team confirmation, and a rerun
of the controlling gates.
