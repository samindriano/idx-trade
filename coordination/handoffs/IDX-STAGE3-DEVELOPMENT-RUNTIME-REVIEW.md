# ChatGPT review handoff

Date: 2026-08-09 (Asia/Jakarta)
Branch: `research/idx-stage3-v1`
Reviewed runtime documentation head: `3651d9ca989ed149988a9140a00cc170a82a57a5`
Correction checkpoint commit: `b81d508b5de86ef157a60b09131c03abe1669c9b`

## Independent review conclusion

Stage 3 produced a real but modest **ranking signal** in development OOF. The frozen advancement rule is satisfied, most convincingly by HistGradientBoosting, which beat both base-rate and momentum PR-AUC in F1/F2/F3.

However, Stage 3 did **not** establish calibrated probability quality. Challenger Brier/ECE are not consistently better than the base-rate model and F3 calibration drift is material. Therefore the project is not ready for a calibrated `P(TP before SL)` production claim, sizing, Kelly, execution-PnL, or locked holdout inspection.

Recommended gate decision: `STAGE3_REVIEW_PASS_FOR_BOUNDED_STAGE4_RESEARCH`, subject to a separately frozen Stage-4 plan before any new development outcomes are generated. Stage 4 should remain development-only and focus on robustness/ablation/calibration hypotheses rather than broad model search.

Do not inspect the locked holdout until Stage-4 choices are frozen and an explicit holdout authorization is given.

## Correct population interpretation

Full-valid H10 resolved binary rows: 512,959 = 197,910 TP + 315,049 SL.

Primary broad-liquid H10 model rows: 208,375 = 80,038 TP + 128,337 SL.

The original runtime checkpoint sentence equating 197,910 + 315,049 with 208,375 was a documentation error only; model metrics already used the intended 208,375 primary-liquid model table.
