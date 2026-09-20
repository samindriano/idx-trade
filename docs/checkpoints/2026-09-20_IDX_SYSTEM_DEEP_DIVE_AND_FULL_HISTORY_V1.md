# IDX-Trade — System Deep-Dive and Full Historical Marathon Dossier V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `READ-ONLY FORENSICS / NO-GO FOR SYSTEM-WIDE CERTIFICATION`

This checkpoint has two deliberately separate evidence classes:

- `HISTORICAL / PRIOR`: work completed before this system-wide deep-dive. It is
  retained as history and is not silently upgraded into current runtime proof.
- `CURRENT DEEP-DIVE`: new read-only audits performed in the isolated lane on
  2026-09-20 against the pinned runtime and retained source references.

No protected H5/H10/OOS/PnL/hidden-incumbent outcomes were opened. No provider,
cloud, capture, telemetry, scheduler, canonical-data, production, or incumbent
state was modified. No code, configuration, experiment packet, counter, or
production artifact was changed by this checkpoint.

## 1. Executive conclusion

The system is not yet certifiable as restart-safe, accounting-complete, or
lineage-complete, even though several important components have strong bounded
controls and historical test evidence.

The current decision is:

`NO-GO / SYSTEM-COMPLETION BLOCKED BY OPERATIONAL AND EVIDENCE-CONTROL GAPS`

The most decision-changing current findings are:

1. T0 bootstrap and missed-Open continuity have crash windows that cannot be
   completed or reconciled safely after a process interruption.
2. The operational controller keeps phase/attempt state in memory; a crash can
   leave no durable state describing whether a side effect was running,
   retryable, missed-late, complete, or conflicted.
3. A positive partial BUY can be recorded as a complete holding while its
   unfilled planned remainder disappears from the retry path. Dividend tax is
   explicitly unresolved and the paper ledger credits gross cash.
4. Cloud/prepared execution artifacts do not bind the complete runtime-config
   identity. The CA/accounting hash can describe the raw pre-projection state,
   while sizing consumed a projected state.
5. Several persisted verifier PASS results are stale or semantically shallow:
   current-head freshness is not enforced, denylist/token scans admit disguised
   protected-looking fields, and nested packet schema is permissive.

These findings do not authorize reopening Decision V2, changing sizing policy,
opening protected evaluation, or repairing production in this lane.

## 2. Lane and provenance

Current isolated lane:

- worktree: `C:\Users\Sam\.codex\worktrees\idx-alpha-available-data-20260919`
- branch: `codex/alpha-available-data-20260919`
- observed HEAD: `51c527155c6b5ad6ed5b25cb1a68a3a2ce217c1d`
- latest observed HEAD subject: `research: audit official announcement authority surface`
- authoritative coordination source read before this work:
  `origin/main:coordination/TEAM_STATUS.md`

At the time of this checkpoint, two pre-existing untracked files were visible:
`research/alpha_idx_financial_report_surface_v1.py` and
`tests/test_alpha_idx_financial_report_surface_v1.py`. They were not created,
staged, edited, or removed by this deep-dive.

The current lane remains an isolated pre-admission/research lane. The canonical
project status says the project is in system-completion mode, Decision V2 is
closed, the E2E paper path is active, the 100-session evaluation is blocked,
and protected outcomes must remain closed.

## 3. Historical / prior marathon record

### 3.1 The complete prior alpha archive

The complete earlier alpha marathon is already preserved in:

`docs/checkpoints/2026-09-20_ALPHA_MARATHON_ALL_FINDINGS_ARCHIVE_V1.md`

That archive is the authoritative navigation layer for the previous marathon
and should be read together with its machine records. It contains, among other
things:

- historical archaeology and failure taxonomy;
- Stockbit/Zapi capture reliability and retention history;
- V4-X1 prospective gate and operational reliability history;
- closed-family alpha archaeology;
- corrected Stage-A construction and independent replay;
- fixed C1-C4 structural results;
- orthogonality, overlap, horizon, normalizer, breadth, turnover, and score
  geometry diagnostics;
- H-LIQ, H-VOL, H-EXC-01, and H-EXC-02 red-team boundaries;
- corporate-action, price-basis, identity, issuer, source, and PIT findings;
- local Zapi and public EOD/IPO capability probes;
- eligibility-policy conflict, feature warm-up, anchor-state, and population
  boundary findings;
- verifier, packet, freshness, nested-schema, and semantic-challenger limits;
- exact no-retry and no-admission rules.

Its machine record at the time of the archive reported 54 experiment records,
47 findings, 17 no-retry records, and 18 source-capability records. Those
numbers are historical archive metadata, not a claim that the current working
tree has not advanced since then.

The prior alpha conclusion was:

