# Broker / Margin Source Live Audit — Independent Review

Date: 2026-08-13 (Asia/Jakarta)
Reviewed branch: `data/broker-margin-source-audit-v0`
Reviewed HEAD: `567ec03e6cb73d602c4abde2d9062916aee61f61`

## Decision

`BROKER_MARGIN_SOURCE_LIVE_AUDIT_ACCEPTED_MARGIN_FLOW_REJECTED`

The bounded 2026-07-14 source audit is accepted as decision-valid for its stated scope.

## Accepted findings

- Zapi `margin-summary` is a faithful wrapper of the official IDX `GetMarginSummary` endpoint for the audited period: 220/220 rows exact on date and all audited metrics.
- Zapi `stock-summary` is a faithful wrapper of the official IDX `GetStockSummary` endpoint: 965/965 rows exact.
- All 220 Margin Summary securities are members of the applicable 326-name official margin-eligible list.
- Literal H2 (`All Stock rows/metrics filtered only by eligibility`) is rejected for this date: 106 eligible names are absent from Margin Summary, including 100 with positive All Stock activity, and all-six metric equality is 0/220.
- H1 (`actual margin-financed transaction flow`) is not supported. The official public source exposes generic market-summary fields and no financing-account, margin-loan, collateral, financed amount, or margin-position field.
- Value/Volume/Frequency in Margin Summary never exceed same-date All Stock on the common universe, but that inequality alone does not identify the underlying reporting semantics.
- Historical PIT/publication/knowledge timing remains unresolved; the returned period date must not be treated as first-knowable or publication time.

## Operational interpretation

The safest accepted description is:

**official IDX Margin category/reporting view over a subset of margin-eligible securities, with the exact inclusion and aggregation semantics not yet certified.**

It must not be described or used as:

- margin usage;
- margin financing flow;
- leverage intensity;
- crowding intensity;
- financed-volume/value share;
- margin-position or collateral information.

## Research boundary

No bulk historical acquisition, automation, feature generation, or model experiment is justified from this lane now.

If this source is revisited, it should be under a new, separately specified category/membership research question with a defensible PIT/effective-time contract. It should not be reopened as a margin-flow lane without new official source evidence that explicitly identifies financed transactions.

## Final status

The V0 source audit is complete and may be closed. The source itself may remain PARKED for possible future category-level research, but the margin-flow hypothesis is rejected under the current evidence.
