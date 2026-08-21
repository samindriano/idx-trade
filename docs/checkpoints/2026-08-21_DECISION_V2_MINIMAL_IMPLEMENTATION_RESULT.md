# Decision V2 Minimal — Implementation Result

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_TESTED_AUDIT_REMEDIATED_NO_HISTORICAL_REPLAY`

Branch: `research/idx-decision-v2-minimal-implementation-v1`

Parent preregistration: `research/idx-decision-v2-minimal-prereg-v1`

## Result

The frozen Decision V2 Minimal preregistration has been implemented without historical replay.

Implemented components:

- generic rank/state Decision V2 Minimal engine;
- separate V4-X1 verified-score adapter/profile;
- deterministic incumbent/challenger state observations;
- previous-session entry confirmation;
- two-observation exit confirmation;
- immediate universe exit;
- qualified vacancy fill with temporary underfill;
- qualified gap-5 soft replacement;
- explicit capacity state `FULL` vs `UNFILLED_NO_QUALIFIED_CHALLENGER`;
- shadow-state rule identity binding through `DecisionV2ShadowState.from_plan(...)` with cross-profile mismatch rejection;
- deterministic row-order-independent output;
- adversarial/unit tests covering the frozen semantics and audit remediation.

## Audit remediation

Independent audit PR `#42` found one blocking observability gap before replay: numeric `unfilled_slots` existed, but the preregistered explicit `UNFILLED_NO_QUALIFIED_CHALLENGER` state was missing.

That gap is remediated without changing policy behavior or thresholds.

The same remediation also adds non-scientific state-lineage hardening:

- Decision plans already carry `rule_id`;
- `DecisionV2ShadowState.from_plan(...)` now preserves that identity;
- a bound state is rejected if reused under a different Decision profile;
- legacy unbound generic states remain backward-compatible;
- the controlled future historical replay runner must use bound states only.

The separate exact-adjacent-session requirement remains a replay-runner invariant: iteration must use consecutive entries from the pinned 600-date score ledger `(t-1, t)` with no skipped session, no fold reset, and no pre-roll.

## Validation

Draft implementation PR: `#41` — `Implement Decision V2 minimal state machine`.

Remediated implementation code HEAD validated by GitHub Actions: `32af46172a686fdf407e1026ad4acdab12edc355`.

Full repository pytest result:

- `432 passed`;
- `26 warnings`;
- `0 failed`.

The warnings are pre-existing pandas/NumPy deprecation/future warnings in unrelated modules/tests.

## Scientific boundary

No exact 600-OOS Decision V2 replay has been run.

No realized returns or PnL were loaded or computed. No H5/H10 rescue rule, score/rank smoothing, parameter change, alpha/model refit/retune, provider/network call, or protected/fresh-forward outcome access occurred.

The implementation remains locked to the preregistered V4-X1 profile:

- target max `10`;
- strong/entry zone `<=10`;
- retention zone `<=20`;
- previous-session entry confirmation `<=20`;
- two consecutive available observations outside `20` required for confirmed exit;
- soft replacement gap `>=5`;
- immediate universe absence exit;
- temporary underfill allowed.

## Next boundary

Audit remediation is accepted. The next separately gated work is preparation of the outcome-blind exact 600-OOS structural replay runner with:

- pinned source manifest/score hashes;
- exact adjacent score-session ledger enforcement;
- bound shadow-state lineage;
- all preregistered mechanical acceptance gates encoded before the first replay.

The replay itself remains unexecuted and should not be run until that runner is implemented and reviewed.
