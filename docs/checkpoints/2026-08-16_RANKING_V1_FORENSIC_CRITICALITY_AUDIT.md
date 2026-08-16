# Ranking V1 Forensic Criticality Audit

Date: 2026-08-16 (Asia/Jakarta)
Branch: `research/idx-ranking-v1-forensic-audit-v1`
Base main: `617216a5268dac9329aa66f2389c054d4392bfce`
Status: `FORENSIC_REVIEW_ONLY_NO_NEW_EXPERIMENT`

## Scope

This checkpoint records the second-pass adversarial audit of Ranking V1 before any V2 audit begins. It does not modify V1, reopen its consumed holdout, fit a model, access protected/fresh-forward outcomes, call a provider, or authorize a rescue experiment.

Primary historical sources reviewed:

- `docs/RESEARCH_SPECIFICATION_V1.md`
- `docs/STAGE3_IMPLEMENTATION_PLAN_V1.md`
- `docs/checkpoints/2026-08-09_STAGE3_DEVELOPMENT_RUNTIME.md`
- `docs/checkpoints/2026-08-09_STAGE4_DEVELOPMENT_RUNTIME.md`
- `docs/checkpoints/2026-08-09_STAGE5_RANKING_HOLDOUT_RUNTIME.md`
- `docs/checkpoints/2026-08-09_STAGE5_POSTMORTEM_INTERPRETATION.md`
- `docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md`
- `docs/checkpoints/2026-08-09_SIGNAL_RESEARCH_1260_GO.md`

The live repository coordination ledger on `main` was inspected before this note. No active lane owns a V1 forensic design audit; all existing V1/Probability/Path-Risk/O2 restrictions remain unchanged.

## Historical facts that control this audit

1. V1 was built on `SIGNAL_RESEARCH_HLCV`, not a full execution-grade OHLCV contract.
2. The materialized V1 research panel had 981,940 ACTIVE rows and 446,843 null Open values (45.5061%). Open-dependent primary features were explicitly prohibited.
3. Primary V1 target was H10 fixed first-touch barrier classification referenced to `Close_t`: TP +1.5 ATR14 versus SL -1.0 ATR14. Only `TP_FIRST` and `SL_FIRST` formed the binary calibration/model target; no-touch/ambiguous/unresolved states remained outside that binary denominator.
4. V1 used a row-wise binary HGB classifier. Daily within-date ranking was an evaluation diagnostic, not the fitted objective.
5. Development evidence was strong enough to advance, but the one-shot locked holdout failed: HGB PR-AUC only +0.0002105 over base overall, ROC-AUC 0.49484, with HOLDOUT_B negative PR delta and negative Q5-Q1.
6. The historical post-mortem supported a regime/covariate-shift hypothesis but explicitly did not establish a causal explanation.

## Criticality ranking

### P0 — architecture-invalidating questions

#### P0.1 Target/estimand selection: `TP_FIRST vs SL_FIRST | future-resolved`

**Current answer:** This target is scientifically valid for the narrow question V1 asked, but it is not obviously the correct estimand for the product. Conditioning the binary model on future-resolved first-touch outcomes excludes `NO_BARRIER_HIT` observations even though sideways/non-opportunity cases matter for daily stock selection. The probability being learned is closer to `P(TP first | one barrier resolves, V1 eligibility)` than `P(best opportunity today | eligible universe)`.

**Why critical:** If the estimand is wrong, adding better features to V1 cannot fix the core decision problem.

**Required remediation before a new-generation ranker:** Re-specify the target family before outcomes are inspected. Candidate directions should preserve all economically relevant future states or directly define a rankable future utility. Any new target must explicitly account for no-touch, ambiguity, executable entry timing, and magnitude/risk information. Do not rescue V1 by simply relabelling old outcomes after observing results.

#### P0.2 Tradability mismatch: `Close_t` label reference versus executable `t+1` entry

**Current answer:** V1 explicitly treated `Close_t` as a signal-reference price, not a fill. Therefore V1 never established that its ranking survives the overnight gap or remains actionable at next-session execution. With historical Open largely unavailable when V1 was frozen, this question could not be answered properly.

**Why critical:** A ranking edge that disappears between `Close_t` and executable `Open_(t+1)` is not a usable swing-entry edge.

**Required remediation:** A future target/validation contract should separate (a) information cutoff at close t, (b) next-session executable entry semantics, and (c) subsequent path/outcome. The exact Open source and market-session semantics must be separately certified; missing Open must fail closed rather than be synthesized.

