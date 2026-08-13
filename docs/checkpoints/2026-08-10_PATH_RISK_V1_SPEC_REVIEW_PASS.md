# Path Risk V1 Specification Review — PASS

Date: 2026-08-10 (Asia/Jakarta)
Status: **PATH_RISK_V1_SPEC_REVIEW_PASS — IMPLEMENT/PREP ONLY, REAL OUTCOMES BLOCKED**

## Decision

The first Path Risk lane is accepted as a separate, falsifiable risk-estimation experiment:

`PATH-RISK-A-ADVERSE-EXCURSION-Q75-V1`

Controlling specification:

`docs/PATH_RISK_V1_SPEC.md`

The next phase is authorized only for implementation, tests, and real **outcome-blind** feature-cache preparation through discovery session `984`.

Real historical Path Risk target construction/scoring remains blocked until a second review after the feature cache is frozen.

## Why this is methodologically separate from ranking

The frozen final opportunity ranker remains exact:

`V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`

Path Risk does not ask whether a name should rank higher. It asks how severe the adverse path may be before the existing H10 setup resolves.

The learned output is a q75 adverse-excursion estimate in stop-distance units, not a TP probability, expected return, PnL forecast, or direct veto rule.

No Path Risk result may retroactively alter V3/V4 or the final 33-feature ranking model.

## Target review

The target is accepted because it is aligned with the actual setup path rather than endpoint return or full-horizon drawdown after a trade would already have resolved.

For each complete valid H10 setup, the target uses the minimum low only from `t+1` through the first barrier-touch date, or through `t+10` if no barrier is touched.

This avoids the legacy failure mode where a path metric can look better while answering a different opportunity question. It also avoids using post-resolution price behavior as if it were pre-resolution trade risk.

The target is intentionally uncapped. Values above `1R` describe stop-bar adverse overshoot geometry; they are not claims about execution loss or fill price.

## Sample-selection review

The risk feature frame must retain the full causal primary-liquid population before any future outcome is joined.

It must not reuse the resolved-TP/SL-only V2/V3 training cache as the Path Risk population because doing so would condition live applicability on future label resolution.

This is a hard requirement.

## Model/search review

The effective search budget is small:

- one target;
- one quantile (`0.75`);
- one HGB regressor configuration;
- one exact frozen 33-feature information set;
- one expanding chronological fold contract;
- one constant training-quantile baseline;
- one frozen discovery gate.

There is no model zoo, quantile grid, target variant, feature family search, or post-result rescue.

## Validation review

Discovery is restricted to F1-F4. F5/F6 are not touched by the implementation/prep phase and are not automatically authorized after discovery.

Pinball loss is the primary proper scoring objective. Spearman and realized risk-quintile spread are required secondary gates so a nominal pinball gain cannot promote a model that fails to meaningfully stratify risk.

Coverage is diagnostic rather than a hard gate in V1.

## Protected outcome boundary

The implementation/prep task must not:

- load the real H10 label artifact;
- compute real adverse-excursion targets;
- fit the real PR-001 model;
- compute real pinball/Spearman/quintile results;
- access F5/F6 Path Risk outcomes;
- access post-2026-07-31 outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`.

Synthetic fixtures may test target and gate semantics.

## Authorized next action

Implement:

- Path Risk target-builder primitives;
- outcome-blind full-primary-liquid 33-feature discovery-cache builder;
- q75 HGB candidate and constant-baseline evaluator;
- fixed F1-F4 runner/gate;
- focused regression tests;
- outcome-blind cache/audit CLI.

Then run full pytest and prepare/hash the real feature-only cache through signal session `984` on Windows-local immutable sources.

Stop and return to ChatGPT before any real target/performance access.
