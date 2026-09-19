# Alpha Archaeology Result V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Scope: read-only reconstruction from committed checkpoints, tombstones, and
historical source refs; no new target/outcome access

## Reading rule

This map separates the original experiment verdict from later integrity/PIT
adjudication. A historical result can be valid for the exact run that produced
it while later source or contamination review changes whether it remains a
trusted parent. No historical result below authorizes a new run or a rescue.

## Ranking V1 and V2

| Family | What was tested | Durable result | Failure class / scope |
|---|---|---|---|
| Early Stage 3/4/4B/5 Ranking V1 | Early HGB ranking/probability/calibration chain with a locked temporal holdout | Development ranking evidence was useful, but the locked Stage-5 holdout failed its preregistered gate; probability calibration was not production-ready | `OOS_FAIL` / `MODEL_FAIL`; does not reject all ranking or all HGB mechanisms |
| Ranking V2 | Logistic XS, HGB XS, HGB XS Market, and pairwise logistic candidates; durable control `HGB_XS_MARKET` | HGB_XS_MARKET became the clean historical parent/control; feature family includes causal cross-sectional price/volatility/participation, market context, and market-relative transforms | `KEEP_CONTROL`; not a new alpha survivor by itself |

The V2 source map identifies `research_v2_features.py` and
`research_v2_models.py` on `origin/research/idx-ranking-v2-spec-v1`. The V2
feature contract explicitly excludes open dependency and computes same-date
cross-sectional ranks and market context causally.

## V3 family map

| ID | Hypothesis / representation | Evidence | Latest interpretation |
|---|---|---|---|
| V3-A | Recency decay, H=252 and H=504 | Both failed paired promotion against exact V2 control | `STRUCTURALLY_REJECTED` for the tested recency representations; no rescue |
| V3-B | Structure-Lite: V2 plus fixed eight-feature causal geometry bundle | Initial F1–F4 review showed positive paired PR deltas on all four folds and promoted the bundle for the next step; later clean PIT-safe adjudication found KOCI pre-listing contamination and a failed frozen late paired gate | Historical initial `REPRESENTATION_PASS`; latest trusted lineage `PIT_FAIL / OOS_FAIL`; clean V2 restored as survivor |
| V3-C | Explicit NORMAL/STRESS two-expert regime specialization | Control equivalence passed; candidate absolute sanity passed; overall paired and regime gates failed. Overall median PR change about `-0.012317`, STRESS about `-0.028965` | `STRUCTURALLY_REJECTED` for sample-fragmenting regime specialization; regime state remains useful as a diagnostic partition |
| V3-D | V2 plus six PIT sector-relative features | Blocked before cache/score because no immutable ticker-by-date historical IDX-IC source with effective and available-at semantics was admitted | `BLOCKED_SOURCE_ADMISSION`; does not reject sector-relative mechanisms |
| V3-E | Exact V2 25 features plus frozen XGBoost LambdaMART same-date ranker | Dependency `xgboost==3.2.1` first blocked pre-outcome; corrected pre-outcome to `3.2.0`; control equivalence passed, candidate absolute sanity passed, paired promotion failed | `MODEL_FAIL / OOS_FAIL`; keep V2 control, no rescue |

V3 ordinals `001–011` were historically accounted for as documented; V3-D
ordinals `008/009` remained unviewed because the PIT sector gate blocked before
outcome materialization. These are historical-development results, not current
protected evaluation.

## V4 family map

The original V4 design arena contained seven bounded families: participation
quality, price-path quality, cross-sectional context, peer/sector relative
strength, systematic-adjusted/idiosyncratic strength, catalyst/fundamental
context, and flow/ownership information. Only the first three received the
documented first-pass historical-development run.

| Family | Fixed experiment | Result | Latest classification |
|---|---|---|---|
| V4-A Participation Quality / Price Impact | A1 Impact/Absorption ordinal 013; A2 Persistent Directional Participation ordinal 014; exact control ordinal 012 | Control equivalence passed; A1 and A2 failed paired promotion gates; no survivors or integration | `OOS_FAIL` for exact representations; participation family not universally closed |
| V4-B Price-Path Quality | B1 Path Coherence/Jump Concentration ordinal 016; B2 Range Acceptance/Rejection ordinal 017; exact control ordinal 015 | Control equivalence passed; both challengers failed unchanged gates; no B1+B2 integration | `OOS_FAIL` for exact representations |
| V4-C Cross-Sectional Opportunity Context | Four-feature opportunity-dispersion ordinal 019; exact control ordinal 018 | Control equivalence passed; ordinal 019 failed unchanged paired/regime gates; no cross-family integration | `OOS_FAIL` for exact representation |
| V4-D Peer/Sector Relative Strength | Conditional on PIT sector history | Not admitted because sector history remained blocked | `BLOCKED_SOURCE_ADMISSION`; not a mechanism rejection |
| V4-E Systematic-adjusted/idiosyncratic strength | Later available-data lane produced C1/C4-style structural candidates, but no admitted target comparison | Structural only | `FUTURE_RESEARCH` pending target admission and incumbent overlap |
| V4-F Catalyst/Fundamental Context | Financial event/quality representations | Exact Financial Event V1 failed/flat; C3 is a separate fixed quality/growth capability candidate | Exact event `OOS_FAIL`; broader family `BLOCKED/UNTESTED` |
| V4-G Flow/Ownership | Foreign-flow and ownership/free-float work | Source/PIT admission partial or blocked; exact Foreign Flow V2 additive H10 failed | Exact additive representation `OOS_FAIL`; broader family `UNTESTED/BLOCKED` |

