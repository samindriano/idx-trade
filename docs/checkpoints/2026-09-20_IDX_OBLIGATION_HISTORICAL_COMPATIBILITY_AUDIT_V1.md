# IDX-Trade — Obligation Historical Compatibility Audit V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `HISTORICAL_CONTRACT_RECONCILED / MIGRATION_NOT_IMPLEMENTED`

This checkpoint audits the historical execution contracts that a future
quantity-obligation design must preserve or deliberately supersede. It uses
repository history only and does not recreate old experiments or modify
runtime/source state.

## 1. Controlling historical commits

| Commit | Historical role | Contract consequence |
|---|---|---|
| `e1531b3c` | `fix(execution): remediate paper state divergence and execution allocation` | Introduced the current verified execution shape, ticker-level pending intents, zero-lot BUY pending, and ticker-set shadow/pending invariants. Positive BUY fills became ordinary positions once `shares > 0`. |
| `d8d34b79` | `fix(execution): capacity-guard exits and persist partial sells` | Added positive partial SELL capacity handling, residual positions, and `pending_sells`; it did not add symmetric positive BUY residual persistence. |
| `ce91d60a` | `fix(e2e): close dividend replay review gaps` | Added an independent replay/oracle path that compares planned versus filled fields and expects zero pending transitions in its completed synthetic production replay. |

The current defect is therefore a historical contract split: the later SELL
remediation is quantity-aware in the position/pending transition, while the
earlier BUY contract remains membership-complete for positive underfills.

## 2. Compatibility matrix

| Legacy behavior | Preserve? | Required treatment under a new obligation ledger |
|---|---|---|
| Whole-lot and non-negative-cash invariants | Yes | Keep as per-attempt and post-state invariants. |
| Sell-before-buy replacement ordering | Yes | Keep `replacement_group_id` and block the BUY while the SELL residual is unresolved. |
| Zero-lot BUY creates a pending transition | Yes, semantics clarified | Create an obligation with planned quantity and `filled=0`; do not rely on ticker-only pending membership. |
| Positive partial SELL preserves actual residual position | Yes | Map cumulative fills and remaining shares to one logical SELL obligation. |
| Positive partial BUY becomes a held position | No as completion semantics | Preserve actual filled position, but create a residual BUY obligation. |
| Ticker-set shadow invariant | Compatibility view only | Derive membership from actual positions plus active obligations; do not use it as quantity completion. |
| `pending_transition_count == 0` replay expectation | Historical result only | Do not rewrite the old result; version a new oracle that asserts obligation completion or explicit residual state. |
| Legacy pending row with no quantity/age | Preserve data, not meaning | Wrap as `LEGACY_UNQUANTIFIED_PENDING`; remaining quantity is `UNKNOWN`, never fabricated from the current position. |

## 3. Migration boundary

The existing state schema cannot reconstruct a positive BUY's lost planned
remainder after the fact. A safe migration therefore has three classes:

1. **Complete historical fill** — no residual obligation is needed when the
   persisted fill and plan prove `planned == filled`.
2. **Explicit zero-lot pending** — create a quantified obligation from the
   preserved planned sizing entry and `filled=0`.
3. **Positive partial or ticker-only legacy state** — retain the actual paper
   position, but mark the missing remainder `UNKNOWN_ORPHANED_PARTIAL` and
   require manual/research reconciliation. Do not infer `planned_shares` from
   current target membership or from cash.

This boundary prevents a remediation from manufacturing historical exposure or
retroactively changing CA entitlement. Corporate-action entitlement must still
use the actual cum-date position; an unknown legacy remainder cannot receive a
dividend by inference.

## 4. Replay and acceptance consequence

The independent `ce91d60a` oracle is valuable because it already compares
planned and filled quantities. Its `pending_transition_count: 0` expectation,
however, is compatible only with the old completed-replay fixtures. A new
versioned oracle should additionally compare:

- obligation ID and parent state hash;
- cumulative planned/filled/remaining/relinquished quantities;
- retry attempt/session history;
- explicit cancellation/expiry events;
- actual positions and pending compatibility views;
- CA entitlement/settlement state;
- restart and same-session replay identity.

The old oracle and historical PASS records must remain immutable historical
evidence. They cannot be silently reinterpreted as proof of the new contract.

## 5. Decision

Historical assumptions are sufficiently reconciled to define a safe next
research step: build an isolated versioned obligation/replay harness with
explicit orphan handling. A direct runtime migration or source patch is not
justified by this audit alone.

No protected outcomes, provider, production, cloud/capture/telemetry,
canonical-data, or incumbent state was accessed or modified.
