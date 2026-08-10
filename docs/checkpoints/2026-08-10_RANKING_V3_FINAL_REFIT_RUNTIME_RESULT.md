# Ranking V3-B Final Refit Runtime Result

Date: 2026-08-10 (Asia/Jakarta)  
Status: COMPLETE — FROZEN FINAL TRAINING REFIT; FORWARD VERDICT BLOCKED

## Decision

The authorized final V3-B Structure-Lite refit completed exactly once. The
result is a frozen training model and provenance bundle for the final
historical-development ranker. No historical performance metric was computed
from this refit, and this run does not produce a fresh-forward verdict.

Architecture remains:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

The cumulative historical evaluated-candidate count remains `17`; the final
refit is not a new candidate evaluation.

## Execution identity and pytest

- repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`;
- branch: `research/idx-ranking-v2-spec-v1`;
- implementation/code HEAD: `56e6aa43d318775a5abcf73c87401fafde993b82`;
- full pytest: `364 passed, 0 failed, 3 warnings`;
- pytest shell duration: approximately `18.507s`;
- warnings: three existing pandas `FutureWarning` instances in the curated
  identity and tradability-anchor reconstruction tests.

The branch was clean and synchronized before execution. The final
documentation commit is separate from the implementation HEAD recorded above.

## Frozen input identity verification

| Artifact | Path | SHA-256 / Git blob |
|---|---|---|
| signal panel | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\unknown_state_diagnostic_1260_20260809\model_safe_signal_research_panel_1260.parquet` | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official calendar | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv` | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\security_master_1260.csv` | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| V2 prepared table | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet` | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| V2 prepared manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_cache_manifest.json` | `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143` |
| final-forward spec | `docs/RANKING_V3_FINAL_FORWARD_SPEC_V1.md` | Git blob `024f1919de8d5ea4e2e9933a9e4c1a1ef9bbe4f4` |

The exact final 33-feature-order SHA-256 is
`100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`.

## Final refit

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001`

| Artifact | Path | SHA-256 |
|---|---|---|
| training table | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001\ranking_v3_b_structure_lite_final_training_table.parquet` | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| final model | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001\ranking_v3_b_structure_lite_final.joblib` | `1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6` |
| model manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001\ranking_v3_b_structure_lite_final_manifest.json` | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| final summary | `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_b_final_refit_20260810_001\ranking_v3_b_structure_lite_final_summary.json` | `e8e42dec10c73257fe4776f682f55d146ed8ca49b4aed7ce63ddb7488419e6a0` |

Frozen training facts:

- status: `RANKING_V3_B_FINAL_REFIT_FROZEN`;
- rows: `292,633`;
- tickers: `737`;
- signal-session range: `20..1250`;
- sessions `1225..1250`: training-only;
- duplicate `(ticker, date, signal_session_index)` rows: `0`;
- non-finite values in the 33 feature columns: `0`;
- `historical_performance_metrics_computed`: `false`.

The independent model/manifest verification
`verify_final_v3_refit_artifacts(...)` returned:

```json
{
  "valid": true,
  "model_sha256": "1a702031113ff75f38158aa35d1c2bac477cd424d7f14b83d7a89e6c74fef0f6",
  "manifest_sha256": "4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9",
  "training_table_sha256": "5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe",
  "rows": 292633,
  "tickers": 737
}
```

## Runtime profile

- `build_final_v3_training_table`: `548.094689s`;
- `training_table_serialization`: `0.411702s`;
- `final_model_fit`: `6.023038s`;
- `model_serialization`: `0.022819s`;
- total runtime: `554.696931s`.

The runner used its frozen deterministic single-process implementation. No
uncontrolled worker fan-out or alternate fit was introduced.

## Boundary confirmation

- no post-2026-07-31 labels/outcomes were inspected;
- no historical performance metric was computed from the final refit;
- no fresh-forward verdict was run;
- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`;
- the real global `FORWARD_OUTCOME_ACCESS_STARTED` marker was not written;
- no V4 rescue or new alpha candidate was created;
- no probability calibration, Path-Risk, Stage 6, `IDX-VAL-002`, execution/PnL,
  paper/live, or main merge was started.

Recommended next action: stop for ChatGPT review. Any future fresh-forward
access requires the separately authorized pre-outcome manifest and atomic
marker workflow.
