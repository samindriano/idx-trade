# Handoff

from: Codex  
to: MAIN / independent ChatGPT review  
task_id: IDX-RANKING-OHLCV-O2-GEOMETRY  
model_used: Luna xhigh orchestra DIRECT/one-writer  
reasoning_level: xhigh  
source_repository: `samindriano/idx-trade`  
source_commit: `2d33bcbb4820761a561df57f23ae9f18a348b4ba`  
branch: `research/idx-ranking-ohlcv-o2-geometry-v1`  
head_commit: pending push  

scope: Execute only the frozen O2_OPEN_GEOMETRY historical-development experiment.

files_changed:
- `src/idx_trade/ohlcv_o2_geometry_research.py`
- `tests/test_ohlcv_o2_geometry_research.py`
- `docs/checkpoints/2026-08-12_OHLCV_O2_GEOMETRY_RUNTIME.md`
- `coordination/handoffs/IDX-RANKING-OHLCV-O2-GEOMETRY.md`

findings:
- Exact O1 common-support population reproduced: 278,168 rows, 729 tickers.
- Baseline was refit in this run with the exact canonical V3-B 33-feature
  order/hash, H10 labels, six folds, evaluator and HGB contract.
- O2 appended only `open_position`, `open_to_high`, `open_to_low` in the frozen
  order; certified geometry formulas matched to floating-point tolerance.
- O2 paired PR-AUC improved in all six folds: median `+0.0072762209098306`,
  lower quartile `+0.0047096450033947`, positive folds `6/6`.
- Aggregate ranking guardrail reversal: `false`.
- Final decision: `O2_SURVIVOR`.
- No fresh-forward outcome or network access occurred.

decisions_made:
- O2 meets the frozen survivor rule and is sent for independent review.
- No O3, interaction, regime, feature-mining, combination, or final-refit work
  was started.

decisions_needed:
- Independent ChatGPT review before any combination/final-refit decision.

blocking_risks:
- The result is historical-development evidence only; it is not independent
  forward validation and must not be treated as execution/PnL evidence.

validation_run:
- focused pytest: `3 passed`;
- full pytest: `282 passed, 5 warnings`;
- external runtime: two models / six folds / approximately 44.6 seconds;
- external artifact manifest SHA-256:
  `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a`.

recommended_next_action:
Stop for independent ChatGPT review. Do not start another experiment from this
branch until the survivor is reviewed and a new scope is explicitly authorized.
