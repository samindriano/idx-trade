# IDX-Trade — Multi-Session Pending / CA / Reversal Matrix V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated `codex/alpha-available-data-20260919`  
Status: `CROSS_COMPONENT_PASS_WITH_PENDING_POLICY_BLOCKER`

This is a synthetic, outcome-blind continuation of the partial-fill frontier.
It composes repeated exit capacity, paired replacement, dividend entitlement
and payment, and a later Decision reversal. It does not modify runtime source,
canonical data, provider state, cloud/capture state, or production state.

## 1. Contract and probe

The probe used the retained runtime source commit
`402fca4b27e91cf8c82d21ff1394ba2d6da73656` and the actual
`prepare_execution_v1` / `execute_open_v1` paths.

Initial paper state:

- cash: IDR 45,000,000;
- actual holding: `AAA:5,000` shares;
- Decision replacement: sell `AAA`, buy `BBB`, 5,000 planned shares each;
- `AAA` reference-day value: IDR 100,000,000 for the first three sessions;
- `AAA` reference-day value: IDR 0 on the fourth session;
- `BBB` reference-day value: sufficiently large.

The configured 1% per-name capacity therefore allowed 1,000 `AAA` shares per
session at the configured effective price, then zero on the fourth session.

## 2. Repeated pending transition

| Session | Sell planned / filled | Buy planned / filled | Position after | Pending state |
|---|---:|---:|---|---|
| S1 | 5,000 / 1,000 | 5,000 / 0 | `AAA:4,000` | sell `AAA` + buy `BBB` |
| S2 | 4,000 / 1,000 | 5,000 / 0 | `AAA:3,000` | sell `AAA` + buy `BBB` |
| S3 | 3,000 / 1,000 | 5,000 / 0 | `AAA:2,000` | sell `AAA` + buy `BBB` |
| S4 zero capacity | 2,000 / 0 | 5,000 / 0 | `AAA:2,000` | sell `AAA` + buy `BBB` |

Cash after S4 was IDR 47,989,507.50. The pending-intent schema contained only
`side`, `ticker`, `rank_consensus`, `reason`, and `replacement_peer`. It had no
age, attempt count, creation session, or explicit remaining-share field. The
remaining `AAA` quantity can be reconstructed from the position and fill
history in this probe, but it is not owned by the pending intent itself.

## 3. Dividend composition

A synthetic certified cash dividend was attached to the original cum-date
holding:

- entitlement: 5,000 shares at IDR 25/share;
- ex-date receivable: one row, IDR 125,000;
- payment date: IDR 125,000 added to cash;
- cash before payment: IDR 47,989,507.50;
- cash after payment: IDR 48,114,507.50;
- pending replacement after payment: unchanged, sell `AAA` plus buy `BBB`;
- same-session payment replay: exact state equality.

This confirms that the dividend lifecycle correctly preserves cum-date
entitlement and exactly-once payment while the unresolved replacement remains
pending. Settlement does not itself trigger a new sizing or execution pass.
That is a policy boundary, not evidence of CA over-entitlement or double pay.

## 4. Decision reversal

The next synthetic Decision target returned to the actual `AAA` holding and
requested no replacement. The Decision V2 adapter was also exercised with the
shadow state implied by the pending pair (`BBB`) and the reversed target
(`AAA`). It explicitly recognized the reversal and produced:

- position: `AAA:2,000`;
- pending sell: none;
- pending buy: none;
- effective buy intents: none;
- effective sell intents: none;
- fills: none;
- `reconciliation_required`: `false`;
- no fill-based cancellation record;
- cash unchanged from the post-payment state.

Thus the adapter's cancellation behavior is deterministic and intentional at
the order-selection layer. The remaining gap is auditability: the resulting
`ExecutionResult` does not emit a typed cancellation/reversal event or retain
the canceled obligation's lineage. There is also no pending-age/expiry/manual-
review contract to show whether a long-lived residual should have escalated
before the reversal.

## 5. System interpretation

| Boundary | Result | Classification |
|---|---|---|
| repeated partial exit → pending state | residual sell remains recoverable across four sessions | bounded PASS |
| pending replacement → CA payment | payment is exactly-once and does not mutate pending intent | bounded PASS / policy boundary |
| pending state → remaining quantity | remaining shares are not explicit in pending schema | `OBSERVABILITY_GAP` / economic-risk latent risk |
| pending state → expiry/escalation | no age or attempt semantics are represented | `POLICY_NOT_CERTIFIED` |
| Decision reversal → pending cancellation | pending pair disappears without a cancellation event | `POLICY_AND_AUDIT_GAP` |

The new evidence narrows the architecture question. CA settlement itself is
deterministic; the unresolved contract is the lifecycle of an execution
obligation after settlement, capacity starvation, and target reversal.

## 6. Required future contract before remediation

A quantity-aware obligation ledger should define, at minimum:

1. planned, filled, and remaining quantity for each logical order;
2. session creation, last-attempt, attempt count, and reason history;
3. whether CA settlement can trigger re-planning or only changes available cash;
4. explicit cancellation/reversal events and their audit lineage;
5. expiry, escalation, and manual-reconciliation behavior;
6. restart/replay identity for each obligation independent of ticker membership.

No source patch is applied by this checkpoint. Repeating the same four-session
probe is not justified until one of those contracts changes.

## 7. Provenance and firewall

- Evidence is synthetic and local to the retained runtime path.
- No protected outcome, provider, cloud, capture, telemetry, scheduler,
  canonical dataset, production, or incumbent state was accessed or changed.
- This matrix does not certify broker reconciliation, executable capacity,
  tax/net policy, or predictive performance.
