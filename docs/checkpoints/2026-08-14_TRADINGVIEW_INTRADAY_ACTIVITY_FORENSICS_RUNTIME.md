# TradingView Intraday Activity-Aware Forensics V1 - Runtime

Status: `RUNTIME_COMPLETE_PENDING_INDEPENDENT_REVIEW`

This was an offline-only forensic classification of the frozen TradingView
admission pilot. It does not alter or rescue the frozen
`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED` verdict.

## Runtime identity and boundaries

- Branch: `data/tradingview-intraday-activity-forensics-v1`
- Runtime HEAD before this checkpoint commit: `97b1f01c4ec4171e438cff6e4ad9118afde7e3b8`
- Prepared checkpoint: `docs/checkpoints/2026-08-14_TRADINGVIEW_INTRADAY_ACTIVITY_FORENSICS_PREPARED.md`
- Admission artifact root (external, read-only):
  `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`
- New output root (external):
  `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_intraday_activity_forensics_v1_20260814`
- Provider/network calls: `0`
- TradingView rerun: `false`
- Canonical panel write: `false`
- Frozen admission verdict changed: `false`

Hash-pinned inputs were verified before reading:

- admission artifact manifest: `de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee`
- frozen sample manifest: `3de36746942bbf6e7dc201ce14d1aa94c75ab1dc6ebd59989e828f41114971bd`
- Mathieu intraday bars: `332c26cb2a7951b2664d99349e4cfffeb516d5c416b0c37a5e6fe4bcdfff4f95`
- Mathieu request manifest: `ca1271ab7551c2f4cdd3029b179a11748cb2a1892726477fa9b2e6b40603d4d8`
- canonical panel before and after: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

The runtime used only the frozen six yearly July windows and the exact
canonical daily panel. Activity was classified fail-closed:

- positive volume: `ACTIVE_POSITIVE_VOLUME`;
- zero volume with flat available H/L/C: `INACTIVE_ZERO_VOLUME_FLAT`;
- missing/ambiguous activity: `UNCERTAIN_*`.

## Overall result

| metric | count |
|---|---:|
| listed certified sessions | 1,477 |
| canonical-active sessions | 1,282 |
| TV-covered active sessions | 1,282 |
| true TV misses on active sessions | 0 |
| explained no-trade sessions | 0 |
| uncertain sessions | 195 |
| activity-aware coverage | 100.00% |
| conservative lower-bound coverage | 86.80% |

The 195 unresolved rows were all `UNCERTAIN_CANONICAL_ROW_MISSING`; no
zero-volume flat or zero-volume non-flat rows were observed. They therefore
cannot be treated as genuine no-trade sessions. The point estimate is perfect,
but the conservative lower bound remains below the contextual 90% reference.

Interpretation: `ACTIVITY_AWARE_COVERAGE_INCONCLUSIVE_DUE_TO_UNCERTAIN_ACTIVITY`.
This does not change the frozen admission rejection and does not authorize a
provider rerun, bulk acquisition, panel integration, Path Risk restart, O2
access, or modelling.

## Yearly result

| year | listed certified sessions | canonical-active | TV-covered active | true TV misses | explained no-trade | uncertain | activity-aware coverage | conservative lower bound |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021 | 227 | 215 | 215 | 0 | 0 | 12 | 100.00% | 94.71% |
| 2022 | 250 | 236 | 236 | 0 | 0 | 14 | 100.00% | 94.40% |
| 2023 | 250 | 220 | 220 | 0 | 0 | 30 | 100.00% | 88.00% |
| 2024 | 250 | 212 | 212 | 0 | 0 | 38 | 100.00% | 84.80% |
| 2025 | 250 | 195 | 195 | 0 | 0 | 55 | 100.00% | 78.00% |
| 2026 | 250 | 204 | 204 | 0 | 0 | 46 | 100.00% | 81.60% |

The listed-session total is 1,477 because the frozen sample's listing intervals
exclude three ticker-session pairs from the nominal 1,480 session grid.

## External outputs and hashes

The output root contains exactly these three runtime files:

- `activity_support.csv` — 1,477 classified expected ticker-session rows;
  SHA-256 `6963fefc5ffa0af0732628b46218a98a8401c729ace0d5c9cc73b14a413777d0`
- `missing_session_forensics.csv` — 195 missing-TV rows; SHA-256
  `d03f8f2e7399d4337bbb1c550b6330d9bf9a1850fb2d4c967e184d220ab6ef9f`
- `summary.json` — SHA-256
  `5778169260cd0712ee75a1228e2d5ddf1f5d05ac3933e6a99c82d10b2176506b`

The panel SHA after runtime remained
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
No external raw admission artifact was modified.

## Validation

- focused TradingView tests: `14 passed`;
- full pytest: `53 passed, 1 failed`;
- pre-existing failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`; the fixture emits two revision conflicts (`raw_close` and `vendor_adj_close`) while the assertion expects one. This lane did not modify storage code or that test;
- `git diff --check`: passed before final commit.

An unrelated untracked `apps/` directory was preserved and not staged.

This lane stops for independent ChatGPT review.
