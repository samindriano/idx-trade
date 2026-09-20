# IDX-Trade Contract Hardening and Runtime Remediation Marathon V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: isolated implementation `codex/idx-contract-hardening-20260920`  
Status: `PHASE-1 FOUNDATION + PHASE-2 EXECUTION IN PROGRESS / NO PRODUCTION OR PROTECTED-OUTCOME ACCESS`

## Objective

Replace the confirmed semantic state-loss pattern with versioned, auditable,
restart-safe runtime contracts while preserving frozen alpha/Decision science,
historical artifacts, and fail-closed legacy behavior.

This is an implementation/remediation lane. It is not an alpha optimization,
data-acquisition, predictive-evaluation, or deployment lane.

## Implementation base and lineage

| Item | Value |
|---|---|
| Implementation worktree | `C:\Users\Sam\.codex\worktrees\idx-contract-hardening-20260920` |
| Implementation branch | `codex/idx-contract-hardening-20260920` |
| Implementation base | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` |
| Audited runtime branch | `runtime/idx-e2e-baseline-paper-v1` |
| Audited runtime pin | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` |
| Deep-dive research checkpoint | `d007077694ad861abd86f21cc8f42f7575837298` |
| Research branch at checkpoint | `codex/alpha-available-data-20260919` |
| Current `origin/main` relation | `671` commits only in implementation base side; `763` only in `origin/main` side |
| Runtime-file drift vs `origin/main` | Audited runtime files are deleted from current `origin/main`; no silent porting is permitted |

The implementation base is byte/source-hash aligned with the audited runtime;
there is no base-versus-audit drift. Current `origin/main` is a different
lineage for these runtime files, so this lane stays pinned to the retained
runtime branch until an explicit integration decision exists.

### Audited source hashes

| Source | SHA-256 |
|---|---|
| `v4_x1_execution_v1_contract.py` | `0208800825e6f2f91af9d224d7540e829828379ca332f6630889789c936cf1fe` |
| `v4_x1_execution_v1.py` | `010567bfd6c9156d5c088a96ecb251ed2074c461cc5c326fcf9c98789ab76fc9` |
| `v4_x1_execution_v1_decision_v2_adapter.py` | `c151e2b1e43850d3f8c462eea58276a814efc9fa82ea233e73ee2cd46da35fd6` |
| `forward_dividend_runtime_v1_1.py` | `98ebc637340757f03e36c3c8b876f134022ca1282b9bad35cf573b4b784eca23` |
| `e2e_paper_orchestration_v1.py` | `d10ace3f01e407ed8198460d5571f26e92107f681f3268ad60be1d42cc081eec` |
| `e2e_paper_runtime_config_v1.py` | `df1e88c4b1f994fc44514a3910e5f066aee4754260e8c7a05e75c4550969631d` |
| `e2e_paper_runtime_config_v2.py` | `0907f0fd02af7f61e48959efc7f1318a0c6559ef78ba9f34c7ddfc5fd494c356e6` |

The config-v2 hash row is retained from the research checkpoint and must be
rechecked before any config-lineage implementation claim; source identity
checks in code remain authoritative.

## Confirmed findings entering remediation

| Finding family | Current disposition | First remediation owner |
|---|---|---|
| Positive partial BUY loses residual | `CONFIRMED / IMPLEMENT` | Versioned quantity-obligation state |
| Partial SELL/replacement lacks full quantity lineage | `CONFIRMED / IMPLEMENT` | Same obligation owner, not a parallel pending ledger |
| Snapshot persists positions but not obligations | `CONFIRMED / IMPLEMENT` | Versioned snapshot schema and restart replay |
| CA projected-state versus execution-parent mismatch | `CONFIRMED / LOCAL_TIMING_MATRIX_IMPLEMENTED` | Raw execution parent plus projected NAV-only sizing and additive timing-matrix extension; artifact replay remains open |
| Execution evidence aggregate-only | `CONFIRMED / IMPLEMENT` | Versioned execution-evidence artifact |
| Reconciliation false bit has no detector provenance | `CONFIRMED / CONTRACT_REQUIRED` | Versioned reconciliation result |
| Identity alias/revision splits | `CONFIRMED / LOCAL_TRANSITION_BINDING_IMPLEMENTED` | Shared identity contract and hash-bound Decision resolution; authoritative source/child replay remains open |
| Exposure/cash cause state loss | `CONFIRMED / LOCAL_TRANSITION_BINDING_IMPLEMENTED` | Structured cause records join exact obligations and expose retry transition; child replay matrix remains open |
| Config/runner identity absent from artifacts | `CONFIRMED / LOCAL_LINEAGE_IMPLEMENTED` | Artifact lineage fields and equality gates; operational binding matrix remains open |
| Controller crash windows | `CONFIRMED / LOCAL_RECOVERY_FENCE_IMPLEMENTED` | Durable recovery-required fence; side-effect matrix remains open |
| Latest snapshot no recovery path | `CONFIRMED / IMPLEMENT_AFTER_CHAIN_CONTRACT` | Immutable quarantine/recovery manifest |
| Post-entry concentration overlay | `POLICY_GAP / DO NOT INVENT` | Remains unresolved unless authoritative policy appears |
| Dividend tax/net treatment | `POLICY_GAP / DO NOT INVENT` | Remains gross-only bounded behavior |
| Unsupported structural CA admission | `EXTERNAL_BLOCKED / FAIL CLOSED` | No provider/data work in this lane |

