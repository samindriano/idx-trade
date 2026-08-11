# Targeted Zapi Residual Audit — Implementation Draft Checkpoint

Date: 2026-08-11 (Asia/Jakarta)
Branch: `data/idx-open-backfill-zapi-residual-audit-v1`
Parent Yahoo residual HEAD: `2a40b1da4f75a0c8c80b2045e5e07f3ea0ed50e7`

## Status

**`ZAPI_TARGETED_RESIDUAL_AUDIT_IMPLEMENTED_LOCAL_VERIFICATION_REQUIRED`**

A bounded Source-2 audit has been specified and implemented without touching the accepted Yahoo census branch or any parallel Ranking/PIT-sector work.

## Frozen research scope

The audit targets only:

- `120` deterministic rows from the `32,103` Yahoo no-factor H/L/C mismatch residual class;
- `80` deterministic rows from Yahoo provider-gap/error residuals, including all five error tickers where rows exist;
- `40` deterministic known-existing-Open controls.

Corporate-action-related residual rows are excluded from this Source-2 stage.

The audit is diagnostic only. No panel write, bulk backfill, execution-grade promotion, or downstream modelling is authorized.

## Implementation

Added:

- `src/idx_trade/zapi_residual_audit.py`;
- `tests/test_zapi_residual_audit.py`;
- `docs/OPEN_BACKFILL_ZAPI_RESIDUAL_AUDIT_V1.md`;
- `coordination/handoffs/IDX-OPEN-BACKFILL-ZAPI-RESIDUAL-AUDIT.md`.

The runner:

- verifies immutable panel SHA;
- rebuilds accepted residual classes from Yahoo census evidence;
- freezes a deterministic provider-outcome-independent sample;
- groups Zapi requests by unique sample date to reduce quota use;
- reads credentials only from `ZAPI_API_KEY`;
- fails closed on absent credential or plan/access gating;
- applies unchanged exact panel H/L/C + valid in-range Open admission;
- arbitrates no-factor mismatch rows as panel-supported, Yahoo-supported, three-way disagreement, or no Source-2 row;
- writes external diagnostic artifacts only;
- leaves `execution_grade_promoted=false` and `bulk_backfill_authorized=false`.

## Required local verification before network runtime

Codex must run focused and full pytest before any Zapi request.

Two concrete implementation invariants require explicit verification and the smallest correction if needed:

1. pandas/numpy boolean known-control exactness must be evaluated by boolean value, not Python object identity;
2. the artifact manifest must exclude itself and the not-yet-finalized summary so no stale circular hash can be recorded.

No sample quota, source, gate, or arbitration redesign is authorized during verification.

## Stop boundary

After local verification and the bounded Zapi audit, STOP for independent ChatGPT review before any Source-2 backfill proposal.
