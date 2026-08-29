# INC-001 unresolved economic-gap decomposition — V1 local handoff

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Artifact build source HEAD: `678b4fb4718dcb5c799bc81cab82a9689ac6ea1f`

## Scope and authority

This is a local-only, outcome-blind decomposition of the accepted certified
190-event economic reconciliation. It does not resolve events, change the
certified reconciliation, run Phase-E, call providers, access outcomes or
targets, fit/refit/score models, mutate counters, rewrite canonical history,
execute production work, or merge PR #103/#108.

The controlling inputs are unchanged:

- economic reconciliation V3:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v3`
  with manifest SHA-256
  `60d4b5caf9fbadd81c8f63edf4976f2d476ead6a26884c9d74f965759250a746`;
- source-authority V1.1 V8:
  `D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8`
  with manifest SHA-256
  `556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`.

The V3 and V1.1 V8 roots are immutable. Older roots are historical
intermediates only and are not controlling.

## Exact decomposition result

The starting ledger contains exactly 190 unique economic event IDs and 190
distinct constituent source rows. No unresolved economic event has multiple
source rows, so no source-row duplication or hidden within-event contradiction
was silently collapsed.

```text
SOURCE_EVIDENCE_ROWS            = 412
ECONOMIC_PHYSICAL_EVENTS        = 389
RESOLVED_TRANSITIONS            = 153
UNRESOLVED_TRANSITIONS          = 190
NON_BASIS_EXCLUDED              = 46

PRIMARY_REASON_COUNTS
  EXACT_TRANSITION_DOCUMENT_NOT_ACQUIRED       = 105
  DOCUMENT_RETAINED_TRANSITION_SEMANTIC_MISSING = 34
  ECONOMIC_TAXONOMY_UNRESOLVED                  = 51
  TOTAL                                          = 190
```

Family decomposition is:

```text
RIGHTS_HMETD                  52 exact-document-not-acquired
                              19 retained-page-insufficient
STOCK_SPLIT                   10 exact-document-not-acquired
                              11 retained-page-semantic-missing
REVERSE_SPLIT                  1 retained-page-semantic-missing
CAPITAL_RESTRUCTURING         19 exact-document-not-acquired
BONUS_SHARES                  11 exact-document-not-acquired
STOCK_DIVIDEND                 5 exact-document-not-acquired
                               2 retained-page-semantic-missing
MERGER                         5 exact-document-not-acquired
TRUE_SECURITY_CONVERSION       3 exact-document-not-acquired
                               1 retained-page-semantic-missing