`NO-GO / PRE-ADMISSION / OUTCOME-BLIND / PREDICTIVE STAGE BLOCKED`

No better predictive model was established. C1/C2/C4 remained structural
research candidates; C3 remained blocked by sparse/late financial support.

### 3.2 Historical / prior system-completion results

The following results are retained from the pinned historical E2E/runtime
lineage. They are useful evidence of what was tested and what was previously
accepted, but they are not a substitute for the current deep-dive findings.

#### Cash dividend and E2E remediation — HISTORICAL / PRIOR

Recorded in the retained coordination handoffs:

- `coordination/handoffs/IDX-CASH-DIVIDEND-E2E-REMEDIATION-RESULT.md`
- `coordination/handoffs/IDX-CASH-DIVIDEND-E2E-ADVERSARIAL-RESULT.md`

The prior work addressed economic oracles, child-process restart, phase-boundary
reporting, same-announcement blocker recovery, and cash/dividend lifecycle
orchestration. The recorded validation included:

- remediation focused suite: 83 passed;
- remediation full suite: 656 passed;
- adversarial focused suite: 126 passed;
- adversarial full suite: 662 passed;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- deterministic core replay: PASS;
- production-path replay: PASS;
- resume probe: PASS.

The prior handoff states that the tested path covered capacity, lot, price, fee,
and cash rules; both BUY and SELL fee/slippage paths; exact below/above stamp
duty behavior; exact per-session fill vectors; and cold restart of a completed
execution session. The same historical handoff also says that receivables affect
total-return NAV for sizing but are not spendable cash, and that divergent
pre-existing state fails closed.

The new deep-dive below does not invalidate those bounded passes. It identifies
additional edge paths not closed by them: positive partial-BUY remainder
handling, unresolved dividend tax policy, T0 bootstrap crash recovery, and
durable controller/continuity state.

#### E2E controller integration — HISTORICAL / PRIOR

`coordination/handoffs/IDX-E2E-PAPER-CONTROLLER-INTEGRATION-V3.md` records a
fail-closed phase-oriented controller integration, provider checkout identity,
and prior focused/full test passes. It explicitly retained independent review,
cold-restart, invocation, fault-handling, and idempotency decisions as gates
before weekday acceptance.

#### Cloud-first orchestration — HISTORICAL / PRIOR

`coordination/handoffs/IDX-E2E-CLOUD-FIRST-ORCHESTRATION-V1.md` records prior
cloud-runtime implementation and validation, including 13 focused cloud-runtime
tests, the relevant E2E/Official Open regression group, and a full pytest pass
with three existing pandas warnings. The historical cloud path was intended to
preserve checkout/input identity and fail closed.

The current deep-dive finds that the cloud entrypoint and prepared artifact
lineage still do not bind the full runtime-config identity. This is a lineage
hardening finding, not proof that a historical production run used the wrong
configuration.

#### Official Open and pre-weekday reconciliation — HISTORICAL / PRIOR

`coordination/handoffs/IDX-E2E-PAPER-FINAL-PRE-WEEKDAY-RECONCILIATION.md` records
prior Official Open/execution focused validation (47 passed), operational/CA/
orchestration validation (97 passed), and a full suite of 702 passed with three
pre-existing pandas warnings. The official IDX CA endpoint was recorded as
HTTP 403 in that environment, so the handoff kept the external-evidence blocker
explicit rather than fabricating completion.

## 4. Current deep-dive — runtime, state machine, and restart

Audit snapshot: retained pinned runtime
`32eaaa8e50d0521de7faef98faa8081219bc667b` for the operational-controller
analysis. No provider or protected-outcome access occurred.

### 4.1 Bounded PASS: execution artifact atomicity and staged recovery

`src/idx_trade/e2e_paper_orchestration_v1.py:_atomic_write` uses a temporary
file, fsync, and immutable-conflict checks. `execute_preopen` stages a
transaction and writes snapshot, execution, and metadata. `_recover_staged_execution`
can reconstruct missing snapshot/execution artifacts. Existing synthetic tests
cover duplicate execution and missing execution/snapshot recovery.

This is a bounded execution-artifact PASS, not a whole-controller restart PASS.

### 4.2 FAIL: T0 bootstrap crash window

`bootstrap_t0` writes the runtime snapshot before `state/T0.json`. If the process
dies between those writes, the next invocation sees pre-existing snapshot state
and raises `E2E_T0_PREEXISTING_RUNTIME_STATE`; it cannot complete or reconcile the
matching interrupted bootstrap.

Required closure: a durable bootstrap intent/transaction or an explicit
recovery rule that validates and completes the matching snapshot/T0 pair.

### 4.3 FAIL: missed-Open continuity is not one recoverable transaction

