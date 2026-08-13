# Handoff

from: Codex
to: ChatGPT
task_id: IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-ERRATUM-RESULT
model_used: Codex Luna xhigh orchestra profile
reasoning_level: xhigh
source_repository: `C:/Users/Sam/OneDrive/Documents/Project/idx-trade`
source_commit: `adc4dbde92aa42aba31626cc0c8c6f681a735e88`
branch: `research/idx-ranking-v2-spec-v1`
head_commit: pending documentation commit

## Scope

Executed only the corrected V3-E True Ranking F1-F4 local run from
`coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-ERRATUM.md`.
The erratum wrapper was used with XGBoost `3.2.0`, the exact V2 HGB control was
run first, exact equivalence was proved, and only then was the single frozen
LambdaMART candidate run. No research definition was changed.

## Findings

- full pytest: `307 passed, 0 failed, 3 warnings, 14.08s`;
- environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`,
  scikit-learn `1.8.0`, XGBoost `3.2.0`;
- discovery: 169,464 combined rows, 474 tickers, 400 dates, session indices
  `525..984`, dates `2023-06-23..2025-06-05`;
- control equivalence: PASS, 84,732 rows, max score diff `0.0`, max metric diff
  `0.0`;
- LambdaMART absolute sanity: PASS;
- LambdaMART paired promotion: FAIL;
- final verdict: `V3_E_TRUE_RANKING_KILL_KEEP_V2_CONTROL`;
- cumulative viewed candidate count: `9` (ordinals 010 and 011 now viewed);
- V2 HGB_XS_MARKET remains the active ranking control.

Paired summary versus control:

- PR improvement median `+0.0049421451`, q25 `-0.0034997915`, worst
  `-0.0253353754`, non-below folds `3/4`;
- ROC change median `+0.0036990136`;
- Q5-Q1 change median `-0.0072112874`, non-below folds `1/4`;
- top-decile lift change median `-0.0025193041`;
- F4 PR improvement `-0.0253353754`, Q5-Q1 change `-0.0022487774`,
  top-decile lift change `-0.0167865707`.

## Files changed

- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_HYPOTHESIS_LEDGER_V1.md`;
- `docs/checkpoints/2026-08-10_RANKING_V3_TRUE_RANKING_RESULT.md`;
- `coordination/handoffs/IDX-RANKING-V3-TRUE-RANKING-LOCAL-RUN-RESULT.md`.

External runtime evidence (not committed):

`D:/Documents/Project/idx-trade-data-gate-20260808v/ranking_v3_e_true_ranking_erratum_run_20260810_002`

Main hashes:

- summary `ca2e359aaf20089125f2b0606fa152a3042dcaec8249ffa5b5a16e50db28ba72`;
- control equivalence `086f70141dceb4df5ba99e76e8877f59a186efcf44bffc3eabcb7849d1d246c3`;
- metrics `34a9cdc0543ba441762dd3245e21a363086d9ec4de4ec3dbbb1caada0788e933`;
- predictions `2b409764e73624a6897f1c72b2c77d0e6b5a7fe712c1be96fbf50901d1a9dd33`;
- paired `a0aa6c736cebcc1dbc9f83b928f7095103e6670661255656191e483f4dc38daf`;
- query diagnostics `299e5ac46590060bcbac970502b422ff6e61422c16d478886c6e500e7e346c1d`;
- score diversity `0e1e48e84e373f906368534fcb3797ec11d8b37dcba9db2e276302a765ef6cf8`;
- top-decile overlap `cce4a7526c3ca35f15bdfd1bc40a930dc5a4bf5ef69d904625f5fafb8b23a548`;
- runtime `1683b040548f55eb58df84348427d60eebaed5d03a4c157559dea331770c518d`.

## Decisions made

The frozen paired gate was not weakened. LambdaMART is killed for promotion and
retained only as a diagnostic historical result. No integration is authorized
from this handoff.

## Boundary confirmation

- V2F5/V2F6 not materialized, scored, or summarized;
- fresh-forward V2 outcomes not accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` not written;
- V3-D remains blocked/unscored;
- no calibration, Stage 6, IDX-VAL-002, execution-PnL, paper/live, or main merge.

## Recommended next action

ChatGPT should review the pushed checkpoint and result artifacts. Keep V2
HGB_XS_MARKET as control; do not automatically integrate V3-E.
