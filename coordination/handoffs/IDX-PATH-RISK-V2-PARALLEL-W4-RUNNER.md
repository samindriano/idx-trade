# Worker W4 — Runner / Provenance / Boundary Hardening

Role: PRODUCTION + VALIDATION
Mode: parallel writer, isolated worktree
Allowed write scope: `tests/test_path_risk_v2_runner_hardening.py` plus this worker's final handoff only.

## Read first

- `AGENTS.md`
- `docs/PATH_RISK_V2_SPEC.md`
- `src/idx_trade/path_risk_v2_discovery_run.py`
- existing `tests/test_path_risk_v2_discovery_run.py`
- `coordination/handoffs/IDX-PATH-RISK-V2-DISCOVERY-F1-F4-RUN.md`

## Question

Does the discovery runner fail closed on provenance/import/output/fold-boundary errors and make it impossible to accidentally materialize Path Risk F5/F6 or fresh-forward outcomes?

## Required adversarial tests

Cover at least:

1. exact V1 model-table SHA required;
2. exact calendar SHA and exact V2 spec Git blob required;
3. model table must have expected 252,198 rows and max signal session <=984;
4. any session 985+ row causes hard failure;
5. duplicate ticker/date/session identities fail;
6. missing/extra/reordered frozen feature columns fail where contract requires exactness;
7. output directory must be new/empty and no silent overwrite/rerun is allowed;
8. candidate set is exactly PR-002 + PR-003; no PR-001 or PR-004 path;
9. selected folds are exactly F1-F4;
10. summary flags must keep F5/F6=false, fresh_forward=false, forward_marker=false;
11. artifact/summary hashing is deterministic on synthetic fixtures where applicable;
12. runner must not import/load final V3-B all-history model artifacts or raw H10/path sources.

Do not use local real-data artifacts.

If production code is wrong, encode a failing test and describe the minimal fix. Do not edit production code.

## Validation

Run your new test file and existing Path Risk V2 focused tests. Report exact pass/fail counts.

## Final handoff

Create `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W4-RESULT.md` using the AGENTS handoff shape. Include base SHA, worker commit SHA, files changed, tests, defects found, and minimal recommended MAIN fix if needed.
