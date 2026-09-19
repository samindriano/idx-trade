# Foreign Flow Fast/Slow Transition Alpha Challenger V1

Date: 2026-09-19 Asia/Jakarta  
Lane: `codex/alpha-challenger-pit-safe-20260919`  
Status: `PREREGISTERED — WAITING FOR UNSEEN EVIDENCE`

## Motivation

The audited Foreign Flow V2 family is PIT-safe and outcome-blind, but its old
universal additive H10 experiment is already consumed and failed.  That result
does not justify a rescue on the same folds.  The outcome-blind representation
shows that five-session and twenty-session persistence are not interchangeable
(Spearman correlation about `0.519`), and the direct fast-minus-slow state is
structurally orthogonal to the accepted incumbent on its common support.

The new hypothesis is role-specific: a recent foreign-flow state that is
strengthening or weakening relative to its own medium state may be a transition
or confirmation context, rather than a universal additive classifier feature.

## Frozen candidate

For each ticker and feature session:

```text
transition_score = persistence_5 - persistence_20
transition_rank  = percentile_rank_within_feature_session(transition_score)
```

If either persistence input is unavailable, `transition_rank = 0.5` and an
availability flag is retained.  No imputation, future information, fitting,
winsorization, or sign search is allowed.

The only predeclared incremental test is:

```text
candidate_score = 0.90 * incumbent_alpha_consensus + 0.10 * transition_rank
```

Both terms are higher-is-better normalized scores on `[0, 1]`. The incumbent
input is the frozen score artifact's `alpha_consensus`, not its positional
`rank_consensus` field (`1` is best there). This direction clarification was
recorded before any outcome access; it does not change the weight or introduce
a result-selected variant.

## Structural audit only

Input artifact:

- path: `D:\Documents\Project\idx-trade-foreign-flow-representation-v2-20260815-001\foreign_flow_representation_v2.parquet`
- SHA-256: `0c2212a166115b2f5b974b93096ea06b222b7451d70fa7d58257a9bed0f7a1f0`
- rows: `1,102,400`
- feature sessions: `1,259` (`2021-04-30` through `2026-07-31`)
- tickers: `979`
- causal-next-official verified: `true`
- outcome-blind / model-fit / provider-call: `true / false / false`

On the accepted V4-X1 challenger score support:

- rows: `172,697` across `600` dates;
- transition-score availability: `96.3972%`;
- transition-rank vs incumbent Spearman: approximately `-0.0060`.

These are structural facts only.  No historical performance number is used
for selection because the dates overlap consumed incumbent evaluation folds.

## Future gate

The candidate may be evaluated only on separately admitted unseen prospective
or holdout evidence.  It passes only if all gates hold:

- mean daily IC delta `>= +0.005`;
- first-quartile daily IC delta `>= 0`;
- at least `80%` non-negative 20-session blocks;
- common-support coverage `>= 95%`;
- zero PIT/provenance/missingness violations.

Otherwise the candidate is a NO-GO.  Historical folds must not be reopened
for sign, weight, threshold, or feature rescue.
