# V4 CA Blocker Attribution V2 — Preregistration

Status: `ACTIVE / OUTCOME-BLIND DIAGNOSTIC ONLY`

Branch: `data/idx-v4-ca-blocker-attribution-v2`
Scientific/code-test anchor: `7a70f0643296019bc7bf3150137b65b000a0b344`
Scientific parent: `data/idx-v4-ksei-coverage-gap-remediation-v1@8414ff04f4e89afafd07a55b7065e0f585bb7235`

## Purpose

Recompute blocker attribution after the targeted KSEI remediation recovered 31
of 43 previously unresolved histories and introduced additional observed CA
evidence. The V1 attribution result is stale for current prioritization.

This is not a continuity certification replay. Every non-baseline scenario is
an optimistic row-level upper bound over blocker reasons already present in the
post-remediation ledger.

## Frozen input

Full continuity ledger SHA-256:

`9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`

Expected identity:

- 344,790 rows
- 610 tickers
- 600 signal dates
- horizons exactly H5 and H10

Expected blocker reason counts:

- `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL`: 312,294
- `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED`: 24,212
- `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED`: 6,844
- `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY`: 1,200
- `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`: 240

Expected baseline before any optimistic assumption:

- H5 passing dates: 462/600; minimum 0.8814102564
- H10 passing dates: 461/600; minimum 0.8789808917
- consensus passing dates: 461/600; minimum 0.8789808917

Any mismatch is a hard stop.

## Frozen scenarios

1. `BASELINE`
2. `SCHEDULE_ONLY_CEILING`
3. `KSEI_COVERAGE_ONLY_CEILING`
4. `CROSS_SOURCE_ONLY_CEILING`
5. `ALL_COVERAGE_CEILING` = KSEI coverage + cross-source
6. `SCHEDULE_PLUS_KSEI_COVERAGE_CEILING`
7. `SCHEDULE_PLUS_CROSS_SOURCE_CEILING`
8. `SCHEDULE_PLUS_ALL_COVERAGE_CEILING`

The runner reports all per-date H5/H10/consensus gate counts, minimum rates,
worst dates, assumed newly-resolved rows, and the inclusion-minimal scenario(s)
whose optimistic ceiling reaches 600/600 for all three metrics.

## Non-waivable blocker

All 240 rows with
`TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` remain unresolved in every
scenario. The runner rejects any attempted scenario that includes that reason.

## Interpretation

A clearing scenario means only that resolving that *currently observed*
blocker dimension is mathematically capable of clearing the frozen 90% gate.
It is not evidence that acquisition/remediation will actually clear the gate,
because newly recovered evidence may expose new mechanical events or schedule
requirements.

## Hard boundaries

- provider/network calls: prohibited
- KSEI retry/acquisition: prohibited
- schedule acquisition: prohibited
- CA semantic or gate changes: prohibited
- universe/date identity changes: prohibited
- R5/R10 or target-rank materialization: prohibited
- model fit/prediction/IC/performance/bootstrap: prohibited
- protected/fresh-forward outcome access: prohibited

STOP after the single offline attribution result for ChatGPT review.
