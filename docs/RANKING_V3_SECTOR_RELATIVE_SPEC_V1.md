# Ranking V3-D Sector-Relative Specification V1

Date: 2026-08-10 (Asia/Jakarta)

Status: **PRE-OUTCOME IMPLEMENTATION BASELINE — NOT AUTHORIZED TO SCORE**

Hypothesis ID: `V3-D-SECTOR-RELATIVE-V1`

This document defines the implementation baseline for V3-D while V3-C is still running locally. No V3-D outcome has been viewed. The implementation may be amended once, outcome-blind, after independent review of V3-C and before any V3-D F1-F4 score is opened. Any such amendment must be documented, re-hashed, re-reviewed, and frozen before V3-D run authorization.

## 1. Research question

> Does compact point-in-time within-sector relative information add robust ranking value beyond the exact frozen V2 `HGB_XS_MARKET` whole-market cross-sectional and market-relative representation?

V3-D tests one feature-family hypothesis only. It does not inherit V3-B Structure-Lite or V3-C regime specialization in the discovery candidate. Those components remain separately attributable and may only be combined in the later one-shot integration experiment if they survive their own gates.

## 2. Candidate budget

Provisional candidate slots, to remain unchanged unless amended before any V3-D outcome access:

1. `V3-D-SECTOR-RELATIVE-V1-CONTROL-008` — exact V2 `HGB_XS_MARKET` control;
2. `V3-D-SECTOR-RELATIVE-V1-CANDIDATE-009` — exact V2 25 features plus the six sector-relative features in Section 5.

No second sector candidate, sector-specific model zoo, sector-dependent hyperparameters, threshold grid, feature ablation, or rescue variant is allowed in this implementation baseline.

## 3. Hard prerequisite: point-in-time sector-history gate

V3-D outcomes are prohibited until a sector-history artifact passes this gate.

The sector-history artifact must contain at least:

- `ticker` — normalized security ticker used by the research panel;
- `sector_code` — stable sector classification code/name for the interval;
- `effective_from` — first date classification is economically effective;
- `effective_to_exclusive` — first date classification is no longer effective; may be empty for open-ended latest interval;
- `available_at` — date/time the classification was publicly/reliably available to the research system;
- `source_id` — immutable source-document identifier;
- `source_sha256` — SHA-256 of the source document/snapshot supporting the row.

Optional source metadata may be carried but may not replace these fields.

### 3.1 Point-in-time usability

For each interval define:

`usable_from = max(effective_from, calendar_date(available_at))`.

A sector classification may be assigned to signal date `t` only when:

`usable_from <= t < effective_to_exclusive`

or the interval is open-ended on the right.

Therefore a classification learned after its economic effective date is **not backfilled** into earlier signals. Current-sector labels may never be propagated backward through history merely because the current classification is known today.

### 3.2 History validity

The validator must fail closed on:

- invalid ticker/date/source hash;
- empty sector code;
- `effective_to_exclusive <= effective_from`;
- `available_at` after the interval has already ended;
- overlapping usable intervals for the same ticker;
- two different sector codes simultaneously usable for one ticker/date;
- duplicate source rows with inconsistent metadata;
- untraceable ticker/security identity mapping.

Changes in classification are allowed only as explicit non-overlapping intervals. Missing history remains missing; it is never inferred from adjacent/current rows.

### 3.3 Provenance freeze

Before outcome authorization, record and freeze:

- sector-history file SHA-256;
- every unique source document/source SHA represented;
- row count and ticker count;
- first/last effective and available dates;
- interval-overlap audit;
- assignment coverage through V2F1-F4;
- unresolved ticker/date counts and reasons.

If provenance cannot establish historical effective dates and availability, V3-D remains `BLOCKED_PIT_SECTOR_HISTORY` regardless of how attractive a current-sector mapping appears.

## 4. Outcome-independent feature population

Sector features must be built from the same full causal primary-liquid feature frame used by frozen V2, not from the resolved H10 label table.

Preparation sequence:

