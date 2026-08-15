# Foreign Flow Forward Context Bridge V1

Date: 2026-08-15 (Asia/Jakarta)

Branch: `data/foreign-flow-forward-context-bridge-v1`

Status: `IMPLEMENTATION_VALIDATED_LOCAL_RUNTIME_REQUIRED`

Validation PR: `#25` (draft, validation-only; no merge authorization)

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
- a self-contained Stock Summary transport using the same official IDX endpoint/validation pattern and strict `recordsTotal` single-response completeness gate used by the canonical EOD design;
- Foreign Flow normalization via the existing accepted `parse_stock_summary_foreign_flow()` contract;
- market context using the repo's canonical Yahoo `auto_adjust=False` adapter, local raw-price cache when present, and raw OHLCV columns only;
- immutable raw / market / Foreign Flow / manifest artifacts;
- transaction-like behavior: provider/price validation completes before final bridge session files are created, so a failed attempt does not intentionally publish a partial bridge session;
- hash, identity, session, unit, HLC, volume/value and outcome-blind verification.

The first CI attempt exposed accidental imports from the separate operator-EOD branch (`forward_monitoring`, `idx_stock_summary`, and a batching helper). Those cross-branch imports were removed. The bridge is now self-contained relative to its accepted producer base and imports only modules actually present there.

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

## Validation

A scoped PR workflow was added only to validate this lane without importing unrelated historical-alpha tests.

Focused bridge + downstream semantic suite on GitHub Actions:

`24 passed, 5 warnings`

Covered test files:

- `tests/test_forward_foreign_flow_context_bridge.py`
- `tests/test_forward_foreign_flow_context_bridge_policy.py`
- `tests/test_forward_foreign_flow_context_bridge_plan.py`
- `tests/test_forward_foreign_flow_representation_v2.py`
- `tests/test_forward_foreign_flow_setup.py`

The warnings are existing pandas `FutureWarning`s in the accepted V2 feature implementation.

The repository-wide default CI remains red **before test execution** because existing `tests/test_foreign_flow_alpha_v2.py` imports `joblib` while the branch's `pyproject.toml` does not declare/install `joblib` or scikit-learn. That dependency issue is outside this bridge lane and was not modified to manufacture a green full-suite result.

The initial bridge CI collection errors caused by unavailable cross-branch imports are closed; after remediation, the only collection error in the default full workflow is the unrelated `joblib` dependency.

No real provider call or user Windows artifact runtime was executed in this ChatGPT environment.

## Local execution gate

Before any real bridge capture:

1. fetch latest canonical `origin/main:coordination/TEAM_STATUS.md` and claim/continue this lane;
2. checkout this exact branch and rerun focused tests plus the available full suite / `git diff --check` locally;
3. identify the actual runtime root and accepted historical panel/archive/security-master pins already used by the V2 producer; do not guess paths or hashes;
4. sync a bridge-local official calendar from the historical cutoff through the desired source/next-session horizon;
5. run the read-only planner;
6. use bridge capture **only** for planner rows marked `NEED_BRIDGE_CAPTURE` and only through 2026-08-10;
7. use the existing canonical EOD catch-up runtime for every `NEED_CANONICAL_EOD` session after 2026-08-10;
8. rerun planner until `CONTEXT_BRIDGE_READY` with no ambiguity;
9. run exactly one bridge-aware prospective producer smoke test for the next official feature session;
10. verify prospective Representation V2 + Setup State hashes and stop for independent review.

Do not access outcomes, change O2 eligibility/counter rules, modify existing 2026-08-10/11/12 canonical bytes, integrate HSC/free-float, or start price-state research in this lane.
