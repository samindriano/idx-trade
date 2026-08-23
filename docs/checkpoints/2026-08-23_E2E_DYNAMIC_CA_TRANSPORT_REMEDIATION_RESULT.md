# E2E Dynamic Corporate-Action Transport Remediation — Result

Date: 2026-08-23 (Asia/Jakarta)
Branch: `integration/idx-e2e-baseline-paper-v1`
Pre-remediation checkout: `91323a9509eda740a6f45294d81c5e0b02c4f34a`
Final pushed code commit: `511bf8f7c9992102445954164b7f7e4fea742436`
Provider checkout: `D:\Documents\Project\idx-bei-forward-ca-provider`
Provider commit: `75d6c0f74fa360d225794c70c383348977de6798`

## Verdict

`DYNAMIC_CA_REAL_TRANSPORT_VERIFIED_E2E_WEEKDAY_READY`

This is a bounded real-provider transport result, not a live PAPER execution.
The historical `POST_EOD` smoke for `BBCA`, session `2026-08-21`, completed
through the immutable phase manifest and V1.2 attestation without accessing
protected outcomes or mutating live PAPER state.

## Diagnosis

The prior anti-403 remediation was found in the V2/V2b history (`f114fcb`,
`7206d9e`, `4e2029ac`, `4b266ef`, `68127a3`, `e7198e43`). It used a persistent
`curl_cffi.requests.Session(impersonate="chrome")`, public IDX warm-up pages,
cookie continuity, and the page-specific Referer; it did not manually set a
User-Agent. The current Dynamic CA path had regressed to the pinned provider's
stateless module-level request path, with no warm-up/session continuity.

The bounded matrix did not reproduce a stable 403: current direct requests
often returned valid HTTP 200 JSON, including the control
`TradingSummary/GetStockSummary` response (`963` rows, `recordsTotal=963`,
`recordsFiltered=963`). However, the real smoke still returned HTTP 503 after
the provider's retry sequence on `NewsAnnouncement/GetAllAnnouncement`.
Therefore the failure is transport availability/WAF or upstream transport
instability, not an application-level CA schema rejection. A 200 response
with malformed or invalid schema remains fail-closed and never falls back.

The matrix results were:

| Probe | Result |
|---|---|
| Current stateless `GetIssuedHistory` | HTTP 200 JSON for the tiny no-row window; no stable 403 reproduced |
| Persistent Session, no warm-up | HTTP 200 JSON |
| Homepage warm-up | HTTP 200 HTML warm-up, then HTTP 200 JSON |
| Relevant-page warm-up | warm-up/API path usable; one primary-root warm-up was HTTP 503 but API remained independently checked |
| Generic vs page-specific Referer | HTTP 200 JSON in both bounded samples; no causal improvement claimed |
| Date `YYYYMMDD` vs ISO date | HTTP 200 JSON with identical no-row body in the bounded probe |
| Control `TradingSummary/GetStockSummary` | HTTP 200 JSON, 963 rows/counts |

No evidence showed that removing a manual User-Agent was harmful; the
remediation leaves User-Agent ownership to curl_cffi impersonation.

## Zapi raw transport evidence

Zapi was used only as transport for exact IDX paths. The raw envelope identity
observed in the live probe is `project=finance:idx:raw`, with nested
`provider=idx` and the exact requested `path`. Raw response bytes were kept in
the external diagnostic root, not Git, and the credential was never written to
an artifact.

| Upstream path | HTTP | Payload evidence | Raw body SHA-256 |
|---|---:|---|---|
| `ListingActivity/GetIssuedHistory` | 200 | list, `recordsTotal=0`, `recordsFiltered=0` for the bounded no-row window | `1aebcb2c135f52d05933b5b10e609da4c939c885f514bd9c77955ecbfea866fd` |
| `NewsAnnouncement/GetAllAnnouncement` | 200 | `Items=2`, `PageCount=1` | `2acedfed3ae46878c1f912480269f325172469c13990491eced052b942b86396` |
| `Home/GetCalendar` | 200 | `Results=282` | `8c5d63ad904af36d82950293cab721707f81a513e182df31c2867992a39917dd` |

