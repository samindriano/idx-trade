# Multi-Session Adoption Rehearsal Matrix V1

Date: 2026-09-21

This matrix selects existing candidate-local synthetic tests as the required
whole-system rehearsal surface. It does not invoke an operational entrypoint,
provider, scheduler, cloud path, telemetry, or external artifact.

| # | Scenario | Candidate test | Exact invariant asserted |
|---:|---|---|---|
| 1 | normal full BUY | test_real_verified_v2_bootstrap_prepares_execution_without_rule_projection | verified adapter and execution plan preserve bound state/contract |
| 2 | positive partial BUY | test_positive_partial_buy_survives_restart_and_retry_completes_remainder | planned = filled + remaining + relinquished; residual survives restart |
| 3 | residual BUY retry | test_zero_lot_is_pending_and_retried_without_shadow_change | zero fill remains pending; no shadow-position drift |
| 4 | partial SELL | test_sell_capacity_can_partial_fill_and_blocks_paired_buy | sell residual and paired buy remain blocked with quantity lineage |
| 5 | SELL to BUY replacement | test_partial_sell_retry_completes_replacement_buy_with_obligation_lineage | replacement is linked to the sell obligation and retries exactly |
| 6 | blocked replacement | test_failed_sell_blocks_pair_and_persists_both_transitions | failed sell blocks paired transition; both durable records persist |
| 7 | target reversal | test_pending_buy_reversal_cancels_impossible_sell_and_unblocks_paired_buy | reversal changes only through explicit, bound transition |
| 8 | explicit cancellation/relinquishment | test_explicit_obligation_close_allows_decision_reversal | close event is policy/hash bound and replayable |
| 9 | dividend cum/ex/payment lifecycle | test_integrated_dividend_cum_ex_payment_is_exactly_once | entitlement and settlement are exactly once and registry-bound |
| 10 | CA payment before Decision | test_ca_timing_matrix_covers_three_payment_boundaries[2026-09-01-True-True-PAYMENT_BEFORE_DECISION] | raw and sizing state agree on pre-decision settlement |
| 11 | CA payment on Decision date | test_ca_timing_matrix_covers_three_payment_boundaries[2026-09-02-False-True-PAYMENT_ON_DECISION] | settlement belongs to sizing boundary, not raw execution parent |
| 12 | CA payment on execution date | test_ca_timing_matrix_covers_three_payment_boundaries[2026-09-03-False-False-PAYMENT_ON_EXECUTION] | settlement is deferred to execution boundary |
| 13 | restart after preparation | test_preopen_recovers_after_snapshot_before_execution_commit | restart recovers durable prepared parent without duplicate execution |
| 14 | restart after partial execution | test_recovery_preserves_verified_obligation_ancestor | verified partial obligation ancestor remains exact |
| 15 | restart after CA settlement | test_receivable_may_progress_exactly_once_to_settlement | receivable cannot disappear and cannot settle twice |
| 16 | stale/malformed latest snapshot | test_recovery_quarantines_tampered_latest_and_returns_verified_ancestor | latest is quarantined; only verified ancestor is selected |
| 17 | verified ancestor recovery | test_orchestration_state_loader_recovers_verified_snapshot_ancestor | ancestor hash/chain is preserved and replayable |
| 18 | identity alias conflict | test_identity_contract_rejects_overlapping_aliases | overlapping aliases fail closed; no silent normalization |
| 19 | config mismatch | test_bound_runtime_lineage_survives_execution_and_rejects_config_mismatch | config/runner/branch/commit mismatch blocks replay |
| 20 | interrupted child process | test_real_child_timeout_preserves_boundary_and_requires_recovery | child completion is not inferred; boundary becomes RECOVERY_REQUIRED |
| 21 | controller RECOVERY_REQUIRED | test_each_side_effect_boundary_is_durable_and_replay_fenced | each side-effect boundary is durable and replay-fenced |
| 22 | replay completed execution | test_integrated_dividend_cum_ex_payment_is_exactly_once | identical replay is idempotent; duplicate settlement is impossible |

## Rehearsal interpretation

The matrix intentionally reuses independent tests at the contract and
orchestration layers rather than claiming that a single test exit code proves
the entire system. The final challenge must additionally inspect:

- obligation conservation;
- state/cash/position drift;
- exact parent and payload hashes;
- duplicate event/settlement behavior;
- pending transition ownership;
- recovery/quarantine/fork decisions;
- identity/config/session binding;
- absence of provider/outcome access.

The selected node IDs executed on candidate code HEAD `66140b05` and produced
`29 passed` (parameterized CA timing and controller cases are included). This
is synthetic evidence only; it does not invoke an operational entrypoint.
