# SUSPSTATE-01 Suspension-Interval Reconciliation — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `SOURCE_BLOCKED / NOT_ADMITTED / NO CANDIDATE`

## Question

Can the available official suspension/tradability intervals explain the
regular-market `NO_TRADE` state without collapsing distinct market semantics or
silently deduplicating overlapping intervals?

This is a read-only, outcome-blind source reconciliation. It does not alter
the interval source, no-trade anchors, canonical panel, or telemetry and does
not infer a predictive mechanism.

## Evidence

- Interval source rows: `76`; tickers: `12`; source references: `37`.
- Markets: `38 REGULAR`, `36 CASH`, `2 NEGOTIATED`.
- Finite intervals: `71`; open intervals: `5`.
- Finite duration: minimum `1` day, median `5` days, maximum `77` days.
- Effective dates range from `2023-08-15` through `2026-06-10`.
- Session expansion produced `2,880` market rows and `2,409` unique keys.
- Expansion contains `471` duplicate key groups and `942` duplicate rows;
  therefore the expansion is not key-unique and must not be silently
  deduplicated.

For the regular market only:

- Expanded rows: `1,170`.
- Regular interval/no-trade overlap: `1,168`.
- Regular interval rows not marked `NO_TRADE`: `2`.
- Unique regular interval keys not covered by `NO_TRADE`: `2`.
- Unique `NO_TRADE` anchor keys not covered by a regular suspension interval:
  `120,498` of `121,666`.

The large uncovered `NO_TRADE` population is not evidence against the
execution artifact; it shows only that the currently available suspension
interval source is sparse relative to the full no-trade anchor population.
The 471 duplicate groups also prevent a clean row-level duration or coverage
interpretation without an explicit overlap policy.

## Disposition and blockers

| Gate | Result |
|---|---|
| Required columns/source/reference validity | `PASS` |
| Interval date order and official-session expansion | `PASS` |
| Regular/CASH/NEGOTIATED separation preserved | `PASS` |
| Expanded key uniqueness | `FAIL` |
| `NO_TRADE` equivalent to suspension | `UNKNOWN` |
| Announcement/publication available-at semantics | `UNKNOWN` |
| Population completeness | `UNKNOWN` |
| Predictive admissibility | `NOT ADMITTED` |

Interpretation is explicitly `UNKNOWN_NO_TRADE_NOT_EQ_SUSPENSION` and
`UNKNOWN_ANNOUNCEMENT_NOT_ROW_LEVEL_AVAILABLE_AT`. Do not convert the
intervals into a daily suspension feature, impute uncovered dates, or remove
overlaps without a frozen policy and row-level source evidence.

## Reproducibility and firewall

- Preregistration: `docs/checkpoints/2026-09-19_ALPHA_SUSPSTATE01_SOURCE_PREREGISTRATION_V1.md`.
- Generator: `research/alpha_suspstate01_reconciliation_v1.py`; SHA-256
  `45e45633e877e00afc1bd7184daf10a13df23f639ef89641bacc746326742975`.
- Result JSON SHA-256:
  `d5ad7b50c1eaa8e48e17892114496bb91a7e66adcb1395ecf3f72d57ed012d75`.
- Independent verifier: `research/verify_alpha_suspstate01_reconciliation_v1.py`;
  SHA-256 `7f0e16460bd6ec04c2e2f6ac4d97b4753c4cb474ef084dedd7a8175bf61d345d`.
- Independent verification: `PASS`; output SHA-256
  `c7abfd82dfda37e63d105885ad6bb75ed7ccac7bb4aca80bc91480dbd8ce29f1`.
- Hash-contract output SHA-256
  `6cfd164fad2275983e2403e191c289648fd5a3d76d4451d44d13a589395427e0`;
  status `PASS`.
- Generator target/privacy firewall output SHA-256
  `e2fe6fdd8c87ff6f2299a25bf1b571e959bdabcbad7be8a75dba21b80023da67`;
  status `PASS`.
- Independent-verifier target/privacy firewall output SHA-256
  `39a2ca00dc49a84abdb55f72c60133b7ef2e22ab107f4a00bf6a0031f254c338`;
  status `PASS`.

The hashes are copied from the final staged artifacts; the actual SHA-256
values contain no spaces. No target, provider, cloud, incumbent predictive
data, canonical data, capture, scheduler, or production artifact was accessed
or modified.

## Next allowed action

No further SUSPSTATE retry is justified from the same interval source. A
future attempt would require a frozen overlap policy, row-level publication
timestamps, and an authoritative definition of the `NO_TRADE` state.
