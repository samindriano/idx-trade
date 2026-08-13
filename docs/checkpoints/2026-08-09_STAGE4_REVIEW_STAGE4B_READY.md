# Stage 4 Independent Review — Stage 4B Ready

Date: 2026-08-09 (Asia/Jakarta)

Parent Stage-4 branch: `research/idx-stage4-v1`
Parent Stage-4 final documentation commit: `d08247d04c46562c5c8ed4348116fcf0dd9305fd`
Stage-4B branch: `research/idx-stage4b-calibration-v1`

## Review decision

**`STAGE4_REVIEW_PASS_FOR_STAGE4B_CALIBRATION_ONLY`**

The Stage-4 automatic status `STAGE4_RANKING_GO_CALIBRATION_BLOCKED` is accepted.

The project should not stop because the ranking evidence remains positive and internally consistent enough for a bounded continuation, but it should also not open the final holdout because the probability architecture is not yet calibrated.

## Ranking review

Positive evidence:

- HGB beat base-rate and momentum PR-AUC in F1/F2/F3;
- within-date Q5 > Q1 in F1/F2/F3;
- pooled Q5-Q1 TP-rate spread was positive;
- ranking did not collapse in the two worst F3 calibration regimes.

Important qualification:

- ranking strength remains modest;
- quintile ordering is not fully monotonic in every fold (for example F2 Q2 TP rate exceeded Q5 even though Q5 > Q1);
- therefore this is evidence for useful ranking information, not a claim of a strong production ranking engine.

## Feature attribution review

The frozen attribution statuses were mechanically correct, but magnitudes matter:

- STRUCTURE removal mean PR-AUC delta: `-0.013006`;
- MOMENTUM: `-0.007881`;
- HISTORY: `-0.001986`;
- VOLATILITY: `-0.001878`;
- VOLUME_LIQUIDITY: `-0.000896`.

Interpretation:

- STRUCTURE is the clearest contributor;
- MOMENTUM is the second clearest contributor;
- the other three are directionally supportive under the frozen rule but small in magnitude and should not be described as equally important.

No feature subset is changed after observing these results.

## Calibration diagnosis

Stage 4 selected ISOTONIC by lowest pooled Brier among NATIVE / PLATT / ISOTONIC, but readiness failed:

- pooled Brier did not beat base-rate;
- pooled ECE did not beat base-rate;
- prevalence gap improved versus base-rate in only 1/3 folds;
- all metrics remained finite;
- holdout remained untouched.

The most revealing failures were F3 `TREND_MID` and F3 `VOLATILITY_HIGH`, where predicted probabilities materially exceeded the realized TP-vs-SL positive rate while ranking PR-AUC remained above prevalence.

This supports a narrow hypothesis of **probability-level / prior drift** rather than immediate abandonment of the ranking model.

## Why Stage 4B is allowed

Stage 4B is not another general model search. It tests one post-Stage-4 diagnosis explicitly and records it as a new research iteration.

Frozen primary Stage-4B hypothesis:

`STATIC_ISOTONIC -> causal 60-session mature-label prior shift`

The correction is deterministic in odds space and uses only TP-vs-SL labels whose H10 path is fully mature at the after-close prediction timestamp.

A `CAUSAL_PRIOR_ONLY_60` comparator is mandatory. The adjusted model must beat this comparator on pooled Brier; otherwise any apparent gain could be explained by simple market-wide prevalence tracking rather than score-conditioned probability information.

A 126-session prior window is sensitivity-only and cannot rescue the 60-session primary hypothesis.

## Implementation status

Files added:

- `docs/STAGE4B_CALIBRATION_PLAN_V1.md`
- `src/idx_trade/research_stage4b.py`
- `src/idx_trade/stage4b_development.py`
- `tests/test_research_stage4b.py`

CI after implementation:

- **198 passed, 0 failed**;
- existing warning family only.

Core regression guards cover:

- prior-shift odds identity/monotonicity;
- H10 maturity cutoff;
- 60-session prior window boundaries;
- invariance to future-target mutation;
- mandatory dynamic-prior comparator;
- 126-session sensitivity cannot rescue primary failure;
- holdout access blocks readiness.

## Frozen Stage-4B inputs

- Stage-3 primary model table SHA-256:
  `c161911f1330eec12335c6e2711bdca045ad5cfdb1e52f789b1489e987a67189`
- Stage-4 calibration OOF predictions SHA-256:
  `964d3bdbb39b3069deb8328b981150a634d9c2ba780759e9294baccd2e1869b5`
- Stage-4 development summary SHA-256:
  `1d904314e01c1a03b1ffce1cdb6ff5cec4be4caa8723ae0b7413927258be3155`

Stage-4B runtime must preserve Python 3.13.5, NumPy 2.4.2, pandas 2.3.3, pyarrow 23.0.1, scikit-learn 1.8.0.

## Next boundary

Current status after this checkpoint:

**`STAGE4B_IMPLEMENTATION_READY_FOR_RUNTIME`**

The next task is execution-only against the existing local Stage-3/Stage-4 runtime artifacts.

Do not open Stage 5 or the locked holdout even if the automatic Stage-4B status becomes `STAGE4B_CALIBRATION_FREEZE_READY`. Independent review is required first.
