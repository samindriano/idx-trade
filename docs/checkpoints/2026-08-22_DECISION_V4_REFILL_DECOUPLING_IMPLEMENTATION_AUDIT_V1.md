# Decision V4 Refill Decoupling V1 — Implementation Audit

Date: 2026-08-22 Asia/Jakarta

Verdict: `IMPLEMENTATION_PARITY_ACCEPTED_RUNNER_PREPARATION_ONLY_REPLAY_NOT_AUTHORIZED`

Reviewed implementation branch:

`research/idx-decision-v4-refill-decoupling-implementation-v1`

Reviewed implementation HEAD:

`815b4280dec66a49b368bfc17667d66e9ce43fd1`

Accepted preregistration audit base:

`178f06146f2f0388f9253edd810284ed4e1b5a79`

Frozen preregistration:

`docs/specs/decision_v4_refill_decoupling_v1.json`

## Exact diff surface

GitHub compare from accepted audit base to implementation HEAD is strictly ahead by five commits, behind by zero, with exactly five added files:

1. `docs/checkpoints/2026-08-22_DECISION_V4_REFILL_DECOUPLING_IMPLEMENTATION_V1.md`
2. `src/idx_trade/decision_v4_refill_decoupling.py`
3. `src/idx_trade/v4_x1_decision_v4_refill_decoupling.py`
4. `tests/test_decision_v4_refill_decoupling.py`
5. `tests/test_v4_x1_decision_v4_refill_decoupling.py`

No pre-existing V3/model/runtime implementation file was modified.

## Independent parity findings

The implementation preserves the accepted V3 semantics for:

- bootstrap exact Top10;
- start-of-session incumbent classification;
- strong/acceptable hold thresholds;
- one-session mild grace and confirmed mild exit;
- immediate severe exit at rank >50;
- immediate universe absence exit;
- challenger A/B/C/D classification;
- Tier D prohibition;
- temporary underfill permission;
- Tier-A soft replacement ordering, rank-gap threshold, and peer semantics.

The implementation introduces exactly the preregistered V4 mechanism:

- after all start-of-session incumbents are classified, `severe_exit_session` is frozen solely from whether at least one incumbent is `SEVERE_DETERIORATION_EXIT`;
- the flag is frozen before challenger refill and before soft replacement, so it is non-circular;
- flagged sessions use vacancy priority `A_CORE` only;
- non-flagged sessions retain V3 vacancy priority `A_CORE -> B_NEAR -> C_DISTANT`;
- the restriction applies to every vacancy on a flagged session regardless of whether the vacancy originated from severe exit, confirmed mild exit, universe exit, or pre-existing underfill;
- unchanged V3 Tier-A soft replacement still executes after refill;
- remaining vacancies may stay underfilled.

The V4-X1 adapter binds the frozen profile exactly:

- rule id `V4_X1_DECISION_V4_REFILL_DECOUPLING_V1`;
- target cap 10;
- strong 10;
- retention 20;
- mild 50 / severe 51+;
- soft replacement minimum rank advantage 5;
- temporary underfill allowed;
- verified-score projection reused from the existing V4-X1 Decision V3 adapter;
- non-bootstrap shadow state must be explicitly bound to the V4 rule id.

No threshold sweep, alternative refill cap, cooldown, delayed entry, min-hold, turnover cap, regime rule, Tier-D admission, soft-gap change, model refit, or rescore was introduced.

## Local validation evidence

Runner-only local validation at exact implementation HEAD reported:

- static compile/import: PASS;
- `git diff --check`: PASS;
- diff paths: exact expected five files;
- focused V4/V3 tests: 39 passed;
- broader Decision regression with correct `PYTHONPATH=src`: 185 passed, 0 failed;
- full pytest: 546 passed, 0 failed, 0 skipped, 3 pre-existing pandas FutureWarnings;
- no tracked mutation;
- no commit/push by the local runner.

The first broader validation attempt had one environment-only subprocess import failure because pytest's configured `pythonpath=["src"]` does not automatically alter the child Python process spawned by the V3 CLI hardening test. Re-running with an explicit temporary `PYTHONPATH=src` made that isolated hardening test pass and the full regression suite clean. No source change was needed or made.

## Scientific boundary

- `600_SESSION_REPLAY_NOT_RUN = true`
- `REALIZED_DECISION_OUTCOMES_NOT_ACCESSED = true`
- `PROTECTED_FORWARD_NOT_ACCESSED = true`
- `MODEL_REFIT_OR_RESCORE = false`
- `THRESHOLD_SWEEP = false`
- `ALTERNATIVE_V4_VARIANT = false`
- `PROVIDER_OR_NETWORK_DATA_CALL = false`
- `REPLAY_AUTHORIZED = false`

## Audit conclusion

The Decision V4 implementation is accepted as a faithful implementation of the frozen preregistration and is eligible only for the next preregistered step: preparation and independent audit of a separate guarded structural replay runner.

This checkpoint does **not** authorize the 600-session historical structural replay.

The candidate remains the final Decision experiment. No V4.1/V4.2/rescue variant is authorized after observing future results.
