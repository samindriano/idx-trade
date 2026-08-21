# V4-X1 Decision V1 — Temporal Persistence Diagnosis Prep

Date: 2026-08-21 Asia/Jakarta
Status: `PREPARED_OUTCOME_BLIND_TEMPORAL_DIAGNOSIS_ONLY`

## Trigger

The completed head-entry diagnosis showed that cross-head disagreement worsens instability but does not explain most one-session failures:

- `BOTH_LE10` entries still hard-exit next session at ~39.7%;
- `H5_ONLY_LE10` ~51.4%;
- `H10_ONLY_LE10` ~46.0%;
- among one-session hard exits, both H5 and H10 are already beyond rank 20 in ~74.2% of cases;
- H10 remains <=20 in only ~16.0% of one-session hard exits.

Therefore an H10-only veto or same-session cross-head confirmation cannot be assumed to solve the dominant failure mode.

## Scientific question

Does prior temporal persistence materially distinguish durable V4-X1 extreme-rank candidates from one-day spikes?

The diagnosis will condition current Top-10 / Top-20 candidates on only prior rank history and measure future rank survival. It does not simulate a Decision V2 rule.

## Predeclared structural views

For current consensus Top-10 candidates, compare:

1. previous-session consensus Top-10;
2. previous-session consensus rank 11–20;
3. previous-session rank >20 or absent;
4. current consecutive Top-10 run >=2 / >=3 sessions;
5. current consecutive Top-20 run >=2 / >=3 sessions;
6. same-session H5/H10 agreement, combined with prior consensus persistence.

For candidate-capacity context, also measure how many names per session satisfy persistent Top-20 conditions. This is descriptive only and is not a portfolio-size or Decision-V2 parameter test.

Primary future structural measurements:

- next-session Top-10 survival;
- next-session Top-20 survival / drop >20;
- any drop >20 over the next three available sessions;
- next-session rank movement;
- per-session persistent-candidate counts.

## Interpretation boundary

A large reduction in next-session / three-session rank failure after simple prior persistence would support the hypothesis that a Decision layer can filter one-day alpha spikes without changing the frozen alpha model.

If even previously persistent, cross-head-supported candidates continue to collapse at rates close to unconfirmed Top-10 candidates, that is evidence that the extreme-rank instability is intrinsic enough to justify considering a separately named stability-aware alpha challenger.

No numerical pass/fail threshold is preregistered here; the goal is mechanism diagnosis, not parameter selection.

## Explicitly forbidden

- realized returns or target outcomes;
- historical portfolio PnL;
- Decision V2 simulation;
- holding-period / smoothing / threshold sweep;
- model fit/refit/retune;
- provider/network calls;
- protected or fresh-forward outcomes.
