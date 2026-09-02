# INC-001 transition-capability probe — V1

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Controlling implementation/input head: `f6f4ec027665fe8c33632cc211923a7d6503a7e2`

This is a bounded representative official-source capability probe in the
existing INC-001 / V1.1 lane. It is not a new audit phase and does not replace
the V1.1 census. No further IDX acquisition, KSEI bulk acquisition, Phase-E,
outcome/target access, model fit/refit/scoring, counter mutation, canonical
historical rewrite, taxonomy expansion, or merge was performed.

## Control and immutable evidence

The implementation head was already pushed and verified equal to the remote:

```text
REMOTE_HEAD = f6f4ec027665fe8c33632cc211923a7d6503a7e2
branch      = data/ca-aware-feature-basis-remediation-v1
remote      = origin/data/ca-aware-feature-basis-remediation-v1
```

The new immutable probe root is controlling for this bounded capability result:

```text
D:\Documents\Project\idx-ca-transition-capability-probe-20260829-v1
MANIFEST SHA-256: 4949b9e501d0c751f9c7a51093daa88a0cbcb0da87d132836ffe0dd9894bc8dd
```

It contains 8 deterministic selections, 6 retained KSEI index responses, 3
downloaded/hash-bound official PDFs with rendered page-1 checks, request
ledgers, exact linkage results, capability summary, and the prospective plan.
Selection was made from the immutable unresolved ledger before provider lookup:
at most the earliest and latest candidate per requested family, tie-broken by
event identity.

## Required result fields

```text
REMOTE_HEAD = f6f4ec027665fe8c33632cc211923a7d6503a7e2

RIGHTS_HMETD_SOURCE_CAPABILITY = PARTIAL_HISTORICAL_CAPABILITY
RIGHTS_HMETD_SAMPLE_TESTED = 2
RIGHTS_HMETD_SAMPLE_RESOLVED = 1
RIGHTS_HMETD_ESTIMATED_LOOKUP_COVERAGE = 1/72 strict local exact-lookup floor; 71 remain uncertified; no extrapolation

STOCK_SPLIT_SOURCE_CAPABILITY = HISTORICAL_SOURCE_PATH_PROVEN
STOCK_SPLIT_SAMPLE_TESTED = 2
STOCK_SPLIT_SAMPLE_RESOLVED = 2
STOCK_SPLIT_ESTIMATED_LOOKUP_COVERAGE = 2/41 representative exact lookups proven across 2021 and 2026; 39 require individual evidence

MANDATORY_CONVERSION_SOURCE_CAPABILITY = CAPABILITY_NOT_PROVEN
MANDATORY_CONVERSION_SAMPLE_TESTED = 2
MANDATORY_CONVERSION_SAMPLE_RESOLVED = 0
MANDATORY_CONVERSION_ESTIMATED_LOOKUP_COVERAGE = 0/39 exact transition lookup proven

VOLUNTARY_CONVERSION_SOURCE_CAPABILITY = CAPABILITY_NOT_PROVEN
VOLUNTARY_CONVERSION_SAMPLE_TESTED = 2
VOLUNTARY_CONVERSION_SAMPLE_RESOLVED = 0
VOLUNTARY_CONVERSION_ESTIMATED_LOOKUP_COVERAGE = 0/93 exact transition lookup proven

PHYSICAL_EVENT_CENSUS = 412
BASELINE_RESOLVED_TRANSITIONS = 121
BASELINE_UNRESOLVED_TRANSITIONS = 291
```

The lookup figures are conservative local evidence floors, not a claim that
the remaining rows can be resolved without individual source evidence.

## Representative linkage

Three events have newly staged, exact, hash-bound transition evidence in this
probe. The controlling 121/291 census is intentionally unchanged pending a
separately authorized census reconciliation:

