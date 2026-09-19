# C3 Financial Capability Audit V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `D_C3_FINANCIAL_CAPABILITY`  
Result: `PASS_STRUCTURAL_ONLY / C3 REMAINS BLOCKED FOR ALPHA CLAIMS`

## Scope and boundary

This is an outcome-blind capability audit of the parked Financial PIT bundle.
It reads only the financial bundle, the corrected Stage A feature artifact, and
the frozen official-session calendar. It does not read targets, forward returns,
incumbent scores, provider/network data, or protected prospective outcomes.

The result describes source capability and governance completeness. It is not an
IC, ICIR, OOS, return, superiority, or promotion result.

## Source inventory

| Source | Rows / dates / tickers | SHA-256 | Classification |
|---|---:|---|---|
| Financial `bundle_rows.parquet` | 277,244 / 1,231 / 729 | `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b` | `PARTIAL_PARKED_CAPABILITY_ONLY` |
| Corrected Stage A features | joined to 310,761 eligible rows | `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4` | frozen structural artifact |
| Official sessions | 1,260 dates | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` | `FROZEN_ONLY` |

There are zero duplicate `(ticker,date)` keys in the financial bundle and zero
financial rows unmatched to the feature panel. Of the matched rows, 249,333 are
eligible and 27,911 are ineligible under the frozen structural mask.

## Capability funnel

| Gate | Rows | Dates | Tickers | Rate / interpretation |
|---|---:|---:|---:|---|
| Financial rows | 277,244 | 1,231 | 729 | source inventory |
| Core 3 fields finite | 70,520 | 525 | 321 | 25.44% of bundle rows |
| All 5 fields finite | 34,412 | 291 | 274 | 12.41% of bundle rows |
| All 5 + frozen valid/eligible | 30,994 | 291 | 265 | 9.9736% of 310,761 eligible rows |
| Usable Top-30 dates in economics view | — | 278 | — | sparse and late relative to 600-session window |

The five fields are liabilities/assets, cash/assets, net margin, YoY revenue,
and YoY total assets. Core 3 means the first three fields only. Adding either
YoY field reduces the finite support to the same 34,412 rows; the limiting
capability is therefore the YoY/provenance-complete subset, not the core ratio
fields alone.

## Missingness and governance findings

- 206,313 rows have no financial bundle feature state and are classified as
  `BUNDLE_FEATURE_MISSING` / `NO_FINANCIAL_STATE` for the five fields.
- The bundle status is `SELECTED` for 70,931 rows, `NO_FINANCIAL_STATE` for
  186,764 rows, and `UNRESOLVED_PERIOD_BOUNDARY` for 19,549 rows.
- 35,358 rows carry declared missing input for the two YoY fields; 741 rows
  carry `UNIT_MISMATCH`; 9 rows carry `AMBIGUOUS_SAME_TIME`; 411 rows carry
  `UNRESOLVED_INPUT`.
- 206,313 rows have missing knowledge timestamps, reporting version IDs,
  period dates, and attachment hashes. These rows are not admitted into the
  provenance-complete finite subset.
- No `same_bundle_violation` or `selected_knowledge_time_violation` was
  observed among the finite/provenance-complete subset.
- The validity funnel reports 34,412 rows with knowledge-time, period,
  provenance, same-bundle, and selected-knowledge gates all satisfied; after
  the frozen decision mask, 30,994 rows remain.

This supports a precise conclusion: the financial bundle contains a usable
structural capability island, but it is not population-complete enough for a
new-alpha historical comparison. Sparse rows must not be backfilled from an
unapproved provider or treated as neutral observations.

## Frozen-window result

The frozen six-hundred-session window is `2024-01-12` through `2026-07-31`.
The all-five finite subset covers 291 dates and 274 tickers before the frozen
eligibility mask, and 30,994 valid eligible rows / 265 tickers after the mask.
The period-stratum breakdown of all-five finite rows is:

| Stratum | Rows | Dates | Tickers |
|---|---:|---:|---:|
| `9M` | 12,205 | 354 | 275 |
| `FY` | 4,093 | 327 | 241 |
| `H1` | 9,389 | 432 | 251 |
| `Q1` | 8,725 | 414 | 245 |

The source contains 206,313 rows without a period stratum; these are not
silently assigned to a reporting period.

## Relation to C3 status

C3 remains `BLOCKED`, not because the financial mechanism has been disproven,
but because its available PIT/provenance support is sparse and partial. The
earlier structural economics result is consistent with this audit: 278 usable
Top-30 dates, 10.93% mean Top-30 turnover, and 25.77% Top-10 ticker slot share
are descriptive diagnostics only.

## Re-entry condition

C3 may re-enter the frozen historical comparison only after a separately
reviewed admission artifact establishes population completeness, historical-as-
of/PIT authority, identity/calendar coverage, corporate-action basis,
revision/vintage handling, and both required target horizons. The re-entry must
use the fixed C3 formula and common support; no sparse-period rescue, fallback
provider, or outcome-driven refit is allowed.

The mechanism-defined subset map is recorded in
`2026-09-19_C3_FINANCIAL_CONTRACT_MAP_RESULT_V1.md`. It confirms that a
quality-core capability island is broader, while any contract requiring either
YoY field falls back to the same 34,412-row bottleneck as all-five. This does
not change the fixed C3 contract or its `BLOCKED` status.

## Reproducibility

- Builder: `research/c3_financial_capability_audit_v1.py`
- Builder SHA-256: `ad7708bb25574f1f2736fa222b9d241acbba866846cada9dc99801a62976e8ae`
- Output: `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\c3_financial_capability_audit_v1.json`
- Output SHA-256: `4dfe048905acfeef7073a445d926e0c810ca8ebe47a6d1765e00264c67965c31`
- Script compilation: `PASS`
- Audit status: `PASS_STRUCTURAL_ONLY`
- `outcome_accessed`: `false`
- `target_accessed`: `false`
- `provider_accessed`: `false`
