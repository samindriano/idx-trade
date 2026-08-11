# OHLCV O2 Full-Three Final Refit Runtime

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-final-refit-v1`
Starting remote HEAD: `b5c811277f5f30837eb427ec5bc760c2b5c916ed`
Runtime status: `O2_FULL_3_FINAL_REFIT_COMPLETE_PENDING_INDEPENDENT_REVIEW`

## Scope and protected boundary

This runtime fit exactly one final historical model:
`O2-GEOMETRY-FULL3-V1-CANDIDATE-001`.

It did not access post-2026-07-31 outcomes, run forward validation, overwrite
canonical V3-B, call a provider, tune or calibrate, enlarge the population,
or begin execution/model deployment work. The forward-scoring contract was
written but not executed.

## Frozen preflight

- common-support rows: `278,168`;
- common-support tickers: `729`;
- training row identity SHA-256:
  `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- canonical V3-B feature order SHA-256:
  `100ff7a9bacf394b2adc1daa7eb73b0fe7b89613a6918a9e4ded60ca67a55e9e`;
- final 36-feature order SHA-256:
  `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- feature order: canonical V3-B 33 features followed by
  `open_position`, `open_to_high`, `open_to_low`;
- H10 target: `TP_FIRST=1`, `SL_FIRST=0`;
- historical boundary: `2026-07-31`;
- HGB: median imputation with indicators and empty-feature retention, then
  `HistGradientBoostingClassifier(learning_rate=0.05, max_iter=200,
  max_leaf_nodes=31, l2_regularization=1.0, random_state=42)`.

All required input hashes were verified before fitting:

| input | SHA-256 |
|---|---|
| immutable model-safe panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official exchange calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| PIT security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| accepted Open panel | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| accepted Open provenance | `90deaad64ff3330921859eb222df556794c345bb3d440df89edab8ef6d342687` |
| V3-B training table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| V3-B final manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| accepted O1 manifest | `2441f9fcadc9a496ed5d15306bb7bbcb87c9978ecdc26033f5bd7619c2d08714` |
| accepted O2 runtime manifest | `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a` |
| accepted O2 robustness manifest | `ba685239991ad820c45955c2116f56dd00a077b54a8d052c49adb2f97be438bd` |
| accepted O2 minimality manifest | `919e35bb8d2fe68588db331e3de25f6c2a490c2727aea9f68e1179c0bcbe5183` |

Every artifact listed by the three accepted O2 manifests was re-hashed before
the final fit.

## Final model result

- fitted model artifact: `o2_geometry_full3_final_model.joblib`;
- model SHA-256:
  `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
- training rows: `278,168`;
- training tickers: `729`;
- final training-row CSV SHA-256:
  `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f`;
- fit runtime: `15.388028100001975` seconds.

The final manifest explicitly records:

- `fresh_forward_outcomes_accessed=false`;
- `forward_outcome_access_marker_written=false`;
- `canonical_v3b_overwritten=false`;
- `independent_forward_validation_passed=false`;
- `execution_grade_promoted=false`.

## Forward-scoring contract written, not executed

The contract requires scoring after session-t close, with session-t
Open/High/Low available only after the session is complete. It retains the
canonical V3-B eligibility/universe rules plus valid causal Open geometry.
Missing or invalid geometry makes a ticker/session ineligible; no synthetic
fill is allowed. No outcome is required to produce a score. The contract is
in `forward_scoring_contract.json` in the external runtime root.

## Validation

- focused pytest: `2 passed`;
- full pytest: `286 passed, 5 warnings`;
- provider/network calls: none;
- forward validation: not run;
- canonical V3-B overwrite: false.

## External artifacts

Root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\ohlcv_o2_final_refit_v1_20260812`

Artifact manifest SHA-256:
`a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3`

| file | SHA-256 |
|---|---|
| `environment_manifest.json` | `14b6e4d0768c11cd1537fca854ebd81f8e0475cda3494f0de9284526efd541a9` |
| `feature_manifest.json` | `3ba2e2f09f8b3ef89d4c6d966495f40808b72998a352662bf46ac5b9c0190c67` |
| `final_training_rows.csv` | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f` |
| `forward_scoring_contract.json` | `8be6ef3a0e3194bfdc96754833a65d22db4e8507bbc683319a1a6683ebac7979` |
| `model_manifest.json` | `535875e74a1b3a6532e95addf819521758798a767bc49ee9b30d54054a0ae7c2` |
| `o2_geometry_full3_final_model.joblib` | `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb` |
| `runtime_summary.json` | `096a956c49eb671cf975627466a999e60faca9aac0ae26c13a1c1656970d860f` |
| `training_contract.json` | `0f3ee6ef5ff2fac9132d2fe44042573c2348f53d0b155c25b65dcd1034db7698` |

The artifact manifest re-hash verified all `8/8` listed artifact files.

## Stop condition

Stop here for independent ChatGPT review. A separate authorization is required
before any forward scoring or forward outcome evaluation.
