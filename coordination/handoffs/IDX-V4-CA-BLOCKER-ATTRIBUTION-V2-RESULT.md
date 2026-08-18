# Handoff — IDX-V4-CA-BLOCKER-ATTRIBUTION-V2 Result

from: Codex
to: ChatGPT
task_id: `IDX-V4-CA-BLOCKER-ATTRIBUTION-V2`
branch: `data/idx-v4-ca-blocker-attribution-v2`
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `620d4efe1165a1e40e4302b5719684664a8cf415`
scope: one offline post-KSEI blocker-attribution calculation

## Result

Validation passed and exactly one offline attribution run completed. The
runner returned:

`OPTIMISTIC_ATTRIBUTION_V2_MULTIPLE_MINIMAL_CLEARING_SCENARIOS`

This is diagnostic-only. Baseline continuity remains blocked; optimistic
ceilings are not certifications.

## Validation and input

- Focused pytest: `13 passed`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Input ledger SHA-256:
  `9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`.
- Provider calls: `0`.
- Known mechanical rows never waived: `240`.

## Scenario result

| Scenario | H5 pass/min | H10 pass/min | Consensus pass/min | Assumed rows | All pass |
|---|---:|---:|---:|---:|---|
| BASELINE | 462 / 0.8814102564 | 461 / 0.8789808917 | 461 / 0.8789808917 | 0 | NO |
| SCHEDULE_ONLY_CEILING | 600 / 0.9615384615 | 600 / 0.9585987261 | 600 / 0.9585987261 | 24,212 | YES |
| KSEI_COVERAGE_ONLY_CEILING | 600 / 0.9022222222 | 597 / 0.8991228070 | 597 / 0.8991228070 | 6,844 | NO |
| CROSS_SOURCE_ONLY_CEILING | 515 / 0.8846153846 | 504 / 0.8821656051 | 504 / 0.8821656051 | 1,200 | NO |
| ALL_COVERAGE_CEILING | 600 / 0.9066666667 | 600 / 0.9035087719 | 600 / 0.9035087719 | 8,044 | YES |
| SCHEDULE_PLUS_KSEI_COVERAGE_CEILING | 600 / 0.9834024896 | 600 / 0.9792531120 | 600 / 0.9792531120 | 31,056 | YES |
| SCHEDULE_PLUS_CROSS_SOURCE_CEILING | 600 / 0.9647435897 | 600 / 0.9617834395 | 600 / 0.9617834395 | 25,412 | YES |
| SCHEDULE_PLUS_ALL_COVERAGE_CEILING | 600 / 0.9871794872 | 600 / 0.9834024896 | 600 / 0.9834024896 | 32,256 | YES |

Minimal clearing scenarios: `ALL_COVERAGE_CEILING`,
`SCHEDULE_ONLY_CEILING`.

Reason counts: no-crossing `312,294`; exact official transition required
`24,212`; KSEI history not certified `6,844`; target interval crosses
mechanical transition `240`; cross-source candidate absent from KSEI history
`1,200`.

## Promoted files

- `docs/artifacts/v4_ca_blocker_attribution_20260818_v2/summary.json`
- `docs/artifacts/v4_ca_blocker_attribution_20260818_v2/MANIFEST.json`
- `docs/artifacts/v4_ca_blocker_attribution_20260818_v2/blocker_attribution_v2_per_date.csv`
- `docs/checkpoints/2026-08-18_V4_CA_BLOCKER_ATTRIBUTION_V2_RESULT.md`

Hashes are recorded in the checkpoint. No input ledger copy was committed.

recommended_next_action: ChatGPT review of attribution only; do not treat
optimistic scenario clearance as actual continuity certification.
