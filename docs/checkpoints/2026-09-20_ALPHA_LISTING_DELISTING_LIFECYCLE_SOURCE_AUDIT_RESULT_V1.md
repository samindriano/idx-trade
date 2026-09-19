# Listing / Delisting Lifecycle Source Audit Result V1

Status: `PASS_STRUCTURAL_ONLY / SOURCE_ADMISSION_BLOCKED`

This is a read-only, outcome-blind audit of the explicitly persisted IDX
listing/delisting acquisition. It does not call the provider, open targets or
outcomes, mutate canonical data, repair lifecycle rows, or create a feature or
candidate.

## Structural evidence

- The acquisition summary covers 440 monthly requests from 1990 through
  2026-08-31, with zero recorded request errors.
- The current-listing CSV contains 962 rows and 962 unique ticker keys.
- The delisting CSV contains 163 rows across 159 ticker keys.
- All 440 monthly raw JSON files are present, status 200, and match their
  declared byte counts and SHA-256 values.
- All monthly JSON payloads parse, their `data` counts match both `rows` and
  `totalItems`, and all rows expose the expected code/name/listing/delisting
  fields.
- The 163 normalized delisting rows match the monthly raw payloads exactly as
  a multiset of ticker, company, listing date, delisting date, and source
  reference. All source references and per-row raw-source hashes match.
- Current-listing dates and delisting dates parse without invalid values, and
  all current-row provenance hashes match the source hash recorded in the
  acquisition summary.

The raw/normalized source integrity gates are therefore PASS. This does not
make the lifecycle source PIT-admissible.

## Lifecycle and PIT limitations

- The persisted source is event-level listing/delisting evidence, not a daily
  point-in-time membership panel.
- No issuer/ISIN transition chain, publication-time or available-at field,
  revision/vintage field, or corporate-action linkage is present.
- Six ticker-level conflicts remain in the official-derived conflict artifact:
  `BUKK`, `INRU`, `ITMA`, `KIAS`, `SKBM`, and `UNTX`.
- The independent interval checks find one delisting-before-listing row,
  12 rows participating in overlapping intervals, and 13 rows participating in
  same-listing-date conflicts. The retained price-lifecycle summary records
  15 conflict rows and 2,280 ambiguous price rows across five price tickers;
  the differing counts reflect distinct row scopes in the two artifacts.
- Two nonstandard-code rows (`MAMIP`, `MYRXP`) are explicitly excluded by the
  local acquisition artifact.

These are semantic admission blockers, not silently repairable data errors.
No relisting interpretation, issuer continuity, effective date, or daily
membership state was inferred.

## Decision

The source is useful as a future lifecycle capability inventory and as a
bounded forensic reference. It remains `PARTIAL / IDENTITY_BLOCKED` and is not
admitted for feature construction, universe masking, candidate evaluation,
corporate-action repair, or protected-packet expansion. The next decision-
changing evidence would be an independently admitted population-wide daily
membership source with issuer/ISIN continuity, effective/publication timing,
revision lineage, and corporate-action linkage.

## Artifact provenance

- Acquisition summary SHA-256: `ced02fe566be97b68d100ece6a217a8a7a6fe203ed6ea618b1503d956d80c00c`
- Monthly metadata SHA-256: `93d525f2111fccac4009d2054f2059dac2f685d1e4910497fc05258b60aa58d0`
- Current records file SHA-256: `6d6a7ae8f4ebeaa24426429d255f171462b650aceb36100d6f983cd5d6ea8624`
- Delisting records file SHA-256: `7d1db5e2e73c9af9d2b26fe50c913a88efa1adfc326ced6f1c78827901e26c40`
- Conflict artifact SHA-256: `83cdd9e2d6b218c711dc346feb40d0bca99dfa6e635c0376a34a835c6b3d1837`
- Excluded-code artifact SHA-256: `dc5168bfc834a6f94797f0397835c6ded028b4226127d1a9afdb74a4d5f37a5a`
- Price-lifecycle summary SHA-256: `4cfe1a41358be1cd78285efea125f9245d07a8d738b3658eab117eec4b3b5f8e`
- Audit JSON SHA-256: `5147d4ab86ae3c3429c50c6b490bad908f1677f567fe73ac2d87ec0e34a14b03`
- Independent verification JSON SHA-256: `51762bb9187b46cff039c13c063baf5a8d6dc49c5e2ff493491968d2e2d27e51`
- Hash-contract JSON SHA-256: `a3b259f0efe693f9c828640832a7404d1d2b131fb4ac1ede158b8ef700cf6f7f`
- Builder SHA-256: `d5d3b7262a2cc0337ea4800f6fb724d8a6f9b002ed10e5fce6274c9310f02b6f`
- Independent verifier SHA-256: `a5b652697d722eae0110fdfaef456c5fa311d01fef2fd9715c71c29ef328dc72`

The independent verifier, generic hash contract, and outcome-blind target
firewall all returned `PASS`. No network, provider, credential, cloud,
target, outcome, incumbent, canonical, or production state was accessed or
modified.
