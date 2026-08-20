# PIT Security Identity — Stage C Exact V4-X Training-Support Intersection Result

## Decision

`V4_X_EXACT_TRAINING_REPRESENTATION_AFFECTED_BY_SECURITY_IDENTITY_OMISSION`

The exact frozen H5/H10 training-support intersection is materially affected
by the generic historical identity omission through shared cross-sectional
representation. A clean V4-X refit is required after the identity and other
cross-lane changes are consolidated. No refit, scoring, replay, or forward
counter update was performed here.

## Frozen lineage and inputs

- Stage-B result HEAD: `0e778d2311eba01e66966f3440262d9ea50cc8e2`
- Stage-B manifest SHA-256: `f81e0a0b8e30cddba7b9bb58d378fd06800d4cc61a50d71cf279c9c7f0885489`
- Stage-C preregistration/runner initial commit: `5de764404b98c6c8671659e867ee7b5d7d87cc5c`
- Stage-C final code HEAD: `994da22` (preflight-only parser corrections included)
- V4-X config blob: `7bfca6b0805e680092c7f8baa6efcd39998482d6`
- final-refit runner blob: `2d538c1c99fb348b87d6c268e2df821b9099d203`
- frozen feature-builder blob: `59ad05f815870ae00480dc7945fe18371d8eff9c`
- target-state parquet SHA-256: `f7b0b0f29616f6f12615d87925f116218f4a2e01c97ef64bb8e1fc4984f30d1c`
- per-date support SHA-256: `ac11a75c891b965db14c6b6ea8f64da10ad08c492c7a6410fbd77d790a6e28e4`
- prefit manifest SHA-256: `0c222a10d8c48852f53451f0ce0bdec44b1156b8b9050c536f51b416ff18cfcc`
- calendar SHA-256: `661d3f19d0dc427d2a8b5c832594de5d43c9433ffac414f35835f47c9faaf09a`
- panel SHA-256: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`
- frozen/pre-reconcile security master SHA-256: `c8efa462c5fee94a92aca7e5915513fdb8be6d04c2264021bab47bf1cc50a240`
- reconciled historical security master SHA-256: `9d0d30215ab129f196f494e4af499fff92fe510f5a432dd2dad321f02ff7a2f9`
- Stage-B representation diff SHA-256: `a13940e40e7e50ff7f6ee6edf2b9574a1a08928f7754df0e9458a43748adaea8`

The target-state parquet was read only through the authorized projection:
`ticker,date,target_state_h5,target_state_h10`. Numeric returns, ranks and
other target columns were not loaded. Per-date support was read only as
`session_index,date,h5_eligible,h10_eligible`.

## Exact support

Support selection was exact equality to the frozen available state on frozen
eligible dates. The required eligible-date counts were met:

| head | eligible dates | support rows | support tickers |
|---|---:|---:|---:|
| H5 | 986 | 241,487 | 629 |
| H10 | 982 | 239,836 | 629 |

All selected support identities had a counterfactual primary representation.
All non-direct support identities also had a base primary representation. No
support-presence gap was found.

## Stage-B representation re-derivation

The historical identity overlay was re-derived generically and matched the
accepted Stage-B counts: FINN and FREN were the two right-only identities;
FREN contributed 952 direct feature rows, and 933 changed/spillover dates.
The exact representation comparison matched:

| quantity | value |
|---|---:|
| direct new rows | 952 |
| changed shared rows | 707,462 |
| spillover changed rows | 707,462 |
| changed dates | 933 |
| changed tickers | 922 |
| base primary rows | 347,829 |
| counterfactual primary rows | 348,762 |

## Exact support intersection

The direct FREN rows do not themselves occur in the exact final H5/H10
training support. The support impact is nevertheless material through the
shared cross-sectional spillover representation:

| head | affected rows | direct FREN rows | spillover rows | affected tickers | affected dates | row fraction | date fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| H5 | 153,037 | 0 | 153,037 | 555 | 688 | 63.3728% | 69.7769% |
| H10 | 151,788 | 0 | 151,788 | 555 | 684 | 63.2882% | 69.6538% |

The union across heads contains 153,136 unique `(ticker,date,impact_type)`
rows, 555 tickers, and 688 dates, from `2022-02-11` through `2025-04-14`.
All union impact rows are `SPILLOVER`; direct FREN support intersection is
zero.

## External immutable artifacts

Output root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_security_identity_stage_c_v1_20260820`

- `MANIFEST.json`: `5d3bce5ce8776d68a356ea814aa2dcd8909cb26b8d3334ea5e3f68f089a5fe61`
- `summary.json`: `c4d55545066bb28401246ec0ff217c6bf2a36a77372cedd158fe7ca579bfb4c5`
- `h5_support_identities.csv`: `2c2874bde129f8cefb68af1aae01ab88203dfe74c2bc8cf4cf3e5bab61e76ede`
- `h10_support_identities.csv`: `606eae2a431d0b924f7dbe574cbca493f1b857bf55aeb0d1af74db3d01c03386`
- `affected_representation_identities.csv`: `565111725b6ba2f4715793c9b528825077e4dd382090ff9f5d3362dc63a04aa2`
- `h5_intersection.csv`: `2a75b06304af61153849be74efafc94336ec7cc71a13d8d0054d26331840dbb5`
- `h10_intersection.csv`: `0428946bd55fa444cbd684ec99bade430c00b955730a30995384e3e9607c2d80`
- `union_intersection.csv`: `eba7343b7bf7bc956b0cca505da275d8cd3bd3c239d8207313dbd3b2febd37a8`
- `support_presence_gaps.csv`: `cd0798331ab7df75e2036f534982cf783c09d9734de8adb2fc8f44ec86edf938` (empty gaps artifact)

## Guardrails

- target numeric values loaded: `false`
- forbidden target columns loaded: `[]`
- provider/network calls: `false`
- model fit/scoring/predictions/performance metrics: `false`
- protected/fresh-forward outcomes: `false`
- forward counter mutation: `false`

