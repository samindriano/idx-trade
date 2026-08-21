# Decision V2 — Failure-Mechanism Diagnosis Result

Date: 2026-08-21 Asia/Jakarta

Status: `COMPLETE_OUTCOME_BLIND_DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS`

Scientific boundary: descriptive mechanism diagnosis only. This diagnosis did not rerun Decision V2, simulate alternative Decision rules or thresholds, sweep parameters, inspect realized returns/PnL, access protected/fresh-forward outcomes, call providers/network, or refit/retune the alpha model.

## Pinned identity

- frozen Decision structural status: `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`
- structural manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`
- structural plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`
- historical source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- historical score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- score sessions: `600`
- score rows: `172,697`
- diagnosis artifact root: `D:\Documents\Project\idx-v4-x1-decision-v2-failure-mechanism-diagnosis-20260821-v1`
- diagnosis manifest SHA-256: `bada04d8403457d4456653fad66d9119b80349f65e13be9cff911a886c31af06`

## 1. Exit-grace severity is strongly informative

Among `EXIT_PENDING_1`, next-session recovery to rank <=20 declines materially as the current collapse becomes more severe:

| Current-rank reporting stratum | n | Recovery <=20 next session | Confirmed exit next session |
|---|---:|---:|---:|
| 21–30 | 313 | 49.68% | 50.32% |
| 31–50 | 265 | 36.74% | 62.88% |
| 51–100 | 255 | 25.88% | 74.12% |
| 101–200 | 237 | 13.08% | 86.50% |
| >200 | 91 | 10.99% | 89.01% |

The two most severe strata (>100) are only 328/1,161 pending observations (~28.3%) but account for about 72.3% of total rank excess beyond 20. Including rank 51–100, observations worse than rank 50 account for about 90.7% of total rank excess.

Therefore the V2 rank-quality failure is concentrated in severe first-day collapses. Treating rank 21 and rank 200 identically for one-session grace is not supported by the observed alpha-rank dynamics.

This does **not** select an emergency-exit threshold. The bins above are descriptive reporting strata only.

## 2. Candidate scarcity is policy-created, not a lack of current Top-10 supply

Across all `135` underfilled sessions, rejected fresh Top-10 supply was at least as large as the number of vacancies (`share_underfilled_sessions_rejected_supply_ge_vacancy = 1.0`).

Thus every underfilled session had enough current Top-10 names to fill the portfolio mechanically; the vacancies existed because the binary previous-rank confirmation rule rejected those names.

Next-session Top-20 persistence of rejected fresh Top-10 candidates varies by previous-rank history:

| Previous-rank reporting stratum | n | Next Top-10 | Next Top-20 |
|---|---:|---:|---:|
| 21–30 | 115 | 34.78% | 51.30% |
| 31–50 | 145 | 27.59% | 47.59% |
| 51–100 | 210 | 26.67% | 33.81% |
| 101–200 | 200 | 26.50% | 39.00% |
| >200 | 80 | 18.75% | 26.25% |
| previous absent | 4 | 50.00% | 50.00% |

The pattern is not perfectly monotonic, so the diagnosis does not justify simply selecting a wider previous-rank cutoff. It does show that a binary `previous <=20` vs `previous >20` classification discards useful gradation: prior proximity to the retention zone contains information about subsequent persistence.

Current-day rank among these rejected candidates is broadly similar across strata (typically rank 5–7 median/mean range), so current Top-10 strength alone does not solve the distinction.

## 3. Residual churn is mainly confirmed-exit / vacancy-fill clustering

There were `245` transitions with replacement count >=3 (`40.90%`).

Mechanism incidence on those high-churn transitions:

- confirmed-exit sells appear on `85.71%` of high-churn sessions; total `574` sells there;
- qualified vacancy fills appear on `87.35%`; total `579` buys there;
- soft-replacement sells appear on `50.61%`; total `231` sells there;
- universe exits appear on only `4.90%`; total `12` sells there.

Dominant sell driver across the 245 high-churn transitions:

- confirmed exit: `157` transitions;
- soft replacement: `71`;
- confirmed-exit / soft-replacement ties: `10`;
- confirmed-exit / soft-replacement / universe-exit ties: `3`;
- no sell driver: `4`.

Therefore residual churn is primarily the downstream consequence of clustered confirmed exits followed by vacancy fills. Soft replacement remains material but secondary; universe exits are negligible.

This means the next design should not optimize turnover directly first. If exit handling and challenger qualification become better calibrated, much of the residual churn may fall mechanically.

## 4. Blocks 3 and 6 amplify the same mechanism rather than exhibiting a different one

The weakest blocks are characterized by the same two mechanisms at higher intensity:

### Block 3

- exit pending: `288`;
- share current rank >100 among pending: `39.24%`;
- recovery rate: `21.18%`;
- confirmed exits: `220`;
- underfilled sessions: `57`;
- vacancy-days: `144`;
- high-churn >=3 share: `61%`;
- mean replacements: `3.04`.

### Block 6

- exit pending: `255`;
- share current rank >100: `35.29%`;
- recovery rate: `24.90%`;
- confirmed exits: `192`;
- underfilled sessions: `34`;
- vacancy-days: `74`;
- high-churn >=3 share: `56%`;
- mean replacements: `2.89`.

Healthier blocks show lower severe-collapse incidence, higher pending recovery, fewer underfilled sessions, and less churn. No evidence from this diagnosis requires a fold-specific or regime-specific Decision rule.

## 5. Causal synthesis

The frozen V2 failure mechanism is now sufficiently specific:

> Decision V2 Minimal correctly introduced temporal memory, but its evidence states are too binary. Incumbents receive the same one-session grace regardless of deterioration severity, causing a heavy tail of stale holdings after catastrophic rank collapses. Challengers are rejected whenever the previous rank is outside 20 regardless of how close or far outside it was, creating policy-induced underfill. Confirmed-exit clusters then generate most of the residual churn through vacancy-fill chains. Blocks 3 and 6 are not a distinct regime; they are higher-intensity realizations of the same mechanism.

## 6. Architectural implication for the successor Decision

The diagnosis supports a generic **graded evidence-state** successor rather than a V4-X1-specific rescue rule.

Conceptually, the next Decision policy should be able to distinguish:

1. ordinary deterioration vs severe deterioration for incumbents;
2. stronger vs weaker temporal evidence for fresh challengers;
3. vacancy urgency from challenger qualification;
4. incumbent and challenger evidence asymmetrically but without binary all-or-nothing treatment.

The evidence does **not** yet choose exact rank boundaries, emergency-exit threshold, challenger tiers, soft-replacement changes, or any numerical parameter.

## 7. What is not authorized

Do not silently test rank 30/50/100 emergency exits, previous-rank 30/50 entry rules, gap changes, H5/H10 branches, score smoothing, regime-specific exceptions, or any other Decision variation from this result.

Do not access return/PnL or reopen alpha V4-X1/V4-X2 merely because V2 Minimal was rejected.

## 8. Next step

The mechanism diagnosis is sufficient to stop further descriptive forensics for now. The next scientific step is a separately named, preregistered **Decision successor with graded evidence states**, with the smallest model-agnostic mechanism family justified by the findings above. Numerical semantics must be frozen before any structural replay.