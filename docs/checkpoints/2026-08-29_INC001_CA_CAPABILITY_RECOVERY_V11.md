# INC-001 CA capability recovery — V1.1 continuation

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Implementation baseline: `077cc0299c4fcab0418da0614aac193600eb3ab2`

This is a bounded recovery continuation, not a new audit phase. It repairs the
local IDX evidence-capture path and verifies the existing capability scope.
No bulk acquisition, Phase-E, outcome/target access, model work, counter
mutation, canonical rewrite, taxonomy change, or merge occurred.

## Controlling recovery artifact

```text
D:\Documents\Project\idx-ca-source-authority-capability-recovery-20260829-v1
MANIFEST SHA-256: dd3331c960bf710c045cc2d77fe649eb8e438e1ace3eb291af4250e672e62819
```

The artifact contains the canary ledger, nine first-page transport ledger and
raw JSON bodies, parsed category summary, retained KSEI capability evidence,
retained TPIA/ADRO schedule documents, baseline pins, and capability matrix.
All 25 non-manifest entries match their recorded byte lengths and SHA-256
values.

## IDX recovery result

The prior nine invocations failed at local persistence because the capture
script used unsupported `New-Item -LiteralPath` and attempted to assign the
read-only PowerShell automatic variable `$Error`. This was an operational
capture failure, not provider negative evidence.

After correcting only those local handling defects:

- one exact `stockSplit` canary succeeded: HTTP 200, JSON content, 12,504 raw
  bytes, SHA-256 `dc0e8f940337d15f6f49f4ab9c2b05cfe547bfecc0724bd50399905791666236`;
- the nine previously authorized first-page requests each succeeded with
  HTTP 200, preserved raw bytes, valid SHA-256, and parsed JSON;
- `recordsTotal == recordsFiltered == first_page_rows` for every category,
  all totals were at most the frozen `length=250`, and the aggregate was 202
  rows;
- empty categories were `reverseStock`, `dividenSaham`, and `konversiSaham`.
  Their zero totals are not negative/no-event authority;
- no retry, redirect, page 2+, ticker expansion, or bulk request occurred.

Accordingly:

```text
IDX_CANARY_CAPTURE             = PROVEN
IDX_9_FIRST_PAGE_CAPTURE       = PROVEN
IDX_CATEGORY_COMPLETENESS      = PROVEN_FOR_EXACT_NINE_FILTERED_QUERIES_BY_RECORDS_TOTAL_SIGNAL
IDX_PAGINATION_AUTHORITY       = PARTIAL_FIRST_PAGE_TOTAL_SIGNAL_ONLY
IDX_NEGATIVE_COVERAGE_AUTHORITY= UNKNOWN
IDX_HISTORICAL_AS_OF_AUTHORITY = UNKNOWN
```

The `recordsTotal` signal is query-bounded evidence. It does not establish an
independent provider historical as-of contract or negative/no-event semantics.

## KSEI and schedule result

The three corrected ticker-specific KSEI GETs were not repeated. Retained
official interface evidence shows visible source-native rows but no provider
contract proving complete history, pagination absence, historical as-of, or
negative/no-event meaning. The controlling verdict is
`KSEI_CAPABILITY_NOT_PROVABLE_FROM_CURRENT_OFFICIAL_INTERFACE`; therefore
`RETAINED_567_PROMOTABLE=UNKNOWN` and `KSEI_NEXT_BULK_PATH=NONE`.

Retained official schedules only were inspected. TPIA `KSEI-9582/JKU/0524`
contains source-native `Pemisahan Unit Usaha` buyback/payment semantics.
ADRO `KSEI-27597/JKU/1124` contains source-native PUPS entitlement semantics
and the AADI listing date. Neither explicitly supplies
`REGULAR_MARKET_EX_DATE` or `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE`.
The exact transition result remains `UNKNOWN`. Retained TPIA document linkage
remains one underlying event; the 291 unresolved physical-event count is not
reduced.

## Scientific and authorization state

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED          = FALSE
```

The next action is ChatGPT review of the recovery artifact and exact-head CI.
No production execution or merge is authorized by this checkpoint.
