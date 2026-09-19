# FILINGAGE-01 Financial Reporting-Age Surface — Result V1

Date: 2026-09-19 (Asia Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `SOURCE_PARTIAL_STRUCTURAL_SIGNAL / NOT_ADMITTED / NO CANDIDATE`

## Decision

The financial bundle contains a coherent reporting-age field that is worth
preserving as a future information-arrival hypothesis, but it is not admitted
as alpha data. The field is arithmetically reproducible from the source
timestamps and has a distinct low-overlap structural signature versus C1/C2/C4.
Coverage is partial and starts only in 2024; population-wide PIT/publication,
revision/vintage, and identity authority remain unresolved.

No C3A/C3B/C5 ID, target, outcome, IC, ICIR, OOS, predictive comparison, or
packet expansion was created.

## Source quality profile

- Source: `D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run3\bundle_rows.parquet`.
- Rows: `277,244`; tickers: `729`; dates: `1,231`.
- Source date range: `2021-06-02` through `2026-07-17`.
- Duplicate `(ticker,date)` keys: `0`.
- All bundle rows joined to the frozen panel and feature artifact: `100%`.
- Statuses: `186,764` `NO_FINANCIAL_STATE`, `70,931` `SELECTED`, and
  `19,549` `UNRESOLVED_PERIOD_BOUNDARY`.
- Non-null reporting-age rows: `70,931`, across `525` dates and `322` tickers.
- Reporting-age availability: `2024-04-30` through `2026-07-17`; it does not
  cover the full 2021–2026 panel.
- Eligible age rows: `64,817`, across `525` dates and `311` tickers.
- Provenance-bearing rows (knowledge time, version, attachment, period date):
  `70,931`; the remaining `206,313` rows lack these fields.

Validity checks all passed:

- age values finite and nonnegative;
- age present only on `SELECTED` rows;
- knowledge time is not after decision time;
- declared age equals
  `decision_timestamp_utc - bundle_reporting_knowledge_at_utc` within `1e-9`
  days (maximum observed absolute difference `4.8149e-10` days);
- official-session and panel/feature joins are complete.

These checks establish internal consistency only. They do not prove public
availability at the exchange, revision completeness, issuer continuity, or
that the recorded knowledge timestamp is an independently authoritative
publication timestamp.

## Target-free structural signature

Registered recency surface: `recency = -bundle_filing_age_days`, with lower
age meaning more recent information. On the latest 600 official sessions,
only `505` dates had at least 30 eligible finite names.

Mean daily Spearman of recency versus existing structural scores:

| Surface | C1 | C2 | C4 |
|---|---:|---:|---:|
| FILINGAGE-01 recency | `0.00107` | `0.01890` | `-0.00162` |

Mean Top-30 overlap:

| Surface | C1 | C2 | C4 |
|---|---:|---:|---:|
| FILINGAGE-01 recency | `12.3366%` | `13.1419%` | `11.0957%` |

Recency Top-30 bottom-market-value Q1 share was `20.7525%` across `15,150`
selected slots. These are structural composition observations, not evidence
of predictive orthogonality or usefulness.

## Interpretation and blockers

The source supports a distinct information-arrival/reporting-staleness
question, separate from the current C3 quality/growth values. However:

- source coverage is late and incomplete;
- source semantics are not independently documented as public availability;
- historical revision/vintage behavior is not established;
- issuer/security identity and corporate-action basis remain unresolved;
- missing rows cannot be filled, forward-carried, or treated as neutral.

Disposition: `FUTURE_RESEARCH / CONTRACT_PENDING`, not `ADMISSIBLE` and not a
candidate. A future contract would need explicit available-at, revision/vintage,
identity, period, and missingness rules before any target evaluation.

## Independent verification and firewall

- Generator: `research/alpha_filingage01_source_audit_v1.py`; SHA-256
  `baa4e196d8a225f971c63c75b2c7ef10bed5baa3cd8b83c7b5adea848e11db5a`.
- Artifact SHA-256:
  `21325d1ff017c706454d61662135823f3f341af89e73e651c70fcb929b8f6aeb`.
- Independent verifier: `research/verify_alpha_filingage01_source_audit_v1.py`;
  SHA-256 `3255ffa5dcca56b2a6840f9b565c3dcfee303e42883955357b7d23c29f9d0258`.
- Independent verification: `PASS`; output SHA-256
  `88a757d2d347d537c9cc210909bba16fcec4132fd2304b81d8cccec323332af5`.
- Artifact hash-contract: `PASS`; output SHA-256
  `c7805e1969e2b1191fc4ff6c2466dba608bd9d2df681ab2dd4713daefe083cef`.
- Generator target/privacy firewall: `PASS`; output SHA-256
  `966aa9141d6e933a7112093ae283250ec43ac1abc7f2cfbe5ec9ea7b76726cb3`.
- Independent-verifier target/privacy firewall: `PASS`; output SHA-256
  `b9128c28820032a0fa980147870342d7bf872fd466da72412ea3f68415e447f7`.
- Financial source SHA-256:
  `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`.

All access flags are false for outcome, provider, cloud, incumbent predictive
data, and candidate creation.

## Next allowed action

Do not create a candidate or run protected evaluation from this result. The
highest-value follow-up is a source-contract review of public availability,
revision/vintage, issuer identity, and historical population coverage. If
those gates cannot be independently established, retain FILINGAGE-01 as a
documented partial capability and do not retry with imputation or provider
fallback.
