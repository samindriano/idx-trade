# IDX-Trade — Quantity-Obligation Replay Harness V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `SPEC_HARNESS_PASS / RUNTIME_NOT_IMPLEMENTED`

This is an independent in-memory validation of the proposed obligation
contract. It is not a runtime patch and must not be read as evidence that the
current production paper state already has these semantics.

## 1. Harness and scope

Artifacts:

- `research/idx_quantity_obligation_replay_harness_v1.py`
- `tests/test_idx_quantity_obligation_replay_harness_v1.py`

The harness uses only the standard library and synthetic state. It tests a
single BUY obligation through partial fill, JSON reload, duplicate replay,
retry, CA payment, target reversal, and duplicate cancellation.

## 2. Exact result

Focused command:

```text
python -m pytest -q tests/test_idx_quantity_obligation_replay_harness_v1.py
3 passed
```

Scenario:

| Stage | Filled | Remaining | Other state |
|---|---:|---:|---|
| Planned | 0 | 5,000 | status `PLANNED` |
| First partial fill | 2,400 | 2,600 | status `PARTIAL`, attempt 1 |
| Duplicate fill replay | 2,400 | 2,600 | exact state/hash unchanged |
| Retry fill | 3,400 | 1,600 | status `PARTIAL`, attempt 2 |
| CA settlement | 3,400 | 1,600 | entitlement 3,400 shares; payment IDR85,000 |
| Target reversal | 3,400 | 0 | relinquished 1,600; status `CANCELED` |
| Duplicate cancellation replay | 3,400 | 0 | exact state unchanged |

The conservation invariant held throughout:

```text
planned 5,000 = filled 3,400 + remaining 0 + relinquished 1,600
```

The synthetic CA policy correctly used actual shares at the cum-date boundary
(3,400), not the original target quantity (5,000). Cash moved from IDR
45,000,000 to IDR45,085,000 exactly once.

## 3. What this validates

- Planned, filled, remaining, and relinquished quantities can be conserved
  without using ticker membership as a completion proxy.
- A stable obligation identity supports duplicate fill/cancel idempotency after
  a real JSON reconstruction, not merely the same in-memory object.
- CA entitlement remains tied to actual shares and does not over-entitle a
  future residual BUY.
- Target reversal can close a residual explicitly while retaining its quantity
  and reason.
- A positive partial with no preserved historical plan is classified as
  `UNKNOWN_ORPHANED_PARTIAL`, not assigned a fabricated remainder.

## 4. What this does not validate

- The current runtime does not consume this harness or persist this schema.
- SELL/replacement-pair execution, aggregate risk, projected-CA parent hashes,
  and actual runtime snapshot migration remain separate work.
- The harness does not prove broker reconciliation, executable capacity, tax
  correctness, cloud behavior, or predictive performance.

Therefore this is a design-consistency PASS and an implementation requirement,
not a system-completion PASS.

## 5. Next frontier

Extend the isolated harness with a SELL/replacement pair and an explicit
restart/recovery event log, then compare the resulting acceptance requirements
against the immutable historical replay oracle. No production/runtime source
patch is justified by this spec-only pass.
