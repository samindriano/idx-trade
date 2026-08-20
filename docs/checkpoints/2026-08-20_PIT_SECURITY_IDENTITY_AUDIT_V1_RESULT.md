# PIT Security Identity / Listing-Domain V1 — Result

## Decision

`PIT_SECURITY_IDENTITY_OMISSION_CHANGES_V4_REPRESENTATION_TRAINING_SUPPORT_INTERSECTION_REQUIRED`

Stage B is material. The frozen V4 representation changes when the generic
authoritative historical identity overlay is supplied, so this issue is not
exonerated by the representation audit alone. No refit or scoring is
authorized by this audit.

Stage C was not run. The retained repository artifacts contain frozen
validation date identities and per-date support summaries, but no exact
per-ticker H5/H10 training-support identity artifact. Reconstructing that
identity from a target ledger would cross the task boundary; inferring it from
date-level support would not be exact. The result is therefore
`BLOCKED_EXACT_TRAINING_SUPPORT_IDENTITY_UNAVAILABLE`; a separate
outcome-blind support-identity authorization is required before continuation.

## Frozen lineage and inputs

- branch parent: `origin/research/price-basis-clean-refit-v1`
- parent commit: `a56265e452541e4d205376bbe8194f4887a920b4`
- frozen feature-builder blob: `59ad05f815870ae00480dc7945fe18371d8eff9c`
- restoration policy: `RESTORE_AUTHORITATIVE_HISTORICAL_MASTER_RIGHT_ONLY_IDENTITIES_V1`
- calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- frozen security master SHA-256: `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`
- reconciled historical master SHA-256: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- pre-reconcile master SHA-256: `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`

The generic overlay contains exactly two right-only identities:

| ticker | listed_from | listed_to | source |
|---|---:|---:|---|
| FINN | 2017-06-08 | 2021-05-05 | `IDX_DIGITAL_STATISTIC_DELISTING` |
| FREN | 2006-11-29 | 2025-04-16 | `ISSUER_OFFICIAL_IDENTITY_AND_MERGER_EVIDENCE` |

## Stage B representation audit

| Metric | Frozen master | Historical-overlay counterfactual |
|---|---:|---:|
| input panel rows | 981,940 | 981,940 |
| missing security-master exclusions | 952 | 0 |
| pre-listing exclusions | 1 | 1 |
| primary-liquid rows | 347,829 | 348,762 |
| FREN feature rows | 0 | 952 |
| FREN history-qualified rows | 0 | 933 |
| FREN primary-liquid rows | 0 | 933 |

FREN rows span `2021-04-29` through `2025-04-14`. FREN's primary-liquid
dates are therefore not a hypothetical edge case: 933 dates qualify under the
exact frozen builder. FINN has no panel rows in this input period.

Across shared ticker/date keys, `707,462` rows changed on `933` dates and
`922` tickers. All shared changes are spillover to non-FREN ticker rows;
there are `707,462` spillover rows on `933` dates and `922` tickers. The
direct addition is `952` FREN rows. The representation diff reports changes
in all 25 V4 control representation columns, including XS ranks, market
context, and market-relative fields; the exact per-column counts are in
`representation_diff.json`.

No target values, labels, predictions, performance metrics, or protected
forward artifacts were loaded. No provider/network call occurred. No model
fit, score, refit, or counter change occurred.

## External immutable artifacts

Output root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_audit_v1_20260820`

| artifact | SHA-256 |
|---|---|
| `summary.json` | `a6ac6ce333eff1617a51d3f7d1e7b96809fc156977213dc2a77a1a1d122f64dd` |
| `identity_overlay.csv` | `eb4050dffccfe3beb649f5f9d13eb9631be8ccfcf85751f942e936a72ce2ede8` |
| `representation_diff.json` | `a13940e40e7e50ff7f6ee6edf2b9574a1a08928f7754df0e9458a43748adaea8` |
| `MANIFEST.json` | `f81e0a0b8e30cddba7b9bb58d378fd06800d4cc61a50d71cf279c9c7f0885489` |

The manifest records `outcome_blind=true`, `provider_calls=false`,
`model_fit=false`, `model_scoring=false`, and
`protected_forward_accessed=false`.

## Stop condition

The current V4-X model lineage must remain locked. Stage C requires an exact
per-ticker H5/H10 training-support identity artifact, preferably already
frozen and target-free. The existing date-level support summaries are not a
substitute. Do not load a target ledger or infer row identities in this lane.
