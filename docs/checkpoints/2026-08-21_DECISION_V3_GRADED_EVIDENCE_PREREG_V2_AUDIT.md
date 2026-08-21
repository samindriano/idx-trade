# Decision V3 Graded Evidence V2 — Adversarial Preregistration Audit

Date: 2026-08-21 Asia/Jakarta

Status: `PREREG_V2_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`

Reviewed preregistration HEAD: `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`

Reviewed rule ID: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`

This review attempts to falsify the entire revised mechanism before implementation. No Decision V3 code or replay was executed. No alternative threshold/rule simulation, parameter sweep, realized returns/PnL, protected/fresh-forward outcome, H5/H10 Decision internal, provider/network call, or model refit was used.

## 1. Verdict summary

The revised preregistration **survives the pre-implementation kill test**, but only as a high-risk structural hypothesis.

Implementation is authorized because the previous audit's evidence-scope blockers have been resolved and the new Tier-C permission is deliberately restricted to an already-empty seat. Historical replay remains unauthorized until implementation and runner audits are complete.

This is not a prediction that V3 V2 will pass the structural gates. The churn gate remains particularly difficult.

## 2. What changed from rejected prereg V1

Only one material permission changed:

- previous-rank `>50`, current-Top10, previously observed challengers move from completely forbidden to **Tier C residual-vacancy-only**.

Tier C:

- cannot create a vacancy;
- cannot soft-replace;
- is used only after Tier A and B vacancy supply is exhausted.

Previous-absent current-Top10 names remain unqualified after bootstrap.

No numeric threshold was added beyond the already proposed rank-50 boundary. Top10, Top20, gap-5, target10, incumbent severity states, bootstrap, adjacency, source contract and all hard acceptance thresholds remain unchanged.

## 3. Kill attack A — Tier C can create a delayed churn loop

Global fresh-Top10 next-session Top20 persistence is weak for distant previous ranks:

- previous 51..100: `36.10%`;
- previous 101..200: `38.93%`;
- previous >200: `27.64%`.

Therefore Tier C can plausibly produce this chain:

`existing vacancy -> distant fresh Top10 fill -> rapid deterioration -> severe exit -> new vacancy -> another fill`

The fact that Tier C does not manufacture a vacancy **on entry day** does not mean it is turnover-neutral across time.

This is the strongest surviving attack on the design.

### Why it does not kill prereg V2 before implementation

The prereg does not hide this risk. It requires Tier-C-specific holding duration, one-session spell, next-state, next severe-exit and downstream replacement diagnostics. More importantly, the unchanged hard gates directly reject the policy if this loop becomes material:

- Gate B rejects excessive replacement/churn;
- Gate C rejects excessive one-session holdings;
- Gate D rejects poor rank quality.

Adding a Tier-C-specific cooldown, minimum hold, confirmation, current-rank cutoff, or custom exit rule now would add an unvalidated degree of freedom and would weaken the scientific test.

Verdict on attack A: **survives for one exact structural test; high failure risk remains**.

## 4. Kill attack B — weak entrant permission escalates after entry

Once a Tier-C candidate fills a vacancy, it becomes an ordinary incumbent on the next session. It can therefore receive the same mild-deterioration grace as any other incumbent if it moves from current Top10 to rank 21..50.

This means the evidence tier affects **entry permission**, but is not retained as a permanent label controlling future holding logic.

An adversarial alternative would make Tier-C-origin positions easier to exit. The audit rejects adding that rule now because:

1. the diagnosis did not preregister or evaluate entry-tier-dependent incumbent persistence;
2. it would add another state variable and another policy branch;
3. it would make the supposedly generic Decision layer more path-dependent;
4. rank-quality and churn gates already test whether ordinary incumbent treatment is adequate.

Verdict on attack B: **real risk, but simpler state erasure after entry is the cleaner falsifiable design**.

## 5. Kill attack C — severe immediate exit may intensify already-busy sessions

Among the `583` V2 severe pending observations with current rank >50:

- `45.11%` occur on transitions where V2 already has >=3 replacements;
- only `18.35%` recover to rank <=20 next session;
- `87.99%` have at least one same-session unheld core challenger;
- `95.71%` have at least one core-or-near challenger.

The first fact is adverse: immediate severe exits may shift more activity onto high-churn days.

The remaining evidence is favorable enough to justify testing the hypothesis once: severe collapses usually do not recover immediately, and replacement evidence is usually present.

The audit does **not** infer that replacement availability reduces churn; it only removes the earlier concern that severe exit routinely creates an unfillable seat.

Gate B remains unchanged and must kill V3 if churn is excessive.

Verdict on attack C: **survives, but no churn-pass presumption**.

## 6. Kill attack D — Tier C makes the capacity gate easier

Allowing every previously observed current-Top10 challenger to fill a residual vacancy after A/B means capacity will mechanically improve on many sessions. Therefore Gate E becomes less discriminative than it was under V2.

This is not evidence that Tier-C names are high quality.

The design remains acceptable because:

- Tier C is not allowed to displace any incumbent;
- previous-absent names remain forbidden, so full capacity is not tautologically guaranteed;
- rank quality remains constrained by Gate D;
- churn and holding persistence remain constrained by Gates B/C;
- Tier-C-specific diagnostics expose whether capacity is being bought through unstable one-day names.

The replay result must not describe a Gate-E pass alone as scientific success.

Verdict on attack D: **not fatal; capacity must be interpreted jointly with churn/rank gates**.

## 7. Kill attack E — rank 50 could be a post-hoc development threshold

Rank 50 was chosen after observing V2 failure diagnostics. Therefore it is a **development-time hypothesis**, not untouched holdout evidence.

This is acceptable only under the following discipline, which prereg V2 satisfies:

- no historical V3 trajectory has yet been run;
- no 30/40/60/100 sweep is allowed;
- the threshold is frozen before implementation/replay;
- exactly one structural replay will later issue ACCEPT/REJECT;
- a reject cannot silently modify 50.

The global kill diagnosis strengthens the coarse 50 boundary for challengers: next Top20 persistence drops from `50.00%` for previous 31..50 to `36.10%` for 51..100, while more-distant strata remain weak as a broad class.

Non-monotonicity between 51..100 and 101..200 argues **against** adding more distant-rank sub-bands, not against the coarse near/distant split.

Verdict on attack E: **scientifically acceptable as one preregistered development hypothesis, not as an optimized threshold**.

## 8. Kill attack F — previous-absent candidates could rescue remaining underfill

Previous-absent current-Top10 observations have only `n=19` globally. Their observed next Top20 rate is not enough to establish a stable evidence class.

Admitting them merely to make capacity look better would be goal chasing.

Keeping Tier D forbidden is therefore an important restraint. If V3 V2 fails capacity because of this choice, the result must be accepted as a reject rather than repaired in the same run.

Verdict on attack F: **design choice survives and improves scientific discipline**.

## 9. Kill attack G — policy complexity / overfitting

V2 already used numeric concepts 10, 20 and gap-5. V3 V2 adds one new numeric boundary, 50, and converts challenger eligibility from binary to three ordered permission levels plus no-history denial.

It does **not** add:

- head-specific logic;
- score magnitude;
- regime or block logic;
- smoothing;
- turnover caps;
- current-Top10 sub-thresholds;
- tier-specific sizing;
- tier-specific exit thresholds.

The audit therefore considers complexity still bounded enough for a generic Decision layer.

Adding any of the above before the first V3 V2 structural verdict would cross the line into mechanism proliferation.

Verdict on attack G: **survives**.

## 10. Kill attack H — unchanged soft replacement remains a possible churn source

V2 diagnosis showed soft replacement is secondary but material on high-churn transitions. V3 V2 deliberately leaves gap-5 unchanged.

This means the replay may fail because the combination of severity exits plus the old soft-replacement path is still too active.

The audit considers keeping it unchanged preferable to retuning it simultaneously, because otherwise a V3 result would not isolate whether graded evidence solved the diagnosed failures.

If churn fails, no same-run gap adjustment is allowed.

Verdict on attack H: **known unresolved risk, correctly isolated rather than tuned away**.

## 11. Contract audit

Human preregistration and machine profile are materially aligned on:

- rule ID;
- target10 / Top10 / Top20 / rank50 / gap5;
- incumbent states;
- Tier A/B/C/D definitions;
- A -> B -> C vacancy priority;
- Tier B/C no-soft-replacement semantics;
- Tier D previous-absent prohibition;
- immediate universe exit;
- bootstrap once / no pre-roll / no fold resets;
- frozen source hashes and row/session counts;
- unchanged structural gate thresholds;
- exact ACCEPT/REJECT strings.

Implementation must pin the prereg/profile identity and fail closed on mismatch before any replay is authorized.

## 12. Why the idea survives overall

The revised design has a coherent generic interpretation:

> evidence quality controls **what a challenger is allowed to do**, rather than simply deciding whether the challenger exists.

- Tier A has enough temporal evidence to fill vacancies and challenge incumbents.
- Tier B has moderate evidence and may fill but cannot create turnover.
- Tier C has weak but nonzero temporal evidence and may only prevent an already-existing seat from staying empty after stronger evidence is exhausted.
- Tier D has no previous-session evidence and remains blocked.

This is materially different from V2's binary confirmation while remaining model-neutral.

## 13. Audit verdict

`PREREG_V2_REVIEW_ACCEPTED_IMPLEMENTATION_ONLY_REPLAY_NOT_AUTHORIZED`

The preregistration is sufficiently explicit and evidence-scoped to implement exactly once.

This verdict does **not** authorize historical replay.

## 14. Next authorization

Allowed next work:

1. implement a generic Decision V3 graded-evidence state machine and V4-X1 profile exactly as preregistered;
2. add adversarial/property tests for every permission boundary and ordering rule;
3. independently diff implementation against both the human prereg and machine profile;
4. only after implementation audit acceptance, prepare a guarded one-shot structural replay runner.

Not authorized:

- changing rank 50, Top10/Top20 or gap-5;
- adding Tier-C-specific hold/exit rules;
- admitting previous-absent candidates;
- adding H5/H10, score magnitude, regime or smoothing rules;
- running V3 historical structural replay;
- inspecting returns/PnL or protected outcomes;
- alpha V4-X2 work.