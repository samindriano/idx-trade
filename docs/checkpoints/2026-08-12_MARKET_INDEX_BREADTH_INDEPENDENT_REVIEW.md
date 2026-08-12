# Market / Index / Breadth History V1 — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Reviewed branch: `data/market-index-breadth-history-v1`
Reviewed runtime HEAD: `e160889b1f33b0a3275e617e5f6877576909de19`
Decision: `MARKET_INDEX_BREADTH_V1_SOURCE_AUDIT_ACCEPTED_CONDITIONAL_PIT_BLOCKED`

## Review conclusion

The bounded source audit is accepted. The reported verdict
`CONDITIONAL_SOURCE_READY_PIT_BLOCKED` is appropriately conservative and is
supported by the committed contract, source diagnostics, and tests.

Accepted conclusions:

- official IDX `TradingSummary/GetIndexSummary` is a usable sampled source for
  session-date index state and aggregate volume/value/frequency/market-capital
  context;
- official IDX `TradingSummary/GetStockSummary` is a usable sampled source for
  per-security session-date change and regular/non-regular market activity;
- sampled Zapi payload parity is evidence of transport/access parity, not an
  independent canonical provenance source;
- no official advancing/declining/unchanged aggregate or denominator contract
  was established, so derived stock change buckets must remain explicitly
  non-canonical/audit-only;
- historical session date is not publication time, Zapi access/cache time is
  not `knowledge_at`, and no immutable revision lineage was established;
- the 2021 aggregate reconciliation mismatch is correctly preserved as a
  blocker rather than repaired by assumption;
- no historical PIT-complete window, bulk acquisition, feature use, modeling,
  or protected-outcome access is authorized.

## Implementation review

The normalization code fail-closes on malformed/duplicate rows, basic index
OHLC and non-negative aggregate invariants, missing source hashes, and missing
PIT timing. `OpenPrice` is intentionally excluded from this lane. The derived
breadth helper explicitly excludes zero-regular-volume rows from unchanged and
labels the result non-official. Focused tests cover these core boundaries.

One non-blocking hardening item should be resolved before any production/bulk
capture reuses `OfficialIDXMarketContextProvider`: the helper currently sends
`length=100,start=0` and the focused test only asserts request shape. A future
capture lane must prove complete-response/pagination semantics against
`recordsTotal` (or equivalent) and fail closed on partial stock-summary pages.
The present source-audit verdict does not depend on treating this helper as a
certified complete-universe fetcher, so this does not invalidate the audit.

Likewise, raw sampled captures were intentionally retained outside Git. Their
recorded SHA-256 values are useful evidence, but any future operational capture
should persist immutable raw payloads plus manifests so a later reviewer can
re-hash the exact bytes independently.

## Authorization boundary

This lane is complete as a source audit and may be parked at
`CONDITIONAL_SOURCE_READY_PIT_BLOCKED`.

Do not bulk-acquire historical rows or feed them to V3-B/O2/Path Risk from this
checkpoint. The clean next way to advance this source family is prospective
forward EOD capture: record the actual post-close acquisition time and immutable
raw bytes going forward, without pretending that this retroactively certifies
historical PIT timing.

Any forward capture lane must remain separate from existing Stockbit intraday,
OPEN, O2/V3-B forward counters/outcomes, and all model research.