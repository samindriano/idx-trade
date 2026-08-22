# E2E Baseline Paper V1 — Official Open Provenance Implementation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Prep anchor: `6b315a03479f0e135444e2d32c49a47313cbf315`

## Phase A source probe result

Bounded local probe on 2026-06-12 used AADI, BBCA, and BBRI.

### Zapi IDX transport — re-probe

The first attempt was blocked by Cloudflare HTTP 403 / Error 1010. A later bounded re-probe succeeded through Cloudflare and materially clarified the source behavior.

Observed on the successful re-probe:

- normalized wrapper `finance:idx/stock-summary`: HTTP 200 JSON;
- raw IDX passthrough: HTTP 200 JSON;
- direct IDX: HTTP 200 JSON;
- wrapper/raw/direct values matched exactly for AADI, BBCA, and BBRI across the compared fields;
- `OpenPrice` substitution by `FirstTrade`: not detected;
- duplicate ticker/session keys: 0;
- provider identity: `idx`;
- dataset identity: `stock-summary`;
- raw path identity: `TradingSummary/GetStockSummary`.

Representative values:

| Ticker | OpenPrice | FirstTrade | Wrapper/raw/direct |
|---|---:|---:|---|
| AADI | 8100 | 8075 | exact |
| BBCA | 6000 | 5975 | exact |
| BBRI | 2880 | 2890 | exact |

However the code-filtered normalized wrapper returned `rows=1`, `recordsTotal=1`, `recordsFiltered=959`, while raw/direct returned `rows=959`, `recordsTotal=959`, `recordsFiltered=959`.

Therefore the re-probe establishes **price-field fidelity** for the sampled rows but does not establish a clean full-session completeness contract for the filtered wrapper metadata. The strict transport verdict remains:

`ZAPI_IDX_OPENPRICE_TRANSPORT_PROOF_FAIL`

This does **not** mean Zapi returned a wrong Open price. It means the normalized wrapper is not admitted as the canonical full-session completeness authority for this baseline. Zapi raw passthrough remains a plausible future redundant transport because the sampled raw response was exact to direct IDX, but no silent fallback is configured.

### Direct IDX transport

Direct official IDX returned a complete 959-row session payload with:

- `recordsTotal = 959`
- `recordsFiltered = 959`
- zero duplicate ticker/session keys.

The direct source again demonstrates that `OpenPrice` and `FirstTrade` are distinct fields. This aligns with the retained historical official-source audit on `data/idx-open-official-stock-summary-recovery-v1`, where `OpenPrice` was the only defensible Open candidate and `FirstTrade` was rejected as a fallback.

## Frozen baseline source contract

For E2E Baseline Paper V1:

- authority: `IDX`
- transport: `DIRECT_IDX_HTTPS`
- upstream path: `TradingSummary/GetStockSummary`
- field semantics: `IDX_OFFICIAL_OPENPRICE`
- fallback policy: `NONE`
- positive finite `OpenPrice`: available for paper Execution
- zero/non-positive/null/invalid `OpenPrice`: unavailable, preserving pending-transition semantics
- positive `FirstTrade` never repairs an unavailable `OpenPrice`
- Stockbit/IEP/IEV/generic 09:00 snapshots remain inadmissible as the canonical Open source.

No Zapi fallback is configured. If direct IDX is unavailable on a prospective session, Open acquisition fails closed rather than changing providers silently.

## Implementation

### `src/idx_trade/official_open_evidence_v1.py`

Adds a direct IDX source-evidence contract that:

1. requests the full Stock Summary session (`length=9999`, `start=0`, exact date);
2. preserves exact raw response bytes;
3. requires a non-empty full-session response with `recordsTotal == recordsFiltered == returned row count`;
4. requires exact `StockCode`, `Date`, `OpenPrice`, and `FirstTrade` fields;
5. rejects duplicate ticker/session keys and wrong-session rows;
6. projects raw `OpenPrice` literally into `open_price` without fallback;
7. retains `first_trade` only as an audit witness;
8. builds the complete session in a hidden staging directory;
9. writes raw bytes, normalized parquet, then manifest inside staging;
10. hash-binds raw and normalized artifacts;
11. atomically promotes the complete staging directory to the final session path;
12. cleans abandoned in-process staging on handled failure;
13. marks `execution_grade = true` only under this fixed contract;
14. refuses overwrite of an already-existing final session evidence directory.

This staging/promote model prevents a handled mid-write failure from leaving a partial final evidence session that could be mistaken for complete evidence.

Conceptual runtime layout:

```text
runtime/e2e_baseline_paper_v1/
  official_open/
    latest_capture.json
    logs/
    YYYY-MM-DD/
      raw_response.json
      open_prices.parquet
      manifest.json
```

### `src/idx_trade/v4_x1_execution_v1_verify.py`