The adapter now admits Zapi only when the envelope project, provider, exact
path, inner payload, and normalized-byte relationship all verify. Authority
remains IDX; Zapi is not treated as an independent source.

## Implemented remediation

- Restore a persistent `curl_cffi` Chrome-impersonated Session for the pinned
  IDX client.
- Warm `https://www.idx.co.id/` and the company-summary page before API calls;
  retain session state and use the page-specific API Referer.
- On direct transport failure/non-response, attempt exact Zapi raw passthrough
  under `DIRECT_IDX_THEN_ZAPI_RAW_V1`.
- Preserve the exact Zapi HTTP envelope as an external raw artifact and store
  a hash-pinned normalized payload for the existing CA schema validator.
- Use the actual raw envelope identity `finance:idx:raw`.
- Never fallback after a direct HTTP 200 that is malformed, semantically
  invalid, incomplete, or has the wrong schema.
- Preserve all existing CA event semantics, calendar fingerprints, phase
  completeness, and V1.2 attestation gates.

## Real smoke

Command scope: `POST_EOD`, `BBCA`, `2026-08-21`, external root only:

`D:\Documents\Project\idx-e2e-dynamic-ca-real-smoke-20260823-v5`

- direct IDX announcement leg: HTTP 503 after the pinned retry sequence;
- selected transports: `DIRECT_IDX_HTTPS` and `ZAPI_IDX_RAW_PASSTHROUGH`;
- issued-history: direct IDX, complete;
- announcements: Zapi raw passthrough, complete;
- calendar: direct IDX, complete;
- phase status: `COMPLETE`;
- phase manifest SHA-256: `7dcb501578eb5dda2f0aee9a8008f5c0eb23fa85a63d7adbeac6bb658bd15535`;
- V1.2 attestation SHA-256: `d27b1a3e49568a9ff7cccc979459672f549dbbdceaeae18ae16964be3b4f6bf2`;
- representative normalized announcement artifact SHA-256:
  `c1cfeb59c365ab9b676f98b0094a2e5af4d3b299e32bdb898c81461b81e041fd`;
- representative Zapi raw envelope SHA-256:
  `7624ea9a83b059f9692880106930422dc4b7f114857458fb7654bf7d81b2359c`;
- production `verify_phase_manifest` result: PASS;
- attestation result: `RELEVANT_EVENT_DETECTED`;
- outcome access: false.

The one idempotency/recovery check against the same completed root stopped at
`FORWARD_CA_OUTPUT_EXISTS` before provider access. No final artifacts were
overwritten, and the manifest/attestation hashes remained unchanged.

## Validation

- focused CA/attestation/runtime tests: `49 passed`;
- full repository pytest: `706 passed, 0 failed, 3 FutureWarnings`;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- secret/artifact scan: no `ZAPI_API_KEY`, `x-api-key`, or test credential in
  the external smoke artifacts;
- no protected outcomes, model scoring, or live PAPER state accessed.

## External pin reconciliation

- runtime `expected_commit`: `511bf8f7c9992102445954164b7f7e4fea742436`;
- `capture_forward_ca_idx_bei.py` SHA: `6699a8e1af260c70fd70a0ef74611b18a2049568789651621063e13821516ec3`;
- external config SHA sidecar: `72433697097cb14668503cce157005a035dfb6e87410f9cdbee8c4a765bb0723`;
- installed `IDXTrade-E2E-Paper` action uses that config SHA;
- task remains enabled with its existing 11 daily triggers;
- no unrelated scheduler was changed.

Operational caveat: the repository currently has the pre-existing user change
`notebooks/e2e_monte_carlo_v4_x1.ipynb`. The scheduler's fail-closed bootstrap
checks repository cleanliness, so the next scheduled cycle will stop at the
repo-dirty gate until that user-owned notebook change is committed or otherwise
resolved. This lane intentionally did not alter it.
