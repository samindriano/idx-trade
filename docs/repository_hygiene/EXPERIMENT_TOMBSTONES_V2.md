# Experiment Tombstones V2

Date: 2026-08-22 Asia/Jakarta
Purpose: preserve durable scientific conclusions while allowing aggressive branch deletion.

This ledger is intentionally about **what was learned**, not about keeping every historical implementation branch alive.

## Decision lineage — CLOSED

### Decision V1

Outcome: structurally too churny on the exact 600-session Decision development trajectory.

Durable lesson: static Top10/Top20/gap-5 rules that look reasonable in local/property tests can produce excessive realized membership churn once adjacent-session rank dynamics are replayed continuously. Rank persistence and capacity must be tested on the actual trajectory, not inferred from static slices.

Disposition: intermediate V1 trajectory/rank-dynamics/persistence branches may be deleted after this ledger and PR history preserve the conclusions.

### Decision V2 — INCUMBENT

Decision V2 remains the frozen incumbent Decision policy. Its model-agnostic state-machine implementation is retained as a live anchor.

Durable lesson: previous-session entry confirmation, multi-observation deterioration handling, deterministic underfill and qualified replacement materially improve policy quality relative to V1, and V2 remained the best economic development-set policy among the tested Decision family.

### Decision V2.1 Conservative Severe Replacement

Outcome: structurally cleaner in some respects but economically worse than V2.

Key remembered development-set deltas versus V2:
- H5 gross approximately `-0.00044406` (~-4.44 bps)
- H10 gross approximately `-0.00078613` (~-7.86 bps)

Durable lesson: rank cleanliness is not equivalent to economic quality.

Disposition: tombstone and delete live experiment branch.

### Decision V2.2 Coherent Vacancy Admission

Outcome: worse than V2 and materially more underfilled.

Key remembered development-set deltas versus V2:
- H5 gross approximately `-0.00097027`
- H10 gross approximately `-0.00098917`
- underfilled sessions `199`
- vacancy days `620`

Durable lesson: stronger admission coherence can starve portfolio capacity without improving economics.

Disposition: tombstone and delete live experiment branch.

### Decision V3 Graded Evidence

Outcome: structural reject.

Durable mechanism diagnosis:
- severe-exit sessions were common and clustered;
- mandatory severe exits were immediately followed by vacancy refill;
- fragile entrants often became future severe exits, producing a refill loop;
- Tier-A soft replacement entrants were more durable than vacancy-fill entrants, but the observed selection mechanism did not identify a safe new threshold.

Representative diagnosed mechanism:
`clustered mandatory severe exits -> immediate same-session vacancy refill -> fragile entrant -> later severe exit -> refill again`.

The A-admission gap magnitude itself did not provide a defensible durability signal: next-severe and eventual-severe associations were essentially null/weak, so a larger soft rank-gap threshold was not authorized.

Disposition: all prereg/audit/runner/diagnosis intermediates may be deleted. Exact Decision V3 source is not required for E2E. PR history + this tombstone preserve its scientific value.

### Decision V4 Refill Decoupling

Outcome: `DECISION_V4_REFILL_DECOUPLING_V1_STRUCTURAL_REJECT`.

One-shot source: 600 sessions / 172,697 rows.

Binding failed frozen gates:
- mean replacements `2.814691` > max `2.25` -> churn fail;
- median completed holding `2.0` < min `3` -> persistence fail;
- mean target size `8.94` < min `9.0` -> capacity fail.

Passed/positive structural characteristics included:
- mean target rank `9.300708`;
- full-target Top10 overlap `7.769608`;
- one-session holding share `0.265351`.

Descriptive mechanism counts:
- severe-exit sessions `342`;
- Tier-A severe-session vacancy fills `713`;
- Tier-B candidates blocked `294`;
- Tier-C candidates blocked `341`;
- underfilled sessions `192`;
- vacancy days `636`.

Durable lesson: restricting lower-confidence refill improves rank cleanliness but does not solve churn/persistence and materially harms capacity. No V4.1/V4.2/rescue is authorized.

Retained anchor: final V4 result/Decision closure audit branch only. Intermediate V4 prereg/implementation/runner/audit branches may be deleted.

## Ranking / alpha lineage

### Early Stage 3 / Stage 4 / Stage 4B / Stage 5 Ranking V1

Outcome: useful development evidence but superseded by later Ranking V2/V4-X1 lineage; the locked Stage-5 Ranking V1 holdout failed the preregistered final gate and became a benchmark/postmortem source.

Durable lessons:
- HGB ranking evidence was stronger than probability calibration evidence;
- calibration was not reliably production-ready;
- a model can show positive development ranking metrics and still fail a locked temporal holdout;
- probability output must not be treated as trustworthy simply because ranking quality is positive.

Disposition: retain at most a postmortem archive tag; delete the live Stage 3/4/4B/5 branch chain.

### Ranking V2

