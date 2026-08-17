# Handoff: Ranking V4-3 pre-fit runtime V1

Date: 2026-08-17 (Asia/Jakarta)
Owner: `ChatGPT/V4-3-Prefit-Runtime`
Branch: `research/idx-ranking-v4-3-prefit-runtime-v1`
Parent support acceptance: `48dbca3799a71306a62a9ad156a106e1a978b006`
Status: `BLOCKED_PINNED_PREREGISTRATION_HASH_MISMATCH`

## Completed by ChatGPT

- independently accepted `research/idx-ranking-v4-3-preregistration-v1@55440cac2b605c687963ce858ccd3610659ddba0`;
- froze machine-readable pre-fit runtime protocol;
- implemented an outcome-blind environment capture script;
- added focused protocol/estimator-semantics tests;
- documented that no target/model execution is authorized by this lane.

## Local operator task only

1. refetch latest `origin/main:coordination/TEAM_STATUS.md` and preserve all other rows;
2. checkout/pull this branch exactly;
3. run:
   - `python -m pytest tests/test_ranking_v4_3_preregistration.py tests/test_ranking_v4_3_prefit_runtime.py`
   - `python -m py_compile scripts/capture_v4_3_prefit_environment.py`
   - `git diff --check`
4. require a clean worktree;
5. execute only the pre-fit environment capture to a brand-new immutable external directory;
6. promote only the small JSON environment manifest plus a result checkpoint/handoff;
7. update TEAM_STATUS to `REVIEW`;
8. STOP.

Do not materialize R5/R10, target ranks, fit a model, generate predictions, compute IC/Top30/raw-return performance, call providers, or touch fresh/protected outcomes.

## Additional pre-model hard gate

Before a later historical V4 execution is authorized, the target materializer must explicitly fail closed on mechanical corporate-action discontinuities inside the future entry-to-terminal-price interval. No assumption that a generic CA-integrity flag equals pathwise price continuity is authorized without separate evidence.
