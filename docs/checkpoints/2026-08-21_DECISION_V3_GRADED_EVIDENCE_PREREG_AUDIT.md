# Decision V3 Graded Evidence — Adversarial Preregistration Audit

Date: 2026-08-21 Asia/Jakarta

Status: `PREREG_REVIEW_NOT_ACCEPTED_ADDITIONAL_MECHANISM_DIAGNOSIS_REQUIRED`

Reviewed preregistration HEAD: `0a8f9c560039305e7f3ebbdf7546c7ed0937e83b`

This is a pre-implementation adversarial review. No Decision V3 implementation or replay was executed. No alternative threshold/rule simulation, realized returns/PnL, protected/fresh-forward outcomes, provider/network calls, or model refit was used.

## 1. What survives the kill test

The broad successor hypothesis survives:

- temporal memory remains supported by V2 holding/churn improvements;
- incumbent deterioration severity is strongly informative;
- V2 challenger confirmation is too binary;
- block 3/6 do not require regime-specific policy;
- a generic graded evidence-state Decision layer remains architecturally preferable to V4-X1-specific H5/H10 rescue logic.

The audit does **not** recommend reopening alpha V4-X1 or launching V4-X2.

## 2. Kill finding A — severe immediate exit creates a direct churn-feasibility conflict

Frozen V2 churn:

- total replacements: `1,435` over `599` non-bootstrap transitions;
- mean replacements: `2.395659`;
- Gate-B maximum mean: `2.25`.

An integer replacement total must therefore be at most `1,347` to satisfy the frozen mean gate. V3 would need at least `88` fewer replacement-seat changes than V2 before considering any other gate.

From the already-frozen V2 failure diagnosis, among `EXIT_PENDING_1` observations with current rank >50:

- rank 51..100: `255` evaluable; `66` recover to <=20 next session;
- rank 101..200: `237` evaluable; `31` recover;
- rank >200: `91` evaluable; `10` recover.

That is approximately `107` severe-pending cases on the V2 trajectory that V2 did **not** need to exit because they recovered next session, but the proposed V3 rule would classify as immediate `SEVERE_DETERIORATION_EXIT` if the same state were reached.

This is not a valid estimate of exact V3 replacement count because V3 state paths would differ. It is an adversarial feasibility warning: the proposed mechanism introduces an additional mandatory-exit pressure of the same order as, and larger than, the entire `88`-replacement improvement V2 still needed to pass Gate B.

At the same time, V3 retains gap-5 soft replacement unchanged and additionally admits provisional vacancy fills. Therefore the prereg does not yet explain **where the required churn reduction is expected to come from**.

The idea is not logically impossible, because earlier severe exits could change later state paths and reduce later confirmed exits/soft replacements. But the current evidence is insufficient to justify implementation without first measuring the event-level interaction between severe collapses, same-day replacement supply, and existing churn clusters.

## 3. Kill finding B — Tier-B evidence population does not match Tier-B use population

The V2 failure diagnosis showed that all `135` underfilled V2 sessions had enough **rejected fresh Top-10 supply in aggregate** to cover vacancies. The challenger persistence table was then computed for rejected fresh Top-10 rows **on those underfilled sessions**.

The proposed V3 rule uses previous rank 21..50 as `PROVISIONAL_VACANCY_CHALLENGER` on **any session with an existing vacancy**, including:

- vacancies inherited from prior underfill;
- confirmed mild exits;
- universe exits;
- newly created immediate severe exits on sessions that were not underfilled in V2.

Therefore the evidence population used to justify Tier B is narrower than the future use population.

This is a methodological scope mismatch. The audit cannot assume that previous-rank 21..50 persistence measured only on V2-underfilled stress sessions is representative of all current Top-10 fresh challengers that V3 may consume globally.

Before Tier B is frozen, the same outcome-blind alpha-rank diagnosis should be run for **all fresh current Top-10 candidates across the 600 sessions**, stratified by previous-rank history, not only the underfilled subset.

This requires no alternative Decision simulation and no returns/PnL.

## 4. Kill finding C — rank 50 is well supported for incumbent severity, less strongly supported as a global challenger boundary

For incumbent exit-grace severity, the diagnostic evidence is strong and directionally monotonic:

- 21..30 recovery <=20 next session: ~49.7%;
- 31..50: ~36.7%;
- 51..100: ~25.9%;
- 101..200: ~13.1%;
- >200: ~11.0%.

