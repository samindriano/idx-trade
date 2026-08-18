# V4 CA — FREN KSEI Exact Replay Result

Date: 2026-08-18
Status: `V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE`
Lane: `data/idx-v4-material-six-remediation-v1`

## Verdict

The remaining FREN material-six blocker is resolved on the frozen V4 corporate-action support.

The 2024 PMHMETD V transition is proven directly by an official KSEI Rights Distribution schedule. The accepted transition is the explicit Regular/Negotiated Market ex-right date, not a date inferred from record/distribution timing.

The already accepted 2025 merger/security-cessation transition remains unchanged.

Final FREN coverage status: `CERTIFIED` under the disclosed mixed archival census method:

`ISSUER_OFFICIAL_ARCHIVE_MECHANICAL_CENSUS_PLUS_KSEI_OFFICIAL_RIGHTS_SCHEDULE`

The legacy static KSEI registered-security page was **not** recovered and is not represented as recovered.

## Final official FREN rights evidence

Official KSEI April-2024 Rights Distribution archive index:

- index SHA-256: `b53cfa79bece2d989019c5b00f1f6df8fb80f970022911977e3f6de4994093aa`

Pinned official KSEI schedule PDF:

- reference: `KSEI-7000/JKU/0424`
- URL: `https://web.ksei.co.id/Announcement/Files/165545_ksei_7000_jku_0424_202404041510.pdf`
- SHA-256: `5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91`

Explicit schedule semantics reverified offline from the pinned PDF:

- Cum Right — Regular/Negotiated Market: `2024-04-16`
- **Ex Right — Regular/Negotiated Market: `2024-04-17`**
- Record Date: `2024-04-18`
- Rights Distribution: `2024-04-19`
- rights trading start: `2024-04-22`
- rights trading end: `2024-05-06`
- ratio: `178 old shares : 75 HMETD`
- transition source: `OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE`

No subtraction from Record Date or Distribution Date is used.

## FREN exact event semantics

### PMHMETD V

- family: `RIGHT_DISTRIBUTION_PMHMETD_V`
- semantic class: `EXACT_TRANSITION`
- transition date: `2024-04-17`
- transition source: `OFFICIAL_KSEI_REGULAR_NEGOTIATED_MARKET_EX_RIGHT_DATE`
- reason: `EXACT_FREN_PMHMETD_V_KSEI_EX_RIGHT_2024-04-17_NO_RECORD_DATE_INFERENCE`
- event ID: `7e2b98fd84d7b0b518622ff70a407b8fab85d6754b717afcb1817b9500cf72f8`

### Merger/security cessation

- family: `MERGER_OR_RESTRUCTURING`
- semantic class: `EXACT_TRANSITION`
- transition date: `2025-04-16`
- transition source: `OFFICIAL_ISSUER_MATERIAL_DISCLOSURE`
- reason: `SMARTFREN_CEASES_BY_OPERATION_OF_LAW_NO_EXCL_PRICE_STITCHING`
- event ID: `286ab82349a4c6ffd6687c944e5731693f6a43789aa34385a1728a5cfff1499b`

## FREN window result

Frozen FREN support is preserved exactly:

- FREN window rows: `604`
- resolved rows: `578`
- mechanically crossing rows: `26`
- PMHMETD V crossing rows: `13`
- merger crossing rows: `13`
- resolved rate: `0.956953642384106`

The 26 crossing rows correctly remain fail-closed as `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`. Exact-event resolution does not waive a target interval that genuinely spans a price-basis transition.

## Final 611-ticker continuity replay

- verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`
- corporate action continuity certified: `true`
- frozen tickers: `611`
- frozen dates: `600`
- frozen rows: `345394`
- coverage certified tickers: `602`
- coverage unresolved tickers: `9`
- cross-source conflicts: `0`
- event rows relevant to study: `85`
- `EXACT_TRANSITION` events: `53`
- `SCHEDULE_REQUIRED` events: `32`
- schedule-required tickers: `28`

Per-date gate:

- H5: `600/600`, minimum rate `0.9134615384615384`
- H10: `600/600`, minimum rate `0.9102564102564102`
- consensus: `600/600`, minimum rate `0.9102564102564102`

Continuity status counts:

- `RESOLVED_NO_MECHANICAL_DISCONTINUITY`: `324954`
- `PRICE_CONTINUITY_UNRESOLVED_EFFECTIVE_DATE`: `16184`
- `PRICE_CONTINUITY_UNRESOLVED_COVERAGE`: `4256`

The remaining nine coverage gaps are outside the frozen material-six remediation set. This result therefore closes FREN/material-six but does **not** claim `611/611` KSEI coverage.

## Final artifact provenance

External final artifact root:

`D:\Documents\Project\idx-v4-ca-fren-ksei-exact-20260818-v1`

Final hashes:

- final replay manifest SHA-256: `6cb1e660c6baa2d9b7a7aca5cece66691d5cd9564378104b618eed2cfce610ab`
- attestation SHA-256: `1876d19b73dfea6ba3eb9667e1bea3aadc7f770a75a96489f3fb1d8d3671ad36`
- census manifest SHA-256: `adefbc35a56e05a555b681acbd780fb9c5fad30621f8fa8ba04afd5efd836df8`
- final continuity summary SHA-256: `b6cdf8eb47ac1020707f4fbb4e45cbebf962876b1350d82e352b086bea0709e1`
- continuity window SHA-256: `bce52718fd2731142d84bbeb51beae93147746e2150015a36644dd98dcaee5bf`
- event semantics audit SHA-256: `c501943897d26cf1a580e6fa9275b39711e65ea0564c04f9d687ee189619784f`
- per-date SHA-256: `c84210982a0945dea1b6609e120f8768592ad8b558ad4d12d4bcb29e3dafdfee`
- schedule-evidence-needs SHA-256: `8a5d5fc7301360f9f62d6d64ae0cafe22447fed9eab4053f3334757cbc5b5892`
- final mixed coverage SHA-256: `954a270be85722a408c41c535077df0ab58dfadb656d4fa86b7dc9df370788ed`
- inherited KSEI history SHA-256: `4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d`
- official calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- frozen continuity ledger input SHA-256: `5139cbb39e34fd46b6214435b1bc6bb937ec1e5400ec268376e412bdd2225426`
- prior event evidence SHA-256: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

Parent lineage:

- material-six parent manifest SHA-256: `c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c`
- ADRO exact-entitlement parent manifest SHA-256: `8a952e0e94ed2b99a7fb3f6bcfb60d30e8be7df928f1bad6f8f9d46a01a600c9`

## Validation

Immediately before the successful runtime, the focused final suites passed:

`26 passed`

covering:

- KSEI schedule exact semantics,
- offline replay contract,
- original FREN archive semantics,
- ADRO entitlement semantics,
- bilingual `Mei` / `May` representation for the exact trading-end date while retaining fail-closed behavior when that date is absent.

## Guardrails preserved

- outcome-blind: `true`
- offline final replay: `true`
- network calls in final replay: `false`
- provider calls: `false`
- model fit: `false`
- performance computed: `false`
- prediction generated: `false`
- target/rank materialized: `false`
- protected-forward accessed: `false`
- price inference: `false`
- record-date inference: `false`
- EXCL price stitching: `false`

## Scientific conclusion

FREN is no longer a material-six coverage blocker. The April-2024 rights transition and April-2025 merger transition are both exact, source-pinned mechanical boundaries, and the frozen 611-ticker continuity gate remains certified after adding them.

This closes the final unresolved name in the material-six scope. See the companion material-six final-closure checkpoint for the six-name scope-level conclusion.
