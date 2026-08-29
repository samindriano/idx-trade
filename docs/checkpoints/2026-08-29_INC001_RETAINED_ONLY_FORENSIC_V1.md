# INC-001 retained-only IDX forensic — V1.1 continuation

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`

This is a local, outcome-blind forensic follow-up to the accepted V1.1
reconciliation. No provider/network call, redundant IDX refetch, KSEI fetch,
291-event schedule acquisition, taxonomy expansion, Phase-E, outcome/target
access, model work, counter mutation, canonical rewrite, or merge occurred.

## Controlling evidence

The already-pushed reconciliation commits were verified equal with origin at
`6d9e26a5b902d52c96487cad8a491596c3af4e2e`. Exact-head CI run `33238608143`
completed successfully with 334 passed and one non-blocking Node.js 20 action
warning.

The new forensic artifact is immutable and controlling for this check:

```text
D:\Documents\Project\idx-ca-source-authority-retained-only-forensic-20260829-v1
MANIFEST SHA-256: 0e5c49e4f7ca443bc382cce9698c469ed68134dc365d2e6def24371bf8cd3019
```

It is derived from the prior reconciliation root, the retained raw IDX pages,
and the already captured current exact-query bodies. No bytes were acquired.

## Six retained-only rows

All six rows are inside the accepted 716 application population and closure
geometry. The old source query used `caType=` (blank) with the full date range
`dateFrom=20180101&dateTo=20260814`; the current query uses the category-specific
`caType` with the same date range and `start=0&length=250`.

| ID | Ticker | Source-native label | Candidate date | Frozen family | Old page/ref SHA | Current exact query | Scope equivalence |
|---|---|---|---|---|---|---|---|
| 19811 | PDPP | `Dividen Saham` | 2023-12-21 | STOCK_DIVIDEND | `caType=` `start=250`, SHA `b5b0f96d...` | `dividenSaham`, total 0, SHA `6932ae0d...` | FALSE |
| 22961 | RCCC | `Dividen Saham` | 2024-07-10 | STOCK_DIVIDEND | `caType=` `start=0`, SHA `9606312c...` | `dividenSaham`, total 0, SHA `6932ae0d...` | FALSE |
| 45220 | KLAS | `Dividen Saham` | 2024-11-29 | STOCK_DIVIDEND | `caType=` `start=0`, SHA `9606312c...` | `dividenSaham`, total 0, SHA `6932ae0d...` | FALSE |
| 82369 | WINS | `Dividen Saham` | 2026-06-18 | STOCK_DIVIDEND | `caType=` `start=0`, SHA `9606312c...` | `dividenSaham`, total 0, SHA `6932ae0d...` | FALSE |
| 82782 | SPMA | `Dividen Saham` | 2026-07-30 | STOCK_DIVIDEND | `caType=` `start=0`, SHA `9606312c...` | `dividenSaham`, total 0, SHA `6932ae0d...` | FALSE |
| 82860 | PACK | `obligasiWajibKonversi` | 2026-08-12 | MANDATORY_CONVERSION | `caType=` `start=0`, SHA `9606312c...` | `obligasiWajibKonversi`, total 2 (`82055`, `16622`), SHA `aaea7a88...` | FALSE |

The full refs, full 64-hex SHA values, capture timestamps, exact parameter
maps, raw paths, and returned payloads are in `retained_only_forensics.csv`.
The old capture timestamps are `2026-08-13T17:23:50.475491Z` for ID 19811 and
`2026-08-13T17:23:50.415388Z` for the other five. The old raw pages were
`idx_issued_all_250.json` for 19811 and `idx_issued_all_0.json` for the other
five.

## Disappearance alternatives

```text
RETAINED_ONLY_QUERY_SCOPE_EQUIVALENT = 0/6
RETAINED_ONLY_TRUE_DISAPPEARANCE_COUNT = 0
IDX_HISTORICAL_SNAPSHOT_MONOTONICITY = UNKNOWN_NOT_EQUIVALENT_QUERY_SCOPES
IDX_CURRENT_SNAPSHOT_NEGATIVE_AUTHORITY = UNSUPPORTED_BY_OBSERVED_SOURCE_BEHAVIOR
```

Evidence-based disposition of the alternatives:

| Alternative | Disposition |
|---|---|
| true source snapshot non-monotonicity | UNKNOWN; no old/current scope-equivalent pair exists |
| different `dateFrom/dateTo` | Ruled out; both use 20180101–20260814 |
| different `caType` | Confirmed; old is blank `caType=`, current is category-specific |
| category migration | Unproven; no same ID appears in another current category |
| source row ID mutation | Unproven; no direct linkage to a new ID exists |
| field mutation causing identity mismatch | Unproven; no directly corresponding current row exists |
| previous deduplication bug | Not observed; all 708 old raw rows have unique IDs and each retained row is present |
| current reconciliation bug | Not observed; independently verified stable-ID union is 130 common, 72 live-only, 6 retained-only |

The current `dividenSaham` zero result cannot negate the five old positive rows.
The current `obligasiWajibKonversi` positive result also does not contain
`82860`; this is observed source behavior under a non-equivalent query scope,
not proof of a historical snapshot failure. All positive source-bound rows are
preserved and remain valid evidence.

## Live-only sanity check

All 72 live-only rows are excluded from physical-event addition:

```text
outside application and closure geometry = 14
outside application scope                = 34
outside closure geometry                 = 24
inside accepted physical-event scope    = 0
```

No live-only ticker can affect the accepted 716 dependency closure through
cross-sectional membership. No population expansion occurred.

## Unresolved transition decomposition

This is a read-only decomposition of the accepted 291-event reconstruction;
no schedule acquisition was performed. Every unresolved row has candidate-date
evidence (`291/291`) and none has exact transition evidence locally (`0/291`).
The exact family/source table is in `unresolved_transition_decomposition.csv`.

```text
UNRESOLVED_BY_FAMILY =
BONUS_SHARES=11, CAPITAL_RESTRUCTURING=19, MANDATORY_CONVERSION=39,
MERGER=5, RIGHTS_HMETD=72, STOCK_DIVIDEND=7, STOCK_SPLIT=41,
UNKNOWN_TAXONOMY=4, VOLUNTARY_CONVERSION=93

