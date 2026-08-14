# Financial PIT Alpha V1 preregistration

Status: `OUTCOME_BLIND_SUPPORT_CENSUS_COMPLETE_REVIEW_REQUIRED`

This document freezes the data join and comparison design before any model fit
or performance metric is opened. It is not an authorization to train or score.

## Parent artifacts

- Clean V2 historical-development support: `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_remediation1_retry1\outcome_blind_common_support.parquet`
  - SHA-256: `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
  - 277,244 rows, 729 tickers, session indices 20..1250.
  - This is the clean V2 support parent. No V3-B/O2 lineage is used.
- Accepted Financial PIT feature panel:
  - SHA-256: `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`
  - External manifest SHA-256: `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140`.
  - Scope is restricted to `GENERAL` + `CONSOLIDATED` and the frozen 13-feature family.

## Frozen as-of join contract

The clean V2 support stores a normalized session date rather than an intraday
decision timestamp. The frozen deterministic cutoff is:

`SESSION_DATE_END_ASIA_JAKARTA_UTC_EXACT`

That is the final nanosecond of the Asia/Jakarta civil session date, converted
to UTC. A Financial state is eligible only when its
`reporting_knowledge_at_utc <= decision_timestamp_utc`. The panel's
`as_of_timestamp_utc` is retained as provenance but is not used as a substitute
for the knowledge-time gate.

For each V2 row, ticker, fiscal year, feature, and period stratum, the join
selects the latest eligible state by `reporting_knowledge_at_utc`. Before the
first eligible filing, the feature remains missing. Same-knowledge-time
conflicting versions are marked ambiguous and do not fall back to an earlier
or later value. Later revisions replace an earlier version only from their own
knowledge timestamp onward.

This contract is intentionally limited by the date-only V2 parent: a future
experiment requiring an earlier intraday cutoff needs a separate frozen
timestamp contract.

## Feature and period rules

Only these 13 accepted features are in scope:

`size_log_total_assets`, `size_log_revenue`,
`leverage_liabilities_to_assets`, `capital_equity_to_assets`,
`liquidity_cash_to_assets`, `profitability_net_income_to_assets`,
`profitability_attributable_income_to_equity`, `cash_flow_ocf_to_net_income`,
`cash_flow_ocf_to_revenue`, `margin_net_income_to_revenue`, `yoy_revenue`,
`yoy_net_income`, `yoy_total_assets`.

Q1, H1, 9M, and FY remain separate strata. Cumulative duration facts are not
pooled across period lengths; no Q1+H1+9M+FY summation, annualization, TTM,
interpolation, carry-forward across unresolved states, zero-fill, or synthetic
imputation is allowed. Negative or zero-denominator and unresolved inputs stay
non-available according to the accepted panel status.

Every selected state retains ticker, fiscal year/period, scope, feature and
period stratum, panel as-of timestamp, filing version, attachment SHA,
publication/knowledge timestamps, exact period evidence, representation,
source references/locations, and fact identities.

## Future comparison contract (not run here)

After independent review of this preregistration and the support census, freeze
one exact row-identity set before opening any performance result. All later
candidates must use that same set and the inherited chronological/purge
semantics of clean V2. The preregistered comparison is:

1. clean V2 baseline on the frozen Financial experiment support;
2. Financial-only, only if review confirms it is scientifically meaningful;
3. clean V2 plus the frozen Financial PIT family.

Missing-value handling must be frozen before metrics. No post-result tuning,
feature additions, rescue candidate, or cross-lane combination is permitted.
Foreign Flow, Corporate Actions, intraday, sector, Path Risk, V3-B, and O2
are outside this experiment.

No target, outcome, F5/F6, fresh-forward, model fit, or performance metric was
accessed in this preregistration stage.
