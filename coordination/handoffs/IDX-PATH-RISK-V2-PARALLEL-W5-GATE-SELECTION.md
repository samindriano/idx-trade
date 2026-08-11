# Worker W5 — Gate / Selection / Spec-Consistency Hardening

Role: EXPERIMENT + VALIDATION
Mode: parallel writer, isolated worktree
Allowed write scope: `tests/test_path_risk_v2_gate_selection_hardening.py` plus this worker's final handoff only.

## Read first

- `AGENTS.md`
- `docs/PATH_RISK_V2_SPEC.md`
- `src/idx_trade/path_risk_v2.py`
- `src/idx_trade/path_risk_v2_discovery_run.py`
- existing Path Risk V2 tests

## Question

Are the frozen PR-002/PR-003 metric definitions, candidate gates, and winner-selection logic implemented exactly as preregistered, with deterministic tie handling and no post-result rescue path?

## Required adversarial tests

Cover at least:

1. each frozen gate condition independently causes FAIL when violated;
2. `>=3/4`, `4/4`, median thresholds, and strict `ROC > 0.5` semantics are exact;
3. positive improvement sign means lower log-loss/Brier than comparator;
4. neither passes -> `PATH_RISK_V2_DISCOVERY_FAIL_CLOSE`;
5. exactly one passes -> select it;
6. both pass with alpha-logloss median difference >0.002 -> higher median wins;
7. both pass with difference <=0.002 -> simpler PR-002 wins;
8. nonfinite metrics/probabilities cannot pass;
9. candidate list is fixed to PR-002/PR-003 only;
10. ECE and Spearman remain diagnostics, not accidental promotion gates;
11. F5/F6 cannot participate in discovery aggregation/selection;
12. no code path creates PR-004 or reinterprets PR-001.

Also perform a static spec-to-code constant audit and report any mismatch even if existing tests happen to pass.

Do not use local real-data artifacts.

If production code is wrong, encode a failing test and describe the minimal fix. Do not edit production code.

## Validation

Run your new test file and existing Path Risk V2 focused tests. Report exact pass/fail counts.

## Final handoff

Create `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W5-RESULT.md` using the AGENTS handoff shape. Include base SHA, worker commit SHA, files changed, tests, spec/code mismatches, and minimal recommended MAIN fix if needed.
