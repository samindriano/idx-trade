# INC-001 ZAPI Corporate Action Coverage-Contract Revalidation V1

Date: 2026-09-02 (Asia/Jakarta)

Status: `COMPLETE_WITH_RESIDUAL_BLOCKERS`

Decision: `NO-GO` for historical CA admission and INC-001 closure.

Classification: `3_MATERIAL_PARTIAL_CONTRACT_IMPROVEMENT_NOT_AUTHORITY_CLOSURE`

## Scope and pin

This is a new read-only audit branch based exactly on the controlling CA lane:

```text
repository: samindriano/idx-trade
base SHA: 0f6132ce55568565745aa68400295da4cba04e27
branch: audit/zapi-ca-coverage-contract-revalidation-v1
artifact: D:\Documents\Project\idx-ca-zapi-coverage-contract-revalidation-20260902-v1
artifact MANIFEST.json SHA256: a0ec3271be942e1005f9d9862ba9f3d6d0053d82b4b314ad78356d4df4efc83d
V17 manifest SHA256: 8d2139c9388c6b94c4131ca692f0de3add433c294e4a7b20f2db6d7f22b106e8
```

The V17 external artifact was verified before use and remained unchanged. No
V17 counts, runtime path, production workflow, outcomes, targets, features,
models, counters, PaperState, or provider state were mutated.

## Evidence capture

The audit retained 147 unique/repeat authenticated GET responses under the
external artifact `raw/` directory. HTTP results were 131 `200`, 5 `400`, and
11 `503`; no API key was written to evidence. The initial response parser was
corrected to unwrap the live ZAPI envelope (`data` for successful payloads,
`content` for errors). Only derived CSV/JSON/report files were regenerated;
raw response bytes were not overwritten. A three-call repeatability set was
added for five probes; normalized payload hashes were stable while raw hashes
differed because response timestamps changed.

Required matrices are present: `MANIFEST.json`, `request_index.csv`,
`endpoint_capability_matrix.csv`, `pagination_audit.csv`,
`window_partition_audit.csv`, `combined_vs_individual_audit.csv`,
`empty_result_audit.csv`, `coverage_semantics_audit.csv`,
`identity_history_audit.csv`, `revision_semantics_audit.csv`,
`transition_control_audit.csv`, `authority_requirement_reassessment.csv`,
`documentation_vs_live_matrix.csv`, `repeatability_audit.csv`,
`summary.json`, `REPORT.md`, and `README.md`.

## Capability change actually proven

The current public documentation and live behavior establish a material
operational change: `/v1/finance:idx/corporate-actions` accepts the five named
families `dividend`, `rights`, `additional-listing`, `delisting`, and
`new-listing`, with `from`/`to` month windows capped at twelve months,
pagination, and query coverage fields. Individual monthly family endpoints
also return bounded coverage fields. `/issued-history` returns listing-date
bounds, action, shares, and sharesAfter. The live public documentation is
`https://zpi.web.id/api/finance/idx`.

The current documentation also contains two material example inconsistencies:
a combined example requests `2025-11` through `2026-04` but displays a
`2025-05-01` start and twelve months; an issued-history example requests
`BBCA`/`Waran` but displays `INDF` `Stock Split`/`ESOP` rows. These are
documentation-contract uncertainties, not evidence of population completeness.

This is bounded query/source-scope capability. It is not a proof of whole IDX
population coverage, exhaustive no-event semantics, historical PIT/as-of
authority, revision lineage, or exact market-basis transition semantics.

## Findings

### Query completeness and negative authority

1. Successful combined responses expose `coverageStart`, `coverageEnd`,
   `segmentsRequested`, `segmentsAnswered`, `unpublishedMonths`,
   `completeForQuery`, `source`, totals, and pagination state.
2. `completeForQuery=false` is live and paired with `unpublishedMonths` for
   selected queries. Those rows are incomplete and cannot support a negative
   conclusion.
3. Unknown `ZZZZ` and malformed `!!!` both returned HTTP 200 with
   `total=0`, `completeForQuery=true`, and no unpublished months. The API does
   not first establish valid security identity before returning a green empty
   result.
4. Page-beyond-final probes returned HTTP 200 with empty `items`,
   `completeForQuery=true`, but retained non-zero totals (`BBCA` dividend 2;
   `INDF` issued-history 32). Empty pages are not empty event sets.
5. HTTP 503 is provider unavailability, not an empty result. The first nine
   stock-split controls were 503; one retry for each later returned HTTP 200.

Therefore `completeForQuery=true` is retained as a query/source-scope claim,
not real-world `NO_EVENT` authority. The fail-closed interpretation is
required for malformed identity, incomplete months, pagination anomalies, and
503 responses.

