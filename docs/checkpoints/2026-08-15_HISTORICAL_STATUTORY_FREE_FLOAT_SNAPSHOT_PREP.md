# Historical Statutory Free Float Snapshot V1 — Preparation

Date: 2026-08-15 Asia/Jakarta
Status: `PREPARATION_ONLY_PENDING_CANONICAL_TEAM_STATUS_CLAIM`

## Goal

Build a point-in-time-safe historical table of **official reported statutory free-float snapshots** for IDX-listed equities. This is not effective/mobile supply and is not a holder-subtraction estimate.

The preferred observation is the explicit official free-float share count and percentage reported in an IDX market-wide free-float status announcement or issuer LBRE/monthly registration report.

## Scientific boundary

Never derive statutory free float as `100% - sum(>=1% holders)`, `100% - HSC concentration`, or from current Company Profile holder rows. Holder-level reconstruction remains diagnostic only and stays fail-closed under the separate Statutory Free Float Reconstruction V1 contract.

## PIT identity

Each admitted snapshot must preserve at least:

- ticker;
- ownership/report position date (`as_of_date`);
- official publication timestamp (`published_at`);
- explicit free-float shares;
- explicit free-float percentage;
- total listed shares when explicitly reported;
- source family (`IDX_MARKET_WIDE_FF_STATUS` or `ISSUER_LBRE`);
- announcement number;
- correction/original lineage;
- exact official attachment URL;
- attachment SHA-256;
- metadata-source SHA-256.

The observation becomes usable only at `published_at`, never retroactively at `as_of_date`.

## Correction policy

- Preserve original and correction records independently.
- A correction must identify a deterministic prior record for the same issuer/position date.
- Latest-known state at a cutoff may use a correction only after the correction publication timestamp.
- Do not overwrite or delete the original raw record.
- Ambiguous correction lineage fails closed.

## Snapshot policy

This lane emits observations only. It does not create daily forward-filled free-float values and does not interpolate between month ends.

A later integration contract may define how a latest-known official observation is carried into a daily research feature. That future contract must separately address corrections, ownership-change events, and staleness.

## Expected source hierarchy

1. Exact official issuer LBRE/monthly-registration attachment with explicit free-float fields.
2. Exact official IDX market-wide free-float status attachment with explicit ticker row.
3. No synthetic/mirror replacement when exact official bytes are unavailable.

If both issuer LBRE and market-wide status exist for the same issuer/position date, retain both source observations and require an explicit reconciliation result rather than silently preferring a disagreement.

## Historical target

The prior bounded audit proves official free-float-related attachment coverage from April 2024 through August 2026, but does not prove continuous monthly coverage or 2021–2023 availability. V1 must census the actual available official observations and report gaps rather than manufacture a regular monthly grid.

## Not authorized

- holder-level statutory reconstruction;
- effective/mobile-supply inference;
- HSC or >=1% subtraction;
- daily free-float panel;
- volume/free-float or Foreign Flow/free-float features;
- HHI/concentration features;
- models or protected outcomes.
