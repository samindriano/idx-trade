# E2E Baseline Paper V1 — Official Open Dual-Transport Local Acceptance

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Validated implementation HEAD: `a17d580a0dbd89c648215043281b6f995385bec2`

## Verdict

`OFFICIAL_IDX_OPENPRICE_DUAL_TRANSPORT_LOCAL_VALIDATION_PASS_READY_FOR_SCHEDULER_INSTALL`

The execution-grade official Open transport gate is accepted at the local code + real-network integration level.

## Validation

- exact validated HEAD: PASS
- compile/import: PASS
- focused regression: **71 passed**
- `git diff --check`: PASS
- worktree after validation: clean
- scheduler remained uninstalled during validation
- no Stockbit call
- no protected prospective outcome access
- Zapi API key was not exposed

## Real fallback smoke — 2026-06-12

The canonical transport chain was exercised end-to-end:

1. `DIRECT_IDX_HTTPS` attempted first;
2. direct IDX returned HTTP 403;
3. `ZAPI_IDX_RAW_PASSTHROUGH` was automatically invoked;
4. Zapi returned HTTP 200;
5. nested provenance and full-session completeness passed;
6. evidence certification succeeded;
7. `verify_open_execution_inputs()` accepted the certified evidence.

Selected transport: `ZAPI_IDX_RAW_PASSTHROUGH`

Transport policy: `DIRECT_IDX_THEN_ZAPI_RAW_V1`

Frozen authority/source semantics remained:

- authority: `IDX`
- upstream path: `TradingSummary/GetStockSummary`
- field semantics: `IDX_OFFICIAL_OPENPRICE`
- price fallback policy: `NONE`
- `FirstTrade` remains audit witness only

### Provenance/completeness

- nested provider: `idx`
- nested path: `TradingSummary/GetStockSummary`
- rows: **959**
- `recordsTotal`: **959**
- `recordsFiltered`: **959**
- duplicate `StockCode`: **0**
- positive `OpenPrice`: **589**
- unavailable `OpenPrice`: **370**

### Witness values

| Ticker | OpenPrice | FirstTrade |
|---|---:|---:|
| AADI | 8100 | 8075 |
| BBCA | 6000 | 5975 |
| BBRI | 2880 | 2890 |

### Smoke artifact hashes

- manifest SHA-256: `14b2366af748f9dce16d6a555666a087ffdaf7c5930c11a653ef1cd70153309c`
- raw Zapi envelope SHA-256: `b8cc90f1b7ef846ad8d6a051c1295ab61b14b1bce704afc4e2d3734221a269a1`
- normalized Open evidence SHA-256: `f91100c3aa74dfb5ef15c93e84b9ed1db2231fb085622c60b96590657a9d28ac`

The raw artifact was confirmed to preserve the complete Zapi HTTP JSON envelope (`data` / `project` / `timestamp`), while normalization consumed the nested IDX Stock Summary object.

## Verifier acceptance

Verified lineage:

- `authority = IDX`
- `upstream_path = TradingSummary/GetStockSummary`
- `field_semantics = IDX_OFFICIAL_OPENPRICE`
- `fallback_policy = NONE`
- `transport_policy = DIRECT_IDX_THEN_ZAPI_RAW_V1`
- `transport = ZAPI_IDX_RAW_PASSTHROUGH`

Adversarial locks passed for:

- wrong nested provider;
- wrong nested path;
- incomplete full-session counts;
- Zapi envelope relabelled as direct transport;
- direct response relabelled as Zapi transport;
- zero `OpenPrice` with positive `FirstTrade`;
- forged `FirstTrade` substitution;
- malformed direct response not being hidden by secondary transport;
- both transports unavailable -> fail closed.

## Deployment boundary

The dedicated task `IDXTrade-E2E-OfficialOpen` may now be installed locally.

Before installation, confirm `ZAPI_API_KEY` is available as a **persistent Windows user or machine environment variable**, not merely in the current transient PowerShell process. The scheduled task action must not contain or print the key.

The existing task contract remains:

- 09:02, 09:07, 09:12, 09:17, 09:22 Asia/Jakarta-local Windows clock;
- `AtLogOn` same-session catch-up;
- `StartWhenAvailable`;
- one instance at a time;
- current session only;
- first successful certified capture becomes immutable/idempotent;
- if both transports fail, no execution-grade Open artifact is created.

After installation, the next operational gate is one genuine same-session weekday capture. Because 2026-08-22 is Saturday, the next normal IDX weekday observation target is Monday, 2026-08-24 (subject to exchange-session availability).

No CA/dividend/persistent-runtime transplant is blocked by additional Open source research now. The source/transport investigation is closed unless a future production regression appears.
