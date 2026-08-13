# Foreign Flow Feature Contract V1 — Causal Remediation

Status: `REVIEW`

Branch: `research/idx-foreign-flow-feature-contract-v1`

Reviewed parent: `c000824f253fef41065edbe696811016d20392fe`

## Finding and fix

The independent review correctly found that
`foreign_gross_to_volume_1` used the current feature-session `buy`, `sell`,
and `volume` arrays instead of the prior flow-through session. It now uses
lagged arrays exactly aligned with the one-session rolling net feature:

`feature_session[i] = t+1`

`foreign_gross_to_volume_1[i] = (ForeignBuy[t] + ForeignSell[t]) / RegularVolume[t]`

No feature definition, source, model, outcome, or provider behavior was
otherwise changed.

## Regression coverage

Focused `tests/test_foreign_flow_features.py`: **9 passed**.

The tests now prove:

1. changing flow or volume on the feature session leaves every
   `FEATURE_COLUMNS` value unchanged for that row;
2. changing prior-session buy/sell changes the next-session gross feature by
   the exact formula;
3. all one-day and rolling features use only data through
   `flow_through_session`;
4. zero-volume and missing-flow behavior remains fail-closed.

The unrelated prior change to `tests/test_storage.py` was reverted. The exact
full repository command therefore reports the pre-existing storage expectation
mismatch:

- command: `python -m pytest -q` from this repository root;
- collected: 49;
- passed: 48;
- failed: 1;
- failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
  expects one conflict, while the existing source independently reports both
  `raw_close` and `vendor_adj_close` conflicts.

This feature lane does not alter that unrelated storage contract or test.

## Rematerialized artifacts

External root:
`D:\Documents\Project\idx-trade-foreign-flow-feature-contract-20260814-v1`

- feature parquet SHA-256:
  `059471948ad9efb5b2343d9aed729d04c5e3f2c01881153679db579b3a1d1733`;
- materialization manifest SHA-256:
  `8c45bb42cc9bda4002967f8bc5fd5509842947dbaa3e1f764e925cbe0f8ccd1a`;
- offline audit manifest SHA-256:
  `2341df7d7ff646dc8a13da2a45e9220e0c4c569017b373ca72daed18dcb377e4`;
- coverage rows: 1,102,650 / 979 tickers / 1,259 feature sessions;
- fully available: 964,078;
- partial: 137,592;
- missing: 980.

The old feature SHA
`fbfe79290270d3f9955a81366352e9b3615dd4bd61e73848bdb345154ac056f9` is no
longer authoritative.

## Exact archive-session gap

The 28 dates were derived as accepted-flow-session set minus official-volume-
session set, without weekday or calendar inference:

`2021-04-01`, `2021-04-05`, `2021-04-06`, `2021-04-07`, `2021-04-08`,
`2021-04-09`, `2021-04-12`, `2021-04-13`, `2021-04-14`, `2021-04-15`,
`2021-04-16`, `2021-04-19`, `2021-04-20`, `2021-04-21`, `2021-04-22`,
`2021-04-23`, `2021-04-26`, `2021-04-27`, `2021-04-28`, `2026-08-03`,
`2026-08-04`, `2026-08-05`, `2026-08-06`, `2026-08-07`, `2026-08-10`,
`2026-08-11`, `2026-08-12`, `2026-08-13`.

## Boundaries

No provider/network call, outcome access, performance testing, model fitting,
O2/forward-counter work, Financial PIT work, or Corporate Action work was
performed. The lane remains `REVIEW` pending independent review of the causal
fix and the pre-existing unrelated full-suite failure.
