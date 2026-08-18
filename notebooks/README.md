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

## Local paths

Large datasets/artifacts remain external to Git. Each notebook has a small `CONFIG` cell where you point to your local parquet/CSV/JSON artifact. Nothing auto-discovers protected outcome paths.

## Historical model source map

The current V4-3 branch is intentionally narrow, so older model modules are not expected to appear in the current `src/idx_trade` tree.

- Clean Ranking V2 historical implementation: branch `research/idx-ranking-v2-spec-v1`, especially `src/idx_trade/research_v2_features.py`, `src/idx_trade/research_v2_models.py`, `src/idx_trade/ranking_v2_candidate.py`, and `src/idx_trade/ranking_v2_forward_runtime.py`.
- V3-B Structure-Lite historical implementation is preserved in historical ranking lineage, including `src/idx_trade/ranking_v3_structure_lite.py` and `src/idx_trade/research_v3_structure_lite.py` on the older research tree used by the V2/V3 development lineage.
- O2 implementation: branch `research/idx-ranking-ohlcv-o2-final-refit-v1`, especially `src/idx_trade/ohlcv_o2_final_refit.py`; related research lives in `ohlcv_o2_geometry_research.py`, `ohlcv_o2_minimality.py`, and `ohlcv_o2_robustness_audit.py`.
- Current V4-3 implementation: `src/idx_trade/ranking_v4_3_features.py`, `ranking_v4_3_model_eval.py`, `ranking_v4_3_preregistration.py`, and `ranking_v4_3_target_execution.py`.

Useful Git commands:

```bash
git branch -a | findstr ranking
git show origin/research/idx-ranking-v2-spec-v1:src/idx_trade/research_v2_models.py
git show origin/research/idx-ranking-ohlcv-o2-final-refit-v1:src/idx_trade/ohlcv_o2_final_refit.py
```

If a historical branch is not present locally, run `git fetch origin --prune` first.

## Safety rule

Use historical-development outputs for learning. Do **not** point these notebooks at the O2 forward outcome vault or any protected/fresh-forward label artifact before the repository's explicit vault-opening gate.