Outcome: HGB_XS_MARKET became the durable clean historical parent/baseline. Ranking V2 spec/runtime lineage remains a live anchor because it is still scientifically and operationally relevant.

### V3-B / O2 contamination lineage

Historical finding: KOCI pre-listing contamination affected causal historical features. Clean PIT-safe reproduction restored clean V2 HGB_XS_MARKET as the historical survivor; V3-B failed the frozen late paired gate and O2 became `O2_DIAGNOSTIC_ORPHANED_PARENT`.

Durable lesson: downstream model performance cannot rescue contaminated feature lineage. Clean parent reproduction outranks historical headline metrics.

Disposition: retain the clean-reproduction anchor, not every O1/O2/minimality/geometry/robustness branch.

## Probability / payoff / reliability / path-risk auxiliary models

### Probability V1

Outcome: `PROBABILITY_V1_NOT_READY_DEFERRED`.

Lesson: ranking strength did not establish calibrated TP-before-SL probability quality.

### Expected Payoff V1

Outcome: no survivor.

Representative evidence:
- median MSE skill about `-0.05217`;
- `0/6` positive folds.

Lesson: do not add an expected-payoff ML layer without genuine incremental predictive value.

### Reliability

Outcome: limited survivor only. `score_margin_reliability` qualified historically; other reliability constructions did not justify becoming a mandatory decision layer.

Lesson: reliability is metadata/sidecar evidence, not a license for a second decision model.

### Path Risk

Outcome: prior attempts did not establish a production-ready path-risk model.

Disposition: failed/superseded auxiliary model branches can be tombstoned unless needed by a current forward sidecar.

## Historical Open / execution-price recovery

Multiple Wildan/Yahoo/Zapi/TradingView/Investing attempts explored historical Open recovery.

Durable conclusion: historical executable Open could not simply be reconstructed or substituted without defensible source/scale/session semantics. Existing Open must not be overwritten by approximate/provider-mismatched values.

Important recurring issues:
- Yahoo historical OHLC split behavior was mixed/inconsistently aligned with official events;
- Zapi alternative sources did not reliably fill the missing-Open population under exact H/L/C admission;
- provider timestamps/access time are not automatically PIT publication time;
- pre-opening/auction semantics mean a simplistic 09:00 snapshot may not equal official opening semantics.

Disposition: old source-audit/backfill branches may be deleted after selected final semantic anchors are archived/retained. E2E should use prospective, explicitly certified execution-price acquisition instead of trying to rescue historical PnL.

## Historical Universe

Outcome: `FAIL_NO_COMPLETE_WINDOW`.

Durable issue: official listing/relisting/delisting public surfaces did not establish a defensibly complete bounded historical universe; lifecycle conflicts such as BUKK/relisting semantics prevented canonical promotion.

Disposition: archive the final source-audit result, delete intermediate branch clutter. Do not infer lifecycle from price presence.

## PIT sector history

Outcome: partial source readiness, incomplete historical canonical coverage.

Known state included ready official evidence for several years but dedicated annual 2022/2023 sources unresolved and 2026 effective-date linkage incomplete in the original pass.

Disposition: old PIT-sector branch may be archived/deleted; retain only the latest revival/current lane if it still has live acquisition value.

## Corporate actions

Early Corporate Actions V1 established official source discovery but did not provide defensible historical execution continuity. Mechanical split validation against the mixed Yahoo price basis largely failed.

Later V4 clean/continuity work became the relevant lineage. Forward paper work has validated official cash-dividend authority, cash-dividend accounting, certified-event registry and persistent state; unsupported structural events remain fail-closed.

Disposition: preserve the current clean/continuity/forward-CA anchors. Intermediate schedule/event forensic branches may be deleted once their result is incorporated into those anchors.

## Foreign Flow

Early Foreign Flow V1 established unit/source semantics but historical PIT publication timing remained unresolved. Later representation/forward work superseded the scaffold.

Disposition: retain final representation + prospective capture/runtime branches; archive/delete early scaffold/review intermediates.

## TradingView / Investing historical intraday

Historical intraday admission attempts did not achieve a defensible canonical historical panel under frozen coverage/fidelity gates.

Representative TradingView rejection: certified-session coverage around `86.62%` failed despite relatively high returned-row HLC/volume fidelity. Later semantic work showed extended-session data can begin before regular 09:00 and that auction/open identity is not automatically proven.

Investing admission was also rejected on coverage/provider-error and fidelity grounds.

Durable lesson: do not lower admission gates merely because the surviving rows look good. Historical intraday is not required to finish E2E baseline.

Disposition: retain a small semantic/price-path anchor set only; delete most forensic/admission intermediates.

## Data-source experiments generally

When a branch is deleted under Hygiene V2, the conclusion is **not erased**. A future agent must treat the tombstone as binding historical evidence unless new, independently justified source evidence appears. Deleted failed experiments must not be casually recreated under a new branch name.
