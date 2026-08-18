# V4 CA — ADRO Exact Entitlement Replay Result

Date: 2026-08-18
Status: `ADRO_EXACT_TRANSITION_RESOLVED`
Lane: `data/idx-v4-material-six-remediation-v1`

## Verdict

The previously unresolved ADRO 2024 AAI/AADI PUPS-related Right Distribution event is now resolved to an exact transition date using issuer-official cross-document entitlement evidence.

- Frozen event ID: `41c1e8493213d0151799837330c0dc7d8fea633d458c03e40b61ea0247bb9e58`
- Semantic class: `EXACT_TRANSITION`
- Transition date: `2024-11-28`
- Transition source: `OFFICIAL_ISSUER_CROSS_DOCUMENT_ENTITLEMENT_EX_DATE`
- Family: `RIGHT_DISTRIBUTION_AAI_PUPS`
- No record-date fallback
- No distribution-date fallback
- No price inference
- KSEI provider calls in this replay: `false`
- Outcome-blind: `true`

## Official evidence

Two issuer-official AlamTri documents were downloaded and SHA-pinned during the replay:

1. PUPS prospectus
   - URL: `https://www.alamtri.com/files/news/berkas_eng/2309/Prospektus%20PUPS%20Alamtri.pdf`
   - SHA-256: `ed40b6da5ca4df1f07a8d0e9d3855b1097ab1faaecd6783435e79633fec40300`
   - bytes: `990555`

2. 18-Nov-2024 EGMS minutes
   - URL: `https://www.alamtri.com/files/news/berkas_eng/2307/ADRO-Ringkasan%20Risalah%20RUPSLB%20181124-English.pdf`
   - SHA-256: `23b5636f69d0fee55f9af761d4c0d9e66c31e8d062e5f885f8cf2d53f944109c`
   - bytes: `211464`

The accepted linkage is:

`PUPS participant set / shareholder-record identity -> 2024-11-18 EGMS dividend entitlement -> issuer-official Regular & Negotiated Market Ex Dividend date 2024-11-28`.

This replaces the earlier unresolved state. The date is not inferred from KSEI record/distribution dates.

## ADRO window result

- ADRO target-window rows: `1200`
- resolved rows: `1187`
- resolved rate: `0.9891666666666666`
- rows that cross the exact transition and remain mechanically blocked: `13`

The 13 crossing rows are expected and important: exact-event resolution does not waive windows that genuinely span a mechanical corporate-action basis transition.

## 611-ticker continuity replay

The full frozen support remains certified:

- frozen tickers: `611`
- frozen rows: `345394`
- coverage certified tickers: `601`
- coverage unresolved tickers: `10`
- cross-source conflicts: `0`
- event rows relevant to study: `84`
- exact-transition events: `52`
- schedule-required events: `32`
- schedule-required tickers: `28`

Per-date gate:

- H5: `600/600`, minimum rate `0.9134615384615384`
- H10: `600/600`, minimum rate `0.9102564102564102`
- Consensus: `600/600`, minimum rate `0.9102564102564102`

Verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`

## Provenance

- Parent material-six manifest SHA-256: `c26b9e60f17b181016cd2ee4c30720ef4a4323b82603a5a0c9c01ea0fd175a4c`
- ADRO replay manifest SHA-256: `8a952e0e94ed2b99a7fb3f6bcfb60d30e8be7df928f1bad6f8f9d46a01a600c9`
- Final continuity summary SHA-256: `b28bb822d6bda32440a4e4790045d1b1535cbb0285dcd4a244369baff3d7aa6a`
- Continuity ledger SHA-256: `09bc20f19c0dcf557da00490d734e5a6bcd423dd218b5e6fad642a4576ccf675`
- Event semantics audit SHA-256: `0c8adf01339ea6ae5b505b02c24200c65750e0f5af680e480bccde177d03c6fc`
- Per-date SHA-256: `e6aeed8fc1c4ee9f8a1abc94d667b7f2e10799f422e929f779e586b2158a4f8c`

## Material-six status after ADRO replay

- AVIA: resolved
- SMAR: resolved
- SCMA: resolved
- MEGA: resolved (zero frozen target-window rows)
- ADRO: **resolved exact transition**
- FREN: still coverage-unresolved; exact merger boundary is known but complete KSEI registered-security history remains uncertified

Therefore the only remaining unresolved name from the material-six remediation set is FREN.

## Guardrails preserved

- No model fit
- No performance computation
- No predictions
- No target/rank materialization
- No protected-forward access
- No price inference
- No source substitution
- Missing schedules outside this exact ADRO evidence remain fail-closed
