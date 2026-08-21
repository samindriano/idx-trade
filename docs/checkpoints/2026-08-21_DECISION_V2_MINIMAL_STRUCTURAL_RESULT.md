# Decision V2 Minimal — Structural Replay Result

Date: 2026-08-21 Asia/Jakarta

Status: `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`

Scientific boundary: one authorized outcome-blind structural replay only. No realized returns, historical PnL, protected/fresh-forward outcomes, provider/network calls, model refit/retune, Decision parameter sweep, alternative threshold test, pre-roll, or fold reset were used.

## 1. Pinned execution identity

- alpha model ID: `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`
- alpha fingerprint: `30e1b505a731da944021078a80d62d75afe7bd461507b2d207b28849140f79cf`
- Decision rule ID: `V4_X1_DECISION_V2_MINIMAL_V1`
- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- source score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- exact score sessions: `600`
- exact score rows: `172,697`
- replay contract canonical SHA-256: `2f4e04fe060b43da6d555717a5aab687c10f40fa114ee954ae24082f912d455f`
- result artifact root: `D:\Documents\Project\idx-v4-x1-decision-v2-minimal-structural-replay-20260821-v1`
- result manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`
- primary / secondary deterministic plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`

## 2. Gate verdicts

| Gate | Verdict | Key evidence |
|---|---|---|
| A — correctness / determinism | PASS | all correctness violations `0`; second pass exact match |
| B — churn reduction | FAIL | mean replacements `2.3957 > 2.25`; >=3 replacement transitions `40.90% > 35%`; turnover vs naive `0.4589` passes |
| C — holding persistence | PASS | median completed spell `3`; one-session share `10.10%` |
| D — rank quality | FAIL | full-target Top-10 overlap `7.191` passes; mean target rank `21.345 > 12` |
| E — capacity | FAIL | mean size `9.488` and size-10 share `77.5%` pass; size <=8 share `14.17% > 10%` |
| F — no hidden stale state | PASS | stale-state violations `0` |

Overall frozen verdict: `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`.

## 3. What V2 materially improved

V2 Minimal solved part of the V1 problem and should not be interpreted as a null result.

### Churn improvement

- V2 total structural replacements excluding bootstrap: `1,435`.
- frozen V1 reference: `2,686`.
- naive daily exact Top-10 reference: `3,127`.
- V2/V1 replacement ratio: `0.53425`, i.e. about a `46.6%` reduction versus V1.
- V2/naive ratio: `0.45891`.
- mean replacements per transition fell from about `4.48` in V1 to `2.396` in V2.

The churn gate still failed because the preregistered requirement was deliberately stronger: mean <=2.25 and >=3 replacements on <=35% of transitions. Actual >=3 share was `40.90%`.

### Holding persistence improvement

- median completed spell increased from V1's `1` session to `3` sessions;
- mean completed spell `4.385` sessions;
- one-session spell share only `10.10%`;
- p90 `9` sessions; p95 `13`; max `45`.

Thus temporal hysteresis genuinely created multi-session persistence rather than merely changing labels.

### Current-alpha overlap remained respectable when full

- mean current Top-10 overlap on full 10-name targets: `7.191 / 10`;
- normalized all-session Top-10 overlap: `0.6858`;
- mean current Top-20 overlap: `7.553` names.

The rejection therefore is not because V2 ignored the alpha everywhere.

## 4. Primary failure mechanism: V2 over-corrected V1 with binary inertia

V1 was too reactive to today's rank. V2 Minimal corrected this with two binary temporal mechanisms:

1. every first observation outside rank 20 receives one-session exit grace regardless of how severe the rank collapse is;
2. every fresh Top-10 entrant from prior rank >20/absence is rejected regardless of how strong the current rank is.

The replay shows that these mechanisms are directionally useful but too blunt when used as hard binary rules.

### 4.1 Exit grace protects recoveries, but also carries catastrophic rank collapses

Decision-state behavior:

- `EXIT_PENDING_1` observations: `1,161`;
- pending observations eligible for next-session resolution: `1,159`;
- recovered to <=20 next session: `359`;
- recovery rate: `30.97%`;
- confirmed exits: `798`.

So one-session grace prevented a meaningful fraction of V1-style immediate hard exits: roughly 31% of pending cases recovered.

However, the rank-quality tail is severe:

- target rank >20 name-days: `1,161`;
- sessions containing at least one >20 holding: `472 / 600`;
- mean number of >20 holdings per session: `1.935`;
- median current rank among >20 target rows: `51`;
- mean: `80.65`;
- p75: `110`;
- p90: `185`;
- p95: `222`;
- max: `405`.

This explains the otherwise unusual combination:

- median target rank = `7` (typical holding remains strong), but
- mean target rank = `21.345` (FAIL).

The failure is therefore a heavy-tail stale-holding problem, not broad portfolio rank decay. A small number of very severe first-day collapses are mechanically retained because the V2 rule treats rank `21` and rank `200` identically on the first outside-20 observation.

