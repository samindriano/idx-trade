# IDX-Trade — Decision V2 State and Regime Matrix V1

Date: 2026-09-20 (Asia/Jakarta)

Status: `SYNTHETIC STATE-MACHINE PASS / EXPOSURE TRANSITION REQUIRES EXPLICIT ACCOUNTING`

This is an outcome-blind synthetic state test of the pinned Decision V2 logic.
It does not tune parameters or inspect protected returns.

## 1. Setup

Runtime snapshot: `045e25a19d9f71170d2c863e768102937e59ad73`.

Profile:

- target maximum: 10;
- strong zone: ranks 1–10;
- retention zone: ranks 1–20;
- soft replacement gap: 5;
- previous-rank confirmation ceiling: 20.

Synthetic sequence:

1. Day 1: `A1..A10` bootstrap Top-10.
2. Day 2: `A10` moves to rank 21; fresh challenger `Z` is rank 22.
3. Day 3: `A10` remains rank 21; `Z` jumps to rank 1.
4. Day 4: `Z` remains rank 1.

The Decision shadow state was advanced from each returned plan, so this is a
multi-session state transition rather than four independent calls.

## 2. Observed plans

```text
2026-01-02 bootstrap=True  target_n=10 buys=A1..A10
             sells=[] unfilled=0 capacity=FULL

2026-01-03 bootstrap=False target_n=10 buys=[] sells=[]
             unfilled=0 capacity=FULL

2026-01-04 bootstrap=False target_n=9 buys=[]
             sells=[A10:CONFIRMED_EXIT_GT20_2]
             unfilled=1 capacity=UNFILLED_NO_QUALIFIED_CHALLENGER

2026-01-05 bootstrap=False target_n=10
             buys=[Z:QUALIFIED_VACANCY_FILL] sells=[]
             unfilled=0 capacity=FULL
```

## 3. What this confirms

### 3.1 Fresh extreme rank is not an immediate buy

`Z` was rank 1 on Day 3 but had been rank 22 on Day 2. It was not bought on
Day 3. The state machine requires prior confirmation inside the previous Top-20
boundary.

### 3.2 Confirmed exit can create a real underfill

`A10` needed two consecutive observations outside rank 20 before exit. When it
exited on Day 3, `Z` was still unqualified, so the target fell to nine names.
This is explicit `UNFILLED_NO_QUALIFIED_CHALLENGER`, not an accidental missing
row.

### 3.3 Persistence delay is asymmetric with vacancy filling

The fresh challenger is delayed one session, while the confirmed incumbent
exits on the second bad observation. This can create a temporary cash/exposure
state even when a visually attractive rank-1 name exists.

### 3.4 The transition is deterministic under the declared state contract

The state carries the previous session date and target positions. Existing
validation rejects stale state, duplicate ranks, non-contiguous ranks, and
Decision state/previous-score mismatch.

## 4. System interaction

At Day 3, downstream Sizing/Execution should observe:

- one sell intent;
- zero buy intents;
- nine target positions;
- one unfilled slot;
- residual cash rather than upward renormalization.

That means a regime/state transition is also an accounting and risk transition.
The system should preserve why the tenth seat is empty: it is a persistence
qualification state, not Open unavailability, capacity failure, or a risk hold.

## 5. Boundaries and next synthetic cases

This matrix does not prove predictive benefit or economic superiority. It does
not test actual prices, fills, CA projection, or external universe authority.

The next useful state-only cases are:

- universe disappearance and immediate exit;
- pending BUY reversal after an underfill;
- pending SELL reversal after a confirmed exit;
- ten correlated names with full nominal slots;
- a fresh challenger becoming qualified exactly as capacity blocks its buy;
- restart between Decision shadow update and PaperState persistence.

Verdict:

`DECISION_STATE_RULES_REPRODUCIBLE / EXPOSURE-STATE LINEAGE MUST BE PRESERVED`

