# Ranking V4-3 — Corporate Action Admission Bridge Prep

Date: 2026-08-18
Status: `V4_3_CA_ADMISSION_PREPARED_LOCAL_VERIFICATION_PENDING`
Branch: `research/idx-ranking-v4-3-ca-admission-v1`

## Purpose

This is the final outcome-blind admission bridge between the already-frozen V4-3 execution lineage and the now-certified Corporate Action forward-price continuity gate.

It does not modify V4-0/V4-1/V4-2/V4-3 scientific semantics. It does not materialize historical R5/R10, target ranks, models, predictions, IC, Top30, spreads, bootstrap results, raw-return diagnostics, or protected-forward outcomes.

## Previously frozen V4-3 lineage

The admission contract pins the already accepted pre-target engineering identities:

- prefit runtime manifest SHA-256: `cf6f1b0c859dd21b1c0f377f45d62ecdc98165ff6e0975b852a85b11cfbcaac6`
- PIT support refresh manifest SHA-256: `7a15008ccd565678ae85c8a78ce50aac696304b9ddfaca554a35cd38e929cf0b`
- execution-code manifest SHA-256: `631a3b6f5b4ef75ddded196f1327a84cb0136b8d8316ecc86310939a1c8d6ef6`
- frozen validation identity SHA-256: `91fe0e5a1c2489d5397f9f8bef7fc999d3f83a3f0cb94b6cdb5852c1e07cd915`

The prior PIT refresh verdict remains:

`V4_3_PIT_REMEDIATED_SUPPORT_PRESERVES_FROZEN_6X100`.

## Final Corporate Action evidence admitted

External final CA root:

`D:\Documents\Project\idx-v4-ca-fren-ksei-exact-20260818-v1`

Pinned identities:

- final replay manifest SHA-256: `6cb1e660c6baa2d9b7a7aca5cece66691d5cd9564378104b618eed2cfce610ab`
- continuity summary SHA-256: `b6cdf8eb47ac1020707f4fbb4e45cbebf962876b1350d82e352b086bea0709e1`
- continuity ledger SHA-256: `bce52718fd2731142d84bbeb51beae93147746e2150015a36644dd98dcaee5bf`
- per-date SHA-256: `c84210982a0945dea1b6609e120f8768592ad8b558ad4d12d4bcb29e3dafdfee`

Required semantic result:

- verdict `V4_CA_EVENT_WINDOW_CONTINUITY_CERTIFIED`
- `corporate_action_continuity_certified=true`
- 600 frozen dates / 345,394 frozen rows / 611 frozen tickers
- 600/600 H5, H10, and consensus gate dates
- each minimum per-date continuity rate >= 0.90
- zero cross-source conflict tickers
- 602 coverage-certified / 9 unresolved tickers

The nine unresolved names are outside the material-six set and are permitted only because the already-frozen per-date continuity gate remains above 90%; they are not silently reclassified as clean.

## Fail-closed implementation

Machine-readable admission contract:

`config/ranking_v4_3_ca_admission.json`

Verifier:

`src/idx_trade/ranking_v4_3_ca_admission.py`

Runner:

`scripts/run_v4_3_ca_admission.py`

Tests:

`tests/test_ranking_v4_3_ca_admission.py`

The verifier requires byte-exact pins before semantic acceptance. It also requires the prefit execution manifest to prove that historical target/model/performance access has not already occurred.

FREN remains specifically pinned to:

- official KSEI rights schedule PDF SHA-256 `5af9284d88a7621f3b400fe7f9a28e104459ae6e710e47bf765974c940daaa91`
- exact Regular/Negotiated Market ex-right transition `2024-04-17`
- exact merger/security-cessation transition `2025-04-16`

No record-date inference, price inference, or EXCL stitching is admitted.

## Authorization boundary

Only if the local bridge returns:

`V4_3_CA_ADMISSION_PASS_HISTORICAL_EXECUTION_AUTHORIZED`

may the already-preregistered historical V4-3 execution proceed:

1. materialize frozen H5/H10 returns and target ranks;
2. fit the frozen Context25 control and Context25+Geometry3 challenger;
3. generate frozen validation predictions;
4. compute the preregistered six-fold evaluation and promotion verdict.

Even after PASS, the following remain prohibited:

- any change to target, universe, folds, purge, features, learner, hyperparameters, Top30 rules, bootstrap, or gates;
- post-result rescue/tuning;
- new provider calls as part of this execution;
- protected/fresh-forward access.

A weak or no-survivor V4-3 result is an admissible final scientific result and must not trigger an unregistered rescue.
