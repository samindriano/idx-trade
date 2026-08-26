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

Status: `OPEN_AUDIT`

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