In `e2e_paper_continuity_schedule_v1.py`, the advanced snapshot, missed-execution
audit, and metadata are written in separate sequences. Two crash windows are
material:

- crash after snapshot but before audit: retry can reject the advanced state as
  `E2E_MISSED_EXECUTION_STATE_SESSION_MISMATCH`;
- crash after audit but before metadata: retry can return the existing audit
  without repairing metadata, and the next `prepare_post_eod` can reject the
  previous score as bootstrap/conflicting state.

Required closure: one recoverable continuity transaction, or an explicit
reconciliation procedure that must run before the next session is admitted.

### 4.4 FAIL: operational controller is not a durable state machine

`e2e_paper_operational_controller_v2.py:run_operational_cycle_v2` keeps RUNNING
state in memory; latest state is persisted through finish, while child
execution occurs later. A crash during CA capture or child execution leaves no
durable phase, attempt, lease, heartbeat, or terminal reason.

Required closure: persist phase/attempt state before side effects and reconcile
on restart into explicit `RETRYABLE`, `MISSED_LATE`, `COMPLETE`, and conflict
states. This must be tested with fault injection at each side-effect boundary.

### 4.5 PASS with limitation / UNKNOWN: locking and malformed prepared state

`e2e_operational_guard_v1.py:exclusive_run_lock` provides OS-level process
exclusion and releases on crash; the focused lock test passed. Snapshot/schema/
hash corruption fails closed through verified reads and runtime snapshot checks.

However, `_prepared_for_session` in
`e2e_paper_operational_controller_v1.py` silently skips malformed prepared
artifacts. That can surface as `WAITING_PREPARED_EXECUTION` instead of an
explicit corruption/quarantine state. Malformed-state recovery remains UNKNOWN.

## 5. Current deep-dive — accounting, cash, sizing, execution, and CA

Audit snapshot: retained ref
`origin/integration/idx-e2e-baseline-paper-v1@6e1bf4a1`.

### 5.1 PASS: core sequencing and bounded fee rules

`execute_open_v1` sells before buys, applies 25 bps sell fees and 15 bps buy
fees, charges Rp10,000 stamp duty above Rp10m turnover, enforces non-negative
cash, and keeps whole-lot holdings. The cited tests cover the main sequencing,
fee, and capacity cases.

### 5.2 UNKNOWN / potential FAIL: positive partial BUY remainder disappears

`joint_open_allocation` caps lots by capacity, but `execute_open_v1` persists
`pending_buys` only when filled shares are zero. A positive fill below
`planned_shares` can become a complete held position without preserving the
unfilled remainder for later retry.

Synthetic counterexample from the audit: with Rp50m NAV, a Rp1,000 target,
Rp100m reference value, and a 10-lot capacity, 50 lots are planned, 10 are
held, and the remaining 40 lots have no retry record.

Required policy decision: determine whether planned lots are an upper bound or
an intended quantity. If intended, persist a residual-order state and define
its next-session semantics; if upper bound, encode and test that policy
explicitly rather than silently dropping the remainder.

### 5.3 FAIL: dividend tax treatment is unresolved

`src/idx_trade/forward_dividend_v1.py` declares
`TAX_TREATMENT = "UNRESOLVED_GROSS_PAPER_CREDIT"`; settlement credits gross
dividend cash without withholding. The existing test confirms the gross-credit
behavior, but that is not a tax-complete accounting policy.

Required closure: a frozen tax/accounting policy, explicit ledger fields, and
replay tests for gross, withholding, and any applicable jurisdictional rule.

### 5.4 PASS: CA fail-closed boundary and cash-dividend routing

Plain CA booleans are rejected. Execution requires hash-verified CA coverage;
cash-dividend events route through verified reconciliation, and unsupported
structural actions are not silently transformed. Persisted dividend snapshots
are immutable/parent-bound and repeated settlement is idempotent in the tested
path.

Coverage of non-cash structural CA families remains UNKNOWN.

## 6. Current deep-dive — cross-subsystem lineage and configuration

Audit snapshot: detached pinned runtime
`045e25a19d9f71170d2c863e768102937e59ad73`; the audit reported authoritative
`origin/main` at `8b5bc6db1a4d89ca0fb2a49760899d3f18453f23` for that historical
runtime snapshot.

### 6.1 FAIL: cloud path does not enforce the hash-pinned runtime config

`scripts/run_e2e_paper_cloud_v1.py:_controller_config` and `run_once` build
configuration from environment/current HEAD but do not verify config JSON, config
SHA, or runner SHA in the same manner as the scheduled bootstrap attestation.
Cloud result identity records commit/runner data without the complete config
identity.

Counterexample: the schedule and input manifest remain unchanged while cloud
environment/provider-path configuration changes.

