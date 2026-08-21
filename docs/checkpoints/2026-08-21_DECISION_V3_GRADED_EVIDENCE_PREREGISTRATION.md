# Decision V3 Graded Evidence — Preregistration

Date: 2026-08-21 Asia/Jakarta

Status: `PREREGISTERED_NOT_IMPLEMENTED_NOT_REPLAYED`

## 1. Scientific purpose

Decision V2 Minimal is frozen as `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`.

The subsequent outcome-blind failure-mechanism diagnosis is frozen as:

- status: `COMPLETE_OUTCOME_BLIND_DECISION_V2_FAILURE_MECHANISM_DIAGNOSIS`;
- structural manifest SHA-256: `a555368181dff5084be342dbf13b79993252767ae7e00804f7601477b29995ba`;
- diagnosis manifest SHA-256: `bada04d8403457d4456653fad66d9119b80349f65e13be9cff911a886c31af06`;
- historical score manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- historical score SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exact source: `600` sessions / `172,697` score rows.

The diagnosis established four findings without using realized returns/PnL or alternative Decision simulations:

1. incumbent recovery probability declines strongly with deterioration severity;
2. V2 underfill was policy-created because every underfilled session still had enough current Top-10 rejected-fresh supply to cover vacancies;
3. residual churn is dominated by clustered confirmed exits followed by vacancy fills rather than universe exits;
4. weak blocks 3 and 6 amplify the same mechanism rather than requiring a regime-specific rule.

Decision V3 is therefore a **generic graded evidence-state successor**. It does not reopen alpha V4-X1 and does not use V4-X1-specific H5/H10 internals.

## 2. Architecture boundary

The reusable pipeline remains:

`Alpha / Ranking -> Decision Policy -> Portfolio / Risk -> Sizing -> Execution`

Decision V3 may consume only:

- current cross-sectional `rank_consensus`;
- immediately previous official-session `rank_consensus`;
- prior Decision shadow membership;
- current eligible-universe presence;
- the frozen Decision V3 profile.

Decision V3 must not consume:

- H5/H10 head identity or head-specific ranks;
- raw alpha score magnitude or score margin;
- realized returns;
- historical or prospective PnL;
- volatility or regime labels;
- sector data;
- liquidity or execution state;
- sizing/capital/fill state;
- protected or fresh-forward outcomes.

The generic engine must know only rank/evidence states and deterministic profile parameters. V4-X1 is only the first frozen alpha profile plugged into that engine.

## 3. Frozen Decision V3 profile

