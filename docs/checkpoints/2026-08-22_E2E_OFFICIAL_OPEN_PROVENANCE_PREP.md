# E2E Baseline Paper V1 — Official Open Provenance Preparation

Date: 2026-08-22
Branch: `integration/idx-e2e-baseline-paper-v1`

## Objective

Promote only a source-bound, hash-verifiable official IDX opening price into Execution V1. Do not use an arbitrary 09:00 snapshot, first observed trade, IEP snapshot, or unverified generic OHLCV `open` field as the paper fill base.

This is an execution-evidence integration task. It does not reopen Alpha, Decision V2, Sizing V1, or the hostile-audited Execution V1 economics.

## Frozen semantic target

Authoritative field semantics:

- upstream authority: Indonesia Stock Exchange (IDX / BEI);
- upstream dataset: Trading Summary / Stock Summary;
- upstream path identity: `TradingSummary/GetStockSummary`;
- authoritative field: `OpenPrice`;
- `FirstTrade` is explicitly not an admissible fallback;
- IEP/IEV are pre-opening diagnostics only and are not the final paper fill price;
- non-positive, absent, malformed, or unverified `OpenPrice` means unavailable Open and therefore preserves existing Execution pending-transition semantics.

Historical official-source audit retained on `data/idx-open-official-stock-summary-recovery-v1` found `OpenPrice` to be the only defensible opening-price candidate. It must not be confused with `FirstTrade`.

## Reuse, do not duplicate

The retained `ops/idx-forward-open-archive-v1` already owns prospective append-only forward OHLCV/Open archiving and intentionally records `execution_grade_promoted = false` until a source is frozen.

Therefore E2E should not create a second generic forward-Open archive. The intended integration is:

1. freeze/audit one official-Open provider adapter;
2. capture raw source evidence through the retained archive or a thin compatible source-evidence sidecar;
3. certify a session artifact as execution-grade only after source/schema/hash checks;
4. make `verify_open_execution_inputs()` consume that certification rather than trusting any file with an `open` column.

## Candidate operational transport

Preferred first candidate for bounded audit:

- Zapi `finance:idx/stock-summary`, or its raw IDX proxy path for `TradingSummary/GetStockSummary`;
- semantics must remain upstream IDX `OpenPrice`, not a Stockbit-derived synthetic Open;
- transport/provider metadata, request date, response bytes and normalized artifact must be preserved and hashed;
- the Zapi wrapper must not rewrite `OpenPrice`, silently substitute `FirstTrade`, forward-fill, or synthesize missing values.

Direct IDX retrieval may remain an authority/cross-check path where operationally available, but historical Cloudflare behavior means transport robustness must be separated from semantic authority.

Stockbit may later provide IEP/IEV diagnostics and an Open cross-check, but it is not the canonical execution source in this baseline contract.

## Required phases

### Phase A — bounded source proof

Before wiring Execution, prove the candidate transport contract on a small outcome-blind probe:

- exact upstream/path/provider identity;
- request session date;
- raw response schema and pagination behavior;
- `StockCode`, `Date`, `OpenPrice`, `FirstTrade` presence and types;
- duplicate ticker/date behavior;
- recordsTotal / recordsFiltered consistency where exposed;
- raw response bytes SHA-256;
- explicit confirmation that normalized `open` equals positive raw `OpenPrice` only;
- zero/non-positive `OpenPrice` remains unavailable;
- no `FirstTrade` fallback;
- if a direct IDX response is obtainable for the same bounded sample, compare exact relevant fields.

No protected prospective alpha outcome may be inspected. This is market-data provenance only.

### Phase B — execution-grade artifact contract

Freeze an immutable per-session evidence layout, conceptually:

```text
runtime/e2e_baseline_paper_v1/
  official_open/YYYY-MM-DD/
    raw_response.json
    open_prices.parquet
    manifest.json
```

Minimum manifest fields:

- schema_version;
- session_date;
- authority = IDX;
- upstream_path = `TradingSummary/GetStockSummary`;
- transport identity and version/config identity;
- request parameters;
- raw artifact path + SHA-256;
- normalized artifact path + SHA-256;
- field_semantics = `IDX_OFFICIAL_OPENPRICE`;
- fallback_policy = `NONE`;
- row count / unique ticker count;
- duplicate count = 0;
- positive OpenPrice count;
- unavailable OpenPrice count;
- capture timestamp;
- execution_grade = true only after all certification checks pass.

### Phase C — verifier hardening

Upgrade the Open verification boundary so Execution cannot accept arbitrary OHLCV.

`VerifiedOpenExecutionInputs` should carry at least:

- session date;
- positive official OpenPrice mapping;
- available tickers;
- normalized artifact SHA;
- raw source SHA;
- manifest SHA;
- source/authority identity;
- field semantics identity.

Verifier must reject:

- missing/unverified manifest;
- wrong session;
- wrong upstream/source identity;
- wrong field semantics;
- changed raw/normalized bytes;
- duplicate ticker rows;
- malformed price;
- `FirstTrade`-based normalization;
- generic Stockbit/intraday/09:00 snapshot presented as official Open;
- fabricated fallback for zero/missing OpenPrice.

### Phase D — regression/adversarial locks

Add focused tests for:

1. valid certified IDX OpenPrice artifact accepted;
2. wrong-date artifact rejected;
3. raw SHA tamper rejected;
4. normalized SHA tamper rejected;
5. manifest tamper rejected;
6. duplicate ticker rejected;
7. positive `FirstTrade` with zero OpenPrice remains unavailable;
8. arbitrary generic OHLCV `open` without execution-grade manifest rejected;
9. positive OpenPrice maps exactly to Execution raw Open;
10. missing Open continues existing pending BUY/SELL behavior;
11. legacy low-level Execution mechanics remain unchanged.

### Phase E — prospective acquisition scheduling

Only after Phase A-D pass:

- use the retained forward-Open acquisition lane rather than a new duplicate scheduler;
- ensure capture happens only after official opening price has formed;
- exact capture wall-clock time is less important than immutable same-session source evidence, because paper execution is a simulation of opening-auction participation rather than a broker-fill claim;
- no retroactive fabrication if a prospective session was missed.

## Explicitly deferred

- IEP/IEV high-frequency capture or execution policy;
- live/manual pre-opening order submission around 08:57;
- dynamic limit-price logic using IEP/IEV;
- Stockbit as an authoritative Open source;
- broker routing;
- any Alpha/Decision feature derived from pre-opening auction data.

These may be separately designed after the canonical E2E baseline and prospective evaluation are stable.

## Next action

Run Phase A as a bounded, local source/schema probe using existing credentials/config only. Do not commit credentials or raw secrets. If the transport proves faithful to IDX `OpenPrice`, implement the certification artifact and verifier hardening on this same E2E branch.

Current prep verdict:

`OFFICIAL_OPEN_PROVENANCE_CONTRACT_DEFINED_BOUNDED_SOURCE_PROOF_NEXT_NO_EXECUTION_CORE_CHANGE`
