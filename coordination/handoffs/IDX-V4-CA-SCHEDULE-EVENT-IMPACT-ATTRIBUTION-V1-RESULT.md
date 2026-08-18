# Handoff — IDX-V4-CA-SCHEDULE-EVENT-IMPACT-ATTRIBUTION-V1 Result

from: Codex
to: ChatGPT
task_id: `IDX-V4-CA-SCHEDULE-EVENT-IMPACT-ATTRIBUTION-V1`
branch: `data/idx-v4-ca-schedule-event-impact-attribution-v1`
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `a38791863cee7e17365942e6dc202e26692a593f`
scope: one offline event-level attribution over the exact post-KSEI ledger

## Result

Validation passed and exactly one offline attribution run completed. The
selected subset is deterministic inclusion-minimal, not a proven global
minimum. The selected 7-event counterfactual passes the frozen 90% gate, but
the result is only an optimistic acquisition-priority diagnostic:

`V4_CA_SCHEDULE_EVENT_IMPACT_ATTRIBUTION_COMPLETE`

## Validation and inputs

- Focused pytest: `13 passed`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Ledger SHA:
  `9dce85c55a9e8a9e1effba5c7e0d24faa150bfb0d70c0162cfb85955d8a435ec`.
- Schedule-needs SHA:
  `1988f2bb679b09835e045235fa7aa46f4d8c62cf9531e76a5b5b889d848a127a`.
- Provider calls: `0`.
- Events: `39` total, `34` critical; known mechanical rows preserved: `240`.

## Exact attribution

- Baseline: H5/H10/consensus `462/461/461`; minimum rates
  `0.8814102564/0.8789808917/0.8789808917`; fails.
- Schedule-only ceiling: `600/600/600`; minimum rates
  `0.9615384615/0.9585987261/0.9585987261`; optimistic pass.
- Selected 7-event subset: `600/600/600`; minimum rates
  `0.9038461538/0.9012738854/0.9012738854`; optimistic pass.
- Selected subset basis:
  `DETERMINISTIC_INCLUSION_MINIMAL_NOT_GLOBAL_CARDINALITY_PROVEN`.
- Exact search: `NOT_RUN_CRITICAL_UNIVERSE_ABOVE_EXACT_BOUND`, evaluations `0`.
- Reverse-pruned events: none.
- Zero-blocking-row event IDs: none.

Selected ordered tickers: NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN.

Top emitted impact order: NISP, ISAT, ADRO, PANI, RAJA, PTRO, CUAN, CYBR,
MSIN, PACK. Full event IDs, families, source dates, and impact fields are in
the promoted `schedule_event_impact.csv` and dated checkpoint.

## Promoted files

- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/summary.json`
- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/MANIFEST.json`
- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/schedule_event_impact.csv`
- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/selected_schedule_event_subset.csv`
- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/selected_subset_per_date.csv`
- `docs/artifacts/v4_ca_schedule_event_impact_attribution_20260818_v1/greedy_selection_trace.csv`
- `docs/checkpoints/2026-08-18_V4_CA_SCHEDULE_EVENT_IMPACT_ATTRIBUTION_V1_RESULT.md`

Hashes are recorded in the checkpoint. No source/config or large external
ledger was committed.

recommended_next_action: ChatGPT review; do not acquire schedule evidence or
call the selected subset certified automatically.
