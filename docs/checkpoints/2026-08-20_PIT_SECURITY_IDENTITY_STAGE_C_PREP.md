# PIT Security Identity — Stage C Exact V4-X Training-Support Intersection V1

## Frozen status

This checkpoint freezes the outcome-blind Stage C contract before any support
intersection rows are inspected.

- Stage-B branch: `audit/pit-security-identity-v1`
- Stage-B result HEAD: `0e778d2311eba01e66966f3440262d9ea50cc8e2`
- Stage-B manifest SHA-256: `f81e0a0b8e30cddba7b9bb58d378fd06800d4cc61a50d71cf279c9c7f0885489`
- Stage-C branch: `audit/pit-security-identity-stage-c-v1`
- V4-X config blob: `7bfca6b0805e680092c7f8baa6efcd39998482d6`
- final-refit runner blob: `2d538c1c99fb348b87d6c268e2df821b9099d203`
- frozen V4 feature-builder blob: `59ad05f815870ae00480dc7945fe18371d8eff9c`

The deterministic Stage-B re-derivation uses the same pinned inputs:

| representation input | SHA-256 |
|---|---|
| official calendar | `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a` |
| canonical panel | `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76` |
| frozen security master / pre-reconcile master | `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240` |
| reconciled historical security master | `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9` |

## Frozen authorized inputs

| input | path | SHA-256 |
|---|---|---|
| target-state corpus | `D:\Documents\Project\idx-v4-3r-historical-one-shot-20260819-v1\v4_3r_target_ledger.parquet` | `f7b0b0f29616f6f12615d87925f116218f4a2e01c97ef64bb8e1fc4984f30d1c` |
| prefit per-date support | `D:\Documents\Project\idx-v4-3r-ca80-prefit-support-20260819-v1\v4_3r_ca80_full_target_support_per_date.csv` | `ac11a75c891b965db14c6b6ea8f64da10ad08c492c7a6410fbd77d790a6e28e4` |
| prefit manifest | `D:\Documents\Project\idx-v4-3r-ca80-prefit-support-20260819-v1\MANIFEST.json` | `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc` |
| Stage-B representation diff | `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_audit_v1_20260820\representation_diff.json` | `a13940e40e7e50ff7f6ee6edf2b9574a1a08928f7754df0e9458a43748adaea8` |
| Stage-B manifest | `D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_audit_v1_20260820\MANIFEST.json` | `f81e0a0b8e30cddba7b9bb58d378fd06800d4cc61a50d71cf279c9c7f0885489` |

The target-state parquet is accessed only with the projection
`ticker,date,target_state_h5,target_state_h10`. Its numeric target/rank
columns are forbidden and are never loaded. The per-date projection is only
`session_index,date,h5_eligible,h10_eligible`.

## Exact rules

H5 support is the unique `(ticker,date)` set where `h5_eligible == true` and
`target_state_h5 == TARGET_H5_AVAILABLE`. H10 uses the corresponding H10
columns and `TARGET_H10_AVAILABLE`. Eligible-date counts must be exactly 986
and 982. Duplicate identities, invalid dates/states, hash mismatches, or
unexpected columns fail closed.

Stage-B affected identities are derived exactly from the frozen Stage-B
feature builder and pinned inputs if the Stage-B artifact does not contain
row identities. Direct identities are newly admitted FREN rows. Spillover
identities are shared non-FREN `(ticker,date)` keys with any changed frozen
representation cell. No approximation from changed dates is allowed.

The original X1 merge semantics are audited by checking that every selected
support identity has an exact base/counterfactual model-frame representation.
No target rank, return, label, prediction, metric, or model operation is
allowed.

## Decision rule

- zero affected exact final-training identities in both heads:
  `PIT_SECURITY_IDENTITY_REPRESENTATION_CHANGE_OUTSIDE_V4_X_EXACT_TRAINING_SUPPORT`
- one or more affected exact identities in either head:
  `V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`
  and record `EVENTUAL_CLEAN_REFIT_REQUIRED_AFTER_CROSS_LANE_CONSOLIDATION`.

No refit, scoring, historical performance, provider call, counter mutation,
or protected/fresh-forward access is authorized.
