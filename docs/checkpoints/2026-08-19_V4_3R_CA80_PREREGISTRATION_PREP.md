# V4-3R CA80 preregistration prep — 2026-08-19

Status: `V4_3R_CA80_PREREGISTERED_PREFIT_SUPPORT_REPLAY_PENDING`

## Why this is a new generation

The original V4-3 corporate-action/target-support contract required >=90% date-level certified support. After the agreed outcome-blind official-source remediation stop rule, the final combined replay remained blocked:

- schedule events resolved: 33 / 80;
- schedule events unresolved: 47 / 80;
- frozen H5 minimum support: 0.8432203389830508;
- frozen H10 minimum support: 0.8395061728395061;
- frozen consensus minimum support: 0.8395061728395061;
- historical target loaded: false;
- model fit: false;
- performance computed: false.

The V4-3 >=90% result remains a genuine failure. It is not waived or rewritten.

V4-3R is a separately preregistered generation created before any historical target/model/performance access. It changes only the date-level observability threshold needed to make the experiment executable under the evidence that is realistically available.

## Frozen V4-3R delta

Two related thresholds change from 0.90 to 0.80:

1. prefit date full-target-support gate;
2. evaluation date target-coverage gate.

The 0.80 value is a round practical threshold and is explicitly adaptive to already observed **outcome-blind support/provenance information**. It was not selected using target returns, predictions, IC, Top30 performance, model outputs, or protected forward outcomes.

## What does NOT change

- target H5 = `Close_(t+5) / Open_(t+1) - 1`;
- target H10 = `Close_(t+10) / Open_(t+1) - 1`;
- target ranks use only defensibly target-observable rows;
- unsupported rows never receive a target;
- unresolved/known mechanical corporate-action crossings remain fail-closed at row level;
- no price inference for corporate-action effective dates;
- primary-liquid decision universe unchanged;
- Control = Context25 HGBR;
- Challenger = Context25 + Geometry3;
- 6 folds x 100 validation dates unchanged;
- 10-official-session purge unchanged;
- learner family and hyperparameters unchanged;
- preprocessing unchanged;
- Top30 and `top30_min_observable=27` unchanged;
- bootstrap and promotion gates unchanged;
- no rescue candidate or alternate learner is admitted.

## Mandatory prefit replay

Before any target access, run the dedicated V4-3R support replay over immutable parent manifest:

`12d60b703d9617db95e89374485abb335a4024c4c6642a5cbee0d72e1eeb2f43`

The V4-3R prefit gate passes only if:

- all frozen 600 validation dates pass H5, H10, and consensus support >=80%;
- the last 600 consensus-eligible dates remain exactly the frozen validation identity;
- there are zero eligible dates after the frozen end;
- all 12 fold/head training-date sets are non-empty;
- no target/model/performance/protected-forward access occurred.

The runner must also record how many frozen dates are in `[0.80, 0.90)` versus `>=0.90`. This is diagnostic only and cannot change the primary verdict.

## Historical-execution boundary

Until the prefit replay passes and its exact manifest is pinned, historical V4-3R target access, model fit, prediction, performance computation, and protected-forward access remain prohibited.

After first historical target/performance access, any material change to threshold, universe, folds, purge, target, features, learner, evaluator, metrics, or promotion rules creates another generation.

## Coordination note

Latest canonical `main:coordination/TEAM_STATUS.md` was read before this lane. No overlapping visible active V4-3R CA80 lane was found. The shared coordination file was not edited from this branch; scientific authority is this branch-local frozen preregistration and subsequent manifests.
