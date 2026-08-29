# Handoff: INC-001 CA capability verification continuation V1.1

from: MAIN / Codex  
to: ChatGPT review  
task_id: `INC001-CA-CAPABILITY-VERIFICATION-V11`  
branch: `data/ca-aware-feature-basis-remediation-v1`  
implementation head: `077cc0299c4fcab0418da0614aac193600eb3ab2`

## Decision

`NO-GO / UNKNOWN`: bounded capability verification did not establish a
source-authoritative full-scope path. The retained 567 KSEI captures remain
unpromoted. This handoff records no bulk acquisition and no scientific or
production execution.

## Immutable evidence

Controlling capability root:

```text
D:\Documents\Project\idx-ca-source-authority-capability-verification-20260829-v1
MANIFEST SHA-256: c8f7c1b39fa99bf4e7fa0075fadae2d88a89edb54cdde68c6de4fb87f105b24a
```

Controlling V1.1 reconstruction remains:

```text
D:\Documents\Project\idx-ca-source-authority-audit-20260829-v11-deterministic-rerun-v8
MANIFEST SHA-256: 556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71
```

## Bounded request result

### KSEI

Exactly these three corrected GETs were completed, with no retry,
redirect, pagination, or bulk request:

```text
https://web.ksei.co.id/services/registered-securities/shares/lc/AADI?setLocale=en-US
https://web.ksei.co.id/services/registered-securities/shares/lc/ADRO?setLocale=en-US
https://web.ksei.co.id/services/registered-securities/shares/lc/AALI?setLocale=en-US
```

The raw response SHA-256 values are, respectively,
`861f892e182c74c744c134fbcfe46159a7abf49e3deb7f5248e44330b538cedc`,
`ed1db63cc538e6dc4d316ea3722e71036fb2c7dc0c50a1142b5e1d05dedd69b3`, and
`878f04d84acfd48bbdb86ab38b75a349c5ed716354057ec89c6d678598185a41`.
They prove positive visible rows only. Completeness, pagination, as-of,
negative/no-event, and full-family authority are all `UNKNOWN`.

### IDX GetIssuedHistory

The nine frozen first-page categories were invoked with
`dateFrom=20180101`, `dateTo=20260814`, `start=0`, `length=250`:

```text
stockSplit, reverseStock, hmetd, dividenSaham, sahamBonus,
obligasiWajibKonversi, konversiSaham, kurangModal, gabungUsaha
```

A local capture/persistence defect retained no response status, body, or
hash. The artifact records the exact URLs and failure reason. This is a
capture failure, not provider negative evidence; all IDX authority fields are
`UNKNOWN`. No retry or page 2+ request was made.

### Retained official schedules

Only retained official bytes were inspected; no fresh schedule request was
issued. `KSEI-9582/JKU/0524` contains the TPIA source-native
`Pemisahan Unit Usaha` buyback/payment semantics, including 2024-05-20
payment/transfer. `KSEI-27597/JKU/1124` contains ADRO source-native PUPS
semantics: 4,389 ADRO shares yield 1,000 rights, each usable to buy one AADI
share, with 2024-11-29 recording, 2024-12-02 distribution, and 2024-12-05
AADI listing. Neither document supplies an accepted
`REGULAR_MARKET_EX_DATE` or `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE`.
Schedule lookup and exact-transition capability remain `UNKNOWN`.

## Scope and authorization

ADRO and AADI are in fit/application/closure (`629/716/716`). Their candidate
evidence can intersect accepted geometry, but the transition boundary remains
uncertified. The existing 291 unresolved physical transition events and the
frozen taxonomy are unchanged. TPIA retained document linkage remains a
single physical event; document count is not a new admission requirement.

```text
RETAINED_567_PROMOTABLE     = UNKNOWN
KSEI_NEXT_BULK_PATH         = NONE
SCHEDULE_LOOKUP_CAPABILITY  = UNKNOWN
EXACT_TRANSITION_SEMANTICS  = UNKNOWN
BULK_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED           = FALSE
REFIT_AUTHORIZED             = FALSE
COUNTER_ACTION               = NONE
```

Scientific verdict remains `DATA_ADMISSION=FAIL`,
`RESEARCH_ADMISSION=FAIL`, `MODEL_PROMOTION=NOT_EVALUATED`,
`HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN`,
`REFIT_AUTHORIZED=FALSE`, `COUNTER_ACTION=NONE`.

Review the artifact and stop. Do not merge PR #108/#103, run Phase-E, acquire
bulk data, access outcomes, fit/refit/score, mutate counters, rewrite
canonical history, or expand taxonomy under this handoff.
