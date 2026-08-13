# Clean V2 Open-Alpha Research Pass — V2.1 / V2.2

Date: 2026-08-13 (Asia/Jakarta)
Status: **RESEARCH_PASS_COMPLETE_OUTCOME_BLIND_NO_MODEL_FIT**
Owner: `ChatGPT/Open-Alpha-Research`
Branch: `research/idx-v2-open-alpha-research-pass-v1`

## Decision

Use the corrected clean V2 `HGB_XS_MARKET` as the control for one bounded Open-alpha remediation experiment with exactly two challengers:

1. **V2.1 — Direct O2 Geometry Repair**: clean V2 + the exact three previously frozen O2 Open-geometry features.
2. **V2.2 — Previous-Range Opening Displacement**: clean V2 + one new, compact three-feature family describing where the opening price lands relative to the previous PIT-valid ACTIVE bar's range.

Do **not** outcome-test a broad menu of Open variants and select the best afterward. This pass deliberately chooses the V2.2 family before any V2.2 historical fit/score is run.

No model was fit, no new historical metric was computed, no provider was called, and no fresh-forward outcome was accessed in this research pass.

## Current clean-lineage boundary

The PIT-safe replay now retains clean V2 and rejects clean V3-B. O2 remains useful as an Open-geometry diagnostic, but its old parent is rejected, so O2 cannot automatically propagate as the clean successor.

Therefore the appropriate remediation question is not "rescue V3-B/O2". It is:

> Starting from clean V2, does a small, preregistered Open-derived feature family add robust historical-development ranking value on exact common support?

Any accepted challenger must be evaluated against a fresh refit of **clean V2 on the exact same Open-ready rows**, not against the 292,631-row full-population V2 metrics.

## Repository audit: what has already been consumed

### Clean V2 control

V2's frozen `HGB_XS_MARKET` feature set contains 25 features:

- 10 within-date stock-state percentile ranks;
- 9 continuous market-state context features;
- 6 stock-minus-market relative features.

The existing V2 feature set already contains close-based range/location information such as `xs_rank_close_position_20`, `xs_rank_distance_high_20_atr`, and `xs_rank_distance_low_20_atr`. New Open features should therefore add a distinct opening-state representation rather than duplicate these close-based states.

### O1 is already consumed and must not become V2.2

The prior O1 historical experiment already outcome-tested these exact daily Open families on common support:

- `overnight_gap` only;
- `intraday_return` only;
- `overnight_gap + intraday_return` decomposition.

O1 ended `O1_NO_SURVIVOR`: all three failed the frozen lower-quartile paired-improvement gate. Consequently, simply rerunning close-to-open, open-to-close, their decomposition, or a lightly normalized version as the supposedly new V2.2 would be outcome-informed rescue behavior rather than a clean design choice.

### O2 geometry is already a known hypothesis

The frozen O2 family added exactly:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

This family was historically encouraging, including after PIT correction as an orphaned-parent diagnostic. That evidence justifies one direct-parent repair test, but V2.1 must be labelled as a **known remediation hypothesis**, not a novel blind discovery.

### O2.1 / intraday data boundary

The prior flat-range O2.1 historical challenger is closed `NO_SURVIVOR`. Stockbit intraday capture is prospective/shadow and does not have the historical depth required for an apples-to-apples V2 historical candidate. Opening-auction imbalance, first-5/15/30-minute, and order-book features are therefore out of scope for this pass.

## Literature review

The literature strongly supports treating the open as a distinct information/liquidity regime, but it does **not** establish one universal daily Open feature that should work on IDX.

Relevant evidence:

- Berkman, Koch, Tuttle & Zhang (2012), *Journal of Financial and Quantitative Analysis*, DOI `10.1017/S0022109012000270`: positive overnight moves can be followed by intraday reversal, with the opening price playing a central role and retail attention associated with temporary price pressure.
- Lou, Polk & Skouras (2019), *Journal of Financial Economics*, DOI `10.1016/j.jfineco.2019.03.011`: overnight and intraday return components show persistent but offsetting patterns, consistent with different investor clienteles.
- Lu, Malliaris & Qin (2023), *Journal of Financial Economics*, DOI `10.1016/j.jfineco.2023.03.002`: high information asymmetry around the open and heterogeneous liquidity provision can create temporary opening price deviations that attenuate intraday.
- Barardehi, Bogousslavsky & Muravyev (2026), *Review of Financial Studies*, DOI `10.1093/rfs/hhag036`: intraday and overnight components of past returns contain materially different information for momentum/reversal behavior.
- Plastun et al. (2020), *North American Journal of Economics and Finance*, DOI `10.1016/j.najef.2020.101177`: opening gaps are not universally "filled"; post-gap behavior can instead show temporary continuation.

These papers motivate using Open as a separate state variable. They do **not** directly validate the exact previous-high/previous-low formulation proposed below. That formulation is a low-degree-of-freedom engineering/economic representation chosen for PIT safety, novelty relative to consumed O1/O2 experiments, and availability from the project's existing daily OHLC data.

## Outcome-blind design-space ranking

