# Financial PIT Feature Contract V1

**Status:** `DONE`

**Decision:** `FINANCIAL_PIT_FEATURE_CONTRACT_V1_ACCEPTED_PERIOD_BOUNDARY_REMEDIATION_NEXT`

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
must first receive a separate frozen normalization contract. No annualization
or TTM formula is authorized here; exact boundaries alone do not justify
mixing cumulative periods of different lengths. TTM is never constructed from
instant facts.

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

## Offline availability dry-run (pre-sidecar baseline; superseded)

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

## Period-boundary remediation V1

This section supersedes the pre-sidecar dry-run above. The feature contract
was accepted with decision
`FINANCIAL_PIT_FEATURE_CONTRACT_V1_ACCEPTED_PERIOD_BOUNDARY_REMEDIATION_NEXT`.
The remediation uses a separate, exact provenance-bound sidecar and does not
rewrite the accepted fact corpus.

### Evidence contract

The sidecar accepts only evidence from the actual immutable filing bytes:

* visible XLSX sheet `1000000`, with the bilingual current-period date label
  and its same-row value cell recorded as `sheet=...;label_cell=...;value_cell=...`;
* explicit `idx-dei:CurrentPeriodStartDate` and
  `idx-dei:CurrentPeriodEndDate` inline-XBRL facts in the official IDX-DEI
  namespace and `contextRef=CurrentYearInstant`.

Period labels, filenames, fiscal year, publication time, and Q1/H1/9M/FY
aliases are never used to invent a boundary. Conflicting or chronologically
impossible source dates remain unresolved. Instant end dates may remain usable
for instant facts when the duration start is invalid; duration facts require
both exact dates.

### Pinned offline artifacts

The source diagnostics and facts are the accepted immutable artifacts listed
above. The attachment root was read locally; `network_calls=0` and
`redownloads=0`.

| Artifact | SHA-256 |
|---|---|
| `period_boundaries.jsonl` | `f29f50b86100c23c5407325f02d6f42e8d7d03dc9d5779c5da1d2763c20a4168` |
| sidecar `summary.json` | `46da80d1564220babf90a9165dc6dcdf2bc8b5c918eded903d82112e1680a6d9` |
| sidecar `MANIFEST.json` | `798bba02b8b37c06e2a6e7bd133103df00fbfcccebb2612b9d47facf11e97b49` |
| feature availability `availability.json` | `0f29944bc3bcd657e38d371848bdfc799ef85edf04dbf7ec59dad89cd1b98d30` |
| feature availability `MANIFEST.json` | `902919263ff7009afe3a64bc39601f259a6972d97840a21ab780894bf59cd68d` |

External roots:

* `D:\Documents\Project\idx-financial-pit-period-boundary-20260814-v3`
* `D:\Documents\Project\idx-financial-pit-feature-contract-20260814-period-sidecar-v3`

### Boundary recovery census

| Measure | Result |
|---|---:|
| filing versions | `5,965` |
| instant boundaries recovered | `5,965 / 5,965` |
| duration boundaries recovered | `5,962 / 5,965` |
| fully recovered filing versions | `5,962 / 5,965` |
| XLSX / XBRL representations | `5,963 / 2` |
| canonical fact rows | `37,246` |
| fact rows with explicit verified boundaries | `37,239` |
| fact rows unresolved for period metadata | `7` |
| protected outcomes / feature values / model work | `false / false / false` |

The sidecar summary contains the complete recovery matrix by year, normalized
period (`Q1/H1/9M/FY`), statement scope, representation, and template/industry
family. The aggregate filing view is:

