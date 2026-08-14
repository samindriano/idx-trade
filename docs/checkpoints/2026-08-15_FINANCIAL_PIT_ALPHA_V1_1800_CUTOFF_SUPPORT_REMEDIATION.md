# Financial PIT Alpha V1 — 18:00 cutoff and inherited-fold support remediation

Status: `FINANCIAL_PIT_ALPHA_V1_SUPPORT_CENSUS_CONDITIONALLY_ACCEPTED_CUTOFF_AND_RUN_SPEC_REWORK_REQUIRED`

Result state: `OUTCOME_BLIND_SUPPORT_REMEDIATION_COMPLETE_REVIEW_REQUIRED`

This checkpoint records the requested cutoff and run-spec remediation. It does
not authorize fitting, scoring, loading labels, or opening performance metrics.

## Scope and boundaries

- Branch: `research/idx-financial-pit-alpha-v1`
- Clean V2 parent: `outcome_blind_common_support.parquet`, SHA-256
  `6590686c6790b81abf204b2fc4228e2bb8b3039a7d18c573ec116aee7c117ab6`
- Accepted Financial feature panel SHA-256:
  `1d60ee69070546d21040af8c61f2170c5cca2254f131626a19bf4c1d59f3f023`
- Accepted Financial panel manifest SHA-256:
  `639fc6e6fe3f7f853d23b6f5244c98ec8ed5c63b219aa59e698c8db908fb2140`
- External census root:
  `D:\Documents\Project\idx-financial-pit-alpha-20260815-v1-census-1800`
- Network/provider calls: `0`
- Labels/outcomes/scores/performance metrics: not accessed
- Financial PIT source/materialization artifacts: unchanged

## Cutoff remediation

The previous contract used the end of the Asia/Jakarta civil day. The
remediated contract is:

`SESSION_DATE_18_00_ASIA_JAKARTA_UTC_EXACT`

For every normalized session date `t`, the decision cutoff is exactly
`18:00:00 Asia/Jakarta` converted to UTC. A Financial state is eligible only
when `reporting_knowledge_at_utc <= session_t_18_00_WIB`. A post-18:00 filing is
not rescued into session `t`; it first becomes eligible on a later session.

Comparison against the preserved previous census:

| Measure | Previous 23:59 | Remediated 18:00 | Change |
|---|---:|---:|---:|
| support rows | 70,556 | 70,520 | -36 |
| support tickers | 321 | 321 | 0 |
| same-day knowledge rows | 1,377 | 966 | -411 |
| same-day rows after 18:00 retained | 411 | 0 | -411 |
| gained rows | — | 0 | — |
| knowledge-time violations | — | 0 | — |

The 36 lost support rows are one row each for: `AADI`, `ADRO`, `APIC`,
`AWAN`, `BIPI`, `BMTR`, `BREN`, `BRMS`, `DATA`, `DOID`, `DSNG`, `EMTK`,
`FILM`, `FORE`, `GPSO`, `HEAL`, `HILL`, `HRTA`, `HRUM`, `INDF`, `INDY`,
`INET`, `KAEF`, `MAPI`, `MBMA`, `MDKA`, `MEDC`, `MNCN`, `PTBA`, `RAJA`,
`RATU`, `RMKE`, `SMGA`, `TAPG`, `UNTR`, and `VISI`. No support row or ticker
was gained.

The remediated support identity key SHA-256 is
`f0fc75a6e4dc5056eed3b1acd38d00f4273ff184891e5ff579d62489f1b83c58`; the
materialized comparison support key SHA-256 is
`b1257db0a2fc175aab010f1ab1a925e3c7d949b43fe1dd332874382fd09ec00d`.

There are 6 source-level Financial timestamp conflict keys in the census.
The exact latest-selected 52-slot matrix has 0 ambiguous selected joins; the
6 source conflicts are retained as diagnostics and are not silently repaired.

## Frozen 52-slot matrix and candidates

The matrix contains exactly 13 feature IDs × 4 period strata (`Q1`, `H1`,
`9M`, `FY`). For each V2 row and slot, the resolver selects the latest eligible
state under the 18:00 cutoff, with provenance retained. Fiscal year, knowledge
timestamp, filing age, and source/version evidence are diagnostics only.

Missing handling is frozen to the clean V2 preprocessing family:
fold-local-median `SimpleImputer`, missing indicators, and
`keep_empty_features=True`, with statistics fitted within each training fold.

| Candidate | Raw features | Feature-order SHA-256 |
|---|---:|---|
| `CONTROL` | 25 | `1107bf6a65d0b2c86128de7c1123c876ffc9c5e19471b6f32852727f8c5b9a72` |
| `FINANCIAL_ONLY` | 52 | `c64b5fddf12e86b4d21d39d13eace81d44fac1bda4a4f9497c577e1deb489188` |
| `V2_PLUS_FINANCIAL` | 77 | `7704275d3ec85ecc09f6e20b5abac27d9ea6e70cc274bd24949f133d7faee0ec` |

