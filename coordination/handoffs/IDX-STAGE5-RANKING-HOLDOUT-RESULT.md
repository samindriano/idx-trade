# Handoff
from: EXPERIMENT / LOCAL RUNTIME EXECUTION
to: MAIN / ChatGPT REVIEW
task_id: IDX-STAGE5-RANKING-HOLDOUT-RESULT
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 05c2bb549b446da374c13937a41aa6732cf71ec0
branch: research/idx-stage5-ranking-holdout-v1
head_commit: 551c837b6bffad5db3bfbbd6032f9e072881801e
scope: Execute exactly one frozen Stage-5 V1 ranking-only locked holdout and record the factual result.
files_changed: docs/CURRENT_STATUS.md; docs/PROJECT_CONTEXT_MASTER.md; docs/PROJECT_LEDGER.md; docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md; coordination/handoffs/IDX-STAGE5-RANKING-HOLDOUT-RESULT.md
findings: Automatic result STAGE5_RANKING_HOLDOUT_FAIL. HGB H10 PR-AUC was 0.4073793720 versus base 0.4071688603, but HGB ROC-AUC was 0.4948433255 and HOLDOUT_B PR-AUC was 0.3471254020 versus its 0.3577062238 base rate. Q5-Q1 was positive overall at 0.0108405246 but negative in HOLDOUT_B at -0.0198933303.
decisions_made: Final models were frozen and hashed before holdout label access. The global and local one-shot markers were written before outcome access. The holdout is consumed for RANKING_V1_ONLY and must not be rerun. Probability V1 remains PROBABILITY_V1_NOT_READY_DEFERRED.
decisions_needed: MAIN / ChatGPT REVIEW should decide whether any bounded forward research is appropriate. This runtime itself authorizes no Stage 6, Probability V2, IDX-VAL-002, execution-PnL claim, paper/live trading, or main merge.
blocking_risks: Ranking V1 failed the preregistered ROC-AUC and temporal-stability checks. The strict execution-grade Open history remains incomplete, and the consumed holdout cannot be reused for Probability V2.
validation_run: Full pytest 206 passed, 0 failed, with three existing pandas FutureWarnings. Frozen input hashes matched. Research manifest valid=true, 15/15. Runtime artifact and one-shot marker hashes were verified against the runner summary.
recommended_next_action: Independent ChatGPT review of docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md. Stop all later stages until review gives an explicit new authorization.
