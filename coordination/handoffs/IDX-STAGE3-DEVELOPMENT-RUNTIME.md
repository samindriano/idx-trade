# Handoff
from: EXPERIMENT / VALIDATION
to: MAIN / ChatGPT REVIEW
task_id: IDX-STAGE3-DEVELOPMENT-RUNTIME
model_used: GPT-5 Codex frozen Stage-3 runtime
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 4c484b087aff592234dbe9905213e9d83b2f2611
branch: research/idx-stage3-v1
head_commit: cd976da89003d7d714fc9d2a6c8dd13956e3e04e
scope: Execute the approved frozen Stage-3 development runner against the immutable SIGNAL_RESEARCH_HLCV artifacts through development fold F3 only.
files_changed: docs/PROJECT_CONTEXT_MASTER.md; docs/PROJECT_LEDGER.md; docs/checkpoints/2026-08-09_STAGE3_DEVELOPMENT_RUNTIME.md; coordination/handoffs/IDX-STAGE3-DEVELOPMENT-RUNTIME.md
findings: Full pytest 184 passed, 0 failed. Admission passed with panel hash 67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76, manifest hash b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a, manifest valid 15/15, max signal 942, max future source 962, and holdout_outcome_accessed=false. Full valid rows 712325; history-qualified 692648; primary broad-liquid 244761; H10 resolved binary rows 208375. H10: TP_FIRST 197910, SL_FIRST 315049, AMBIGUOUS_SAME_BAR 6974, NO_BARRIER_HIT 107189, UNRESOLVED_PATH 40463, INVALID_BARRIER 44740, UNRESOLVED_HORIZON_END 0.
decisions_made: The frozen advancement rule is met: logistic_compact beats base_rate and momentum_20 on F2/F3; hist_gradient_boosting beats both on F1/F2/F3. This is development OOF evidence only. Pooled PR-AUC is logistic 0.364646 and HGB 0.374347; pooled Brier/ECE are not uniformly better than base-rate.
decisions_needed: Independent ChatGPT review must decide whether this development evidence supports a separately scoped next phase. No Stage 4 or holdout action is authorized by this handoff.
blocking_risks: Strict execution-grade 1260 remains FAIL. Development OOF is not final OOS. Calibration quality is weaker than base-rate on pooled Brier/ECE for challengers, and HGB/logistic fold calibration drift is visible in F3. No claim of execution PnL is valid because Open remains nullable.
validation_run: `python -m pytest` -> 184 passed, 0 failed; runner exit code 0; all 15 runtime artifact hashes matched; `holdout_outcome_accessed=false`; no source/runtime artifacts added to Git.
recommended_next_action: Review `docs/checkpoints/2026-08-09_STAGE3_DEVELOPMENT_RUNTIME.md` and the external runtime artifacts. Do not inspect holdout outcomes, tune V1, start Stage 4, run IDX-VAL-002, or merge to main.
