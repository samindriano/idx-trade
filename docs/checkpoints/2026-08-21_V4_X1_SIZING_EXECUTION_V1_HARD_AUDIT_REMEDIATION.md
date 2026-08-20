# V4-X1 Decision V1 — Sizing / Execution V1 Hard-Audit Remediation

Date: 2026-08-21  
Branch: `research/idx-v4-x1-decision-v1`

## Verdict

`SIZING_EXECUTION_V1_HARD_AUDIT_REMEDIATED_PRE_FIRST_PAPER_OUTCOME_FORWARD_PAPER_BLOCKED_UNTIL_VERIFIED_CA_ATTESTATION`

The original Sizing V1 and Execution V1 freeze checkpoints are retained as historical evidence but are superseded by this remediation **before the first executable-paper outcome is consumed**.

No V4-X1 alpha rule, model, feature, score formula, prospective counter, Decision V1 membership rule, rank-gap rule, hard-exit rule, or protected outcome was changed or accessed.

Historical portfolio PnL remains unauthorized.

## Why remediation was required

A hostile re-audit found downstream implementation risks that could bias or corrupt paper evidence even while the original focused tests passed.

### P0 — unverified corporate-action boolean

The original execution API accepted a caller-supplied `corporate_action_continuity_ok: bool`. A raw boolean had no evidence identity and could not prove split/dividend/rights/conversion continuity.

Remediation:

- raw CA booleans are rejected;
- Execution V1 requires `VerifiedCorporateActionAttestation`;
- the attestation is file-backed and SHA-verified;
- V1 admits only `NO_RELEVANT_EVENTS` across every involved ticker for the exact decision-to-execution session interval;
- any relevant or unresolved event fails closed to a separate CA reconciliation path;
- no quantity/cash transformation is guessed from price jumps.

### P0 — shadow / executable-paper divergence after zero or unavailable fills

The original implementation could produce zero executable quantity while Decision V1 had already moved its scientific shadow target. On the next date the Decision layer could emit HOLD, leaving the paper portfolio permanently missing the intended name.

Remediation:

- paper state now persists explicit `pending_buys` and `pending_sells`;
- zero-lot, missing-Open, capacity-constrained entry, unavailable exit, and blocked paired replacement become pending transitions;
- pending transitions retry only while still consistent with the latest Decision V1 target;
- if the shadow/paper mismatch is not explained by a current intent or an explicit pending transition, execution fails closed with `UNEXPLAINED_SHADOW_PAPER_DIVERGENCE`;
- Decision V1 shadow state is never rewritten to auto-heal paper non-fills.

### P0 — raw price / session / tradability inputs lacked evidence boundary

The original execution API accepted plain price mappings and a plain tradability set.

Remediation:

- `VerifiedEODExecutionInputs` verifies file-backed EOD artifacts;
- raw Close(t) must agree exactly between the session OHLCV sibling artifact and the canonical model-input artifact;
- artifact SHA identities are carried downstream;
- the official calendar artifact is SHA-pinned;
- execution date is derived as the **immediate next official session**, not an arbitrary later date;
- `VerifiedOpenExecutionInputs` verifies exact Open(t+1) session identity and file SHA;
- positive observed Open rows define paper entry/exit availability; there is no caller-supplied free-form tradability set.

### P1 — artificial cash drag from independent per-entry execution budgets

The original Open execution divided actual cash into independent equal slices and floored each name separately. In a deterministic Rp50m bootstrap example with ten equal Rp1,000 prices, Sizing V1 planned 50 lots/name but execution reduced all ten to 49 lots, leaving roughly 1.6% NAV as mechanical cash even though a materially closer joint allocation existed.

Remediation:

- actual Open allocation is joint across all eligible entrants;
- Sizing V1 lots remain strict upper bounds;
- target remains equal-notional, not rank-weighted;
- fee, slippage, stamp duty, 15% entry cap, cash, and capacity are evaluated jointly;
- deterministic regression now produces eight names at 50 lots and two names at 49 lots in the canonical Rp50m / Rp1,000 example, with residual cash below Rp100k.

A second hostile edge case found that a local `floor-1/floor/ceil` enumeration could still collapse an entire low-price batch when fees required reducing more than one lot per name. That implementation was replaced before freeze by a **fee-aware joint equal-target water-fill**:

1. initialize each entrant at a fee-aware equal-cash floor;
2. if stamp duty makes the batch infeasible, remove the least damaging lots rather than zeroing the batch;
3. spend residual cash one lot at a time on the most under-target entrant only while the addition moves that name closer to the equal target;
4. enforce all upper/capacity/cash constraints on every addition.

