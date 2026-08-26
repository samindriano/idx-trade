# IDX-Trade Human Notebooks

These notebooks are a human-facing learning layer over the research codebase. They are intentionally exploratory and read-only by default: they do not replace frozen research runners, do not mutate canonical artifacts, and must never open protected/fresh-forward outcomes.

## Suggested order

1. `00_idx_trade_for_humans.ipynb` — repo/model lineage map and basic orientation.
2. `01_market_data_sanity.ipynb` — inspect one market panel with your own eyes.
3. `02_feature_exploration.ipynb` — understand cross-sectional features and distributions.
4. `03_clean_v2_model_walkthrough.ipynb` — manually fit/read one historical Clean-V2-style fold.
5. `04_financial_pit_walkthrough.ipynb` — inspect one ticker/date PIT financial bundle.
6. `05_experiment_review.ipynb` — recompute simple experiment summaries from historical result tables.
7. `06_current_signal_inspection.ipynb` — inspect an outcome-blind score snapshot only.
8. `07_foreign_flow_mechanism_discovery.ipynb` — outcome-blind Foreign Flow mechanism discovery: coverage, distributions, extreme cases, persistence, ticker drill-down, and optional long-memory 5/20/60/120/250-session views.

## Local paths

Large datasets/artifacts remain external to Git. Each notebook has a small `CONFIG` cell where you point to your local parquet/CSV/JSON artifact. Nothing auto-discovers protected outcome paths.

`07_foreign_flow_mechanism_discovery.ipynb` defaults to the previously materialized local Foreign Flow V2 representation path and keeps the raw archive path optional. Phase A intentionally does **not** calculate future returns, IC, Sharpe, TP/SL outcomes, or fit a model. Future-return analysis is reserved for a separately frozen Phase B after mechanism hypotheses are written from the descriptive evidence.

## Historical model source map

The notebooks may refer to research code preserved on historical branches. Historical model code does not need to live in the current working tree.

- Clean Ranking V2 historical implementation: branch `research/idx-ranking-v2-spec-v1`, especially `src/idx_trade/research_v2_features.py`, `src/idx_trade/research_v2_models.py`, `src/idx_trade/ranking_v2_candidate.py`, and `src/idx_trade/ranking_v2_forward_runtime.py`.
- V3-B Structure-Lite historical implementation is preserved in historical ranking lineage, including `src/idx_trade/ranking_v3_structure_lite.py` and `src/idx_trade/research_v3_structure_lite.py` on the older research tree used by the V2/V3 development lineage.
- O2 implementation: branch `research/idx-ranking-ohlcv-o2-final-refit-v1`, especially `src/idx_trade/ohlcv_o2_final_refit.py`.

Useful Git commands:

```bash
git fetch origin --prune
git branch -a | findstr ranking
git show origin/research/idx-ranking-v2-spec-v1:src/idx_trade/research_v2_models.py
```

## Safety rule

Use historical-development outputs for learning. Do **not** point these notebooks at the O2 forward outcome vault or any protected/fresh-forward label artifact before the repository's explicit vault-opening gate.
