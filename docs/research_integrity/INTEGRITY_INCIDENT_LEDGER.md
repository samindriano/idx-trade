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

Human notebook inspection showed an apparent raw historical BBCA pre/post-stock-split discontinuity. Existing project lineage also contains CA target-continuity and selective price-basis remediation work, so the visual alone does not establish final-model contamination.

### Current question

Determine whether any structural corporate-action price-basis discontinuity can survive into backward-looking feature windows used by the frozen V4-X1 lineage, and whether any affected identities entered exact final fit rows.

The audit must distinguish:

- raw notebook visualization;
- target/price-evidence remediation;
- feature-input remediation;
- target-window continuity;
- backward feature-window continuity;
- direct ticker impact;
- cross-sectional/market spillover;
- exact final-fit identity membership.

### Known scope boundary

No remediation, V4-X1 refit/tuning, protected outcome access, prospective counter mutation/reset, retroactive fills, or production capture/runtime change is authorized by this incident entry.

### Required permanent protection if confirmed

At minimum:

- event-family-specific CA semantics;
- known-event golden cases including BBCA split if canonical evidence confirms it is an appropriate case;
- backward-window integrity check covering the representation's maximum relevant lookback;
- explicit regression test preventing an incompatible pre/post-event price basis from silently entering admitted feature rows;
- independent recomputation / red-team evidence.

### Current closure verdict

`NOT_CLOSED`

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