### 6.2 FAIL: prepared POST_EOD lineage omits runtime-config identity

`prepare_post_eod` and
`e2e_paper_schedule_binding_v1.py:write_prepared_schedule_binding` bind scores,
EOD artifacts, calendar, and planned schedule, but not runtime-config SHA,
runner SHA, executable paths, or complete provider configuration.

Counterexample: prepare under configuration A, execute under compatible
configuration B; schedule/EOD hashes still pass.

### 6.3 FAIL: CA/accounting hash can describe the wrong state for sizing

`_state_for_dividend_sizing` projects CA state, but the orchestration path can
overwrite `dividend_state_hash` and `dividend_ledger_hash` with raw pre-
projection state. A certified dividend can therefore alter projected cash/NAV
used for sizing while the recorded hash describes the unprojected state.

Required closure: hash and persist the exact projected state consumed by sizing,
alongside the raw parent hash and transformation/projection identity.

### 6.4 FAIL: cloud/local backend boundary is permissive

`build_cloud_store_from_env` accepts `E2E_CLOUD_STORAGE_BACKEND=local`, and the
cloud runner does not reject that value at a production entrypoint.

Counterexample: environment drift to `local` can produce a local commit through
the cloud runner. This is a configuration-safety issue, not evidence that such
drift occurred in a historical run.

### 6.5 PASS / UNKNOWN: certified cash-dividend parent guards

`_verify_prepared_ca_parent` enforces scope, parent-event immutability, and
evidence for new events. `execute_open_v1_1_reconciled` rechecks date scope
before applying events. Coverage of non-cash structural corporate actions is
still UNKNOWN.

## 7. Current deep-dive — evaluation and verifier integrity

### 7.1 FAIL: persisted verifier PASS is stale

The persisted external result records PASS for contract SHA
`1385ce...` at HEAD `4ca81d...`, while the current contract SHA is `a76cd5...`
after commit `02a7429d`. The verifier emits hashes but does not validate the
freshness of a historical result against the current contract/head.

Therefore the historical PASS cannot be treated as current gate evidence until
it is independently rebound and rerun against the current head.

### 7.2 FAIL: firewall has semantic false-greens

`research/alpha_research_target_firewall_v1.py` relies on denylist/token scans
and non-empty Parquet schema checks. Synthetic fields such as
`future_ret5_value`, `secret_signal`, and disguised variants can pass. The
result proves only the bounded static assertions that were checked, not absence
of protected payload semantics.

### 7.3 FAIL: nested authority-packet schema is permissive

`research/verify_alpha_data_authority_packet_v1.py` checks top-level keys and
broad state conditions but not an exact nested schema. The nested-schema
challenger recorded cases where unknown/missing nested fields still produced a
current-verifier PASS. The strict nested allowlist remains unintegrated.

### 7.4 UNKNOWN: verifier independence and formula circularity

Hash/envelope checks do not independently recompute producer formulas and cannot
prove runtime access absence. Independent constructor/mutation challengers are
useful controls, but they do not establish source authority or correctness of
an admitted artifact.

### 7.5 PASS scoped / UNKNOWN real-world absence: protected access gate mechanics

`src/idx_trade/prospective_evaluation_gate_v1.py` requires explicit
authorization and code pins, rehashes inputs immediately before marker
publication, enforces marker-before-loader, and fails closed on partial state.
These are strong static transaction controls. They are not independent proof
that real runtime access never occurred.

### 7.6 UNKNOWN: external source freshness

The current-head attestation checks Git-bound files and hashes but explicitly
leaves external-source freshness UNKNOWN. The future packet remains correctly
blocked until this authority is resolved.

## 8. Interaction map: how the failures compose

The important system interaction is:

`candidate/rank -> predecessor session -> EOD/Open -> CA projection -> NAV/cash
 -> sizing -> lot allocation -> execution -> PaperState -> restart/replay`

The current evidence shows:

- alpha/rank output can be structurally reproducible while rank-conditioned Open
  readiness and source admission remain unresolved;
- Decision/Sizing/Execution can be individually tested while the exact projected
  CA state and runtime configuration are not fully bound into the stage lineage;
- execution artifact recovery can be sound while T0/continuity/controller
  recovery is not;
- cash and fee arithmetic can pass while partial-fill residual semantics and tax
  policy remain unresolved;
- gate mechanics can fail closed while stale/static verifier PASS and semantic
  false-greens make the evidence registry itself unsafe to treat as current
  certification.

Consequently, a passing component test is not a system-level PASS unless its
input identity, projected state, runtime configuration, durable phase state, and
replay semantics are all bound.

## 9. Consolidated component status

