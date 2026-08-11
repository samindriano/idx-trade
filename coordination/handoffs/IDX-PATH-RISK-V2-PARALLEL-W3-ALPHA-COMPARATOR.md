# Worker W3 — Alpha-Only Comparator / Leakage Hardening

Role: VALIDATION
Mode: parallel writer, isolated worktree
Allowed write scope: `tests/test_path_risk_v2_alpha_comparator_hardening.py` plus this worker's final handoff only.

## Read first

- `AGENTS.md`
- `docs/PATH_RISK_V2_SPEC.md`
- `src/idx_trade/path_risk_v2_discovery_run.py`
- `src/idx_trade/ranking_v3_structure_lite.py`
- existing Path Risk V2 tests

## Question

Does the fold-specific V3-B alpha-only comparator remain strictly training-only and provide a valid incremental-information baseline for Path Risk V2?

## Required adversarial tests

Cover at least:

1. only outer-training rows may fit the alpha model;
2. alpha fit population uses only `TP_FIRST`/`SL_FIRST` with the frozen TP=1, SL=0 ranking target;
3. validation stop-touch outcomes never enter alpha fit or logistic mapping fit;
4. final all-history V3-B refit artifact/model is never loaded by this comparator;
5. logistic mapping is trained only on outer-training alpha scores + stop-touch targets;
6. comparator can score `AMBIGUOUS_SAME_BAR` and `NO_BARRIER_HIT` validation rows without using their outcomes as model inputs;
7. feature order is exact frozen 33 features;
8. fold-gap/validation boundaries remain exact F1-F4 and no session 985+ is accepted;
9. synthetic mutation of validation outcomes does not alter fitted comparator parameters or pre-metric validation probabilities;
10. one-class training conditions fail closed.

Do not use local real-data artifacts.

If production code is wrong, encode a failing test and describe the minimal fix. Do not edit production code.

## Validation

Run your new test file and existing Path Risk V2 focused tests. Report exact pass/fail counts.

## Final handoff

Create `coordination/handoffs/IDX-PATH-RISK-V2-PARALLEL-W3-RESULT.md` using the AGENTS handoff shape. Include base SHA, worker commit SHA, files changed, tests, defects found, and minimal recommended MAIN fix if needed.
