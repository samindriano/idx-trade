# Decision V4 Refill Decoupling V1 — Structural Runner Preparation

Date: 2026-08-22 Asia/Jakarta

Status: `RUNNER_PREPARED_STATIC_REVIEW_COMPLETE_LOCAL_VALIDATION_PENDING_REPLAY_NOT_AUTHORIZED`

Runner branch:

`research/idx-decision-v4-refill-decoupling-structural-runner-v1`

Runner implementation/test HEAD before this documentation commit:

`ee01b98c0b50c6c60850093540957ee9cd4960a5`

Accepted implementation audit parent:

`audit/idx-decision-v4-refill-decoupling-implementation-v1` at `73939c7dbe6db23554323fd0bd4c21ddfd4b964a`

Accepted implementation HEAD:

`815b4280dec66a49b368bfc17667d66e9ce43fd1`

Frozen preregistration:

`docs/specs/decision_v4_refill_decoupling_v1.json`

Frozen preregistration canonical JSON SHA-256:

`aa8763bdebf7b3334016a651d0376b17d6c6d7aa3a2c2356bf126fd5de8396f7`

## Added runner surface

Exactly six runner-preparation files were added before this checkpoint:

1. `src/idx_trade/decision_v4_structural_contract.py`
2. `src/idx_trade/decision_v4_structural_replay.py`
3. `scripts/run_v4_x1_decision_v4_refill_decoupling_structural_replay.py`
4. `tests/test_decision_v4_structural_contract.py`
5. `tests/test_decision_v4_structural_replay.py`
6. `tests/test_decision_v4_structural_runner_hardening.py`

No pre-existing V3 implementation, V3 structural replay, source loader, model, scorer, or forward-runtime file was modified.

## Reused hardened infrastructure

The runner intentionally reuses the existing Decision V3 structural infrastructure where semantics are unchanged:

- strict pinned V4-X1 historical score source loader;
- source manifest and score SHA checks;
- 600-session / 172,697-row source count checks;
- consensus-rank reconstruction from the same projected score inputs;
- verified-score session construction;
- Decision shadow-state contract;
- plan digest construction;
- target/membership/intent/state ledgers;
- holding-spell construction;
- fixed six-block and fold reporting;
- existing frozen structural metric calculations and thresholds;
- independent post-replay ledger/source integrity validator.

The V4 runner does not read H5/H10 realized outcomes, returns, PnL, protected/fresh forward data, provider/network data, or any model-refit inputs.

## V4-specific runner logic

The V4 replay path uses only:

`V4_X1_DECISION_V4_REFILL_DECOUPLING_V1`

The runner independently reconstructs start-of-session incumbent states from current/previous ranks, independently derives the severe-session flag, independently derives challenger tiers, and independently reconstructs the expected vacancy-fill sequence.

On a severe session the independent expected refill sequence is `A_CORE` only. On a nonsevere session it is `A_CORE -> B_NEAR -> C_DISTANT`.

A separate V4 correctness gate fails closed if:

- any Tier-B/Tier-C vacancy refill occurs on a severe session; or
- the planner's severe-session classification disagrees with the independent rank-based reconstruction.

This correctness gate does not change any preregistered performance threshold.

## Required descriptive diagnostics

The runner emits all preregistered descriptive diagnostics:

- `severe_exit_session_count`
- `tier_a_vacancy_fills_on_severe_sessions`
- `tier_b_candidates_blocked_on_severe_sessions`
- `tier_c_candidates_blocked_on_severe_sessions`
- `underfilled_sessions_after_severity_conditioned_refill`
- `vacancy_days_after_severity_conditioned_refill`
- `block_1_to_6_churn_quality_capacity_summary`

For blocked B/C candidates, the frozen reporting definition is seat-feasible B/C challengers that would have occupied residual vacancies under unchanged V3 `A -> B -> C` priority after available A supply, but are withheld solely because the session is severe. This is descriptive only and cannot alter a gate or threshold.

## Guard ordering

The CLI requires the exact process authorization token before any preregistration or historical-source access. With a wrong token it must fail with:

`DECISION_V4_REPLAY_AUTHORIZATION_TOKEN_REJECTED`

before attempting to inspect/hash the frozen preregistration or load the historical source.

The presence of the token string in source code does not itself authorize execution. Scientific authorization remains a separate post-validation/post-audit step.

## Static review

Before this checkpoint:

- exact branch diff from the implementation-audit parent was strictly ahead by six commits, behind by zero;
- exactly the six runner-preparation files above were added;
- the Python source strings were syntax-compiled before repository writes;
- no historical replay was executed;
- no outcome, PnL, forward, provider, model-refit, or rescore path was accessed.

## Local validation required next

Codex may only act as a local runner to:

- verify exact branch/HEAD;
- compile/import the new runner modules/script;
- run `git diff --check`;
- run the new V4 structural contract/replay/hardening tests plus implementation/V3 structural regressions;
- run full pytest if focused/broader tests pass;
- prove wrong authorization rejects before prereg/source access;
- verify the worktree remains unmodified.

Codex is not authorized to edit, repair, tune, commit, push, or execute the historical 600-session replay during this validation pass.

## Scientific boundary

- `600_SESSION_REPLAY_NOT_RUN = true`
- `REALIZED_DECISION_OUTCOMES_NOT_ACCESSED = true`
- `PROTECTED_FORWARD_NOT_ACCESSED = true`
- `MODEL_REFIT_OR_RESCORE = false`
- `THRESHOLD_SWEEP = false`
- `ALTERNATIVE_V4_VARIANT = false`
- `PROVIDER_OR_NETWORK_DATA_CALL = false`
- `REPLAY_AUTHORIZED = false`

## Next gate

If local validation passes, ChatGPT must independently audit the exact frozen runner branch/HEAD. Only a separate runner-audit acceptance checkpoint may authorize the one-shot 600-session structural replay.

If the one-shot structural replay later rejects V4, Decision V2 remains the frozen incumbent and Decision research closes. No V4.1/V4.2/rescue variant is authorized.
