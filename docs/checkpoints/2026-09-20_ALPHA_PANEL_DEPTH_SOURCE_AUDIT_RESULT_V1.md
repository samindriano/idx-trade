# Alpha available-data lane — panel-depth source audit result v1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Scope: read-only source capability and provenance audit; no feature construction,
candidate creation, model fitting, outcome access, provider/network access, or
canonical/active-data mutation.

## Result

The local `panel-depth` archive is structurally coherent enough for a source
capability record, but it is not admitted as a PIT-safe feature source.

`PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

The audited manifest is `20260919T035510Z`. It contains 12 symbols and 18,835
normalized rows: 1,616 rows for each of 11 symbols and 1,059 rows for GOTO.
The long histories run from 2020-01-02 through 2026-09-18; GOTO starts on
2022-04-11. Dates are valid, unique, and descending within each symbol.

## Structural checks

- All required OHLCV, bid/offer, listed-share, and foreign buy/sell fields are
  present.
- Foreign-share and foreign-value net arithmetic is exact on every row.
- `high >= low` and positive `bid <= offer` invariants hold.
- All 12 raw responses match their declared hashes and byte lengths.
- Official IDX snapshot parity is exact for all 23 available symbol/date pairs
  across 2020-01-02 and 2026-09-18. The only unavailable comparison is GOTO on
  2020-01-02 because the local history starts after that listing date.
- The normalized BBCA rowset is an exact duplicate of the existing
  historical-depth BBCA rowset (1,616-row intersection); it is not an
  independent source surface.

The official-date comparison is a structural cross-check only. It does not
establish historical publication time, revision/vintage behavior, or
point-in-time feature availability.

## Admission blockers

The normalized rows do not carry row-level code/name fields; identity is only
available at the top-level/file scope. No row-level `available_at`, knowledge
time, publication timestamp, revision, vintage, ISIN, issuer-transition, or
corporate-action fields were present. The manifest `observed_at` is capture
metadata, not proof that the values were available for a historical prediction.
The archive therefore cannot be promoted into the feature or candidate lane.

No feature, ranking, target, return, IC/OOS evaluation, C5, or model status was
created or changed.

## Reproducibility artifacts

Staged under:
`D:/Documents/Project/idx-alpha-available-data-staging-20260919/stage-a-final-guarded/20260919T-finalized-guarded/`

| Artifact | SHA-256 |
|---|---|
| `alpha_panel_depth_source_audit_v1_v3.json` | `6248fb5051c3baeac60cf0eb920423488fde79faca78aa4b378f81dcd9e71c3c` |
| `alpha_panel_depth_source_audit_v1_v3_verification.json` | `069331274e9cab5d8b68dd5f112b375a4c63bd3114c0059ed82cb8d8bc34e0fd` |
| `alpha_panel_depth_source_audit_v1_v3_hash_contract_rerun.json` | `540b10ee868b7277d586af7a9d9cb371075af528bf53e680ba8e43cd85779b83` |
| `alpha_panel_depth_source_audit_v1_v3_firewall.json` | `9d4391023465db26a90ac07c26b3169830ad2a8e5394d05ddfb143cf5ee23cee` |
| `alpha_panel_depth_source_audit_v1.py` | `973ba4a8fe2f9062f2169cab5e1d4070395eca8b1fcf0d6b81a9f3100e0bc31a` |
| `verify_alpha_panel_depth_source_audit_v1.py` | `6cfe6ba912326ce1a72c5152fe6cc2f16de03f39daae8d1886d184245a3dfb04` |

The firewall result is `PASS`; the artifact contract rerun and structural
verifier also pass. The displayed firewall digest is recorded from the staged
file and must be treated as the immutable lane reference.

## Safe continuation

The next useful step is a separate audit of any newly available authoritative
row-level PIT, identity, corporate-action, and revision metadata. Reusing the
duplicated BBCA surface or manufacturing PIT semantics from capture timestamps
is not authorized. The incumbent alpha, protected packet, canonical datasets,
capture/cloud/telemetry state, and active model lane remain unchanged.