Rule ID: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V1`

Frozen constants:

- target-count ceiling: `10`;
- strong zone: current rank `<=10`;
- acceptable retention zone: current rank `11..20`;
- mild deterioration zone: current rank `21..50`;
- severe deterioration zone: current rank `>50`;
- core challenger: current rank `<=10` and previous rank `<=20`;
- provisional vacancy challenger: current rank `<=10` and previous rank `21..50`;
- distant/absent fresh challenger: current rank `<=10` and previous rank `>50` or absent;
- soft-replacement minimum rank advantage: `5`;
- temporary underfill allowed;
- universe disappearance exits immediately;
- bootstrap first replay session to exact current Top-10 once;
- no pre-roll;
- no fold resets.

### Why rank 50 is frozen here

The failure diagnosis preregistered rank strata as descriptive reporting bins and then showed a large deterioration gradient:

- current `21..30`: next-session recovery to <=20 approximately `49.7%`;
- `31..50`: approximately `36.7%`;
- `51..100`: approximately `25.9%`;
- `101..200`: approximately `13.1%`;
- `>200`: approximately `11.0%`.

Observations worse than rank 50 account for approximately `90.7%` of total rank-excess damage beyond 20 in V2 pending holdings.

For rejected fresh Top-10 challengers, prior `21..30` and `31..50` also had materially stronger next-session Top-20 persistence than more distant histories as a broad class.

The boundary at `50` is therefore frozen **once** as the smallest common severity/proximity boundary supported by the preregistered diagnostic strata. It is not a sweep candidate. No 30/40/60/100 alternative may be evaluated in the same replay.

## 4. Historical bootstrap and state continuity

Historical structural replay, if later authorized, must:

1. begin from empty Decision state on the first of the exact 600 frozen OOS dates;
2. use one bootstrap exception: exact current Top-10 on the first date;
3. use no pre-roll;
4. carry Decision state continuously through all 600 sessions;
5. never reset at fold boundaries;
6. verify that previous-session input is exactly session `t-1` from the pinned 600-session ledger.

After bootstrap, every entrant must satisfy one of the challenger states below.

## 5. Incumbent state machine

For a security held at the start of session `t`:

### A. `STRONG_HOLD`

Condition:

- current rank `<=10`.

Action:

- retain;
- not soft-replaceable;
- clear any deterioration state.

### B. `ACCEPTABLE_HOLD`

Condition:

- current rank `11..20`.

Action:

- retain by default;
- clear any deterioration state;
- may be soft-replaced only by a **core challenger** under the frozen gap-5 rule.

### C. `MILD_DETERIORATION_PENDING_1`

Condition:

- current rank `21..50`;
- immediately previous-session rank `<=20`.

Action:

- retain for this session;
- not soft-replaceable;
- this is the only one-session grace state.

If next session returns to rank `<=20`, the pending state clears.

### D. `CONFIRMED_MILD_DETERIORATION_EXIT`

Condition:

- current rank `21..50`;
- immediately previous-session rank `>20`.

Action:

- exit now;
- remove before vacancy filling.

Thus mild deterioration still receives at most one consecutive available-session grace observation.

### E. `SEVERE_DETERIORATION_EXIT`

Condition:

- current rank `>50`.

Action:

- immediate exit on this observation regardless of previous rank;
- no one-session grace;
- remove before vacancy filling.

This is severity-aware deterioration handling. It does not depend on H5/H10 or score magnitude.

### F. `UNIVERSE_EXIT`

Condition:

- incumbent absent from current eligible universe.

Action:

- immediate exit;
- no grace;
- remove before vacancy filling.

## 6. Challenger evidence states

Only **current Top-10** non-held names may be challengers.

### Tier A — `CORE_QUALIFIED_CHALLENGER`

Conditions:

- current rank `<=10`;
- present previous session;
- previous rank `<=20`.

Permissions:

- may fill any open vacancy;
- may trigger soft replacement of an `ACCEPTABLE_HOLD` incumbent if rank advantage is at least 5.

### Tier B — `PROVISIONAL_VACANCY_CHALLENGER`

Conditions:

- current rank `<=10`;
- present previous session;
- previous rank `21..50`.

Permissions:

- may fill an existing open vacancy only;
- may not create a vacancy;
- may not trigger soft replacement;
- may be used only after all available Tier-A challengers have been consumed for vacancy filling.

This is the key graded-entry change. A near-history fresh Top-10 name is not treated as equivalent to either a fully confirmed challenger or a distant one-day spike.

### Tier C — unqualified distant/absent fresh challenger

Conditions:

- current rank `<=10`; and either
  - previous rank `>50`, or
  - absent from the previous eligible universe.

Action:

- cannot enter this session;
- cannot trigger soft replacement;
- does not block temporary underfill if Tier A/B supply is insufficient.

## 7. Exit and vacancy filling remain separate questions

Decision V3 preserves the architecture lesson that exit urgency and replacement qualification are distinct.

Order per session:

1. classify incumbents;
2. execute mandatory removals from `SEVERE_DETERIORATION_EXIT`, `CONFIRMED_MILD_DETERIORATION_EXIT`, and `UNIVERSE_EXIT`;
3. retain strong, acceptable, and mild-pending incumbents;
4. identify current Top-10 challenger tiers;
5. fill existing vacancies first with Tier A, then Tier B, each ordered by current rank then ticker;
6. after vacancy filling, Tier A only may soft-replace eligible `ACCEPTABLE_HOLD` incumbents under gap-5;
7. Tier B never triggers soft replacement;
8. if fewer than 10 names remain after all permitted fills, temporary underfill is explicit as `UNFILLED_NO_QUALIFIED_CHALLENGER`.

A vacancy may come from a mandatory exit or may already exist from prior underfill. Tier B is allowed in either case because it fills an existing vacancy rather than manufacturing turnover.

## 8. Soft replacement remains unchanged

The V2 gap-5 mechanism is not being retuned.

An `ACCEPTABLE_HOLD` incumbent at rank `11..20` may be soft-replaced only when:

1. an unheld Tier-A `CORE_QUALIFIED_CHALLENGER` exists;
2. `incumbent_rank - challenger_rank >= 5`.

Restrictions:

- `STRONG_HOLD` cannot be soft-replaced;
- `MILD_DETERIORATION_PENDING_1` cannot be soft-replaced;
- Tier-B provisional challengers cannot soft-replace;
- deterministic matching is best challenger rank then ticker against the weakest eligible incumbent satisfying gap-5.

## 9. Explicit non-features

Decision V3 does **not** include:

- H5 veto or H10 veto;
- H5/H10 agreement;
- raw-score thresholds;
- score smoothing;
- rolling rank average / EW rank;
- minimum holding period;
- cooldown period;
- turnover cap;
- rank-change or acceleration thresholds;
- sector constraints;
- volatility/regime state;
- liquidity or execution constraints;
- conviction weighting;
- sizing or cash allocation;
- PnL/return-aware rules;
- fold-specific or block-specific behavior.

Any such addition requires a separate successor preregistration.

## 10. Frozen replay source contract

If implementation later passes independent review, Decision V3 may be structurally replayed exactly once on the same frozen 600-session source:

- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score parquet SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exact sessions: `600`;
- exact rows: `172,697`;
- no score regeneration;
- no model refit;
- no provider/network calls;
- no target/outcome ledger access;
- no realized return/PnL access;
- no protected/fresh-forward access.

Only rank columns required by the Decision contract may be read.

## 11. Required structural metrics

The V3 replay must report at least the same metrics as V2 for direct comparison:

### Turnover / churn

- total replacements excluding bootstrap;
- mean / median / p75 / p90 / p95 / max replacements;
- share transitions with 0 / 1 / 2 / >=3 replacements;
- turnover ratio versus frozen naive daily Top-10;
- turnover ratio versus frozen Decision V1;
- turnover ratio versus frozen Decision V2.

### Holding persistence

- completed holding spell count;
- mean / median / p75 / p90 / p95 / max duration;
- one-session share;
- <=3-session share;
- right-censored spell count.

### Rank quality

- mean Top-10 overlap on full targets;
- normalized Top-10 overlap on all sessions;
- mean Top-20 overlap;
- mean / median target rank;
- mean worst held rank;
- count/distribution of target rows with rank >20;
- count/distribution of target rows with rank >50.

### Capacity

- mean / median / minimum target size;
- share size 10;
- share size 9;
- share size <=8;
- underfilled sessions;
- vacancy-days.

### State attribution

- mild-pending observations and next-session recoveries;
- severe-deterioration immediate exits;
- confirmed mild-deterioration exits;
- universe exits;
- Tier-A vacancy fills;
- Tier-B vacancy fills;
- Tier-A soft replacements;
- Tier-C fresh Top-10 rejections;
- sessions where Tier B prevented underfill;
- high-churn mechanism attribution.

### Time stability

- six fixed 100-session blocks;
- fold-boundary transitions reported descriptively;
- no reset at boundaries.

## 12. Frozen hard acceptance gates

**The V2 structural acceptance thresholds are retained unchanged.** Decision V3 does not get easier gates because V2 failed.

### Gate A — correctness and determinism

All must hold:

- no target size >10;
- no duplicate target;
- no non-bootstrap entrant outside current Top-10;
- no entrant with previous rank >50 or previous absence;
- Tier-B entrant occurs only as a vacancy fill, never as soft replacement;
- Tier-A/Tier-B vacancy priority is deterministic and Tier A is exhausted before Tier B is used;
- no incumbent with current rank >50 remains in target;
- no incumbent remains in rank 21..50 for a second consecutive available session;
- no first mild deterioration observation (21..50 after previous <=20) is sold except universe disappearance, which by definition cannot coexist with a current rank;
- no soft replacement unless challenger is Tier A and rank gap >=5;
- identical replay under row-order permutation;
- identical replay on exact rerun/in-memory determinism pass.

### Gate B — churn reduction

- mean replacements per non-bootstrap transition `<=2.25`;
- turnover ratio versus naive daily Top-10 `<=0.50`;
- share transitions with >=3 replacements `<=35%`.

### Gate C — holding persistence

- median completed holding spell `>=3` sessions;
- one-session completed holding share `<=35%`.

### Gate D — rank quality preservation

- mean current Top-10 overlap on full targets `>=6.0/10`;
- mean target rank `<=12.0`.

### Gate E — capacity

- mean target size `>=9.0`;
- target size 10 on `>=70%` of sessions;
- target size <=8 on `<=10%` of sessions.

### Gate F — no hidden stale state

- zero target rows with current rank >50 after Decision processing;
- zero target rows in rank 21..50 after two consecutive available sessions outside rank 20;
- universe disappearance fails closed immediately.

All gates must pass.

## 13. Verdict semantics

### `DECISION_V3_GRADED_EVIDENCE_STRUCTURAL_ACCEPT`

Only if every hard gate passes.

Next action would be to freeze the exact V3 implementation/profile and prepare a prospective outcome-blind Decision shadow. Historical PnL is not required for this structural acceptance.

### `DECISION_V3_GRADED_EVIDENCE_STRUCTURAL_REJECT`

If any hard gate fails.

A reject does not authorize silent changes to rank 50, Top10/Top20, gap-5, challenger tiers, confirmation length, or any other policy parameter.

Any next attempt must be separately named and preregistered.

## 14. Forbidden until structural verdict

Do not inspect or use:

- realized H5/H10 returns;
- historical portfolio PnL;
- protected/fresh-forward outcomes;
- fills/fees/slippage for Decision selection;
- model refit or feature changes;
- alternative severe-exit thresholds;
- alternative provisional-entry thresholds;
- alternative rank gaps;
- same-run rescue variants;
- parameter sweeps.

## 15. Immediate next step

This preregistration itself authorizes **no replay**.

The next step is:

1. independently review this preregistration for ambiguity and accidental degrees of freedom;
2. implement a generic Decision V3 engine/profile exactly as written on a separate implementation branch;
3. add adversarial/property tests;
4. independently diff implementation against this frozen preregistration;
5. only then prepare a guarded one-shot structural replay runner.
