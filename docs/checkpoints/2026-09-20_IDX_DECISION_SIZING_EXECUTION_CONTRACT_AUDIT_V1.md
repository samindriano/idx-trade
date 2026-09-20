# IDX-Trade — Decision → Sizing → Execution Contract Audit V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `BOUNDED CONTRACT PASS / SYSTEM LINEAGE HARDENING STILL REQUIRED`

This is a read-only contract audit of the pinned Decision V2, Sizing V1, and
Execution V1 adapter. It does not reopen Decision research, inspect outcomes, or
change the live incumbent.

## 1. Runtime and scope

Pinned runtime:

`045e25a19d9f71170d2c863e768102937e59ad73`

Audited files:

- `src/idx_trade/decision_v2_minimal.py`
- `src/idx_trade/v4_x1_decision_v2_minimal.py`
- `src/idx_trade/v4_x1_sizing_v1.py`
- `src/idx_trade/v4_x1_sizing_v1_decision_v2_adapter.py`
- `src/idx_trade/v4_x1_execution_v1_decision_v2_adapter.py`

## 2. Bounded PASS findings

### 2.1 Decision underfill is explicit rather than silently renormalized

Decision V2 computes `unfilled_slots` and uses
`UNFILLED_NO_QUALIFIED_CHALLENGER` when fewer than ten target positions are
available. The profile requires underfill to be allowed. This is consistent
with the project policy that fewer than ten names retain residual cash rather
than renormalizing remaining names upward.

### 2.2 Sizing consumes only verified Decision V2 buy intents

The V2 sizing adapter verifies the plan before passing it to the sizing core.
The core rejects:

- non-buy intents in the buy set;
- duplicate buy intents;
- buys outside `target_positions`;
- buys outside Decision Top-10;
- missing reference prices;
- invalid cash/NAV;
- entry-cap, lot, and cash invariant violations.

The nominal target remains 10% per name with a 15% entry cap. Fewer buy intents
therefore produce fewer funded names, not larger remaining weights.

### 2.3 Session/provenance checks exist at each adapter boundary

The sizing adapter checks Decision rule identity, current score-session identity,
and previous score-session/hash identity. The execution adapter checks:

- paper-state session equals Decision session;
- EOD input session equals Decision session;
- prior reconciliation is not required;
- EOD NAV is finite/valid;
- raw close and Open inputs cover the involved names;
- Decision V2 target/buy/sell state is reconciled against paper state;
- buy/sell overlap and pending-state contradictions fail closed.

This is stronger than a loose function-to-function call and materially reduces
silent Decision→Sizing drift.

### 2.4 Pending reversal semantics are explicit

The V2 execution adapter explicitly checks reversal of a pending SELL before
paper fills it and reversal of a pending BUY before paper acquires it. It also
rejects invalid pending-buy/pending-sell state and unexplained shadow/paper
lineage mismatch.

These guards connect Decision state to executable paper state rather than
treating every new Decision plan as a clean slate.

## 3. Important hidden couplings

### 3.1 Underfill is a Decision state, a cash state, and a risk state

`unfilled_slots` originates in Decision V2, but its economic meaning appears in
Sizing and PaperState as residual cash and possibly pending transitions. The
system must distinguish “no qualified challenger” from “Open missing”, “capacity
limited”, “lot infeasible”, and “risk-held cash”. The current contract carries
some of these reasons but does not provide one portfolio-level exposure taxonomy.

### 3.2 The adapter is provenance-aware but runtime identity is incomplete

Decision score/session/hash lineage is carried through the V2 sizing adapter.
The prior runtime-lineage audit nevertheless found that the prepared/cloud
artifacts do not bind complete runtime-config SHA, runner SHA, executable paths,
or full provider configuration. Component provenance can therefore pass while
the surrounding execution environment has drifted.

### 3.3 CA-projected cash is upstream of sizing, but hash lineage can lag it

Execution projects sell proceeds and cash before sizing. The separate CA audit
found that the persisted dividend state/ledger hashes can describe the raw
pre-projection state while the allocator consumed projected state. The
Decision→Sizing contract is therefore locally valid but globally incomplete
until the consumed projected state is itself immutable and hash-bound.

### 3.4 The 10% target is not a continuing risk cap

Sizing controls entry notional. The execution config explicitly defers
post-entry weight drift/risk overlay. Thus an adapter PASS does not imply that
the resulting portfolio remains equal-risk or below a continuing concentration
limit.

## 4. Synthetic contract cases to preserve

These are deterministic cases for a future isolated test harness:

1. Six qualified targets: verify six 10%-target seats, four unfilled slots,
   residual cash, and no renormalization.
2. Ten targets with one missing raw close: verify sizing/execution fails before
   any mutation and preserves the prior state.
3. Pending BUY reversed by Decision: verify either explicit cancel/reconcile or
   fail-closed conflict, never duplicate acquisition.
4. Pending SELL reversed by Decision: verify no sell of a position that is still
   intentionally retained without a reconciliation record.
5. Same Decision plan and scores but different runtime config: verify prepared
   artifact identity rejects the mismatch once config lineage is hardened.
6. Same raw CA parent but different projected cash state: verify sizing hash
   distinguishes the consumed projection.
7. Ten individually valid names sharing one synthetic factor: verify nominal
   sizing passes but the future risk layer reports concentration rather than
   claiming diversification.

## 5. Verdict

`DECISION_SIZING_EXECUTION_LOCAL_CONTRACT = PASS BOUNDED`

`SYSTEM_LINEAGE_AND_PORTFOLIO_RISK = NOT CERTIFIED`

The core adapters have meaningful fail-closed checks. The remaining issues are
not a reason to retune Decision V2. They are integration hardening requirements:

- bind runtime/config identity into each stage artifact;
- bind projected CA/NAV state consumed by sizing;
- classify underfill/cash/pending states consistently;
- add a continuing portfolio-risk layer or explicitly document that the paper
  system is intentionally risk-overlay-free.

No retry, model change, provider call, protected read, or production mutation was
performed.

