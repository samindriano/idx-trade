# Decision V3 A-soft vs A-vacancy diagnosis result

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SOFT_VACANCY_DIAGNOSIS`

Manifest SHA-256: `d17f009df762678734d3f073419d44b707d55ba6dd3f25627e332438c9a7c224`

This one-shot descriptive diagnosis is consumed. Do not rerun it automatically.

## Core result

Observed Tier-A soft-replacement entrants were materially more durable than Tier-A vacancy-fill entrants in the frozen rejected Decision V3 trajectory.

- A_SOFT entries: 422
  - next-session severe: 8.7886%
  - eventual severe among completed spells: 32.1343%
  - median duration: 3 sessions
  - severe-session share at entry: 32.7014%
- A_VACANCY entries: 721
  - next-session severe: 22.9167%
  - eventual severe among completed spells: 65.4114%
  - median duration: 2 sessions
  - severe-session share at entry: 88.0721%

Overall next-session severe gap (soft - vacancy): -14.1281 percentage points.

## Candidate-evidence comparison

The durability gap is not explained by A_SOFT having uniformly stronger current/previous rank evidence.

- A_SOFT current rank mean 6.11 vs A_VACANCY 5.05 (vacancy was actually better-ranked on the entry day).
- A_SOFT previous rank mean 12.48 vs A_VACANCY 11.59.
- rank improvement current-minus-previous is nearly identical (-6.37 vs -6.54).
- Top10 persistence is also similar/slightly stronger for A_VACANCY (mean run 1.41 vs 1.33).
- A_SOFT does have materially longer Top20 persistence: mean 5.53 vs 3.43; median 3 vs 2.

## Session-context comparison

The two entry mechanisms occur in very different session environments.

- mean severe exits at entry: A_SOFT 0.43 vs A_VACANCY 2.66
- mean mandatory exits: 0.69 vs 3.29
- severe-session share: 32.7% vs 88.1%
- Top10 overlap with prior session: 5.56 vs 4.17
- Top20 overlap: 13.61 vs 10.28
- prior Top10 names collapsing >50/absent: 0.69 vs 2.55

This strongly supports session-stress / vacancy-urgency context as a major explanatory axis.

## Severe-session-only check

Restricting both classes to severe sessions reduces but does not eliminate the gap:

- A_SOFT: 138 entries, next-session severe 14.4928%
- A_VACANCY: 635 entries, next-session severe 23.9370%
- gap: -9.4443 percentage points

So raw session selection explains part, but not all, of the durability difference.

## Stratified direction

Across preregistered rank/persistence/overlap strata, A_SOFT generally retains lower next-session severe incidence. However severe-exit-count strata are mixed, which means simple severe-count thresholding is not supported as a successor rule.

Notable descriptive pattern:
- within current-rank strata: soft lower in all 3 strata
- within previous-rank strata: soft lower in both strata
- within Top10-run strata: soft lower in all comparable strata
- within Top20-run strata: soft lower in all comparable strata
- within Top10-overlap strata: soft lower in all 3 strata
- severe-exit-count strata: mixed direction

## Scientific interpretation

Supported:
1. A_SOFT durability is real descriptively and not merely because its current rank is stronger.
2. A_VACANCY is heavily concentrated in stressed, low-overlap, high-mandatory-exit sessions.
3. Session stress explains part of the A_SOFT/A_VACANCY gap, but a substantial gap remains even within severe sessions.
4. Longer Top20 persistence is a plausible candidate-evidence axis worth further diagnosis.

Not supported / not authorized:
- causal claim that soft replacement itself causes durability
- copying the V3 soft-gap rule into vacancy refill
- severe-count threshold policy
- V4 implementation or replay
- wait/cash policy simulation
- return/PnL inference

Next research question: determine whether the remaining A_SOFT advantage is primarily explained by longer Top20 persistence / relative-to-incumbent evidence, or by finer same-session selection effects that the coarse severe-session controls do not capture.
