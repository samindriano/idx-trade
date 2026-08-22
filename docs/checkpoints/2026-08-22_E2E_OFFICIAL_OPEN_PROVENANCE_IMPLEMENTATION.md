# E2E Baseline Paper V1 — Official Open Provenance Implementation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`
Prep anchor: `6b315a03479f0e135444e2d32c49a47313cbf315`

## Phase A source probe result

Bounded local probe on 2026-06-12 used AADI, BBCA, and BBRI.

### Zapi IDX transport

Both documented Zapi routes were attempted:

- `finance:idx/stock-summary`
- `finance:idx/raw` passthrough for `TradingSummary/GetStockSummary`

All six bounded requests returned Cloudflare HTTP 403 / Error 1010 before an application payload was returned. Therefore wrapper/raw field-faithfulness was not evaluable and Zapi is **not admitted as an Execution-grade dependency** in this baseline.

Probe verdict:

`ZAPI_IDX_OPENPRICE_TRANSPORT_PROOF_FAIL`

This is a transport/WAF admission failure, not evidence that Zapi rewrites `OpenPrice`.

### Direct IDX transport

One direct official IDX request succeeded with HTTP 200 and returned a complete 959-row session payload with:

- `recordsTotal = 959`
- `recordsFiltered = 959`
- zero duplicate ticker/session keys.

Representative raw values:

| Ticker | OpenPrice | FirstTrade |
|---|---:|---:|
| AADI | 8100 | 8075 |
| BBCA | 6000 | 5975 |
| BBRI | 2880 | 2890 |

The direct source therefore again demonstrates that `OpenPrice` and `FirstTrade` are distinct fields. This aligns with the retained historical official-source audit on `data/idx-open-official-stock-summary-recovery-v1`, where `OpenPrice` was the only defensible Open candidate and `FirstTrade` was rejected as a fallback.

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
8. writes raw bytes, normalized parquet, then manifest last;
9. hash-binds raw and normalized artifacts;
10. marks `execution_grade = true` only under this fixed contract;
11. refuses overwrite of an already-existing session evidence directory.

Conceptual runtime layout:

```text
runtime/e2e_baseline_paper_v1/
  official_open/YYYY-MM-DD/
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

## Regression/adversarial locks added

New/updated tests cover:

- literal separation of `OpenPrice` and `FirstTrade`;
- full-session count requirement;
- manifest/source hash binding;
- no overwrite;
- direct request has no ticker filter and requests complete session;
- generic OHLCV without certified manifest rejected;
- valid certified official Open accepted;
- zero OpenPrice + positive FirstTrade remains unavailable;
- wrong execution date rejected;
- raw bytes tamper rejected;
- normalized bytes tamper rejected;
- manifest authority tamper rejected;
- forged FirstTrade substitution rejected even if the attacker also rewrites normalized artifact SHA and availability counts;
- duplicate raw ticker/session key rejected.

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

The generic `ops/idx-forward-open-archive-v1` is not silently promoted because its existing OHLCV validator requires positive Open for every archived row, while the official Execution contract must preserve non-positive OpenPrice as explicit unavailability. Scheduler integration should therefore reuse that operational lane but call this official-open evidence sidecar rather than mislabel the generic archive.

## Validation status

Repository implementation is complete pending a fresh local compile/import + focused regression run on the exact branch HEAD.

If local validation passes, the next step is operational wiring:

1. bind the existing Forward Open scheduled lane to the direct IDX official-open evidence capture after the opening auction has formed;
2. no retroactive fabrication for missed sessions;
3. then continue to selective CA/dividend/persistent-runtime transplant.

Current verdict:

`OFFICIAL_IDX_OPENPRICE_EVIDENCE_AND_VERIFIER_IMPLEMENTED_PENDING_LOCAL_VALIDATION_ZAPI_NOT_ADMITTED_DIRECT_IDX_FAIL_CLOSED_BASELINE`
