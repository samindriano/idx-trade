# Financial PIT Feature Contract V1

**Status:** `REVIEW`

**Decision:** `FINANCIAL_PIT_FEATURE_CONTRACT_DESIGN_REVIEW_PERIOD_METADATA_BLOCKED`

This document defines a conservative, point-in-time-safe feature contract. It
does not authorize feature materialization, feature selection, model fitting,
alpha testing, outcome access, or changes to O2/V3-B.

## Authority and input boundary

The design uses only the accepted offline scientific-notation remediation
artifacts. No provider or network call was made in this lane.

| Artifact | SHA-256 |
|---|---|
| accepted remediation `MANIFEST.json` | `95db03c431dadb5a0af749fd63687f39c8a68d450d7dee17c4c5c53c5bf73d7b` |
| accepted `fact_records.jsonl` | `3cba29b53a8f3d68bae016adf59ffe3edb385c690b44d843a1790227b4152575` |
| accepted `filing_diagnostics.jsonl` | `a0a47d4fcfc58518ae97149722f4fb44c96b8c9430b51f1e9199bc09926fb5f4` |
| accepted `coverage.json` | `fcccd4eef062723a088f534b9b1a2b8e2016d3de150b39634622c7a4bb5ace1f` |
| accepted `summary.json` | `dc6c4e8f45829162ab9984292c5a706893e07c8b5761e8454c7ba3555cd7e316` |
| accepted `exclusions.json` | `209e9f2b2c8543b46c66023e5d29162d5db84dbfa7d86ee798388d07a4c7ec4c` |

The immutable source root is:

`D:\Documents\Project\idx-financial-pit-scientific-notation-remediation-census-20260813-v3`

The accepted source contains **5,965** PIT-ready filing diagnostics and
**37,246** extracted/diagnostic fact rows. The 143 scope-unresolved joins,
unsupported representations, ambiguous attachments, hash conflicts,
publication/linkage gaps, and provider failures remain outside the source
corpus and are not repaired here.

## Fact-shape contract

Every candidate input must retain its raw and normalized period metadata. A
fact is usable only when its shape and boundaries agree:

| Shape | Candidate facts | Required evidence |
|---|---|---|
| `INSTANT` | total assets, total liabilities, total equity, cash and cash equivalents | authoritative instant context (normally `CurrentYearInstant`) plus explicit `instant_date` or proven equivalent period-end date; no duration start |
| `DURATION` | revenue, net income, attributable net income, operating cash flow | authoritative duration context (normally `CurrentYearDuration`) plus explicit `period_start` and `period_end`; no instant date |

The context name alone is not enough. A source row with a shape but without
the explicit dates is `UNRESOLVED_PERIOD`, not a usable financial fact. The
current accepted v3 fact corpus has `period_kind`/context information but has
null `period_start`, `period_end`, and `instant_date` for all 37,246 rows.
Consequently, the dry-run is intentionally blocked from materialization.

## Reporting-period semantics

The accepted aliases are normalized without combining periods:

| Source alias | Normalized period | Meaning |
|---|---|---|
| `tw1` / `Q1` | `Q1` | cumulative year-to-date through Q1 |
| `tw2` / `H1` | `H1` | cumulative year-to-date through H1 |
| `tw3` / `9M` | `9M` | cumulative year-to-date through 9M |
| `audit` / `FY` | `FY` | fiscal-year duration / year-end instant as applicable |

Income-statement and cash-flow values are cumulative YTD. The contract never
sums `Q1 + H1 + 9M + FY`. A future standalone-quarter or TTM transformation
must prove exact boundaries and use a mathematically correct formula; it is
not part of this dry-run. If TTM is later authorized, the duration formula is
`FY(y-1) + YTD(y,p) - YTD(y-1,p)` for the same issuer, scope, concept,
currency/unit/scale, and comparable period `p`. Every component must be
knowable at the decision timestamp. TTM is never constructed from instant
facts.

YoY candidates match the same normalized period (`Q1` to prior-year `Q1`,
`H1` to prior-year `H1`, `9M` to prior-year `9M`, or `FY` to prior-year `FY`),
the same statement scope, fact identity, shape, currency/unit/scale and
applicability class. A prior filing published after the decision timestamp
makes the YoY value unavailable.

## Revision-aware as-of selection

For a decision timestamp `t`, the resolver considers only complete filing
versions with `knowledge_at <= t`, then selects the latest such version for
the logical issuer/period/scope key. Facts are never mixed across versions.
Distinct attachment hashes at the same effective knowledge timestamp are
`AMBIGUOUS_VERSION`. An earlier version remains valid only for an as-of point
before a later observed version; if the earlier version is not available, its
facts remain missing rather than being backfilled from the later filing.

Each available feature must preserve the exact input version IDs and
attachment hashes. The provenance chain also retains ticker, fiscal period,
scope, normalized shape/boundaries, publication and knowledge timestamps,
currency/unit/scale, taxonomy/version, source reference and location, source
artifact hashes, parser/contract version, decision timestamp, and the
applicability/availability decision.

## Missing values and denominator policy

Missing, unsupported, unresolved, or conflicting facts remain missing. The
contract does not zero-fill, carry forward, interpolate, use a different
statement scope, substitute a nearby label, apply an FX conversion, or add an
epsilon. An observed zero remains an observed zero; it is not silently changed.

Candidate denominator rules are explicit:

