# V4-X1 Decision V1 — Rank-Dynamics Diagnosis Prep

Date: 2026-08-21 Asia/Jakarta
Status: `PREPARED_OUTCOME_BLIND_DIAGNOSIS_ONLY`

## Trigger

The exact 600-OOS structural trajectory replay of frozen Decision V1 found mechanically undesirable churn:

- 2,686 replacements excluding bootstrap;
- mean 4.48 and median 4 replacements per transition;
- 78.1% of transition days have >=3 replacements;
- only 6/599 no-change transitions;
- median completed holding spell 1 session;
- 1,978/2,686 sells are `HARD_EXIT_RANK_GT20`;
- only ~14.1% turnover reduction versus exact daily Top-10.

No realized return/PnL was used.

## Why prior kill tests did not catch this

The existing Decision V1 unit/property tests were designed for **single-session contract correctness**:

- exact gap boundary;
- rank20/rank21 hard-exit boundary;
- deterministic ordering;
- fixed-point replacement invariants;
- forged/tampered artifacts;
- row-order invariance;
- randomized static holdings.

The 10,000 randomized property cases are independent cross-sectional snapshots against a synthetic monotonic score table. They do not create a realistic sequence of changing V4-X1 scores/ranks and do not constrain turnover or holding duration.

Therefore there is no contradiction: implementation correctness passed, while longitudinal policy viability was untested.

## Hypotheses to diagnose before any Decision V2 design

### H1 — Rank-transition discontinuity

The real V4-X1 cross-section may have low enough day-to-day rank persistence that a meaningful fraction of current Top-10 names jump directly beyond rank 20 next session.

Measure Top-10 -> Top-10 / 11–20 / >20 / absent transitions, overall and from starting rank buckets 1–3, 4–6, 7–10.

### H2 — Relative-rank amplification

Because `alpha_h5` and `alpha_h10` are within-date percentile ranks of raw model predictions, and `alpha_consensus` averages those percentiles, relatively modest raw prediction movement may create large changes in relative rank when the cross-section is dense or many names rotate together.

Measure consecutive-session raw H5/H10 correlation, percentile-alpha correlation, rank correlation, rank deltas, and local alpha spacing around ranks 10/11 and 20/21.

### H3 — Fold-boundary model switching

Each 100-date validation fold is scored by a separately fitted model. Some instability may be concentrated at the five fold transitions rather than being a general daily property.

Compare fold-boundary transitions with the 594 within-fold transitions.

### H4 — One-day hard-exit whipsaw

A single `rank >20` observation may often be transient. If recently exited names return <=20 or Top-10 within 1–5 sessions and are then re-bought, V1's one-observation hard exit acts as a whipsaw amplifier.

Measure rank recovery and actual re-buy delay after every hard exit.

### H5 — Universe churn

Changing eligibility/universe membership may explain apparent rank jumps.

Measure prior-session names absent next session and compare with the already-small `NO_LONGER_IN_V4_X1_DECISION_UNIVERSE` exit count.

### H6 — Daily myopia versus multi-session alpha horizon

V4-X1 combines H5/H10 predictive heads. A Decision policy that acts on every daily rank shock may be temporally mismatched to the persistence/decay of the underlying signal. This is a conceptual hypothesis only at this stage; no minimum holding period or confirmation rule is authorized yet.

## Explicitly forbidden in this diagnosis

- realized H5/H10 returns;
- target ledger;
- historical portfolio PnL;
- parameter sweep;
- rank threshold sweep;
- exit confirmation simulation;
- turnover cap simulation;
- rolling score/rank smoothing candidate simulation;
- any Decision V2 selection;
- model fit/refit/retune;
- prospective/protected forward outcome access;
- provider/network calls.

## Decision after diagnosis

The diagnosis should narrow the problem to one or more mechanism classes. Only then create a **small theory-driven Decision V2 preregistration**. Possible mechanisms may include temporal confirmation, score-margin logic, slower target adjustment, or explicit turnover control, but none is selected or authorized by this checkpoint.