| Surface | Current disposition | Meaning |
|---|---|---|
| Alpha structural research | `HISTORICAL / STRUCTURAL ONLY` | Extensive prior evidence; no predictive winner or admission. |
| Decision V2 | `FROZEN / DONE` | Do not reopen tuning from these operational findings. |
| Core sell-before-buy/fee/lot arithmetic | `PASS BOUNDED` | Main path tests exist. |
| Cash-dividend parent/replay path | `PASS BOUNDED` | Certified cash-dividend path is guarded and idempotent in tested cases. |
| Non-cash CA coverage | `UNKNOWN` | No complete system-level authority established. |
| Positive partial BUY remainder | `UNKNOWN / POTENTIAL FAIL` | Residual can disappear; policy is not explicit. |
| Dividend tax accounting | `FAIL / UNRESOLVED` | Gross-credit paper policy is explicitly unresolved. |
| Execution artifact atomic recovery | `PASS BOUNDED` | Does not cover all phase/state transactions. |
| T0 bootstrap recovery | `FAIL` | Snapshot/T0 write gap is not recoverable. |
| Missed-Open continuity recovery | `FAIL` | Snapshot/audit/metadata writes are not one transaction. |
| Controller durable state machine | `FAIL` | RUNNING/attempt/phase state is memory-only during side effects. |
| Runtime-config lineage | `FAIL` | Cloud/prepared artifacts omit full config identity. |
| Projected CA hash lineage | `FAIL` | Recorded hash may describe pre-projection state. |
| Cloud/local boundary | `FAIL` | Local backend is accepted by cloud entrypoint. |
| Protected gate mechanics | `PASS SCOPED` | Strong static controls; not proof of real-world absence. |
| Verifier freshness | `FAIL` | Historical PASS is not bound to current contract/head. |
| Verifier semantic firewall | `FAIL / KNOWN GAP` | Token/denylist checks false-green on disguised fields. |
| Nested packet schema | `FAIL / KNOWN GAP` | Unknown/missing nested fields can PASS. |
| Verifier formula independence | `UNKNOWN` | Producer recomputation and runtime absence are not proven. |

## 10. No-retry and no-mutation boundary

This dossier does not authorize:

- another alpha/model smoke or protected evaluation;
- a new worker smoke solely to confirm these findings;
- Decision V2 tuning, sizing-policy tuning, or C5/model expansion;
- a provider/scraper/Zapi call or canonical-data fill;
- production/cloud/capture/telemetry/scheduler edits;
- reset, archive, backfill, counter mutation, merge, push, or deployment;
- treating a historical PASS as current without freshness rebinding.

The next implementation work, if separately authorized, should be isolated and
sequenced as bounded hardening experiments with synthetic fault injection:

1. durable T0 and continuity transaction/reconciliation state;
2. controller phase/attempt/lease persistence and restart classification;
3. explicit partial-fill residual policy and tests;
4. frozen dividend tax/accounting policy;
5. immutable runtime/config identity in prepared and execution artifacts;
6. projected CA-state hash lineage;
7. production rejection of local cloud storage;
8. verifier result freshness, strict nested schema, and semantic allowlist;
9. independent producer-formula recomputation where a gate depends on it.

## 11. Final handoff

The historical alpha marathon is fully preserved separately and remains
outcome-blind. The new system-wide deep-dive found meaningful bounded PASS
surfaces, but also multiple independent FAIL/UNKNOWN conditions that prevent a
system-level certification. The strongest immediate blocker is restart/state
durability; the strongest accounting blocker is partial-fill/tax semantics; the
strongest evidence-control blocker is stale/semantic verifier PASS; and the
strongest lineage blocker is missing runtime/config/projected-CA identity.

No retry was performed, no protected result was opened, and no other lane was
modified.

## 12. Continuation index — risk, economics, and component coupling

The following later checkpoints extend this dossier without changing the
historical alpha archive:

- `2026-09-20_IDX_RISK_CONCENTRATION_HOLDING_AUDIT_V1.md`:
  nominal entry sizing and local execution guards are present, but no active
  drawdown, sector, factor, issuer-concentration, or post-entry weight overlay
  is certified. Underfill, cash state, pending orders, and concentration remain
  coupled but not represented by one portfolio-risk invariant.
- `2026-09-20_IDX_TRANSACTION_COST_CAPACITY_AUDIT_V1.md`:
  fee/slippage/stamp arithmetic is deterministic, while slippage is explicitly
  uncalibrated, regular-market-value is only a capacity proxy, aggregate
  session liquidity is not modeled, and paper fills are not broker-fill proof.
  A ten-name synthetic order set confirmed all individual caps can pass with
  aggregate gross fill near Rp9.009m and no aggregate liquidity guard.