UNRESOLVED_BY_SOURCE =
IDX_GET_ISSUED_HISTORY=136, KSEI_REGISTERED_SECURITY_HISTORY=155
```

The missing semantic for each family/source unit is an exact event-linked
`REGULAR_MARKET_EX_DATE` or `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE`, or
a separately validated source-specific transition lower bound with accepted
source status, source ref, and valid evidence SHA. Candidate dates do not meet
that requirement.

## Remaining gap decomposition

| Gap | Exact requirement | Proven capable source | Status |
|---|---|---|---|
| EVENT_DISCOVERY_COMPLETENESS | Full 716 application/closure identity-by-family positive or source-certified no-event coverage, with ref/SHA/date-level attestation | IDX exact nine-query positive result sets only | PARTIAL |
| NEGATIVE_NO_EVENT_AUTHORITY | Source-defined exhaustive zero/no-event semantics per family, identity scope, and interval | None | `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED` |
| HISTORICAL_ASOF_AUTHORITY | Source-defined historical as-of/publication boundary bound to query, ref, and raw SHA | None | `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED` |
| EXACT_TRANSITION_SEMANTICS | Exact event linkage plus accepted regular-market transition semantic or certified lower bound | None for remaining 291 | `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED` |
| CROSS_SOURCE_CONFLICTS | Source-contract adjudication of three conflicting family/date identities with retained refs/hashes | None | `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED` |
| TAXONOMY_POLICY | Raw label, entitlement/basis semantics, authoritative refs/hashes, and explicit policy decision | None | `AUTHORITATIVE_SOURCE_NOT_YET_IDENTIFIED` |

The exact source requirements and the “no invented source” rule are also
recorded in `remaining_gap_decomposition.csv`.

## Frozen evidence-union invariant

Historical CA evidence is append-only and source-bound:

- newer snapshots may add evidence;
- a newer snapshot must not erase previously hash-bound official evidence merely
  because a row disappears;
- conflicts or mutations must be surfaced, not silently replaced; and
- positive evidence and negative/no-event authority are separate concepts.

This is limited to the existing evidence union and does not redesign the
Research Integrity framework.

## Authorization and stop

```text
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED           = FALSE
REFIT_AUTHORIZED             = FALSE
COUNTER_ACTION               = NONE
```

Return for ChatGPT review and stop. Do not perform provider/network calls,
redundant IDX fetches, KSEI fetch/bulk, 291-event schedule acquisition,
taxonomy expansion, Phase-E, outcomes/targets, model work, counter mutation,
canonical rewrites, or PR #103/#108 merge.
