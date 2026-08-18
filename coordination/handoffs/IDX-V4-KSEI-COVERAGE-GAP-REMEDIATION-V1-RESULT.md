# Handoff — IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1 Result

from: Codex
to: ChatGPT
task_id: `IDX-V4-KSEI-COVERAGE-GAP-REMEDIATION-V1`
branch: `data/idx-v4-ksei-coverage-gap-remediation-v1`
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `15dfe535f091b23ad510100a7002830e982415e2`
scope: import-path retry, one targeted 43-ticker official KSEI run, one
outcome-blind continuity replay

## Result

The retry completed without source/config patching. Import-path validation
passed after setting `PYTHONPATH` to the worktree `src` directory. The exact
targeted runner completed once, recovering 31 of 43 gap tickers. The exact
continuity replay then completed once and remained blocked:

`V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`

`corporate_action_continuity_certified=false`.

## Validation

- Focused pytest: `7 passed`.
- `py_compile`: PASS.
- `git diff --check`: PASS.
- Zero-network preflight: PASS;
  `V4_KSEI_COVERAGE_GAP_RUNTIME_PREFLIGHT_PASS`;
  `network_calls=0`.
- Gap count: `43`.
- Gap identity SHA-256:
  `1cd050985841519d24f58a38d10014693ff4a843cbd438586237ad4419ffe812`.

## Acquisition evidence

- KSEI provider requests/raw captures: `76 / 76`.
- Recovered: `31` tickers, `636` history rows.
- Remaining unresolved: `12` tickers — AMAN, AVIA, AYAM, BCIP, ICBP, PRIM,
  SKRN, SLIS, SMAR, SNLK, SOCI, SOFA.
- Recovered active mechanical/unknown rows: `24 / 0`.
- Merged coverage: `598 certified / 12 unresolved`.
- Recovery failures: `HTTP_NON_200_OR_EMPTY=11`,
  `PARSE_IDENTITY_MISMATCH=1`.
- Acquisition manifest SHA:
  `7e86f5e52d7c2ff609ee9dd4be28ff1aefea1e4d5c7d7d9dbffb6abd07185f50`.

## Continuity evidence

- Relevant event rows: `83`.
- Exact transitions: `44`.
- Schedule-required transitions: `39` across `35` tickers.
- Cross-source conflict tickers: MEGA, SCMA.
- H5/H10/consensus gate dates: `462 / 461 / 461`.
- Minimum H5/H10/consensus rates:
  `0.8814102564 / 0.8789808917 / 0.8789808917`.
- Frozen gate: `0.90`; therefore blocked.
- Continuity summary SHA:
  `3939fbd7e5d63d702782ca7851c8249802a0341a8ac97d5ee15133f265a155ec`.
- Continuity overlay SHA:
  `bda80ad53a6e1426f147177c50896e6776ec78196602e45fb9b5489282e7c026`.

Full promoted artifact hashes and external-root paths are recorded in the
dated checkpoint:
`docs/checkpoints/2026-08-18_V4_KSEI_COVERAGE_GAP_REMEDIATION_RESULT.md`.

## Files changed

- `docs/artifacts/ranking_v4_ksei_coverage_gap_remediation_v1/summary.json`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_remediation_v1/MANIFEST.json`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_remediation_v1/coverage_gap_results.csv`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_remediation_v1/parent_failure_diagnostic.csv`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/summary.json`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/MANIFEST.json`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/event_semantics_audit.csv`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/schedule_evidence_needs.csv`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/v4_frozen_continuity_per_date_event_window.csv`
- `docs/artifacts/ranking_v4_ksei_coverage_gap_continuity_v1/ksei_coverage_gap_continuity_overlay.json`
- dated checkpoint above

Raw captures, request deltas, full merged history, and the full continuity
ledger remain external.

## Constraints honored

No source/config patch, alternate provider, alias remap, parser relaxation,
567-ticker recrawl, schedule acquisition, R5/R10, target/rank, model,
prediction, performance, or protected/fresh-forward outcome access.

recommended_next_action: ChatGPT review of the blocked continuity result; do
not start a rescue or schedule acquisition automatically.