- `2026-09-20_IDX_DECISION_SIZING_EXECUTION_CONTRACT_AUDIT_V1.md`:
  Decision V2→Sizing V1→Execution V1 has meaningful provenance and fail-closed
  checks, but full runtime-config identity, projected-CA/NAV identity, and a
  unified underfill/cash/pending/risk taxonomy remain missing.
- `2026-09-20_IDX_PINNED_RUNTIME_SYNTHETIC_VALIDATION_V1.md`:
  the pinned component/E2E test slices passed `86` tests in an isolated scratch
  extraction. This confirms bounded regression coverage, not crash-recovery,
  broker-fill, executable-capacity, or protected-outcome proof. A direct
  injected failure after the T0 snapshot and before `T0.json` reproduced the
  retry error `E2E_T0_PREEXISTING_RUNTIME_STATE`; a second injection after the
  missed-Open continuity snapshot reproduced
  `E2E_MISSED_EXECUTION_STATE_SESSION_MISMATCH`.
- `2026-09-20_IDX_DECISION_STATE_REGIME_MATRIX_V1.md`:
  a four-session synthetic rank sequence confirmed the persistence asymmetry:
  a fresh rank-1 challenger is delayed, a confirmed exit can create a real
  nine-seat underfill, and the challenger fills only after prior-rank
  qualification. This is a Decision/cash/exposure state, not merely a rank
  output.

- `2026-09-20_IDX_CA_DIVIDEND_LIFECYCLE_AUDIT_V1.md`:
  the earlier direct IDX cash-dividend work is preserved as HISTORICAL/PRIOR,
  while the current pinned-runtime continuation confirms the bounded
  certified-event -> entitlement -> receivable -> settlement -> cash path,
  NAV-versus-spendable-cash separation, late-certification historical-state
  requirement, and recursive runtime/journal checks. Zapi's historical
  coverage/revision request remains a source lead only: local admission is
  still blocked, non-cash CA remains fail-closed, and tax/net policy is
  unresolved. The continuation slice passed `116` tests.
- `2026-09-20_IDX_CROSS_COMPONENT_PARTIAL_FILL_CA_MATRIX_V1.md`:
  an isolated replacement scenario confirmed that a 1% capacity-limited exit
  can partially fill, preserve the residual holding and pending sell, and
  block the paired buy while maintaining cash/lot invariants. The result is a
  deterministic paper transition, not broker reconciliation; the
  `reconciliation_required=false` interpretation, pending-age escalation, and
  multi-session interaction with dividend settlement remain policy questions.
  A direct composition probe also preserved the dividend ledger across the
  partial exit and settled Rp125,000 exactly once, while process-restart
  coverage across that combined path was then exercised through a synthetic
  five-snapshot chain. The ledger and hashes survived reload; payment cash
  increased while pending replacement remained pending, confirming that cash
  settlement and pending-order reconsideration are separate policy events.
- `2026-09-20_IDX_RUNTIME_CONFIG_ARTIFACT_IDENTITY_AUDIT_V1.md`:
  the pinned runtime config loader and controller guard are hash/commit pinned
  and passed 22 focused tests, while the 27-test orchestration slice also
  passed. The audit confirms the remaining lineage gap precisely: prepared and
  execution artifacts bind state/input/plan hashes but omit the full external
  config SHA, runner SHA, executable identity, and explicit code identity. This
  is a read-only `FAIL — RUNTIME_CONFIG_IDENTITY_NOT_BOUND`, not evidence of a
  live contamination or a reason to modify the active system in this lane.
- `2026-09-20_IDX_UNIVERSE_IDENTITY_WARMUP_STRESS_AUDIT_V1.md`:
  a 19-test baseline passed, but three synthetic cross-component probes found
  structural gaps: pre-listing observations count toward IPO warmup and
  liquidity, normalized `TICKER`/`TICKER.JK` aliases can create duplicate
  selected rows, and overlapping listing eras are accepted while downstream
  state remains ticker-only. This is `FAIL —
  UNIVERSE_IDENTITY_AND_WARMUP_BOUNDARY_NOT_PROVEN`; no policy or source fix
  was applied.
- `2026-09-20_IDX_EVALUATION_IDENTITY_CONTRACT_AUDIT_V1.md`:
  the synthetic-only prospective suite passed 120/120, but the pure metric
  evaluator accepts `ALIS` and `ALIS.JK` as distinct issuers while the final
  score-artifact gate normalizes `.JK` and rejects the collision. This is
  `FAIL — EVALUATION_IDENTITY_CONTRACT_SPLIT`; no source or data fix was
  applied.
