# Foreign Flow Forward Context Bridge V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `data/foreign-flow-forward-context-bridge-v1`

Status: `IMPLEMENTATION_READY_LOCAL_RUNTIME_REQUIRED`

## Purpose

Close the bounded rolling-context gap between the accepted historical market panel ending 2026-07-31 and the already accepted prospective Foreign Flow Representation V2 / Setup State pipeline.

This is **not** a second forward monitor, scheduler, O2 counter, model path, or canonical-session repair system.

## Key design decision

The operator-facing forward runtime intentionally starts at 2026-08-10 and writes a mutable operator calendar under `forward_monitoring/calendar`. Existing session manifests pin the calendar SHA observed at their capture time. Therefore the bridge must not extend or rewrite that operator calendar to recover 2026-08-03..07.

Instead, the bridge writes immutable, range-versioned official IDX calendar evidence under:

`forward_monitoring/context_bridge/calendar/ranges/<start>_<end>/`

and bridge-only context sessions under:

`forward_monitoring/context_bridge/sessions/<YYYY-MM-DD>/`

## Implementation

### `forward_foreign_flow_context_bridge.py`

Provides:

- immutable official calendar-range sync using the existing `session_backfill.run_exchange_session_backfill()` / official IDX session parser;
- bounded bridge-only session capture using the same official IDX Stock Summary provider already used by canonical EOD;
- Foreign Flow normalization via the existing `parse_stock_summary_foreign_flow()` contract;
- market context using the same Yahoo raw-OHLC semantics / existing local raw cache helpers as canonical EOD;
- strict Stock Summary `recordsTotal` completeness;
- immutable raw / market / Foreign Flow / manifest artifacts;
- hash, identity, session, unit, HLC, volume/value and outcome-blind verification.

The bridge manifest explicitly records:

- `bridge_only=true`;
- `canonical_session_repair=false`;
- `outcome_blind=true`;
- `forward_outcomes_accessed=false`;
- no model scoring/fitting;
- no scheduler/counter mutation.

### `forward_foreign_flow_context_bridge_run.py`

Bridge-aware adapter around the already accepted V2 materializer.

For every required post-2026-07-31 session it resolves exactly one context source:

1. verified canonical EOD session when available;
2. otherwise a verified bridge-only session, but only through **2026-08-10**.

Hard policy:

- bridge fallback allowed for the pre-monitor gap and the 2026-08-10 monitor-start session if its preserved canonical capture is invalid;
- sessions **after 2026-08-10 require valid canonical EOD**;
- valid canonical + valid bridge for the same bridge-eligible session is `AMBIGUOUS_CONTEXT_SOURCES` and fails closed;
- an invalid canonical session may be bypassed only by a separately captured and separately hash-pinned bridge artifact; the canonical bytes are not rewritten or promoted.

The adapter combines pinned historical context + exactly one verified source per extension session, then calls the accepted:

`materialize_representation_v2_for_session()`

followed by:

`enrich_prospective_foreign_flow_setup()`.

No V2 formula, rolling window, percentile, rank, persistence, divergence, Setup State threshold or label is changed.

### `forward_foreign_flow_context_bridge_plan.py`

Read-only local planner. It performs zero provider calls and zero writes.

It classifies each required session as:

- `CANONICAL_READY`
- `BRIDGE_READY`
- `NEED_BRIDGE_CAPTURE`
- `NEED_CANONICAL_EOD`
- `AMBIGUOUS_CANONICAL_AND_BRIDGE`

This planner must be run before any bridge provider call.

## Known evidence boundary before local run

Previously recorded runtime evidence says:

- accepted historical market panel ends at 2026-07-31;
- 2026-08-10 preserved canonical attempt is incomplete (`962` returned rows vs `recordsTotal=963`) and must not be treated as complete;
- 2026-08-11 and 2026-08-12 canonical artifacts were verified and must not be rewritten;
- the operator calendar starts at 2026-08-10 by design.

The bridge calendar, not weekday inference, must determine the exact official sessions in the gap. Expected dates such as 2026-08-03..07 are hypotheses until the official calendar sync verifies them.

## Validation status

Code and focused tests were authored through the GitHub connector. No local Python runtime, provider call, or user Windows artifact root is available to this ChatGPT environment, so **no test-pass claim is made here**.

Added focused tests cover:

- operator calendar bytes remain untouched by bridge calendar sync;
- calendar range is immutable/idempotent;
- invalid canonical session can use a verified bridge without canonical repair;
- canonical + bridge ambiguity fails closed;
- post-monitor sessions cannot fall back to bridge;
- bridge adapter provenance keeps operator calendar/counter untouched;
- read-only planner separates `NEED_BRIDGE_CAPTURE` from `NEED_CANONICAL_EOD`.

## Local execution gate

Before any real bridge capture:

1. checkout this exact branch and run focused + full pytest + `git diff --check`;
2. sync a bridge-local official calendar from the historical cutoff through the desired source/next-session horizon;
3. run the read-only planner;
4. use bridge capture **only** for planner rows marked `NEED_BRIDGE_CAPTURE`;
5. use the existing canonical EOD catch-up runtime for every `NEED_CANONICAL_EOD` session after 2026-08-10;
6. rerun planner until `CONTEXT_BRIDGE_READY`;
7. run exactly one bridge-aware prospective producer smoke test for the next official feature session;
8. verify prospective Representation V2 + Setup State hashes and stop for independent review.

Do not access outcomes, change O2 eligibility/counter rules, modify existing 2026-08-10/11/12 bytes, integrate HSC/free-float, or start price-state research in this lane.