1. SHA-verify the frozen signal panel, calendar, security master, V2 prepared table, and V2 prepared manifest.
2. Materialize raw research data only through official signal session `984` for V3-D discovery.
3. Rebuild baseline features and the exact V2 full feature frame outcome-independently.
4. Assign PIT sector membership using Section 3.
5. Compute sector-relative features across the **full same-date primary-liquid universe with valid PIT sector membership**, independent of future H10 resolution.
6. Join the six features to the exact resolved V2 F1-F4 discovery rows by `(ticker,date,signal_session_index)`.
7. Prove exact existing V2 row/order/label/25-feature equivalence before freezing the V3-D cache.

V2F5/V2F6 rows must not be materialized in the V3-D discovery model cache. Reserved post-2026-07-31 V2 forward outcomes remain off-limits.

## 5. Compact six-feature candidate

The implementation baseline uses exactly three already-frozen raw concepts:

- `close_return_5`;
- `close_return_20`;
- `close_position_20`.

For each concept, append exactly two within-sector transforms, producing six features:

1. `sector_rank_close_return_5`
2. `sector_rank_close_return_20`
3. `sector_rank_close_position_20`
4. `sector_relative_close_return_5`
5. `sector_relative_close_return_20`
6. `sector_relative_close_position_20`

No ATR, liquidity, volume, valuation, fundamental, broker-flow, or sector-specific technical library is added in V1.

### 5.1 Eligible same-date sector group

A sector group for date `t` is formed only from rows that are:

- in the frozen causal `universe_primary_liquid` on `t`;
- assigned a valid PIT sector on `t`;
- present in the outcome-independent feature frame.

For each source concept separately, at least `5` finite primary-liquid members are required in the date-sector group. If fewer than 5 finite members exist for that concept, both transforms for that concept are missing for all rows in that group/date.

### 5.2 Within-sector percentile rank

For valid groups:

`sector_rank_x = percentile_rank(x within date-sector, method=average)`.

This uses the same pandas-style average-tie percentile semantics as the existing V2 same-date rank implementation, but the group key is `(date, sector_code)` rather than date only.

### 5.3 Stock-minus-sector median

For valid groups:

`sector_relative_x = stock_x - median(x within date-sector)`.

The median is computed from all finite primary-liquid members in the PIT sector group on that date, independent of whether their future H10 label resolves.

Sector code itself, group size, and sector median are audit metadata, not model features in V1.

## 6. Model semantics

Control remains the exact V2 `HGB_XS_MARKET`.

The sector candidate uses:

- exact V2 25 ordered features first;
- the six Section 5 features appended in exact listed order;
- exact median `SimpleImputer(add_indicator=True, keep_empty_features=True)`;
- exact frozen HGB parameters/seed;
- no scaler;
- exact H10 label/universe/fold/scoring semantics;
- uniform training weights.

No sector-specific expert, score adjustment, calibration, or within-sector post-ranking is performed. The HGB receives the sector-relative numerical representation and still emits one global ranking score.

## 7. Pre-score data/coverage gate

This gate is outcome-independent and must pass before control/candidate performance is scored.

For each F1-F4 training and validation block:

- PIT sector assignment coverage among V2 rows >= `90%`;
- finite coverage for each of the six sector features >= `80%`;
- at least `8` distinct represented sectors in validation;
- no row with an invalid/overlapping PIT assignment;
- no silent row drop caused by sector missingness.

Report also group-size distribution, rows excluded from feature computation because group finite count <5, sector concentration, and unresolved membership reasons.

If any mandatory gate fails, decision is `V3_D_SECTOR_BLOCKED_KEEP_V2_CONTROL`; do not weaken group size, coverage thresholds, or backfill sector history to rescue the experiment.

## 8. Discovery folds and control equivalence

Outcome discovery is V2F1-V2F4 only. F5/F6 remain sealed for the eventual final-V3 late-development confirmation.

