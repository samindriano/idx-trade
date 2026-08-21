# Decision V2 — Failure-Mechanism Diagnosis Preregistration

Date: 2026-08-21 Asia/Jakarta

Status: `PREREGISTERED_NOT_EXECUTED`

This diagnosis follows the frozen `DECISION_V2_MINIMAL_STRUCTURAL_REJECT` result. It is descriptive and outcome-blind. It does not authorize a Decision V2.1 rule, threshold sweep, rerun of the V2 structural replay, return/PnL access, or alpha modification.

## Pinned evidence

- structural result manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`
- structural plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`
- historical source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- score parquet SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- exact source: 600 sessions / 172,697 score rows.

## Question 1 — Exit-grace severity

For every frozen `EXIT_PENDING_1` observation, report current rank, previous rank, rank jump, next-session rank/absence, whether the name recovered to rank <=20, and whether the following frozen Decision state became confirmed exit.

Describe recovery and rank-damage concentration using fixed descriptive current-rank bins `21–30`, `31–50`, `51–100`, `101–200`, and `>200`. These bins are reporting strata only and MUST NOT be treated as candidate Decision thresholds.

Key outputs: counts, recovery rate, next-session Top-20/Top-10 rate, current/next rank distributions, and share of total `rank-20` excess carried by each bin.

## Question 2 — Candidate scarcity

For every frozen underfilled session, enumerate current Top-10 challengers rejected only for lack of prior-session confirmation. Report previous-rank category (`21–30`, `31–50`, `51–100`, `101–200`, `>200`, or absent), current rank, next-session rank/absence, and next-session Top-10/Top-20 persistence.

Report rejected-fresh count versus frozen unfilled slots per session and the share of underfilled sessions where rejected fresh supply numerically equals/exceeds the vacancy count. This is a supply diagnostic only; no hypothetical fills are simulated.

## Question 3 — Residual churn attribution

For every non-bootstrap transition, count frozen sell/buy intents by reason: confirmed exit, universe exit, soft replacement, qualified vacancy fill, and any other frozen reason. For transitions with replacement_count >=3, report mechanism incidence and counts, plus a deterministic descriptive dominant-mechanism label. No alternative sequencing or replacement policy is simulated.

## Question 4 — Time concentration

Repeat the core Q1–Q3 summaries for the six frozen 100-session blocks. Determine whether blocks 3/6 are quantitatively worse versions of the same mechanism or show a different composition.

## Forbidden

No realized returns, PnL, protected/fresh-forward outcomes, provider/network call, model refit/retune, alternative Decision threshold, alternative confirmation length, alternative gap, policy simulation, parameter sweep, or Decision V2 replay rerun.

## Next step after diagnosis

Freeze the descriptive diagnosis first. Only then may a separately named successor Decision preregistration be drafted, and only if its mechanism is justified by this diagnosis rather than by threshold hunting.