| Year | Period | Versions | Fully recovered | Consolidated | Separate | XLSX | XBRL |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2024 | Q1 | 306 | 306 | 230 | 76 | 306 | 0 |
| 2024 | H1 | 588 | 587 | 425 | 163 | 587 | 1 |
| 2024 | 9M | 620 | 620 | 456 | 164 | 620 | 0 |
| 2024 | FY | 661 | 661 | 485 | 176 | 661 | 0 |
| 2025 | Q1 | 602 | 602 | 451 | 151 | 602 | 0 |
| 2025 | H1 | 693 | 693 | 511 | 182 | 693 | 0 |
| 2025 | 9M | 572 | 572 | 430 | 142 | 572 | 0 |
| 2025 | FY | 674 | 674 | 496 | 178 | 674 | 0 |
| 2026 | Q1 | 662 | 661 | 494 | 168 | 662 | 0 |
| 2026 | H1 | 587 | 586 | 432 | 155 | 586 | 1 |

The three fail-closed filing boundaries are:

* `LEAD` H1 2024 XLSX: the visible source cells report start
  `2024-09-27` and end `2024-06-30`; chronology is impossible. The filing has
  no canonical fact rows in the accepted fact corpus.
* `UNVR` Q1 2026 XLSX: visible source cells report start `2026-04-30` and
  end `2026-03-31`; the three duration facts are unresolved. Exact instant
  facts retain the independently recovered `2026-03-31` instant boundary.
* `VTNY` H1 2026 XBRL: the exact IDX-DEI end fact is present for `2026-06-30`
  in `1000000.html`, but no authoritative current-period start fact is
  present. Duration facts remain unresolved; no start date is inferred.

### Post-sidecar availability dry-run

The rerun validates the manifest-pinned sidecar before building in-memory
availability statuses. It does not materialize feature values. The
model-safe contract is enforced as `GENERAL + CONSOLIDATED`; Financial,
Financial/Sharia, Separate, and unknown applicability remain audit-only or
fail-closed.

| Candidate | Available | Main fail-closed diagnostics |
|---|---:|---|
| `size_log_total_assets` | 3,258 | missing 960; unresolved input 8; not applicable 1,737 |
| `size_log_revenue` | 3,246 | missing 965; non-positive denominator 7; unresolved input 8 |
| `leverage_liabilities_to_assets` | 3,258 | missing 960; unresolved input 8; not applicable 1,737 |
| `capital_equity_to_assets` | 3,258 | missing 960; unresolved input 8; not applicable 1,737 |
| `liquidity_cash_to_assets` | 3,258 | missing 960; unresolved input 8; not applicable 1,737 |
| `profitability_net_income_to_assets` | 3,258 | missing 960; unresolved input 8; not applicable 1,737 |
| `profitability_attributable_income_to_equity` | 3,133 | missing 960; non-positive denominator 125; unresolved input 8 |
| `cash_flow_ocf_to_net_income` | 1,502 | missing 963; unresolved input 1,160; not applicable 1,737 |
| `cash_flow_ocf_to_revenue` | 2,093 | missing 968; non-positive denominator 5; unresolved input 1,160 |
| `margin_net_income_to_revenue` | 3,246 | missing 965; non-positive denominator 7; unresolved input 8 |
| `yoy_revenue` | 1,609 | missing 2,574; unit mismatch 31; unresolved input 8 |
| `yoy_net_income` | 1,219 | missing 2,569; denominator non-positive 399; unit mismatch 31 |
| `yoy_total_assets` | 1,618 | missing 2,569; unit mismatch 31; not applicable 1,737 |

### Safe period policy

Exact boundaries make temporal shape auditable, but they do not authorize
annualization. The three cumulative-duration-sensitive candidates
(`size_log_revenue`, `profitability_net_income_to_assets`, and
`profitability_attributable_income_to_equity`) remain **period-stratified** by
the exact normalized period and boundary pair. Q1, H1, 9M, and FY are never
pooled or summed. A future normalization or TTM formula requires a separate
frozen contract and evidence that every component was knowable at the
decision timestamp. The safest current policy is therefore same-period
stratification, not an invented annualization adjustment.

No feature-performance testing, model fitting, protected-outcome access, O2
change, provider call, or network/redownload operation occurred in this lane.
