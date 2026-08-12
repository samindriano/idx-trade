# Reliability / Uncertainty V0 — Historical Diagnostic Result

Date: 2026-08-13 (Asia/Jakarta)  
Branch: `research/idx-reliability-uncertainty-v0`  
Frozen specification: `37259c68e22d5703f6fae6738785dee87886e63c`

## Decision

`RELIABILITY_V0_FEASIBILITY_GO`

The diagnostic was executed exactly once against the pinned historical O2,
V3-B, and Open artifacts. No proxy, threshold, gate, feature, or runtime
semantics were changed after the result was observed.

Only the primary proxy `score_margin_reliability` qualified. The second
primary proxy, `joint_marginal_support_reliability`, did not qualify.

## Frozen input contract

| Input | SHA-256 |
|---|---|
| O2 geometry artifact manifest | `cc26bc689dd37bc83cc2c32d348d3201e5c4f41577f4bb8f938ab5cac2c7a97a` |
| O2 OOF predictions | `fe02c0c743e7bfc5a57b1c8e731c5685a4bff5f9854f910f88703b15a6ca8f0c` |
| O2 common-support rows | `59b95ad907a8adc911bbf2a411cb1b52a433bd3d225927268440a11b958f6c6f` |
| O2 fold definitions | `f16ddd1640701b206cb10418ca9fa7736695fe8268ac5c38213ba22b1fe76046` |
| O2 feature manifest | `9014166635a7365d6f0a101132648c24637b04a6af2455063f3f37eee6586f04` |
| V3-B training table | `5893c9f2872aae0f33acd4104d82ee8c1d4474aae7d54e9d01879724b86dffbe` |
| V3-B training manifest | `4e84ce02c6ee856c0f260dd6099b2a479723c53da82131ae669e0bf7e4d384f9` |
| Open coverage/readiness rows | `d9b2da0b1831b8fe087fe8ee9093e6ce7f649dd0c6c3f6f378cebe23e5694242` |
| O2 feature order | `a2f04da9100eca4c3896330c2188df0e5afa6371f9a4baec2f4fea10495b980f` |
| Common-support key | `716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a` |

The Open coverage artifact contained 292,633 rows, of which 278,168 were
Open-feature-ready and used to reconstruct the exact common support. The
accepted O2 OOF input contained 140,679 rows. The historical cutoff remained
2026-07-31.

## Primary proxy metrics

The rows below are the six frozen folds, in order. Each fold had 100 eligible
sessions after the frozen minimum-row and two-class session filter.

| Fold | `score_margin_reliability` Spearman | Q4−Q1 lift | 40% selective lift | Conditional lift |
|---|---:|---:|---:|---:|
| V2F1 | 0.081850 | 0.035195 | 0.013157 | 0.001153 |
| V2F2 | 0.062493 | 0.032099 | 0.011739 | 0.007624 |
| V2F3 | 0.060163 | 0.024922 | 0.010190 | 0.008324 |
| V2F4 | 0.028562 | 0.018043 | 0.006529 | 0.003888 |
| V2F5 | 0.050241 | 0.023549 | 0.011250 | 0.011740 |
| V2F6 | 0.046900 | 0.028080 | 0.013286 | 0.007029 |

Gate aggregates for `score_margin_reliability`:

- median fold-median session Spearman: `0.055202`
- q25 fold-median session Spearman: `0.047736`
- positive Spearman folds: `6/6`
- median fold-mean Q4−Q1 quality lift: `0.026501`
- positive Q4−Q1 folds: `6/6`
- median fold-mean 40% selective quality lift: `0.011495`
- positive selective-lift folds: `6/6`
- median fold-mean conditional quality lift: `0.007326`
- positive conditional-lift folds: `6/6`
- qualification: `true`

For `joint_marginal_support_reliability`, the corresponding gate aggregates
were Spearman median `-0.072706`, q25 `-0.087514`, `0/6` positive Spearman
folds, Q4−Q1 median `-0.047596`, selective median `-0.015877`, and
conditional median `-0.008215`; qualification was `false`.

## Runtime boundary

The persisted runtime flags are all false:

- no provider calls;
- no O2 refit or rescore;
- no reliability model fit;
- no composite reliability score;
- no trade-filter optimization;
- no fresh-forward outcomes;
- no `FORWARD_OUTCOME_ACCESS_STARTED` marker.

## External output

Output directory:

`D:\Documents\Project\idx-trade-data-gate-20260808v\reliability_uncertainty_v0_20260813_001`

The artifact manifest and every child artifact were independently SHA-verified.

| Artifact | SHA-256 |
|---|---|
| `artifact_manifest.json` | `09b0f927821c3f594d74d07f2bd6d2b03fd2bcce13366f0cc9231d3912db7eb1` |
| `aggregate_decision.json` | `ecda04c26251957756b4bc32e5af15d621337b8f81a8763ccff39c69dc6cb70a` |
| `fold_proxy_metrics.csv` | `d7593e975b8076db7ea35ef576a467e50928dd4417f556015f600e46e24c42d0` |
| `preflight_contract.json` | `e41eb7a7249a196d321a12ef7da4e85a0e5eb2b4193d3be085e6b4ad866d9e09` |
| `proxy_gate_summary.csv` | `bc76d3aed09d071f8560b49aef1392ef53ac77904baabbf9fd45468f496659fe` |
| `proxy_rows.parquet` | `84f94df0ec0586a71a7be63de7f181b5933a515014e194d41c8d29d4cd5937ae` |
| `session_metrics.csv` | `da0019c7828ac14794989819b5806c7b58fd01d25bbee024608719fac5a8700f` |

## Validation

The Reliability V0 focused suite passed: `8 passed`. The final full suite
passed: `48 passed, 0 failed, 0 warnings` in `1.53s`.

The full-suite run required an engineering-only test-fixture correction:
the existing storage implementation intentionally preserves independent
`raw_close` and `vendor_adj_close` revision conflicts, so its test now expects
both conflicts. This did not alter Reliability V0 code or research semantics.
