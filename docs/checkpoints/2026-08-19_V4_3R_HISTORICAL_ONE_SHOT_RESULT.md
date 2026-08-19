# Ranking V4-3R CA80 — historical one-shot result

Date: 2026-08-19 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3r-ca80-prereg-v1`
Generation: `V4_3R_CA80`
Status: `V4_3R_GENERATION_NO_SURVIVOR`

## Immutable result

The preregistered one-shot historical-development execution completed after the prefit support gate, execution freeze, compile checks, and focused tests had passed.

Final runner output:

- `fit_count = 24`
- `historical_target_loaded = true`
- `model_fit = true`
- `prediction_generated = true`
- `performance_computed = true`
- `protected_forward_accessed = false`
- `provider_calls = false`
- `control_absolute_pass = false`
- `challenger_absolute_pass = false`
- `challenger_incremental_pass = false`
- `preregistered_decision = V4_GENERATION_NO_SURVIVOR`
- final status `V4_3R_GENERATION_NO_SURVIVOR`
- next `STOP_FOR_INDEPENDENT_REVIEW_NO_RESCUE_OR_RETUNE`

Target-support parity checks were exact:

- H5 mismatches: `0`
- H10 mismatches: `0`
- consensus mismatches: `0`

External result root:

`D:\Documents\Project\idx-v4-3r-historical-one-shot-20260819-v1`

Result manifest:

`D:\Documents\Project\idx-v4-3r-historical-one-shot-20260819-v1\MANIFEST.json`

Manifest SHA-256:

`05c00e5ab42adf34f9bffff4dd5237043d6d281b3e0abe1571f14a59eeb16fef`

Summary:

`D:\Documents\Project\idx-v4-3r-historical-one-shot-20260819-v1\summary.json`

## Scientific interpretation

This is a clean no-survivor verdict under the frozen V4-3R contract. The control failed its absolute promotion gates, the challenger failed its absolute gates, and the challenger also failed the incremental gate. Therefore neither architecture is eligible for promotion or fresh prospective confirmation from this generation.

The result is decision-valid with respect to the frozen target-support contract because all H5/H10/consensus row-level support parity mismatches are zero and the runner completed exactly 24 preregistered fits.

The original V4-3 generation remains separately failed and closed under its preregistered >=90% CA-support gate. V4-3R does not retroactively pass V4-3; V4-3R is the separately preregistered CA80 generation whose only scientific threshold delta was the date-level support/evaluation gate from 0.90 to 0.80.

## Runtime warning note

During sklearn/joblib execution on Windows, `loky` attempted physical-core discovery through `wmic`, which is unavailable on this machine. A subprocess reader thread also emitted a `cp1252` decode exception. These warnings did not terminate the main Python process: the runner subsequently completed all 24 fits, produced the final result JSON, wrote the result manifest/summary, and returned the explicit frozen verdict above. No scientific interpretation should be changed because of these warnings.

## Post-result boundary

`HISTORICAL_ACCESS_BOUNDARY.json` has been crossed and this V4-3R generation is outcome-open and consumed.

Do not:

- rerun V4-3R;
- delete the result root and retry;
- retune either learner;
- change the 80% gate;
- change features, folds, purge, targets, Top30 rules, metrics, bootstrap, or promotion gates;
- create a rescue candidate inside V4-3R;
- reopen CA acquisition to rescue this result;
- inspect or use protected/fresh-forward outcomes for this generation.

Any material scientific continuation requires a separately preregistered new generation with a new hypothesis justified independently of this failed result.

Verdict:

`V4_3R_GENERATION_NO_SURVIVOR`
