# V4-3 CA IDX Combined Replay Prep — 2026-08-19

Status: `PRETARGET_COMBINED_REPLAY_READY_FOR_LOCAL_EXECUTION`

## Purpose

Recompute the frozen V4-3 training-domain CA continuity gate after applying two immutable, outcome-blind official-evidence adjudications in sequence:

1. KSEI schedule-80 adjudication: 21/80 resolved (1 exact transition, 20 exact nonblocking), manifest `13f4e84d8586c22e100382071f0b4cd4cdbb87e3099b7f0526f844a495ab1fd0`.
2. IDX residual-59 adjudication: 12/59 resolved (10 exact transitions, 2 exact nonblocking), 0 conflicts, manifest `4e296c54785d34e446f43259fd51b02176c1e4193e0816089acb24244117539f`.

The base training-domain replay remains manifest `c115ea0bec59cab4da0cda45ee66ba2be5814e0bb9e854e3f7ecd616edc83861`. The post-KSEI residual-59 identity is frozen as `f1c587eca59a9e7ec68cb8b1b2fc0980489a8f8a1b608f10403f2cc9f6d85707`.

## Replay order

The combined runner starts from the base replay, applies the already-frozen KSEI adjudication to all 80 schedule-required events, verifies that the exact remaining 59-event identity matches the frozen residual identity, and only then applies the IDX adjudication. No event outside that residual identity may be altered.

## Scientific firewall

This replay is outcome-blind and provider-free. It does not perform network calls, provider calls, source substitution, new discovery, fuzzy event matching, price inference, Record/Distribution-to-transition inference, pass-preserving subset selection, threshold changes, parser/semantic relaxation, target/rank materialization, historical target access, model fit, prediction, performance calculation, or protected-forward access.

The preregistered gate remains `0.90` and the frozen validation folds remain SHA-256 `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`.

## Coordination

Latest canonical `main:coordination/TEAM_STATUS.md` was read before this material continuation. No overlapping visible active V4-3 combined CA replay lane was identified. The connector does not safely expose a surgical row-only update for the large shared ledger, so this branch-local checkpoint records ownership without overwriting the canonical coordination file.

## Next

Run the focused tests and execute `scripts/run_v4_3_ca_training_domain_idx_combined_replay_v2.py` against the immutable base replay, KSEI adjudication, and IDX adjudication roots. If the preregistered gate passes, pin the resulting artifact before any historical target access. If it remains blocked, review the remaining schedule events under the previously agreed stop rule before any further acquisition.
