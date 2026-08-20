# V4-X Clean-Data Consolidation V1 — Stage-A Result

Date: 2026-08-20 (Asia/Jakarta)  
Branch: `data/v4-x-clean-data-consolidation-v1`  
Runtime status: `STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION`

## Result

One authorized local Stage-A runtime completed successfully against the frozen
local artifacts. The Stage-A candidate preserves the exact parent population:
`981,940` rows and `945` tickers. `identity_preserved=true` and
`universe_repair_performed=false`.

H/L/C consolidation:

- repaired rows: `1,657`
- repaired tickers: `12`
- policy: accepted H/L/C overlay only

Open consolidation:

- total repaired rows: `1,655`
- official `IDX_OFFICIAL_OPENPRICE`: `1,216`
- CA-factor fallback `CA_FACTOR_RECONSTRUCTION`: `439`
- fail-closed unavailable candidates: `2`
- no other missing Open was filled

Integrity/parity verdicts:

- H/L/C accepted overlay: PASS
- Volume parity: PASS; unchanged from parent
- Regular-Market Value parity: PASS; unchanged from parent
- other parent fields: PASS; unchanged
- parent row/ticker identity: PASS
- identity/universe repair: NOT PERFORMED

## Frozen input hashes

| Input | SHA-256 |
|---|---|
| panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| HLC remediation manifest | `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278` |
| Open remediation manifest | `753d5470bd240bbf6158142bc5a2b339cea96f83cfb7451c5e18fc10cf5f060f` |
| official-integrity manifest | `bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016` |
| Regular-Market Value audit manifest | `e7147f9f378d8c05ed5307e9c0fd92c29a8465221207e2484001a7772c8d8f37` |
| consolidation config | `f7c68b29483cc9ccd22b08f1e5da67a5bc746bc0edd8851d3d392c111dc960b0` |

## External artifacts

Root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

| Artifact | SHA-256 |
|---|---|
| `MANIFEST.json` | `eaeabad3c2050142d973d3f8ec350934b995b4e890ea4a12588304d325073969` |
| `summary.json` | `28c61dfa6ae6c145a2186e8b8f197038e019d48fad469e958a18cbd74ee8c7fc` |
| clean Stage-A panel parquet | `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e` |
| provenance sidecar parquet | `cc6d66b3429c3b9f4c66d7120706bfd96c22b6d1d3ed7c2da567899cccf95c28` |
| provenance sidecar CSV | `91cf615a9ab533a1478fbc1aecc5084341647070d091d85d5a7ee53a2ad4ccf3` |
| correction ledger CSV | `6f883aaae54b3180bc3c38a2836b88b9cb983ed215dbb61246329a869138e125` |

## Guardrails

All frozen guardrails are false: no provider calls, model fit/score/tuning,
target/outcome access, protected/fresh-forward access, parent overwrite,
calendar/session change, volume/value repair, universe repair, primary-
liquidity change, forward-counter mutation, or V4-X2 execution.

The final clean input and model refit remain unauthorized. The next boundary
is independent PIT Security Identity / Listing-Domain adjudication before any
final clean-universe manifest or refit.

## Validation

- Focused: `python -m pytest -q tests/test_v4_x_clean_data_consolidation.py` → `8 passed`.
- Implementation-only fixes: none.
- Stage B/refit: not run.
