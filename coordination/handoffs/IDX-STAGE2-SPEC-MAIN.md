# Handoff
from: EXPERIMENT / VALIDATION
to: MAIN
task_id: IDX-STAGE2-SPEC
model_used: GPT-5 Codex; independent read-only adversarial review pass
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: 057d7c2df57ebe259f8b93642128e91ad294b146
branch: data/idx-data-002c
head_commit: pending documentation commit
scope: Freeze Stage-2 research question, signal timing, label family, universe, temporal validation, purge/embargo, metrics, baselines, calibration, and leakage threat model.
files_changed: docs/RESEARCH_SPECIFICATION_V1.md; docs/VALIDATION_PLAN_V1.md; docs/VALIDATION_THREAT_MODEL_V1.md; docs/checkpoints/2026-08-09_STAGE2_RESEARCH_SPECIFICATION.md; docs/PROJECT_CONTEXT_MASTER.md; docs/PROJECT_LEDGER.md; coordination/handoffs/IDX-STAGE2-SPEC-MAIN.md
findings: The immutable SIGNAL_RESEARCH_HLCV input remains 981,940 ACTIVE rows over the exact 1,260-session window. The primary signal question is causal post-close structure versus a bounded future excursion. The primary label is H=10 first-touch barrier with ATR14, k_sl=1.0, and RR=1.5; H=5/H=20 are bounded sensitivities. Open is not required or synthesized.
decisions_made: Freeze SIGNAL_REFERENCE_CLOSE as a label reference, not a fill. Keep AMBIGUOUS_SAME_BAR, NO_BARRIER_HIT, and UNRESOLVED_PATH explicit. Use the broad causal liquid universe and exact development/holdout/fold contract documented in the specification. Preserve separate Probability, Opportunity Score, and Estimate Reliability semantics.
decisions_needed: MAIN must separately approve Stage 3 implementation before any label/feature code, model, calibration fit, or holdout read.
blocking_risks: Strict execution-grade 1260 remains FAIL and must not be silently replaced by the signal layer. The final 20 holdout sessions cannot receive complete H=20 labels within the immutable panel and remain a declared horizon-end buffer.
validation_run: Independent read-only adversarial review found no material unresolved issue after a fold-boundary consistency correction. Documentation diff check clean. Existing full pytest after the last executable change: 157 passed, 0 failed, three pre-existing pandas warnings.
recommended_next_action: Review this handoff and the three Stage-2 documents, then issue a separate Stage 3 authorization if desired. Do not inspect holdout outcomes or begin modelling from this handoff.