Cases worse than 50 also account for ~90.7% of total V2 pending rank-excess damage. A severity boundary around the preregistered 50 reporting cut is therefore defensible as a development hypothesis for incumbents.

For challengers, the evidence is weaker:

- previous 21..30 -> next Top-20 ~51.3%;
- previous 31..50 -> ~47.6%;
- previous 51..100 -> ~33.8%;
- previous 101..200 -> ~39.0%;
- previous >200 -> ~26.3%.

The broad near-vs-distant gradient exists, but it is not monotonic beyond 50, and it was measured only on the V2-underfilled subset.

Using the **same 50 boundary for both incumbent exit and global challenger admission** is parsimonious, but currently partly a design convenience rather than an equally supported empirical boundary on both sides.

The audit therefore rejects the claim that one common threshold has already been sufficiently justified for both mechanisms.

## 5. Kill finding D — static Tier-B supply does not prove capacity rescue

On V2 underfilled sessions, rejected fresh Top-10 rows with previous rank 21..50 total:

- previous 21..30: `115` rows;
- previous 31..50: `145` rows;
- combined proposed Tier-B supply: `260` rows.

Frozen V2 recorded `307` vacancy-days.

These counts are not directly comparable as a deterministic capacity bound because an admitted candidate may remain held across multiple later sessions and V3 paths would differ. However, they show that the proposed Tier-B subset is materially smaller than the total rejected supply that supported the statement `rejected_supply >= vacancy on 100% of underfilled sessions`.

Therefore the current prereg cannot infer that Tier B will solve the V2 capacity failure. A session-level count of **Tier-A + proposed Tier-B supply versus vacancies** is required before implementation if capacity rescue is part of the mechanism rationale.

## 6. What is NOT a kill finding

The audit did not find a semantic contradiction in:

- Top-10 / Top-20 zones;
- one-session mild deterioration semantics;
- immediate universe exit;
- Tier-A-first vacancy ordering;
- Tier-B vacancy-only restriction;
- unchanged gap-5 soft replacement;
- bootstrap once / no pre-roll / no fold resets;
- unchanged V2 hard acceptance thresholds.

The human and machine-readable prereg contracts are materially aligned on those points.

## 7. Verdict

`PREREG_REVIEW_NOT_ACCEPTED_ADDITIONAL_MECHANISM_DIAGNOSIS_REQUIRED`

The current Decision V3 preregistration should **not be implemented yet**.

The graded-evidence concept survives, but the exact `>50 immediate exit + previous 21..50 provisional vacancy fill` pairing has not survived the adversarial evidence-scope/churn-feasibility review strongly enough to justify freezing executable code.

Do not solve this by changing thresholds now.

## 8. Smallest next diagnosis before revising the prereg

One narrow outcome-blind diagnostic pass is sufficient. It must not simulate Decision V3 or any alternative policy.

### A. Global fresh-Top10 persistence

Across **all** non-held/fresh current Top-10 observations in the exact 600-session alpha rank stream, report by previous-rank strata:

- observation count;
- next-session Top-10 / Top-20 persistence;
- next-session rank distribution;
- previous absence separately;
- six 100-session blocks.

This tests whether the Tier-B proximity evidence generalizes beyond V2-underfilled sessions.

### B. Severe-collapse replacement context

For every V2 `EXIT_PENDING_1` observation with current rank >50, report descriptively on the same session:

- count of current unheld core candidates (previous <=20, current Top10);
- count of current unheld near candidates (previous 21..50, current Top10);
- whether Tier-A supply alone could fill the hypothetical seat;
- whether Tier-A + near supply could fill it;
- whether the event occurs on a V2 high-churn >=3 transition;
- whether the incumbent recovered <=20 next session;
- block attribution.

This does **not** execute an exit or fill. It only measures whether the proposed severe-exit mechanism tends to fire when replacement evidence exists or when it would create extra vacancy/churn pressure.

### C. Session-level underfill supply decomposition

For each of the 135 V2 underfilled sessions, report:

- vacancy count;
- Tier-A available count;
- previous 21..50 fresh Top10 count;
- previous >50 fresh Top10 count;
- previous-absent fresh Top10 count;
- whether Tier-A + 21..50 supply is >= vacancies.

This directly tests the proposed provisional tier without simulating it.

## 9. Boundary after this audit

Until the narrow diagnosis above is frozen:

- no Decision V3 implementation;
- no Decision V3 replay;
- no threshold changes;
- no PnL/return access;
- no H5/H10 rescue;
- no alpha V4-X2 launch.
