# Eligibility contract contradiction — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`  
Disposition: `BLOCKED / POLICY DECISION REQUIRED`  
Scope: read-only, outcome-blind audit. No candidate, feature artifact,
protected data, provider, cloud, capture, telemetry, or canonical state was
modified.

## Finding

The frozen research protocol says the decision universe uses a trailing-60
official-session median regular-market-value rule with **at least 20 finite
observations** and a minimum median of IDR 1 billion
(`2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md`, data/PIT section).

The implemented helper in `research/alpha_stage_a_v2.py` instead applies
`min_periods=window` for every rolling operation, including both the 60-session
count and median. Therefore a row with 20 valid values and 40 missing values is
not admitted by the implementation even though the prose says at least 20
finite observations.

The future packet also states `min_periods=window` for rolling operations, so
the protocol prose, packet prose, and implementation are not yet a single
unambiguous contract. This is not safe to resolve by silently changing the
mask or re-running the candidate artifacts.

## Quantified impact

The read-only replay used the frozen official-session grid, regular-active
anchors, and existing `regular_market_value` field:

| Definition | Eligible full-grid rows |
|---|---:|
| Current implementation (`min_periods=60`) | 310,761 |
| Literal prose interpretation (count `>=20`, median `min_periods=20`) | 348,765 |
| Newly admitted under literal prose | 38,004 |
| Newly admitted tickers | 619 |
| Newly admitted dates | 1,241 |

The staged feature mask matches the current implementation exactly (0 mask
mismatches across 981,940 stored panel rows). That proves artifact consistency,
not that the implementation is the intended scientific contract.

## Decision

- Do not change `alpha_stage_a_v2.py` or regenerate the staged feature artifact
  until the eligibility definition is explicitly resolved by the authoritative
  research contract.
- Do not compare the two populations, choose the larger population, or use the
  difference to tune any candidate.
- Keep C1/C2/C4 at `FUTURE_RESEARCH`, keep the packet blocked, and treat any
  future re-entry as requiring one frozen, hash-bound eligibility definition.
- A legitimate resolution must state whether the count and median each use
  `min_periods=60`, or whether count/median use a declared minimum of 20, plus
  the exact missingness and population rules. Only then may an authorized
  outcome-blind replay and artifact re-hash occur.

## Evidence and hashes

- Constructor helper: `research/alpha_stage_a_v2.py`
  - SHA-256: `62a16137d039c0304e00fbf91de65ed5c70d50952faccf2aff1b0a587f49e59a`
- Protocol: `docs/checkpoints/2026-09-19_ALPHA_RESEARCH_PROGRAM_PROTOCOL_V1.md`
  - SHA-256: `39abbd6ea79c80bf0619bbdd00220461fbd25c899da58ed787fd7c4e332ebfee`
- Packet contract: `research/alpha_future_evaluation_packet_v2_contract.json`
  - SHA-256: `cea96074bea9e489d96230fb8737041b2c70508178411b4aebb390d520b3e1aa`
- Independent constructor replay: `alpha_c1234_constructor_replay_v1.json`
  - replay status: `PASS_INDEPENDENT_FORMULA_AND_RANK_REPLAY`
  - limitation: it reproduces the current implementation; it does not choose
    between the contradictory eligibility contracts.