The Open verifier is hardened so generic OHLCV is no longer admissible.

`verify_open_execution_inputs()` now requires a certified manifest and verifies:

- schema version;
- authority = IDX;
- upstream path identity;
- direct transport identity;
- `IDX_OFFICIAL_OPENPRICE` field semantics;
- fallback policy = NONE;
- `execution_grade = true`;
- exact execution session;
- raw artifact SHA-256;
- normalized artifact SHA-256;
- raw response full-session counts;
- manifest counts against re-parsed raw evidence;
- normalized ticker/session keyset against raw source;
- normalized `open_price` exact equality to raw `OpenPrice`;
- normalized `first_trade` exact equality to raw `FirstTrade` witness;
- positive/unavailable OpenPrice counts.

`VerifiedOpenExecutionInputs` now also carries:

- manifest path + SHA;
- raw source path + SHA;
- authority;
- upstream path;
- field semantics;
- fallback policy;
- transport identity.

The existing low-level Execution simulator still consumes the same positive Open mapping and unchanged missing-Open pending semantics.

## Same-session capture runtime and scheduler wiring

Added:

- `src/idx_trade/official_open_capture_runtime_v1.py`
- `scripts/run_official_open_capture.ps1`
- `scripts/install_official_open_capture_task.ps1`

Runtime policy:

- current Jakarta session date only;
- never automatically requests a previous session;
- no network before 09:02 Jakarta;
- no network on Saturday/Sunday;
- full-session direct IDX request only, with no ticker filter;
- existing certified session is idempotent / no second provider call;
- empty same-day source is `SOURCE_NOT_READY_OR_NO_SESSION` so a later scheduled retry can try again;
- any partial final evidence folder is `PARTIAL_EVIDENCE_FAIL_CLOSED`;
- `latest_capture.json` records the latest operational status.

Windows task defaults:

- task: `IDXTrade-E2E-OfficialOpen`;
- retries: 09:02, 09:07, 09:12, 09:17, 09:22 local time;
- logon catch-up enabled;
- `StartWhenAvailable` enabled;
- one instance at a time;
- direct IDX only;
- this task is separate from the legacy `IDXTrade-ForwardOpenArchive` and does not re-enable or mutate that superseded task.

The repeated morning triggers are deliberate. Opening-auction matching is already complete, but official Stock Summary publication may lag by a few minutes. The first successful capture becomes immutable and later retries become no-ops.

A same-day logon catch-up may capture later in that same session because the paper system is reconstructing the already-formed official opening-auction price from a Decision fixed the prior EOD. It never backfills an earlier date automatically.

## Regression/adversarial locks added

New/updated tests cover:

- literal separation of `OpenPrice` and `FirstTrade`;
- full-session count requirement;
- manifest/source hash binding;
- no overwrite;
- atomic staging cleanup on handled mid-write failure;
- direct request has no ticker filter and requests complete session;
- generic OHLCV without certified manifest rejected;
- valid certified official Open accepted;
- zero OpenPrice + positive FirstTrade remains unavailable;
- wrong execution date rejected;
- raw bytes tamper rejected;
- normalized bytes tamper rejected;
- manifest authority tamper rejected;
- forged FirstTrade substitution rejected even if the attacker also rewrites normalized artifact SHA and availability counts;
- duplicate raw ticker/session key rejected;
- runtime too-early and weekend network suppression;
- current-session-only capture;
- idempotent existing-session behavior;
- retryable empty source behavior;
- partial final session fail-closed;
- no automatic previous-session backfill.

## Explicit non-changes

This implementation does **not** change:

- Decision V2;
- Sizing V1 math;
- Execution V1 sell-before-buy ordering;
- buy/sell fee assumptions;
- slippage;
- 1% reference-value capacity guard;
- 15% entry cap;
- lot sizing;
- missing-Open pending behavior;
- CA/dividend semantics;
- alpha or protected prospective outcome data.

The generic/superseded `ops/idx-forward-open-archive-v1` is not silently promoted. The E2E baseline owns a separate official-open evidence sidecar with stricter source semantics.

## Validation / deployment status

Code, verifier hardening, same-session runtime, and Windows scheduler wiring are implemented on the E2E branch, but **not yet deployed** and **not yet accepted** until a fresh local compile/import + focused regression + direct IDX integration smoke passes on the exact HEAD.

After local validation:

1. install the dedicated official Open task locally;
2. observe at least one real same-session morning capture and verify the certified manifest;
3. then continue to selective CA/dividend/persistent-runtime transplant and E2E orchestration.

Current verdict:

`OFFICIAL_IDX_OPENPRICE_EVIDENCE_VERIFIER_AND_SCHEDULER_WIRING_IMPLEMENTED_PENDING_LOCAL_VALIDATION_DIRECT_IDX_FAIL_CLOSED_BASELINE_ZAPI_OPTIONAL_ONLY`
