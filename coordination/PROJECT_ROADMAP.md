# IDX-Trade — Canonical Project Roadmap

Last updated: 2026-09-09 Asia/Jakarta
Canonical location after merge: `origin/main:coordination/PROJECT_ROADMAP.md`

## Purpose

This file is the canonical **ordering of work**, not a history of every experiment. Historical conclusions live in checkpoints, closed PRs, `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`, and `archive/hygiene-v2/*` tags.

Before material work:

1. read this roadmap;
2. read `origin/main:coordination/TEAM_STATUS.md`;
3. read the newest controlling checkpoint/spec for the target lane;
4. do not reopen a frozen/closed stage merely because downstream integration is inconvenient;
5. prefer one durable branch per live lane.

---

# 1. Target end-to-end architecture

```text
PIT / execution-grade data
        ↓
V4-X1 Clean Alpha / Ranking
        ↓
Decision V2 target policy
        ↓
Baseline portfolio constraints
        ↓
Sizing V1
        ↓
Execution V1
        ↓
Corporate-action + accounting safety
        ↓
Prospective Paper Portfolio
        ↓
Whole-stack paper evaluation
        ↓
Semi-live / live integration
```

Parallel research such as financial PIT, foreign flow, price/trend state, reliability, Stockbit/broker-flow, sector PIT, intraday/path data, and other challenger signals does **not** block the baseline E2E stack unless explicitly promoted by a new frozen contract.

---

# 2. Current critical path

## Current summary

| Stage | Status | Progress / blocker | Next |
|---|---|---|---|
| 0 — Data / identity / PIT / provenance | `DONE` | The frozen baseline has the required identity, PIT, and provenance structure. | Keep optional historical improvements separate from E2E. |
| 1 — Alpha / Ranking | `DONE` | V4-X1 Clean is frozen. | Keep alpha unchanged. |
| 2 — Prospective alpha capture/scoring | `BLOCKED` | Deployment remediation is unresolved; missed sessions cannot be fabricated. | Resolve the operational deployment blocker. |
| 3 — Decision Policy | `DONE` | Decision V2 is the incumbent and research is closed. | Do not reopen tuning. |
| 4 — Prospective Decision V2 Shadow | `WAITING` | Waiting to bind fresh frozen alpha ranks to the Decision V2 shadow. | Implement the separate shadow when the E2E lane is ready. |
| 5 — Portfolio policy + Sizing V1 | `DONE` | Frozen seat-based sizing is retained with residual cash allowed. | Use the existing sizing implementation. |
| 6 — Execution V1 | `DONE` | Causal next-session execution and pending/non-fill semantics are retained. | Use the existing execution implementation. |
| 7 — Corporate Action + Accounting Safety | `DONE` | Cash-dividend foundations are complete; unsupported structural CA remains fail-closed. | Use retained safety foundations in E2E. |
| 8 — E2E Baseline Paper V1 | `ACTIVE` | The primary integration lane is wiring the frozen stack into one restart-safe flow. | Complete the next eligible genuine paper cycle. |
| 9 — Prospective Paper Evaluation | `WAITING` | Evaluation starts after E2E activation; promotion criteria must be frozen first. | Wait for E2E activation. |
| 10 — Semi-live / Live | `PARKED` | Later progression is not current work. | Revisit only after whole-stack evaluation and explicit authorization. |

## Stage 0 — Data / identity / PIT / provenance

**Status:** `DONE`

The frozen baseline has the required identity, PIT, and provenance structure.

The current clean V4-X1 lineage has enough certified identity/PIT/provenance structure for the frozen baseline. Optional historical-data improvements remain useful but must not hold E2E hostage.

Hard rules remain:

- no look-ahead;
- no outcome leakage;
- explicit source/provenance hashes where required;
- unsupported/uncertain execution semantics fail closed;
- historical source feasibility is separate from production admission.

---

## Stage 1 — Alpha / Ranking

**Status:** `DONE`

V4-X1 Clean is frozen; future alpha changes require a separately named challenger.

Current frozen alpha:

- generation: **V4-X1 Clean**;
- clean historical parent lineage: V2 `HGB_XS_MARKET`;
- clean historical OOS evidence retained;
- clean final refit retained;
- prospective scorer lineage retained.

Do not silently modify V4-X1 because downstream Decision/Paper behavior is imperfect. Any future alpha change is a separately named challenger after baseline E2E is functioning or explicit reprioritization.

---

## Stage 2 — Prospective alpha capture/scoring

**Status:** `BLOCKED`

The deployment blocker must be resolved before new prospective score sessions can
be admitted.

Required path:

