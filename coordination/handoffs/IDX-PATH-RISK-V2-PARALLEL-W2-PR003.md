# Worker W2 — PR-003 Discrete Competing-Risk Hardening

Role: VALIDATION
Mode: parallel writer, isolated worktree
Allowed write scope: `tests/test_path_risk_v2_pr003_hardening.py` plus this worker's final handoff only.

## Read first

- `AGENTS.md`
- `docs/PATH_RISK_V2_SPEC.md`
- `src/idx_trade/path_risk_v2.py`
- existing `tests/test_path_risk_v2.py`

## Question

Does PR-003 correctly construct the discrete H1..H10 at-risk process and transform conditional CONTINUE/STOP/TP probabilities into coherent cumulative incidence without future leakage?

## Required adversarial tests

Cover at least:

1. TP event on H1/H5/H10 creates CONTINUE rows only before the event and TP exactly at event step;
2. SL event analogously creates STOP exactly at event step;
3. `AMBIGUOUS_SAME_BAR` maps to STOP under the frozen conservative convention;
4. `NO_BARRIER_HIT` creates exactly 10 CONTINUE rows;
5. no rows after first event;
6. `path_horizon_step` is always integer 1..10 and is the only extra candidate input beyond the frozen 33 features;
7. vectorized expansion preserves signal identity and row counts on mixed synthetic cases;
8. recursive CIF satisfies nonnegative bounded STOP/TP/survival and mass conservation at every horizon;
9. deterministic repeated fit/predict under seed 42;
10. malformed event timing (barrier date before/equal signal, outside H10, not on official session) fails closed.

Do not use local real-data artifacts.

If production code is wrong, encode a failing test and describe the minimal fix. Do not edit production code.

## Validation

Run your new test file and existing Path Risk V2 focused tests. Report exact pass/fail counts.

## Final handoff

Create `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W2-RESULT.md` using the AGENTS handoff shape. Include base SHA, worker commit SHA, files changed, tests, defects found, and minimal recommended MAIN fix if needed.
