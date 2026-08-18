# V4 CA — FREN Official Archive Replay Prep

Date: 2026-08-18
Status: `FROZEN_READY_FOR_ONE_SHOT_RUNTIME`
Lane: `data/idx-v4-material-six-remediation-v1`

## Problem

FREN was restored to the frozen CA support (302 validation signal rows / 604 H5+H10 rows), and its merger/security-cessation boundary is already exact at 2025-04-16. However, the legacy FREN static KSEI registered-security page no longer yields a certifiable FREN history after the merger, so FREN remains coverage-unresolved.

This lane does **not** pretend that static source recovered.

## New evidence found

Primary official archives show an additional mechanical event inside FREN's frozen support period:

1. PMHMETD V / Rights Issue V in April 2024.
   - KSEI official record-date reminder identifies FREN `Distribusi Right/ Efek` on 2024-04-18.
   - KSEI official distribution reminder identifies FREN `Distribusi Right/ Efek` on 2024-04-19.
   - Smartfren's official 2024 Corporate Action archive contains `Prospektus PMHMETD V PT Smartfren Telecom Tbk` as the 2024 mechanical corporate-action item.
   - Smartfren's official 2024 disclosure archive contains `Perubahan Jadwal PMHMETD V`, `Informasi Tambahan PMHMETD V FREN`, and `Prospektus Ringkas PMHMETD V FREN`.
   - The runtime must discover/download an issuer-official PDF and prove the Regular/Negotiated Market ex-right date explicitly. The expected date 2024-04-17 is not accepted from secondary media or from record-date subtraction.

2. Merger/security cessation on 2025-04-16.
   - already issuer-official and exact from the accepted material-six lane;
   - KSEI official reminders corroborate FREN Stock Split/Reverse/Amortization record processing and FREN Voluntary Conversion around the same boundary.

## Frozen admission method

FREN may change from `coverage_certified=false` to `true` only if all of the following pass in one run:

- issuer 2024 corporate-action archive identity passes;
- issuer 2024 PMHMETD disclosure-set identity passes;
- official KSEI FREN rights record/distribution identity passes;
- an issuer-official Smartfren PDF explicitly proves the Regular/Negotiated Market ex-right date;
- official issuer merger effective date remains 2025-04-16;
- official KSEI merger-processing identities pass;
- no additional mechanical family is visible in the frozen issuer 2024 Corporate Action archive;
- final FREN event audit contains exact transitions for both 2024-04-17 and 2025-04-16;
- windows genuinely crossing either transition remain blocked;
- all other FREN windows resolve without a coverage error.

The accepted provenance label is explicitly:

`ISSUER_OFFICIAL_ARCHIVE_PLUS_KSEI_EVENT_CORROBORATION`

This is a disclosed official archival source route. It is not represented as recovery of the old static KSEI registered-security page.

## Frozen parent artifacts

Material-six root expected:

`D:\Documents\Project\idx-v4-ca-material-six-remediation-20260818-v4`

- manifest SHA-256: `c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c`
- expanded 611 ledger SHA-256: `5139cbb39e34fd46b6214435b1bc6bb937ec1e5400ec268376e412bdd2225426`
- coverage SHA-256: `44f7b9e9f7e02e5f2dacaf27f5ded3aa1d41d4ce61664725db096f7a28a93081`
- history SHA-256: `4dcdd9e44cc40e348079c1447aa3e1e20427b000247be5be91b6622fb03e997d`

ADRO accepted root expected:

`D:\Documents\Project\idx-v4-ca-adro-exact-entitlement-20260818-v3`

- manifest SHA-256: `8a952e0e94ed2b99a7fb3f6bcfb60d30e8be7df928f1bad6f8f9d46a01a600c9`

The ADRO raw official documents are reused locally so no ADRO network acquisition is repeated.

## Expected scientific effect if accepted

- frozen universe remains exactly 611 tickers / 345,394 rows / 600 dates;
- FREN remains present; no universe exclusion;
- FREN coverage becomes certified through the disclosed official archival method;
- coverage certified count should become 602;
- unresolved coverage count should fall from 10 to 9;
- the 2024 rights and 2025 merger boundaries become exact mechanical transitions;
- crossing windows remain fail-closed;
- the unchanged 90% per-date gate is replayed.

No expected performance/model effect is specified or evaluated.

## Guardrails

- outcome blind;
- no model fit;
- no performance computation;
- no prediction;
- no target/rank materialization;
- no protected-forward access;
- no price inference;
- no record-date subtraction;
- no EXCL price stitching;
- no alternate commercial provider;
- failure to discover an issuer-official PDF with the exact ex-right schedule fails closed.