Candidate contract JSON SHA-256:
`a55526407183449e25f8334c03b4dd0d76ed9b95eb3041aa079217c2c9d4468a`.

The frozen clean V2 model identity remains `HGB_XS_MARKET` with the existing
hyperparameters. No candidate was fit.

## Inherited V2F1–V2F6 support census

The inherited folds were preserved exactly:

`V2F1 1–504 / purge 505–524 / validation 525–624`; then the same 120-session
step through `V2F6 1–1104 / purge 1105–1124 / validation 1125–1224`.

The table reports observed V2 rows and the number of rows with at least one
available Financial feature; `slot rate` is available 52-slot values divided
by rows × 52.

| Fold | Block | V2 rows | V2 tickers | Financial rows | Financial tickers | Slot rate | Empty slots | All-missing slots |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| V2F1 | train | 104,153 | 523 | 0 | 0 | 0.000000 | 52 | 0 |
| V2F1 | purge | 4,050 | 258 | 0 | 0 | 0.000000 | 52 | 0 |
| V2F1 | validation | 21,478 | 337 | 0 | 0 | 0.000000 | 52 | 0 |
| V2F2 | train | 129,681 | 574 | 0 | 0 | 0.000000 | 52 | 0 |
| V2F2 | purge | 4,456 | 277 | 0 | 0 | 0.000000 | 52 | 0 |
| V2F2 | validation | 20,023 | 313 | 388 | 33 | 0.003295 | 39 | 3 |
| V2F3 | train | 154,160 | 611 | 388 | 33 | 0.000428 | 39 | 3 |
| V2F3 | purge | 3,764 | 249 | 698 | 48 | 0.031278 | 39 | 3 |
| V2F3 | validation | 20,244 | 296 | 9,628 | 168 | 0.115978 | 13 | 9 |
| V2F4 | train | 178,168 | 632 | 10,714 | 168 | 0.014209 | 13 | 9 |
| V2F4 | purge | 4,369 | 266 | 2,590 | 157 | 0.213414 | 13 | 9 |
| V2F4 | validation | 20,159 | 304 | 12,174 | 180 | 0.272666 | 0 | 9 |
| V2F5 | train | 202,696 | 664 | 25,478 | 203 | 0.044207 | 0 | 9 |
| V2F5 | purge | 3,927 | 251 | 2,400 | 154 | 0.383058 | 0 | 9 |
| V2F5 | validation | 25,179 | 439 | 15,353 | 252 | 0.417777 | 0 | 3 |
| V2F6 | train | 231,802 | 705 | 43,231 | 274 | 0.090526 | 0 | 3 |
| V2F6 | purge | 6,353 | 412 | 3,712 | 239 | 0.425668 | 0 | 3 |
| V2F6 | validation | 32,986 | 499 | 19,812 | 287 | 0.463402 | 0 | 0 |

This makes `FINANCIAL_ONLY` scientifically unusable under the inherited
folds: V2F1 has no Financial support in train or validation, and V2F2 has no
Financial support in train (with only 388 validation rows). `V2_PLUS_FINANCIAL`
can technically retain empty columns under the imputer contract, but the
Financial challenger family is not uniformly supportable across the inherited
folds. Per the frozen instruction, no new folds are invented and no metrics
are authorized until ChatGPT reviews this blocker.

The support artifact records are:

- Census summary SHA-256:
  `e33ded6fcd6b12c6083c8e877ae78ce4a82d05279a4f3b62aee04f7f25d28343`
- Join diagnostics SHA-256:
  `6822a00e700b506bfa70a63422c2ee9498310045330fcb3ef2c89afed74a76bc`
- Selected 52-slot matrix SHA-256:
  `464c2a18bd7b238f98c786365026466bfd52c514022b3ced09798b2654665471`
- Support census manifest SHA-256:
  `12550704487104f96be4e708649d3d6a7cc6a767feb73d42e5ede86a2276eb18`
- Inherited-fold census SHA-256:
  `afecdbabdfda5545432e4629a725d4e3c6b5dd0c1fdcda8869c3103cd725cdd2`
- Inherited-fold manifest SHA-256:
  `713ec8a5a2d17423a1367eaa7b752ad4efcab9badb0a02a78bcb6f1cb9fdb93f`

## Decision and stop boundary

`CONTROL` is definitionally frozen. The Financial challengers are not
authorized for fitting because at least one inherited fold is unusable for the
Financial support contract. This task therefore stops at the outcome-blind
support census and requests independent ChatGPT review.

No labels, outcomes, scores, performance metrics, model fits, provider calls,
fresh-forward artifacts, V3-B/O2 artifacts, or Financial source/materialization
artifacts were accessed or changed.
