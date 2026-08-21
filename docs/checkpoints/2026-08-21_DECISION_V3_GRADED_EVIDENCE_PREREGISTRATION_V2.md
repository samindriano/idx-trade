# Decision V3 Graded Evidence — Preregistration V2

Date: 2026-08-21 Asia/Jakarta

Status: `PREREGISTERED_V2_NOT_IMPLEMENTED_NOT_REPLAYED`

Rule ID: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`

## 1. Scientific lineage

Decision V2 Minimal is frozen as `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`.

The first Decision V3 preregistration was rejected at adversarial review with status:

`PREREG_REVIEW_NOT_ACCEPTED_ADDITIONAL_MECHANISM_DIAGNOSIS_REQUIRED`

The required outcome-blind kill diagnosis then completed once with:

- status: `COMPLETE_OUTCOME_BLIND_DECISION_V3_KILL_DIAGNOSIS`;
- diagnosis manifest SHA-256: `9ab7f282de86556b3c158f7e1c31c8883b38f9108e94ecd8e43a92b9344c8444`;
- V2 structural manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`;
- V2 structural plan digest: `51adba87f6ab714044e5064cd7a1c6c72c7327d0e04acf82ab39ff98f876c3e4`;
- historical source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- historical score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exact source: `600` sessions / `172,697` rows.

The kill diagnosis established:

1. severe V2 pending collapses with current rank `>50` recover to rank `<=20` next session only `18.35%` of the time;
2. at least one current unheld core challenger exists on `87.99%` of severe-collapse observations, and core-or-near supply exists on `95.71%`;
3. global fresh-current-Top10 persistence is graded by previous rank: next-session Top20 persistence is approximately `66.26%` for previous `<=20`, `54.85%` for `21..30`, `50.00%` for `31..50`, `36.10%` for `51..100`, `38.93%` for `101..200`, and `27.64%` for `>200`;
4. previous-absent fresh Top10 has only `n=19`, insufficient to grant an evidence-backed permission tier;
5. after excluding core candidates already consumed by V2, `core + previous 21..50` residual supply covers all remaining vacancies on only `77/135 = 57.04%` of V2-underfilled sessions.

Therefore V3 V1's binary prohibition on every previous-rank `>50` candidate is too restrictive for capacity, but fully admitting weak-evidence candidates to create turnover is not justified.

## 2. Architecture boundary

The reusable pipeline remains:

`Alpha / Ranking -> Decision Policy -> Portfolio / Risk -> Sizing -> Execution`

Decision V3 V2 may consume only:

- current cross-sectional `rank_consensus`;
- immediately previous official-session `rank_consensus`;
- prior Decision shadow membership;
- current eligible-universe presence;
- frozen deterministic profile parameters.

It must not consume:

- H5/H10 identity or head-specific ranks;
- raw score magnitude or margin;
- realized returns or historical/prospective PnL;
- volatility/regime/sector labels;
- liquidity, execution, fill, sizing or capital state;
- protected/fresh-forward outcomes.

## 3. Frozen constants

- target-count ceiling: `10`;
- strong zone: current rank `<=10`;
- acceptable retention zone: current rank `11..20`;
- mild deterioration zone: current rank `21..50`;
- severe deterioration zone: current rank `>50`;
- soft-replacement minimum rank advantage: `5`;
- temporary underfill allowed;
- universe disappearance exits immediately;
- bootstrap first replay session to exact current Top10 once;
- no pre-roll;
- no fold resets.

No alternative severe threshold, challenger boundary, rank gap, or confirmation length may be tested in the same historical replay.

## 4. Incumbent state machine

For a security held at the start of session `t`:

### A. `STRONG_HOLD`

- current rank `<=10`;
- retain;
- not soft-replaceable;
- clear deterioration state.

### B. `ACCEPTABLE_HOLD`

- current rank `11..20`;
- retain by default;
- may be soft-replaced only by Tier A under gap-5;
- clear deterioration state.

### C. `MILD_DETERIORATION_PENDING_1`

- current rank `21..50`;
- immediately previous rank `<=20`;
- retain for this session;
- not soft-replaceable.

If next session returns to rank `<=20`, pending clears.

### D. `CONFIRMED_MILD_DETERIORATION_EXIT`

- current rank `21..50`;
- immediately previous rank `>20`;
- exit immediately before vacancy filling.

