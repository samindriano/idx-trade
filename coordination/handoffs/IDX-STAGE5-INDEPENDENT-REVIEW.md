# Handoff
from: MAIN / ChatGPT REVIEW
to: EXPERIMENT / future bounded post-mortem
 task_id: IDX-STAGE5-INDEPENDENT-REVIEW
model_used: GPT-5.6 Thinking
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: c947bfea8f27aac0104b78283e6a8a63c255dfd3
branch: research/idx-stage5-ranking-holdout-v1
head_commit: documentation commit after review
scope: Independently review the completed one-shot Stage-5 ranking-only locked holdout and set the next authorization boundary.
files_changed: docs/checkpoints/2026-08-09_STAGE5_INDEPENDENT_REVIEW_FAIL.md; docs/CURRENT_STATUS.md; coordination/handoffs/IDX-STAGE5-INDEPENDENT-REVIEW.md
findings: The preregistered FAIL is accepted. HGB H10 PR-AUC was effectively equal to base (+0.0002105), overall ROC-AUC was 0.494843, HOLDOUT_A was positive, but HOLDOUT_B reversed below base with ROC below 0.5 and negative Q5-Q1. H5/H20 sensitivities were near-null. The result is a valid research failure, not a runtime/provenance failure.
decisions_made: Ranking V1 is rejected as a generalizable holdout-passed architecture and retained only as a failed benchmark. The consumed holdout must not be rerun. V1 must not be promoted to Stage 6. Probability V1 remains PROBABILITY_V1_NOT_READY_DEFERRED. Bounded post-mortem/V2 research design is authorized; any V2 independent validation requires fresh forward data strictly after 2026-07-31.
decisions_needed: Before implementing Ranking V2, predefine a small set of diagnostic questions and candidate hypotheses. Do not run an open-ended model search against the consumed holdout.
blocking_risks: Temporal instability/nonstationarity is the dominant observed failure pattern. Aggregate results alone cannot identify its cause. Strict execution-grade historical Open remains incomplete, so execution-PnL claims remain blocked.
validation_run: Reviewed frozen Stage-5 plan, runtime checkpoint, handoff, current status and PR #7 at final factual SHA c947bfea8f27aac0104b78283e6a8a63c255dfd3. Runtime evidence states 206 tests passed, frozen hashes matched, models were frozen before holdout labels, and one-shot markers were written before outcome access.
recommended_next_action: Run a bounded read-only Stage-5 post-mortem on the existing runtime artifacts to diagnose A-vs-B drift, feature/score distribution drift, and conditional/top-tail behavior. Use findings only to preregister Ranking V2; do not claim validation from the consumed holdout.