The V4-A/B/C first-pass checkpoint records all eight viewed/control ordinals
and confirms no rescue, integration, fresh-forward access, or production
mutation.

## V4-X1 and O2 lineage

- V4-X1 Clean is the current frozen incumbent alpha lineage in canonical
  coordination. It must remain untouched by this lane.
- O2/OOHLV geometry experiments were diagnostic/auxiliary and later became an
  orphaned or superseded parent after clean PIT adjudication. O2.1 flat-range
  work is also historical diagnostic evidence, not a new incumbent.
- The clean V2/V3-B/O2 reproduction lane is the controlling source for the
  contamination lesson: causal feature lineage outranks an attractive
  historical headline metric.

## Auxiliary and adjacent research

| Direction | Result | What it does not prove |
|---|---|---|
| Expected Payoff | No survivor; approximately `0/6` positive folds and negative median MSE skill in the tombstone | Does not reject ranking alpha or all payoff formulations |
| Reliability | `score_margin_reliability` was a limited historical survivor; other constructions were not justified as mandatory decision layers | Does not establish a second predictive model |
| Path Risk | No production-ready model | Does not reject path features as alpha/context |
| Decision V1/V2/V3/V4 | Decision V2 retained as incumbent; other policies were economically/structurally worse or underfilled | Decision policy evidence is not alpha-family evidence |
| Historical Open recovery | Yahoo/Zapi/TradingView/Investing substitutions failed exact semantic/coverage/PIT gates | Does not prove no future certified execution-price source can exist |
| Historical universe | No complete bounded historical universe was certified | Does not reject all universe research; it blocks claims requiring lifecycle completeness |

## Mechanism-level lessons

1. Clean PIT lineage dominates model complexity: contamination can reverse a
   historical apparent win.
2. A single additive feature-block failure rejects that exact block/target/model
   role, not the whole information family.
3. Explicit regime specialization can fragment support and amplify stress-state
   degradation even when aggregate absolute sanity passes.
4. V3-B/V4 experiments show that ranking separation and top-decile behavior can
   diverge; top-ranked membership diagnostics must remain visible.
5. Sector, financial, foreign-flow, ownership, and corporate-action families
   require source admission before another fair comparison.
6. Structural diagnostics should precede model fitting; this is why the current
   C1–C4 program keeps target-free coverage, redundancy, robustness, and
   economics work separate from future evaluation.

## Unresolved archaeology

- Exact V4-D/E/F/G candidate implementations are not all present in the active
  worktree; some were tombstoned or retained only as historical references.
- V3-B initial promotion and later PIT-safe rejection are both recorded; the
  later integrity adjudication controls current trust.
- Some old family names (V4-A/B/C) are historical labels and should not be
  reused for new candidates without a new hypothesis card and novelty gate.

## Source references

- `docs/repository_hygiene/EXPERIMENT_TOMBSTONES_V2.md`
- `docs/repository_hygiene/RETAINED_LINEAGE_V2.md`
- `docs/checkpoints/2026-08-26_CLOSED_ALPHA_FAMILY_REEVALUATION.md`
- `docs/checkpoints/2026-08-26_ALPHA_FRONTIER_RESEARCH_V1_BOOTSTRAP.md`
- historical `docs/checkpoints/2026-08-10_RANKING_V3_*` and
  `docs/checkpoints/2026-08-10_RANKING_V4_*` records in retained Git history
- `origin/research/idx-ranking-v2-spec-v1:src/idx_trade/research_v2_models.py`
- `origin/research/idx-ranking-v2-spec-v1:src/idx_trade/research_v2_features.py`
- `origin/research/idx-ranking-v2-spec-v1:src/idx_trade/ranking_v3_structure_lite.py`

