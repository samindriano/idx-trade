# V4 CA Blocker Attribution V1 — Preregistration

Status: `FROZEN_FOR_ONE_OFFLINE_DIAGNOSTIC_RUN`

Parent result: `data/idx-v4-ca-residual-document-continuity-replay-v1@489891211b872e7f0c561f85af1cb8221f4d00ef`.

## Purpose

The final Stage-B continuity replay remains blocked at minimum H5/H10/consensus rates `0.8237179487 / 0.8216560510 / 0.8216560510`. Before any new CA acquisition or semantic work, quantify which current blocker dimension is mathematically capable of clearing the frozen 90% per-date gate.

This lane is diagnostic only. It consumes the immutable Stage-B full continuity ledger and computes optimistic row-level ceilings. It does not reconstruct hidden downstream blockers, does not reclassify any event, and cannot certify continuity.

## Frozen input

Full Stage-B ledger:

`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2\v4_frozen_continuity_ledger_event_window.csv`

Required SHA-256:

`585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`

Expected identity: 344,790 rows / 610 tickers / 600 signal dates / horizons {5,10}.

## Frozen blocker reasons

- residual schedule uncertainty: `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED`;
- KSEI history coverage: `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED`;
- cross-source conflict: `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY`;
- known mechanical crossing: `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION`.

The known-mechanical-crossing reason is **never waived in any scenario**.

## Frozen scenarios

1. `BASELINE`.
2. `SCHEDULE_UNKNOWN_RESOLVED_CEILING` — optimistic assumption that every currently schedule-unknown row becomes resolved.
3. `KSEI_COVERAGE_RESOLVED_CEILING` — optimistic assumption that every currently KSEI-coverage-blocked row becomes resolved.
4. `ALL_COVERAGE_RESOLVED_CEILING` — KSEI coverage plus cross-source blocker rows resolved.
5. `SCHEDULE_PLUS_KSEI_COVERAGE_CEILING`.
6. `SCHEDULE_PLUS_ALL_COVERAGE_CEILING`.

These are upper bounds over currently observed row reasons. They deliberately do not claim that real remediation would produce the same row states; resolving one blocker may reveal another hidden blocker.

## Metrics

For each scenario and each of the frozen 600 dates, reproduce the same H5/H10 and consensus population logic as the frozen continuity gate:

- H5 resolved rate;
- H10 resolved rate;
- consensus resolved-ticker intersection rate;
- number of dates meeting >=0.90;
- minimum rate;
- worst date.

A scenario `all_600_pass=true` only means its optimistic row-level ceiling reaches the gate. It is not continuity certification.

## Decision interpretation

- If schedule-only ceiling fails 600/600, coverage remediation is mathematically required under current observed blockers.
- If all-coverage-only ceiling fails 600/600, residual schedule/event remediation is mathematically required.
- If neither alone passes but combined passes, both dimensions are required.
- If combined ceiling fails, current blocker classes cannot clear the frozen gate even under optimistic row-level assumptions; STOP for methodological review.

No acquisition is automatically authorized by any result.

## Hard boundary

No provider/network, target/rank/model/prediction/performance/bootstrap/protected/fresh-forward outcome, threshold change, universe change, or CA semantic change.