Before candidate metrics may be interpreted, the exact V2 control must reproduce immutable V2 F1-F4 prediction rows/scores/metrics at `rtol=0`, `atol=1e-12`, using the existing control-equivalence contract.

Control-equivalence failure is a hard stop.

## 9. Primary metrics and promotion gate

Use the exact V2 metrics and the existing V3 absolute sanity + paired promotion gates:

Absolute sanity:

1. all required metrics finite;
2. median PR-AUC minus prevalence >0;
3. positive PR delta >=3/4 folds;
4. median ROC >0.50;
5. ROC >0.50 >=3/4 folds;
6. median Q5-Q1 >0;
7. positive Q5-Q1 >=3/4 folds.

Paired versus exact V2 control:

1. median PR-delta improvement >= `+0.001`;
2. q25 PR improvement >=0;
3. worst-fold PR improvement >=0;
4. PR not below control >=3/4 folds;
5. median ROC change >=`-0.005`;
6. median Q5-Q1 change >=`-0.005`;
7. Q5-Q1 not below control >=3/4 folds.

Top-decile lift is mandatory diagnostic and cannot rescue a failed gate.

## 10. Mandatory sector diagnostics

Because V3-B improved broad separation while its median top-decile lift diagnostic weakened, V3-D must explicitly report concentration effects rather than relying only on aggregate metrics.

For each F1-F4 validation block report:

- sector membership row/date coverage;
- candidate top-decile composition by sector;
- control-vs-candidate top-decile overlap/Jaccard;
- sector concentration (largest sector share of top decile);
- per-sector PR-AUC delta versus prevalence for sectors with >=300 validation rows;
- paired candidate-minus-control sector PR improvement for those sectors;
- F4 sector behavior.

These are diagnostics in V1, not post-hoc rescue gates. If they reveal a structural problem, any redesign requires a new pre-outcome amendment/hypothesis before further outcome access.

## 11. Deterministic decision

- PIT/data/coverage gate fails before model outcomes: `V3_D_SECTOR_BLOCKED_KEEP_V2_CONTROL`.
- Clean candidate fails absolute or paired promotion gate: `V3_D_SECTOR_KILL_KEEP_V2_CONTROL` / `KEEP_DIAGNOSTIC`.
- Clean candidate passes both: `V3_D_SECTOR_PROMOTE_RELATIVE6` / `PROMOTE_FOR_NEXT_RESEARCH_STEP`.

No rescue feature set is allowed after V3-D outcomes are viewed.

## 12. Implementation now, authorization later

Engineering may proceed now for:

- PIT sector-history validation and assignment;
- sector feature builder;
- F1-F4-only immutable cache preparation;
- coverage/provenance report;
- exact control-equivalence runner;
- one fixed sector candidate runner;
- sector diagnostics;
- focused tests;
- artifact hashing and handoff.

However V3-D outcome execution is **not authorized** until:

1. V3-C result has returned and been independently reviewed;
2. any justified outcome-blind V3-D amendment is completed and frozen;
3. a real PIT sector-history artifact passes the Section 3/7 data gate;
4. a separate V3-D run-authorization checkpoint pins the final spec/code/data hashes.

## 13. Ledger

Reserve provisionally:

- ordinal `008` exact V2 control;
- ordinal `009` sector-relative candidate.

They remain unviewed and do not increment the cumulative candidate count until an authorized V3-D outcome run actually occurs.

## 14. Hard prohibitions

Do not:

- use current-sector backfill for historical rows;
- infer sector membership from future/current company metadata;
- compute sector statistics only on label-resolved rows;
- include Structure-Lite or Regime in the V3-D discovery candidate;
- tune sector features/group-size/coverage gates after seeing V3-D outcomes;
- score/load/summarize V2F5/V2F6;
- inspect reserved V2 fresh-forward outcomes;
- write `FORWARD_OUTCOME_ACCESS_STARTED`;
- start V3-E/integration/F5-F6/calibration/Stage6/IDX-VAL-002/execution/PnL/Kelly/paper/live/main merge automatically.
