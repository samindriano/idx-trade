# V4 CA — ADRO Exact Entitlement Replay Prep

Date: 2026-08-18
Status: `PREPARED_NOT_YET_RUNTIME_VALIDATED`
Branch: `data/idx-v4-material-six-remediation-v1`

## Scope

This is a narrow continuation of the accepted material-six CA remediation. It targets only the frozen ADRO 2024 AAI/AADI PUPS Right Distribution event:

`41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58`

No model fit, target/rank materialization, performance computation, protected-forward access, price inference, universe waiver, or KSEI recrawl is authorized.

## Why this is different from the rejected inferred-date attempt

The earlier ADRO attempt was correctly rejected because it tried to infer a transition from KSEI Record/Distribution dates. That remains forbidden.

The new path uses two issuer-official AlamTri documents and an exact entitlement identity:

1. **PUPS Prospectus, 29 Nov 2024**
   - official URL: `https://www.alamtri.com/files/news/berkas_eng/2309/Prospektus%20PUPS%20Alamtri.pdf`
   - defines PUPS participation as the Company's shareholders who obtain the dividend pursuant to the 18 Nov 2024 EGMS decision;
   - states the exact PUPS ratio 4,389 ADRO shares -> 1,000 Purchase Rights;
   - states the 29 Nov 2024 PUPS recording date.

2. **2024 EGMS Summary Minutes, published 20 Nov 2024**
   - official URL: `https://www.alamtri.com/files/news/berkas_eng/2307/ADRO-Ringkasan%20Risalah%20RUPSLB%20181124-English.pdf`
   - gives the distribution schedule for the additional final cash dividend approved at the 18 Nov 2024 EGMS;
   - explicitly states for Regular and Negotiated Market: Cum Dividend = 26 Nov 2024 and Ex Dividend = 28 Nov 2024;
   - states Record Date = 29 Nov 2024.

Therefore the proposed 28 Nov 2024 boundary is **not** derived from the record date. The prospectus directly binds PUPS participation to the dividend entitlement, while the official EGMS minutes explicitly name that entitlement's Regular/Negotiated Market Ex Date.

## Frozen acceptance rule

ADRO may be promoted from `SCHEDULE_REQUIRED` to `EXACT_TRANSITION` only when all of the following hold:

- exact frozen event ID above;
- ticker `ADRO`;
- source type `Right Distribution`;
- status `Active`;
- Cum Date remains blank;
- Record Date exactly `2024-11-29`;
- Distribution Date exactly `2024-12-02`;
- ratio exactly `4389 ADRO : 1000 ADRO-H`;
- both official PDFs are freshly downloaded and their required text is verified;
- the accepted transition is exactly `2024-11-28`.

Any near miss remains fail-closed.

## Replay parent

The runtime must consume the successful material-six 611 artifact root:

`D:\Documents\Project\idx-v4-ca-material-six-remediation-20260818-v4`

Pinned parent manifest SHA-256:

`c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c`

Pinned parent properties:

- 611 frozen support tickers;
- 345,394 H5/H10 rows;
- 601 KSEI coverage-certified tickers;
- aggregate continuity certified;
- zero cross-source conflicts;
- AVIA, SMAR, and SCMA resolved in the material-six lane;
- FREN restored to support but still coverage-unresolved;
- ADRO still schedule-required before this replay.

## Runtime design

`scripts/run_v4_ca_adro_entitlement_replay.py`

The runner:

- verifies exact parent artifact hashes;
- makes **zero KSEI/provider calls**;
- downloads only the two issuer-official AlamTri PDFs;
- applies the exact cross-document entitlement classifier to ADRO only;
- preserves the accepted FREN/MEGA/SMAR/SCMA material-six semantics;
- replays the unchanged 90% per-date continuity gate;
- writes a separate ADRO overlay and manifest.

A proven transition does not automatically resolve windows crossing 28 Nov 2024. Such windows must remain `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`; entry on the transition date remains post-event basis under the frozen policy.
