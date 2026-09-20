# Eligibility Policy Delta by Era V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_POLICY_DELTA_BY_ERA_NO_SELECTION`

## Question

Is the unresolved minimum-20 versus minimum-60 eligibility fork confined to an
early warm-up era, or does it change the structural population throughout the
available panel?

## Scope and boundary

This is an outcome-blind decomposition of the two already-defined eligibility
scenarios. It reads the frozen structural panel, official sessions, and
tradability anchors only. It does not select a policy, regenerate candidates,
read targets/outcomes, or modify canonical, production, cloud, capture,
telemetry, or incumbent state.

## Result

The minimum-20 minus minimum-60 delta is present in every calendar year:

| Year | Minimum-20 rows | Minimum-60 rows | Newly admitted rows | New tickers | New dates |
|---|---:|---:|---:|---:|---:|
| 2021 | 39,150 | 27,527 | 11,623 | 297 | 148 |
| 2022 | 71,188 | 66,931 | 4,257 | 110 | 246 |
| 2023 | 63,265 | 58,688 | 4,577 | 122 | 239 |
| 2024 | 58,545 | 53,876 | 4,669 | 101 | 237 |
| 2025 | 66,690 | 58,949 | 7,741 | 180 | 236 |
| 2026 partial | 49,927 | 44,790 | 5,137 | 123 | 135 |
| **Total** | — | — | **38,004** | **619** | **1,241** |

The ambiguity is therefore not only an early warm-up artifact. It remains a
population-defining fork in 2025 and 2026 as well. The additional rows are
called “newly admitted” only as a mask difference; they are not inferred to be
listings, delistings, ticker reuse, or superior policy choices.

## Adjudication

| Gate | Result |
|---|---|
| Delta by calendar year | `PASS_STRUCTURAL_ONLY` |
| Policy selected | `NO` |
| Era selected | `NO` |
| Population completeness | `UNKNOWN / BLOCKED` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |

This strengthens the existing `POLICY_AUTHORITY_MISSING` blocker: it cannot be
quarantined to the earliest era. No candidate ranking or outcome comparison was
used to choose between the masks.

## Reproducibility

- Code: `research/alpha_eligibility_era_delta_v1.py`
- Code SHA-256:
  `dd20ca55a6ac8d967e3e76853724d2e81f49d074a40a9e78aed6f2d70f198f7c`
- Scenario helper SHA-256:
  `58d3280c9e191903bd195bfa11a92201ee693ead1b752f1010f5b93b15cd0e11`
- Durable result: `research_knowledge/eligibility_era_delta_v1.json`
- Durable result SHA-256:
  `2a5764e2bccb5b50f8834eac89b1f389ce41880cffb86b2fe357e433970416cb`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260920T-candidate-era\alpha_eligibility_era_delta_v1.json`
- External result SHA-256:
  `b35eb7c5c8ba27a501d22032f074cb5a528bf5fa782417f5a01912ee43570513`
- Focused tests: `2/2` passing.
