# Decision V2 Minimal — Preregistration

Date: 2026-08-21 Asia/Jakarta

Status: `PREREGISTERED_NOT_IMPLEMENTED_NOT_REPLAYED`

Branch: `research/idx-decision-v2-minimal-prereg-v1`

## 0. Purpose

This document freezes one minimal Decision V2 hypothesis before implementation or structural replay.

Decision V2 is **not** a bespoke rescue system for V4-X1. It is a reusable stateful rank-to-target policy whose first calibration profile is V4-X1.

The core question is:

> Given a useful but temporally noisy cross-sectional alpha stream, can a small amount of generic temporal evidence prevent the Decision layer from amplifying one-day rank noise into portfolio churn?

The preregistration is informed only by the completed outcome-blind Decision V1 diagnostics. No realized return, PnL, protected/fresh-forward outcome, model refit, alpha retune, or Decision V2 replay result has been inspected.

---

# 1. Controlling evidence before this preregistration

Decision V1 implementation was correct but longitudinally unacceptable on the exact frozen 600-OOS V4-X1 score path:

- 2,686 replacements excluding initial bootstrap;
- mean replacements/session ≈ `4.4841`;
- median replacements/session = `4`;
- >=3 replacements on `78.13%` of transitions;
- median completed holding spell = `1` session;
- only ~`14.1%` churn reduction versus naive exact daily Top-10;
- `1,978 / 2,686` completed sells were hard exits above rank 20.

The rank-dynamics and temporal-persistence diagnoses found:

- exact Top-10 next-session survival ≈ `47.98%`;
- fresh Top-10 names arriving from prior rank >20/absence fall back >20 next session ≈ `54.80%` of the time;
- prior-Top-10/current-Top-10 names fall >20 next session ≈ `20.67%`;
- Top-10 runs of at least 3 sessions fall >20 next session ≈ `15.17%`;
- strict persistence filters materially improve durability but can leave fewer than 10 candidates;
- H5/H10 disagreement worsens durability but is not the primary root cause;
- modestly widening the rank-20 boundary is not supported as the root fix;
- hard-exit followed by automatic replacement creates a churn feedback loop.

These findings motivate temporal confirmation and decoupled replacement, not alpha-specific head rules.

Architectural lessons are recorded separately in:

`docs/checkpoints/2026-08-21_DECISION_V1_FAILURE_MODES_AND_MODULAR_DESIGN_PRINCIPLES.md`

---

# 2. Separation of generic engine and alpha profile

Decision V2 has two conceptual layers.

## 2.1 Generic Decision engine

The engine understands only:

- current cross-sectional rank;
- immediately previous-session cross-sectional rank;
- current target membership;
- whether a security is present in the current eligible universe;
- deterministic policy parameters supplied by an alpha profile.

The generic engine does **not** know:

- model family;
- model features;
- H5/H10 semantics;
- raw prediction scale;
- return labels;
- realized performance;
- volatility regime;
- PnL;
- execution/fill state.

## 2.2 V4-X1 Decision profile V1

The first profile supplies only rank-band and confirmation constants:

- target count: `10`;
- strong / entry zone: rank `<=10`;
- acceptable / retention zone: rank `<=20`;
- soft replacement minimum rank advantage: `5` ranks;
- entry temporal confirmation: candidate must also have previous-session rank `<=20`;
- exit temporal confirmation: incumbent must be rank `>20` on `2` consecutive available sessions;
- universe disappearance: immediate exit, no temporal grace;
- no alpha-head-specific logic.

The numeric rank bands and gap reuse the already-frozen V1 values rather than introducing a threshold sweep.

---

# 3. Exact Decision V2 Minimal semantics

## 3.1 Inputs per session

For each official score session `t`, the Decision engine receives:

1. verified current score/rank table for `t`;
2. verified immediately previous official score/rank table for `t-1`, except at bootstrap;
3. prior Decision target state;
4. deterministic V4-X1 Decision profile V1.

