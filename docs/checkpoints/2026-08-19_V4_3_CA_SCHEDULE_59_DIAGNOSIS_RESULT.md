# V4-3 CA Schedule-59 Failure-Mode Diagnosis Result

Date: 2026-08-19
Branch: `research/idx-ranking-v4-3-ca-schedule59-diagnosis-v1`
Status: `V4_3_CA_SCHEDULE_59_FAILURE_MODE_CENSUS_COMPLETE`

Accepted local diagnosis root:

`D:\Documents\Project\idx-v4-3-ca-training-domain-schedule59-diagnosis-20260819-v1`

Manifest SHA-256:

`8c717e8f4bf7fb69edfe366cd0f219ef0c7d9f812006c409ed682eb6e9c9fb12`

Residual event identity SHA-256:

`f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`

## Complete 59-event diagnosis

Failure modes:

- `MECHANICAL_NO_EXPLICIT_REGULAR_MARKET_TRANSITION`: 47
- `MECHANICAL_SOURCE_DATE_NOT_LINKED_TO_LAYOUT_BOUND_RECORD_DISTRIBUTION`: 2
- `NO_FROZEN_CANDIDATE_DOCUMENT`: 6
- `VOLUNTARY_CASH_DATE_NOT_LINKED_TO_SOURCE_DATE`: 1
- `VOLUNTARY_NO_LAYOUT_BOUND_CASH_DATE`: 2
- `VOLUNTARY_NO_RECOGNIZED_CASH_DOCUMENT`: 1

Remediation classes:

- `SECONDARY_OFFICIAL_EX_OR_NEW_BASIS_SCHEDULE_DISCOVERY`: 47
- `SECONDARY_OFFICIAL_DOCUMENT_DISCOVERY`: 6
- `SECONDARY_OFFICIAL_EVENT_LINKAGE_DISCOVERY`: 3
- `SECONDARY_OFFICIAL_CASH_SCHEDULE_DISCOVERY`: 2
- `SECONDARY_OFFICIAL_CASH_DOCUMENT_DISCOVERY`: 1

53/59 already had at least one frozen V1 candidate document but remained unresolved; six had no frozen V1 candidate document.

## Scientific interpretation

The dominant residual is not a provider-transport failure and not a lack of any document. Forty-seven events have candidate official documents but still lack an admissible explicit Regular-Market Ex / first-new-basis transition. Therefore repeating the same `corporate-action-schedules` category/month crawl is not the next justified action.

The next acquisition must use a secondary official KSEI discovery surface and preserve all 59 events. No pass-contribution ranking or minimum-to-pass subset is allowed.

## Firewall

This diagnosis performed no network/provider call, target/rank materialization, model fit, prediction, performance computation, bootstrap, price inference, threshold change, or protected-forward access.
