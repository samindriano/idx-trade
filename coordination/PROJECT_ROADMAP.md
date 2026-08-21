# IDX-Trade — Canonical Project Roadmap

Last updated: 2026-08-21 15:23 Asia/Jakarta
Canonical location: `origin/main:coordination/PROJECT_ROADMAP.md`

## Purpose

This file is the **single canonical ordering of work** for the IDX-Trade project.

It exists because the project accumulated many valid branches/checkpoints in a non-linear chronological order: alpha research, Path Risk, Decision, Sizing, Execution, Corporate Actions, forward capture, reliability, alternative data, and frontend work were sometimes explored before neighboring layers were finished. Chronology is not the architecture.

For any new ChatGPT/Codex chat:

1. read this file first to understand the global order;
2. read `origin/main:coordination/TEAM_STATUS.md` to avoid colliding with active lanes;
3. read the newest controlling checkpoint for the current stage before changing code;
4. do not reopen a frozen earlier stage merely because a later stage is being worked on;
5. do not jump to Paper/Live simply because downstream plumbing already exists.

This roadmap controls **work ordering**, not scientific authorization. A branch-local freeze/checkpoint remains authoritative for its scientific contract.

---

# 1. Final system architecture

The intended end-to-end system is:

```text
PIT / execution-grade data
        ↓
Cross-sectional Alpha / Ranking
        ↓
Decision Policy (rank → target names)
        ↓
Portfolio / Risk Policy
        ↓
Sizing (target names → quantities)
        ↓
Execution Simulation Contract
        ↓
Corporate-Action + Accounting Safety
        ↓
Prospective Paper Portfolio
        ↓
Paper Evaluation / Promotion Gate
        ↓
Semi-Live / Live Integration
```

Three other categories run **beside** this critical path rather than redefining its order:

```text
Predictive secondary evidence:
Path Risk / Reliability / Probability / Payoff

Data research lanes:
Foreign flow / fundamentals / sector PIT / Stockbit / intraday / disclosures / etc.

Product & operations:
EOD automation / monitoring / frontend / personal KSEI integration
```

A parallel lane may improve a later version, but it must not silently become a prerequisite for the baseline system unless explicitly promoted by a new freeze.

---

# 2. Canonical critical path

## Stage 0 — Data, identity, PIT, provenance, and governance

**Goal:** make every later scientific result defensible.

Includes:

- canonical OHLCV / session calendar;
- security identity / ticker lineage;
- tradability semantics;
- PIT discipline;
- provenance / artifact hashes;
- corporate-action evidence boundaries;
- no-leakage and outcome-vault rules;
- repository coordination/governance.

**Status:** `MATURE_ENOUGH_FOR_CURRENT_V4_X1_BASELINE`, with several historical-data improvement lanes still incomplete.

This stage is never globally “finished”; new data sources can be added later. But missing optional data must not automatically block a frozen baseline that already has an accepted data contract.

---

## Stage 1 — Alpha / Ranking research and freeze

**Question:** “Which IDX stocks should rank higher today?”

Current lineage:

- V2 `HGB_XS_MARKET` — historical baseline;
- V3-B Structure-Lite — accepted historical generation before later V4 work;
- V4-X1 Clean — current frozen alpha.

Current frozen model:

- Model ID: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- Generation: `V4-X1-CLEAN`
- Fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- clean historical OOS headline IC approximately `0.098054`;
- exact 600-date historical replay already exists;
- model/science are frozen.

**Status:** `DONE / FROZEN`.

Do not reopen V4-X1 merely because downstream Decision, Risk, or Paper behavior is imperfect. Any scientific alpha change is a separately named challenger (for example V4-X2), never a silent patch.

---

## Stage 2 — Prospective Alpha validation

**Question:** “Does the frozen V4-X1 alpha survive genuinely new data?”

Includes:

- automated fresh EOD capture;
- frozen V4-X1 scoring;
- immutable forward artifacts;
- protected outcome vault;
- 100-session primary prospective evidence;
- no retrospective model changes based on the protected forward path.

**Status:** `ACTIVE / ALWAYS-ON`.

This runs in parallel with downstream engineering. It does **not** mean Paper Trading must already be active.

---

