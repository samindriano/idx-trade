# V4-3 CA residual attribution V2 — compact continuity compatibility fix

Date: 2026-08-19 Asia/Jakarta
Branch: `data/v4-3-ca-training-domain-ksei-129-v1`
Status: `READY_FOR_OFFLINE_ATTRIBUTION_V2_RERUN`

## Failure observed

The first residual-attribution run stopped before creating an output root with:

`CONTINUITY_COLUMNS_MISSING:['blocking_event_ids']`.

This is an engineering/schema mismatch only. The immutable KSEI-129 offline
replay intentionally persisted compact continuity with status/reason fields but
not the diagnostic-only `blocking_event_ids` list. The scenario calculations do
not require event IDs.

## Fix

A V2 wrapper was added at:

`scripts/run_v4_3_ca_training_domain_residual_attribution_v2.py`

It preserves the V1 scenario/gate implementation and:

1. supplies an empty compatibility field only for V1 input validation;
2. reconstructs schedule-event attribution from the separately hash-pinned
   event audit using `semantic_class == SCHEDULE_REQUIRED` and exact ticker
   identity;
3. fails closed if a schedule-blocked ticker lacks a corresponding
   SCHEDULE_REQUIRED event-audit identity.

This reconstruction matches the frozen `window_continuity` semantics: any
SCHEDULE_REQUIRED event on a ticker remains in the missing-schedule set for that
ticker's windows until exact official schedule evidence exists.

## Scientific boundary unchanged

- parent KSEI-129 replay manifest remains immutable;
- gate remains exactly 0.90;
- baseline/coverage-only/schedule-only/coverage+schedule/price-only diagnostic
  scenarios are unchanged;
- exact mechanical crossings are never waived;
- no provider/network retry;
- no target/rank materialization;
- no model fit/prediction/performance;
- no protected-forward access;
- no pass-preserving subset selection.

The failed V1 attribution run created no result root, so V2 may use the same
fresh output path after verifying `Test-Path` is false.
