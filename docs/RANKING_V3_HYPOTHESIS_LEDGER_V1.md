# Ranking V3 Hypothesis Ledger V1

Status: **V3-A F1-F4 DISCOVERY COMPLETE, 3 CANDIDATES EVALUATED**

This ledger was created with the recency specification. Ordinals `001`-`003`
were executed exactly once on V2F1-V2F4 after the mandatory control-equivalence
gate passed. The cumulative evaluated counter is now `3`. These are historical
development results, not independent validation.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact uniform V2 `HGB_XS_MARKET` control | `COMPLETE` | `true` | `CONTROL_REFERENCE` |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | normalized exponential decay, H=252 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | normalized exponential decay, H=504 official sessions | `COMPLETE` | `true` | `KEEP_DIAGNOSTIC` |

## Executed result identity

- parent hypothesis: `RANKING_V2_HGB_XS_MARKET`;
- run/source commit: `362510997e3db41e81b21ec8e7422308338fbef1`;
- implementation code commit: `3e368f7d7d6fa1e8ce0d076039640aaeef06a27f`;
- spec SHA-256: `53c5bc3e90af12fea62a73815e1e85352e836d69938ce0e9287437a52c1d58fa`;
- review addendum Git blob: `1ee532c849636c47dab12ba3702ce7590abfcd74`;
- prepared cache SHA-256: `522f17b2aa4a15f51b503c1a0920dc68290b4b34425a12afaeb8b2bfd5cdd5e5`;
- prepared manifest SHA-256: `6b404f14a76843f1868579406c9660aaeb85cd4823e9021e13967ed0424f6143`;
- fold set: `V2F1-V2F4` only;
- feature-order hash: `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72` (SHA-256 of the canonical JSON array in frozen order);
- model identity: exact `HGB_XS_MARKET`, frozen V2 preprocessing/HGB parameters, random seed `42`;
- metrics artifact: `ranking_v3_a_recency_f1_f4_metrics.csv`;
- metrics artifact SHA-256: `fe22292ebad0d553042eb8f48faf3ddb13584e8062776a46d63adfd55bf8c603`;
- runtime environment: Python `3.13.5`, NumPy `2.4.2`, pandas `2.3.3`, PyArrow `23.0.1`, scikit-learn `1.8.0`, Windows 11;
- output directory: `D:\Documents\Project\idx-trade-data-gate-20260808v\ranking_v3_recency_discovery_20260810_retry1`.

All three rows use `result_status=COMPLETE`, `result_viewed=true`,
`cumulative_candidate_count=1/2/3`, and fold-local mean-one normalization.
The control uses `uniform_1.0`; H=252 and H=504 use `2**(-age/H)`.

## Required row schema after authorization

Every executed row must add, without deleting prior rows:

`hypothesis_id`, `parent_hypothesis`, `candidate_id`, `candidate_ordinal`,
`spec_sha256`, `spec_commit`, `cache_sha256`, `cache_manifest_sha256`,
`fold_set`, `feature_order_hash`, `model_identity`, `weight_formula`,
`weight_normalization`, `result_status`, `result_viewed`, `metrics_artifact`,
`artifact_sha256`, `verdict`, `cumulative_candidate_count`, `code_commit`,
`environment`, and `notes`.

The counter increments only when a candidate is actually run. A failed run,
viewed result, or killed candidate remains in the denominator permanently.
