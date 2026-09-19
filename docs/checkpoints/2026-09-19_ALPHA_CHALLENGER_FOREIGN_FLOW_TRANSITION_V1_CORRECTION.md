# Foreign Flow Transition Challenger V1 — Direction Correction

Date: 2026-09-19 (Asia/Jakarta)

Status: `CORRECTED_BEFORE_OUTCOME_ACCESS`

## Issue

The first outcome-blind prospective diagnostic mixed two opposite rank
orientations:

- `rank_consensus`: positional rank, where `1` is best;
- `foreign_flow_transition_rank`: percentile rank, where larger is better.

It then used `nlargest` on the positional incumbent rank and on the mixed
blend. The reported one-session `100%` top-30 overlap and `0%` churn are
therefore invalid structural evidence and are superseded. No performance or
outcome claim depended on them.

## Corrected contract

The fixed blend uses the frozen score artifact's normalized higher-is-better
`alpha_consensus`:

```text
candidate_score = 0.90 * alpha_consensus + 0.10 * transition_rank
```

Candidate membership is selected by descending `candidate_score`. The weight,
transition feature, PIT boundary, and no-outcome rule are unchanged.

## Corrected outcome-blind audit

The audit covered all 15 available clean V4-X1 prospective score artifacts
from 2026-08-21 through 2026-09-17. The transition overlay was genuinely
available on only 5 of those 15 feature sessions: 2026-09-10, 09-11, 09-14,
09-15, and 09-17. Earlier sessions receive the explicitly neutral `0.5` rank
because the 20-session persistence input is incomplete; they are not evidence
of transition signal orthogonality.

On the five available sessions:

- availability ranged from `95.9459%` to `96.9072%` on common score rows;
- mean transition-vs-incumbent Spearman was `-0.01552985`;
- mean corrected top-30 overlap was `84.6667%`;
- mean corrected top-30 churn was `15.3333%`;
- maximum corrected top-30 churn was `20%`.

This remains structural evidence only. No target, label, return, protected
outcome, counter, provider, or canonical artifact was accessed or written.

## Disposition

The candidate remains `SHADOW_ONLY / NOT_ADMITTED`. The corrected evidence is
more honest but weaker than the superseded diagnostic: it shows moderate
orthogonality and meaningful membership change on only five sessions, not a
proven alpha improvement. The predeclared OOS performance gate remains
unchanged.
