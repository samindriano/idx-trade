# Decision V3 A Same-Session Diagnosis Result

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_A_SAME_SESSION_DIAGNOSIS`

Frozen manifest SHA-256: `bb2b38696d83629ace4a50609eb042e42951086fda27c7d9f39ad50f25f87902`

## Population

- paired sessions: 151
- A_SOFT entries: 204
- A_VACANCY entries: 223

## Durability

Entry-weighted:
- A_SOFT next-session severe: 11.33%
- A_VACANCY next-session severe: 18.02%
- gap soft minus vacancy: -6.69 pp
- A_SOFT eventual severe among completed: 37.44%
- A_VACANCY eventual severe among completed: 52.49%
- gap soft minus vacancy: -15.05 pp
- median holding: A_SOFT 3 sessions vs A_VACANCY 2 sessions

Equal-session-weighted:
- next-session severe mean gap: -4.89 pp across 150 observable paired sessions
- eventual severe mean gap: -11.58 pp across 149 comparable paired sessions

## Candidate evidence inside the same sessions

A_SOFT was not the higher-ranked entrant on the entry date. In paired sessions:
- current rank mean: A_SOFT 7.14 vs A_VACANCY 3.91
- previous rank mean: A_SOFT 13.03 vs A_VACANCY 11.53
- rank improvement current-minus-previous: A_SOFT -5.89 vs A_VACANCY -7.62

Thus A_VACANCY looked mechanically stronger by current/previous rank.

Persistence differences were modest and mixed:
- Top10 run mean: A_SOFT 1.30 vs A_VACANCY 1.43
- Top20 run mean: A_SOFT 5.00 vs A_VACANCY 4.76
- last-3 Top20 count: A_SOFT 2.53 vs A_VACANCY 2.43
- t-2/t-3 historical ranks were somewhat better for A_SOFT in aggregate, but equal-session directions were mixed rather than monotone.

A_SOFT soft-rank-gap against the displaced acceptable incumbent:
- mean 9.26
- median 9
- p25 7
- p75 11
- p90 13

## Stratified direction

Within same-session candidate-evidence strata, A_SOFT retained lower next-session severe incidence in every comparable stratum for:
- current rank: 3/3
- previous rank: 2/2
- Top10 run: 3/3
- Top20 run: 2/2
- last-3 Top20 count: 2/2

Median soft-minus-vacancy next-severe gaps ranged roughly -5 pp to -11 pp depending on dimension.

## Scientific interpretation

Same-session restriction removes session-level stress confounding by construction. The durability advantage of A_SOFT therefore survives after holding the entry session fixed.

The result does **not** establish a causal effect of soft replacement. Selection into A_SOFT vs A_VACANCY is still non-random. However, the evidence weakens explanations based only on session stress, raw current rank, previous rank, or simple Top10/Top20 persistence.

The strongest surviving architectural hypothesis is that **positive relative admission evidence / competition against an existing acceptable incumbent contains information that unconditional vacancy filling lacks**. A_SOFT entrants were often lower-ranked than A_VACANCY entrants yet more durable, and the observed soft replacement margin was materially above the minimum rule threshold (median gap 9).

This does not authorize Decision V4 implementation or replay. Any successor design must remain preregistered and should distinguish incumbent-removal urgency from challenger-admission evidence without using cash-underfill as a hidden churn solution.

Scientific boundary remained clean: no alternative policy, portfolio/PnL, returns/outcomes, protected/fresh forward, model refit, or provider/network access.