## Stage 3 — Decision Policy

**Question:** “Given the ranker, which names should the portfolio target?”

Frozen Decision V1:

- target 10 names;
- new entrants must be current Top-10;
- current Top-10 holdings are retained;
- rank >20 is mandatory exit intent;
- rank 11–20 is replaceable only when the best unheld Top-10 candidate is at least 5 ranks better;
- no fixed H5/H10 holding expiry;
- continuous shadow state, no fold reset;
- outputs are intents/target membership, not fills.

Historical-state semantics are also frozen:

- start once from empty positions / all cash on the first of the exact 600 OOS dates;
- no pre-roll;
- carry Decision shadow state across all 600 dates and all fold boundaries.

**Current work:** outcome-blind **600-OOS structural trajectory audit** of the already-frozen Decision V1.

The audit must inspect only mechanical behavior:

- churn / replacements;
- holding duration;
- Top-10 overlap;
- retained 11–20 names;
- portfolio rank quality;
- exit/replacement reasons;
- comparison with naive daily exact Top-10.

No return/PnL is required for this audit.

**Status:** `FROZEN; STRUCTURAL_AUDIT_ACTIVE`.

If the frozen rule looks mechanically undesirable, do not silently retune Top-10/Top-20/gap-5 after seeing the result. A changed rule becomes **Decision V2** with a new preregistration.

---

## Stage 4 — Prospective Decision Shadow

**Question:** “What would frozen Decision V1 decide each fresh EOD?”

After Stage 3 structural replay is reviewed, connect fresh V4-X1 scores to an immutable outcome-blind Decision shadow:

```text
fresh V4-X1 rank
      ↓
Decision V1
      ↓
BUY / HOLD / SELL intents
      ↓
10-name target shadow state
```

No lot sizes, cash, fees, fills, dividends, or NAV belong here.

The Decision shadow should accumulate prospectively alongside the frozen V4-X1 100-session program.

**Status:** `NEXT_AFTER_DECISION_TRAJECTORY_REVIEW`.

This is the next true scientific/product step before activating Paper Trading.

---

## Stage 5 — Baseline Portfolio / Risk Policy

**Question:** “What non-alpha portfolio constraints are required before quantities and execution?”

Baseline V1 should remain simple and non-predictive:

- long-only;
- target 10 names;
- no strategic market-timing cash overlay;
- no conviction weighting;
- no rank weighting for capital allocation;
- no cosmetic daily rebalance of HOLD names;
- explicit concentration / liquidity / feasibility limits only.

Several constraints are already embedded downstream:

- maximum new-entry reference weight 15% NAV;
- execution-capacity guard based on 1% prior-session regular-market value;
- residual mechanical cash allowed.

**Status:** `BASELINE_POLICY_EFFECTIVELY_FROZEN`.

A future predictive risk overlay is a challenger, not a reason to block the baseline.

---

## Stage 6 — Sizing V1

**Question:** “Given target names, how many shares/lots should the paper portfolio attempt?”

Frozen baseline:

- primary paper NAV Rp50,000,000;
- sensitivity NAVs Rp25,000,000 and Rp100,000,000;
- Rp10,000,000 feasibility-only;
- IDX lot size 100 shares;
- approximately equal 10% NAV target per new name;
- 15% NAV new-entry cap;
- deterministic equal-quota whole-lot allocation;
- no conviction/rank weighting;
- residual cash allowed.

**Status:** `DONE / FROZEN / REMEDIATED`.

This component was built earlier than necessary. Keep it parked until the project reaches Paper activation; do not keep redesigning it while Decision shadow is still the current scientific priority.

---

## Stage 7 — Execution V1

**Question:** “How are planned lots transformed into simulated fills without look-ahead?”

Frozen/remediated baseline includes:

- Decision at EOD(t);
- sizing reference raw Close(t);
- simulated execution base raw Open(t+1);
- no retroactive Open-based sizing;
- sell-before-buy semantics;
- paired replacement dependency;
- missing/untradable Open → non-fill/pending transition;
- retail fee assumptions;
- slippage assumption;
- daily turnover stamp-duty rule;
- 1% prior-session regular-market-value capacity guard;
- explicit pending buys/sells after non-fill or partial exit;
- paper state distinct from scientific Decision shadow.

