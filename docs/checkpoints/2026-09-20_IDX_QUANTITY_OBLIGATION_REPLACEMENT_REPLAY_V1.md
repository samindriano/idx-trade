# IDX-Trade — Quantity-Obligation SELL/Replacement Replay V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `SPEC_HARNESS_PASS / RUNTIME_NOT_IMPLEMENTED`

This is the second independent spec harness for the proposed obligation
contract. It covers a paired SELL/BUY replacement and does not change the
current execution runtime or historical replay oracle.

## 1. Focused validation

Artifacts:

- `research/idx_quantity_obligation_replacement_replay_v1.py`
- `tests/test_idx_quantity_obligation_replacement_replay_v1.py`

Command and result:

```text
python -m pytest -q tests/test_idx_quantity_obligation_replacement_replay_v1.py
2 passed
```

## 2. Exact scenario

Initial state: `AAA:5,000`, target replacement `AAA → BBB`, with one 5,000-
share SELL obligation and one 5,000-share BUY obligation in the same
replacement group.

| Stage | Position | SELL obligation | BUY obligation |
|---|---|---|---|
| Planned | `AAA:5,000` | remaining 5,000 | remaining 5,000 |
| First Open | `AAA:4,000` | filled 1,000, remaining 4,000 | blocked, remaining 5,000 |
| JSON reload | `AAA:4,000` | same hash/state | same block event retained |
| Retry | `AAA:3,000` | filled 2,000, remaining 3,000 | blocked again, filled 0 |
| Target reversal | `AAA:3,000` | canceled/relinquished 3,000 | canceled/relinquished 5,000 |

The conservation identity held independently for both obligations. The replay
event log retained:

```text
SELL-FILL-1, SELL-FILL-2,
BUY-BLOCK-1, BUY-BLOCK-2,
SELL-CANCEL-1, BUY-CANCEL-1
```

Duplicate cancellation replay returned exact state equality. JSON reload before
the retry preserved the state hash.

## 3. What this adds

- A quantity-aware design can preserve sell residuals and block paired buys
  without collapsing the replacement into ticker membership.
- Repeated blocked attempts remain observable through attempt count and reason
  history.
- Reversal can close both sides explicitly while retaining each relinquished
  quantity and the replacement group identity.
- The proposed state graph handles the historical partial-SELL behavior and
  the missing positive partial-BUY behavior with one conservation rule.

## 4. Limits

This is still a spec-only harness. It does not prove current runtime adoption,
broker reconciliation, executable liquidity, risk-overlay behavior, tax policy,
or production restart behavior. Migration of legacy ticker-only pending rows
remains fail-closed and must not fabricate remaining quantities.

Next local frontier: compare this event-level acceptance matrix to actual
runtime artifact serialization and historical replay boundaries, without
patching production code.