- `2026-09-20_IDX_STORAGE_REVISION_ATOMICITY_AUDIT_V1.md`:
  the lane-local storage/backfill suite passed 8/8, but duplicate dates in
  existing history raise an uncontrolled ambiguous-Series `ValueError`, while
  duplicate dates in incoming history silently keep the last row. Atomic
  writers also replace existing destinations and are not immutable evidence
  writers. Verdict: `FAIL — DUPLICATE-DATE STORAGE INPUT NOT FAIL-CLOSED`;
  no source or data fix was applied.
- `2026-09-20_IDX_PRICE_CA_REPRESENTATION_AUDIT_V1.md`:
  the data-gate slice passed 7/7, but malformed optional split/dividend values
  are coerced to `NaN` and then filled as zero, making invalid CA input look
  like a no-event; duplicate dates are also silently reduced to the last row.
  Verdict: `FAIL — INVALID OPTIONAL CA VALUES ARE NOT PRESERVED AS UNKNOWN`;
  no source or data fix was applied.
- `2026-09-20_IDX_EXECUTION_STATE_IDENTITY_AUDIT_V1.md`:
  the retained runtime branch passed 59 focused execution/E2E tests, but a
  fractional share value is silently truncated during state normalization and
  a `replacement_peer` alias such as `AAA.JK` can leave a replacement buy
  pending after the canonical `AAA` sell has fully filled. Verdict: `FAIL —
  EXECUTION IDENTITY/STATE COERCION BOUNDARY`; no runtime source fix was
  applied.
- `2026-09-20_IDX_DIVIDEND_SIZING_STATE_HASH_AUDIT_V1.md`:
  a synthetic payment-on-decision-date case settled projected cash for sizing
  but failed at next-stage execution with `EXECUTION_V1_STATE_HASH_MISMATCH`:
  the base plan was hashed from projected state while execution used the raw
  persisted state. Verdict: `FAIL — PROJECTED CA SIZING STATE IS NOT
  EXECUTION-PARENT-COMPATIBLE`; no runtime source fix was applied.
- `2026-09-20_IDX_SIZING_EXECUTION_PARTIAL_BUY_AUDIT_V1.md`:
  a positive partial buy filled 2,500 of 5,000 planned shares after an Open
  price gap, but produced no pending buy; the next session generated no retry,
  and snapshot/reload preserved the underfilled position with a valid hash.
  Verdict: `FAIL — POSITIVE PARTIAL BUY IS NOT PERSISTED AS PENDING`; no
  runtime source fix was applied.
- `2026-09-20_IDX_PARTIAL_BUY_TRIGGER_MATRIX_V1.md`:
  four independent synthetic paths—capacity plus Open-price change, buy-fee
  cash boundary, stamp-threshold boundary, and paired replacement—each
  produced a positive planned-versus-filled gap with empty pending state and
  no next-session retry. This confirms a general sizing-to-execution obligation
  loss rather than a single price-gap incident. A separate ten-seat Decision V2
  run filled one seat only partially but still reported `FULL` with zero
  unfilled slots and no retry. No runtime source fix was applied.
- The same underfilled state was composed with the cash-dividend lifecycle:
  actual 1,200 shares correctly generated IDR 30,000 entitlement/settlement,
  while the 5,000-share planned hypothetical would have generated IDR 125,000.
  This is upstream execution underexposure propagating into CA economics, not
  a dividend-engine double-pay defect.
- The existing dividend-aware runtime snapshot writer/loader faithfully
  round-tripped the underfilled `AAA:1,200` position with empty pending state
  and equal runtime hash. Restart integrity therefore preserves the semantic
  loss instead of discovering or repairing it.
- Full orchestration recovery also returned `RECOVERED_STAGED_EXECUTION` with
  identical execution/snapshot hashes and the same `T00:2,400` underfill with
  no pending buy. Atomic recovery is deterministic, but cannot reconstruct a
  residual quantity absent from the transaction/state schema.
- Historical archaeology explains the asymmetry: `e1531b3c` introduced
  zero-lot buy pending plus ticker-set invariants, `d8d34b79` later explicitly
  hardened positive partial sells, and `ce91d60a` replayed positive buy
  planned/filled differences with pending count zero. The current defect is
  therefore a historical contract split, not only an allocator edge case.
- `2026-09-20_IDX_PENDING_CA_REVERSAL_MATRIX_V1.md` extends the frontier across
  four sessions: repeated partial exit and zero capacity preserve a pending
  replacement; a 5,000-share cash-dividend entitlement settles IDR125,000
  exactly once without triggering a replan; and the Decision V2 adapter
  deterministically cancels both pending rows on a later target reversal while
  emitting no typed cancellation lineage. The remaining gap is an obligation
  lifecycle contract (remaining quantity, age, attempts, expiry/escalation, and
  explicit cancellation), not dividend arithmetic.
