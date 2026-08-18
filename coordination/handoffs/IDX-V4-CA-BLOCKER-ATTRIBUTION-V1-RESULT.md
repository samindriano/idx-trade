# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-V4-CA-BLOCKER-ATTRIBUTION-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `fd5e143669eb875a9887c71c74e13ce5a404b781`
branch: `data/idx-v4-ca-blocker-attribution-v1`
head_commit: result documentation commit follows the frozen attribution anchor
scope: one offline optimistic-ceiling attribution over the immutable Stage-B ledger

## Validation

- focused pytest: `8 passed in 0.84s`
- `py_compile`: PASS
- `git diff --check`: PASS
- input ledger SHA: `585a9c55b200b2fe8e7b8d4a7f0453c3fdc1d659c666b036bbdec797c04ec634`
- provider calls: `0`

## Exact attribution result

Verdict:
`OPTIMISTIC_ATTRIBUTION_COVERAGE_DIMENSION_ALONE_CAN_CLEAR_GATE_SCHEDULE_ALONE_CANNOT`

Scenario summary:

- `BASELINE`: H5/H10/consensus `0/0/0`, minimum rates `0.8237179487 / 0.8216560510 / 0.8216560510`, all-pass `NO`.
- `SCHEDULE_UNKNOWN_RESOLVED_CEILING`: `598/586/586`, minimum rates `0.8975409836 / 0.8949579832 / 0.8949579832`, all-pass `NO`, assumed rows `23,012`.
- `KSEI_COVERAGE_RESOLVED_CEILING`: `600/600/600`, minimum rates `0.9066666667 / 0.9035087719 / 0.9035087719`, all-pass `YES`, assumed rows `27,884`.
- `ALL_COVERAGE_RESOLVED_CEILING`: `600/600/600`, minimum rates `0.9102564103 / 0.9076433121 / 0.9076433121`, all-pass `YES`, assumed rows `29,084`.
- `SCHEDULE_PLUS_KSEI_COVERAGE_CEILING`: `600/600/600`, minimum rates `0.9839743589 / 0.9808917197 / 0.9808917197`, all-pass `YES`, assumed rows `50,896`.
- `SCHEDULE_PLUS_ALL_COVERAGE_CEILING`: `600/600/600`, minimum rates `0.9871794872 / 0.9840764331 / 0.9840764331`, all-pass `YES`, assumed rows `52,096`.

Known mechanical-crossing rows never waived: `227`.

## Artifacts

Promoted under `docs/artifacts/v4_ca_blocker_attribution_20260818_v1/`:

- `summary.json` SHA `63a7574b8556fc3d72822567d493ae4cc96207b2961eabb27a53d4c21a90f31b`
- `MANIFEST.json` SHA `ea1421d080f43739e193d02c85f34ec5eca0f04d04fcb29787746ea101033841`
- `blocker_attribution_per_date.csv` SHA `2aeb6988ed2280302b0f9a4301abe4df9ab18fa518a98a7c813d9632201c0472`

This remains an optimistic diagnostic ceiling only. It does not certify
continuity, alter gates, authorize CA acquisition, or authorize R5/R10,
target/rank/model/performance/outcome work. Update TEAM_STATUS to `REVIEW`,
push, and stop.
