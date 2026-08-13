# Stage 5 Independent Review — Ranking V1 Rejected

Date: 2026-08-09 (Asia/Jakarta)
Branch reviewed: `research/idx-stage5-ranking-holdout-v1`
Runtime code commit: `05c2bb549b446da374c13937a41aa6732cf71ec0`
Runtime result checkpoint: `docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md`
Runtime summary SHA-256: `1a38171eead5a9c72de62da4f6ef486f35e3fba2e962c3b0bccac9fea033acd0`

## Independent decision

**RANKING V1 IS REJECTED AS A GENERALIZABLE HOLDOUT-PASSED ARCHITECTURE.**

The automatic `STAGE5_RANKING_HOLDOUT_FAIL` is accepted. The frozen gate must not be relaxed post hoc and the consumed holdout must not be rerun.

This is a research failure, not a runtime/provenance failure. The Stage-5 execution was procedurally valid: exact environment and frozen input hashes matched, the manifest verified 15/15, 206 tests passed, final development models were serialized and hashed before holdout label access, and the one-shot markers were written before outcome access.

## Evidence interpretation

Primary H10 holdout:

- resolved rows: 71,420;
- prevalence/base PR-AUC: `0.4071688603`;
- HGB PR-AUC: `0.4073793720`;
- HGB delta vs base: only `+0.0002105118`;
- HGB ROC-AUC: `0.4948433255`;
- overall Q5-Q1: `+0.0108405246`;
- top-decile lift vs overall prevalence: `+0.0251666343`.

The small positive PR-AUC delta and positive extreme-tail enrichment are not sufficient to rescue V1 because the preregistered overall ROC gate failed and temporal behavior reversed.

Temporal halves:

- HOLDOUT_A: prevalence `0.4647456292`, PR-AUC `0.4866372564`, delta vs base `+0.0218916273`, ROC-AUC `0.5186811460`, Q5-Q1 `+0.0464755652`;
- HOLDOUT_B: prevalence `0.3577062238`, PR-AUC `0.3471254020`, delta vs base `-0.0105808218`, ROC-AUC `0.4810497816`, Q5-Q1 `-0.0198933303`.

This is not merely a lower base-rate period. In HOLDOUT_B the ranking diagnostics themselves reversed: PR-AUC fell below prevalence, ROC-AUC fell below 0.5, and Q5-Q1 became negative. The current evidence therefore does not support a stable V1 ranking edge across the locked period.

Sensitivity does not provide a rescue:

- H5: PR-AUC delta vs base `+0.0040738886`, ROC-AUC `0.5003881183`;
- H20: PR-AUC delta vs base `+0.0016666710`, ROC-AUC `0.4958467114`.

H5/H20 were sensitivity-only by preregistration and are in any case near-null on the frozen score.

## What may still be learned

The result contains a bounded post-hoc hypothesis, not a validated claim: HOLDOUT_A and the overall top decile suggest that the frozen features may contain conditional or extreme-tail information that is not temporally stable. Possible explanations include feature/outcome relationship drift, market-regime dependence, cross-sectional normalization issues, or development overfit. None is established by the current aggregate artifacts.

A post-mortem may inspect the consumed holdout for diagnosis and V2 hypothesis generation, but any such use permanently makes those outcomes research data. No V2 may claim independent validation on this holdout.

## Authorization boundary after review

Do not:

- rerun Stage 5;
- tune or relabel V1 against the consumed holdout and call it validated;
- continue Probability V1 calibration rescue;
- start the previously defined Stage 6 as if V1 passed;
- make execution-PnL, paper-trading, or live-trading claims;
- run `IDX-VAL-002`;
- merge to `main`.

Authorized next scope is only a **bounded Stage-5 post-mortem / V2 research-design phase**. It should first diagnose why HOLDOUT_A and HOLDOUT_B diverged, with frozen descriptive analyses rather than an optimizer/search loop.

High-priority V2 hypotheses to evaluate in development research include:

1. cross-sectional/date-relative feature normalization and explicit market/sector relative-strength features;
2. explicit regime features or a predeclared regime-conditional architecture, because the feature-outcome relationship appears temporally unstable;
3. a ranking-native objective grouped by signal date rather than relying only on pooled binary classification;
4. stronger but causal support/resistance and market-structure representations;
5. a selective top-tail objective as a separately preregistered hypothesis, because overall top-decile enrichment survived while broad ranking did not.

These are hypotheses only. They must not be selected by repeatedly scoring alternatives on the consumed Stage-5 holdout.

## Future validation rule

Ranking V1 remains preserved as a failed benchmark. A redesigned Ranking V2 and any future Probability V2 require a fresh forward evaluation period strictly after `2026-07-31`. The consumed 2025-07-15..2026-07-31 holdout may be used for diagnosis/development only after this review, never again as independent evidence.

Probability V1 remains:

`PROBABILITY_V1_NOT_READY_DEFERRED`
