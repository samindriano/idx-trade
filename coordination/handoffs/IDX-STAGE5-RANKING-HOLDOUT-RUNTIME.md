# Handoff
from: MAIN / ChatGPT REVIEW
to: EXPERIMENT / LOCAL RUNTIME EXECUTION
task_id: IDX-STAGE5-RANKING-HOLDOUT-RUNTIME
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 92d5f6c03a2f266bd613db2b1cb6e210a28e0715
branch: research/idx-stage5-ranking-holdout-v1
head_commit: pending latest documentation commit
scope: Execute exactly one frozen Stage-5 V1 ranking-only locked holdout after all final models are serialized and hashed.
files_changed: docs/STAGE5_RANKING_HOLDOUT_PLAN_V1.md; src/idx_trade/research_stage5.py; src/idx_trade/stage5_ranking_holdout.py; tests/test_research_stage5.py; docs/CURRENT_STATUS.md; docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_READY.md; coordination/handoffs/IDX-STAGE5-RANKING-HOLDOUT-RUNTIME.md
findings: Stage 3/4 ranking evidence is positive but modest; Stage 4 and Stage 4B probability calibration failed proper-score gates. Probability V1 is frozen NOT_READY_DEFERRED. The preregistered primary PR-AUC ranking question is allowed one untouched holdout test. Stage-5 implementation substantive CI passed 206/206 with only existing warning classes.
decisions_made: Final training signals stop at 988 to preserve H20 purge before holdout 1009. Primary H10 holdout is 1009-1250. H5/H20 are sensitivity-only. Models are frozen before holdout outcome labels. A durable global marker beside the immutable panel makes holdout access one-shot across output directories. Once marker exists, no automatic rerun is allowed.
decisions_needed: After runtime, ChatGPT independently reviews PASS/MIXED/FAIL/BLOCKED and decides whether ranking V1 may proceed to forward shadow evaluation. Probability V1 remains disabled regardless of Stage-5 ranking result.
blocking_risks: This action permanently consumes the 2025-07-15..2026-07-31 holdout for RANKING_V1_ONLY. A crash after the global marker is written still consumes the holdout for project-governance purposes. Strict execution-grade Open history remains incomplete, so no execution-PnL claim is allowed.
validation_run: Latest substantive Stage-5 code/test CI before documentation freeze -> 206 passed, 0 failed; 15 existing pandas/NumPy warning instances. Holdout not accessed.
recommended_next_action: Under exact Stage-3/4 numerical environment, run `python -m idx_trade.stage5_ranking_holdout` once against the exact frozen panel/manifest/calendar/security-master/Stage-4B summary. If the global holdout marker appears and the process then fails, STOP and report; DO NOT rerun. Runtime artifacts remain outside Git. Document factual result and stop before any Stage 6, Probability V2, IDX-VAL-002, main merge, paper or live trading.
