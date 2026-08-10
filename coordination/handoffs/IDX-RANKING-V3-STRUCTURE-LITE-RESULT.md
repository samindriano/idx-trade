# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V3-STRUCTURE-LITE-F1-F4-RUN
model_used: Codex
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b
branch: research/idx-ranking-v2-spec-v1
head_commit: final documentation commit will be reported after push
scope: frozen V3-B Structure-Lite prepare and one F1-F4 discovery run

## Files changed

- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`
- `docs/CURRENT_STATUS.md`
- `docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_F1_F4_RESULT.md`
- `coordination/handoffs/IDX-RANKING-V3-STRUCTURE-LITE-RESULT.md`

Runtime artifacts remain outside Git under:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_prepare_20260810_run1`

and

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_structure_lite_run_20260810_run1`.

## Preflight and artifact verification

- branch synchronized from remote to source HEAD `eee4ed0458fdfdea5fdc0f5335ec211efd3dd80b`;
- working tree was clean before run;
- full pytest: `252 passed, 0 failed, 3 warnings in 32.16 s`;
- wrapper wall duration: `36.29 s`;
- all seven required frozen artifacts hash-matched exactly;
- the source-layout command required `PYTHONPATH=src`; no code/spec change was made.

## Cache result

- status: `RANKING_V3_B_STRUCTURE_LITE_DISCOVERY_CACHE_FROZEN`;
- rows/tickers/sessions: `216,472 / 674 / 20..984`;
- cache SHA-256: `7084759fddaa20e82ec03e50205f2872520e6b3e11ea5f294033589a9c803405`;
- manifest SHA-256: `e428cad0ff24b57977106482cef1478e60c0660adcee6dbf103803516b35aeb2`;
- exact V2 identity/order/prefix: PASS;
- duplicate/orphan and infinity checks: PASS;
- event states: `{-2,-1,0,1,2}`;
- observed volume values: `{0,1}`;
- `v2f5_v2f6_materialized=false`;
- `outcome_metrics_computed=false`.

Feature finite rates were: support distance/touch `91.5546%`, resistance
distance/touch `96.4236%`, nearest age `99.9279%`, role reversal `99.9302%`,
event `99.9302%`, and volume `99.9302%`.

## Run result

- folds: V2F1-V2F4 only;
- control equivalence: **PASS**, `84,732` rows, max score diff `0.0`, max
  required metric diff `0.0` at `1e-12`;
- absolute sanity gate: **PASS**;
- paired promotion gate: **PASS**;
- candidate verdict: `PROMOTE_FOR_NEXT_RESEARCH_STEP`;
- final decision: **`V3_B_STRUCTURE_LITE_PROMOTE_GEOMETRY8`**;
- cumulative evaluated ledger count: `5`.

Aggregate paired deltas:

- median PR-delta improvement `+0.0039258450`;
- q25 PR-delta improvement `+0.0026897894`;
- worst PR-delta improvement `+0.0018412974`;
- PR not below control `4/4`;
- median ROC change `+0.0022459186`;
- median Q5-Q1 change `+0.0113241480`;
- Q5-Q1 not below control `4/4`;
- median top-decile lift change `-0.0036228765` (diagnostic only).

Exact per-fold metrics and all artifact hashes are in:

`docs/checkpoints/2026-08-10_RANKING_V3_STRUCTURE_LITE_F1_F4_RESULT.md`

## Decisions and prohibitions

The fixed eight-feature geometry candidate is promoted for the next separately
authorized research step only. No second variant, ablation, rescue, parameter
change, or definition change was made. This is not independent validation,
probability, execution, or deployment evidence.

V2F5/V2F6 were not accessed. Reserved post-2026-07-31 V2 fresh-forward
outcomes were not accessed. `FORWARD_OUTCOME_ACCESS_STARTED` was not written.
V3-A was not reopened. V3-C/D/E, integration, calibration, Stage 6,
`IDX-VAL-002`, execution-PnL, paper/live, and main merge were not started.

## Recommended next action

Independent ChatGPT review of the complete F1-F4 result. Stop here; do not
automatically start V3-C or F5/F6.
