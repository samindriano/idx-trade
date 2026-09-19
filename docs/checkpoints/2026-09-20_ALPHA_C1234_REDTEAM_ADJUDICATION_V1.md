# C1/C2/C4 and combination red-team adjudication — 2026-09-20

Lane: isolated `codex/alpha-available-data-20260919`
Scope: independent, read-only Phase-Q challenge. No target/outcome access,
model scoring, provider/network access, canonical-data mutation, capture/cloud/
telemetry mutation, or candidate promotion.

## Executive result

The independent red-team does not upgrade any candidate or combination to
`READY_FOR_REENTRY`. The current disposition remains `NO-GO` for protected
evaluation pending independent admission and unresolved basis/capacity gates.

| Challenge | Result | Interpretation |
|---|---|---|
| Key/mask/rank/deterministic selection | `PASS — narrow` | Replay checks pass, but this is not a full constructor rebuild. |
| Full feature-constructor and eligibility rebuild | `UNKNOWN` | Existing verifier is artifact/structural replay only. |
| PIT/as-of/knowledge-time OHLCV | `UNKNOWN` | No row-level available-at, revision, or vintage authority. |
| Corporate-action/price basis | `FAIL for readiness` | The 188-row unresolved basis stress changes C1 materially; minimum Top-30 overlap reaches 36.667%. |
| Identity/listing continuity | `UNKNOWN` | Security master does not provide an issuer/ISIN transition chain; panel/master populations differ. |
| Survivorship/population completeness | `UNKNOWN` | No completeness contract is established. |
| Concentration/liquidity/executable capacity | `FAIL for readiness` | C1/C2/C4 Q1 market-value exposure is 26.63%/21.26%/34.46%; q99 turnover is 63.33%/56.00%/40.00%; ADV/spread/queue/fill remain unavailable. |
| Parameter/lookback robustness | `FAIL for full robustness claim` | Corrected key-aligned overlaps with the baseline remain only C1 57.23%/52.04%, C2 65.32%/60.14%, C4 44.76%/45.41%. |
| C1/C4 additive independence | `FAIL` | Daily Spearman is 0.4624 and equal-weight combination dependence is about 0.850/0.851. |
| Process-level anti-overfitting proof | `UNKNOWN` | Equal weights/no optimization are bounded, but access flags remain self-attested. |
| Combination readiness | `FAIL` | C1+C4 is the lowest-turnover combination at 34.85%, but remains dependent, concentrated, and capacity-unadmitted. |

These are structural readiness decisions, not predictive results. No IC, ICIR,
OOS, forward return, incumbent comparison, or superiority claim is made.

## Evidence anchors

- `research/verify_alpha_c1234_adversarial_audit_v2.py:154-220,283-324`
- `docs/checkpoints/2026-09-19_ALPHA_C1234_REDTEAM_SCOPE_ADJUDICATION_RESULT_V1.md:30-47`
- `docs/checkpoints/2026-09-19_ALPHA_CA_PRICE_BASIS_RESULT_V1.md:59-71,87-103`
- `docs/checkpoints/2026-09-19_ALPHA_IDENTITY_CONTINUITY_RESULT_V1.md:22-50`
- `docs/checkpoints/2026-09-19_ALPHA_CAPACITY_FRICTION_TAIL_RESULT_V1.md:38-71`
- `docs/checkpoints/2026-09-19_ALPHA_PHASE_Q_REDTEAM_CORRECTION_RESULT_V1.md:32-51`
- `docs/checkpoints/2026-09-19_ALPHA_STRUCTURAL_LAB_RESULT_V1.md:124-145`
- `docs/checkpoints/2026-09-19_ALPHA_COMBINATION_ECONOMICS_RESULT_V1.md:34-80`

## Decision

Keep C1/C2/C4 as conditional `FUTURE_RESEARCH` items and keep combinations
outside the protected C1-C4 packet. Do not retry this exact red-team question
unless a new constructor, independently admissible PIT/CA/identity source, or
changed falsifiable contract becomes available. The strongest next legal
frontier is source-basis reconciliation, not target evaluation or weight
optimization.
