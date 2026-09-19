# H-LIQ-01 Temporal Persistence Red-Team — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_SUPPORT / FAIL_UNQUALIFIED_PERSISTENCE / NOVELTY_UNKNOWN`

## Question

Does H-LIQ-01's structural novelty and composition remain stable through time
and liquidity buckets, or can its earlier aggregate diagnostics hide a moving
mechanism/exposure?

This is an independent, read-only, target-free red-team check. It does not
create C5, access outcomes, or modify the H-LIQ artifact.

## Evidence

Inputs were the frozen panel and guarded Stage-A feature artifact:

- Panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`.
- Guarded feature SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`.

The fixed check used six consecutive 100-session blocks, all liquidity
buckets, and Top-30 selections. Coverage passed: `600` sessions, `100` dates
per block, and complete Top-30 selections per block.

However, the temporal behavior was not stable enough for an unqualified
persistence claim:

- Q4 H-LIQ/C2 dependence ranged from `0.0762` to `0.3053` across blocks.
- Selected bottom-market-value Q1 share ranged from `29.47%` to `51.30%`.
- Prior H-LIQ diagnostics already show listing-age concentration and sector
  robustness blocked; this check does not resolve those gaps.

## Adjudication

| Review item | Result |
|---|---|
| Six-block coverage/mask integrity | `PASS` |
| Temporal persistence as an unqualified claim | `FAIL` |
| Mechanism-level novelty | `UNKNOWN` |
| Economic interpretation/capacity | `UNKNOWN` |
| PIT/CA/identity authority | `UNKNOWN / BLOCKED` |
| Candidate creation | `NO` |

The changing dependence and composition do not prove H-LIQ is useless; they do
show that its aggregate novelty/economic story is not stable enough to upgrade
the disposition. Retain `FUTURE_RESEARCH / NOVELTY_PENDING /
ECONOMIC_CAUTION`, and do not create C5 or add H-LIQ to the protected packet.

## Reproducibility

The check reused only the existing frozen panel, guarded features, and
previously audited H-LIQ definitions. No new code or artifact was created by
the worker; this document records the independent adjudication. Existing
supporting evidence:

- `2026-09-19_ALPHA_HLIQ01_NOVELTY_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_SOURCE_DECOMPOSITION_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md`
- `2026-09-19_ALPHA_HLIQ01_SIZE_NEUTRAL_RESULT_V1.md`

No target, outcome, provider, cloud, incumbent, canonical, capture, scheduler,
telemetry, or production state was accessed or modified.