| event | family | official evidence | accepted transition |
|---|---|---|---|
| `2d3d3f62ee9f5553dcbe3cf5db962eefbfdf6437f37cc1185edb3c1c3a0877e0` / PGJO | `RIGHTS_HMETD` | `KSEI-2833/JKU/0221`, SHA-256 `bb851721306564f397ee1eca85ea9ba064d28308af0b9adcf438de716d0757ca` | 2021-02-25, explicit `Tanggal Ex di Pasar Regular dan Pasar Negosiasi` |
| `38b59adf7e0ede37b0cd1d102f941783adcc0d308dfa4a1c758a5678031e159a` / ERAA | `STOCK_SPLIT` | `KSEI-4844/JKU/0321`, SHA-256 `1649b8927cef483522b47ba4bf987d361f719b5970a37f2419baea693c4701b2` | 2021-03-31, explicit first trading with new nominal in the regular/negotiation market |
| `be7065dfbb3f479026d0701928b1eb26bc39de606e4e2e2bc20b4b925442a16a` / MLPT | `STOCK_SPLIT` | `KSEI-18691/JKU/0726`, SHA-256 `3d98ae958b06fa191ed21e5e2bc89ad4695631aaaad345e2c814d60252c25b11` | 2026-07-21, explicit first trading with new nominal in the regular/negotiation market |

The other five selected rows remain unresolved. The ERAA document is a
stock-split document and is not transferred to the selected ERAA mandatory
conversion row. KETR retained tender documents establish tender/payment
context but no regular-market basis transition. BNBR and BRIS sampled index
requests returned HTTP 500; there was no retry or document acquisition. PACK
had no selected-ticker match in the sampled MASR index. Candidate dates remain
candidate dates and were not promoted.

The exact row-level evidence is in
`representative_linkage_results.csv` and the index/document linkage audit is
in `provider_index_matches.csv` under the immutable root.

## Future acquisition geometry

The prospective plan reconciles exactly to all 291 baseline unresolved physical
events. The 8-row capability probe is separate from later bulk acquisition;
the 3 exact sample results do not subtract from the controlling baseline.

| family | baseline unresolved | later event-level acquisition |
|---|---:|---:|
| `RIGHTS_HMETD` | 72 | 72 |
| `STOCK_SPLIT` | 41 | 41 |
| `MANDATORY_CONVERSION` | 39 | 39 |
| `VOLUNTARY_CONVERSION` | 93 | 93 |
| `CAPITAL_RESTRUCTURING` | 19 | 19 |
| `BONUS_SHARES` | 11 | 11 |
| `STOCK_DIVIDEND` | 7 | 7 |
| `MERGER` | 5 | 5 |
| `UNKNOWN_TAXONOMY` | 4 | 4 |
| **Total** | **291** | **291** |

No later bulk acquisition is authorized by this checkpoint. Any future request
must use the immutable event identities, not convenient sampling, and must be
separately authorized.

## Authority and scientific state

```text
IDX_NEGATIVE_NO_EVENT_AUTHORITY = UNSUPPORTED_FOR_CURRENT_SNAPSHOT_AS_HISTORICAL_NEGATIVE_AUTHORITY
IDX_HISTORICAL_ASOF_AUTHORITY   = UNKNOWN
KSEI_REGISTERED_SECURITY_COMPLETENESS = UNKNOWN

DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE

FULL_291_ACQUISITION_AUTHORIZED = FALSE
PHASE_E_AUTHORIZED              = FALSE
REFIT_AUTHORIZED                = FALSE
COUNTER_ACTION                  = NONE
```

## Validation and stop

- Artifact validation passed: 23 manifest-listed files, all byte lengths and
  SHA-256 values verified; 8 linkage rows and 3 exact resolutions verified;
  plan total verified as 291.
- `git diff --check` passed.
- `python -m py_compile src/idx_trade/ca_source_authority_audit_v11.py
  src/idx_trade/ca_aware_feature_basis_r3.py` passed.
- Exact-head GitHub Actions for the pushed implementation head succeeded:
  run `33241262804`, job `99070891938`, 334 passed. The only reported warning
  was the GitHub Actions Node.js 20 deprecation warning for checkout/setup-
  python being forced to Node.js 24; it was not a test failure.
- No code or census file was changed by this probe. The handoff/checkpoint
  documentation is local and is not pushed in this stop state.

This checkpoint is complete and returned for ChatGPT review. Stop here; do not
perform further IDX acquisition, KSEI bulk acquisition, Phase-E, outcomes or
targets, model work, counter action, canonical historical rewrites, taxonomy
expansion, or PR merge.
