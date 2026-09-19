# Claim — Foreign Flow Fast/Slow Transition Challenger V1

- Owner: isolated alpha challenger lane
- Branch: `codex/alpha-challenger-pit-safe-20260919`
- Scope: outcome-blind, PIT-safe derived overlay only
- Incumbent protection: do not modify, refit, rescore, or replace V4-X1

## Frozen question

Does a fixed cross-sectional overlay based on the difference between
five-session and twenty-session foreign-flow persistence add stable value to
the frozen incumbent on genuinely unseen prospective sessions?

## Frozen construction

For each `(ticker, feature_session)`:

`transition_score = foreign_weighted_persistence_5 - foreign_weighted_persistence_20`

The overlay is the within-session percentile rank of `transition_score`.
Unavailable inputs are neutral rank `0.5`, never imputed or forward-filled.
The initial blend to evaluate, if eligible unseen evidence becomes available,
is `0.90 * incumbent_alpha_consensus + 0.10 * transition_rank`, with both
terms higher-is-better on `[0, 1]`.

The phrase `incumbent_rank` in the initial draft was corrected before any
outcome access. `rank_consensus` is a positional rank where `1` is best and
must not be blended with the higher-is-better transition percentile.

## Evidence boundary

The Foreign Flow V2 representation is an offline, hash-verified,
outcome-blind artifact.  Its historical dates overlap the consumed incumbent
evaluation geometry, so this challenger must not be selected or rejected from
those historical folds.  No prospective provider call, protected outcome, or
counter mutation is authorized by this claim.

## Acceptance gate for future unseen evidence

Evaluate only on a separately admitted prospective/holdout set with the same
universe and date-level metric as the incumbent:

- mean daily IC delta at least `+0.005`;
- first-quartile daily IC delta non-negative;
- at least `80%` non-negative 20-session blocks;
- common-support coverage at least `95%`;
- no PIT, provenance, or missingness violation.

Any failed gate is a NO-GO.  Do not flip the sign, change the weight, or
search variants after seeing results.