This is an important architecture lesson: temporal hysteresis is useful, but pure observation-count confirmation is not severity-aware.

### 4.2 Entry confirmation prevents chasing fresh spikes, but creates episodic candidate scarcity

- fresh Top-10 rejected as unconfirmed: `1,792`;
- unfilled sessions: `135`;
- unfilled vacancy-days: `307`;
- mean target size: `9.488`;
- full 10-name target: `77.5%` of sessions;
- target size 9: `8.33%`;
- target size <=8: `14.17%` (FAIL);
- minimum target size: `4`.

The mean capacity is acceptable and most sessions are full; the problem is episodic tail underfill rather than continuous low capacity.

This indicates that the binary `current Top-10 AND previous <=20` challenger rule is too restrictive in some unstable cross-sections. It correctly blocks one-day spikes, but at times blocks so much of current Top-10 supply that confirmed exits cannot be replaced.

This is the mirror image of the exit-grace failure: incumbent evidence is too permissive for one day, while challenger evidence is too restrictive for one day.

## 5. Residual churn source

V2 still produced:

- confirmed exits: `798`;
- universe exits: `21`;
- soft replacements: `468`;
- vacancy fills: `819`;
- total conservative replacement count: `1,435`.

The churn miss is comparatively modest versus the rank-quality/capacity misses:

- mean `2.3957` vs gate `2.25`;
- >=3 share `40.90%` vs gate `35%`;
- naive turnover ratio already passes at `0.4589`.

Therefore the next design should not optimize directly for another small turnover reduction. First diagnose whether residual churn is dominated by:

- confirmed-exit chains after severe rank collapses;
- soft-replacement activity among otherwise acceptable 11..20 incumbents;
- vacancy exit/fill sequencing under candidate scarcity.

No parameter changes are authorized from this result alone.

## 6. Temporal concentration / instability

The failure is not uniform across the six 100-session blocks.

Especially weak blocks:

### Block / fold 3

- mean replacements `3.04`;
- >=3 replacement share `61%`;
- mean target rank `36.09`;
- mean target size `8.56`;
- full target only `43%`;
- `288` >20 name-days;
- `57` unfilled sessions.

### Block / fold 6

- mean replacements `2.89`;
- >=3 replacement share `56%`;
- mean target rank `32.62`;
- mean target size `9.26`;
- full target `66%`;
- `255` >20 name-days;
- `34` unfilled sessions.

Other blocks are materially healthier, particularly 1 and 4.

Fold-boundary transitions can be locally severe (e.g. target size `4`, mean rank `178.25` at index 300; size `6`, mean rank `247.17` at index 500), but the rejection cannot be dismissed as a five-boundary artifact because whole 100-session blocks 3 and 6 remain weak.

Production prospective operation uses one frozen final refit, so fold-boundary behavior should not be converted into a production-specific Decision rule. It is diagnostic evidence only.

## 7. Scientific interpretation

The best current causal summary is:

> Decision V2 Minimal successfully reduced V1's excessive sensitivity, but over-corrected with binary temporal inertia. It often retains a severely collapsed incumbent for one session regardless of collapse magnitude while simultaneously rejecting fresh challengers regardless of current strength. This creates a heavy tail of stale rank exposure, episodic underfill, and enough residual replacement clustering to miss the churn gate.

This is stronger and more specific than saying either `temporal confirmation does not work` or `V4-X1 is unsalvageable`.

Temporal information demonstrably helps: holding persistence and churn improved substantially. The problem is the binary implementation of temporal evidence, not the existence of temporal evidence itself.

## 8. What this result does NOT authorize

Do not now silently try:

- previous-rank threshold 25/30/etc.;
- three-session exit confirmation;
- immediate exit threshold 30/50/etc.;
- different gap-5 values;
- disabling soft replacement;
- H5/H10 veto/rescue rules;
- score smoothing;
- PnL/return inspection;
- alpha refit or V4-X2 launch.

Any changed policy requires a separately named preregistration after mechanism diagnosis.

## 9. Next authorized work

The next work is a narrow outcome-blind **Decision V2 failure-mechanism diagnosis**, not Decision V2.1 simulation.

It should answer four questions from the frozen structural ledger / pinned alpha ranks only:

1. **Exit-grace severity:** among `EXIT_PENDING_1`, how do recovery probability and next-state differ by current collapse magnitude / rank trajectory, and how much of mean-rank damage comes from extreme first-day collapses?
2. **Candidate scarcity:** on underfilled sessions, how many current Top-10 names are unavailable only because they are fresh/unconfirmed, and what prior-rank categories account for that shortage?
3. **Residual churn attribution:** how much transition clustering comes from confirmed exits, soft replacements, universe exits, and exit/fill sequencing; which mechanism dominates >=3-replacement sessions?
4. **Time concentration:** are the above mechanisms qualitatively consistent across blocks, or do blocks 3/6 fail through a distinct mechanism?

This diagnosis must not simulate alternative Decision thresholds or use realized returns/PnL.

Only after that diagnosis should a separately named successor policy be preregistered.