```text
fresh official EOD
   ↓
frozen V4-X1 clean scorer
   ↓
immutable prospective score/rank artifact
   ↓
protected forward evaluation registry
```

The scorer/deployment lineage exists. The last scheduler migration attempt failed closed at the Windows Administrator requirement before mutation.

Next action is **operational deployment remediation only**. Do not retroactively fabricate missed prospective score sessions and do not access protected outcomes early.

The frozen 100-session forward program remains separate and outcome-blind until its opening condition is satisfied.

---

## Stage 3 — Decision Policy

**Status:** `DONE`

Decision V2 is the frozen incumbent and decision research is closed.

Incumbent: **Decision V2**.

Binding project state:

- Decision V1: superseded;
- Decision V2: incumbent;
- Decision V2.1: economically worse than V2;
- Decision V2.2: economically worse / more underfilled;
- Decision V3: structural reject;
- Decision V4 Refill Decoupling: structural reject;
- no V4.1/V4.2/V5/rescue search on the consumed 600-session development set.

Decision V4 final one-shot structural replay rejected on churn, median holding persistence, and capacity despite strong rank cleanliness. Therefore **no V4 economic comparison was authorized**.

Do not reopen Decision tuning while completing E2E.

---

## Stage 4 — Prospective Decision V2 Shadow

**Status:** `WAITING`

This stage is waiting for the prospective binding of fresh frozen alpha ranks to
the Decision V2 shadow.

Bind fresh frozen alpha ranks to Decision V2 prospectively:

```text
immutable V4-X1 score/rank(t)
        ↓
Decision V2
        ↓
BUY / HOLD / SELL intents
        ↓
immutable DecisionV2ShadowState
        ↓
target names / empty seats
```

Decision state is **not** fill state. It must remain independently observable so execution non-fills can create legitimate divergence between desired target and simulated paper holdings.

No realized outcome/PnL is needed to run this shadow.

---

## Stage 5 — Baseline portfolio policy + Sizing V1

**Status:** `DONE`

Baseline is intentionally simple:

- long-only;
- maximum 10 seats;
- approximately **10% NAV per seat/name**;
- whole-lot allocation;
- no conviction/rank weighting;
- no strategic market-timing cash overlay;
- residual cash allowed;
- new-entry cap/liquidity feasibility guards remain enforced.

If Decision V2 has only 8 qualified names, baseline exposure is approximately 80% with 20% residual cash. **Do not renormalize the 8 names to 12.5% merely to force 100% investment.**

Sizing implementation is already present in the retained downstream `integration/forward-ca-attestation-v1` lineage; no new Sizing research lane is required.

---

## Stage 6 — Execution V1

**Status:** `DONE`

Baseline includes:

- decision after EOD(t);
- sizing reference from causal t information;
- simulated raw Open(t+1) execution base;
- sell-before-buy semantics;
- paired replacement dependency;
- missing/untradable Open → non-fill/pending transition;
- fees/slippage assumptions;
- liquidity/capacity guards;
- pending buy/sell persistence;
- paper fill state separate from Decision shadow.

Execution code is already retained in `integration/forward-ca-attestation-v1`. Do not redesign execution before integrating it.

---

## Stage 7 — Corporate Action + Accounting Safety

**Status:** `DONE`

Cash-dividend foundations are complete. Unsupported structural CA transitions
remain fail-closed; initial E2E integration need not wait for every CA type.

Forward foundations retained:

- official CA evidence boundaries;
- cash-dividend entitlement/receivable/payment lifecycle;
- receivable contributes to NAV but is not spendable cash;
- idempotent payment conversion;
- append-only certified-event registry;
- persistent hash-backed state;
- restart-safe foundations.

Unsupported structural actions such as an unimplemented split/rights/bonus-share case should **block/flag the affected paper transition**, not silently approximate accounting.

Do not block initial E2E integration on implementing every possible corporate action.

---

## Stage 8 — E2E Baseline Paper V1

**Status:** `ACTIVE`

Planned single primary lane:

`integration/idx-e2e-baseline-paper-v1`

Goal: wire accepted/frozen components into one prospective, restart-safe system.

Target flow:

```text
POST_EOD(t)
  official EOD
      ↓
  V4-X1 Clean score
      ↓
  Decision V2
      ↓
  fixed 10% seat sizing
      ↓
  prepared paper orders
      ↓
  CA safety / evidence
      ↓
  immutable prepared state

NEXT SESSION
  CA recheck
      ↓
  official/certified Open inputs
      ↓
  Execution V1
      ↓
  sells → buys → fees/slippage/capacity
      ↓
  fills + pending transitions
      ↓
  dividend/CA lifecycle
      ↓
  holdings + cash + receivables + NAV
      ↓
  immutable PaperPortfolioState
```

