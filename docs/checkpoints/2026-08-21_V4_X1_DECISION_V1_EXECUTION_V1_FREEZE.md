# V4-X1 Decision V1 — Execution V1 Freeze and Forward-Paper Core

Date: 2026-08-21
Branch: `research/idx-v4-x1-decision-v1`

## Verdict

`EXECUTION_V1_FORWARD_PAPER_CORE_IMPLEMENTED_HISTORICAL_PNL_BLOCKED_CA_CONTINUITY`

Execution V1 is frozen as the first paper-execution layer downstream of frozen V4-X1 Alpha, Decision V1, and Sizing V1.

## Frozen execution semantics

### Timing

- Decision: after official EOD on session `t`.
- Sizing reference: canonical raw `Close(t)`.
- Earliest execution session: next official session `t+1`.
- Fill base: canonical raw `Open(t+1)`.
- Lots are determined from information known at/after EOD(t); realized Open(t+1) is never used to size lots retroactively.

### Trade ordering

- Full sell intents are processed before buys.
- Projected sell proceeds for sizing use raw `Close(t)` minus the primary slippage assumption and sell fee.
- For paper execution, successfully realized sell proceeds are available as buying power for same-session buys.
- A replacement buy whose paired sell is unavailable is blocked.
- A sell intent for an actual zero position is a resolved no-op.

### Costs

Primary retail paper assumptions:

- buy transaction fee: `15 bps`
- sell transaction fee: `25 bps`
- slippage: `10 bps` per side
- slippage sensitivities reserved for later reporting: `0 bps` and `25 bps` per side
- account-level stamp duty: `Rp10,000` when daily gross turnover exceeds `Rp10,000,000`

Fee reference checked on 2026-08-21:

- Stockbit Sekuritas current published fee: 0.15% buy / 0.25% sell, article updated 2026-08-05.
- Ajaib current published fee: 0.1513% buy / 0.2513% sell for the lowest retail transaction tier.

The V1 primary 15/25 bps assumption is therefore a representative retail baseline, not a zero-cost assumption.

### Buy cash-fit rule

Sizing V1 quantities are an upper bound.

At Open(t+1):

- never increase above Sizing V1 planned lots;
- after realized sells, divide actual available buy cash equally across eligible buy names;
- each buy budget is capped by its original Sizing V1 equal quota;
- fee and slippage must fit inside that budget;
- actual filled entry gross notional must remain within the 15% EOD(t) NAV cap;
- any gap-up / cash pressure may only reduce lots.

This preserves Sizing V1's rank-agnostic equal-quota design and prevents hidden execution-time rank weighting.

### Availability / dependency

- missing or invalid raw Open(t+1) => no fill;
- non-tradable ticker => no fill;
- unavailable sell => paired replacement buy blocked;
- operational non-fill marks the resulting paper state `reconciliation_required=true`;
- no subsequent automatic session may prepare from a paper state carrying unresolved reconciliation.

### State integrity

- paper state is distinct from Decision V1 shadow state;
- positions must be positive whole lots;
- state identity is SHA-pinned into the order plan;
- execution against a different cash/position state fails closed;
- execution session must be strictly after the decision session.

## Corporate-action gate

Canonical data intentionally preserves raw OHLC for execution and keeps adjusted-close fields separate.

Historical V4 corporate-action continuity is not yet certified. The latest accepted continuity evidence still reports:

- `corporate_action_continuity_certified=false`
- `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

Therefore:

- `corporate_action_continuity_ok=false` aborts the execution session before mutation;
- historical portfolio PnL remains unauthorized;
- no stock split, dividend, conversion, rights, or other event is guessed from price jumps;
- historical PnL may reopen only after a separately accepted quantity/cash continuity source or equivalent defensible corporate-action accounting path exists.

Forward paper can run only on sessions whose involved holdings/trades pass the corporate-action continuity gate.

## Validation

Pre-publish local validation:

- focused execution tests: `13 passed`
- integrated randomized execution cases: `20,000 passed`
- `py_compile`: PASS

Covered invariants include:

- Close(t) sizing / Open(t+1) fill separation;
- no buy quantity increase after sizing;
- gap-up lot reduction;
- actual 15% entry cap;
- sell-before-buy replacement;
- paired-sell dependency;
- missing-open no-fill;
- CA pre-mutation abort;
- state-hash mismatch rejection;
- nonnegative cash;
- whole-lot final positions;
- fee/slippage direction;
- stamp-duty accounting;
- reconciliation lock after operational failure.

## Next action

Do **not** run historical portfolio PnL yet.

Next work is forward-paper orchestration:

1. connect fresh V4-X1 score / Decision V1 output to immutable paper state;
2. load raw Close(t) after EOD for prepare;
3. on the next fresh official session, load raw Open(t+1) and tradability;
4. require CA continuity pass;
5. persist order plan, fills, and state transition immutably;
6. expose paper NAV / holdings / residual cash / execution exceptions separately from the protected 100-session alpha outcome vault.

Historical PnL remains blocked pending corporate-action continuity.