## Dependency order

1. Quantity-obligation contract and invariant engine.
2. Execution and Decision/replacement adapter integration.
3. Durable state, snapshot, restart, and legacy migration.
4. CA/accounting composition and projected-state lineage.
5. Execution-evidence evaluation contract.
6. Reconciliation provenance contract.
7. Identity and exposure/cash cause contracts.
8. Config/artifact lineage.
9. Controller crash recovery.
10. Latest-snapshot immutable quarantine/recovery.
11. Independent post-remediation system challenge.

Every material change must show: old failing case, neighboring adversarial
case, cross-component replay, restart/idempotency, legacy behavior, and a
second-order challenge.

## Current implementation evidence

The isolated lane currently contains:

- `OBLIGATION-V1` source and invariant tests;
- additive `PaperPortfolioState.obligations` ownership with compatibility
  pending projections and an obligation-aware state hash;
- positive partial BUY persistence and retry completion;
- positive partial BUY restart replay: the V2 snapshot reload preserves the
  filled/remainder split before the next-session retry;
- partial SELL and paired replacement quantity lineage;
- duplicate fill/cancel idempotency at the obligation layer;
- explicit `RUNTIME_SCHEMA_V2` obligation snapshot serialization chained to V1
  parents, with old payload compatibility;
- legacy migration classification that returns `UNKNOWN_ORPHANED_PARTIAL`
  instead of fabricating missing plan/fill quantities;
- immutable quarantine/recovery for a tampered latest snapshot, with valid
  fork histories still rejected;
- Decision V2 residual retry for a partial BUY whose actual position already
  exists, without changing Decision science.
- explicit CA sizing lineage separating raw execution state from projected
  total-return NAV; the E2E plan no longer silently rebinds only outer hashes;
- `CA_TIMING_MATRIX-V1` classifies payment-before-decision,
  payment-on-decision, payment-on-execution, and later payment boundaries,
  while permitting only hash-bound additive preopen CA extensions;
- persisted execution replay rechecks nested evidence/reconciliation/timing/
  lineage parents, including a tamper test that recomputes only the outer hash;
- projection guard that rejects changes to positions, pending intents,
  obligations, reconciliation state, or state source identity;
- versioned `EXECUTION_EVIDENCE-V2` artifact with per-fill quantities,
  parent/state hashes, cash/position replay, turnover, pending, and
  reconciliation checks;
- typed `RECONCILIATION_RESULT-V1` provenance artifact binding the internal
  detector to CA attestation/source and execution-evidence hashes, with
  explicit `NOT_PERFORMED` external reconciliation scope; its verifier also
  validates dates, hash-shaped provenance fields, normalized ticker sets, and
  coverage inclusion;
- `IDENTITY_CANONICAL-V1` interval/alias/revision validation with unresolved
  identity failure;
- `EXPOSURE_CAUSE-V1` records attached to quantity-bearing evidence;
- bound exposure causes explicitly report zero position on new entry and full
  exit, while preserving `None` only when the before-state is unavailable;
- `TRANSITION_BINDING-V1` hash-binds Decision identity resolutions and joins
  positive-quantity causes to same-session obligations, preserving explicit
  `RETRY_OBLIGATION` semantics;
- orchestration replay requires and revalidates persisted Decision identity
  evidence, rejecting missing or source-hash-tampered rows;
- `RUNTIME_LINEAGE-V2` and controller `RECOVERY_REQUIRED` crash fence;
- runtime-lineage verification rejects hash-valid noncanonical binding status
  and field combinations;
- obligation deserialization rejects hash-valid noncanonical field extensions;
- synthetic paired replacement retry reloads the V2 snapshot, carries the
  partial SELL remainder into the next session, and fills the replacement BUY
  only after SELL completion;
- operational `BOUND` lineage is persisted/rechecked across synthetic
  prepare/execute/replay and config mismatch is rejected;
