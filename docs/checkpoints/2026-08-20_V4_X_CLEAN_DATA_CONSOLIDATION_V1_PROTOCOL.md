# V4-X Clean-Data Consolidation V1 — Frozen Protocol

Date: 2026-08-20 (Asia/Jakarta)
Branch: `data/v4-x-clean-data-consolidation-v1`
Status: `STAGE_A_PROTOCOL_FROZEN_WAITING_FOR_OFFLINE_RUNTIME`
Base main: `79d4d6c2a02eb3677aa8e1d90fa22eacbf2451b9`

## Scientific purpose

Materialize one explicit, auditable Stage-A clean-data candidate from the immutable frozen panel plus already accepted H/L/C and Open correction overlays. This stage is outcome-blind and does not finalize the clean universe while the independent PIT Security Identity / Listing-Domain Stage-C lane remains active.

The goal is to avoid repeated/silent repairs and make every changed field traceable. Stage A is not a model refit authorization.

## Frozen parent inputs

- Frozen panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- Official exchange calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.
- Accepted H/L/C remediation manifest SHA-256: `2eaba67111783c6dc690f56254d949bc1ad8a897053a0db18a2918e1122c8278`.
- Accepted Open remediation manifest SHA-256: `753d5470bd240bbf6158142bc5a2b339cea96f83cfb7451c5e18fc10cf5f060f`.
- Full-panel official-integrity audit manifest SHA-256: `bf87e0c8ce49468113eec32cb7df931ff0df887444de727a57c65b495d87c016`.
- Regular-Market Value audit manifest SHA-256: `e7147f9f378d8c05ed5307e9c0fd92c29a8465221207e2484001a7772c8d8f37`.

Expected parent population: `981,940` rows and `945` tickers.

## Accepted corrections admitted in Stage A

### H/L/C

Exactly `1,657` unique ticker-date rows across 12 tickers are replaced from the accepted `price_basis_hlc_overlay_v1.csv`.

Only `high`, `low`, and `close` may change through this overlay.

### Open

Exactly `1,655` unique ticker-date rows are replaced from the accepted `open_price_basis_overlay_v1.csv`.

The accepted Open policy is:

`IDX_OPENPRICE_PRIMARY_CA_FACTOR_FALLBACK_FAIL_CLOSED_V1`

Expected sources:

- 1,216 `IDX_OFFICIAL_OPENPRICE` rows;
- 439 `CA_FACTOR_RECONSTRUCTION` rows.

The two separately listed fail-closed Open candidates must remain unavailable (`NaN`) in the Stage-A output. They may not be synthesized or rescued. Stage A does not fill any other missing Open.

## Fields that must remain unchanged

Full-panel audits already exonerated `volume` and `regular_market_value`. Therefore Stage A must prove exact parent parity for both fields across the entire preserved parent row identity.

The official exchange calendar must remain byte-identical to its frozen parent; Stage A copies no calendar and changes no session identity.

All other non-H/L/C/Open panel columns must remain value-identical to the frozen parent.

## Identity and concurrent-lane boundary

The ACTIVE `audit/pit-security-identity-stage-c-v1` lane owns FREN/KOCI, listing-domain correctness, ticker inclusion/exclusion, universe repair, and exact V4-X training-support intersection.

Stage A therefore:

- keeps exactly the frozen parent ticker-date identities;
- does not add/drop rows or tickers;
- does not adjudicate FREN/KOCI;
- does not create final V4-X training support;
- emits status `STAGE_A_CONSOLIDATION_MATERIALIZED_WAITING_FOR_IDENTITY_ADJUDICATION` on success.

Only a later separately authorized Stage B may consume an independently accepted identity/universe artifact and freeze the final clean input + universe manifest shared by clean V4-X and V4-X2.

## Field-level provenance sidecar

Stage A must produce a separate provenance sidecar, one row per frozen panel ticker-date identity, containing at least:

- `ticker`, `date`;
- `high_source`, `low_source`, `close_source`;
- `open_source`;
- `volume_source`;
- `regular_market_value_source`;
- `hlc_repaired`, `open_repaired`, `open_fail_closed_candidate`;
- `consolidation_policy`.

Source semantics:

- H/L/C repaired rows: `IDX_PUBLIC_STOCK_SUMMARY_CERTIFIED_PRICE_BASIS_OVERLAY`;
- unchanged H/L/C rows: preserve/qualify the parent `price_provenance` as `PARENT:<value>`;
- admitted Open rows: use the accepted `open_remediation_source` (`IDX_OFFICIAL_OPENPRICE` or `CA_FACTOR_RECONSTRUCTION`);
- fail-closed Open candidates: `FAIL_CLOSED_UNAVAILABLE`;
- all other Open rows: `PARENT_UNCHANGED_OPEN_PROVENANCE_UNSPECIFIED` because the frozen panel did not carry field-specific Open provenance;
- Volume: `PARENT_UNCHANGED_OFFICIAL_IDX_PARITY_CERTIFIED`;
- Regular-Market Value: `PARENT_UNCHANGED_OFFICIAL_IDX_PARITY_CERTIFIED`.

This sidecar hardens lineage without rewriting exonerated values.

## Required validation

The runtime must hard-fail on:

- any parent/calendar/repair-manifest SHA mismatch;
- duplicate ticker-date identity in parent or either overlay;
- overlay identity absent from the frozen parent;
- unexpected repair counts or source counts;
- H/L/C overlay values that are non-finite/non-positive or violate `low <= close <= high`;
- admitted Open that is non-finite/non-positive or outside the post-HLC `[low, high]` envelope;
- fail-closed candidate whose Stage-A Open is finite after consolidation;
- any row/ticker count change;
- any change to `volume`, `regular_market_value`, or any parent column other than H/L/C/Open;
- any overlap inconsistency between accepted H/L/C and Open artifacts.

## Immutable output

Default external root:

`D:\Documents\Project\idx-trade-data-gate-20260808v\v4_x_clean_data_consolidation_v1_20260820`

The runner refuses to overwrite a non-empty output directory.

Expected outputs:

- `model_safe_signal_research_panel_1260_stage_a_clean_candidate.parquet`;
- `field_level_provenance_sidecar_v1.parquet` and CSV;
- `clean_data_correction_ledger_v1.csv`;
- `summary.json`;
- `MANIFEST.json`.

The manifest must hash every output and pin every parent input.

## Hard guardrails

- provider calls: false;
- model fit/scoring/tuning: false;
- target/return/rank access: false;
- protected/fresh-forward outcome access: false;
- parent panel overwrite: false;
- calendar change: false;
- volume/value repair: false;
- universe/listing-domain repair: false;
- feature/session-window semantics change: false;
- primary-liquidity rule change: false;
- forward counter mutation/reset: false.

## Next boundary

After Stage-A code + focused tests are independently validated and the offline runtime succeeds, stop with `WAITING_FOR_IDENTITY_ADJUDICATION` unless the concurrent Stage-C identity lane has already produced an independently accepted final artifact. Do not refit V4-X automatically.
