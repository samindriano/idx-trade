# E2E Baseline Paper V1 — Official Open Dual-Transport Remediation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Pre-remediation validated HEAD: `dd21ddb0e3822d614aa7c3a57c82fa8e3d97e3a0`

## Why this remediation exists

The execution-grade Open contract itself passed focused local regression, but the direct IDX integration smoke returned HTTP 403. Separately, the bounded Zapi re-probe had already established that Zapi's **raw IDX passthrough** for `TradingSummary/GetStockSummary` returned the same sampled rows and `OpenPrice` values as direct IDX, with coherent full-session counts (`959/959/959`).

The normalized `finance:idx/stock-summary` wrapper remains inadmissible for this baseline because its code-filtered metadata was observed as `rows=1`, `recordsTotal=1`, `recordsFiltered=959`. This remediation therefore does **not** use that wrapper.

## Frozen source semantics

These remain unchanged:

- authority: `IDX`;
- upstream path: `TradingSummary/GetStockSummary`;
- field semantics: `IDX_OFFICIAL_OPENPRICE`;
- `FirstTrade` remains audit witness only;
- price fallback policy remains `NONE`;
- zero/non-positive/missing `OpenPrice` remains unavailable;
- no Stockbit/IEP/IEV fallback;
- no generic 09:00/first-tick fallback;
- no prior-session automatic backfill.

The only change is **transport redundancy**.

## Canonical transport policy

`DIRECT_IDX_THEN_ZAPI_RAW_V1`

1. Primary: `DIRECT_IDX_HTTPS`.
2. If and only if the direct transport fails at the HTTP/request/empty-response boundary, try `ZAPI_IDX_RAW_PASSTHROUGH`.
3. Zapi raw must identify `provider=idx` and exact `path=TradingSummary/GetStockSummary`.
4. The same strict full-session completeness contract is then applied: returned rows = `recordsTotal` = `recordsFiltered`, with no duplicate ticker/session keys.
5. A direct response that arrives but fails schema/completeness/certification is **not** hidden by switching providers; it fails closed.
6. If both transports fail, capture fails closed and no execution-grade Open artifact is created.

## Manifest / verifier hardening

Schema advances to `idx_official_open_evidence_v1_1`.

The manifest now binds both:

- exact selected `transport`;
- `transport_policy = DIRECT_IDX_THEN_ZAPI_RAW_V1`.

The verifier admits only the two frozen transport identities and revalidates transport-specific raw witnesses. A Zapi raw payload cannot be relabelled as direct IDX, and a direct IDX payload cannot be relabelled as Zapi raw.

`authority`, upstream path, raw SHA, normalized SHA, exact OpenPrice projection, counts, and no-price-fallback semantics remain independently verified.

## Runtime behavior

`official_open_capture_runtime_v1` now:

- remains current-session-only;
- remains no-network-before-09:02;
- remains idempotent once a certified manifest exists;
- attempts direct IDX first;
- reads the optional secondary credential from `ZAPI_API_KEY` without persisting or logging its value;
- invokes Zapi raw only after a direct transport failure;
- records the selected transport in `latest_capture.json`;
- fails closed if no secondary credential is configured and direct transport fails;
- fails closed if the secondary transport also fails.

The existing 09:02/09:07/09:12/09:17/09:22 Windows scheduler wiring is not installed by this remediation. Deployment still requires fresh local validation and a real transport smoke.

## Tests added/updated

Coverage now includes:

- direct success never calls Zapi;
- direct HTTP failure -> Zapi raw fallback;
- Zapi raw request has no ticker/code filter and requests the full exact session;
- Zapi API key is not written into transport metadata;
- Zapi `provider` and raw `path` are mandatory;
- both transports failing is fail-closed;
- direct schema/completeness failure is not masked by transport fallback;
- both transport identities are accepted only with matching raw provenance;
- transport relabel tampering is rejected;
- `OpenPrice` vs `FirstTrade` separation remains locked;
- existing raw/normalized hash tamper protections remain locked.

## Validation state

Implementation is committed on the same E2E lane but has **not yet received fresh local compile/pytest + real dual-transport smoke validation**.

Do not install the morning task until that validation passes.

Pending verdict:

`OFFICIAL_IDX_OPENPRICE_DUAL_TRANSPORT_IMPLEMENTED_PENDING_LOCAL_VALIDATION`
