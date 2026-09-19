# Alpha continuation frontier and constructor replay — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`  
Scope: outcome-blind, pre-admission research only. No protected target,
forward-return, label, incumbent-outcome, provider, network, cloud, capture,
telemetry, or canonical-state access was used.

## Independent C1/C2/C4 constructor replay

The replay was implemented independently of the Stage A builder in
`research/alpha_c1234_constructor_replay_v1.py`. It rebuilds the official
session grid, active/liquid eligibility mask, prior-only rolling inputs, C1,
C2, and C4 scores, and average-tie cross-sectional percentile ranks from the
already staged non-outcome inputs.

Result: `PASS_INDEPENDENT_FORMULA_AND_RANK_REPLAY`.

| Gate | Result |
|---|---:|
| Replay rows | 981,940 |
| Stored rows | 981,940 |
| Key grain | `ticker/date`, unique and exact |
| Official-date membership | PASS |
| Eligibility mask equality | PASS; 0 mismatches |
| C1 score equality | PASS; 0 mismatches, max absolute difference 0.0 |
| C2 score equality | PASS; 0 mismatches, max absolute difference 0.0 |
| C4 score equality | PASS; 0 mismatches, max absolute difference 0.0 |
| C1/C2/C4 rank equality | PASS; 0 mismatches for all three |

The machine result is staged at
`alpha_c1234_constructor_replay_v1.json`; the independent replay firewall
also returned `PASS` for the replay code, staged feature schema, and result
metadata.

This closes the narrow score/rank replay uncertainty identified by the earlier
red-team: the stored C1/C2/C4 scores and ranks are reproducible from the
current implementation and declared inputs. A separate audit then found that
the prose eligibility rule (at least 20 finite values) conflicts with the
implementation's `min_periods=60`; that contradiction is recorded as a
blocking policy decision in
`2026-09-20_ALPHA_ELIGIBILITY_CONTRACT_CONTRADICTION_V1.md`. The replay does
not certify PIT/as-of availability, issuer continuity, corporate-action price
basis, survivorship completeness, executable capacity, or predictive
performance.

## Independent capacity/source frontier audit

A separate read-only audit found no new admissible historical surface and no
decision-changing capacity evidence. The existing structural evidence remains:

- q99 Top-30 turnover is C1 `63.33%`, C2 `56.67%`, C4 `40.00%`;
- Q1 market-value exposure is C1 `26.63%`, C2 `21.26%`, C4 `34.46%`;
- selected names at most 365 days old are C1/C2/C4 `9.66% / 11.60% /
  10.98%`;
- ADV, spread, queue, fill, daily sector history, and population-complete
  issuer/PIT authority remain unavailable;
- the historical foreign-flow archive is structurally intact but has unknown
  publication time; lifecycle/free-float/HSC/broker surfaces remain
  event-only, monthly, or snapshot-only;
- C1+C4 remains the lowest-turnover combination at `34.85%`, but is still
  dependent, bottom-value exposed, and capacity-unadmitted;
- H-LIQ-01 remains `UNKNOWN / NO-GO` for novelty retry.

Accordingly, the high-information frontier is now source admission and
capacity authority, not another same-surface formula or combination retry.

## Decision register

- C1/C2/C4 statuses remain `FUTURE_RESEARCH`.
- Eligibility contract remains unresolved; no alternative mask was promoted.
- C3 remains `BLOCKED`.
- H-LIQ-01, H-VOL-01, and H-EXC-02 remain future structural hypotheses; no C5
  was created.
- No `READY_FOR_REENTRY` candidate exists.
- No target/outcome evaluation was opened.

## Reusable evidence

- `research/alpha_c1234_constructor_replay_v1.py`
- `alpha_c1234_constructor_replay_v1.json`
- `alpha_c1234_constructor_replay_firewall_v1.json`
- `2026-09-20_ALPHA_C1234_REDTEAM_ADJUDICATION_V1.md`
- `2026-09-20_ALPHA_LOCAL_DATA_SURFACE_REVIEW_NO_NEW_EVIDENCE_V1.md`
