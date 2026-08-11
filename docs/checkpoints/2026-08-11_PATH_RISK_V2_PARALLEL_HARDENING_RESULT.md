# Path Risk V2 Parallel Hardening Result

Date: 2026-08-11 (Asia/Jakarta)

Status: `PATH_RISK_V2_PARALLEL_HARDENING_PASS_READY_FOR_LOCAL_DISCOVERY`

## Scope

This checkpoint records the Orchestra HEAVY pre-outcome hardening pass for the
frozen Path Risk V2 implementation. Five isolated Luna xhigh workers covered
the PR-002 and PR-003 test surfaces, alpha comparator, discovery runner, and
gate-selection behavior.

Source branch: `research/idx-ranking-v2-spec-v1`

Source base before worker integration:
`477b4411c8c294e9ca5012a3079248033de5641c`

Orchestra IDX Trade snapshot:
`orchestra/idx-trade` at `e6c84aebb8a374ca526997b0cd17997eec1f95b7`

## Worker results

| Worker | Scope | Final handoff commit | Result |
|---|---|---|---|
| W1 / Boole | PR-002 hardening | `8ca78867bda218e7cf054b2cff6c5ab70a95f80e` | 16 new tests and 10 existing focused tests passed |
| W2 / Ohm | PR-003 hardening | `846f40fe24ef8976d7cf8dccc1cec8c0c447d930` | 17 new tests; 23 combined focused tests passed |
| W3 / Hooke | alpha comparator hardening | `709f5b6bb0641d0597bb71b67da2033da138b082` | 18 focused tests passed |
| W4 / Dewey | discovery-runner hardening | `7a029f031fecfda96659241b385429e5ca30ffdb` | exposed one production schema-validation defect; bookkeeping committed after isolation |
| W5 / Epicurus | gate-selection hardening | `444b5b894324cf56fb3b64b11143b4a7cbc6e68d` | 22 new tests; 32 combined focused tests passed |

## Defect and fix

W4 demonstrated that `_read_v1_model_table` in
`src/idx_trade/path_risk_v2_discovery_run.py` projected the requested columns
before checking the physical Parquet schema. This allowed extra or reordered
source columns to pass validation because the projection normalized the view.

MAIN added an exact physical schema-name and order check using PyArrow before
the existing projected read. Extra, missing, or reordered columns now fail
closed. The patch does not alter the frozen V2 features, target, folds, model
parameters, candidate definitions, or gates.

## Validation

- focused hardening suite: `89 passed`;
- full repository pytest: `470 passed, 0 failed, 3 warnings, 34.73s`;
- `git diff --check`: passed;
- warnings: three existing pandas FutureWarnings in
  `curated_identity.py` and `tradability_anchor_reconstruction.py`;
- no PR-002/PR-003 F1-F4 outcome run was started;
- no Path Risk F5/F6 outcomes were accessed;
- no post-2026-07-31 fresh-forward outcomes were accessed;
- `FORWARD_OUTCOME_ACCESS_STARTED` was not written;
- no risk-veto, reranking, sizing, or alpha+risk integration rule was created.

## Decision

The frozen Path Risk V2 implementation is hardened and ready for the separate
authorized preflight. The actual PR-002/PR-003 evidence-producing F1-F4 run
remains a later serialized task and was intentionally not run here.

