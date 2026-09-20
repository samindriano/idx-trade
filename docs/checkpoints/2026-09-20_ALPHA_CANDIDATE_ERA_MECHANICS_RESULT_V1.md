# Candidate Calendar-Year Mechanics V1

Date: 2026-09-20 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `PASS_STRUCTURAL_ERA_MECHANICS / NO ERA OR POLICY ADMITTED`

## Question

After the existing six-block structural lab and calendar-year support map, do
fixed Top-30 turnover, selection persistence, slot concentration, rank
displacement, and between-year selection overlap vary materially by natural
calendar year?

## Scope and boundary

This is a target-free mechanics audit over the guarded C1-C4 rank artifact and
official session calendar. It uses fixed Top-30 selection, descending rank
with ticker tie-break, and only consecutive official sessions within the same
calendar year for turnover. It does not sweep horizons, select an era, change
eligibility, create C5, or access protected outcomes.

## Main findings

### Broad candidates

| Candidate | 2022 turnover | 2025 turnover | 2026 partial turnover | 2022 effective names | 2026 effective names |
|---|---:|---:|---:|---:|---:|
| C1 | 41.21% | 42.31% | 43.78% | 287.7 | 279.6 |
| C2 | 33.39% | 32.33% | 35.55% | 231.0 | 219.6 |
| C4 | 23.32% | 24.23% | 25.47% | 238.5 | 210.3 |

C1 and C4 show a mild increase in turnover into 2026, while C2 also rises in
2026. These are structural mechanics, not execution or return evidence.

Adjacent-year selected-ticker Jaccard values for 2025→2026 are C1 `0.6438`,
C2 `0.5748`, and C4 `0.5511`. Earlier adjacent-year values are lower or
similar; this is overlap of names selected at any point in each year, not
same-day predictive orthogonality.

### C3

C3 has no usable Top-30 date before 2025. In 2025 it has 153 usable dates,
10.76% mean turnover, effective selected names `61.7`, and mean persistence
`8.00` sessions. In 2026 it has 125 usable dates, 11.24% mean turnover,
effective selected names `51.0`, and mean persistence `8.37` sessions.

The apparently longer persistence and higher concentration are consequences of
sparse/late support and must not be interpreted as quality or predictive
stability.

### Rank displacement

Mean absolute one-session rank displacement remains broadly stable for the
wide-support candidates but is much smaller for sparse C3:

| Candidate | 2022 | 2025 | 2026 partial |
|---|---:|---:|---:|
| C1 | 0.1485 | 0.1527 | 0.1546 |
| C2 | 0.1513 | 0.1585 | 0.1491 |
| C3 | — | 0.0164 | 0.0130 |
| C4 | 0.0741 | 0.0789 | 0.0823 |

C3's low displacement is support-driven and not evidence of a superior signal.

## Adjudication

| Gate | Result |
|---|---|
| Fixed Top-30 mechanics | `PASS_STRUCTURAL_ONLY` |
| Calendar-year comparison | `SUPPORTED_SCOPED` |
| Era admission | `NO` |
| Policy selection | `NO` |
| Predictive interpretation | `FORBIDDEN / NOT TESTED` |

The new result adds a calendar-year mechanics view that was absent from the
prior six-block lab. It does not overturn the existing candidate statuses:
C1/C2/C4 remain `FUTURE_RESEARCH`, C3 remains `BLOCKED`.

## Reproducibility

- Code: `research/alpha_candidate_era_mechanics_v1.py`
- Code SHA-256:
  `b58269a65eaafa627bf912cce7e860196d151939703baec3335e50297fd94039`
- External result:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\alpha_candidate_era_mechanics_v1.json`
- External result SHA-256:
  `797c41486fd08ee86c04988331dc6179994570fe7c2374cc72b14657d04ec34e`
- Focused tests: `2/2` passing.
- Feature input SHA-256:
  `aaff882f0ab2e8542203e117de39ac5a9caf5a8d73a44a110b4a5679311c03b4`
- Official-session input SHA-256:
  `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`

All output remained in the isolated staging root. No canonical, incumbent,
cloud, capture, telemetry, scheduler, or production artifact was modified.