#### P0.3 Objective mismatch: row-wise binary classification versus daily cross-sectional ranking

**Current answer:** The mismatch is real. V1 fitted `TP_FIRST/SL_FIRST` per row and only afterwards evaluated within-date quintile/decile ordering. The product decision is inherently grouped by decision session: choose the best names among contemporaneous alternatives.

**Why critical:** A model can improve global classification while being suboptimal for daily relative ordering, and row-count/date-composition changes can alter implicit training weights.

**Required remediation:** A new-generation design must explicitly compare at least one session-grouped/ranking-aware objective or weighting scheme against a clean classifier control. Daily decision dates, not raw row counts alone, should have deliberate weighting semantics. This must be preregistered; legacy LambdaMART/Ranking V3-E evidence must be audited before reusing any ranking-native family.

#### P0.4 Label geometry may measure barrier mechanics rather than economic opportunity

**Current answer:** V1 used ATR both to define target barriers and to normalize several structure features. This is not leakage, but it creates a plausible mechanism by which the model predicts fixed-ATR first-touch geometry rather than a broader risk-adjusted economic opportunity. Fixed 1.0/1.5 ATR geometry is disciplined but economically arbitrary across all stocks/regimes.

**Why critical:** Strong structure ablation evidence may partly reflect compatibility with the label construction, not portable alpha.

**Required remediation:** A future target audit must ask whether ordering survives across economically motivated outcome definitions rather than optimizing or tuning alternative ATR barriers on consumed outcomes. Magnitude and no-touch information should not be discarded by default.

### P1 — high-priority robustness/representation questions

#### P1.1 Regime invariance versus post-hoc regime explanation

**Current answer:** V1 clearly failed transportability in HOLDOUT_B. The old post-mortem showed large covariate shifts and preserved signs for some structure relationships, but it did not prove regime shift was the causal explanation. V1 should therefore be treated as non-robust, not as a model that merely needed one regime feature.

**Remediation:** Future promotion gates should include stability across dates/regimes, worst-fold/worst-block behavior, and breadth of alpha. Market-relative/cross-sectional representations can be tested, but no single regime story should be assumed ex ante.

#### P1.2 Semantic poverty of HLCV without Open/path information

**Current answer:** V1 could not distinguish materially different sessions that share similar H/L/C but begin at different Opens or follow different intraday paths. This is an information limitation, not proof that Open/intraday features will add alpha. Later simple Open additions failing means `add Open` is not a sufficient remediation.

**Remediation:** Treat Open and intraday path as distinct information classes. Only test economically defined representations after source admission. Do not append a broad Open feature zoo to V1.

#### P1.3 Volume/liquidity lacks economic denominators and actor context

**Current answer:** V1's `Volume / median20 Volume` and relative trading-value features are weak representations of participation. Equal raw/relative volume can have different meaning under different free float and foreign participation. This does not establish that foreign flow or free float is alpha; direct Foreign Flow V1/V2 appends later failed.

**Remediation:** Preserve hypotheses around interactions/normalization such as participation versus tradable supply and flow versus turnover/price acceptance, but only once PIT free-float state is admissible. Do not infer effective supply from unsupported arithmetic.

#### P1.4 Market-beta versus stock-selection alpha is not isolated

**Current answer:** V1 did not establish that its top-ranked names carry stock-specific alpha independent of contemporaneous market exposure. The later V1 post-mortem itself motivated market-relative representation.

**Remediation:** Future evaluation should explicitly report market-relative or cross-sectional outcome/ranking diagnostics and verify that performance is not concentrated in high-beta market phases. Historical market/index PIT readiness must remain respected; causal universe-derived context can be used only under its own frozen semantics.

#### P1.5 Breadth/concentration of alpha was under-gated

**Current answer:** Aggregate fold/quintile metrics do not prove that alpha is broad across tickers, eras, liquidity strata, sectors, listing cohorts, or event states. V1 holdout reversal demonstrates why aggregate development metrics were insufficient.

**Remediation:** Add preregistered concentration diagnostics and minimum breadth/stability gates. Do not optimize slices after seeing which ones perform.

### P2 — important but not first-order architecture blockers

#### P2.1 Source mixture/provider fingerprint risk