**Status:** `DONE / FROZEN / REMEDIATED`, but **not an instruction to start Paper yet**.

---

## Stage 8 — Corporate Action + Accounting Safety

**Question:** “Can simulated portfolio state and NAV remain correct through real corporate actions?”

Current forward work completed materially ahead of Paper activation:

### Cash dividend

Validated authority:

- official IDX `/ListedCompany/GetAnnouncement` discovery;
- official announcement attachment(s) stored and SHA-pinned;
- `LINK_DIVIDEND` treated as lagging corroboration, not current forward authority;
- Zapi company-profile optional parity only.

Validated accounting semantics:

- cum-date EOD entitlement snapshot after same-session execution;
- ex-date creates gross dividend receivable;
- receivable contributes to NAV but is not spendable cash;
- payment converts receivable to cash once;
- ex-date sell retains prior entitlement;
- first ex-date buy gets no dividend;
- evidence and runtime state are hash-backed / restart-safe;
- certified event registry is append-only across snapshots.

Forward cash-dividend core/admission/persistence have passed focused and full CI validation.

### Other CA

- split/reverse-split: still needs supported deterministic transformation before affected Paper execution can continue;
- stock dividend/bonus shares: future;
- rights/HMETD: future / more complex;
- unknown or unsupported CA: fail closed.

**Status:** `CASH_DIVIDEND_CORE_DONE; OTHER_CA_PARTIAL; PAPER_ORCHESTRATOR_PARKED`.

Important: this lane was worked **too early chronologically**. The work is useful and retained, but it should now be parked until the Paper stage.

Historical portfolio PnL remains a separate blocked problem because historical CA continuity is not fully certified. Do not confuse that with forward Decision shadow work.

---

## Stage 9 — Prospective Paper Orchestrator

**Question:** “Can the frozen system run as a coherent simulated portfolio each session?”

Only activate after the project has:

1. reviewed the Decision V1 structural trajectory;
2. deployed Prospective Decision Shadow;
3. confirmed the baseline Decision/Sizing/Execution contracts remain the desired V1 stack;
4. retained fail-closed CA/accounting safety.

Then bind:

```text
POST_EOD
fresh score
→ Decision V1
→ sizing
→ CA evidence capture
→ immutable prepared state

PREOPEN / OPEN
→ fresh CA verification
→ Open inputs
→ simulated fills
→ pending transitions
→ dividend / CA lifecycle
→ immutable next paper state
→ NAV / holdings / cash / exceptions
```

Required before authorization:

- restart/idempotency torture tests;
- exactly-once transition semantics;
- no double dividend booking;
- no state mutation on unresolved CA;
- complete manifest/hash chain;
- clear separation from protected alpha outcome vault.

**Status:** `PARKED / NOT_YET_AUTHORIZED`.

Do not resume merely because much of its plumbing already exists.

---

## Stage 10 — Prospective Paper Evaluation

**Question:** “Does the complete frozen stack behave acceptably after realistic costs and operational constraints?”

Evaluate only after Paper is genuinely prospective and sufficiently accumulated.

Metrics should include, at minimum:

- NAV / return;
- drawdown;
- turnover;
- fees/slippage drag;
- fill/non-fill rate;
- liquidity/capacity incidents;
- residual cash;
- holding duration;
- concentration;
- decision-to-paper divergence;
- CA/accounting exceptions.

Paper evidence evaluates the **whole stack**, not only alpha quality.

**Status:** `FUTURE`.

---

## Stage 11 — Semi-Live / Live integration

Only after the paper stack is accepted.

Possible progression:

```text
read-only recommendation
→ user-confirmed/manual orders
→ semi-automatic broker integration
→ carefully bounded live automation
```

Personal AKSes KSEI integration can be used for authenticated portfolio observation/reconciliation, but it is not itself an order-routing mechanism.

Live capital deployment is a separate authorization from Paper success.

**Status:** `FUTURE`.

---

# 3. Predictive secondary-evidence lanes

These lanes are scientifically interesting but **not mandatory blockers for the baseline V1 stack**.

## A. Path Risk

