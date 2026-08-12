# Handoff

from: MAIN / ChatGPT ARCHITECT
to: LOCAL / Codex

task_id: IDX-RANKING-V2-FINAL-REFIT-FORWARD-RUNTIME-IMPLEMENT
branch: research/idx-ranking-v2-spec-v1
scope: Implement and freeze the final HGB_XS_MARKET refit artifact and the outcome-blind fresh-forward runtime. Do not access fresh-forward outcomes.

## Required first reads

Read in this order:

1. `docs/CURRENT_STATUS.md`
2. `docs/checkpoints/2026-08-10_RANKING_V2_FORWARD_SPEC_REVIEW_PASS.md`
3. `docs/RANKING_V2_CHAMPION_FORWARD_SPEC_V1.md`
4. `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`
5. `docs/checkpoints/2026-08-10_RANKING_V2_HISTORICAL_CHAMPION_REVIEW.md`
6. `docs/RANKING_V2_RESEARCH_SPEC_V1.md`

Explicitly state that `NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` was read before implementation.

## Frozen champion / refit inputs

Champion: `HGB_XS_MARKET`.

Prepared cache:

`D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v2_prepared_cache_20260809\ranking_v2_prepared_model_table.parquet`

Required cache SHA-256:

`522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`

Required cache manifest SHA-256:

`6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`

Final refit rows are fixed to the 292,633 eligible resolved-primary-H10 rows, 737 tickers, signal-session index 20..1250. Use the exact 25-feature order and exact frozen preprocessing/HGB parameters from the forward spec. One fit only. No tuning/search/calibration/candidate comparison.

## Authorized implementation

Implement/test/freeze:

- deterministic final-refit runner;
- final model joblib plus JSON manifest and hashes;
- causal forward feature/universe builder consistent with frozen V2 semantics;
- immutable source snapshot/provenance checks;
- H10 maturity diagnostics;
- fixed 100-session block and first/last-50 stability logic;
- PR-AUC delta, ROC-AUC, Q1/Q5 TP rates, Q5-Q1 TP-rate spread, top-decile TP rate/lift using exact historical semantics;
- pre-outcome manifest generation;
- atomic parent-snapshot `FORWARD_OUTCOME_ACCESS_STARTED` guard and duplicate-access refusal logic;
- deterministic artifact hashing and verification;
- runtime profiling and safe engineering optimization following `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- reference-vs-optimized equivalence tests without accessing fresh-forward outcomes.

Prefer one deterministic Python orchestrator and bounded internal compute. Do not use multiple Codex chats as unrestricted compute workers.

## Hard stop / prohibited

Do **not**:

- write `FORWARD_OUTCOME_ACCESS_STARTED` during this task;
- load/read/summarize fresh-forward labels or outcome paths after 2026-07-31;
- produce a PASS/MIXED/FAIL fresh-forward verdict;
- rerun historical V2 candidate selection;
- alter champion/features/hyperparameters/universe/labels/decision rules;
- start calibration, Stage 6, `IDX-VAL-002`, execution PnL, sizing, paper/live trading, or main merge.

Tests of marker behavior must use temporary/synthetic fixture directories only.

## Required result report

Return to MAIN/ChatGPT with:

- branch and exact HEAD;
- git cleanliness / remote sync;
- pytest/test counts;
- exact numerical environment;
- final model path + SHA;
- final model manifest path + SHA;
- verified training row/ticker/session counts;
- runtime implementation files changed;
- reference-vs-optimized equivalence results, if an optimized path was added;
- post-cache timing/profile findings;
- source-evidence readiness status for post-2026-07-31 forward data;
- explicit confirmation that no fresh-forward outcome was accessed and global marker was not written.

Stop after implementation/freeze. Fresh-forward one-shot outcome access requires a separate authorization when the 100-session block is fully H10-mature.