### Pagination and family reconciliation

BBCA dividend pagination returned two rows over page 1 and page 2 with
`hasMore=true` then `false`; the after-final page was empty while total stayed
2. For the tested BBCA window, the broad five-family combined results matched
the union of twelve monthly individual queries by normalized row hash, and
the two half-window partitions matched the broad query. This is a bounded
consistency observation only: no stable event ID or provider snapshot identity
was exposed.

The combined endpoint rejects `stock-split` with HTTP 400. Stock-splits must
remain a separate family; “all corporate actions” cannot be inferred from the
five-family combined response.

### Stock-split and transition controls

The recovered stock-split endpoint returns candidate rows with `actionCode`,
ratio, price-adjustment factor, nominal values, share counts, and
`listingDate`, but no `source`, coverage bounds, or `completeForQuery`.

| Control | Live candidate evidence | Effect on accepted transition |
|---|---|---|
| SMDR | `2023-01-31`, `1 : 5`, factor `0.2` | Date agrees with V17-resolved date; semantic is still not supplied by ZAPI. |
| DIVA | Two `1 : 2` rows at `2021-09-01` and `2021-09-02` | Duplicate/date identity ambiguity; issued-history exposes only `2021-09-02`. |
| TMAS | `2023-05-25`, `1 : 10` | Differs from accepted first-new-basis session `2023-05-23`. |
| TUGU | `2023-05-26`, `1 : 2` | Differs from accepted first-new-basis session `2023-05-24`. |
| BMRI | `2023-04-06`, `1 : 2` | Differs from V17 unresolved official control `2023-04-04`; issued-history also has same-date split and partial delisting rows on `2023-04-04`. |
| SKRN | `2023-01-06`, `1 : 5` | Matches candidate date, but exact transition remains unresolved in V17. |
| BBRM | `2022-02-18`, reverse split `3 : 2` | Differs from retained candidate `2022-02-17`; separate rights ex-date `2022-02-24` must not be conflated. |
| BBCA / GMFI | No row in tested month | Query-scope empty observation only. |

These results prove that ZAPI listing/event dates are discovery candidates, not
the accepted `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` semantic.

### Issued-history, PIT, and identity

INDF and SMDR issued-history calls initially returned 503 and recovered on
retry. The recovered data contains listingDate, action, shares, and
sharesAfter; every returned item lacks a stable event ID. It provides no
knowledge/as-of or vintage field, no active interval/relisting identity, no
revision/supersession lineage, and no guarantee that the returned rows are the
complete historical identity population. BMRI's two same-date actions and the
different BBRM historical HMETD row further show that action routes cannot be
collapsed into one transition authority.

### Revision and repeatability

Three repeat calls for combined BBCA dividend, individual BBCA December
dividend, BMRI issued-history, unknown ZZZZ, and SMDR stock-splits returned
identical normalized payload hashes. This demonstrates short-run retrieval
repeatability only. It does not prove immutable snapshot identity, correction
or deletion handling, version lineage, or historical as-of behavior.

## Requirement reassessment

Improved/partially supported requirements are query-scoped positive result
enumeration, per-response pagination mechanics, bounded coverage metadata,
and candidate issued/listing history. Remaining blockers are:

- population-wide identity/session coverage;
- explicit exhaustive real-world no-event authority;
- PIT/as-of identity, active intervals, and relisting semantics;
- revision/correction/version/supersession lineage;
- stable event identity across pages and retrievals;
- all Corporate Action family coverage, including stock-splits and
  restructuring/conversion families;
- exact first-new-basis regular-market transition semantics; and
- immutable provider/source snapshot authority.

The retained R3 gate therefore remains fail-closed. This audit changes the
classification of ZAPI from “old capability absent” to a material bounded
query-scope aid, but does not close the admission contract.

## Validation

`python -m py_compile scripts/audit_zapi_ca_coverage_contract_revalidation_v1.py`
passed. The focused regression suite passed: 60 tests in
`test_ca_source_authority_audit_v11.py`,
`test_ca_economic_event_reconciliation_v1.py`,
`test_ca_aware_feature_basis_reconciliation_v1.py`, and
`test_research_integrity_gate_v1.py`.

## Ownership and next bounded action

No runtime or production lane is changed by this audit. Keep ZAPI outside the
canonical transition authority path. The next bounded action is a provider
contract review that obtains explicit vendor guarantees (population scope,
identity, completeness/no-event, PIT/as-of, revision, and transition semantics)
or a separately authorized source-authority lane. Do not repin, backfill,
refit, score, or promote from this artifact.
