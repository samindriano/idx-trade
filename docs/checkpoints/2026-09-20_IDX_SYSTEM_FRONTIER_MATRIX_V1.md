# IDX System Frontier Matrix V1

Date: 2026-09-20  
Lane: isolated `codex/alpha-available-data-20260919`  
Purpose: durable rolling map for the system-wide research marathon

Depth labels are evidence states, not promotion claims. `EXTERNAL_EVIDENCE_BLOCKED` means local work is bounded by protected outcomes, provider ownership, or live production evidence and is not a claim of correctness.

| Surface | Depth | Current evidence / finding | Open local question or blocker | Next useful frontier |
|---|---|---|---|---|
| Alpha / representation interface | STRUCTURALLY_AUDITED | Pure evaluator/gate ticker identity split; outcome evidence remains closed. | Test representation-to-Decision churn without protected targets. | Adversarial alpha-to-Decision interface replay. |
| Decision state machine | CROSS_COMPONENT_TESTED | Rank persistence, exit confirmation, vacancy, soft replacement, and Decision V2 ten-seat shadow scenarios exercised; a 2,400/5,000 seat still reports `FULL`. | Quantity-aware paper state is not represented in Decision membership. | Connect Decision state to residual execution obligations. |
| Portfolio construction / sizing | CROSS_COMPONENT_TESTED | EOD-close sizing can plan 5,000 shares while Open execution fills 2,500; capacity, fee, stamp-boundary, and paired-replacement variants all underfill positively. | Positive partial fills are not a sizing-state contract. | Quantity-aware target/residual model. |
| Turnover / holding-state behavior | STRUCTURALLY_AUDITED | Turnover and holding-duration metrics exist; pending/open denominator contracts tested. | Partial positive buys can distort holding and turnover interpretation. | Recompute metrics from residual-aware fills. |
| Execution / pending / replacement | CROSS_COMPONENT_TESTED | Partial sells persist; alias replacement peer can block a fully completed sell; positive partial buys disappear across four trigger classes, including resolved paired replacement. | Residual buy and canonical relationship identity. | Unified order-obligation ledger. |
| Transaction-cost assumptions | CROSS_COMPONENT_TESTED | Fee/slippage/stamp rules are explicit and allocator-aware, but fee and stamp-boundary underfills are still recorded as complete positive fills. | Positive partial buy under cost pressure can be misclassified as complete. | Cost-aware residual obligation tests. |
| Liquidity / capacity | CROSS_COMPONENT_TESTED | Reference-day capacity and Open allocation interact with sizing; positive partial buys reproduce under capacity and paired replacement. | Capacity-limited buy residual semantics. | Capacity stress matrix with partial buy/sell symmetry. |
| Portfolio accounting / NAV / cash | CROSS_COMPONENT_TESTED | Receivable contributes to NAV but not spendable cash; payment-on-decision sizing hash mismatch found. | Settlement timing policy must align with execution parent. | Three timing cases: before decision, decision date, execution date. |
| Dividends / CA integration | CROSS_COMPONENT_TESTED | Entitlement/receivable/payment lifecycle and restart tested; projected-vs-raw state incompatibility found; actual underfilled shares correctly drive CA but missing residual exposure propagates into dividend economics. | Noncash CA remains fail-closed/external-blocked; residual-obligation/CA timing composition is not yet modeled. | CA lifecycle into residual-aware execution. |
| Risk / concentration / exposure | CROSS_COMPONENT_TESTED | Seat cap, per-name cap, liquidity and concentration audits exist; positive underfill can satisfy ticker membership while missing target quantity. | Concentration and exposure need target-vs-filled obligations. | Risk metrics with residual-aware quantities. |
| Security / ticker / issuer identity | CROSS_COMPONENT_TESTED | Alias collisions found in universe, evaluator, and execution relationship fields. | Shared canonical identity contract not implemented. | Cross-layer identity regression matrix. |
| Universe / eligibility interaction | ADVERSARIALLY_TESTED | Pre-listing warmup, alias collisions, overlapping eras reproduced. | Canonical identity/era policy remains unimplemented. | Link universe identity to Decision/execution state. |
| Storage / revisions / duplicates | ADVERSARIALLY_TESTED | Existing duplicate dates can crash; incoming duplicates keep last; atomic writers replace destinations. | Typed duplicate/revision policy. | Persistence contract and immutable/mutable writer split. |
| Artifact integrity | STRUCTURALLY_AUDITED | Hash chains and exclusive prospective gate outputs tested; orchestration execution payload preserves per-entry planned sizing. | Hashes and planned entries do not bind filled-to-remaining obligations in state. | Bind quantity obligations into state/artifact lineage. |
| Runtime configuration lineage | STRUCTURALLY_AUDITED | Runtime config/runner hashes omitted from some prepared/execution artifact identity. | Full executable/config identity binding. | Re-audit after isolated lineage design. |
| Restart / reload / idempotency | CROSS_COMPONENT_TESTED | 59 runtime tests and CA chain reload pass; actual runtime snapshot reload preserves the wrong positive partial position with equal hash and empty pending state. | Idempotency can preserve semantically incomplete state. | Replay with residual order obligations. |
| Failure recovery / interrupted state | CROSS_COMPONENT_TESTED | Interrupted atomic states, missed Open, and full staged recovery exercised; recovery preserves the positive underfill with equal hashes and empty pending state. | Recovery does not reconstruct missing positive buy residual. | Fault injection after an explicit residual obligation is modeled. |
| Evaluation contracts | CROSS_COMPONENT_TESTED | 120 prospective evaluator/gate/readiness tests pass; pure/gate identity mismatch found. | Protected outcomes remain closed. | Outcome-blind evaluator/runtime contract audit. |
| Research methodology / scientific controls | STRUCTURALLY_AUDITED | PIT, target firewall, OOS and evidence boundaries documented. | No protected predictive validation authorized. | Audit structural metrics versus economic interpretation. |
| Cross-component interfaces | CROSS_COMPONENT_TESTED | CA→sizing→execution hash mismatch; sizing→execution positive partial loss across four trigger classes; Decision V2 ten-seat shadow also suppresses residual retry; identity→replacement mismatch. | Need a single obligation/state graph. | Multi-session residual-aware system harness. |

## Current matrix interpretation

The system is no longer best described as “component tests mostly pass with a few isolated gaps.” The highest-risk pattern is semantic state loss at boundaries: a component can produce an internally valid artifact whose meaning is incomplete for the next component. The positive partial-buy trigger matrix shows that this is a family-level execution contract failure, not a single gap scenario. The most valuable next work is quantity-aware state modeling and a multi-session residual-order harness, not additional alpha feature search.

## External/protected boundaries

- Protected H5/H10, hidden OOS/PnL, and incumbent predictive comparisons remain closed.
- New external data acquisition belongs to another lane and was not used here.
- Live cloud/capture/telemetry/scheduler behavior remains out of scope for mutation.