**Current answer:** The V1 panel mixed IDX Stock Summary and Yahoo raw HLCV. V1's panel-level contracts and provenance were adequate for that research stage, but the newer repository standard is stricter. Provider/era correlation with ticker quality or availability remains an unquantified risk.

**Remediation:** Any clean new-generation corpus should enforce current provenance/source-registry semantics and test source-consistency on overlaps. Do not reinterpret V1 holdout results as source-artifact proof without evidence.

#### P2.2 Security-age / observed-session time proxies

**Current answer:** These features can encode listing cohort/calendar time and were already flagged by the V1 post-mortem. They lack a strong standalone economic mechanism.

**Remediation:** Exclude from core by default or isolate as a separately justified lifecycle/IPO sensitivity family.

#### P2.3 Fixed 20/60 lookbacks and redundancy

**Current answer:** The windows were preregistered, which protects scientific integrity, but preregistration does not make them economically optimal. Structure/momentum families may also carry overlapping information.

**Remediation:** Do not tune many lookbacks on consumed outcomes. If a new representation uses multiple horizons, define a small mechanistic family before evaluation and assess incremental information with preregistered ablations.

#### P2.4 Corporate/event-state heterogeneity

**Current answer:** V1 verified split/reverse-split integrity but did not model broader event states. Some apparent nonstationarity may be unobserved event-state heterogeneity, but current corporate-action PIT coverage is not ready for a market-wide claim.

**Remediation:** Keep event-state integration separate until publication-time linkage is sufficiently complete. Do not block a core ranker solely waiting for this source.

#### P2.5 Intraday path can reduce ambiguity but is not yet historically admitted

**Current answer:** Intraday is a genuinely new information class and could resolve some path ambiguity, but current full-universe historical admission is not complete. It cannot be used retrospectively to rescue V1 today.

**Remediation:** Continue source admission independently; later test intraday as a separately frozen block/interaction against a clean core ranker.

## Direct answers to the key adversarial questions

- **Does V1 prove technical alpha is absent?** No. It proves the exact V1 target/representation/objective combination did not transport through the locked holdout.
- **Does V1 prove structure is robust alpha?** No. Structure contributed strongly inside V1 development, but that may be partly target-geometry-specific and did not rescue holdout transportability.
- **Was V1 invalid research?** No. It was disciplined enough that its failure is informative, but it is a failed benchmark rather than a deployable alpha model.
- **Should V1 simply be rebuilt with Open/Foreign/Free Float?** No. P0 target/objective/tradability questions must be resolved before feature expansion.
- **Should fixed ATR barriers be tuned now?** No. The old outcome window is consumed. Any new target family must be a new preregistered research question, not a V1 rescue.
- **Can current Foreign Flow/free-float/intraday/corporate-action data be treated as ready inputs?** No. Foreign historical data is usable under its accepted causality contract, but direct-alpha additions already failed; statutory free-float PIT history, corporate-action publication linkage, and full historical intraday corpus remain incomplete for unrestricted modeling.
- **What should survive from V1?** PIT/fail-closed discipline, temporal purge, explicit unresolved/ambiguous states, frozen hypotheses, and willingness to kill a model after locked-holdout failure.
- **What should not be inherited automatically?** The binary resolved-only target, Close_t pseudo-entry geometry, row-wise objective, fixed ATR barrier interpretation, age/time proxies, and HLCV-only representation.

## Priority order before any new clean-generation ranker

1. **P0 target/estimand contract** — define what the model should rank economically.
2. **P0 execution-timing contract** — define information cutoff and feasible next-session entry reference.
3. **P0 learning-objective contract** — align training with daily cross-sectional decisions and date weighting.
4. **P0 label-geometry robustness rationale** — avoid silently equating fixed ATR first-touch with alpha.
5. **P1 core representation** — market-relative/cross-sectional + richer clean daily price/volume semantics.
6. **P1 robustness gates** — worst-block, breadth/concentration, stock-specific versus market exposure.
7. **Only then add independently admissible new information blocks** — Foreign Flow interactions/state, free-float/supply when PIT-ready, intraday when corpus-ready, Financial PIT, Corporate Action state.

## Stop rule before V2 audit

Do not design or run a V1 rescue from this checkpoint. The next intended activity is a separate forensic audit of Ranking V2 using the same sequence: reconstruct what V2 changed, identify what it genuinely fixed, adversarially attack its assumptions, compare against data now available, rank unresolved critical questions, and record the findings before moving to V3/O2.