Original architectural intent placed Path Risk after Alpha and before Decision as secondary predictive evidence about adverse price path.

Legacy intent included causal H10 path targets such as adverse excursion / MAE-like behavior, time-to-worst, and recovery characteristics.

However:

- Path Risk V1/V2 failed / did not qualify;
- historical intraday coverage/admission was inadequate;
- the lane is `WAITING` for richer intraday data and a genuinely new preregistered hypothesis family;
- do not retune/rescue V1/V2;
- do not silently create Path Risk V3 merely to make it pass.

**Canonical consequence:** Path Risk is **not a current blocker for Decision V1, Sizing V1, or baseline Paper preparation**.

When sufficient new data exists, Path Risk V3 may return as a separately evaluated secondary-risk model or future overlay/challenger.

**Status:** `WAITING / PARALLEL`.

## B. Reliability / Uncertainty

Reliability research can estimate when model scores are more/less trustworthy. It is useful for diagnostics and possible future selective exposure, but baseline Decision V1 does not require it.

No reliability output may silently alter frozen V4-X1 or Decision V1. A risk/exposure use requires a separately named overlay/version.

**Status:** `PARALLEL / CHALLENGER`.

## C. Probability / Expected Payoff

Prior probability/payoff lanes did not become required production components.

Future versions may use richer prospective outcomes to estimate calibration or expected payoff, but they are not prerequisites for the current baseline.

**Status:** `DEFERRED / PARALLEL`.

---

# 4. Parallel data/research lanes

These can proceed without changing the critical path unless a result is separately admitted.

Examples:

- PIT sector/industry history;
- fundamentals / financial PIT;
- foreign flow;
- Stockbit broker flow / Stream prospective archive;
- corporate/event data expansion;
- intraday/path data;
- market/index/breadth history;
- alternative alpha sources;
- Auction Market Theory / effort-vs-result hypotheses;
- historical OPEN improvements.

Rules:

1. collecting data does not authorize model use;
2. source feasibility is separate from scientific promotion;
3. rejected historical sources remain rejected unless a new preregistered audit justifies reopening;
4. a new signal idea must enter as a challenger, never mutate frozen V4-X1;
5. do not let optional backfills hold the entire project hostage if the baseline path is already defensible without them.

---

# 5. Always-on product / operations lanes

These are supportive and may run in parallel.

## EOD automation

Keep fresh V4-X1 data capture/scoring healthy. Operational repair is allowed without changing frozen science.

## Frontend / Monitoring

The frontend is a viewer/operations surface, not the scientific authority.

It should eventually expose separately:

- current V4-X1 rank/score;
- Decision V1 target and BUY/HOLD/SELL reasons;
- prospective accumulation progress;
- historical model comparisons (including V2 `HGB XS + Market` where useful);
- paper holdings/NAV only after Paper is activated;
- execution/CA exceptions separately from protected alpha outcomes.

Do not remove useful prior-model/hover/score visibility merely to simplify the UI.

## Personal KSEI

Personal AKSes KSEI integration is an authenticated private portfolio-observation/reconciliation lane. Keep credentials out of repo and browser-side code. It is separate from public Ownership/KSEI market data and separate from broker order routing.

---

# 6. Current project position — 2026-08-21

```text
Stage 0  Data / PIT / Governance                MATURE ENOUGH; parallel gaps remain
Stage 1  V4-X1 Alpha                           DONE / FROZEN
Stage 2  Prospective Alpha 100-session          ACTIVE / ALWAYS-ON
Stage 3  Decision V1                            FROZEN; 600-OOS structural audit ACTIVE
Stage 4  Prospective Decision Shadow            NEXT
Stage 5  Baseline Portfolio/Risk Policy         EFFECTIVELY FROZEN
Stage 6  Sizing V1                              DONE / FROZEN / REMEDIATED (parked)
Stage 7  Execution V1                           DONE / FROZEN / REMEDIATED (parked)
Stage 8  Forward CA / Dividend Accounting       CASH DIVIDEND CORE DONE (parked)
Stage 9  Paper Orchestrator                     PARKED / NOT AUTHORIZED
Stage 10 Paper Evaluation                       FUTURE
Stage 11 Semi-Live / Live                       FUTURE

Parallel: Path Risk V1/V2                       FAILED / WAITING; V3 not authorized
Parallel: Reliability / Probability / Payoff    CHALLENGER / DEFERRED
Parallel: Alternative data & source research    CONTINUOUS, separately gated
Parallel: Frontend / Monitoring                 SUPPORTING / CONTINUOUS
```

