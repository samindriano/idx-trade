# Alpha Eligibility Policy Resolution Packet V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Status: `BLOCKED_POLICY_CONFLICT / DECISION REQUIRED`

## Purpose

This packet isolates the one authoritative policy decision currently blocking
future feature-panel execution. It does not choose a population, regenerate
features, alter the incumbent model, or open protected targets/outcomes.

## Observed contradiction

The protocol and packet prose state a trailing-60 regular-market-value rule
with at least 20 finite observations. The implementation helper instead calls
`rolling(window=window, min_periods=window)` for both rolling operations.

Evidence:

- Protocol: `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md:40-43`
  and `:185-189`.
- Packet: `docs/checkpoints/2026-09-19_ALPHA_FUTURE_EVALUATION_PACKET_V2.md:67`
  and `:82-91`.
- Implementation: `research/alpha_stage_a_v2.py:92-96`.
- Provenance: protocol freeze `a02a1547` at
  `2026-09-19T11:16:39+07:00`; implementation addition `1ebced27` at
  `2026-09-19T11:41:01+07:00`; packet closure `9e4e54fa` at
  `2026-09-19T20:34:54+07:00`.

The independent replay measured:

| Interpretation | Eligible rows | Tickers | Dates |
|---|---:|---:|---:|
| Current implementation (`min_periods=60`) | 310,761 | 711 | current staged population |
| Literal minimum-20 interpretation | 348,765 | 619 affected tickers | 1,241 affected dates |
| Difference | +38,004 | 619 affected tickers | 1,241 affected dates |

The implementation replay matches the current staged feature artifact exactly
for 981,940 panel keys, including eligibility, C1/C2/C4 scores, and
average-tie ranks. That proves implementation reproduction only; it does not
resolve which contract is authoritative.

## Resolution options

### Option A — code-aligned minimum 60

Authoritatively amend the protocol and packet prose to require 60 finite
observations for the count and median operations, preserving the current
implementation population of 310,761 rows.

Required follow-up:

1. Record the authoritative policy decision and exact count/median semantics.
2. Amend the protocol and packet text in the isolated lane.
3. Re-hash protocol, packet, contract, and control bindings.
4. Re-run the independent constructor replay and packet/firewall gates.
5. Keep the result outcome-blind and `FUTURE_RESEARCH`; this does not create
   `READY_FOR_REENTRY`.

### Option B — prose-aligned minimum 20

Authoritatively amend the implementation contract to use a declared minimum of
20 finite observations. The exact semantics must state whether both rolling
count and rolling median use `min_periods=20`, or define a different explicit
pair. The literal replay implies 348,765 rows under the current count/median
interpretation.

Required follow-up:

1. Record the authoritative policy decision and exact count/median semantics.
2. Modify only the isolated implementation lane.
3. Regenerate the isolated feature artifact and manifest.
4. Re-run the independent constructor replay, key/score/rank checks, packet,
   firewall, and lane-integrity gates.
5. Reassess structural coverage and friction diagnostics; do not use the
   additional rows for target tuning or predictive claims.

## Required authority record

Before either option can proceed, the decision record must explicitly bind:

- authoritative eligibility rule (`20` or `60`);
- rolling count semantics;
- rolling median semantics;
- finite-value treatment;
- same-session and official-calendar semantics;
- resulting population row count;
- protocol, implementation, packet, and manifest hashes;
- whether isolated feature regeneration is authorized.

An informal choice, chronology-only inference, or preference for the larger
population is insufficient. Until this record exists, the machine guard must
remain `BLOCKED_POLICY_CONFLICT` and the packet must remain non-executable.

## Current controls

- Eligibility consistency guard: `BLOCKED_POLICY_CONFLICT`.
- Future packet verifier: `PASS` means the block is represented faithfully,
  not that the packet is executable.
- Target/privacy firewall: `PASS`.
- Protected target, outcome, incumbent predictive artifacts, provider, cloud,
  capture, telemetry, and canonical state: untouched.

## Decision boundary

No agent or worker may resolve this conflict by selecting Option A or B,
regenerating the panel, or treating either population as authoritative without
the required decision record.