- `2026-09-20_IDX_QUANTITY_OBLIGATION_STATE_CONTRACT_V1.md` records the first
  evidence-driven architecture proposal for that gap: a stable logical
  obligation ID with planned/filled/remaining/relinquished quantities, typed
  retry/block/cancel/expiry events, explicit CA settlement policy, and hash/
  restart binding. It is design-only and deliberately not a runtime patch.
- `2026-09-20_IDX_OBLIGATION_HISTORICAL_COMPATIBILITY_AUDIT_V1.md` reconciles
  `e1531b3c`, `d8d34b79`, and `ce91d60a`: zero-lot BUY pending and positive
  partial-SELL persistence can be migrated, but a historical positive partial
  BUY with no preserved plan must be marked `UNKNOWN_ORPHANED_PARTIAL` rather
  than assigned a fabricated remainder. The old `ce91d60a` replay oracle stays
  immutable; a future residual-aware oracle must be versioned.
- `2026-09-20_IDX_QUANTITY_OBLIGATION_REPLAY_HARNESS_V1.md` records a separate
  3/3 spec-harness PASS for quantity conservation, JSON reload, duplicate event
  idempotency, actual-share CA entitlement, and explicit target-reversal
  relinquishment. It is a design consistency result only; SELL/replacement and
  runtime adoption remain open.
- `2026-09-20_IDX_QUANTITY_OBLIGATION_REPLACEMENT_REPLAY_V1.md` extends that
  result with a 2/2 SELL/replacement harness: partial SELL, blocked paired BUY,
  JSON reload, retry, and explicit dual cancellation preserve quantities and
  event lineage. Runtime artifact adoption and migration remain unproven.
- `2026-09-20_IDX_OBLIGATION_ARTIFACT_SERIALIZATION_BOUNDARY_V1.md` closes the
  serializer ownership question: planned sizing and completed fill vectors are
  present, but the durable snapshot has no obligation ID, remaining quantity,
  attempt history, or cancellation lineage. The proposed remediation can be
  additive/versioned, but current hashes do not prove quantity completeness.
- `2026-09-20_IDX_OBLIGATION_ARTIFACT_MIGRATION_AUDIT_V1.md` records a 6/6
  fail-closed migration audit: complete fills, explicit zero-lot pending, and
  positive partials with preserved fill vectors are distinguishable, while a
  snapshot-only positive position remains `UNKNOWN_ORPHANED_PARTIAL` and a
  quantity inversion requires reconciliation. This is an isolated harness
  result; no runtime migration or historical rewrite was performed.
- `2026-09-20_IDX_UNIVERSE_IDENTITY_COLLISION_AUDIT_V1.md` adds a distinct
  identity-to-universe finding: the pinned runtime turns `ABCD` and `ABCD.JK`
  input aliases into two selected `ABCD` rows with ranks 1/2. The later
  Decision adapter rejects the duplicate, but the universe origin does not
  enforce canonical-key uniqueness; no runtime fix was applied.
- `2026-09-20_IDX_RUNTIME_CONFIG_ARTIFACT_IDENTITY_REVALIDATION_V1.md`
  revalidates the config-lineage gap at current runtime HEAD `402fca4b...`:
  loader fields `config_sha256`/`runner_sha256` are present, while prepared and
  completed orchestration artifact identity still omits them. This confirms a
  current artifact reproducibility blocker without executing or mutating the
  runtime.
- `2026-09-20_IDX_SECURITY_MASTER_REVISION_COLLISION_AUDIT_V1.md` adds an
  identity-history result refined by archaeology: active-vs-delisted duplicate
  preference was explicit in the original design, but same-class revisions
  sharing `(ticker, listed_from)` remain order-sensitive under `keep="last"`,
  leaving a valid-looking but history-dependent master. No canonical or runtime
  data was changed.

The durable rolling controls for this marathon are now:

- `2026-09-20_IDX_SYSTEM_FRONTIER_MATRIX_V1.md` — subsystem depth, evidence,
  open questions, and next frontiers;
- `2026-09-20_IDX_SYSTEM_FINDINGS_NO_RETRY_LOG_V1.md` — findings, blast-radius
  implications, negative results, and no-retry boundaries;
- `2026-09-20_IDX_ACTIVE_FRONTIER_HANDOFF_V1.md` — current hypothesis and
  immediate next questions.

The updated system-level belief is therefore:

`local component correctness != complete portfolio-system correctness`

The next distinct local frontier is not another alpha mutation. It is a
quantity-aware obligation/state graph that composes state transitions, partial
fills, CA settlement, pending expiry/reversal, nominal risk exposure, cost
accounting, restart, and artifact identity in one isolated scenario matrix.
