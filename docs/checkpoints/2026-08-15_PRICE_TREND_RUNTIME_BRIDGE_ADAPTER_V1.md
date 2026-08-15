# Price / Trend Runtime Bridge Adapter V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-runtime-bridge-adapter-v1`

Status: `IMPLEMENTED_VALIDATION_PENDING`

Parent context pin: `integration/price-trend-runtime-context-pin-v1@417e306cf9e30dbb4a9a1ab1ea8855b7dbd7bd51`

## Purpose

Provide the read-only zero-provider adapter required to connect the accepted Price / Trend Forward Sidecar V1 to the already preserved post-2026-07-31 runtime context.

No provider/capture function is imported or called.

## Frozen source policy

- Exact historical parent: Clean-V2 causal market panel SHA `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.
- Exact historical calendar SHA: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`.
- Exact bridge extension calendar SHA: `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`.
- Exact combined session-set SHA: `dd51d3dbcb29915ff80612d84a912da237331e979ee3847bd8fd4984ead413dd`.
- Bridge fallback is allowed only through `2026-08-10`.
- `2026-08-11` onward requires valid canonical DATA_READY EOD market input.
- canonical + bridge both valid on a bridge-eligible date = `AMBIGUOUS_CONTEXT_SOURCES`.
- missing official extension session = fail closed.

## Implementation

New module:

`src/idx_trade/forward_price_trend_context_bridge.py`

Public producer:

`produce_price_trend_state_with_context_bridge(...)`

Strict verifier:

`verify_price_trend_state_context_bridge_strict(...)`

The producer:

1. verifies the historical panel SHA;
2. separately verifies historical and bridge calendars;
3. validates the one-date seam and in-memory combined session-set hash;
4. resolves every extension session exactly once under the frozen bridge/canonical policy;
5. bridge sessions are revalidated read-only from `market_context.parquet`, their bridge manifest, raw Stock Summary, and Foreign Flow provenance hashes;
6. canonical sessions are revalidated from their own DATA_READY manifest, exact model-input path/SHA, and their own capture-time calendar path/SHA;
7. combines only H/L/C/Volume through source `t` with the historical panel;
8. invokes the already accepted `materialize_price_trend_state_for_session()` without changing state formulas or thresholds;
9. writes the same immutable prospective sidecar namespace for `t+1`.

The canonical operator calendar is deliberately not required to equal the bridge extension calendar. Both are revalidated against their own authority; feature-session timing comes from the pinned historical+bridge in-memory union.

## Strict verification

The bridge-aware strict verifier re-establishes:

- standard sidecar schema/hash/count/state-distribution checks;
- exact historical panel and calendar pins;
- exact bridge calendar and combined-session-set pins;
- source `t` -> target `t+1` transition;
- extension-session list length/order;
- every stored source artifact through fresh bridge/canonical semantic validation;
- ambiguity/post-monitor canonical-only policy at verification time;
- deterministic provenance fingerprint.

Consistently re-hashing a semantically tampered canonical or bridge parent must therefore fail.

## Controlled runtime target

First permitted mechanical smoke after CI/local preflight:

`2026-08-12 -> 2026-08-13`

No target canonical directory is required. Smoke may inspect only timing, hashes, schema, counts, state distributions, source kinds, and idempotency. No outcome/performance metric is authorized.

## Tests

`tests/test_forward_price_trend_context_bridge.py` covers:

- bridge sessions through 2026-08-10 followed by canonical 2026-08-11/12;
- production without target-session directory;
- strict verification;
- missing bridge gap rejection;
- canonical+bridge ambiguity rejection;
- no bridge fallback after 2026-08-10;
- canonical parent semantic tamper rejection after consistent re-hash attempt;
- bridge manifest semantic tamper rejection after consistent re-hash attempt;
- combined session-set pin enforcement.

## Still prohibited

- provider/network calls;
- bridge or canonical recapture/repair;
- scheduler or counter changes;
- O2 changes;
- outcome/label/TP/SL access or performance evaluation;
- Price State threshold changes;
- Foreign Flow + Price State combination;
- WATCH / READY / ENTRY_ELIGIBLE;
- HSC/free-float integration.

## Validation gate

Before REVIEW:

1. focused Price State + sidecar + bridge-adapter tests pass;
2. `git diff --check` passes;
3. full repository pytest result is recorded;
4. no new failure beyond the known unrelated storage expectation is introduced;
5. no real runtime smoke is performed from GitHub Actions.
