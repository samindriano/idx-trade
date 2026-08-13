# Path Risk V2 — Preflight Fixture Block Resolved

Date: 2026-08-11 (Asia/Jakarta)
Status: `PRE_OUTCOME_TEST_FIXTURE_BLOCK_RESOLVED_RETRY_AFTER_PYTEST`

The first preflight after the frozen V1 physical-schema guard correction stopped before the Path Risk V2 discovery runner was executed.

Observed local preflight:

- source HEAD before this fix: `0b147d34bc848737a7f55275ef31d60095d01f86`;
- checkout/import resolution: correct;
- working tree: clean and synced;
- pytest: `470 passed, 1 failed, 3 warnings`;
- failing test: `tests/test_path_risk_v2_discovery_run.py::test_v1_model_table_hash_and_session_boundary`.

The failure was a stale synthetic fixture. The test still constructed the pre-hardening projected schema, while the runner now correctly validates the exact physical schema of the immutable V1 discovery model table:

1. identity columns;
2. `universe_primary_liquid`;
3. exact frozen 33 features in order;
4. `label_status`;
5. `first_barrier_date`;
6. `target_tau_date`;
7. `adverse_excursion_r`.

The fixture has been updated to mirror that frozen physical schema. No production-model semantics, features, target, folds, candidate definitions, metrics, gates, or selection rules changed.

No PR-002/PR-003 fit, score, prediction, metric, or verdict was produced. No Path Risk F5/F6 or post-2026-07-31 fresh-forward outcome was accessed, and `FORWARD_OUTCOME_ACCESS_STARTED` remains unwritten.

The `_002` discovery output directory remains the authorized destination because this failure occurred in pytest preflight before the runner was invoked.

Retry is authorized only after pulling the latest branch and obtaining a full local pytest result with zero failures. Then execute the existing run-only handoff exactly once and stop for ChatGPT review.
