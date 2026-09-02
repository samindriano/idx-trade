# Handoff: INC-001 CA capability recovery V1.1

from: MAIN / Codex
to: ChatGPT review
task_id: `INC001-CA-CAPABILITY-RECOVERY-V11`
branch: `data/ca-aware-feature-basis-remediation-v1`
implementation baseline: `077cc0299c4fcab0418da0614aac193600eb3ab2`

## Decision

`NO-GO for bulk / capability partially recovered`: the IDX transport capture
failure is fixed and the exact bounded nine-category first-page evidence is
now retained. This proves only a query-bounded `recordsTotal` signal. KSEI
full-history capability remains unproven, negative/no-event authority remains
unknown, and exact schedule transition semantics remain unknown.

## Immutable recovery evidence

```text
D:\Documents\Project\idx-ca-source-authority-capability-recovery-20260829-v1
MANIFEST SHA-256: dd3331c960bf710c045cc2d77fe649eb8e438e1ace3eb291af4250e672e62819
```

The prior V1.1 reconstruction root remains controlling for the event census:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8
MANIFEST SHA-256: 556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71
```

## IDX evidence

The failed capture was local: unsupported `New-Item -LiteralPath` plus a
collision with PowerShell's read-only `$Error` variable. The exact canary and
the nine frozen requests were rerun only after this handling correction.

Canary:

```text
https://www.idx.id/primary/ListingActivity/GetIssuedHistory?caType=stockSplit&dateFrom=20180101&dateTo=20260814&start=0&length=250
HTTP 200; 12,504 bytes; SHA-256 dc0e8f940337d15f6f49f4ab9c2b05cfe547bfecc0724bd50399905791666236
```

Nine categories:

```text
stockSplit, reverseStock, hmetd, dividenSaham, sahamBonus,
obligasiWajibKonversi, konversiSaham, kurangModal, gabungUsaha
```

All nine are HTTP 200, JSON-parsed, and raw/hash retained. Their response
totals match returned rows and are within 250; aggregate rows are 202. The
three zero-total categories are not source-defined no-event proof. No page 2+
request was necessary because every `recordsTotal` was within the exact first
page length.

```text
IDX_CAPTURE_FAILURE_ROOT_CAUSE = LOCAL_CAPTURE_PERSISTENCE_BUG_FIXED
IDX_CANARY_CAPTURE             = PROVEN
IDX_9_FIRST_PAGE_CAPTURE       = PROVEN
IDX_CATEGORY_COMPLETENESS      = PROVEN_FOR_EXACT_NINE_FILTERED_QUERIES_BY_RECORDS_TOTAL_SIGNAL
IDX_PAGINATION_AUTHORITY       = PARTIAL_FIRST_PAGE_TOTAL_SIGNAL_ONLY
IDX_NEGATIVE_COVERAGE_AUTHORITY= UNKNOWN
```

## KSEI and schedule evidence

The three prior KSEI GETs were not repeated. Retained official interface
evidence proves visible positive rows only, not complete history, pagination,
provider as-of, or negative/no-event semantics. Verdict:

```text
KSEI_SOURCE_CONTRACT_EVIDENCE = RETAINED_OFFICIAL_INTERFACE_VISIBLE_ROWS_ONLY
KSEI_CAPABILITY_VERDICT       = KSEI_CAPABILITY_NOT_PROVABLE_FROM_CURRENT_OFFICIAL_INTERFACE
KSEI_NO_EVENT_AUTHORITY        = UNKNOWN
KSEI_TEMPORAL_AUTHORITY        = UNKNOWN
RETAINED_567_PROMOTABLE        = UNKNOWN
KSEI_NEXT_BULK_PATH            = NONE
```

Only retained official TPIA/ADRO documents were inspected. TPIA contains the
source-native `Pemisahan Unit Usaha` buyback/payment schedule; ADRO contains
source-native PUPS entitlement to acquire AADI shares. Neither document
explicitly provides the required regular-market ex-date or first-new-basis
trading date. Schedule lookup and exact transition semantics are `UNKNOWN`.
The TPIA multi-document relationship remains source-backed deduplication of
one event; the 291 unresolved physical-event count is unchanged.

## Authorization and scientific verdict

```text
SCHEDULE_EXPLICIT_TRANSITION_SEMANTICS = UNKNOWN
SOURCE_BACKED_EVENT_DOCUMENT_DEDUP_AVAILABLE = PROVEN_RETAINED_TPIA_ONLY
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED           = FALSE
REFIT_AUTHORIZED             = FALSE
COUNTER_ACTION               = NONE

DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
```

Review the recovery artifact and exact-head CI, then stop. Do not start KSEI
716/residual-149 acquisition, IDX pagination/backfill, 291-event schedule
acquisition, Phase-E, outcome access, model work, counter mutation, canonical
rewrite, taxonomy expansion, or merge PR #108/#103.
