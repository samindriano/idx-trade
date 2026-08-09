# Open Backfill Tier-2 Source Audit — Ready

Date: 2026-08-10 (Asia/Jakarta)
Branch: `data/idx-open-backfill-tier2-audit-v1`
Parent commit: `6baf8b35a591c99a3a68f19a91d1d88d6588e128`

## Decision

**`OPEN_BACKFILL_TIER2_SOURCE_AUDIT_READY`**

Tier-1 Wildan is closed as a missing-Open recovery source after recovering 0 of 446,843 null Open rows under the frozen admission contract. Tier-2 is authorized only as a bounded source audit.

Read:

- `docs/OPEN_BACKFILL_TIER2_SOURCE_AUDIT_V1.md`;
- `docs/checkpoints/2026-08-10_OPEN_BACKFILL_WILDAN_RUNTIME.md`;
- the Tier-1 independent review checkpoint on the parent branch;
- `coordination/handoffs/IDX-OPEN-BACKFILL-TIER2-AUDIT.md`.

## Candidate order

1. Zapi IDX `stock-summary` pilot if Free-tier access can be established with a local API key without exposing credentials;
2. Yahoo Finance via `yfinance` as a separately scored fallback/personal-research candidate.

No bulk Tier-2 backfill is authorized at this checkpoint.

## Immutable baseline

- 1260-session signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`;
- unresolved Open rows: 446,843;
- existing Open immutable;
- `execution_grade_promoted=false`.

## Required runtime outcome

The local worktree audit must produce a deterministic sample manifest, per-source raw/audit artifacts, access/plan status, H/L/C agreement, known-Open agreement, missing-Open admissibility, rejection reasons, and hashes. It then stops for independent ChatGPT review.

Do not relax source equality rules after seeing results. Do not use the pilot to claim execution-grade coverage.