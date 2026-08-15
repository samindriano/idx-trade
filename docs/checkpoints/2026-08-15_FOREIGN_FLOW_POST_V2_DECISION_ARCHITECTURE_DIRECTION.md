# Foreign Flow Post-V2 — Decision Architecture Direction

Date: 2026-08-15 (Asia/Jakarta)
Status: `DIRECTION_RECORDED_NO_NEW_ALPHA_AUTHORIZATION`
Scope: documentation-only research direction after accepted Foreign Flow V2 Core `NO_SURVIVOR`.

## Context

Foreign Flow V1 and the preregistered Foreign Flow V2 Core experiment both failed to demonstrate incremental H10 PR-AUC alpha versus the accepted Clean V2 `HGB_XS_MARKET` control. V2 Core is therefore closed as an exact alpha hypothesis; it must not be rescued by post-result feature deletion, alternate windows, threshold search, clipping, or a V3/V4 sequence over the same historical folds.

The accepted V2 representation artifact remains useful as a causal descriptive/state artifact. Its failure as a universal direct H10 challenger does not prove that foreign flow has no trading value in every decision role.

## Architectural principle

Do not attempt to reproduce a discretionary trader by feeding every available signal into one monolithic classifier. Separate the trading process into modules with distinct responsibilities:

1. **Structural context** — effective tradable supply / ownership concentration, liquidity, security age, and other slow-moving state.
2. **Demand / accumulation state** — foreign accumulation/distribution, abnormal participation, persistence, cross-sectional preference, and flow-price divergence.
3. **Price state** — downtrend, basing, early reversal, established uptrend, extended/late state.
4. **Confirmation state** — higher-low / swing break, volume expansion, improving short/medium trend structure, and other event-like confirmation.
5. **Ranking / alpha** — rank eligible candidates rather than force every ticker-session into an entry decision.
6. **Risk / execution** — liquidity, gap/supply risk, volatility, sizing, portfolio exposure, and invalidation.

The intended pipeline is conceptually:

`Structural Context -> Accumulation State -> Price State -> Confirmation -> Ranking -> Risk/Execution`

This is closer to systematic discretionary reasoning than a single `all-features -> H10 classifier` design.

## Foreign Flow role after V2

Foreign Flow should no longer be treated by default as a universal additive alpha block for Clean V2.

The preferred role is a **state/setup signal**:

- `DISTRIBUTION`
- `NEUTRAL`
- `ACCUMULATION`
- optionally a stronger/extreme accumulation state if a threshold is fixed outcome-blind

A stock can therefore be classified as, for example:

`ACCUMULATION + DOWNTREND -> WATCH`

rather than being forced into an immediate BUY/SELL label.

Then a separate causal confirmation layer can move the state toward:

`ACCUMULATION + BASING + CONFIRMED_REVERSAL -> ENTRY_ELIGIBLE`

The exact definitions and thresholds are **not frozen here** and must not be chosen from the already-observed V1/V2 outcome folds.

## Scientific boundaries

1. `FOREIGN_FLOW_V2_CORE_NO_SURVIVOR` remains final for the exact eight-feature H10 challenger.
2. Do not inspect feature importance or individual fold behavior to construct a post-hoc V2.1/V3 rescue on the same historical folds.
3. Historical V1/V2 folds are now a development laboratory, not independent confirmation data for future Foreign Flow hypotheses.
4. Any new state-machine / confirmation architecture derived after seeing V2 outcomes requires fresh/prospective validation or a separately protected unseen period.
5. Existing Foreign Flow prospective sidecars may continue as outcome-blind evidence collection; do not create a second forward counter or inspect protected outcomes.

## One previously established exception: PIT supply extension

A supply-adjusted Foreign Flow hypothesis remains scientifically legitimate because the need for PIT free-float / effective-supply information was recorded before the V2 Core outcome was observed.

However, the current Free Float / Effective Supply source lane is not model-ready. The latest bounded audit is `SOURCE_REMEDIATION_REQUIRED`: current IDX Company Profile rows do not expose an explicit reported-free-float field, verified KSEI `BalanceposEfek` artifacts are aggregate holding-composition data, and the official monthly >=1% ownership attachment has not yet been recovered reliably.

Therefore:

- no supply-adjusted Foreign Flow model is authorized yet;
- do not invent an exact free-float denominator;
- finish PIT source remediation first;
- if a defensible historical supply/concentration state becomes available, freeze **one** supply-extension hypothesis before outcome access;
- after that one historical supply experiment, stop iterative Foreign Flow historical tuning on the same folds.

## Preferred next Foreign Flow research paths

### A. Outcome-blind monitoring / descriptive state

Retain the existing accepted Foreign Flow V2 representation as a monitoring sidecar. For each eligible ticker/session, expose causal descriptive fields such as:

- recent net foreign flow / participation;
- own-history abnormality percentile;
- cross-sectional foreign-flow rank;
- persistence / acceleration;
- flow-price divergence;
- missingness / source status;
- later, PIT supply-tightness context if and only if source-safe.

This path creates useful trader context without claiming direct predictive alpha.

### B. Supply-adjusted extension

Only after PIT supply data passes source/provenance/coverage gates, consider a small preregistered family such as:

- foreign net demand relative to defensible PIT tradable-supply shares;
- cross-sectional supply-adjusted foreign pressure;
- interaction of abnormal foreign-flow pressure with a frozen supply-tightness state.

Exact formulas must follow the source semantics that are actually available. Do not choose formulas based on V2 fold performance.

### C. Prospective setup/confirmation study

Separately from H10 alpha tuning, define an outcome-blind Foreign Flow setup state and capture it prospectively alongside price-state / confirmation variables. Examples of states to freeze before evaluation:

- accumulation while price remains in downtrend;
- accumulation during basing;
- accumulation plus first causal reversal confirmation;
- distribution while price is extended.

The objective would be to test whether foreign flow is useful as a **conditional setup/context variable**, not whether it improves every H10 observation directly.

This should use genuinely new prospective observations for confirmation because the architecture is being articulated after seeing V2 historical results.

## Stop rule

The recommended Foreign Flow historical research budget from this point is:

1. no V2 rescue;
2. complete PIT supply source remediation;
3. at most one previously-hypothesized supply-adjusted historical experiment if the data become defensible;
4. then stop historical Foreign Flow iteration on the reused six-fold development regime;
5. pursue any richer state/confirmation architecture prospectively.

If PIT supply remediation fails, close the historical Foreign Flow H10 family and retain Foreign Flow only as descriptive/prospective context until genuinely new evidence is accumulated.

## Final direction

`FOREIGN_FLOW_DIRECT_H10_ALPHA_CORE_CLOSED`

`FOREIGN_FLOW_STATE_CONTEXT_RESEARCH_RETAINED`

`SUPPLY_ADJUSTED_EXTENSION_WAITING_FOR_PIT_SOURCE_REMEDIATION`

`POST_V2_STATE_MACHINE_CONFIRMATION_RESEARCH_PROSPECTIVE_ONLY`
