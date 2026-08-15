# Financial PIT Representation V2 Structural Audit

Status: `FINANCIAL_REPRESENTATION_V2_STRUCTURAL_AUDIT_COMPLETE`

Date: 2026-08-16

Branch: `research/idx-financial-representation-v2`

## Scope and boundary

This is an outcome-blind structural census only. It does not load labels or
predictions, fit or score a model, access O2/V2/V3-B performance, access
protected/fresh-forward outcomes, or make a Financial Alpha V2 decision.

The audit uses one latest known reporting-period bundle per support row. Bundle
chronology is ordered by fiscal year, exact source period date, and the frozen
period rank `Q1 < H1 < 9M < FY`; later knowledge time is used only to choose a
revision within the same period bundle. Candidate features never fall back to
another period when the selected bundle is missing a feature. The cutoff is
18:00 Asia/Jakarta on each session date, represented in UTC in the artifacts.

The only evaluated candidates are:

- `CORE3`: leverage liabilities/assets, cash/assets, net-income/revenue;
- `CORE3_PLUS_YOY_REVENUE`;
- `CORE3_PLUS_YOY_ASSETS`;
- `CORE3_PLUS_BOTH_YOY`.

## Pinned inputs

- Financial feature panel: `D:\Documents\Project\idx-financial-pit-feature-materialization-20260814-v1-final-a\feature_panel.parquet`
  SHA-256 `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`.
- V2 outcome-blind common support: `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_remediation1_retry1\outcome_blind_common_support.parquet`
  SHA-256 `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`.
- Accepted 18:00 support census root: `D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-census-1800`.
- Selected feature states SHA-256
  `7bd63dfb826773af12916e42d687f3c7e8ba9b4ec07f0f26216ba25a8f870949`.
- Support census manifest SHA-256
  `12550704487104f96be4e708649d3d6a7cc6a767feb73d42e5ede86a2276eb18`.
- Support census summary SHA-256
  `e33ded6fcd6b12c6083c8e877ae78ce4a82d05279a4f3b62aee04f7f25d28343`.

## Structural result

The support contains 277,244 rows and 729 tickers. The selected bundle is
available on 70,931 rows / 415 tickers. A further 19,549 rows are explicitly
`UNRESOLVED_PERIOD_BOUNDARY`; they are not silently assigned a fiscal period.
There are 186,764 rows with no eligible Financial state. The selected bundle
has zero same-bundle violations, zero post-cutoff selected states, zero
knowledge-time violations, and zero incomplete selected-bundle provenance.

Availability on the selected bundle:

| Candidate | Available rows |
|---|---:|
| `leverage_liabilities_to_assets` | 70,520 |
| `liquidity_cash_to_assets` | 70,520 |
| `margin_net_income_to_revenue` | 70,520 |
| `CORE3` joint | 70,520 |
| `yoy_revenue` | 34,412 |
| `yoy_total_assets` | 34,412 |
| `CORE3 + yoy_revenue` | 34,412 |
| `CORE3 + yoy_total_assets` | 34,412 |
| `CORE3 + both YoY` | 34,412 |

The two YoY slots have identical support in this census. Their missingness is
not converted to zero or filled from another period. The status decomposition
for each CORE3 feature is 70,520 `AVAILABLE`, 19,960 technical/semantic
unresolved, and 186,764 `NO_FINANCIAL_STATE`. For each YoY feature it is
34,412 `AVAILABLE`, 35,358 `DECLARED_MISSING_INPUT`, 20,710
technical/semantic unresolved, and 186,764 `NO_FINANCIAL_STATE`.

Selected period strata are Q1 17,488, H1 19,731, 9M 25,416, and FY 8,296.
These strata remain separate; no annualization, TTM, interpolation, or period
pooling is performed.

## Fold support

The inherited V2 folds are unchanged. Key Financial-era support counts are:

| Fold | Block | Financial bundle rows | CORE3 rows | YoY rows |
|---|---|---:|---:|---:|
| V2F4 | train | 10,790 | 10,714 | 0 |
| V2F4 | purge | 2,608 | 2,590 | 0 |
| V2F4 | validation | 12,260 | 12,174 | 702 |
| V2F5 | train | 25,658 | 25,478 | 702 |
| V2F5 | purge | 2,420 | 2,400 | 702 |
| V2F5 | validation | 15,437 | 15,353 | 10,534 |
| V2F6 | train | 43,515 | 43,231 | 11,938 |
| V2F6 | purge | 3,728 | 3,712 | 2,981 |
| V2F6 | validation | 19,899 | 19,812 | 16,344 |

V2F1 has no eligible Financial rows in train, purge, or validation. V2F2 has
388 CORE3 rows in validation and no Financial rows in its train or purge
blocks. V2F3 has 388 CORE3 rows in train, 698 in purge, and 9,628 in
validation; its YoY slots are absent throughout those blocks. In V2F4, both
YoY candidates are completely absent from training, so neither can be admitted
under the frozen structural rule. CORE3 is structurally admissible in all
three Financial-era blocks.

## Admission decision

`CORE3` is the widest structurally admissible representation. Both YoY
variants are rejected for this stage because each is completely absent in the
V2F4 training block. This is an outcome-blind support decision, not a claim
about predictive performance. Financial Alpha V2 remains unauthorized pending
separate review and preregistration.

## Reproducibility and artifacts

Run 1 (complete):
`D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run2`

Deterministic rerun:
`D:\Documents\Project\idx-financial-representation-v2-20260816-v1-run3`

All eight files are byte-identical between the two roots. The manifest SHA-256
is `e62a44109007e94a01093800c7220777c7c9f4561a08d57210778f0f2153b96a`.
The artifact manifest records:

- `bundle_rows.parquet`: `c6004832e651b380161ec216efb2020dddbe86419d89c4521f77aeb09335876b`;
- `selected_candidate_provenance.parquet`: `44c1714baaac0a1ec29f9b1870e7cdab9775460e03ddcaf5af64909ed7b2ea35`;
- `coverage_by_period.csv`: `c151fd9ff4e709569f705ff783b14940baa964cb86e2c2cfa847f3e7fb21c083`;
- `fold_coverage.csv`: `d395f067e9a5b7df63d5943952bfa5f474ce6a78b540bfb2b217a3efbafd41d2`;
- `ticker_overlap.csv`: `ae33307aa2984bea51089c688b6acdfa3b1ac533cb54979f77657fbc8f69e74d`;
- `summary.json`: `5ffad333be7b390f0533872306105134a569dc2d70ac9a0150b90fcc2cf16918`.

Both summaries record `labels_loaded=false`, `predictions_loaded=false`,
`model_fit=false`, `performance_metrics_computed=false`,
`protected_outcomes_accessed=false`, `o2_accessed=false`, and
`network_calls=0`.

## Validation

- Focused: `3 passed` (`tests/test_financial_representation_v2.py`).
- Full repository pytest: `1 failed, 64 passed`; the only failure is the
  pre-existing unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`,
  which expects one conflict while current storage semantics report independent
  `raw_close` and `vendor_adj_close` conflicts (two). No storage file was
  changed by this lane.
- `git diff --check`: passed.