### E. `SEVERE_DETERIORATION_EXIT`

- current rank `>50`;
- immediate exit on the first observation, regardless of previous rank;
- no grace;
- remove before vacancy filling.

### F. `UNIVERSE_EXIT`

- incumbent absent from current eligible universe;
- immediate fail-closed exit.

## 5. Challenger evidence tiers

Only non-held **current Top10** names are challengers.

### Tier A — `CORE_CHALLENGER`

Conditions:

- current rank `<=10`;
- present previous session;
- previous rank `<=20`.

Permissions:

- fill any existing vacancy;
- may create a paired soft replacement of an `ACCEPTABLE_HOLD` incumbent under gap-5.

### Tier B — `NEAR_VACANCY_CHALLENGER`

Conditions:

- current rank `<=10`;
- present previous session;
- previous rank `21..50`.

Permissions:

- fill an existing vacancy only;
- never create a vacancy;
- never soft-replace;
- used only after all available Tier-A vacancy candidates are consumed.

### Tier C — `DISTANT_RESIDUAL_VACANCY_CHALLENGER`

Conditions:

- current rank `<=10`;
- present previous session;
- previous rank `>50`.

Permissions:

- fill an **already-existing residual vacancy only**;
- never create a vacancy;
- never soft-replace;
- used only after all available Tier-A and Tier-B vacancy candidates are consumed.

Tier C is intentionally weak permission. It does not claim distant fresh signals are high-confidence; it only distinguishes "weak but observed temporal evidence" from "no temporal evidence" when the portfolio already has an empty seat.

### Tier D — `NO_HISTORY_UNQUALIFIED`

Condition:

- current rank `<=10`;
- absent from the immediately previous eligible universe.

Action:

- cannot enter after bootstrap;
- cannot fill vacancy;
- cannot soft-replace.

Rationale: the kill diagnosis has only `n=19` previous-absent fresh Top10 observations, so V2 does not grant an evidence-backed permission to this state.

## 6. Per-session deterministic order

1. classify all incumbents;
2. execute mandatory `SEVERE_DETERIORATION_EXIT`, `CONFIRMED_MILD_DETERIORATION_EXIT`, and `UNIVERSE_EXIT` sells;
3. retain strong, acceptable, and mild-pending incumbents;
4. identify unheld current-Top10 challengers and classify Tier A/B/C/D;
5. fill existing vacancies from Tier A, ordered current rank then ticker;
6. if vacancies remain, fill from Tier B, ordered current rank then ticker;
7. if vacancies remain, fill from Tier C, ordered current rank then ticker;
8. Tier D is never used;
9. only after vacancy filling, remaining Tier-A challengers may pairwise soft-replace eligible `ACCEPTABLE_HOLD` incumbents under gap-5;
10. if fewer than 10 positions remain because no permitted challenger exists, record `UNFILLED_NO_QUALIFIED_CHALLENGER`.

Tier B/C may fill vacancies inherited from prior underfill or created by a mandatory exit. Neither may manufacture turnover.

## 7. Soft replacement remains unchanged

An `ACCEPTABLE_HOLD` incumbent at rank `11..20` may be soft-replaced only when:

- an unheld Tier-A challenger remains after vacancy filling; and
- `incumbent_rank - challenger_rank >=5`.

Matching is deterministic: best remaining Tier-A challenger by current rank then ticker against the weakest eligible incumbent satisfying gap-5.

No Tier B/C/D challenger may soft-replace.

## 8. Explicit non-features

V3 V2 does not include:

- H5/H10 veto/agreement/weighting;
- raw score thresholds or smoothing;
- rolling/EW ranks;
- minimum hold or cooldown;
- turnover cap;
- current-rank sub-bands inside Top10;
- rank acceleration/delta thresholds;
- sector, volatility, regime or liquidity rules;
- conviction weighting/sizing;
- execution/fill/PnL-aware rules;
- block/fold-specific behavior.

## 9. Frozen replay source

If implementation and independent audit later pass, exactly one structural replay may use:

- manifest SHA-256 `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score SHA-256 `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exactly `600` sessions / `172,697` rows;
- no score regeneration, model refit, provider/network, outcomes, returns or PnL;
- bootstrap exact Top10 once at index 0;
- exact `(t-1,t)` adjacency thereafter;
- continuous state with no fold resets or pre-roll.

