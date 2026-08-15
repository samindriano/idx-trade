# TradingView Historical Price-Path V2.1 — bounded depth preflight runtime

Date: 2026-08-16
Branch: `data/tradingview-historical-price-path-v2-1-remediation`
Runtime commit before request: `0e6c7a4`
Decision: `V2_1_REMEDIATION_READY_FOR_FULL_PREREGISTRATION`

## Authorization and limits

The immutable preregistration was verified before network start. Exactly five
logical anonymous TradingView/Mathieu `prodata` requests were made, with no
retry, alternate symbol, alternate provider, or full-universe acquisition.
The request contract was `IDX:<ticker>`, timeframe string `"60"`, regular
session, adjustment `none`, initial range 500, fetch-more batch 5000, hard cap
3, and required start 2021-04-01 plus one prior official-session buffer.

Preregistration SHA-256:
`5fd9b2eefc69fd0c5a29e9d82e790e9f8490583e82e63522f45c815788b5574e`

The external runtime root is:

`D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_historical_price_path_v2_1_depth_preflight_20260816`

Runtime manifest SHA-256 (semantic value in the manifest):
`49d7db1ac33f2db6de9da1bf579b80b49dd7d26761f26020eafd69a94eb59a49`

The manifest contains 18 artifacts. File hashes include:

- `preflight_summary.json`: `f3d5efca14c71f55be9f8f0bbac1a282826a6f9ab7c1bf08d5c44234d673b7d9`;
- `request_manifest.json`: `8efd2a72f2a08a981f4ec62369e3664d66881e97e553831d166d97cc4742d071`;
- `network_start_marker.json`: `7336d06b8dbb4f901dcb104a92bbc89dabae65a03c68d4b9f32484a103d49a7d`;
- `runtime_artifact_manifest.json` file bytes:
  `9da9c508797466f67fac835b667445a231106af228a77656b25289444504f96e`.

The network marker references the exact preregistration SHA and records request
count 5. No protected outcomes or modeling inputs were accessed.

## Control results

All five controls passed every preflight condition:

| ticker | provider | depth | initial/final bars | earliest/latest session | identity | structural/session |
|---|---|---:|---:|---|---|---|
| BBCA | AVAILABLE | REQUIRED_START_REACHED | 500 / 10,192 | 2020-01-02 / 2026-07-31 | 10,192 MAPPED | 0 violations |
| BBRI | AVAILABLE | REQUIRED_START_REACHED | 500 / 10,207 | 2020-01-02 / 2026-07-31 | 10,207 MAPPED | 0 violations |
| BMRI | AVAILABLE | REQUIRED_START_REACHED | 500 / 10,199 | 2020-01-02 / 2026-07-31 | 10,199 MAPPED | 0 violations |
| TLKM | AVAILABLE | REQUIRED_START_REACHED | 500 / 10,202 | 2020-01-02 / 2026-07-31 | 10,202 MAPPED | 0 violations |
| ASII | AVAILABLE | REQUIRED_START_REACHED | 500 / 10,186 | 2020-01-02 / 2026-07-31 | 10,186 MAPPED | 0 violations |

Total returned bars: 50,986. Each control used two extensions and stopped as
soon as the required boundary was reached. The final extension deltas were
4,692, 4,707, 4,699, 4,702, and 4,686 respectively; no third extension was
needed.

Raw artifact SHA-256 by control:

- BBCA `a6a2dc0462577d16d248718b2720dc891eef51a2ebe25af6bfe449193109273f`;
- BBRI `5ece4c5c82739f5ee5c25f5188e90c2695c1c26befa0c93646bb4c53746ef599`;
- BMRI `214762d4771b1e77034be463be9b67c257b3f9cc97b4d842ad7d17290bc28279`;
- TLKM `e92f43af7d93e1c3d76bab776daece58172451ebfb70bd446073aa4e4a0f4992`;
- ASII `f9effefbfa5f87b46c763a9ce992bdbee951804996fd41063ab4608a1181a62f`.

All controls had zero malformed rows, duplicate rows, invalid OHLCV rows,
session-date leakage rows, and extended/pre-open contamination rows. All had
the prior-session buffer reached. The adapter reported
`required_start_reached` for every control.

## Immutable-input result and boundary

The canonical panel remained unchanged before/after:
`67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

The preflight proves the corrected depth/pagination/early-stop implementation
for five representative long-lived controls. It does not prove full-universe
coverage, does not resolve the 16 provider symbol errors, and does not change
the official canonical daily fidelity oracle. The only next stage would be a
separately reviewed, newly frozen full acquisition; this lane must stop here.
