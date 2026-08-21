# V4-X1 Decision V1 — Rank-Dynamics Diagnosis Result

Date: 2026-08-21 Asia/Jakarta
Status: `COMPLETE_OUTCOME_BLIND_DIAGNOSIS`

Source artifact root:
`D:\Documents\Project\idx-v4-x1-decision-v1-rank-dynamics-diagnosis-20260821-v1`

Manifest SHA-256:
`b350fd5f00dbd2d8cf7dc5a5166bb06e9a3206d210a0dba2a1a4ce289f86631c`

Focused local test evidence supplied by operator: `2 passed in 0.87s`.

## Scientific boundary

No realized returns, target ledger, historical PnL, Decision V2 parameter test, model refit/retune, provider/network call, or protected/fresh-forward access occurred.

## Main diagnosis

### D1 — V1 did not fail because of an implementation bug

The old kill/property tests established static one-session rule correctness. They did not exercise the real 600-session V4-X1 temporal rank path. The new diagnosis confirms that the actual score/rank process is sufficiently dynamic that the one-session hard-exit semantics induce excessive turnover even though all rule invariants are correct.

### D2 — Exact Top-10 identity is intrinsically unstable

Across 599 consecutive transitions:

- mean Top-10 overlap = `4.7796 / 10`;
- median Top-10 overlap = `5 / 10`;
- mean Top-20 overlap = `11.1002 / 20`;
- median Top-20 overlap = `12 / 20`;
- Top-10 next-session survival = `47.80%`;
- Top-20 next-session survival = `65.76%`;
- `33.67%` of current Top-10 names jump directly beyond rank 20 next session;
- only `0.57%` are absent from the next-session universe.

Therefore universe churn is not the material cause. The ranking identities themselves rotate rapidly.

### D3 — This is not mostly a rank-20/rank-21 boundary-jitter problem

Among 1,978 actual `HARD_EXIT_RANK_GT20` events:

- previous rank median = `6`;
- exit rank median = `58`;
- one-session rank jump median = `+52`;
- one-session rank jump p25 = `+25`;
- exit rank p25 = `31`.

Most hard exits therefore leap far across the threshold. Simply widening the hard-exit boundary modestly (for example 20 -> 25/30) is not supported as a root-cause fix.

### D4 — Entry instability is a first-class problem, not only exit sensitivity

For hard exits:

- holding age before exit median = `1` session;
- mean = `1.91` sessions;
- p75 = `2` sessions.

This means many names are admitted on a strong one-day rank and then hard-exited almost immediately. An exit-only remedy would leave the underlying ephemeral-entry problem largely intact.

### D5 — Whipsaw is material but not universal

After a hard exit:

- `27.00%` return to rank <=20 next session;
- `14.56%` return to Top-10 next session;
- `37.16%` return <=20 within 2 sessions;
- `43.63%` return <=20 within 3 sessions;
- `21.84%` return Top-10 within 2 sessions;
- `27.15%` return Top-10 within 3 sessions;
- `34.23%` return Top-10 within 5 sessions;
- actual Decision V1 re-buy within 2/3/5 sessions = `19.62% / 24.62% / 31.70%`.

Temporal whipsaw is therefore large enough to justify explicit investigation, but the majority of hard exits do not immediately recover. A blanket long grace period is not automatically justified.

### D6 — Relative-rank transformation is not the sole source of instability

Median consecutive-session correlations:

- raw H5 = `0.7215`;
- raw H10 = `0.8186`;
- alpha consensus = `0.8110`;
- consensus rank = `0.8070`.

The percentile/rank transform does not collapse a highly stable raw signal into an unstable rank signal. H10 is materially more persistent than H5, while the consensus/rank persistence is close to H10. Thus `relative-rank amplification` is at most a partial mechanism, not the main explanation.

The very high correlation between absolute rank movement and absolute alpha-consensus movement (`median 0.9897`) is expected because the alpha is itself rank-derived; it does not establish an independent rank-only artifact.

### D7 — Fold boundaries are locally severe but globally minor

At the five validation fold transitions:

- mean rank persistence = `0.4518` vs `0.7561` within folds;
- mean Top-10 overlap = `2.2` vs `4.80` within folds;
- Top-10 -> >20 rate = `70%` vs `33.56%` within folds.

However there are only five fold transitions out of 599. They can exaggerate local churn in the historical replay but cannot explain the persistent overall failure mode. Production prospective scoring uses one frozen refit, so this artifact should not be extrapolated as a daily live-production phenomenon.

### D8 — H5/H10 persistence asymmetry is now the most informative unexplained clue

Raw H10 has materially higher consecutive-session persistence than raw H5:

- H10 median = `0.8186`;
- H5 median = `0.7215`.

Because Decision V1 acts on a 50/50 H5/H10 consensus, the next diagnosis should determine whether ephemeral entries and next-day hard exits are disproportionately associated with:

1. H5-only strength at entry;
2. large H5-vs-H10 disagreement at entry;
3. H5 collapse while H10 remains structurally strong;
4. both heads deteriorating together.

This can distinguish whether Decision V2 should use temporal confirmation, cross-head confirmation, or a more general inertia mechanism.

## Updated hypotheses

### H7 — Ephemeral-entry / one-day spike hypothesis

A material share of V1 hard exits may originate from newly bought names whose Top-10 membership was not persistent. If so, entry confirmation is at least as important as exit confirmation.

### H8 — Head-disagreement hypothesis

Names admitted when H5 and H10 disagree strongly may have a substantially higher probability of immediate hard exit. This would make existing head agreement a plausible decision-layer stability signal without modifying the frozen alpha model.

### H9 — H5-transient / H10-veto hypothesis

Because H10 is more persistent, some consensus hard exits may be driven primarily by transient H5 deterioration while H10 remains relatively strong. If common, a decision-layer H10 confirmation/veto could be more principled than arbitrary rank-threshold widening.

### H10 — Joint-head deterioration hypothesis

If most hard exits show simultaneous severe deterioration in both H5 and H10, then head disagreement is not the answer and explicit temporal inertia / partial adjustment becomes the more plausible family.

## What is not supported now

Do not jump directly to:

- `hard_exit >30` as the primary fix;
- changing only the rank-gap threshold;
- an exit-only 2-day grace rule;
- a minimum holding period;
- model refit/retune;
- PnL-driven parameter search.

Those may later become candidates, but the current evidence says the next diagnostic must explain unstable entry and head-level dynamics first.
