# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-CLOSE-RMV-TRADABILITY-AUDIT-V1
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: `5fab5a9a56ce21989ed27474566c5817db6cc1df`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: pending documentation commit
scope: outcome-blind Close/RMV/input-integrity audit
files_changed:
  - `docs/checkpoints/2026-08-24_HISTORICAL_E2E_CLOSE_RMV_TRADABILITY_AUDIT_V1.md`
  - `coordination/handoffs/IDX-HISTORICAL-E2E-CLOSE-RMV-TRADABILITY-AUDIT-V1-RESULT.md`

## Findings

External audit root:
`D:\Documents\Project\idx-historical-e2e-close-rmv-tradability-audit-20260824-v2`

Summary SHA-256:
`36d35aa5a453b21441b209ffdb4b2553212d342fab25698e2f7ff5787b392bcb`

The 5,693 exposure rows have complete current H/L/C/Volume and the 600
session regular-market-value coverage artifact is complete. Key outer joins,
date/index alignment, price invariants, and duplicate ticker×signal-session
checks pass. One next-session row is incomplete and remains excluded.

## Decision

`CLOSE_RMV_CERTIFIED_FOR_EXPOSURE_INPUTS_TRADABILITY_REMAINS_SEPARATE_GAP`

This result does not certify that every exposure was legally/tradably
executable. The separate tradability gate and the frozen corporate-action and
Open gates remain required before any replay scope is frozen.

## Decisions needed

- Do not use this audit to expand the strict replay scope.
- Review the parallel Open, CA, dividend, and replay-engine audits before any
  performance or NAV access.

## Validation

No source/runtime code was changed. No provider calls, labels, protected
outcomes, future returns, model fitting, or performance metrics were accessed.