UNKNOWN_TAXONOMY               4 economic-taxonomy-unresolved
UNRESOLVED_OPERATIONAL_LABEL  47 economic-taxonomy-unresolved
TOTAL                        190
```

All 22 split/reverse-split events remain unresolved. The independent
read-only audit found 22/22 source rows hash-matched, 14 unique retained raw
paths, zero exact retained transition documents for these tickers, and no
certified lower-bound/transition attestation. The exact stock-split partition
is 10 IDX `stockSplit` candidate rows versus 11 KSEI `Mandatory Conversion`
candidate rows. The one reverse-split event is BBRM, KSEI `Mandatory
Conversion`, ratio `(3 BBRM : 2 BBRM)`, with no reverse-split-specific
transition document. No record, distribution, candidate, or listing date was
promoted to `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE`.

For the 71 rights events, 52 IDX `hmetd` rows have a deterministic KSEI
registered-security lookup template known but not executed for this task; 19
KSEI `Right Distribution` rows are retained-page evidence without the
accepted `REGULAR_MARKET_EX_DATE` semantic. This is event-specific planning
evidence, not family-wide completeness.

The 47 KSEI `Voluntary Conversion` rows remain taxonomy unresolved. Their
retained ratios are blank, so the planning classification is
`NO_ECONOMIC_CLASSIFICATION_EVIDENCE`; this is not a conversion-family
promotion. The four `Mixed Dividend` rows remain `UNKNOWN_TAXONOMY` and are
not force-mapped to any new or existing family.

No local-only resolution candidate was found. The local candidate ledger is
empty because no unresolved split event has a retained exact official
first-new-basis schedule with valid source reference and SHA-256, and the
other families lack an already-accepted exact semantic sufficient to admit a
local change.

## Future acquisition geometry

The plan is separate from execution and partitions all 190 events exactly:

```text
SOURCE_CAPABILITY_PROBE_REQUIRED          0 event IDs; 3 representative ticker requests are a precondition
OFFICIAL_DOCUMENT_FETCH_DETERMINISTIC    22 event IDs (21 stock split + 1 reverse split)
OFFICIAL_INDEX_LOOKUP_REQUIRED            71 event IDs (rights)
AUTHORITATIVE_SOURCE_NOT_IDENTIFIED       46 event IDs (capital, bonus, stock dividend, merger, true conversion)
ECONOMIC_TAXONOMY_RESEARCH_REQUIRED      47 event IDs (operational labels)
POLICY_DECISION_REQUIRED                   4 event IDs (unknown taxonomy)
NO_PROVIDER_NEEDED_LOCAL_FIX               0 event IDs
```

The three representative capability-verification requests and any later bulk
acquisition are distinct. No request was executed here. The exact paths,
stop conditions, PASS definitions, and remaining UNKNOWN claims are in
`future_acquisition_units.json`.

## Separate authority blockers

These remain unchanged and independent of event-specific decomposition:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY          = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY              = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

The scientific state is unchanged:

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED      = FALSE
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Artifact and validation

Controlling decomposition root:
`D:\Documents\Project\idx-ca-unresolved-economic-gap-decomposition-20260829-v4`.

Deterministic rerun root:
`D:\Documents\Project\idx-ca-unresolved-economic-gap-decomposition-20260829-v4-rerun`.

Both roots contain the required seven data/summary outputs plus `MANIFEST.json`.
The seven non-manifest outputs are byte-identical between roots; each root's
manifest output-hash audit passes. The controlling root manifest SHA-256 is
`3af6a92738f560f26699725e2f8cf6200dc1dff3fcc6a79d899cb9911d6499bc`.

V1-V3 roots remain immutable historical intermediates only. V4 is the
authoritative result because it includes the corrected anomaly affected-event
identities and retained index-document linkage fields. The V4 rerun manifest
SHA-256 is
`157f958705402d80aaf88c5173dd9c2ee1d35083946ac99b333c9bcb8ed0c494`.

The source-bound anomaly findings are separate from the 190-event ledger:

- `ANOM-014`: one detached transition attestation joined only by a shared
  page hash (BBRM); hash-only joining is invalid.
- `ANOM-015`: two split-family rows (HEAL and SCMA) retain official index PDF
  hrefs but not the corresponding PDF bytes/hash-bound document rows.
- `ANOM-008` and `ANOM-011` remain UNKNOWN findings about parser/source
  absence and V1.1 family-conflict metadata; they do not add events.

The builder is the non-production audit tool
`scripts/build_inc001_unresolved_gap_decomposition_v1.py`. Its input pins,
source refs, raw paths, evidence SHAs, source contracts, population geometry,
and anomaly findings are retained in the artifact. No production module was
changed.

Validation performed before this handoff:

- exact 190-row decomposition checks: PASS;
- independent split/reverse-split read-only audit: PASS for evidence audit,
  NO-GO for local transition resolution;
- manifest output hash audit: PASS for both roots;
- deterministic comparison: 7/7 non-manifest files, PASS;
- py_compile of the new builder: PASS.

The CA/integrity suite, full pytest, final py_compile, diff-check, and
exact-head CI are reported in the final handoff. Stop for ChatGPT review; do
not merge or execute provider or scientific work.
