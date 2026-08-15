# Price / Trend Runtime Bridge Adapter V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `integration/price-trend-runtime-bridge-adapter-v1`

Status: `REVIEW`

Verdict: `PRICE_TREND_RUNTIME_BRIDGE_ADAPTER_V1_ENGINEERING_READY_LOCAL_SMOKE_REQUIRED`

Final validated code HEAD before this documentation-only update: `462b67176dabfe0628aee1c08ed54e31c3f1231d`

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

Core adapter:

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

Consistently re-hashing a semantically tampered canonical or bridge parent therefore fails.

## Optional accepted-context attestation for the first smoke

A separate optional module was added:

`src/idx_trade/forward_price_trend_context_anchor.py`

It does **not** rewrite the immutable Price State sidecar. It creates a sibling:

`price_trend_context_anchor.attestation.json`

for a controlled smoke when an independently accepted context manifest is explicitly supplied.

Approved 2026-08-12 -> 2026-08-13 anchor:

- Foreign Flow Representation V2 manifest path:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\forward_monitoring\prospective\foreign_flow_representation_v2\2026-08-13\foreign_flow_representation_v2.manifest.json`
- accepted manifest SHA-256:
  `4095fbfd39a9ef9459bfa68f6ea8560449683133b882671d3176eb070bcbb51d`

The attestation verifies the accepted Foreign Flow manifest + representation artifact pair, then requires exact agreement with Price State on:

- source and feature sessions;
- historical market-panel path/SHA;
- historical-calendar path/SHA;
- bridge-calendar path/SHA;
- combined session-set SHA/count/first/last;
- extension-session order and source kind;
- bridge manifest + market-context path/SHA for bridge sessions;
- canonical parent DATA_READY manifest path/SHA for canonical sessions.

This is deliberately **optional** and `future_runtime_dependency=false`; Price State remains valid under its own bridge-aware strict verifier without this attestation. The old 2026-08-13 Foreign Flow manifest must never become a generic dependency for future live sessions.

## Controlled runtime target

First permitted mechanical local smoke:

`2026-08-12 -> 2026-08-13`

No target canonical directory is required. The local smoke must:

1. recheck all pinned Windows files/hashes;
2. run the bridge-aware producer with zero providers;
3. run `verify_price_trend_state_context_bridge_strict`;
4. create the optional accepted-context attestation against Foreign Flow manifest SHA `4095fbfd...`;
5. run `verify_price_trend_context_anchor_attestation`;
6. rerun producer/attestation to prove idempotency;
7. inspect only timing, hashes, schema, counts, state distributions, source kinds, and idempotency.

No outcome/performance metric is authorized.

## Validation result

Draft PR: `#28`.

Final synthetic/offline validation at code HEAD `462b67176dabfe0628aee1c08ed54e31c3f1231d`:

- focused Price State + sidecar + bridge adapter + optional context-anchor tests: **38 passed**;
- `git diff --check`: **PASS**;
- inherited Price State validation workflow: PASS;
- inherited Forward Sidecar validation workflow: PASS;
- full repository pytest: **77 passed, 1 failed, 4 warnings**;
- sole full-suite failure remains the unrelated pre-existing `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`, where storage emits independent `raw_close` and `vendor_adj_close` conflicts while the old test expects one.

No Price State, sidecar, bridge-adapter, or anchor-attestation test failed.

Adversarial coverage includes:

- bridge sessions through 2026-08-10 followed by canonical 2026-08-11/12;
- production without target-session directory;
- missing bridge gap rejection;
- canonical+bridge ambiguity rejection;
- no bridge fallback after 2026-08-10;
- canonical parent semantic tamper rejection after consistent re-hash attempt;
- bridge manifest semantic tamper rejection after consistent re-hash attempt;
- combined session-set pin enforcement;
- optional anchor absence does not invalidate the Price State sidecar;
- anchor manifest SHA mismatch rejection;
- consistently re-pinned anchor with a different bridge market-context identity rejection;
- immutable/idempotent context-attestation behavior.

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

## Next boundary

**Windows local byte verification + exactly one zero-provider 2026-08-12 -> 2026-08-13 mechanical smoke.**

Before local execution, Codex must refetch canonical `origin/main:coordination/TEAM_STATUS.md`, safely record/claim the current Price State runtime lane while preserving all other agents' rows, then execute from this exact branch. Stop after smoke artifacts, strict verification, optional accepted-context attestation, idempotency, focused/full tests, `git diff --check`, checkpoint/handoff update, commit/push, and TEAM_STATUS -> REVIEW.

Do not hook this into the canonical scheduler/post-capture path yet. That remains a separate milestone after independent review of the local smoke.