Only `rank_consensus` is used for V2 Minimal decisions.

No H5/H10 fields are decision inputs in this preregistered V2.

## 3.2 Deterministic ranking identity

Ranks are deterministic using the existing frozen alpha ordering/tie semantics. Any exact tie behavior must remain identical to the existing verified V4-X1 score contract.

No new score transformation, smoothing, averaging, or normalization is allowed.

## 3.3 Bootstrap

Historical replay begins exactly once from empty/all-cash Decision state on the first of the exact 600 OOS dates, with no pre-roll.

Because no previous score session is available inside the frozen replay boundary, bootstrap is a one-time exception:

- initialize with the current exact Top-10 on the first replay date;
- mark these as bootstrap holdings;
- from the second replay date onward, all normal V2 confirmation rules apply.

No later reset or fold-boundary bootstrap is permitted.

## 3.4 Qualified challenger / entry rule

A non-held security is a `QUALIFIED_CHALLENGER` on session `t` only if:

1. current rank `<=10`; and
2. the security was present on `t-1`; and
3. previous-session rank `<=20`.

Therefore a fresh jump from prior rank `>20` or prior absence directly into current Top-10 is **not** immediately qualified to take a portfolio seat.

No 2-day/3-day hard persistence requirement is used in V2 Minimal.

## 3.5 Incumbent state

For each currently held security:

### A. Current rank `<=10`

State: `STRONG_HOLD`.

- retain;
- not soft-replaceable;
- any prior exit-pending state is cleared.

### B. Current rank `11..20`

State: `ACCEPTABLE_HOLD`.

- retain by default;
- any prior exit-pending state is cleared;
- may be soft-replaced only under the exact rule in section 3.7.

### C. Current rank `>20`, but previous-session rank `<=20`

State: `EXIT_PENDING_1`.

- retain for this session;
- do not soft-replace;
- do not emit sell intent merely from this first outside-retention observation.

### D. Current rank `>20` and previous-session rank `>20`

State: `CONFIRMED_EXIT`.

- emit sell/exit intent;
- remove from target state for the current Decision output before vacancy filling.

### E. Absent from current eligible Decision universe

State: `UNIVERSE_EXIT`.

- immediate sell/exit intent;
- no one-session grace;
- remove before vacancy filling.

## 3.6 Recovery from exit pending

If an `EXIT_PENDING_1` incumbent returns to rank `<=20` on the next session:

- the pending deterioration is cleared;
- the holding is treated normally as `STRONG_HOLD` or `ACCEPTABLE_HOLD` according to current rank.

No minimum holding period is created.

## 3.7 Soft replacement rule

The existing V1 rank-gap concept is retained, but challenger quality is strengthened.

A held `ACCEPTABLE_HOLD` at current rank `11..20` may be replaced only when:

1. there exists an unheld `QUALIFIED_CHALLENGER` in current Top-10; and
2. `incumbent_rank - challenger_rank >= 5`.

Additional restrictions:

- `STRONG_HOLD` is never soft-replaced;
- `EXIT_PENDING_1` is never soft-replaced;
- only qualified challengers may trigger soft replacement;
- multiple replacements are resolved deterministically by best challenger rank, then ticker tie-break, against the weakest eligible incumbent that satisfies the gap rule.

The rank-gap threshold remains `5`; it is not re-optimized.

## 3.8 Confirmed exit and vacancy filling are separate decisions

After all `CONFIRMED_EXIT` and `UNIVERSE_EXIT` removals, vacancies are filled only from currently unheld `QUALIFIED_CHALLENGER` names, ordered deterministically by current rank then ticker.

If fewer qualified challengers exist than vacancies:

- do **not** backfill with fresh/unconfirmed Top-10 names;
- allow the Decision target to remain temporarily underfilled;
- record explicit `UNFILLED_NO_QUALIFIED_CHALLENGER` capacity state.