Only consensus-ranking inputs required by this contract may be read.

## 10. Required structural metrics

Report at minimum:

### Churn

- total/mean/median/p75/p90/p95/max replacements excluding bootstrap;
- share 0/1/2/>=3 replacements;
- turnover ratio versus frozen naive Top10;
- turnover ratio versus Decision V1 and V2.

### Holding persistence

- completed holding-spell distribution;
- one-session and <=3-session shares;
- right-censored spells.

### Rank quality

- full-target Top10 overlap;
- normalized Top10 overlap all sessions;
- Top20 overlap;
- mean/median target rank;
- mean worst held rank;
- target rows >20 and >50.

### Capacity

- mean/median/min target size;
- share size10, size9, size<=8;
- underfilled sessions and vacancy-days.

### State attribution

- mild pending/recovery counts;
- severe and confirmed-mild exits;
- Tier A/B/C vacancy-fill counts;
- Tier-A soft replacements;
- Tier-D rejections;
- sessions where Tier B prevented underfill;
- sessions where Tier C prevented underfill;
- high-churn mechanism attribution.

### Tier-C risk diagnostics

These are descriptive, not separate tuning gates:

- Tier-C entrant count;
- Tier-C completed holding duration distribution;
- Tier-C one-session holding share;
- Tier-C next-session target state distribution;
- Tier-C entrants that become severe exits on the next available session;
- replacement-seat changes downstream of Tier-C severe exits.

### Stability

- six fixed 100-session blocks;
- fold-boundary transitions descriptive only;
- no reset.

## 11. Frozen hard acceptance gates

All V2 hard thresholds remain unchanged.

### Gate A — correctness / permission integrity

All must pass:

- target size never >10;
- unique target;
- every non-bootstrap entrant is current Top10;
- previous-absent entrant count after bootstrap is zero;
- Tier B used only for an existing vacancy after Tier-A vacancy supply is exhausted;
- Tier C used only for an existing residual vacancy after Tier-A and Tier-B vacancy supply are exhausted;
- Tier B/C never soft-replace or otherwise create a vacancy;
- no incumbent with current rank >50 remains after processing;
- no incumbent remains rank 21..50 for a second consecutive available session;
- first mild-deterioration observation after previous <=20 is retained unless universe disappearance makes rank unavailable;
- soft replacement only Tier A and gap>=5;
- row-order deterministic;
- identical in-memory rerun.

### Gate B — churn

- mean replacements per non-bootstrap transition `<=2.25`;
- turnover versus naive daily Top10 `<=0.50`;
- share transitions with >=3 replacements `<=35%`.

### Gate C — holding persistence

- median completed holding spell `>=3` sessions;
- one-session completed holding share `<=35%`.

### Gate D — rank quality

- mean current Top10 overlap on full targets `>=6.0/10`;
- mean target rank `<=12.0`.

### Gate E — capacity

- mean target size `>=9.0`;
- size10 on `>=70%` sessions;
- size<=8 on `<=10%` sessions.

### Gate F — no hidden stale state

- zero target rows with current rank >50 after processing;
- zero target rows in 21..50 after two consecutive available sessions outside rank20;
- universe disappearance exits immediately.

All gates must pass. Tier-C diagnostics do not create a hidden rescue gate and cannot be used to alter the policy after seeing the replay.

## 12. Verdict

`DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_ACCEPT`

only if every hard gate passes.

Otherwise:

`DECISION_V3_GRADED_EVIDENCE_V2_STRUCTURAL_REJECT`

A reject authorizes no silent modification, threshold sweep, Tier-C restriction/expansion, gap change, H5/H10 rescue, score smoothing, PnL inspection, or alpha retune.

## 13. Scientific interpretation before replay

This preregistration makes three falsifiable claims:

1. severity-aware incumbent exit can remove the V2 stale-rank tail without recreating unacceptable churn;
2. graded vacancy permission A -> B -> C can improve capacity without allowing weak evidence to manufacture turnover;
3. keeping Tier D (previous absent) unqualified preserves a genuine minimum temporal-evidence requirement.

The structural replay exists to falsify these claims. The preregistration does not assert that they will pass.

## 14. Immediate boundary

This document authorizes **no implementation and no replay**.

Next required step: independent adversarial review of this V2 preregistration as a whole. Only an accepted audit may authorize implementation.