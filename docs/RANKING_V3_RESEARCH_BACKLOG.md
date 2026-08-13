# Ranking V3 Research Backlog

Date: 2026-08-10 (Asia/Jakarta)
Status: **IDEA BACKLOG ONLY — NOT AUTHORIZATION TO RUN V3 OUTCOMES**

## Controlling roadmap

The detailed and current V3 research ordering/governance is frozen in:

`docs/RANKING_V3_ROADMAP_AUDIT_V1.md`

That audit supersedes the earlier backlog ordering after review of the frozen V2 result and the private legacy Indonesian-stock model archive.

Mandatory first-reads before any V3 specification or implementation:

- `docs/CURRENT_STATUS.md`;
- `docs/RANKING_V3_ROADMAP_AUDIT_V1.md`;
- `docs/RANKING_V3_LEGACY_MODEL_LESSONS.md`;
- `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md`;
- newest controlling checkpoint/specification.

The legacy archive is hypothesis/failure evidence only. Its old scores are not promotion evidence for `idx-trade`.

## V2/V3 separation

V2 remains a separate frozen forward-validation track. V3 R&D may proceed asynchronously using only already-authorized development knowledge through `2026-07-31` and must not inspect or react to reserved V2 fresh-forward outcomes.

If V2 forward outcomes are learned and used to alter V3 before V3 is frozen, those outcomes become V3 development knowledge and cannot be V3 independent validation.

## Audited V3 hypothesis ladder

### V3-Control

Exact frozen V2 `HGB_XS_MARKET` semantics. Every V3 experiment must compare against the real V2 champion on identical eligible development rows/folds.

### Priority 1 — V3-A RECENCY

Question: does reducing older training-row influence improve robustness under temporal drift?

Keep H10, universe, exact 25 V2 features, HGB architecture/hyperparameters, scoring, and metrics fixed. Change only deterministic fit-row sample weights. Use uniform control plus at most two predeclared recency variants. No half-life sweep after seeing outcomes.

### Priority 2 — V3-B STRUCTURE-LITE

Question: does compact causal support/resistance/price geometry add information beyond V2's existing high/low distances and range position?

Possible future compact bundle: prior-only touch density, level age/recency, role reversal, breakout/retest state, volume confirmation, and compression. Do not port legacy outcome-conditioned setup buckets, ticker-specific backtest overlays, adaptive horizon weights, or hand-tuned score bonuses.

### Priority 3 — V3-C REGIME-SPECIALIZATION

Question: after V2 already includes market context and nonlinear HGB interactions, does explicit conditional specialization still improve worst-regime/worst-fold behavior?

Use only a small causal state definition and one bounded specialist formulation. No broad macro feature soup or threshold grid.

### Priority 4 — V3-D SECTOR-RELATIVE

Question: does within-sector relative strength add incremental edge beyond whole-market context?

Blocked on a point-in-time historical sector-membership data gate. Sector infrastructure may be built asynchronously, but no sector model outcome run is allowed until provenance/effective-date/history coverage passes.

### Priority 5 — V3-E TRUE-RANKING

Question: does one tightly bounded nonlinear same-date ranking objective beat binary HGB scoring?

Lower priority because current pairwise-linear V2 did not win and an older downside-ranking experiment also failed its historical champion. No ranking-library/model tournament.

## Separate later lanes

- **Distribution/uncertainty:** U1-style q10/q50/q90 may become a separate uncertainty/tail layer, not a first-pass V3 ranker feature.
- **Path risk:** V4-style MAE/MFE/path modeling may become a risk/veto/geometry layer, not a replacement opportunity target.
- **Broker flow / EventRank / fundamentals / macro expansion:** require separate point-in-time availability, revision, coverage, and provenance gates before model use.

## Research discipline

Use one falsifiable hypothesis per experiment. Normally allow one exact V2 control plus at most two bounded variants. Maintain a permanent hypothesis ledger with every viewed candidate; failed candidates are never erased from the research denominator.

Use robustness-first diagnostics: median/q25/worst-fold PR-AUC delta, positive-fold count, ROC stability, Q5-Q1 stability, top-decile lift, late-fold behavior, and incremental-selection quality where applicable.

Do not rebuild the legacy monster by automatically stacking every surviving idea. After Tier-1 screening, at most one preregistered integration experiment may compare the best single surviving component versus one combined candidate. Prefer the simpler architecture when practically tied.

The audited default development process reserves the latest development folds from repeated candidate iteration: use earlier folds for bounded discovery, then one frozen final V3 architecture may receive a one-shot **late-development confirmation** on the reserved later folds. This remains development evidence, never independent validation.

## Runtime requirement

Before V3 implementation, read `docs/NEXT_MODEL_RUNTIME_OPTIMIZATION_NOTES.md` and explicitly report that it was read. Prefer one deterministic Python orchestrator with bounded workers; do not use many Codex chats as the compute scheduler by default. Any performance optimization must prove semantic equivalence before outcome-bearing use.

## Next V3 task

The next V3 task is **specification only**:

`RANKING_V3_RECENCY_SPEC_V1`

It must freeze the discovery folds, exact control, at most two recency variants, sample-weight formula/normalization, metrics, robustness gates, promotion/kill rule, hypothesis-ledger identity, runtime/provenance, and the prohibition on reserved V2 forward outcomes.

Only after review of that frozen spec may Codex be authorized to implement and run V3-A scores.
