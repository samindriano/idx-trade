# Decision V2 Minimal — Audit Remediation Acceptance

Date: 2026-08-21 Asia/Jakarta

Status: `REMEDIATION_ACCEPTED_REPLAY_RUNNER_PREPARATION_READY`

Implementation PR: `#41`

Original audit PR: `#42`

Originally audited implementation HEAD: `942095583e1921ae8d3daaf0fffe833317626465`

Remediated code HEAD reviewed: `32af46172a686fdf407e1026ad4acdab12edc355`

## Verdict

The blocking audit remediation is accepted.

The implementation now satisfies the preregistered explicit underfill observability requirement and adds reusable Decision-state lineage hardening without changing Decision V2 policy semantics.

## R1 acceptance — explicit underfill capacity state

PASS.

`DecisionV2Plan` now records deterministic capacity state:

- `FULL` when target capacity is fully populated;
- `UNFILLED_NO_QUALIFIED_CHALLENGER` when the target remains underfilled after exhausting qualified challengers.

The existing numeric `unfilled_slots` remains available for quantitative audit.

Focused tests cover both full and underfilled cases.

## Additional state-lineage hardening

PASS as engineering hardening.

`DecisionV2ShadowState.from_plan(...)` now carries the Decision `rule_id` forward.

A bound shadow state is rejected if supplied to another Decision profile. Legacy unbound generic state remains readable for backward compatibility, but the future controlled 600-OOS runner is required to advance state only through `DecisionV2ShadowState.from_plan(...)`, thereby keeping replay state bound to the frozen profile.

This adds no alpha-specific rule and changes no Decision threshold.

## Policy-semantics diff review

The remediation diff relative to the originally audited implementation contains no change to:

- target count 10;
- entry zone <=10;
- entry confirmation previous rank <=20;
- retention zone <=20;
- two-observation confirmed exit;
- immediate universe exit;
- gap-5 qualified soft replacement;
- temporary underfill permission;
- challenger ordering;
- incumbent ordering;
- bootstrap semantics;
- H5/H10 usage (still none);
- raw-score usage (still none);
- smoothing/regime/turnover/PnL logic (still none).

## Validation

GitHub Actions on remediated code HEAD `32af46172a686fdf407e1026ad4acdab12edc355`:

- `432 passed`;
- `26 warnings`;
- `0 failed`.

The warnings are unrelated pre-existing pandas/NumPy deprecation/future warnings.

## Remaining replay-runner invariant R2

R2 is intentionally not moved into the generic Decision engine.

Before any historical replay, the replay runner must fail closed unless it can prove:

- source manifest SHA-256 exactly `6573a563bb1c408bd32cdd00f9ae8aaba654d5fec96e6a250b4a3b2898d98205`;
- score parquet SHA-256 exactly `48ea8932de3405155550aabcb982ebe325bf0caa9ce5737fd75d23b91a3bda0b`;
- exactly 600 score sessions and 172,697 score rows;
- bootstrap occurs only at ledger index 0;
- every later call uses exact adjacent ledger sessions `(t-1, t)`;
- no skipped score session;
- no fold reset;
- no pre-roll;
- shadow state advances only from the immediately preceding Decision plan and remains bound to the frozen V4-X1 Decision V2 profile;
- all preregistered mechanical acceptance gates are encoded before first replay.

## Scientific boundary

No 600-OOS Decision V2 replay was run during remediation or acceptance.

No realized returns, PnL, protected/fresh-forward outcomes, provider/network calls, model refit, alpha retune, or Decision parameter sweep occurred.

## Authorization

Decision V2 Minimal implementation is accepted for **replay-runner preparation**.

This checkpoint does not itself authorize an unguarded historical replay. The next work is to implement and test the exact outcome-blind structural replay runner with R2 and the frozen acceptance gates, then review that runner before the first 600-OOS execution.
