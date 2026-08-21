# V4-X1 Decision V1 — 600-OOS Structural Trajectory Result

Date: 2026-08-21 Asia/Jakarta

Status: `COMPLETE_REVIEW_NOT_ACCEPTED_FOR_PROSPECTIVE_SHADOW_DECISION_V2_REQUIRED`

## Source identity

The local outcome-blind structural replay completed against the exact frozen clean V4-X1 historical OOS score artifact:

- source root: `D:\Documents\Project\idx-v4-x1-clean-historical-oos-replay-20260820-v2`
- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`
- source score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`
- score dates: 600
- score rows: 172,697
- clean historical OOS IC carried only as source identity: `0.09805414600339561`
- audit status: `COMPLETE_OUTCOME_BLIND_STRUCTURAL_ONLY`

Hard guards remained false for target/return loading, historical PnL, protected/fresh-forward access, provider/network calls, model fit, retune, and Decision parameter changes.

## Decision V1 frozen rule replayed

- target positions: 10
- Top-10 entry
- hard exit rank >20
- minimum rank-gap replacement: 5
- continuous state across all 600 dates
- no fold reset

## Actual structural result

### Turnover

Excluding the initial 10-name bootstrap:

- Decision V1 replacements: **2,686**
- naive exact daily Top-10 replacements: **3,127**
- Decision / naive turnover ratio: **0.8589702590**
- churn reduction versus naive Top-10: approximately **14.10%**
- mean replacements per session: **4.4841 / 10 names**
- median replacements per session: **4**
- p75: **6**
- p90: **8**
- p95: **8**
- maximum: **10**
- sessions with >=3 replacements: **468 / 599 = 78.13%**
- zero-change sessions: **6 / 599 = 1.00%**
- longest no-change streak: **1 session**

### Holding spells

Across 2,696 holding spells:

- median held sessions: **1**
- p75: **2**
- p90: **4**
- p95: **6**
- mean: **2.23**
- maximum: **43**
- 2,686 completed spells; 10 right-censored at the end.

### Exit causes

2,686 completed sells:

- `HARD_EXIT_RANK_GT20`: **1,978** (~73.64%)
- `RANK_GAP_REPLACEMENT`: **677** (~25.20%)
- `NO_LONGER_IN_V4_X1_DECISION_UNIVERSE`: **31** (~1.15%)

The dominant turnover source is therefore the rank>20 hard-exit boundary, not the rank-gap replacement rule.

### Portfolio rank quality

Despite high churn, the target stays very close to exact current Top-10:

- mean Top-10 overlap: **9.315 / 10**
- median Top-10 overlap: **9 / 10**
- mean retained rank-11–20 names: **0.685 / 10**
- median retained rank-11–20 names: **1**
- mean target rank: **5.669**
- median target mean rank: **5.6**
- mean worst held rank: **11.225**
- median worst held rank: **11**
- maximum worst held rank: **14**
- hard-exit violations: **0**

This means V1 sacrifices very little rank purity but also receives little turnover reduction. It behaves much closer to daily exact Top-10 than intended for a sticky decision policy.

### 100-date block stability

Decision replacements by block were 330, 438, 659, 329, 390, and 540 (first block has 99 post-bootstrap sessions; others 100). Elevated churn appears throughout the historical trajectory rather than only at fold boundaries.

## Review verdict

The audit did not preregister a numerical structural pass/fail threshold, so this is **not a statistical gate failure**.

However, for the intended engineering objective of Decision V1 — convert noisy daily rank changes into a materially more stable target portfolio — the observed mechanics are not accepted:

- median holding period of one session is too short for the intended sticky rank-to-portfolio layer;
- four replacements per day on a ten-name portfolio is excessive;
- 78% of transition days replace at least three names;
- the current hysteresis reduces naive Top-10 churn by only ~14%;
- >73% of exits are forced by the hard rank>20 boundary;
- portfolio membership remains ~93% current Top-10 on average.

Therefore:

`DECISION_V1_STRUCTURAL_REVIEW_NOT_ACCEPTED_FOR_PROSPECTIVE_SHADOW`

Do **not** deploy Decision V1 as the prospective Decision Shadow yet.

## Next scientific action

Open **Decision V2** as a separately named/preregistered mechanical-policy challenger. Do not mutate V1.

Decision V2 design should address the observed failure mode without using historical return/PnL for parameter selection. Candidate structural families may include:

1. wider retention / hard-exit bands;
2. persistence confirmation before ordinary exits, with a separately defined emergency exit band;
3. stronger replacement hysteresis;
4. rank/score smoothing or stateful confirmation at the Decision layer;
5. combinations of the above evaluated first on outcome-blind structural diagnostics.

Merely increasing the rank-gap threshold is unlikely to solve the dominant problem because 73.6% of V1 sells are hard exits rather than rank-gap replacements.

Any later performance/PnL comparison requires a separately authorized gate and must not be used to retroactively call V1 mechanically acceptable.
