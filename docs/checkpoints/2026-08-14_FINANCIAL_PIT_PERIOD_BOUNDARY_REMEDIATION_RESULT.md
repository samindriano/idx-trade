# Financial PIT Period-Boundary Remediation V1

**Status:** `REVIEW`

**Decision:** `FINANCIAL_PIT_PERIOD_BOUNDARY_REMEDIATION_COMPLETE_WITH_3_FAIL_CLOSED_FILINGS`

## Scope

This lane followed the accepted Financial PIT Feature Contract V1 and used
only the immutable local scientific-notation remediation census and its
already-captured attachments. It made zero network/provider calls, did not
redownload, did not derive feature values, and did not access outcomes or
models.

The accepted fact corpus remains unchanged. Exact period evidence is stored in
an external manifest-pinned sidecar and consumed by the availability dry-run.

## Source and artifact identity

Accepted inputs:

| Artifact | SHA-256 |
|---|---|
| `fact_records.jsonl` | `3cba29b53a8f3d68bae016adf59ffe3edb385c690b44d843a1790227b4152575` |
| `filing_diagnostics.jsonl` | `a0a47d4fcfc58518ae97149722f4fb44c96b8c9430b51f1e9199bc09926fb5f4` |
| accepted census `MANIFEST.json` | `95db03c431dadb5a0af749fd63687f39c8a68d450d7dee17c4c5c53c5bf73d7b` |

New external sidecar root:
`D:\Documents\Project\idx-financial-pit-period-boundary-20260814-v3`

| Sidecar artifact | SHA-256 |
|---|---|
| `period_boundaries.jsonl` | `f29f50b86100c23c5407325f02d6f42e8d7d03dc9d5779c5da1d2763c20a4168` |
| `summary.json` | `46da80d1564220babf90a9165dc6dcdf2bc8b5c918eded903d82112e1680a6d9` |
| `MANIFEST.json` | `798bba02b8b37c06e2a6e7bd133103df00fbfcccebb2612b9d47facf11e97b49` |

Feature availability output root:
`D:\Documents\Project\idx-financial-pit-feature-contract-20260814-period-sidecar-v3`

| Dry-run artifact | SHA-256 |
|---|---|
| `availability.json` | `0f29944bc3bcd657e38d371848bdfc799ef85edf04dbf7ec59dad89cd1b98d30` |
| `MANIFEST.json` | `902919263ff7009afe3a64bc39601f259a6972d97840a21ab780894bf59cd68d` |

## Boundary contract and recovery

Instant facts require an exact visible-XLSX end-date cell or an explicit
IDX-DEI `CurrentPeriodEndDate` fact in `CurrentYearInstant`. Duration facts
require exact start and end evidence from the same filing. The sidecar records
the source sheet/cell or XBRL context/location and attachment SHA for every
recovered boundary.

| Measure | Result |
|---|---:|
| filing versions | `5,965` |
| instant recovered | `5,965 / 5,965` |
| duration recovered | `5,962 / 5,965` |
| fully recovered | `5,962 / 5,965` |
| XLSX / XBRL | `5,963 / 2` |
| fact rows | `37,246` |
| fact rows with verified boundaries | `37,239` |
| fact rows unresolved for period metadata | `7` |

The full sidecar matrix is keyed by year, Q1/H1/9M/FY, scope,
representation, and template/industry family. The three unresolved filing
cases are:

* `LEAD` H1 2024: visible XLSX start `2024-09-27` is later than end
  `2024-06-30`; the source is retained as evidence but duration is rejected.
  No accepted canonical fact row is attached to this version.
* `UNVR` Q1 2026: visible XLSX start `2026-04-30` is later than end
  `2026-03-31`; its three duration facts are rejected. Instant facts retain
  the exact end date.
* `VTNY` H1 2026: XBRL contains the exact IDX-DEI end fact `2026-06-30` but
  no current-period start fact; duration facts remain unresolved.

No boundary was inferred from report labels, filenames, fiscal period names,
publication dates, or a later/earlier period.

## Availability dry-run

The manifest-pinned sidecar was validated before the dry-run. The conservative
model-safe scope is enforced as `GENERAL + CONSOLIDATED`; other scopes and
industries remain audit-only. No feature values were materialized.

Available rows by candidate:

| Candidate | Available |
|---|---:|
| `size_log_total_assets` | 3,258 |
| `size_log_revenue` | 3,246 |
| `leverage_liabilities_to_assets` | 3,258 |
| `capital_equity_to_assets` | 3,258 |
| `liquidity_cash_to_assets` | 3,258 |
| `profitability_net_income_to_assets` | 3,258 |
| `profitability_attributable_income_to_equity` | 3,133 |
| `cash_flow_ocf_to_net_income` | 1,502 |
| `cash_flow_ocf_to_revenue` | 2,093 |
| `margin_net_income_to_revenue` | 3,246 |
| `yoy_revenue` | 1,609 |
| `yoy_net_income` | 1,219 |
| `yoy_total_assets` | 1,618 |

Missing, unresolved, conflicting, non-positive-denominator, and non-applicable
rows remain separately classified in `availability.json`; no zero-fill or
synthetic imputation was used.

## Safe duration policy

`size_log_revenue`, `profitability_net_income_to_assets`, and
`profitability_attributable_income_to_equity` are cumulative-duration-sensitive
and are restricted to exact same-period strata with matching boundaries. Q1,
H1, 9M, and FY are not pooled or summed. No annualization or TTM formula is
introduced in this lane. A separate frozen normalization contract is required
before any cross-period comparison.

## Validation and decision

Focused boundary, feature-contract, and fact-table tests: `42 passed`.
Full repository pytest: `548 passed, 0 failed, 3 warnings, 27.94s`.
This lane remains `REVIEW` pending ChatGPT review; no feature
materialization, performance testing, model fitting, protected outcome access,
O2 change, network call, or redownload occurred.