The fact that Stages 6–8 already contain significant code **does not move the project to Stage 9**. They were partially built ahead of schedule.

The current scientific priority is Stage 3 → Stage 4.

---

# 7. Immediate ordered queue

Unless the user explicitly changes project direction, work in this order:

## NOW — Q1. Finish Decision V1 structural trajectory audit

Run the preregistered outcome-blind replay on exact 600 OOS scores and review:

- turnover vs daily Top-10;
- holding duration;
- rank quality;
- Top-10 overlap;
- 11–20 buffer usage;
- hard-exit vs rank-gap replacement counts;
- fold-block continuity.

Do not load historical PnL/returns.

## NEXT — Q2. Freeze/accept Decision V1 mechanical behavior

If acceptable, record Decision V1 as mechanically reviewed without changing parameters.

If unacceptable, stop and explicitly open **Decision V2**. Never silently alter Decision V1.

## NEXT — Q3. Deploy Prospective Decision Shadow

Bind fresh V4-X1 score artifacts to Decision V1 and persist target/intent state each EOD.

This should be outcome-blind and independent from paper execution.

## THEN — Q4. Let Alpha + Decision prospective evidence accumulate

Keep the 100-session V4-X1 program intact. Decision shadows accumulate alongside it.

Do not accelerate to Paper merely to generate performance numbers sooner.

## THEN — Q5. Reconfirm downstream V1 stack before Paper activation

Review, do not automatically redesign:

- baseline risk policy;
- Sizing V1;
- Execution V1;
- Forward CA/dividend safety.

Only fix objective engineering defects. Any policy change must be versioned.

## THEN — Q6. Complete Paper Orchestrator + restart/idempotency audit

Resume the parked POST_EOD → PREOPEN/Open orchestrator and exactly-once state transition tests.

## THEN — Q7. Start Prospective Paper

Only after explicit authorization.

## THEN — Q8. Evaluate Paper and decide promotion

After sufficient prospective paper evidence, decide whether to:

- keep baseline;
- create Decision/Risk/Sizing/Execution challengers;
- incorporate a validated future Path Risk/Reliability overlay;
- move toward semi-live execution.

---

# 8. Historical PnL policy

Historical portfolio PnL is **not the current critical-path requirement**.

It remains blocked/untrusted until historical corporate-action quantity/cash continuity is sufficiently defensible. Do not spend unlimited project time forcing historical CA to 100% merely to unlock a retrospective portfolio curve.

Allowed historical work now:

- frozen score/rank analysis;
- Decision V1 structural trajectory replay;
- outcome-blind mechanical diagnostics that do not require cash/share continuity.

Prospective Paper later provides the cleanest executable portfolio evidence under the forward CA/accounting framework.

---

# 9. Versioning rule

Once a layer is frozen, later dissatisfaction does not mutate it silently.

```text
Alpha V4-X1 bad downstream behavior  → investigate; alpha change = V4-X2 challenger
Decision V1 bad mechanics            → Decision V2
Risk baseline change                 → Risk Policy V2 / named overlay
Sizing V1 policy change              → Sizing V2
Execution V1 policy change           → Execution V2
CA/accounting extension              → additive versioned CA engine
```

Engineering bug fixes that preserve the frozen scientific/economic contract may be remediated in place only with explicit regression evidence and documentation.

---

# 10. New-chat bootstrap text

When starting a fresh IDX-Trade chat, the minimal instruction is:

> Read `origin/main:coordination/PROJECT_ROADMAP.md` first, then the latest `origin/main:coordination/TEAM_STATUS.md`, then the newest checkpoint for the current active stage. Follow the canonical critical path; do not infer work order from branch chronology. Current priority is whatever the Roadmap marks `NOW/NEXT`, while always-on prospective capture continues independently.

This should be enough for a new chat to recover the global project order before diving into branch-specific details.
