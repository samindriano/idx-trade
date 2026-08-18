# V4 CA Blocker Attribution V1 — Result

Status: `REVIEW`

## Validation and input

- branch: `data/idx-v4-ca-blocker-attribution-v1`
- execution HEAD: `fd5e143669eb875a9887c71c74e13ce5a404b781`
- focused pytest: `8 passed in 0.84s`
- `py_compile`: PASS
- `git diff --check`: PASS
- Stage-B ledger SHA: `585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`
- output root was fresh before the run
- provider calls: `0`

## Attribution result

Exactly one offline attribution run completed with:

`OPTIMISTIC_ATTRIBUTION_COVERAGE_DIMENSION_ALONE_CAN_CLEAR_GATE_SCHEDULE_ALONE_CANNOT`

All non-baseline scenarios are optimistic row-level upper bounds. They do not
certify corporate-action continuity and do not waive hidden downstream blockers.

| Scenario | H5 pass dates | H5 min | H5 worst | H10 pass dates | H10 min | H10 worst | Consensus pass dates | Consensus min | Consensus worst | New rows assumed | All 600 pass |
|---|---:|---:|---|---:|---:|---|---:|---:|---|---:|---|
| `BASELINE` | 0 | 0.8237179487 | 2026-07-02 | 0 | 0.8216560510 | 2026-06-30 | 0 | 0.8216560510 | 2026-06-30 | 0 | NO |
| `SCHEDULE_UNKNOWN_RESOLVED_CEILING` | 598 | 0.8975409836 | 2024-03-28 | 586 | 0.8949579832 | 2024-06-11 | 586 | 0.8949579832 | 2024-06-11 | 23,012 | NO |
| `KSEI_COVERAGE_RESOLVED_CEILING` | 600 | 0.9066666667 | 2025-04-28 | 600 | 0.9035087719 | 2025-05-21 | 600 | 0.9035087719 | 2025-05-21 | 27,884 | YES |
| `ALL_COVERAGE_RESOLVED_CEILING` | 600 | 0.9102564103 | 2026-07-02 | 600 | 0.9076433121 | 2026-06-30 | 600 | 0.9076433121 | 2026-06-30 | 29,084 | YES |
| `SCHEDULE_PLUS_KSEI_COVERAGE_CEILING` | 600 | 0.9839743589 | 2026-07-02 | 600 | 0.9808917197 | 2026-06-30 | 600 | 0.9808917197 | 2026-06-30 | 50,896 | YES |
| `SCHEDULE_PLUS_ALL_COVERAGE_CEILING` | 600 | 0.9871794872 | 2026-07-02 | 600 | 0.9840764331 | 2026-06-30 | 600 | 0.9840764331 | 2026-06-30 | 52,096 | YES |

Interpretation: resolving the coverage dimension alone has an optimistic
ceiling above the 90% gate, but resolving schedule-required rows alone does
not. This does not prove either remediation is available or sufficient in
actual evidence.

## Baseline blocker accounting

| Reason | Rows |
|---|---:|
| `NO_MECHANICAL_CA_TRANSITION_CROSSES_TARGET_INTERVAL` | 292,467 |
| `EXACT_OFFICIAL_EVENT_TRANSITION_REQUIRED` | 23,012 |
| `KSEI_REGISTERED_SECURITY_HISTORY_NOT_CERTIFIED` | 27,884 |
| `CROSS_SOURCE_CANDIDATE_NOT_REPRESENTED_IN_KSEI_HISTORY` | 1,200 |
| `TARGET_INTERVAL_CROSSES_MECHANICAL_CA_TRANSITION` | 227 |

Known mechanical-crossing rows preserved and never waived: `227`.

## Provenance and artifacts

External output root:
`D:\Documents\Project\idx-v4-ca-blocker-attribution-20260818-v1`

Promoted artifacts:

- `summary.json`: `63a7574b8556fc3d72822567d493ae4cc96207b2961eabb27a53d4c21a90f31b`
- `MANIFEST.json`: `ea1421d080f43739e193d02c85f34ec5eca0f04d04fcb29787746ea101033841`
- `blocker_attribution_per_date.csv`: `2aeb6988ed2280302b0f9a4301abe4df9ab18fa518a98a7c813d9632201c0472`

The run remained diagnostic-only:

- optimistic upper bounds: `true`
- hidden downstream blockers reconstructed: `false`
- model fit/predictions/performance: `false`
- target/rank materialized: `false`
- protected/fresh-forward outcomes: untouched

No new provider or CA acquisition occurred. Stop for ChatGPT review.