This underfill is mechanical, not a market-timing overlay.

The downstream sizing/execution layer is not part of this preregistration.

## 3.9 Maximum target size

The target may contain `0..10` names, with `10` as the desired capacity ceiling.

No action may create more than 10 target names.

## 3.10 No forced daily rebalance

If none of the above state transitions fires, target membership remains unchanged even if exact daily Top-10 identity changes.

---

# 4. Why these changes are considered generic rather than V4-X1-specific

V2 Minimal introduces three generic ideas only:

1. **entry confirmation** — a fresh rank spike does not immediately earn a seat;
2. **exit confirmation** — one adverse rank observation does not automatically terminate an incumbent;
3. **qualified replacement** — the need to remove a name does not prove that today's newest Top-10 name is ready to replace it.

These mechanisms require only rank history and incumbent/challenger state. They do not encode V4-X1 head structure or model internals.

---

# 5. Explicit non-features of V2 Minimal

The following are intentionally excluded:

- H5 veto;
- H10 veto;
- H5/H10 agreement requirement;
- H5/H10 reweighting;
- raw-score thresholds;
- score-margin thresholds;
- rolling score smoothing;
- rolling rank average;
- exponentially weighted rank;
- minimum holding period;
- fixed post-exit cooldown;
- turnover cap;
- sector constraints;
- volatility/regime logic;
- liquidity logic;
- conviction weighting;
- sizing logic;
- execution logic;
- PnL-aware decisions;
- return-aware decisions.

Any such addition requires a separately named preregistration after V2 Minimal is evaluated.

---

# 6. Historical structural replay contract

After implementation/tests are independently reviewed, V2 Minimal may be replayed exactly once on the same pinned 600-OOS historical score path used for Decision V1 diagnostics.

Pinned source identity must remain:

- source manifest SHA-256: `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score parquet SHA-256: `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- score dates: `600`;
- score rows: `172,697`.

Historical state semantics:

- exact first date bootstrap once;
- continuous state across all 600 sessions;
- no fold reset;
- no pre-roll;
- no model refit;
- no score regeneration;
- no provider/network call;
- no target/return/PnL access.

---

# 7. Required structural metrics

The replay must report at minimum:

## Turnover / churn

- total replacements excluding bootstrap;
- mean / median / p75 / p90 / max replacements per transition;
- share of transitions with 0 / 1 / 2 / >=3 replacements;
- turnover ratio versus naive exact daily Top-10;
- turnover ratio versus frozen Decision V1.

## Holding persistence

- completed holding-spell count;
- mean / median / p75 / p90 / p95 / max holding duration;
- one-session holding share;
- <=3-session holding share.

## Rank quality

- mean current Top-10 overlap with target;
- mean target rank;
- median target rank;
- mean worst held rank;
- distribution/count of target names currently rank >20;
- current Top-20 overlap.

## Decision state behavior

- number of `EXIT_PENDING_1` observations;
- recovery rate from `EXIT_PENDING_1` back to <=20 next session;
- `CONFIRMED_EXIT` count;
- `UNIVERSE_EXIT` count;
- soft replacement count;
- vacancy-fill count;
- fresh Top-10 rejected-as-unconfirmed count;
- `UNFILLED_NO_QUALIFIED_CHALLENGER` sessions and vacancy-days.

## Capacity

- target-size mean / median / minimum;
- share of sessions with target size 10;
- share with size 9;
- share with size <=8.

## Stability across time

- metrics by each historical 100-date block / fold segment;
- fold-boundary transitions reported separately but not reset.

---

# 8. Preregistered mechanical acceptance gates

V2 Minimal is considered mechanically acceptable for prospective Decision shadow only if **all hard gates** below pass.

These are engineering gates, not performance gates.

## Gate A — correctness / determinism

Must all pass:

