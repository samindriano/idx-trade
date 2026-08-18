# V4 CA — Material-Six Final Closure

Date: 2026-08-18
Status: `MATERIAL_SIX_6_OF_6_CLOSED`
Lane: `data/idx-v4-material-six-remediation-v1`

## Verdict

The frozen V4 corporate-action material-six remediation scope is now closed six-for-six:

- AVIA — resolved
- SMAR — resolved
- SCMA — resolved; 2026-08-10 candidate is acquisition-halo-only after the frozen target period
- MEGA — resolved exact bonus-share transition; zero frozen target-window rows
- ADRO — resolved exact issuer-official entitlement/ex-date transition on 2024-11-28
- FREN — resolved with exact official KSEI PMHMETD V ex-right transition on 2024-04-17 plus the already accepted 2025-04-16 merger/security-cessation transition

This is a scope-level material-six closure. It does **not** claim complete 611/611 KSEI coverage.

## Final frozen continuity gate

Final FREN replay status: `V4_CA_FREN_KSEI_EXACT_REPLAY_COMPLETE`.

- corporate action continuity certified: `true`
- verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`
- frozen dates: `600`
- frozen rows: `345394`
- frozen tickers: `611`
- coverage certified tickers: `602`
- coverage unresolved tickers: `9`
- cross-source conflict tickers: `0`
- H5 gate dates: `600/600`
- H10 gate dates: `600/600`
- consensus gate dates: `600/600`
- H5 minimum continuity rate: `0.9134615384615384`
- H10 minimum continuity rate: `0.9102564102564102`
- consensus minimum continuity rate: `0.9102564102564102`

The remaining nine coverage gaps are outside the material-six remediation set. They do not invalidate the frozen >=90% V4 continuity gate.

## Final FREN evidence

Official KSEI Rights Distribution schedule:

- reference: `KSEI-7000/JKU/0424`
- PDF SHA-256: `5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91`
- Cum Right Regular/Negotiated Market: `2024-04-16`
- Ex Right Regular/Negotiated Market: `2024-04-17`
- Record Date: `2024-04-18`
- distribution: `2024-04-19`
- trading period: `2024-04-22` through `2024-05-06`
- ratio: `178 old shares : 75 HMETD`

The accepted transition is the explicit official Regular/Negotiated Market ex-right date. No record-date subtraction is used.

## Final artifact provenance

External final FREN root:

`D:\\Documents\\Project\\idx-v4-ca-fren-ksei-exact-20260818-v1`

Pinned final hashes:

- FREN final replay manifest: `6cb1e660c6baa2d9b7a7aca5cece66691d5cd9564378104b618eed2cfce610ab`
- FREN attestation: `1876d19b73dfea6ba3eb9667e1bea3aadc7f770a75a96489f3fb1d8d3671ad36`
- final continuity summary: `b6cdf8eb47ac1020707f4fbb4e45cbebf962876b1350d82e352b086bea0709e1`
- final continuity ledger: `bce52718fd2731142d84bbeb51beae93147746e2150015a36644dd98dcaee5bf`
- event semantics audit: `c501943897d26cf1a580e6fa9275b39711e65ea0564c04f9d687ee189619784f`
- per-date artifact: `c84210982a0945dea1b6609e120f8768592ad8b558ad4d12d4bcb29e3dafdfee`
- final mixed coverage: `954a270be85722a408c41c535077df0ab58dfadb656d4fa86b7dc9df370788ed`

Parent lineage:

- material-six parent manifest: `c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c`
- ADRO exact-entitlement parent manifest: `8a952e0e94ed2b99a7fb3f6bcfb60d30e8be7df928f1bad6f8f9d46a01a600c9`

## Guardrails preserved

- no model fit
- no historical V4 target/rank materialization
- no V4 prediction generation
- no performance computation
- no protected-forward access
- no price-jump inference
- no record-date fallback
- no EXCL price stitching

## Downstream implication

The previously explicit V4-3 pre-fit Corporate Action blocker is now satisfied on the frozen 600-date support. The next authorized engineering step is a fail-closed V4-3 Corporate Action admission bridge that pins this final continuity evidence to the already frozen V4-3 prefit/runtime/execution lineage before first historical target/model access.
