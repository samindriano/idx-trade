# INC-001 CA capability verification continuation — V1.1

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Controlling implementation head: `077cc0299c4fcab0418da0614aac193600eb3ab2`

This is a continuation of V1.1 capability verification, not a new taxonomy or
scientific phase. It records bounded capability evidence only. No bulk
acquisition, Phase-E, provider expansion, outcome/target access, model work,
counter mutation, canonical rewrite, or merge was performed.

## Controlling capability artifact

```text
D:\Documents\Project\idx-ca-source-authority-capability-verification-20260829-v1
MANIFEST SHA-256: c8f7c1b39fa99bf4e7fa0075fadae2d88a89edb54cdde68c6de4fb87f105b24a
```

The artifact is the authoritative result for this bounded check. It preserves
the corrected KSEI raw bodies/ledgers, exact IDX request ledger including the
capture failure, retained official schedule PDFs, baseline pins, and the
capability matrix. It does not replace the controlling V1.1 reconstruction
root `D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8`.

## Evidence and verdicts

- KSEI: exactly three corrected ticker-specific GETs for AADI, ADRO, and AALI
  completed with status 200 and 140 visible source-native rows in total. The
  pages expose `Type of CA`, `Ratio`, `Cum Date`, `Record Date`, `Distribution
  Date`, and `Status`, but do not prove complete intervals, pagination
  behavior, provider as-of/observed-through semantics, or negative/no-event
  authority. Result: `KSEI_PAGE_COMPLETENESS=UNKNOWN`,
  `KSEI_PAGINATION_AUTHORITY=UNKNOWN`, `KSEI_NO_EVENT_AUTHORITY=UNKNOWN`,
  `KSEI_TEMPORAL_AUTHORITY=UNKNOWN`, `RETAINED_567_PROMOTABLE=UNKNOWN`,
  `KSEI_NEXT_BULK_PATH=NONE`.
- The earlier `/lc/=en-US` KSEI attempts were malformed and are excluded from
  assessment. No KSEI retry, redirect, pagination, or bulk request followed.
- IDX: the nine exact first-page category invocations were attempted, but a
  local capture/persistence defect retained neither response metadata nor raw
  bytes. This is not provider negative evidence. All category completeness,
  pagination, and negative-coverage authority remain `UNKNOWN`; no page 2+
  or bulk request was made.
- Retained schedules: `KSEI-9582/JKU/0524` is source-native
  `Pemisahan Unit Usaha` / TPIA buyback material and gives a 2024-05-20
  payment/transfer date; `KSEI-27597/JKU/1124` is source-native PUPS / ADRO
  material and gives 2024-11-29 recording, 2024-12-02 rights distribution,
  2024-12-05 AADI listing, and the offer/distribution period. Neither proves
  the required regular-market ex date or first-new-basis trading date.
  `KSEI-28171/JKU/1224` is retained ADRO context only, not a new request.
  Schedule lookup and exact transition semantic capability therefore remain
  `UNKNOWN`.
- Source-backed TPIA document deduplication remains proven only for the
  retained TPIA relationship; document counts are not an admission gate.

ADRO and AADI are both in the accepted 629 fit, 716 application, and 716
dependency-closure populations. Their 2024 candidate evidence is within the
accepted geometry, but no accepted transition boundary is certified. The
scientific verdict is unchanged:

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Gate and next action

```text
CAPABILITY_VERIFICATION_VERDICT = UNKNOWN
BULK_ACQUISITION_AUTHORIZED    = FALSE
PHASE_E_AUTHORIZED              = FALSE
REFIT_AUTHORIZED                = FALSE
COUNTER_ACTION                  = NONE
```

The next action is ChatGPT review of the immutable capability artifact. Any
future KSEI/IDX bulk acquisition or transition-document work requires a
separate explicit authorization. No production execution is authorized by
this checkpoint.