A dedicated low-price regression verifies that fee pressure does not zero an otherwise feasible ten-name batch.

### P1 — arbitrary ticker-first lot tie

The original Sizing V1 used ticker ASC for exact allocation ties.

Remediation:

- economic objective remains equal-weight / equal-target;
- rank is **not** a sizing weight or conviction multiplier;
- after an exact economic allocation tie, better Decision rank is the first deterministic tie-break;
- ticker ASC is only the final identity tie-break.

### P1 — no causal execution-capacity guard

The original simulated full Open fill had no liquidity/capacity ceiling.

Remediation:

- a new BUY may simulate at most `1%` of verified prior-session regular-market value (`regular_market_value(t)`);
- this is causal EOD information, not Open(t+1) look-ahead;
- capacity can reduce an entry to zero, in which case it becomes a pending paper transition;
- the simulator explicitly labels fills as paper-simulated Open-plus-slippage fills, not broker-fill claims.

This is a conservative V1 feasibility guard, not a calibrated market-impact model. Existing intraday capture infrastructure may support a separately preregistered future calibration; no duplicate capture system is authorized here.

## Frozen semantics preserved

The remediation does **not** change these accepted design choices:

- primary paper NAV: Rp50m;
- sensitivity NAVs: Rp25m / Rp100m;
- Rp10m remains feasibility-only;
- lot size: 100 shares;
- equal-ish target: approximately 10% NAV per new Decision name;
- max new-entry weight: 15% NAV;
- no rank-weighted or conviction-weighted sizing;
- no daily cosmetic HOLD rebalance;
- no strategic market-timing cash overlay;
- residual mechanical cash is allowed;
- Close(t) is the sizing reference and Open(t+1) is the simulated execution base;
- sell intents resolve before paired buys;
- primary costs remain 15 bps buy fee, 25 bps sell fee, 10 bps/side slippage, and Rp10k account-level stamp duty above Rp10m daily gross turnover;
- post-entry weight drift is not cosmetically trimmed; portfolio concentration / market-risk overlays remain future separate layers.

## Validation evidence

Pre-publication local remediation harness using the same remediated modules:

- core hostile-audit focused suite: `11 / 11 PASS`;
- verifier-specific regression suite added: calendar identity, EOD Close provenance mismatch, Open exact date/availability, valid CA no-event attestation, relevant-event rejection, incomplete coverage rejection, source-SHA mismatch rejection;
- combined final local focused suites after the low-price allocator remediation: `19 / 19 PASS`;
- `py_compile`: PASS for sizing, execution contract, execution allocator, execution verifier, and execution orchestrator modules;
- randomized integrated stress: `20,000 / 20,000 PASS` across NAV Rp25m/Rp50m/Rp100m, 1–10 names, price range including low nominal prices, ±20% Open gaps, and broad reference-day liquidity values.

Stress invariants checked:

- non-negative cash;
- whole-lot positive holdings only;
- actual BUY quantity never exceeds Sizing V1 planned quantity;
- actual new-entry gross notional never exceeds 15% EOD NAV;
- actual new-entry gross notional never exceeds 1% verified reference-day regular-market value;
- missing target names exactly equal persisted pending BUY transitions;
- extra actual names exactly equal persisted pending SELL transitions;
- no unexplained scientific-shadow / executable-paper divergence.

Repository regression files include dedicated tests for the original cash-drag failure, pending retry semantics, paired sell dependency, CA boolean rejection, capacity guard, low-price fee pressure, forged DecisionPlan rejection, official-session / price provenance, and CA evidence integrity.

## Remaining intentional blockers

### Historical PnL

Still blocked. The accepted repository evidence remains `corporate_action_continuity_certified=false`; this remediation does not reinterpret or bypass that blocker.

### Forward executable paper

The core engine is remediated, but an actual forward paper execution must not run until the sidecar can produce a file-backed `v4_x1_paper_ca_attestation_v1` covering every involved ticker and exact decision-to-execution interval. V1 only accepts an attested no-relevant-event interval. A real corporate action requires a separately reviewed quantity/cash transformation contract before execution may continue.

### Market-risk / concentration overlays

Still out of scope. No strategic cash timing, dynamic conviction sizing, or automatic trim of post-entry winners is introduced by this remediation.

## Final authorization state

- V4-X1 alpha: unchanged / frozen.
- Decision V1: unchanged / frozen.
- Sizing V1: remediated and re-frozen pre-first-paper-outcome.
- Execution V1: remediated and re-frozen pre-first-paper-outcome.
- Historical portfolio PnL: **NOT AUTHORIZED**.
- Forward paper orchestration: may proceed only up to the verified-CA evidence gate; no fill/state mutation without a valid attestation.
