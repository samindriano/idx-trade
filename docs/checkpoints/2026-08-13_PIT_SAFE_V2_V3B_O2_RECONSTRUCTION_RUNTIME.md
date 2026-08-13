# PIT-Safe V2 / V3-B / O2 Reconstruction Runtime

Date: 2026-08-13 (Asia/Jakarta)
Status: `REPRODUCTION_BLOCKED`
Branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`
Runtime code commit: `9eedff931fc682a26b8c4f7c408d6afd606d0e62`

## Decision

The corrected input rebuild completed without provider calls, model fitting,
protected-outcome access, forward scoring, or overwrite of the immutable
lineage. The boundary is:

`HISTORICAL_LADDER_REPLAY_REQUIRED`

The executable status remains `REPRODUCTION_BLOCKED`. The corrected inputs do
not reproduce the candidate-comparison population: the PIT correction changes
causal features, and the available H10 label artifact ends on 2025-03-20 while
the old V2/V3-B/O2 development artifacts extend to 2026-07-17. Therefore no
historical ladder replay was started in this run.

## Immutable parents

| Artifact | SHA-256 |
| --- | --- |
| immutable signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| official exchange calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| H10 development labels | `eeb6a1b2e48d816131172a35462d55ba4f842eee39f3deb4b1f2540ec3b597e7` |
| prior V2 prepared table | `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5` |
| V3-B open-readiness coverage | `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242` |
| preregistered protocol | `c2d1a919d97fa4cff5c8577fcb5a1093d592151119dff6f4c86e8351b69ded44` |

The original V3-B and O2 artifacts remain external, immutable historical
references; they were not overwritten.

## Corrected reconstruction

The generic security-master interval filter ran before baseline rolling,
cross-sectional, market-context, label-join, and model-table construction.

| Output | Rows | Tickers |
| --- | ---: | ---: |
| corrected PIT-safe panel | 981,939 | 945 |
| corrected V2 prepared table | 208,373 | 668 |
| corrected V3-B table | 208,373 | 668 |
| corrected O2 input table | 194,989 | 658 |

The panel input had 981,940 rows. Exactly one row was removed: `KOCI` on
2023-10-06. Its listing interval begins on 2023-10-07, so the invalid
observation is absent from the corrected panel and cannot enter causal
features. No ACTIVE state was inferred from this identity correction.

The corrected V2 key hash is
`c09459b71f5a600fd55f1f27b0ad9acaa035a33c71cbaf3bec28788a03ff4d90`; the
corrected O2 key hash is
`69541019cec6d73ba2b2b94d41e2599d7d0ea027c94e8b48e9e8cfc231997f9d`.

## Delta and propagation diagnostics

Against the old V2 table, the corrected V2 table has 84,260 fewer identity
rows and no added rows. Only two of those removals are on or before the
available H10 label cutoff; 84,258 are after that cutoff. This is a separate
lineage/input-availability difference, not evidence that all 84,260 rows were
caused by KOCI. The old V2 table has 292,633 rows / 737 tickers and ends on
2026-07-17; the corrected table ends on 2025-03-20, matching the H10 label
artifact's maximum signal date.

For the shared corrected/old V2 identities, the PIT correction changes 826
identity rows across 281 tickers and 9 sessions. KOCI contributes 10 changed
feature rows. Market-context propagation is visible in 632
`market_primary_liquid_count` rows; the full per-feature delta is preserved in
`v2_feature_deltas_long.csv`.

The old V3-B table has 292,633 rows / 737 tickers. The corrected V3-B table
shares 208,373 identities with it, with 84,260 old-only rows and no new rows.
The old O2 final training population has 278,168 rows / 729 tickers; the
corrected O2 input shares 194,989 identities, with 83,179 old-only rows and no
new rows. These comparisons are diagnostics only; no old result was replaced.

## External runtime artifacts

Root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_001`

| File | SHA-256 |
| --- | --- |
| `pit_safe_signal_panel.parquet` | `6f6e83c229e9d50c5bff5ef02706ffd2ea7f0d08125c0b66326e3c994752789e` |
| `pit_safe_ranking_v2_prepared_model_table.parquet` | `dbcc0a6051718f978975dd18b66e1e95cb72a5fe452fbd0c10cb6168f6958708` |
| `pit_safe_ranking_v3_b_training_table.parquet` | `9e12fc225e9e39b67649c6c9ed578ebce78018caf3d192feda4cd7ef742fa0ce` |
| `pit_safe_o2_input_table.parquet` | `9a258e076a777a15aff4a30dfde8e24ee8f59af18a7a510c75c3c53212765698` |
| `v2_feature_deltas_long.csv` | `f1f48ed53699c2a146246534f4c9fa0803ca5379878b831e273890c273abad55` |
| `pit_safe_reconstruction_report.json` | `6884e5981c9c01b70a9e2b539fe63cc3e2cae78a1252b589be70709fa6c6af8c` |
| `artifact_manifest.json` | `34049ae3e74019219dd323a2993ab273e1fb4abb64f12e6560faf8769628107f` |

The manifest contains six artifact entries plus the parent hashes and protocol
hash. The runtime report records all prohibited actions as false.

## Validation and next action

Full pytest passed with exit code 0 after the implementation; only existing
non-blocking pandas/runtime warnings were emitted. No providers, models,
protected outcomes, O2 forward counter, or Stage-5 holdout were touched.

Do not fit V2/V3-B/O2 from these inputs automatically. A future run requires
an explicit decision to replay the preregistered historical ladder on the
corrected, label-bounded population, followed by independent review of the
changed candidate-comparison population and the existing prospective O2
identity boundary.