* `POSITIVE`: the denominator must be finite and strictly greater than zero;
  zero and negative values are unavailable with a denominator diagnostic.
* `NONZERO`: reserved for a future candidate that can justify signed
  denominators; zero is unavailable.
* negative numerators are retained when the denominator rule allows them.
* a negative equity denominator is not converted into an apparently stable
  profitability ratio.

## Candidate families and applicability

The following is a design inventory, not a performance-selected feature set.
No values were materialized in this lane.

| Family | Candidate IDs | Formula / shape |
|---|---|---|
| Size | `size_log_total_assets`, `size_log_revenue` | log of positive instant assets; log of positive duration revenue |
| Leverage / capital structure | `leverage_liabilities_to_assets`, `capital_equity_to_assets` | instant liabilities/assets and equity/assets |
| Liquidity | `liquidity_cash_to_assets` | explicit instant cash-and-equivalents/assets only |
| Profitability | `profitability_net_income_to_assets`, `profitability_attributable_income_to_equity` | cumulative duration income over explicit instant denominator |
| Cash-flow quality | `cash_flow_ocf_to_net_income`, `cash_flow_ocf_to_revenue` | cumulative duration OCF over same-period duration denominator |
| Margins | `margin_net_income_to_revenue` | cumulative duration net income/revenue |
| YoY growth | `yoy_revenue`, `yoy_net_income`, `yoy_total_assets` | same-period prior-year comparison; assets use instant shape |

The frozen candidate applicability matrix is:

| Candidate family / candidate | General | Financial | Financial/Sharia |
|---|---:|---:|---:|
| `size_log_total_assets` | eligible | eligible | eligible |
| `size_log_revenue` | eligible | not applicable | not applicable |
| `leverage_liabilities_to_assets` | eligible | eligible | eligible |
| `capital_equity_to_assets` | eligible | eligible | eligible |
| `liquidity_cash_to_assets` | eligible | eligible | eligible |
| `profitability_net_income_to_assets` | eligible | eligible | eligible |
| `profitability_attributable_income_to_equity` | eligible | eligible | eligible |
| `cash_flow_ocf_to_net_income` / `cash_flow_ocf_to_revenue` | eligible | not applicable | not applicable |
| `margin_net_income_to_revenue` | eligible | not applicable | not applicable |
| `yoy_revenue` | eligible | not applicable | not applicable |
| `yoy_net_income` / `yoy_total_assets` | eligible | eligible | eligible |

Unknown or unproven industry/taxonomy applicability is fail-closed. The
matrix does not claim that a balance-sheet ratio is a regulatory bank ratio;
it only defines what the bounded resolver may audit. A future model-safe
allowlist must separately approve statement scope. The conservative starting
recommendation is `GENERAL + CONSOLIDATED`; `FINANCIAL`,
`FINANCIAL_SHARIA`, and `SEPARATE` require a separate semantic review rather
than silent exclusion or mixing.

## Numeric grammar guard

The accepted extractor strips commas before strict `Decimal` parsing. The
regression test therefore locks `1,2E3` to **12000**, treating the comma as a
grouping separator under the existing grammar. It does **not** interpret the
input as locale decimal notation (`1.2 × 10^3`), and this contract adds no
locale-number guessing. Malformed exponents and nonnumeric text remain
rejected by the accepted parser.

## Offline availability dry-run

The reusable implementation is
`src/idx_trade/financial_feature_contract.py`. It builds filing versions from
the diagnostics (including diagnostics with no extracted core fact), checks
the contract in deterministic order, and emits only availability statuses and
provenance references—never feature values.

The run used a new external output root:

`D:\Documents\Project\idx-financial-pit-feature-contract-20260814-v2`

| Check | Result |
|---|---:|
| filing versions / logical keys | `5,965 / 5,965` |
| fact rows | `37,246` |
| instant / duration rows | `20,471 / 16,775` |
| rows with explicit valid boundaries | `0` |
| rows missing/invalid boundaries | `37,246` |
| available candidate feature rows | `0` |
| materialization gate | `BLOCKED_UNRESOLVED_PERIOD_METADATA` |
| network calls / protected outcomes | `0 / false` |

All feature status counts are persisted in `availability.json`. Because the
period-boundary check is deliberately before value construction, the run
does not claim that the zero available rows are economic sparsity; it says
the current artifact is missing the metadata needed to prove temporal shape.
For example, the balance-sheet candidate family records 4,696
`UNRESOLVED_PERIOD`, 1,259 `MISSING_INPUT`, 8 `UNRESOLVED_INPUT`, and 2
`UNRESOLVED_APPLICABILITY` rows per applicable candidate. OCF candidates show
2,929 `UNRESOLVED_PERIOD`, 1,263 `MISSING_INPUT`, 1,379
`UNRESOLVED_INPUT`, 392 `NOT_APPLICABLE`, and 2
`UNRESOLVED_APPLICABILITY`. The complete per-feature table is the hashed
external artifact.

Dry-run artifacts:

| File | SHA-256 |
|---|---|
| `availability.json` | `3e035b3576dfc36eff51a150271cd49a0721f9ade5b064e7ab172df465a9d97c` |
| `MANIFEST.json` | `2d998548c1da15862c78f4bdf36b46707a14b21d65532507dbf641ae55d62d70` |

This result supports contract review and identifies the next data repair
precisely: retain and validate explicit instant/duration boundaries in the
canonical fact artifact, then rerun a separate offline availability audit.
It does not authorize model work or protected-forward access.
