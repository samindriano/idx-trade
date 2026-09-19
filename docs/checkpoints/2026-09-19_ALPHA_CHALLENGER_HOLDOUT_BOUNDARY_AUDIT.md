# Alpha Challenger Holdout Boundary Audit

Date: 2026-09-19 (Asia/Jakarta)

Status: `NO_ADMISSIBLE_CANONICAL_OOS_HOLDOUT`

## Scope

This is a read-only boundary audit for the isolated alpha-challenger lane. It
does not score the incumbent, open protected outcomes, mutate the prospective
counter, refit the incumbent, or change canonical runtime data.

## Frozen incumbent boundary

The accepted clean V4-X1 final-refit bundle records:

- model generation: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`;
- frozen historical end: `2026-07-17` / session index `1249`;
- clean panel SHA-256:
  `25eb0d0c6fdbd1daefd0f735c08f18feeeef6dfbd0bd55cf8ab7527cf4784c2e`;
- `post_freeze_numeric_target_accessed=false`;
- `historical_prediction_generated=false`;
- `historical_performance_computed=false`;
- `prospective_scoring_authorized=false`.

The final-refit training-date file ends at 2026-07-17 for both H5 and H10.

## Holdout availability

The clean model-safe panel covers 2021-04-29 through 2026-07-31. After the
freeze boundary it contains ten official sessions: 2026-07-20 through
2026-07-31.

Under the frozen target identity:

- H5 uses `Close_(t+5) / Open_(t+1) - 1`;
- H10 uses `Close_(t+10) / Open_(t+1) - 1`;
- canonical consensus requires both target ranks and is `0.5 * H5 + 0.5 * H10`.

The post-freeze panel dates can mature H5 only for the first five post-freeze
signal sessions (2026-07-20 through 2026-07-24). No post-freeze signal session
has H10 terminal data inside this panel. Therefore there is no admissible
canonical H5/H10 consensus holdout in the clean panel.

H5-only evaluation is intentionally not substituted: it would change the
frozen target identity and would not be a comparable incumbent-vs-challenger
test.

## Gate result

`NO_ADMISSIBLE_CANONICAL_OOS_HOLDOUT`

The foreign-flow transition challenger remains a structural/prospective shadow
candidate only. A genuine performance claim requires a separately authorized
fresh canonical evaluation after both horizons are observable; no such outcome
was accessed by this audit.
