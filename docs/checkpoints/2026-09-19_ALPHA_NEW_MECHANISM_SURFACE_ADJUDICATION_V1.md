# New Mechanism Surface Adjudication — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Category: `E / G — bounded mechanism discovery`
Status: `NO-GO / NO NEW CANDIDATE`

## Question

Does the currently admitted local source surface support a genuinely distinct
pre-admission mechanism beyond the already audited C1/C2/C4, H-LIQ-01,
H-VOL-01, and H-EXC-02 directions?

This is a read-only, target-free surface adjudication. It does not create a
candidate, open protected targets, access outcomes, add a provider, or modify
canonical data.

## Evidence

- The guarded Stage-A surface is already represented by C1 residual reversal,
  C2 participation confirmation, C3 financial quality, and C4 path-efficiency
  reversal. See `research/alpha_stage_a_v2.py` and
  `2026-09-19_ALPHA_DATA_INVENTORY_RESULT_V1.md`.
- Effort-vs-result is not a new independent source on this surface:
  `range_per_effort` correlation with the existing representation is
  `0.999291`, and `effort_absorption` correlation is `0.904488`; its Stage-B
  direction is already `NO-GO`. See
  `2026-09-19_ALPHA_CHALLENGER_EFFORT_RESULT_V1_STAGE_A_RESULT.md`.
- Price-path and breakout directions are already covered or closed at the
  tested representation level. See
  `2026-09-19_ALPHA_ARCHAEOLOGY_RESULT_V1.md` and
  `2026-09-19_ALPHA_CHALLENGER_BREAKOUT_EVENT_V1_HISTORICAL_RESULT.md`.
- Cross-sectional disagreement and rank combinations do not establish a new
  information source; the existing combination work explicitly keeps them as
  structural combinations rather than new candidate IDs. See
  `2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md`.
- H-LIQ-01, H-VOL-01, and bounded H-EXC-02 remain the closest distinct
  representations, but their unresolved PIT/corporate-action basis and
  capacity/turnover concerns prevent a new candidate admission. In particular,
  H-EXC-02 has mean Top-30 turnover of `40.7750%`.
- Sector, spread, order-book, broker-flow, and authoritative historical
  available-at fields are not admitted. Historical Open is partial and mixed
  source, so it cannot support a new PIT-safe mechanism here.

## Adjudication

| Direction | Result | Reason |
|---|---|---|
| Effort vs result | `REDUNDANT / CLOSED` | Existing range/path information already captures the surface; high structural correlation |
| Breakout/rejection | `CLOSED AT TESTED REPRESENTATION` | Prior bounded result provides no basis for a rescue sweep |
| Cross-sectional disagreement | `REDUNDANT OR BLOCKED` | Existing combinations and dispersion work cover the available source family |
| New OHLCV/value mechanism | `NO-GO` | No unrepresented, PIT-defensible source was found |
| H-LIQ-01 / H-VOL-01 / H-EXC-02 | `FUTURE_RESEARCH` | Distinct structural questions remain, but none satisfies admission gates |
| New candidate ID | `NO` | Candidate budget unchanged; no protected packet change |

## Decision

No defensible new mechanism is admitted from the current local source surface.
This closes a redundant discovery branch; it does not reject the broader
economic families, nor does it make a predictive claim. Future discovery
requires either an independently admitted source contract or a genuinely new
PIT-safe information surface.

## Boundaries

Population PIT/as-of authority, issuer/ISIN continuity, corporate-action basis,
historical executable capacity, incumbent overlap, and protected outcomes
remain unresolved. No target, outcome, provider, cloud, canonical, capture,
scheduler, telemetry, or production state was accessed or modified.
