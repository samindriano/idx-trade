# IDX-Trade Positive Partial-Buy Trigger Matrix V1

Date: 2026-09-20
Audited runtime: detached `runtime/idx-e2e-baseline-paper-v1` at `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
Documentation lane: isolated `codex/alpha-available-data-20260919`
Status: **FAIL — POSITIVE PARTIAL BUY IS A GENERAL UNDERDELIVERY STATE**

## Scope and boundary

This is an outcome-blind synthetic probe of the retained V4-X1 paper runtime. It does not use protected predictive outcomes, production state, canonical data, cloud/capture/telemetry/scheduler state, or external acquisition. No source or runtime code was changed.

The prior audit established one positive partial buy after a price/capacity mismatch. This matrix tests whether the same semantic loss appears under independent execution constraints and paired replacement sequencing.

## Reproduction matrix

All rows used a valid verified EOD/Open/CA wrapper and a target containing the buy ticker. `pending_buys` was empty after execution in every row. The next-session synthetic Decision was built with the partially held ticker already in `current` and `target`; `effective_buy_intents` was empty in every row.

| Scenario | Planned buy | Filled buy | Execution status | Trigger | Pending after execution | Next-session retry |
|---|---:|---:|---|---|---|---|
| Reference-day capacity plus Open price change | 5,000 | 1,200 | `SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED` | 1% reference-day capacity binds at Open | empty | absent |
| Buy-fee cash boundary | 1,000 | 900 | `SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED` | sizing uses gross reference notional; allocator reserves buy fee | empty | absent |
| Stamp-threshold boundary | 10,000 | 9,900 | `SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED` | allocator rejects the 100th lot because fee plus the IDR 10,000 stamp would exceed cash | empty | absent |
| Paired replacement | 5,000 | 1,200 | `SIMULATED_FILLED_JOINT_LOT_CAPACITY_GUARDED` | old sell completes; replacement buy is capacity-limited | empty | absent |

The stamp row is intentionally precise: the executed 9,900-share batch stayed below the stamp threshold, so `stamp_duty_idr` was zero. The defect is still relevant because the stamp-inclusive candidate was removed by the allocator without creating a residual obligation.

The paired-replacement row had an exact 5,000-share `AAA` sell fill, followed by a 1,200-share `BBB` buy fill. Both pending collections were empty and the state held only `BBB: 1,200`.

## Multi-session and portfolio-state observations

The following values came from a synthetic cold reconstruction of each
`PaperPortfolioState`; the reconstructed state hash equaled the live result
hash in all four rows. The mark-to-market NAV uses the synthetic next-session
close and is not protected predictive evidence.

| Scenario | Completion ratio | Target seats / actual seats | Target membership | Pending buys | Cold-reload hash | Next retry | Mark NAV after next close |
|---|---:|---:|---|---:|---|---|---:|
| Capacity | 24% | 1 / 1 | equal | 0 | equal | absent | IDR 49,993,996.40 |
| Fee boundary | 90% | 2 / 2 | equal | 0 | equal | absent | IDR 9,997,748.65 |
| Stamp boundary | 99% | 2 / 2 | equal | 0 | equal | absent | IDR 100,005,235.15 |
| Paired replacement | 24% | 1 / 1 | equal | 0 | equal | absent | IDR 49,976,508.90 |

This proves a stronger blast-radius statement: seat-count, ticker-membership,
hash-equality, and cash/NAV arithmetic can all look internally valid while the
planned quantity is not delivered. Gross turnover also reflects only the
actual fill; it does not retain a residual obligation that a later metric or
session can discover.

## Decision V2 shadow and ten-seat capacity interaction

A separate Decision V2 synthetic run used ten target tickers with equal planned
5,000-share entries. `T01` had a 1% reference-day capacity that allowed only
2,400 shares; the other nine names filled 5,000 shares each. The resulting
paper state therefore had ten actual seats and no pending buy.

On the next session, a Decision V2 plan built from those actual positions
reported `capacity_state=FULL`, `unfilled_slots=0`, zero effective buy intents,
and zero sizing entries. The shadow layer correctly matched its own ticker
membership invariant, but it had no representation of the missing 2,600
`T01` shares. This extends the failure into the Decision V2 shadow and seat-cap
boundary: a full seat count is not equivalent to a fulfilled target quantity.

## Runtime snapshot restart observation

The underfilled `AAA: 1,200` state was written through the existing dividend-aware
runtime snapshot writer into a temporary directory and loaded back. The loaded
position remained `AAA: 1,200`, pending buys remained empty, and the loaded
runtime hash equaled a fresh recomputation. This is faithful persistence, not
recovery: the snapshot layer preserves the semantically incomplete state
because no residual obligation exists in the state schema.

## Why this is one contract failure

The trigger varies, but the state transition is identical:

1. Sizing emits a positive planned quantity.
2. Open allocation emits a smaller positive lot quantity.
3. Execution records the smaller quantity as a successful fill.
4. Only zero-lot buys are inserted into `pending_buys`.
5. The target/position invariant compares ticker membership, not required quantity.
6. The next Decision sees the ticker in both `current` and `target`, so it emits no new buy intent.

This is therefore a **CROSS-COMPONENT DEFECT**, with **ECONOMIC / EXECUTION RISK** and an **OBSERVABILITY GAP**. It is not limited to a single price-gap path, and it survives paired replacement sequencing as long as the old sell resolves.

## Exact implementation evidence

- Sizing computes planned shares from EOD reference price and whole lots in `src/idx_trade/v4_x1_sizing_v1.py:236-257`.
- Open allocation may return fewer lots because of capacity, cash, fees, stamp, or Open price in `src/idx_trade/v4_x1_execution_v1_allocator.py:33-146`.
- Execution creates pending only when `shares <= 0`; positive underfill is recorded as a normal fill in `src/idx_trade/v4_x1_execution_v1.py:365-404`.
- The final transition check compares missing/extra ticker sets and does not compare planned versus filled quantity in `src/idx_trade/v4_x1_execution_v1.py:417-425`.
- A retry is synthesized only for a pending buy whose ticker is absent from positions in `src/idx_trade/v4_x1_execution_v1.py:93-108`.

Audited source hashes:

| Artifact | SHA-256 |
|---|---|
| `src/idx_trade/v4_x1_sizing_v1.py` | `A49C828DCA4E68E18A2260F047CF2BD7647C8FDFBDAB6D59707A014281AD25A9` |
| `src/idx_trade/v4_x1_execution_v1_allocator.py` | `6E315B47B6C87D2D9A921BF1C5142FE3F2E685EE443A20F43171317BEDCA0481` |
| `src/idx_trade/v4_x1_execution_v1.py` | `010567BFD6C9156D5C088A96ECB251ED2074C461CC5C326FCF9C98789AB76FC9` |
| `tests/test_v4_x1_execution_v1.py` | `ABFD3F2C73155C90E1E5B23ED8FE662AF2DA440C0A1958AF90F1CF3DBF6F66E1` |

## Blast radius

- **Origin:** planned EOD quantity and executable Open quantity are different contracts.
- **Trigger:** any positive lot reduction after sizing, including capacity, fee, stamp-boundary, or replacement execution.
- **Affected state:** actual position contains fewer shares than the plan requested, with no residual obligation.
- **Downstream consumers:** next Decision, restart/reload, turnover/fill metrics, exposure, concentration, NAV interpretation, and any evaluator reading position membership.
- **Failure mode:** semantically fail-open and economically underexposed; it does not create an overspend in these probes.
- **Detection:** current state hash remains internally consistent but does not encode planned/filled/remaining quantity, so hash/config identity cannot detect the loss.
- **Cross-session propagation:** the next-session membership check suppresses retry; a reload of this state would preserve the underfilled position rather than recover the residual.

## Validation

- Current retained runtime focused run: `15 passed` for `tests/test_v4_x1_execution_v1.py tests/test_v4_x1_sizing_v1.py`.
- Prior retained execution/sizing/E2E baseline recorded in `2026-09-20_IDX_SIZING_EXECUTION_PARTIAL_BUY_AUDIT_V1.md`: `59 passed`.
- New matrix probes: four scenarios, four positive underfills, four empty pending-buy states, four absent next-session retry intents.

## Hardening direction — not applied

The evidence justifies a quantity-aware obligation model, not a local status-string patch:

- carry planned, filled, and remaining quantity through sizing, execution, state, and replay artifacts;
- create or update a residual pending buy whenever `0 < filled_shares < planned_shares`;
- make the target invariant quantity-aware;
- let next-session retry consume the residual obligation without changing target membership;
- include the obligation in state hashes and restart/replay equality;
- add capacity, fee, stamp-boundary, paired replacement, and multi-session tests.

No remediation was applied in this lane.

## No-retry boundary

Do not rerun the same four trigger shapes as if they were independent bugs. Reopen this finding only with evidence about a different state owner, a quantity-aware artifact, a multi-session accounting interaction, or an authorized implementation change.
