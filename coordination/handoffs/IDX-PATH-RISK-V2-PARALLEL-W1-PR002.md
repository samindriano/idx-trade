# Worker W1 — PR-002 Direct Stop-Touch Hardening

Role: VALIDATION
Mode: parallel writer, isolated worktree
Allowed write scope: `tests/test_path_risk_v2_pr002_hardening.py` plus this worker's final handoff only.

## Read first

- `AGENTS.md`
- `docs/PATH_RISK_V2_SPEC.md`
- `src/idx_trade/path_risk_v2.py`
- existing `tests/test_path_risk_v2.py`

## Question

Does PR-002 exactly implement the frozen direct H10 stop-touch probability contract, including target semantics, model structure, probability validity, and deterministic behavior?

## Required adversarial tests

Cover at least:

1. `SL_FIRST` and `AMBIGUOUS_SAME_BAR` map to positive stop-touch;
2. `TP_FIRST` and `NO_BARRIER_HIT` map to negative;
3. unknown/ineligible statuses fail closed rather than silently map;
4. PR-002 model selects exact 33 features and no forbidden outcome/alpha/ticker input;
5. frozen HGB hyperparameters exactly match spec;
6. missing feature values remain legal through training-only median imputation;
7. probability output is finite and in `[0,1]` on synthetic train/score fixtures;
8. deterministic repeated fit/predict under seed 42 on the same synthetic data;
9. no Open dependency.

Do not use local real-data artifacts.

If production code is wrong, encode a failing test and describe the minimal fix. Do not edit production code.

## Validation

Run your new test file and existing Path Risk V2 focused tests. Report exact pass/fail counts.

## Final handoff

Create `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W1-RESULT.md` using the AGENTS handoff shape. Include base SHA, worker commit SHA, files changed, tests, defects found, and minimal recommended MAIN fix if needed.
