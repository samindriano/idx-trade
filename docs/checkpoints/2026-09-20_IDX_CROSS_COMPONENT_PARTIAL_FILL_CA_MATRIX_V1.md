# IDX-Trade Cross-Component Partial-Fill / CA Matrix V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `BOUNDED_PASS_WITH_PENDING-STATE_POLICY_ASSUMPTION`  
Scope: isolated synthetic execution/state analysis only. No provider, cloud,
capture, telemetry, canonical-data, production, or protected-outcome access.

This checkpoint follows the corporate-action lifecycle audit and tests an
interaction that is easy to miss when reading each component independently:
Decision replacement pairing + exit capacity + pending transitions + cash
accounting + restartable paper state.

## 1. Contract under test

The pinned execution contract at
`C:\Users\Sam\AppData\Local\Temp\idx-system-045e25a1-dd0f02dcb71f48cf82d2b81e0eead8cf`
uses the following policy:

`paper_nonfill_policy = PERSIST_PENDING_TRANSITION_NOT_SHADOW_MUTATION`

For a replacement from `AAA` to `BBB`:

1. prepare a full `AAA` sell and `BBB` buy pair;
2. cap the `AAA` sell at 1% of reference-day regular market value;
3. if the sell is incomplete, retain residual `AAA` shares and a pending sell;
4. block the paired `BBB` buy rather than pretending the replacement is done;
5. carry both pending transitions into the next paper state.

This is deliberately distinct from a broker-fill claim. It is a deterministic
paper transition policy.

## 2. Synthetic scenario

Inputs were constructed from the pinned test helpers and execution contracts:

- session: `2026-08-21` decision to `2026-08-24` official open;
- cash: Rp45,000,000;
- actual position: 5,000 shares of `AAA`;
- replacement: sell `AAA` rank 21, buy `BBB` rank 1;
- EOD/reference price: Rp1,000 for both names;
- `AAA` regular-market-value: Rp100,000,000;
- `BBB` regular-market-value: sufficiently large;
- official Open: Rp1,000 for both names;
- CA attestation: verified `NO_RELEVANT_EVENTS` for both names.

The capacity ceiling is Rp1,000,000 gross notional. With the configured sell
slippage, the effective price is Rp999, so 1,000 of 5,000 shares can fill.

## 3. Observed result

| Surface | Observation | Result |
|---|---:|---|
| Sell planned | 5,000 shares | PASS |
| Sell filled | 1,000 shares | PASS: strict partial fill |
| Sell gross notional | Rp999,000 | PASS: below Rp1,000,000 cap |
| Residual position | 4,000 `AAA` shares | PASS |
| `AAA` pending sell | `PARTIAL_EXIT_CAPACITY` | PASS |
| `BBB` filled | 0 shares | PASS |
| `BBB` pending buy | `BLOCKED_BY_UNRESOLVED_PAIRED_SELL` | PASS |
| Final position universe | `AAA` remains | PASS: no shadow-only disappearance |
| Cash after sell | Rp45,996,502.50 in the larger probe | PASS: proceeds minus sell fee |
| `reconciliation_required` | `false` | POLICY ASSUMPTION, not broker proof |

The canonical focused test
`tests/test_v4_x1_execution_v1_exit_capacity.py::test_sell_capacity_can_partial_fill_and_blocks_paired_buy`
asserts the key structural results. The larger direct probe used 10,000
`AAA` shares and produced the same state shape: 1,000 filled, 9,000 residual,
paired buy blocked, and no negative cash.

## 4. Why this matters for corporate-action and portfolio state

Corporate-action accounting is attached to the paper state, not merely the
current target list. If a holder reaches cum date and later has a partial exit:

- the dividend entitlement remains bound to the cum-date position;
- the residual holding remains in the actual paper state;
- the paired replacement cannot be treated as fully complete;
- spendable cash changes only by the actually filled sell proceeds and fees;
- any receivable remains a NAV item but not spendable cash until settlement;
- the runtime snapshot must preserve both the dividend ledger and pending
  transition state.

The dividend-aware state hash and ledger hash provide the identity binding for
the CA side. The execution state hash and pending-intent normalization provide
the execution-side binding. Together they prevent a prepared order from being
executed against a state in which the residual holding or dividend ledger was
silently changed.

## 5. Validation evidence

From runtime commit `045e25a19d9f71170d2c863e768102937e59ad73`:

- partial-exit focused test: `1 passed`;
- Decision V2 execution adapter interaction slice: `6 passed`;
- execution/capacity/pending/CA selection run: `7 passed`;
- earlier corporate-action continuation slice: `116 passed`;
- prior pinned Decision/Sizing/Execution and E2E bounded slice: `86 passed`.

The tests cover paired-sell blocking, pending transition persistence,
capacity/lot/cash invariants, Decision V2 shadow lineage, pending reversal, and
verified CA attestation. They do not constitute broker integration or a
population-wide liquidity test.

## 6. Hidden policy assumption and open question

The state sets `reconciliation_required=false` after a partial fill. This is
internally coherent if `reconciliation_required` means “external accounting
mismatch requiring manual reconciliation” and pending intents mean “known,
recoverable execution residual.” It would be wrong if operators interpret that
flag as “the portfolio exactly equals the intended target” or “the broker and
paper state are reconciled.”

Therefore the current classification is:

- `PAPER_TRANSITION_INVARIANTS`: `PASS`;
- `PARTIAL_FILL_POLICY`: `EXPLICIT_AND_DETERMINISTIC`;
- `BROKER_RECONCILIATION`: `UNKNOWN`;
- `PENDING_AGE_ESCALATION_OR_EXPIRY`: `NOT_CERTIFIED`;
- `PORTFOLIO_RISK_OVERLAY_AFTER_PARTIAL_EXIT`: `NOT_PRESENT`.

The material unanswered system question is not whether the first partial fill
is represented correctly—it is. The question is what happens if the residual
pending sell persists through several sessions, a new Decision ranking reverses
the pair, a dividend payment occurs meanwhile, or capacity shrinks to zero.
The current adapter tests cover some reversal paths but do not provide a single
multi-session matrix combining all of those events.

## 7. No-retry / next frontier

No provider or live execution retry is justified by this result. The next
highest-value local test is a synthetic multi-session matrix with these axes:

`partial exit -> dividend ex-date/payment -> pending reversal -> restart ->
same-session replay -> residual expiry/escalation`

It should assert actual shares, pending intents, receivable/settlement state,
cash, total-return NAV, Decision shadow state, runtime parent hashes, and
whether an explicit reconciliation/manual-review state is required. Until that
policy is frozen, partial-fill acceptance should not be described as full
portfolio reconciliation.

## 8. Provenance and non-mutation

- This is a new documentation checkpoint only.
- Scratch execution used synthetic in-memory objects and temporary test state.
- No code/configuration was changed.
- No Zapi/IDX/provider call or protected outcome was made.
- Concurrent `TEAM_STATUS` and research-file changes were not staged or
  modified.

