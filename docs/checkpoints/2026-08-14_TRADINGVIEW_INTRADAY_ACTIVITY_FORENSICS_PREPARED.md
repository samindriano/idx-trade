# TradingView Intraday Activity-Aware Forensics V1 — Prepared

Status: `OFFLINE_RUNTIME_BLOCKED_ON_LOCAL_ARTIFACT_ACCESS`

## Purpose

This lane does **not** alter or rescue the frozen admission-pilot verdict
`TRADINGVIEW_INTRADAY_ADMISSION_REJECTED`. It tests one new diagnostic question:
whether missing TradingView ticker-sessions are genuine provider misses on days
with canonical positive trading activity, or legitimate zero-volume/no-trade
sessions that should not have been expected to produce an intraday candle.

## Lineage

- Admission pilot branch/head: `data/tradingview-historical-intraday-admission-pilot-v1@c26c4e429e162fd6240f6b6918b3f27e86494229`
- Frozen admission artifact manifest SHA-256: `de7246e447a83b15c083d19a00808f13670d97f720bd1e28ce8756e02186e8ee`
- Frozen sample manifest SHA-256: `3de36746942bbf6e7dc201ce14d1aa94c75ab1dc6ebd59989e828f41114971bd`
- Frozen Mathieu intraday-bars SHA-256: `332c26cb2a7951b2664d99349e4cfffeb516d5c416b0c37a5e6fe4bcdfff4f95`
- Frozen Mathieu request-manifest SHA-256: `ca1271ab7551c2f4cdd3029b179a11748cb2a1892726477fa9b2e6b40603d4d8`
- Frozen canonical-panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`

## Frozen forensic contract

Canonical activity is classified without provider calls, rescaling, imputation,
or ticker substitution:

- `ACTIVE_POSITIVE_VOLUME`: canonical daily row exists and volume > 0.
- `INACTIVE_ZERO_VOLUME_FLAT`: volume == 0 and available H/L/C are flat.
- `UNCERTAIN_ZERO_VOLUME_NONFLAT`: volume == 0 but H/L/C are not flat.
- `UNCERTAIN_VOLUME_MISSING`: canonical row exists but volume is unavailable/non-finite.
- `UNCERTAIN_CANONICAL_ROW_MISSING`: canonical daily row is absent.

A missing TradingView session is then classified as:

- `TRUE_TV_MISS_ACTIVE` for canonical-active sessions;
- `EXPLAINED_NO_TRADE` for canonical zero-volume flat sessions;
- `UNCERTAIN_MISSING_ACTIVITY` for unresolved canonical activity evidence.

The diagnostic computes activity-aware coverage only over canonical-positive-volume
sessions and a conservative lower bound that treats unresolved missing sessions as
potentially active. The prior 90% coverage threshold is reused only as contextual
diagnostic reference; it does not retroactively change the frozen admission gate.

## Implementation

New files on branch `data/tradingview-intraday-activity-forensics-v1`:

- `config/tradingview_intraday_activity_forensics_v1.json`
- `src/idx_trade/tradingview_activity_forensics.py`
- `scripts/run_tradingview_intraday_activity_forensics.py`

The runner verifies all frozen artifact hashes and canonical-panel SHA before reading
evidence, then writes `activity_support.csv`, `missing_session_forensics.csv`, and
`summary.json` to a new output root. It performs zero network/provider calls.

## Runtime blocker

The authoritative admission artifacts are explicitly external to Git at:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_intraday_admission_pilot_v1_20260814`

and the canonical panel used by the pilot is likewise a local external artifact.
Those bytes are not accessible through the GitHub connector/runtime available to
this ChatGPT session. Therefore the exact 198 missing ticker-session rows cannot be
classified here without fabricating evidence.

No numerical forensic result is claimed until the runner is executed against those
exact hash-pinned local inputs.

## Boundary

No provider calls, rerun of the frozen pilot, denominator mutation, bulk acquisition,
canonical panel write, feature/model work, Path Risk restart, O2 access, or protected
outcome access is authorized by this checkpoint.
