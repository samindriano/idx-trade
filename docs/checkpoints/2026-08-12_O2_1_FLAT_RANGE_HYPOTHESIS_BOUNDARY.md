# O2.1 Flat-Range Hypothesis Boundary

Date: 2026-08-12 (Asia/Jakarta)
Branch: `research/idx-ranking-ohlcv-o2-forward-v1`
Decision: `O2_1_HYPOTHESIS_RECORDED_NOT_AUTHORIZED`

## Why this checkpoint exists

The first accepted O2 fresh-forward session (2026-08-12) exposed 30 genuinely traded flat-range bars (`open == high == low == close`) for which frozen O2 feature `open_position` is undefined. Frozen O2 correctly excludes those rows at row level and the official O2 counter has already started under that contract.

This observation motivates a possible future challenger hypothesis: a separately trained model could explicitly represent the flat-range state (for example with a `flat_range` indicator and a preregistered convention/representation for geometry) so that genuinely traded flat bars can remain model-eligible.

## Authorization boundary

This idea is **not authorized for implementation or historical experimentation now**.

- Do not modify, refit, recalibrate, or reinterpret frozen O2.
- Do not change O2 eligibility semantics while its 100-session fresh-forward gate is active.
- Do not use the current O2 forward lane as a rescue/optimization loop after seeing forward covariates.
- Do not start an O2.1 branch, fit, benchmark, or candidate search without a separate future authorization and preregistered experiment contract.
- Continue O2 prospectively under the accepted flat-range row-exclusion rule.

## Why the hypothesis is still worth recording

The flat-range state is economically real, not missing data. A future independent challenger may therefore be scientifically reasonable, but it must be treated as a new hypothesis family with its own freeze and fresh-forward evidence. Recording the hypothesis does not grant permission to test it now.

## Revisit condition

Revisit only after an explicit future research decision authorizes a new challenger lane, preferably after the current O2 fresh-forward evidence has accumulated enough to avoid turning forward monitoring into continuous model iteration.
