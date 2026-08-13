# Official IDX Stock Summary Open Recovery — Result

Date: 2026-08-14  
Branch: `data/idx-open-official-stock-summary-recovery-v1`  
Source archive: `D:\Documents\Project\idx-trade-foreign-flow-historical-20260814-v1`

## Decision

`OFFICIAL_STOCK_SUMMARY_OPEN_RECOVERY_NO_ROWS_ADMITTED`

The archive is a complete, hash-verified official IDX Stock Summary capture for
1,288 sessions, but it does not contain a positive `OpenPrice` for any of the
43,800 global canonical missing-Open rows or the 12,589 clean V3-B missing-Open
rows. No recovery overlay row was therefore admitted. `FirstTrade` was not
used as a fallback because its semantic audit does not support treating it as
canonical Open.

## Source and integrity

The archive uses the official `TradingSummary/GetStockSummary` endpoint with
`date=YYYYMMDD`, and contains raw responses plus normalized artifacts. The
archive manifest SHA-256 is:

`fe9b8f64b6915f252502d114a06b107f3f9ea9b50205b0bacb47422f70834334`

| Property | Result |
|---|---:|
| Sessions | 1,288 |
| Date range | 2021-04-01 through 2026-08-13 |
| Raw rows | 1,129,024 |
| Unique ticker/session keys | 1,129,024 |
| Raw artifacts SHA-verified | 1,288 / 1,288 |
| `recordsTotal` = `recordsFiltered` | All sessions |
| Network/provider calls in this lane | 0 |

The accepted archive contains `OpenPrice`, `FirstTrade`, `High`, `Low`, and
`Close`. Archive rows were joined only by exact ticker and session date.

## Open-field semantic audit

The accepted canonical-known intersection contains 938,140 rows, all of which
were present in the raw archive. A positive candidate means finite and greater
than zero.

| Field | Positive candidates | Exact canonical Open | Exact rate among positive candidates | Positive candidates with exact H/L/C |
|---|---:|---:|---:|---:|
| `OpenPrice` | 261,155 | 258,514 | 98.9887% | 258,638 (99.0362%) |
| `FirstTrade` | 261,058 | 147,619 | 56.5464% | 258,541 (99.0358%) |

Across all 938,140 canonical-known rows, exact-match rates were 27.5560% for
`OpenPrice` and 15.7353% for `FirstTrade`; these denominators include the
source's non-positive values and are not admission rates.

### Positive-candidate exact-match rates by year

| Year | `OpenPrice` exact / candidates | Rate | `FirstTrade` exact / candidates | Rate |
|---|---:|---:|---:|---:|
| 2021 | 7,507 / 7,507 | 100.0000% | 4,338 / 7,507 | 57.7861% |
| 2022 | 11,054 / 11,054 | 100.0000% | 6,578 / 11,054 | 59.5079% |
| 2023 | 10,739 / 10,739 | 100.0000% | 6,166 / 10,739 | 57.4169% |
| 2024 | 16,755 / 16,755 | 100.0000% | 9,593 / 16,747 | 57.2819% |
| 2025 | 127,725 / 129,479 | 98.6453% | 73,382 / 129,414 | 56.7033% |
| 2026 | 84,734 / 85,621 | 98.9640% | 47,562 / 85,597 | 55.5650% |

`OpenPrice` is therefore the only defensible candidate for this recovery
contract. It is not a universal equality: 2,641 positive `OpenPrice` values
disagreed with canonical Open and 2,517 positive rows had an H/L/C mismatch.
Those rows remain excluded. `FirstTrade` has 113,439 positive-candidate Open
disagreements and is not a fallback.

Representative mismatch rows are preserved in the external audit files:
`openprice_mismatches.csv` and `firsttrade_mismatches.csv`.

## Recovery census

The canonical missing definition is `open` null/absent, not the separate
`open_available` eligibility flag.

| Scope | Input rows | Raw exact-key rows present | Admitted | Residual | Residual reason |
|---|---:|---:|---:|---:|---|
| Global accepted panel | 43,800 | 43,800 | 0 | 43,800 | `OPENPRICE_NONPOSITIVE_OR_INVALID` |
| Clean V3-B research/model universe | 12,589 | 12,589 | 0 | 12,589 | `OPENPRICE_NONPOSITIVE_OR_INVALID` |

Every residual row has an exact raw Stock Summary row and matching identity;
the blocking condition is that the raw `OpenPrice` is zero, non-positive, or
invalid. No `FirstTrade` fallback, price synthesis, forward fill, or corporate
action reconstruction was used.

The resulting derivative overlays are intentionally empty:

| Artifact | Rows | SHA-256 |
|---|---:|---|
| `official_stock_summary_open_recovery_overlay.parquet` | 0 | `a3eaeedb14c3e731f3f803cd3a42cf67a20e7c03099b5586f1aad08bd29df1a6` |
| `v3b_official_stock_summary_open_recovery_overlay.parquet` | 0 | `1ba429385f35a1db3035255c23e0f2663d40700b8e57ce8c0abca58e312ea24a6` |

The global and V3-B census CSV hashes are:

- `global_missing_open_recovery_census.csv`: `e1a1443adfcf153e4c9d281249bb9479df3f25a0c0a2802cf4d75a6e7e52407a`
- `v3b_missing_open_recovery_census.csv`: `abf7389862ea5b821fddd750329d7550d32cfe569b8ad8a24c574213074f15ef`

The corrected external census summary is 3,206 bytes with SHA-256
`7276c1e486baddb80d5faf5e577a5d1b434d06d9cc4f2461e787726417b7da58`.
The external artifact manifest is SHA-256
`e631686e7b9d296d29ba17adda534d53befdf4cab17d35288283c9bd2056d5d0`.

## Scope and non-changes

- The immutable canonical panel remains 981,940 rows with 938,140 known Open
  and 43,800 missing; input SHA-256 is
  `53f9b22fbb4a4ab26f35907a323fd258711c723ed38e6f9aa9fb6a601dd38fd3`.
- The V3-B support remains 292,633 rows / 737 tickers with 12,589 missing
  Open; input SHA-256 is
  `f23df38655fe6e628d225077377dac8680d9baadbeed6a8fee030ee87ad31084`.
- No canonical panel was rewritten.
- No Foreign Flow normalized artifact was changed.
- Yahoo/TradingView were not queried; their old evidence was not reopened.
- No Corporate Action source was used to reconstruct prices.
- No network, model, outcome, O2, forward-counter, Financial PIT, Intraday,
  or Frontend work was performed.

## Validation

Focused repository tests:

`python -m pytest -q tests/test_data.py tests/test_price_backfill.py tests/test_data_gate.py tests/test_adversarial_data_gate.py`

Result: **10 passed**.

Full suite collected 40 tests and ran to completion with **39 passed, 1
failed, 0 reported warnings**. The unrelated failure is:

`tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`

It expects one conflict, while the current shared storage behavior reports the
two independently auditable conflicts (`raw_close` and `vendor_adj_close`).
This lane did not modify storage semantics or that test.

## Review status

The evidence supports `OpenPrice` as an **OpenPrice-only candidate source** for
future bounded recovery, but the accepted archive cannot resolve the current
residual missing-Open rows. The lane is therefore submitted for independent
ChatGPT review with status `REVIEW`.
