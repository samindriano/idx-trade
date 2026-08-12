# OHLCV O2 Final Refit — Independent Review

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-final-refit-v1`
Reviewed runtime HEAD: `df13b8f0c1d0bc10380845b1b4ecec64ff22495d`
Decision: `O2_FULL3_FINAL_REFIT_ACCEPTED_FORWARD_CONTRACT_AUTHORIZED`

## Review verdict

The final historical refit for `O2-GEOMETRY-FULL3-V1-CANDIDATE-001` is accepted.

Accepted facts:

- exactly one final fit;
- exact frozen common-support population: 278,168 rows / 729 tickers;
- training row identity SHA-256 `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a`;
- frozen 36-feature order SHA-256 `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f`;
- model SHA-256 `42442e438f04ff40e0637fa3a536bbe9b4ab8f50c8556d350ca0e908d592ccfb`;
- final artifact manifest SHA-256 `a7045257aa85c9d1020d3fe4ceb60a1ee100aadc827305ddf5c608a616adc2d3`;
- all parent O2/robustness/minimality manifests and frozen data/model inputs were hash-verified before fitting;
- no tuning, provider call, population enlargement, canonical V3-B overwrite, forward scoring, or post-2026-07-31 outcome access occurred;
- `fresh_forward_outcomes_accessed=false`, `forward_outcome_access_marker_written=false`, `independent_forward_validation_passed=false`, `execution_grade_promoted=false` remain correct.

The final refit is therefore a valid frozen historical-development challenger artifact. It is not yet an independently forward-validated champion and does not replace canonical V3-B.

## Forward-validation authorization boundary

A separate O2 forward contract may now be frozen and implemented subject to all of the following:

1. Do not retroactively count sessions occurring before this final-refit freeze toward O2's official fresh-forward certification.
2. O2 official fresh-forward certification starts at the first eligible official signal session strictly after the accepted final-refit freeze.
3. Canonical V3-B's already-running protected forward gate remains unchanged and must not be reset, shortened, or opened.
4. O2 scoring is allowed after session-t close only, using the frozen 36-feature contract and valid causal Open geometry; no outcome is required to score.
5. Forward scores/predictions must be persisted before corresponding H10 outcomes are eligible to be revealed/evaluated.
6. Missing/invalid Open geometry makes that ticker/session ineligible; no synthetic Open or geometry fill.
7. No model retraining, calibration, threshold tuning, feature changes, provider repair, or outcome-driven adaptation during the gate.
8. O2 forward evidence must remain sealed until the separately frozen maturity/evaluation rule authorizes aggregate review.

Recommended next action: freeze and implement a separate O2 forward-scoring/validation contract. Do not evaluate any forward outcome in this branch.
