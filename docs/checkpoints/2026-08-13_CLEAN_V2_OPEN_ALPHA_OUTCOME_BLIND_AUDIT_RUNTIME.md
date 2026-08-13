# Clean V2 Open Alpha — Outcome-Blind Audit Runtime

Date: 2026-08-13 (Asia/Jakarta)
Status: **OUTCOME_BLIND_AUDIT_COMPLETE_REVIEW**
Branch: `research/idx-v2-open-alpha-prereg-v1`
Runtime root: `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_001_retry2`

## Guard results

- target/outcome columns loaded: **false**;
- model fit: **false**;
- model score: **false**;
- provider calls: **0**;
- protected outcomes accessed: **false**;
- immutable input panel changed: **false**.

The audit's V2 reader requests an explicit identity/feature column list and
does not request `binary_target`, `label_status`, or any outcome column.

## Population and PIT/session audit

- clean V2 source: 292,631 rows / 737 tickers;
- common support: **277,244 rows / 729 tickers**;
- clean V2 exclusions: **15,387**;
- clean-V2 key SHA: `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`;
- common-support key SHA: `e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`;
- duplicate keys: **0**;
- current listing-invalid rows: **0**;
- current non-ACTIVE rows: **0**;
- regular suspension conflicts: **0**;
- calendar-unresolved rows: **0**;
- pre-list and post-delist synthetic boundary checks: **both rejected** (FINN, dates 2017-06-07 and 2021-05-06).

Exclusion breakdown:

| reason | rows |
|---|---:|
| current Open unavailable/invalid | 12,589 |
| current flat range | 1,876 |
| previous ACTIVE flat/invalid range | 922 |

Previous ACTIVE linkage is exact by ticker and official session order. Every
clean-V2 row had a previous ACTIVE observed bar; previous session gaps were
min 1, median 1, max 39. The 1,990 rows with a flat/invalid previous range are
diagnostic; 922 remain after current Open validity and therefore reduce common
support.

## Open coverage/provenance

On the clean-V2 identity set, 280,042 Open values are known and 278,166 rows
pass the strict same-day geometry recomputation. The accepted panel evidence
status counts are:

| panel evidence status | rows |
|---|---:|
| `IDX_PUBLIC_STOCK_SUMMARY_OPEN_OPTIONAL` | 56,710 |
| `YAHOO_RAW_OPTIONAL` | 134,128 |
| `OPEN_UNAVAILABLE` | 101,793 |

The accepted overlay provenance layer reports:

| Open source | rows |
|---|---:|
| `IMMUTABLE_PANEL` | 190,838 |
| `YAHOO_YFINANCE` | 87,610 |
| `ZAPI_TRADINGVIEW` | 1,594 |
| missing provenance | 12,589 |

There are 1,876 published formula mismatches, all explained by the flat-range
artifact behavior described in the preregistration. The new cache does not
carry those rows into common support.

## Feature audit

The full feature statistics and pairwise correlation matrix are external
artifacts. Among the 277,244 common-support rows, the largest absolute
correlation involving a new Open feature is **0.582885** (`open_position` vs
`open_to_high`). The three existing-V2 pairs above 0.95 are:

- `xs_rank_log_regular_value_relative_20` vs `xs_rank_relative_volume_20`: 0.989723;
- `market_relative_close_position_20` vs `xs_rank_close_position_20`: 0.964641;
- `market_median_log_regular_value_relative_20` vs `market_median_relative_volume_20`: 0.960264.

No new Open feature pair reaches 0.95 absolute correlation in this audit.
The feature distributions, missing/finite counts, zero counts, and full
correlation matrix are retained externally.

## Causal/PIT checks

- future-row invariance: **true**;
- previous-bar selection uses previous ACTIVE observed session, not calendar shift;
- no forward-fill or synthetic fill;
- flat-range formulas fail closed;
- pre-list/post-delist rows are rejected by listing-domain predicates.

## Hashes

Used corrected PIT-safe panel SHA before/after:
`6f6e83c229e9d50c5bff5ef02706ffd2ea7f0d08125c0b66326e3c994752789e`.

Input hashes:

| input | SHA-256 |
|---|---|
| corrected V2 table | `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8` |
| Open readiness rows | `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242` |
| corrected PIT-safe panel | `6f6e83c229e9d50c5bff5ef02706ffd2ea7f0d08125c0b66326e3c994752789e` |
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |
| tradability anchors | `33d53f4cf71944e665b1f94a180d5f4ffad084221c08d63858f10fcb93dbe18e` |
| tradability intervals | `fd255f21a3accd763286fbd0b0c6d9d501d618ae611cc0681017e001bdba83cc` |
| Open provenance | `718b09b2d9d40b3418d5627d430e1b0a33feed7b1e8685a580ed53f94b9fee2d` |

Output artifacts:

| artifact | SHA-256 |
|---|---|
| `outcome_blind_common_support.parquet` | `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6` |
| `common_support_exclusions.csv` | `09c04f3eac5b8a4378f38de22208a0016c3a8129175821b971c8440cd7c2e105` |
| `feature_stats.csv` | `787174f0a0f3c3a32b209697a9e82c896b0a1d7d74ec72ae6a7e39e276359f4b` |
| `feature_correlations.csv` | `75ee9e53e90a1388eec365c7bc63ac6fa5de834103b4cf99f5c236cf7214183a` |
| `audit_summary.json` | `34cae1185a539121fac4d53b44b2ca9e09e59293d1e1fa82c7d6f83ec4200fa4` |
| `artifact_manifest.json` | `5caf529107da32a78d77b4b073bf06ce8893257cbcb57be0534be91c8f47e98b` |

## Validation

- focused audit tests: **5 passed**;
- full pytest: **44 passed, 1 failed**;
- unrelated pre-existing failure: `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`, where starting-HEAD storage returns two revision conflicts (`raw_close` and `vendor_adj_close`) while the existing test expects one. No storage code was changed by this lane.

The branch is ready for independent ChatGPT review. No historical outcome run
is authorized by this checkpoint.