- hash-pinned controller prepared-artifact selection rejects missing/unbound
  operational runtime lineage;
- persisted replay cross-checks lineage contract/artifact links and
  reconciliation CA/session parents, including rehashed-tamper tests;
- persisted replay validates cause-obligation binding rows and session scope,
  recomputes obligation join content from state-after rows, and rejects a
  rehashed join-content tamper;
- persisted orchestration replay rejects rehashed nested obligation payload
  extensions through canonical deserialization;
- persisted execution evidence replay canonically parses and reevaluates
  intrinsic fills, state, turnover, pending, and reconciliation invariants;
- CA timing verification rejects hash-valid noncanonical rows and inconsistent
  payment timing/action semantics;
- transition-binding verification rejects hash-valid noncanonical identity and
  cause-obligation envelopes and rows;
- hash-pinned identity evidence rejects hash-valid noncanonical envelope and
  row extensions before child resolution;
- `MIGRATION_PROVENANCE-V1` records legacy source hash/schema, state hash when
  valid, fail-closed classification/disposition/reason, UTC decision time, and
  optional runtime lineage with immutable idempotent persistence;
- `MIGRATION_ACTIVATION-V1` adds an immutable explicit-policy decision gate:
  compatible state can activate, legacy mode requires authorization, and
  orphaned/reconciliation-required state remains blocked;
- orchestration state loading consumes verified-ancestor snapshot recovery;
- dual-calendar V2 controller recovery-fence parity covers all eight synthetic
  side-effect boundaries without provider or outcome access;
- dual-calendar V2 missed-execution handling reuses the exact schedule-bound
  prepared parent when no certified Open exists, with regression coverage;
- latest-snapshot recovery rejects noncanonical snapshot filenames with a
  typed fail-closed error;
- synthetic recovery preserves the verified ancestor's partial obligation
  ledger and pending projection;
- snapshot loading replays the canonical builder and rejects hash-valid but
  noncanonical payload envelopes;
- top-level T0, prepared, execution, transaction, meta, and missed-execution
  artifacts require explicit canonical key envelopes before replay consumers
  proceed; hash-valid unknown top-level extensions fail closed;
- post-implementation independent challenge is recorded PASS for nested replay,
  lineage, CA, cause, identity, snapshot, migration, and controller gates;
- independent challenge V2 also covers real synthetic child interruption,
  hash-pinned identity child wiring, prepared selection, migration activation
  policy, and the verified-snapshot migration consumer; external/live
  validation remains intentionally closed;

Focused cross-component suites pass: execution/allocator/exit/replacement,
Decision adapter, quantity contract, dividend runtime/snapshot, dividend
execution/orchestration, schedule binding, and E2E paper
orchestration/controller. Current HEAD `ba38396a` also passes the full
repository regression with only the three pre-existing pandas warnings. The
follow-up top-level execution replay tamper assertion also passes at
`600866ae`; it rehashes an unknown top-level extension and confirms existing
execution replay rejects it before any idempotent completion path.
The V2 independent-challenge record predates the latest local envelope
hardening;
its synthetic gates remain evidence, not a fresh final challenge at this HEAD.
External authorization/adoption, authoritative identity-source provisioning,
live provider/scheduler interruption validation, automatic migration activation,
and the remaining Decision-seat/cancellation semantics are still open. This
is not a production promotion or phase closure.

## Boundaries

- Frozen alpha and Decision V2 substantive science must not change.
- Protected H5/H10/OOS/PnL and incumbent predictive comparisons remain closed.
- No canonical-data rewrite, provider acquisition, production deployment,
  cloud/capture/telemetry/scheduler mutation, counter mutation, push, or merge.
- Historical artifacts remain immutable evidence; no fabricated legacy
  quantities and no rewrite to make old results appear compliant.

## Durable companion records

- Remediation registry: `docs/checkpoints/2026-09-20_IDX_REMEDIATION_REGISTRY_V1.md`
- Contract catalog: `docs/checkpoints/2026-09-20_IDX_VERSIONED_CONTRACT_CATALOG_V1.md`
- Migration matrix: `docs/checkpoints/2026-09-20_IDX_MIGRATION_COMPATIBILITY_MATRIX_V1.md`
- Active handoff: `docs/checkpoints/2026-09-20_IDX_HARDENING_ACTIVE_FRONTIER_HANDOFF_V1.md`
- Challenge result: `docs/checkpoints/2026-09-20_IDX_INDEPENDENT_CHALLENGE_RESULT_V1.md`
- No-retry/policy log: `docs/checkpoints/2026-09-20_IDX_HARDENING_NO_RETRY_POLICY_LOG_V1.md`