### E2E completion definition

Baseline E2E is complete only when one fresh session can run:

`market data → alpha → Decision V2 → sizing → prepared orders → next-session simulated fill → costs → CA/accounting → holdings/cash/NAV → persisted state`

without manual JSON editing and with deterministic restart behavior.

### Mandatory pre-activation torture tests

At minimum test crashes/restarts after:

- scoring;
- Decision state commit;
- sizing/prepared-order commit;
- CA evidence capture;
- sells but before buys;
- fills but before final paper-state commit;
- dividend entitlement/receivable creation;
- dividend payment settlement.

Required invariants:

- no double trade;
- no double dividend;
- no duplicate state transition;
- no spending receivables as cash;
- no lost pending orders;
- no state-history fork;
- unresolved CA fails closed;
- protected alpha outcome vault remains separate.

Frontend work does not block this milestone.

---

## Stage 9 — Prospective Paper Evaluation

**Status:** `WAITING`

This stage is waiting for E2E activation.

Evaluate the **whole frozen stack**, not just IC.

Minimum metrics:

- NAV/return;
- drawdown;
- turnover;
- fees/slippage drag;
- fill/non-fill rate;
- liquidity/capacity incidents;
- residual cash;
- holding duration;
- concentration;
- Decision-vs-paper divergence;
- CA/accounting exceptions;
- operational restart incidents.

Promotion criteria must be frozen before using accumulated paper outcomes to justify live deployment.

---

## Stage 10 — Semi-live / Live

**Status:** `PARKED`

Semi-live/live progression is not current work and requires explicit future
authorization.

Possible progression:

```text
read-only recommendation
→ user-confirmed/manual order execution
→ semi-automatic broker integration
→ carefully bounded automation
```

Personal AKSes KSEI integration is useful for private portfolio observation/reconciliation but is not itself an order-routing mechanism.

---

# 3. Parallel retained lanes

These are retained but parked unless explicitly reprioritized:

- Financial PIT / financial representation;
- Foreign Flow representation + prospective capture;
- Price/Trend state sidecar;
- Reliability/uncertainty forward sidecar;
- price-basis/open remediation;
- TradingView final historical price-path remediation;
- Personal KSEI bounded authenticated design;
- frontend monitoring.

Always-on operational capture that is already scheduled may continue independently.

New Stockbit/broker-flow or other alpha feasibility work can be valuable later, but **baseline E2E completion outranks starting another model-search loop now**.

---

# 4. Historical closed lanes

Repository Hygiene V2 intentionally removed historical branch clutter while preserving scientific memory.

Before reopening an old idea, read:

- `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`;
- `docs/repository_hygiene/RETAINED_LINEAGE_V2.md`;
- the relevant closed PR/checkpoint;
- `archive/hygiene-v2/*` tag when exact historical code is needed.

Examples of closed/superseded families:

- old Stage3/4/4B/5 ranking experiments;
- contaminated/superseded O2 branches;
- old Probability/Expected-Payoff/Path-Risk rescue attempts;
- Decision V1/V3/V4 intermediate prereg/runner/diagnosis branches;
- rejected historical Open/intraday acquisition attempts;
- old PIT-sector/ownership/free-float/breadth research intermediates;
- obsolete CA schedule/event forensic intermediates.

A deleted branch is **not** an invitation to repeat the experiment.

---

# 5. Repository discipline after Hygiene V2

Hygiene V2 reduced the repository from 274 live remote branches to 50 before the temporary post-cleanup docs branch.

Going forward:

1. prefer one material branch per live lane;
2. use commits/checkpoints within the same branch for minor audit/remediation cycles;
3. create an independent audit branch only when independence is scientifically/destructively meaningful;
4. close final/stale PRs instead of leaving them as archives;
5. archive-tag only exact historical heads worth forensic recovery;
6. write durable negative results into tombstones;
7. do not create branches merely to save command output;
8. review hygiene again before live branches approach 100.

---

# 6. Immediate next actions

In order:

1. finish/post-merge Hygiene V2 canonical documentation;
2. resolve clean prospective scoring scheduler deployment;
3. create **one** primary `integration/idx-e2e-baseline-paper-v1` lane;
4. implement prospective Decision V2 shadow;
5. bind existing Sizing V1 + Execution V1 + CA/accounting state;
6. run restart/idempotency torture tests;
7. activate prospective paper only after those gates pass.

Do not start another Decision experiment or alpha challenger before this baseline is operational unless the user explicitly reprioritizes the project.
