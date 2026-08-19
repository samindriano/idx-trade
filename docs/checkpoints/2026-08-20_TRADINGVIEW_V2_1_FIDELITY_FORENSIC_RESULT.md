# TradingView V2.1 Fidelity Forensic V1 — Result

Date: 2026-08-20 (Asia/Jakarta)
Branch: `data/tradingview-v2-1-fidelity-forensic-v1`
Scientific parent: `data/tradingview-historical-price-path-v2-1-remediation@bfb3cbc`
Runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v\tradingview_v2_1_fidelity_forensic_v1_20260820`

## Decision

**`2022_TRADINGVIEW_YEAR_FAILURE_REJECTED_LEGACY_CANONICAL_SCALE_CONFLICT_DOMINATES`**

The prior V2 result `2022 HLC exact ~= 75.46%` must not be interpreted as evidence that TradingView historical 60m data is broadly unreliable during calendar year 2022.

The decisive evidence is the exact three-way comparison against official IDX Stock Summary H/L/C:

- legacy V2 2022 comparable rows: `538`;
- `ALL_AGREE`: `406`;
- `TV_IDX_AGREE_CANONICAL_DIFF`: `130`;
- `CANONICAL_IDX_AGREE_TV_DIFF`: `2`;
- therefore TradingView agrees exactly with official IDX on `536/538 = 99.6283%` of the legacy 2022 rows;
- among the `132` directional TV-vs-canonical disagreements, `130/132 = 98.4848%` are cases where TradingView and official IDX agree against the legacy canonical comparator.

On the five long-lived V2.1 controls in 2022:

- rows: `1,230`;
- TV vs official IDX HLC exact: `1,192/1,230 = 96.9106%`;
- canonical vs official IDX HLC exact inferred from three-way classes: `984/1,230 = 80.0000%`;
- TV vs legacy canonical HLC exact: `957/1,230 = 77.8049%`.

These relationships reject a broad 2022 TradingView-year failure and instead isolate the legacy canonical raw-price comparator as the dominant source of the apparent anomaly.

## Concentration evidence

The legacy 2022 mismatch is extremely concentrated:

- WICO: `129/129` rows mismatch TV vs canonical, accounting for `97.7273%` of all legacy-2022 mismatch rows;
- TFCO: `2` mismatch rows;
- LMSH: `1` mismatch row;
- FASW, SUPR, DEAL: `0` mismatch rows in their supported 2022 samples.

All `538` legacy 2022 rows are `WINDOW_END` requests. Therefore the earlier support-selection / delisted-end hypothesis is **not supported by the exact V2 sample** and is retired for this anomaly.

## Price-basis / scale forensic

### BMRI

For BMRI across supported 2021-2022 rows:

- legacy canonical / TradingView H/L/C ratio is essentially exactly `0.5`;
- official IDX / TradingView ratio is essentially exactly `1.0`;
- the existing corporate-action evidence records BMRI `stockSplit` effective `2023-04-04`.

This is a deterministic price-basis conflict, not random intraday-path noise.

### WICO

For WICO 2022 (`2022-05-09` through `2022-12-30`, `129` rows):

- canonical / TradingView H/L/C ratio is essentially constant at `0.6232079` across the full supported block;
- official IDX / TradingView H/L/C ratio is exactly `1.0` on all 129 rows;
- the local split-event file contains no WICO event explaining this factor.

Therefore WICO is classified as **legacy canonical scale/adjustment conflict with no authorized corporate-action explanation**, not as a TradingView failure. No correction factor is inferred or applied.

### BBRI 2021 diagnostic

BBRI 2021 shows a different but related pattern:

- canonical / TradingView H/L/C has a strong mode near `0.909076`;
- official IDX / TradingView ratios remain near `1.0`;
- exact-equality TV-vs-IDX is lower because small field-level differences remain, especially H/L, while the magnitude ratios stay near unity.

This is sufficient to show that the old canonical comparator is not a safe raw-price oracle for older history. It is **not** sufficient to certify 2021 TradingView fidelity under the existing exact-equality gate; 2021 regular-session / auction / tick-level discrepancy semantics must be handled explicitly in the next preregistration rather than silently waived.

## Comparator-lineage clarification

The V2 `load_canonical()` path reads `raw_open/raw_high/raw_low/raw_close/raw_volume` from the historical canonical raw parquet directory and renames those fields as `canonical_*` for fidelity comparison.

The current Yahoo provider implementation explicitly uses `auto_adjust=False`, and current canonicalization explicitly preserves raw observed OHLC while keeping vendor adjusted close separate. The deterministic historical scale conflicts observed here therefore indicate that the **legacy canonical artifact bytes are not a reliable raw-price fidelity oracle for all older periods**, regardless of the intended semantics of the current code.

The panel `price_provenance` field joined during the forensic must not be interpreted as provenance for the separate `canonical_*` comparator values. Those came from the canonical raw parquet directory. The forensic prep code joined the panel provenance only as descriptive metadata; using it to explain the comparator values would be incorrect.

## Adjudicator defect

The first runtime summary emitted `2022_ANOMALY_MIXED_UNRESOLVED`. That automated label is **invalid** and must not be used.

The helper required `TV-vs-canonical >= 95%` before allowing a canonical-oracle-conflict verdict. This condition is logically contradictory when the canonical comparator itself is the object under suspicion. The runtime raw rows, three-way classes, ratios, input hashes, and generated CSV evidence remain useful; only the automated adjudication label is rejected.

A second reporting defect also exists: the initial year-level TV-vs-IDX summary filtered on full three-way support, which unnecessarily excludes pairwise-valid rows when canonical support is absent. Future fidelity reporting must compute support independently for each source pair.

## Consequence for the full V2.1 acquisition

**Do not run the 978-ticker acquisition under the old fidelity-oracle contract yet.**

The next safe milestone is a separately frozen **full-acquisition preregistration with fidelity-oracle remediation**:

1. official IDX Stock Summary raw H/L/C/V is the primary historical raw-price diagnostic oracle where exact ticker/date evidence exists;
2. the legacy canonical raw directory remains diagnostic only until its price-basis lineage is independently certified;
3. pairwise support is calculated independently rather than requiring three-way completeness;
4. no inferred scale repair, source voting, averaging, or overwrite is allowed;
5. corporate-action evidence may explain/quarantine known price-basis transitions but may not be inferred from observed ratios;
6. 2021 exact H/L/C discrepancies, especially BBRI, require a bounded regular-session/auction/tick-level semantics check before the full-run fidelity gate is frozen;
7. the existing depth/pagination proof remains valid and unchanged;
8. no model, Path Risk, panel mutation, O2, or protected-outcome access is authorized.

## Step-1 status

**Step 1 is complete for the original 2022 question.**

Resolved:

- the 2022 ~75% anomaly is not a broad TradingView-year failure;
- the old support-selection explanation is not supported;
- deterministic legacy canonical scale conflicts dominate the anomaly;
- official IDX raw daily evidence strongly supports TradingView on the exact 2022 overlap.

Remaining work belongs to the next preregistration milestone, not to reopening the 2022 anomaly.