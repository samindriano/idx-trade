# V4-3R CA80 prefit PASS and execution-freeze handoff — 2026-08-19

Status: `V4_3R_CA80_PREFIT_SUPPORT_PASS_READY_TO_FREEZE_EXECUTION`

## Outcome-blind prefit result

The separately preregistered V4-3R CA80 support replay completed successfully before any historical target/model/performance access.

Pinned external prefit manifest:

`0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`

Observed result:

- support gate: `0.80`;
- historical execution authorized by support gate: `true`;
- H5 eligible sessions: `986`;
- H10 eligible sessions: `982`;
- consensus eligible sessions: `982`;
- frozen 600 full-target eligible: `true`;
- tail-600 identity unchanged: `true`;
- eligible sessions after frozen end: `0`;
- frozen H5 minimum support: `0.8432203389830508`;
- frozen H10 minimum support: `0.8395061728395061`;
- frozen consensus minimum support: `0.8395061728395061`;
- all 12 fold/head training sets non-empty: `true`;
- historical target loaded: `false`;
- model fit: `false`;
- performance computed: `false`.

Training-date counts:

| Fold | H5 | H10 |
|---:|---:|---:|
| 1 | 376 | 372 |
| 2 | 476 | 472 |
| 3 | 576 | 572 |
| 4 | 676 | 672 |
| 5 | 776 | 772 |
| 6 | 876 | 872 |

## Important support-distribution disclosure

The frozen consensus support buckets are:

- `<0.80`: `0 / 600`;
- `[0.80, 0.90)`: `541 / 600`;
- `>=0.90`: `59 / 600`.

Therefore V4-3R is materially dependent on the separately preregistered CA80 policy. It must never be described as the original V4-3 90% gate passing. The V4-3 90% generation remains failed and closed.

This does not invalidate V4-3R because the 80% threshold was frozen using only outcome-blind support/provenance information before historical target returns, predictions, model performance, or protected-forward access.

## Execution freeze added after PASS

The branch now contains:

- `config/ranking_v4_3r_execution_freeze_v1.json`;
- `scripts/capture_v4_3r_execution_freeze.py`;
- `tests/test_v4_3r_execution_freeze_contract.py`.

The execution-freeze layer does not change the V4-3 scientific core. It verifies and pins:

1. the exact passed prefit manifest SHA;
2. the prefit summary child hash and expected PASS diagnostics;
3. V4-3R prereg/support code Git blob identities;
4. inherited V4-3 target/features/model-evaluation Git blob identities;
5. exact accepted Python and package versions from the frozen V4-3 prefit runtime manifest;
6. a clean Git worktree;
7. zero historical target/model/performance/protected-forward access during capture.

## Scientific contract remains unchanged except CA80 date-level threshold

Still frozen:

- H5 target = `Close_(t+5) / Open_(t+1) - 1`;
- H10 target = `Close_(t+10) / Open_(t+1) - 1`;
- unsupported rows never receive targets;
- known/unresolved mechanical CA crossings remain fail-closed at row level;
- primary-liquid decision universe unchanged;
- Control = Context25 HGBR;
- Challenger = Context25 + Geometry3;
- 6 x 100 validation folds unchanged;
- 10-session purge unchanged;
- learner/hyperparameters unchanged;
- Top30 and `top30_min_observable=27` unchanged;
- bootstrap and promotion gates unchanged.

The only generation delta remains the preregistered date-level target-support/evaluation coverage threshold `0.90 -> 0.80`.

## Next hard gate

Run the local execution-freeze capture against the exact external prefit artifact root. Historical target/model/performance access remains prohibited until that capture completes successfully and its resulting manifest SHA is recorded.

Protected-forward access remains prohibited even after the execution-freeze capture.
