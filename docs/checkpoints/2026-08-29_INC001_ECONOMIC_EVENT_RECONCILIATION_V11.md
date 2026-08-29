# INC-001 retained economic-event reconciliation — V1.1 final local handoff

Date: 2026-08-29  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Repository HEAD: `d78e857bf608354d6384083466ca378170214d96`

## Scope and authority

This is a local, outcome-blind reconciliation of retained V1.1 source rows
and already-retained official document bytes. It is not a new acquisition or
scientific phase. No provider/network call, Phase-E, outcomes/targets access,
fit/refit/scoring, counter mutation, canonical historical rewrite, production
execution, or PR merge was performed.

The controlling upstream source-authority result remains the immutable V8 root
`D:\\Documents\\Project\\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8`
with manifest SHA-256
`556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`.
V6/V7 are immutable historical intermediates only and are not authoritative.

The controlling local reconciliation result is the new immutable root
`D:\\Documents\\Project\\idx-ca-economic-event-reconciliation-20260829-v3`
with manifest SHA-256
`60d4b5caf9fbadd81c8f63edf4976f2d476ead6a26884c9d74f965759250a746`.
Its deterministic comparison root is
`D:\\Documents\\Project\\idx-ca-economic-event-reconciliation-20260829-v3-rerun`.
The prior v1 rejected intermediate and v2 certified intermediate remain
immutable but are not controlling.

Pinned input evidence:

- source-authority V8 manifest: `556ab328...`;
- transition-capability probe manifest:
  `4949b9e501d0c751f9c7a51093daa88a0cbcb0da87d132836ffe0dd9894bc8dd`;
- merged IDX request ledger: `20 + 2 = 22` rows, continuous `1..22`, no
  duplicates, ledger SHA-256
  `9bbd03d9552aef8b57c455b1b673512f159796579c00845278134bee0f349004`;
- retained document ledger SHA-256
  `b79a2c8ddcfee1d2874d6a054b8620d1542be31a8f4a68ec8b34ee1e6d2606c7`.

The two continuation ledger rows are the already-retained July 2024 ALDO
index row and October 2024 ISAT index row. ALDO and ISAT document metadata was
bound to their existing local PDF/text bytes; no document was downloaded in
this continuation.

## Reconciled result

```text
SOURCE_EVIDENCE_ROWS             = 412
PROVEN_CROSS_SOURCE_COLLAPSES   = 20
PROVEN_SAME_SOURCE_COLLAPSES    = 3
ECONOMIC_PHYSICAL_EVENTS        = 389
RESOLVED_TRANSITIONS             = 153
UNRESOLVED_TRANSITIONS           = 190
NON_BASIS_EXCLUDED               = 46
WORKING_389_153_190_46_VERDICT   = CERTIFIED
```

The 25 linkage rows are source-evidence edges; their transitive arithmetic is
20 cross-source collapses and 3 same-source collapses. Every proven linkage,
adjudication, and resolved transition has a non-empty source reference and a
valid 64-hex evidence SHA-256. The 34 retained official documents (28
acquisition documents, 3 probe documents, and 3 retained schedule documents)
have zero hash failures.

The source-native adjudication remains conservative:

```text
MANDATORY_CONVERSION -> STOCK_SPLIT              33
MANDATORY_CONVERSION -> REVERSE_SPLIT            2
MANDATORY_CONVERSION -> TRUE_SECURITY_CONVERSION 4
VOLUNTARY_CONVERSION -> TENDER/CASH NON_BASIS    46
VOLUNTARY_CONVERSION -> UNRESOLVED                47
```

The 190 unresolved economic units are preserved in
`remaining_gap_geometry.csv` and are not silently promoted:

```text
RIGHTS_HMETD                  71
STOCK_SPLIT                   21
REVERSE_SPLIT                  1
CAPITAL_RESTRUCTURING         19
BONUS_SHARES                  11
STOCK_DIVIDEND                 7
MERGER                         5
TRUE_SECURITY_CONVERSION      4
UNKNOWN_TAXONOMY               4
UNRESOLVED_OPERATIONAL_LABEL 47
TOTAL                        190
```

## Physical census, forensic findings, and plan boundaries

The physical-event census remains distinct from forensic/taxonomy findings.
The five in-scope `gabungUsaha` rows remain physical census events. Outside
geometry and source-label findings remain forensic-only and do not inflate
event counts. Multiple TPIA documents are linked to one underlying event where
the retained evidence proves that relationship; document-count metadata is
not an additional admission requirement.

The retained KSEI result remains conservative: an observed parsed page is not
a source-certified complete interval without explicit retained completeness
semantics. No empty response, page observation, candidate date, recording
date, distribution date, listing date, or payment date is used as negative or
transition authority.

The original V1.1 future acquisition plan remains exactly 291 baseline
unresolved physical identities, separated from capability verification:

```text
RIGHTS_HMETD           72
STOCK_SPLIT            41
MANDATORY_CONVERSION   39
VOLUNTARY_CONVERSION   93
CAPITAL_RESTRUCTURING  19
BONUS_SHARES           11
STOCK_DIVIDEND          7
MERGER                  5
UNKNOWN_TAXONOMY        4
TOTAL                 291
```

This local reconciliation is not authorization to consume that plan. At the
evidence-reconciliation level, the arithmetic is
`291 - 32 promoted transitions - 46 non-basis exclusions - 23 proven
representation collapses = 190` unresolved economic units. Capability
verification requests and any later bulk acquisition remain separate; future
bulk work requires explicit authorization, exact identity coverage, and
source-defined completeness/empty/no-event semantics.

## ADRO -> AADI forensic finding

ADRO and AADI are present in the accepted 629 final-fit population, 716
application population, and 716 dependency closure. Retained evidence shows
an ADRO KSEI `Right Distribution` with ratio `4389 ADRO : 1000 ADRO-H`, a
separate ADRO `Cash Dividend`, and AADI `ipo` listing evidence. No retained
announcement or structural KSEI history row binds the entitlement to AADI.

The source-native evidence therefore does not prove a distribution-in-specie
or other structural separation entitlement. The separation interpretation is
`REQUIRES_POLICY_DECISION` / taxonomy `UNKNOWN`; it is not mapped to
`CAPITAL_RESTRUCTURING`, `SPIN_OFF`, `DEMERGER`, `PUPS_ENTITLEMENT`, or
`DISTRIBUTION_IN_SPECIE`. The event is not used to expand this lane. The
retained label audit also preserves exact `Pemisahan Unit Usaha` TPIA schedule
labels and seven `gabungUsaha` rows as unmapped forensic findings pending
source semantics and policy.

## Scientific and authorization state

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED      = FALSE
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation

- focused reconciliation tests: `7 passed`;
- all CA/integrity tests: `131 passed`;
- full pytest: exit `0`;
- `py_compile`: `46` Python files, PASS;
- manifest output hash audit: `14/14` PASS;
- deterministic v3/rerun comparison: `13` non-manifest files, PASS;
- `git diff --check`: PASS before final handoff commit;
- exact-head GitHub Actions: pending the post-handoff push; no merge is
  authorized.

Next gate: ChatGPT review of this immutable local reconciliation and handoff.
