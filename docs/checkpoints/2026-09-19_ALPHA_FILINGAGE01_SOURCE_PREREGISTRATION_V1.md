# FILINGAGE-01 Financial Reporting-Age Surface — Preregistration V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PARTIAL_SOURCE_DIAGNOSTIC / NOT_ADMITTED / NO CANDIDATE`

## Question

Does the parked financial bundle contain a sufficiently coherent historical
reporting-age / information-arrival surface to preserve as a future research
direction distinct from the existing C3 quality/growth values, or is it too
sparse or provenance-incomplete to use even for a bounded structural map?

This is a source-capability and target-free structural audit. It cannot produce
IC, ICIR, OOS, P&L, candidate superiority, survivor status, or a C5/C3A ID.

## Registered surface and source

- Source:
  `D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run3\bundle_rows.parquet`.
- Registered field: `bundle_filing_age_days`.
- Registered interpretation under test: elapsed days from
  `bundle_reporting_knowledge_at_utc` to `decision_timestamp_utc`, with lower
  values meaning more recent information. This interpretation is checked for
  arithmetic consistency only; it is not treated as proof of public
  availability or exchange dissemination.
- Expected grain: one financial bundle row per `(ticker,date)`.
- Comparison sources: frozen panel, official 1,260-session calendar,
  tradability anchors, and the corrected structural feature artifact.
- Existing C3 quality/growth fields remain comparison context only; no formula
  rescue or C3 contract change is authorized.

## Frozen checks

1. Inventory row count, columns, dtypes, date/ticker range, duplicate keys,
   official-session membership, and panel/feature join coverage.
2. Validate required-field completeness, status alignment, finite/nonnegative
   age values, timestamp parseability, `knowledge_time <= decision_time`, and
   exact arithmetic agreement between the age field and timestamp difference.
3. Report age coverage by date/ticker, first/last availability, missingness
   trend, bundle status distribution, provenance/version/attachment coverage,
   and cross-sectional breadth on official sessions.
4. On the eligible decision universe only, report fixed descriptive
   distributions, age/recency Top-30 concentration, bottom-value Q1 exposure,
   and daily structural rank/Top-30 overlap against C1/C2/C4. These are not
   candidate tests and use no target or outcome.
5. Preserve exact source/code/input hashes and explicit access flags.

## Fail-closed rules

- Missing knowledge time, version, attachment, or period identity is not
  backfilled or treated as neutral.
- Arithmetic consistency of the age field does not establish PIT/publication
  authority, revision/vintage completeness, issuer identity, or market-open
  availability.
- Coverage beginning in 2024 cannot be generalized to the full 2021–2026
  panel.
- No clipping, winsorization, forward fill, provider fallback, parameter
  sweep, target proxy, candidate ID, packet expansion, or status upgrade.
- Any key, timestamp, negative-age, status, or official-calendar failure makes
  the result `SOURCE_BLOCKED`; otherwise it may be `SOURCE_PARTIAL`, but never
  `ADMISSIBLE` from this audit alone.

## Decision outcomes

- `SOURCE_PARTIAL_STRUCTURAL_SIGNAL`: source arithmetic and grain are coherent
  enough to preserve a bounded future hypothesis, while admission gaps remain.
- `SOURCE_BLOCKED`: material grain, timestamp, status, join, or validity failure.
- `SOURCE_REDUNDANT`: no distinct reporting-age surface remains after the
  preregistered structural checks.
