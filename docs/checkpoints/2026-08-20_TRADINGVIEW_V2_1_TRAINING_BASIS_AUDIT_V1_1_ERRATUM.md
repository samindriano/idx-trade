# TradingView V2.1 Training Basis Impact Audit v1.1 Erratum

Date: 2026-08-20 (Asia/Jakarta)
Branch: `audit/tradingview-v2-1-training-basis-impact-v1`

## Runtime blocker

The first local Step-2 run stopped before any impact calculation with:

`V2_CLEAN_REPLAY_TABLE_NOT_FOUND`

This was a runner wiring error, not a scientific result.

## Root cause

The v1 runner conflated two distinct frozen identifiers documented by the
PIT-safe V2/V3-B/O2 reproduction lineage:

- corrected V2 parquet file SHA-256:
  `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`;
- corrected V2 stable key SHA-256:
  `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`.

It also defaulted to the historical replay *output* root rather than the
immutable corrected-input root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10`

## Correction

`scripts/run_training_price_basis_impact_audit_v1_1.py` is a narrow wrapper
around the frozen v1 audit implementation.  It changes no price-basis
threshold, stable-run rule, feature logic, V2/V4-X adjudication rule, or output
semantics.  It only:

1. points V2 discovery at the exact corrected-input root;
2. pins the exact corrected V2 parquet file SHA;
3. independently verifies the frozen corrected V2 key SHA;
4. verifies the expected corrected V2 population: 292,631 rows / 737 tickers.

The failed v1 run did not reach the V2 comparison or V4-X comparison and is
therefore not evidence for or against training-lineage impact.

## Boundaries unchanged

No provider calls, model fitting, historical scoring, protected-forward access,
target-ledger opening, canonical artifact mutation, or retraining is authorized
by this correction.
