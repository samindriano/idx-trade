# Ranking V4-3 primary-liquid support census — result

Date: 2026-08-17 (Asia/Jakarta)
Branch: `research/idx-ranking-v4-3-preregistration-v1`
Base HEAD: `8dbde070b18edf432348062e5a9218f6ef2665f9`
Status: `V4_3_PRIMARY_LIQUID_SUPPORT_6X100_FEASIBLE`

## Boundary

This run consumed the frozen V4-3 configuration without modification. It is
support/fold materialization only. No R5/R10 values, target ranks, labels,
predictions, IC/performance metrics, model fit, provider calls, or protected
outcomes were accessed.

The exact contract file `docs/SIGNAL_RESEARCH_HLCV_CONTRACT.md` was restored
from the branch's own HEAD bytes after Windows CRLF checkout conversion; its
raw SHA-256 is the pinned `ffff2d21...` value and its Git blob remains the
pinned `4d034e628838f56a0c88b3f23e249fae51a803ac`. No contract or prereg JSON
content changed.

## Frozen inputs

| Input | SHA-256 |
|---|---|
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| signal panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |
| tradability intervals | `fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc` |
| signal manifest | `b703f1f80aa062accfb4387e5c457458c88aec77351e7dd19342b9c45873cd1a` |
| accepted Open derivative | `a1dae0714971904b266a380be6bb96a2a4976068c9d60c54c8c43746826f7cab` |
| Open derivative manifest | `1a6bcc9c7fbbd967cdc69f8876fe1d4aa94b46c0e466469a9643da59251deb14` |
| CA overlay parquet | `2aeab3906434f48c15d9ed7a8fb073fdd3bafff362cedcc7b46f9bf16482ca41` |
| CA overlay manifest | `dfb7219bddec77ced3e3aadfaa2d85d04c19e1d9fd9a8af1badba523ecf91977` |
| frozen V4-3 preregistration | `835da85549b1d6874cb2ab49a029b9f4358fdf28cb8379b3f9df105835b05849` |
| signal contract raw bytes | `ffff2d21b275744a3a2b74c2f7d32be7b589f3c46cf9950c5ff45c48e5bffd73` |

## Primary-liquid support

The frozen decision universe contains 740 tickers, 348,765 decision rows, and
1,241 sessions with rows. The Open lineage is derivative-first, then
incremental verified CA overlay:

- accepted derivative Open rows: 938,139;
- incremental overlay rows: 2,184;
- final Open rows: 940,323;
- overlay overlap with derivative support: 0.

No raw panel was rewritten.

The date-level support census produced:

| Eligible list | Dates |
|---|---:|
| H5 | 1,108 |
| H10 | 1,102 |
| Consensus | 1,100 |

All exceed the frozen 600-session threshold. The exact validation identity
list is the last 600 chronologically ordered consensus-eligible sessions:

- rows: **600**;
- folds: **6 × 100**;
- first validation session: index 650, 2023-12-28;
- final validation session: index 1249, 2026-07-17;
- each fold has exactly 100 rows;
- no duplicate validation session identities;
- H10 purge: 10 official sessions per fold;
- max training signal indices: 639, 739, 839, 939, 1039, 1139.

Fold summary:

| Fold | Official validation indices | Dates | Max training index |
|---:|---|---|---:|
| 1 | 650–749 | 2023-12-28 → 2024-06-10 | 639 |
| 2 | 750–849 | 2024-06-11 → 2024-10-31 | 739 |
| 3 | 850–949 | 2024-11-01 → 2025-04-10 | 839 |
| 4 | 950–1049 | 2025-04-11 → 2025-09-12 | 939 |
| 5 | 1050–1149 | 2025-09-15 → 2026-02-06 | 1039 |
| 6 | 1150–1249 | 2026-02-09 → 2026-07-17 | 1139 |

Mechanism/state conflicts were zero. The run retained explicit ACTIVE,
NO_TRADE, SUSPENDED, UNKNOWN, AMBIGUOUS, and NO_FUTURE_SESSION states; no
state was inferred from row presence.

## Verdict

**`V4_3_PRIMARY_LIQUID_SUPPORT_6X100_FEASIBLE`**.

This authorizes only the conclusion that the frozen primary-liquid support is
large enough for the preregistered 6×100 structure. It does not authorize V4
target materialization, model fitting, predictions, or outcome evaluation.

## Promoted small artifacts

The following small reproducibility artifacts were copied byte-for-byte into
`docs/artifacts/ranking_v4_3_primary_liquid_support_v1/`:

| Artifact | SHA-256 |
|---|---|
| `v4_3_primary_liquid_support_per_date.csv` | `a89d79bf0bbbcc3efb7124cc1a1dbda83a30522ed6dbd1eb45ce315da4499ad3` |
| `v4_3_eligible_h5_sessions.csv` | `e5a9d541f74c5ec1c07496aac9597510e115c230b8e5b754e91721baa0eed0bb` |
| `v4_3_eligible_h10_sessions.csv` | `c6aa516058aae6406dc58844f27c434ebd4cd12ab4b637a74b135d66b9dda373` |
| `v4_3_eligible_consensus_sessions.csv` | `06f7af7d0bc34c1714ed3c19684177cd27dd911c11fd509c231b9bdfb90f970b` |
| `v4_3_validation_folds.csv` | `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915` |
| `v4_3_fold_summary.csv` | `4cd5107f7fd8db126b0f6db43bcf46d37c90935db91e03b7b22c178576764dc6` |
| `census_summary.json` | `e8b466688fe13925bae6ecdaf5973b847d88fd23a1e6c388d268597300e8363a` |
| `manifest.json` | `6cb8df059d310bb337ffe7f5026d416f0e15252c79ecc04e6c597925a0d243a4` |

## Validation

- `tests/test_ranking_v4_3_preregistration.py`: **6 passed**;
- `python -m py_compile scripts/run_v4_3_primary_liquid_support.py`: PASS;
- `git diff --check`: PASS;
- direct runner invocation required `PYTHONPATH=src` because the repository
  package is not installed; this did not change source or scientific config.