| family | research rationale | project/data status | decision |
|---|---|---|---|
| Exact overnight / intraday decomposition | strongest direct literature | already outcome-tested as O1 and failed its frozen gate | **exclude from V2.2** |
| Same-day Open geometry | location of Open within realized H-L range | already known O2 hypothesis; positive diagnostic | **use only as V2.1** |
| Previous-range opening displacement | opening auction price vs prior accepted trading range | daily OHLC only; PIT-simple; not outcome-tested as an Open family in repo | **select for V2.2** |
| Cross-sectional / market-relative overnight gap | fits V2's relative-state philosophy | derives from already-consumed O1 overnight-gap signal; rescue risk | defer |
| Rolling overnight/intraday state / tug-of-war | strong literature | many lookback/design degrees and directly follows known O1 result | defer |
| Open vs rolling 20/60 support/resistance | plausible breakout state | overlaps the rejected clean V3-B/structure lane and adds lookback choices | defer |
| Opening auction / first-minute microstructure | strongest microstructure interpretation | historical canonical data unavailable; Stockbit only prospective/shadow | blocked for historical V2.2 |
| Global-market-to-IDX overnight transmission | plausible for Indonesian market | historical market/index PIT lineage not ready | blocked |

## Recommended V2.1 contract

Working identity:

`V2.1-CLEAN-V2-OPEN-GEOMETRY`

Control prefix: exact clean V2 `HGB_XS_MARKET` 25-feature order.

Append exactly, in the old O2 order:

1. `open_position = (Open_t - Low_t) / (High_t - Low_t)`;
2. `open_to_high = High_t / Open_t - 1`;
3. `open_to_low = Low_t / Open_t - 1`.

Total candidate features: **28**.

No interaction, rank, regime, threshold, alternate denominator, flat-range rescue, or feature mining is authorized by this research pass.

## Recommended V2.2 contract

Working identity:

`V2.2-CLEAN-V2-PREV-RANGE-OPEN-DISPLACEMENT`

Economic question:

> Does the opening auction place the stock inside, above, or below the price region accepted in its previous PIT-valid ACTIVE trading bar, conditional on the clean V2 state?

Let `prev` mean the immediately preceding **observed PIT-valid ACTIVE bar for the same ticker**. Do not forward-fill suspended/no-trade sessions and do not use a future/current-universe listing state.

Append exactly these three features:

1. `open_position_prev_active_range = (Open_t - Low_prev) / (High_prev - Low_prev)`;
2. `open_to_prev_high = High_prev / Open_t - 1`;
3. `open_to_prev_low = Low_prev / Open_t - 1`.

Total candidate features: **28**.

Semantics:

- the first feature distinguishes within-range versus above/below-range opening placement;
- the second and third preserve continuous scale-free distances from the prior range boundaries;
- if `High_prev == Low_prev`, `open_position_prev_active_range` is missing, never infinite; do not drop the row solely for this condition;
- non-positive/non-finite price inputs are invalid and must fail closed or produce explicit missing feature diagnostics according to the frozen cache contract;
- training-only imputation may handle legitimate feature missingness exactly as in the clean V2 model pipeline;
- persist `previous_active_session_index` and the session gap as **diagnostics only**, not model features, so long suspension gaps are visible without introducing another adaptive feature.

This formulation intentionally does not include `Close_prev`, `overnight_gap`, or `intraday_return`, avoiding a disguised rerun of the consumed O1 family.

## Required common-support and pre-outcome audit

Before either challenger can be scored:

1. materialize one corrected PIT-safe **Open-ready common-support table** from the clean V2 identities and accepted historical Open lineage;
2. refit the clean V2 control on those exact same row identities for every fold;
3. require exact feature-prefix preservation and same labels/folds/HGB parameters across control, V2.1 and V2.2;
4. run an outcome-blind cache audit only: row/ticker/date coverage, source/provenance hashes, missing/nonfinite rates, previous-active session-gap distribution, feature distributions, constants, and correlations with existing V2/Open features;
5. do not load `binary_target` during that blind audit;
6. freeze feature order, population hash, candidate identities, selection/survivor rule and no-rescue rule before outcome execution.

The exact common-support count must be **measured from the corrected lineage**, not copied from the old 278,168-row O1/O2 population. The corrected O2 replay currently indicates 278,166 rows, but V2.2's previous-bar availability/semantics still require a fresh outcome-blind cache audit before freezing the candidate population.

## Selection discipline

The eventual historical experiment should contain only:

- `CONTROL_CLEAN_V2_COMMON_SUPPORT`;
- `V2.1-CLEAN-V2-OPEN-GEOMETRY`;
- `V2.2-CLEAN-V2-PREV-RANGE-OPEN-DISPLACEMENT`.

No fourth candidate should be added after outcomes are opened. If both challengers fail, clean V2 remains the surviving historical architecture. If one or both pass, the preregistered paired rule must determine the winner; no post-hoc feature subset, interaction, lookback, normalization, or rescue is allowed.

## Research-pass boundary

This checkpoint is a **design recommendation only**. It does not authorize model fitting or outcome scoring yet. The clean PIT-safe replay/remediation lane must receive final independent acceptance, and the Open common-support cache + outcome-blind audit must be frozen before any V2.1/V2.2 outcome run.
