# Ranking V3 Hypothesis Ledger V1

Status: **SPECIFIED, ZERO CANDIDATES EVALUATED**

This ledger is created with the recency specification. It contains no model
results and no outcome access. The cumulative evaluated counter is `0` at
freeze. The three ordinals are pre-registered slots and are not evidence.

| Ordinal | Hypothesis | Candidate | Definition | Status | Result viewed | Verdict |
|---:|---|---|---|---|---|---|
| 001 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-CONTROL-001` | exact uniform V2 `HGB_XS_MARKET` control | `SPECIFIED_NOT_RUN` | `false` | pending run |
| 002 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL252-002` | normalized exponential decay, H=252 official sessions | `SPECIFIED_NOT_RUN` | `false` | pending run |
| 003 | `V3-A-RECENCY-V1` | `V3-A-RECENCY-V1-HL504-003` | normalized exponential decay, H=504 official sessions | `SPECIFIED_NOT_RUN` | `false` | pending run |

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
