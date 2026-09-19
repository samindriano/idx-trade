# Alpha Hypothesis Card Pack V1

Date: 2026-09-19 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Stage: `E_H_L_FUTURE_RESEARCH / OUTCOME_BLIND`

## Purpose and novelty rule

This pack converts prior archaeology plus a bounded literature review into
future research specifications. A card is not a candidate, not a survivor, and
not predictive evidence. No C5+ identifier is created until a card passes the
novelty gate, has an admissible PIT contract, and receives an independent
structural review.

External literature is hypothesis inspiration only. It is not evidence that a
mechanism works on IDX-Trade. The local panel currently contains daily
OHLCV/volume/value fields, while intraday, spread, depth, historical sector,
complete ownership/flow, and population-wide financial vintages are not
admitted.

## Literature map

- Campbell, Grossman, and Wang (1993) model volume-conditioned serial
  correlation and argue that high-volume price pressure can be followed by
  reversal; see the [QJE article](https://doi.org/10.2307/2118454) and the
  author-hosted [paper PDF](https://web.mit.edu/wangj/www/pap/CampbellGrossmanWang93.pdf).
- Chordia, Roll, and Subrahmanyam (2001) study aggregate liquidity and trading
  activity, including time variation in market liquidity; see [Market Liquidity
  and Trading Activity](https://doi.org/10.1111/0022-1082.00335).
- Chordia, Subrahmanyam, and Anshuman (2001) study the level and variability of
  dollar volume and share turnover as trading-activity variables; see the
  [JFE record and DOI](https://doi.org/10.1016/S0304-405X(00)00080-5).
- Miwa (2019) separates intraday and overnight components and reports that the
  reversal pattern varies with illiquidity and volatility; see
  [Short-Term Return Reversals and Intraday Transactions](https://doi.org/10.1142/S2010139219500022).
- Lee and Swaminathan (2000) study how past volume relates to the magnitude and
  persistence of price momentum; see the [author-hosted paper](https://www.lsvasset.com/pdf/research-papers/Price-Momentum-Trad-Vol-2000.pdf).

The literature therefore supports asking conditional liquidity/participation
questions, but it does not settle the direction, horizon, or implementability
for IDX. It also reinforces the program's existing warning that reversal must
be evaluated alongside trading friction.

## Card H-LIQ-01 — Trading-activity variability state

- **Mechanism:** not the level of participation alone, but instability of
  dollar trading activity may identify changing liquidity demand/supply.
- **Rationale:** the prior C2 uses a five-session abnormal-turnover level
  multiplied by return. A rolling dispersion/variability state is a different
  temporal mechanism, motivated by the trading-activity literature, rather than
  a monotone C2 transform.
- **Required data:** daily `close`, `volume`, and `regular_market_value`;
  ideally a stable dollar-turnover definition and a frozen active/liquid mask.
- **PIT requirements:** only information through decision session `t`,
  official-session windows, identity continuity, and corporate-action-basis
  authority for the price/volume series.
- **Expected structural behavior:** slower-changing state than C2; lower
  turnover than short-horizon participation signals; possible concentration in
  names with unstable liquidity.
- **Likely redundancy:** medium with C2; low with C3. It is not automatically
  distinct from prior effort-vs-result work until the exact variability state
  is defined.
- **Implementation complexity:** low to medium; rolling dispersion and
  cross-sectional rank are available locally.
- **Principal failure modes:** units/scale mismatch, domination by listing or
  data gaps, severe liquidity concentration, and rebranding C2 as a new ID.
- **Target-free evidence:** distribution, coverage, rank/Top-K overlap with
  C1/C2/C4, turnover, liquidity quartiles, state persistence, and parameter
  sensitivity across a predeclared small set of windows.
- **Status:** `FUTURE_RESEARCH / NOVELTY_UNRESOLVED`; no candidate ID yet.
- **Next action:** prototype and independent robustness review are recorded in
  `2026-09-19_ALPHA_HLIQ01_STRUCTURAL_RESULT_V1.md` and
  `2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md`; resolve the remaining
  price-basis, capacity, and novelty questions before any candidate-ID
  decision.

### H-LIQ-01 prototype result

The single frozen representation produced 155,679 finite rows over all 600
sessions, 10.31% mean Top-30 turnover, and 39.67% of selected slots in the
bottom market-value quartile. Daily rank dependence was -0.045 with C1, +0.100
with C2, -0.126 with C3, and -0.105 with C4; Top-30 overlap with C1/C2/C3/C4
was 8.97%/31.34%/4.75%/12.48% on available dates. The result is
`FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`, not C5.

The adversarial follow-up is recorded in
`2026-09-19_ALPHA_HLIQ01_ROBUSTNESS_RESULT_V1.md`: conditional C2 dependence
rises to `0.196` in the top market-value quartile, h10/h40 overlap h20 by
`61.13%`/`62.02%`, and selected ≤365-day listing share is `11.22%` versus
`5.51%` of eligible rows. These findings keep the card open but prevent
candidate admission.

## Card H-VOL-01 — Daily volatility compression state

- **Mechanism:** recent intraday range compression relative to a slower range
  state may identify a changing uncertainty/price-discovery regime.
- **Fixed representation:** `-log(median_5((high-low)/close) /
  median_60((high-low)/close))`, on the official-session grid. One fixed form;
  no sign, horizon, or threshold sweep.
- **Required data:** daily high, low, close, official sessions, and the frozen
  active/liquid mask.
- **PIT requirements:** same EOD-t contract, price-basis/CA authority,
  identity continuity, and no silent source gaps.
- **Observed structural signature:** `308,514` finite eligible rows over
  `1,201` dates and `711` tickers; mean Top-30 turnover `29.2778%`; selected
  bottom-value Q1 share `42.7200%`.
- **Structural distinctness:** mean Top-30 overlap with C1/C2/C4/H-LIQ-01 is
  `9.5209% / 8.0155% / 15.5676% / 13.5803%`; mean daily Spearman with those
  series is `0.1047 / -0.0410 / 0.1856 / -0.0780`. Low overlap is not proof of
  predictive orthogonality.
- **Likely redundancy:** adjacent to V4-B range acceptance/rejection and
  O2/O2.1 flat-range geometry; exact novelty remains unresolved.
- **Principal failure modes:** bottom-value concentration, turnover, mixed
  price basis, suspension/zero-range handling, and confusing structural
  distinctness with predictive value.
- **CA stress:** substituting the 188 retained `idx_close` comparison rows
  changed `547` scores and `8,876` ranks; mean/minimum Top-30 overlap remained
  `99.8307% / 86.6667%`. This narrows but does not clear basis risk.
- **Horizon stress:** fixed `5/20`, `5/60`, and `20/120` forms are materially
  different (`58.9675%`, `9.9182%`, and `29.3193%` pairwise Top-30 overlap);
  `5/20` raises mean turnover to `36.2583%`, while `20/120` falls to
  `271,045` finite rows. Horizon choice remains unresolved.
- **Status:** `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5.
- **Evidence:** `2026-09-19_ALPHA_HVOL01_COMPRESSION_RESULT_V1.md`,
  `2026-09-19_ALPHA_HVOL01_CA_SENSITIVITY_RESULT_V1.md`, and the staged
  `alpha_hvol01_compression_diagnostic_v1.json`/
  `alpha_hvol01_ca_sensitivity_v1.json`.

## Card H-EXC-01 — Previous-close excursion asymmetry

- **Mechanism:** repeated dominance of the high-side or low-side intraday
  excursion around the previous completed close may encode rejection or
  one-sided pressure without requiring current Open or volume.
- **Fixed representation tested:**
  `median_5(((high-prev_close)-(prev_close-low)) /
  ((high-prev_close)+(prev_close-low)))`.
- **Observed result:** `305,814` finite eligible rows; mean Top-30 turnover
  `40.9694%`; q95/max turnover `56.6667% / 93.3333%`; score min/max
  `-16.2 / 5.0`.
- **Structural distinctness:** low mean Top-30 overlap with C1/C2/C4/H-LIQ/
  H-VOL of `1.2708% / 25.1624% / 4.7960% / 14.2770% / 11.8568%`, but low
  overlap is not predictive orthogonality.
- **Failure:** exact raw form is unbounded when previous close is outside the
  current range or the denominator is small; high churn reinforces the failure.
- **Status:** exact representation `STRUCTURALLY_REJECTED_AS_WRITTEN`; the
  broader excursion/rejection mechanism remains unclosed and requires a new
  preregistered bounded contract. No C5.
- **Evidence:** `2026-09-19_ALPHA_HEXC01_EXCURSION_ASYMMETRY_RESULT_V1.md`.

## Card H-EXC-02 — Bounded previous-close excursion balance

- **Mechanism:** the relative balance of absolute high-side and low-side
  excursions around the previous close may encode repeated one-sided pressure
  without requiring current Open or volume.
- **Fixed representation tested:**
  `median_5((abs(high-prev_close)-abs(low-prev_close)) /
  (abs(high-prev_close)+abs(low-prev_close)))`.
- **Observed result:** `308,067` finite eligible rows; score domain exactly
  `[-1, 1]`; mean Top-30 turnover `40.7750%`; q95/max turnover
  `56.6667% / 86.6667%`.
- **Structural distinctness:** mean Top-30 overlap with C1/C2/C4/H-LIQ/H-VOL
  is `1.3380% / 25.8562% / 4.9431% / 14.7849% / 11.4543%`.
- **Failure/caution:** boundedness fixes the H-EXC-01 numerical tail, but high
  turnover, Q4 selected value/dollar-turnover shares of `33.5609% / 33.5665%`,
  and unresolved PIT/CA/capacity keep economics and novelty open.
- **Horizon result:** fixed windows `5/20/60` have mean Top-30 turnover
  `40.7750% / 20.4944% / 11.7570%`, but pairwise Top-30 overlap is only
  `34.7905% / 24.3750% / 42.3333%`; no horizon was selected.
- **Status:** `FUTURE_RESEARCH / NOVELTY_PENDING / ECONOMIC_CAUTION`; no C5.
- **Evidence:** `2026-09-19_ALPHA_HEXC02_BOUNDED_EXCURSION_RESULT_V1.md`.

## Card H-MICRO-01 — High-participation reversal event

- **Mechanism:** a large price concession accompanied by unusually high
  participation may reflect temporary liquidity demand and subsequent
  absorption rather than durable information.
- **Rationale:** directly connected to C1/C2 and Campbell–Grossman–Wang;
  useful as a mechanism card because the event/conditional interpretation may
  differ from a continuous additive score.
- **Required data:** daily OHLCV/value; high/low would allow range-location and
  rejection qualifiers.
- **PIT requirements:** same as C1/C2 plus explicit corporate-action and
  volume-basis authority.
- **Expected structural behavior:** sparse tail events, longer persistence than
  ordinary reversal, and stronger low-liquidity exposure.
- **Likely redundancy:** high with C1, C2, and historical effort-vs-result /
  impact-absorption families. This is not a new candidate without a materially
  different event contract.
- **Implementation complexity:** medium; event thresholds create a high risk
  of arbitrary parameter discovery.
- **Principal failure modes:** decorative thresholding, duplicated C2, extreme
  turnover, and false interpretation of illiquidity as information.
- **Target-free evidence:** event frequency, cross-sectional concentration,
  overlap with C1/C2/C4, persistence, liquidity tail, and threshold stability
  under one frozen perturbation set.
- **Status:** `DO_NOT_RETRY_WITHOUT_NEW_REPRESENTATION`; keep as a mechanism
  review item, not a C5.
- **Next action:** no run until a novelty decision distinguishes it from the
  already documented effort-vs-result and C2 representations.

## Card H-MICRO-02 — Intraday/overnight reversal decomposition

- **Mechanism:** short-horizon reversal may be concentrated in intraday price
  pressure rather than overnight information.
- **Rationale:** literature distinguishes the components, but the local
  historical executable Open/intraday contract is not admitted.
- **Required data:** authoritative intraday or executable Open/close series,
  session timestamps, and a PIT corporate-action transition map.
- **PIT requirements:** source timestamp, publication/availability semantics,
  complete listing/delisting coverage, and no silent Open fallback.
- **Expected structural behavior:** potentially different liquidity exposure and
  horizon decay from C1; impossible to assess honestly from the current panel.
- **Likely redundancy:** conceptual overlap with C1, but information-source
  novelty would be real if the source contract becomes admissible.
- **Implementation complexity:** high.
- **Principal failure modes:** look-ahead through Open recovery, mixed price
  basis, incomplete intraday history, and source revision.
- **Target-free evidence:** source completeness/PIT audit and structural field
  coverage only; no proxy target reconstruction.
- **Capability result:** positive finite Open exists on `201,415/310,761`
  eligible rows (`64.8135%`), with at least 30 Open rows on all `1,201`
  eligible dates; provenance is split between IDX and Yahoo and `20,995`
  source transitions remain.
- **Status:** `PARTIAL_CAPABILITY / BLOCKED_SOURCE_ADMISSION`.
- **Evidence:** `2026-09-19_ALPHA_OPEN_CAPABILITY_RESULT_V1.md`.
- **Next action:** wait for an independently admitted source contract; do not
  scrape or backfill the canonical panel.

## Card H-FUND-01 — Financial change/price disagreement

- **Mechanism:** a change or surprise in PIT financial quality/growth that is
  not yet reflected in price may differ from a static quality-level rank.
- **Rationale:** prior financial experiments do not close all event/change or
  relative-value mechanisms, but C3's current bundle is too sparse for a
  population-wide contract.
- **Required data:** revision-aware filings, publication/knowledge timestamps,
  fiscal-period mapping, stable issuer identity, and price basis.
- **PIT requirements:** complete vintage/revision lineage, reporting lag, period
  boundaries, attachment identity, and no forward fill across knowledge dates.
- **Expected structural behavior:** slower turnover and event clustering;
  coverage should be evaluated before any candidate creation.
- **Likely redundancy:** medium with C3; distinct from C3 only if the change /
  disagreement contract is explicit and not another level composite.
- **Implementation complexity:** high.
- **Principal failure modes:** stale financials, restatement leakage, sparse
  intersection, accounting-period mismatch, and manufactured coverage.
- **Target-free evidence:** capability funnel by feature subset, vintage audit,
  event spacing, missingness clustering, and structural overlap only.
- **Status:** `BLOCKED_PARTIAL_CAPABILITY`.
- **Next action:** extend the C3 capability map, not the candidate budget.

## Card H-FLOW-01 — Extreme flow event conditioned on liquidity state

- **Mechanism:** extreme foreign/ownership flow may matter as an event or as a
  conditional state interacting with price dislocation and liquidity, rather
  than as a universal additive feature block.
- **Rationale:** this is explicitly different from the failed exact additive
  Foreign Flow V2 formulation, but only at the mechanism level; it needs fresh
  admitted data and a new contract.
- **Required data:** historical flow/ownership observations with issuer
  identity, timestamp, revision behavior, and publication availability.
- **PIT requirements:** population completeness, point-in-time availability,
  stable ticker mapping, and event/quantity semantics.
- **Expected structural behavior:** sparse extreme events, clustering around
  liquidity/price shocks, and high source-driven missingness risk.
- **Likely redundancy:** potentially complementary to C1/C2, but this cannot be
  inferred from low correlation alone.
- **Implementation complexity:** high.
- **Principal failure modes:** source semantics, survivorship, publication lag,
  event threshold mining, and reusing consumed historical folds.
- **Target-free evidence:** source capability audit and event distribution only.
- **Status:** `BLOCKED_SOURCE_ADMISSION` / `FUTURE_DATA`.
- **Capability update:** the local official foreign-flow archive now passes
  structural/hash/calendar integrity across 1,129,024 rows and 1,288 sessions,
  but every session has unknown publication time and the declared T+1 rule is
  not a public-availability certificate. See
  `2026-09-20_ALPHA_FOREIGN_FLOW_HISTORICAL_SOURCE_AUDIT_RESULT_V1.md`.
- **Next action:** preserve the old exact additive failure and wait for an
  independently admitted PIT/identity/CA source contract; no generic provider
  restart.

## Card FUTURE_QUOTE_FLOW_INTERACTION_V1 — EOD quote-state / foreign-pressure interaction

- **Mechanism:** the interaction between end-of-day quote state (bid/offer)
  and foreign-pressure flow may distinguish executable liquidity stress from
  a price/participation signal, if both surfaces are observed on a defensible
  common basis.
- **Information source:** bid/offer is a new raw-input surface in the audited
  panel-depth source; foreign-flow shares/value are present but remain within
  the existing H-FLOW/Foreign Flow family.
- **Required data:** population-wide historical quote state with quote
  timestamp/age, depth or executable semantics, price units, and complete
  foreign-flow actor/aggregation/unit definitions.
- **PIT requirements:** available-at/knowledge time, revision/vintage,
  identity/ISIN continuity, corporate-action/share-basis authority, complete
  universe coverage, and an explicit missingness policy.
- **Expected structural behavior:** quote-state and foreign-pressure measures
  should be evaluated as a conditional interaction, not as an additive rescue
  of the closed Foreign Flow V2 formulation; quote-age and depth should matter
  for any executable interpretation.
- **Likely redundancy:** foreign-flow alone is high with H-FLOW-01; bid/offer
  is not yet represented in the incumbent candidate families, but mechanism
  novelty remains unknown until the missing quote contract is supplied.
- **Implementation complexity:** high; source-contract and timestamp work is
  required before any feature definition is scientifically meaningful.
- **Principal failure modes:** stale or snapshot quotes, zero-quote semantics,
  hidden look-ahead, mixed price/share basis, unobserved depth/queue, unit
  ambiguity, and treating structural non-correlation as predictive novelty.
- **Target-free evidence:** source contract, field semantics, coverage,
  timestamp/revision behavior, identity/CA linkage, and structural exposure
  only. No candidate or proxy target may be created from this card.
- **Status:** `FUTURE_DATA / SOURCE_ADMISSION_BLOCKED / NOVELTY_UNKNOWN`.
- **Next action:** obtain an independently admitted historical quote/flow
  contract; do not scrape, rescale, backfill, or run C5 on the current source.

## Novelty gate outcome

No new C5+ candidate is admitted by this card pack.

| Direction | Decision |
|---|---|
| Monotone rank/z-score variants | Closed as duplicates by exact Top-30 match |
| Horizon variants | Distinct representations, but remain diagnostics until a future contract chooses one |
| H-LIQ-01 | Potentially new temporal liquidity mechanism; requires bounded structural prototype |
| H-MICRO-01 | Not novel enough yet; do not retry C2/effort-vs-result under a new name |
| H-MICRO-02 | Partial Open capability, but source/PIT/execution admission blocked |
| H-FUND-01 | C3 capability blocked |
| H-FLOW-01 | Source blocked; exact additive predecessor remains closed |
| H-EXC-02 | Bounded new contract is structurally stable but high-churn; future research only |
| FUTURE_QUOTE_FLOW_INTERACTION_V1 | New bid/offer raw surface, but source contract and mechanism novelty remain blocked/unknown; future specification only |

## Boundary and preservation

This card pack contains no target, forward return, IC, ICIR, OOS, incumbent
comparison, or predictive claim. It does not change the candidate registry or
the protected evaluation packet. External literature is separated from local
IDX evidence, and all future cards must pass the same target firewall and
novelty gate.