- no target size >10;
- no duplicate target ticker;
- no unqualified non-bootstrap entrant;
- no one-observation rank>20 exit unless universe absent;
- no confirmed two-session >20 incumbent retained;
- no soft replacement without rank gap >=5;
- deterministic result under row-order permutation;
- identical replay on exact rerun from the same pinned inputs.

## Gate B — churn reduction

All must pass:

- mean replacements per transition `<=2.25`;
- turnover ratio versus naive exact daily Top-10 `<=0.50`;
- share of transitions with >=3 replacements `<=35%`.

Rationale: V1 mean was ~4.48 and >=3-replacement days were ~78.1%; V2 must cut the dominant mechanical failure by roughly half, not merely improve cosmetically.

## Gate C — holding persistence

All must pass:

- median completed holding spell `>=3` sessions;
- one-session completed holding share `<=35%`.

Rationale: V1 median was 1 session; V2 must create meaningful multi-session persistence.

## Gate D — rank quality preservation

All must pass:

- mean current Top-10 overlap `>=6.0 / 10` when target size is 10, with an equivalent normalized overlap reported for underfilled sessions;
- mean target rank `<=12.0` over ranked target rows.

Rationale: a stable portfolio that largely ignores current alpha is not acceptable.

## Gate E — capacity

All must pass:

- mean target size `>=9.0`;
- target size 10 on `>=70%` of sessions;
- target size <=8 on `<=10%` of sessions.

Rationale: temporal confirmation may create temporary underfill, but a nominal 10-name strategy cannot routinely operate as a much smaller portfolio.

## Gate F — no hidden stale-state failure

Must pass:

- no security may remain in target for a second consecutive available session with current rank >20;
- any exception must be only explicit current-universe absence handling and must fail closed rather than retain silently.

---

# 9. Verdict semantics after replay

Exactly one of the following statuses must be emitted:

### `DECISION_V2_MINIMAL_STRUCTURAL_ACCEPT`

All hard gates pass.

Next authorized step: freeze V2 Minimal implementation/profile and prepare prospective outcome-blind Decision shadow. Do not inspect historical PnL as a prerequisite for this mechanical acceptance.

### `DECISION_V2_MINIMAL_STRUCTURAL_REJECT`

Any hard gate fails.

A rejection does **not** authorize silent threshold adjustment, parameter sweep, H5/H10 rescue rule, smoothing rescue, alpha retune, or PnL inspection.

A next attempt requires a separately named preregistration (for example V2.1 or V3 depending on scope) with explicit rationale based on the failed mechanical dimension.

---

# 10. Forbidden during implementation and structural evaluation

Until the V2 Minimal structural verdict is frozen, do not access or use:

- realized H5/H10 returns;
- historical portfolio PnL;
- protected forward outcomes;
- fresh prospective outcomes;
- return labels for parameter selection;
- execution fills/fees/slippage for Decision rule selection;
- model retraining/refitting;
- alpha feature changes;
- Decision parameter sweeps;
- alternative rank thresholds;
- alternative confirmation lengths;
- alternative rank-gap thresholds;
- post-result rescue variants in the same run.

The only allowed implementation is the exact rule set in this preregistration.

---

# 11. Scientific interpretation boundary

A structural ACCEPT would establish only:

> this generic stateful Decision policy can convert the frozen V4-X1 rank stream into a materially less reactive, still rank-relevant target process.

It would **not** establish profitability, excess return, Sharpe, alpha preservation after costs, or real-money readiness.

A structural REJECT would establish only that this minimal Decision formulation is mechanically inadequate. It would not by itself prove that V4-X1 alpha is invalid.

---

# 12. Authorization state

As of this commit:

- preregistration: authorized and frozen;
- implementation: next allowed step;
- unit/property tests: allowed after implementation;
- 600-OOS structural replay: allowed only after exact implementation is reviewed against this preregistration;
- return/PnL evaluation: not authorized;
- prospective Decision shadow: not authorized until structural ACCEPT;
- V4-X2 alpha research: not opened by this preregistration.
