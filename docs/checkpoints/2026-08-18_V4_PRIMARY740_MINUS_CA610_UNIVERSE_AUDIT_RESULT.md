# V4 primary-liquid 740 -> CA-support 610 universe audit — result

Date: 2026-08-18 (Asia/Jakarta)
Branch: `data/idx-v4-ca-targeted-schedule-evidence-v1`
Status: `V4_PRIMARY740_MINUS_CA610_AUDIT_COMPLETE`

## Boundary

Outcome-blind universe completeness audit only. No target/rank materialization, model fit, prediction generation, performance computation, protected-forward access, or provider calls.

## Frozen identities

- historical primary-liquid union: **740 tickers**
- frozen CA-support ledger: **610 tickers**
- exact set difference: **130 tickers**
- frozen validation dates: **600**
- validation window: **2023-12-28 through 2026-07-17**
- continuity ledger SHA-256: `52ce3f172e126363b6c51b57fbcaf5551a4e2b0217f120e4b01e6ae0d75497eb`
- primary signal panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- audit manifest SHA-256: `c4d0d1b3c07707e0da6a4c931b3fa9724a3e80fe3f4b8f984545e22ba27ea36f`

## Exact absence classes

- `ACTIVE_OR_PRESENT_2026_BUT_NOT_PRIMARY_LIQUID_ON_VALIDATION`: **109**
- `HISTORICAL_PRIMARY_LIQUID_ONLY_BEFORE_2026`: **20**
- `POTENTIAL_CA_SUPPORT_DATA_GAP`: **1** (`FREN`)

Presence diagnostics:

- exact 2026 ACTIVE tradability anchor: **98**
- present in 2026 signal panel but status not proven: **11**
- no 2026 signal-panel rows: **21**

The only ticker in the 740-minus-610 set that had primary-liquid rows on the frozen 600 validation dates yet no CA-support representation is **FREN**. It must not be silently reclassified as benign; it remains the one exact potential CA-support/data-lineage gap from this audit.

All 109 other 2026-present names had zero primary-liquid rows on the frozen validation dates. Therefore their absence from the 610 CA support is explained by the frozen primary-liquidity universe contract rather than by a missing CA-support row.

## Security-master limitation found

The security master exposed columns `listed_from` and `listed_to`, while the audit's generic detector did not recognize those exact column names in this run. Therefore the runtime correctly distinguishes 2026 panel/anchor presence, but does **not** yet claim exact `DELISTED_BY_FROZEN_END` identities from security-master `listed_to`.

Until the detector is remediated and rerun, use the label `HISTORICAL_ONLY_NO_2026_PANEL_ROWS` rather than converting all such names to `DELISTED`.

## Scientific consequence

The 740 -> 610 difference does **not** reveal a broad hidden exclusion bug. It reveals one exact potential support gap (`FREN`) plus names that were historical primary-liquid but were not primary-liquid on the frozen validation support.

This does not change the already certified aggregate CA continuity verdict. It also does not resolve ticker-level technical debt already known inside the 610 support (for example ADRO spin-off semantics, KSEI coverage gaps, and cross-source conflicts).
