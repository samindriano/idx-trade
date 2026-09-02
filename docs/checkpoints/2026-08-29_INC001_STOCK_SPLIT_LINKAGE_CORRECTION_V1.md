# INC-001 stock-split linkage correction — V1

Date: 2026-08-29  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Implementation input HEAD: `014558407c249af92730d648e69663c7eef1c8bf`

This is a bounded, outcome-blind reconciliation correction using only already
retained bytes. It corrects a successor-builder linkage freeze after stronger
official discovery evidence proved two additional cross-source
representations. No provider call, retry, Phase-E run, outcome/target access,
fit/refit/scoring, counter mutation, canonical historical rewrite, taxonomy
expansion, production execution, or PR merge occurred.

## Controlling inputs and successor artifact

The immutable predecessor remains V8 final2 and is not overwritten:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v8-stock-split-discovery-final2
MANIFEST SHA-256: df5e622da2e7577090735e7c2e4905502bb4432f2d29c175c10c966ea66020c1
```

The retained discovery input is also immutable:

```text
D:\Documents\Project\idx-ca-stock-split-discovery-20260829-v5
MANIFEST SHA-256: df44d4f17fe3062ba3c2b97ad773b180fcd0a52d8f74000c0f91f768f0eacfcc
```

The controlling successor is:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final
MANIFEST SHA-256: dcc5e05ca3bc5fe7da148629a26fb913a6e85b92a88cbc88180cfde05eec30cc
```

Its fresh deterministic rerun is:

```text
D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v9-stock-split-linkage-correction-final-rerun2
MANIFEST SHA-256: aef0b88b212871bf77b52211baa427b5a20fe9a808fb880d79e26ddb6e859835
```

The 20 non-manifest output files are byte-identical between the controlling
root and `final-rerun2`. The manifests differ only in their root-specific
metadata and are not compared as payload outputs. An earlier rerun directory
was an intermediate artifact with the predecessor repository pin and is not
controlling.

## Six exact discovery rows

The six V5 rows remain source-level `RESOLVED_EXACT` in the immutable discovery
artifact. This successor adds an explicit source-to-economic mapping; it does
not delete or rewrite any discovery row.

| Ticker / candidate date | Source-native representation | Retained official schedule and source-bound dates |
|---|---|---|
| AKRA 2022-01-11 | KSEI `Mandatory Conversion` | `AKRA_MCONV_20220113_ENG.pdf`, SHA `188f13437014460fde753be13ba4e08bffe8f2679747d173357ce4f35cc7856f`; 1:5; old-last 2022-01-11; first-new 2022-01-12; record 2022-01-13; distribution 2022-01-14 |
| AKRA 2022-01-12 | IDX `stockSplit` | Same retained KSEI schedule and SHA; transition-bearing first-new-basis representation |
| AMOR 2021-12-08 | IDX `stockSplit` | `136609_ksei_22317_jku_1221_202112031400.pdf`, SHA `cba51efedceb15bab28e92cf24d38ff174824b0e07babc11d0fe762e4856ef4d`; 1:2; old-last 2021-12-07; first-new 2021-12-08; record 2021-12-09; distribution 2021-12-10 |
| HRUM 2022-05-31 | KSEI `Mandatory Conversion` | `HRUM_MCONV_20220603_ENG.pdf`, SHA `85073f513b79a4d9ccc3327b960346f7a49f25cae7bb8dc65f91831ef65844a5`; 1:5; old-last 2022-05-31; first-new 2022-06-02; record 2022-06-03; distribution 2022-06-06 |
| HRUM 2022-06-02 | IDX `stockSplit` | Same retained KSEI schedule and SHA; transition-bearing first-new-basis representation |
| MTDL 2021-12-30 | KSEI `Mandatory Conversion` | `MTDL_MCONV_20220104_ENG.pdf`, SHA `680ec2cf874c80868e69659b1c218d7c96605b7ed5d1fe301fc2c5adc3398465`; 1:5; old-last 2021-12-30; first-new 2022-01-03; record 2022-01-04; distribution 2022-01-05 |

The four official schedule refs are retained in the discovery document
inventory. The KSEI candidate rows and IDX rows retain their own source refs
and evidence hashes in `source_evidence_ledger.csv`.

## Linkage audit

```text
PRIOR_PROVEN_LINKAGES       = 25
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 2
REMOVED_OR_CONFLICTING      = 0
```

The two new linkages are independently accepted as
`PROVEN_SAME_ECONOMIC_EVENT`:

```text
HRUM
  left  = 20b0ac04eb0e4c1a5e5a0f127e6ca16a2b57dde47a3366d8491ff830e84f85be
  right = 7a989db93f92d0a3e1d567b7d4ac4a0abf6339ea469e51c554d043d12a9f55af
  authority = https://web.ksei.co.id/Announcement/Files/HRUM_MCONV_20220603_ENG.pdf
  evidence SHA-256 = 85073f513b79a4d9ccc3327b960346f7a49f25cae7bb8dc65f91831ef65844a5

AKRA
  left  = c71df7108a164ae220118add500a6155fe11c1124b2419232c94ea17d5e737c6
  right = cdf92b5059205bd192cac728e09bb711f89139f7528fa7280a8f2fa9533568a8
  authority = https://web.ksei.co.id/Announcement/Files/AKRA_MCONV_20220113_ENG.pdf
  evidence SHA-256 = 188f13437014460fde753be13ba4e08bffe8f2679747d173357ce4f35cc7856f
```

These are not date-proximity links. Each pair has the same ticker and ratio,
and one retained official schedule binds the old-basis last-trading date to
the first-new-basis regular-market date. AKRA and HRUM are therefore both
`PROVEN_SAME_ECONOMIC_EVENT`. Their KSEI rows are
`PROVEN_SAME_EVENT_REPRESENTATION`; their IDX rows are
`TRANSITION_BEARING_SOURCE_REPRESENTATION`. AMOR and MTDL are single retained
source representations and remain transition-bearing. A resolved economic
event and a resolved source representation are intentionally distinct
concepts.

The prior V8 builder's explicit freeze of the V7 linkage ledger prevented
these two source-bound linkages from being admitted. That behavior is
`V8_LINKAGE_FREEZE_BUG = CONFIRMED`. The narrow successor correction now
recomputes base linkages with retained V5 documents, audits every delta, and
accepts only source/ref/SHA-bound new pairs. It does not weaken the base
reconciliation contract or use heuristic linkage.

## Reconciled counts

These are actual results from the new immutable successor, not a forced target:

| Metric | V8 predecessor | V9 successor |
|---|---:|---:|
| Source evidence rows | 412 | 412 |
| Cross-source collapses | 20 | 22 |
| Same-source collapses | 3 | 3 |
| Economic events | 389 | 387 |
| Resolved transitions | 159 | 157 |
| Unresolved transitions | 184 | 184 |
| Non-basis exclusions | 46 | 46 |

The two newly proven linkages collapse two already-resolved source
representations; therefore resolved economic events decrease to 157 while
the unresolved count remains 184. The arithmetic is conserved.

## Remaining unresolved geometry

```text
BONUS_SHARES                 = 11
CAPITAL_RESTRUCTURING        = 19
MERGER                       = 5
REVERSE_SPLIT                = 1
RIGHTS_HMETD                 = 71
STOCK_DIVIDEND               = 7
STOCK_SPLIT                  = 15
TRUE_SECURITY_CONVERSION     = 4
UNKNOWN_TAXONOMY             = 4
UNRESOLVED_OPERATIONAL_LABEL = 47
TOTAL                        = 184
```

The baseline future acquisition plan remains exactly 291 unresolved physical
event identities, split into 24 capability-verification requests and 13
later bulk-acquisition requests. The successor's post-acquisition residual
184 is reconciliation accounting, not a rewrite of the baseline plan.

The 11 provider-discovery failures and the two DIVA bounded no-document rows
remain frozen. BBRM remains unresolved and semantically insufficient; no
provider retry or new CA acquisition was made. The source capability verdict
remains `CAPABILITY_NOT_RELIABLY_REPEATABLE`.

## Scientific state and validation

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY          = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY             = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN

DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
PHASE_E_AUTHORIZED      = FALSE
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

Validation completed on implementation HEAD `01455840`:

```text
FOCUSED_LINKAGE_DISCOVERY_TESTS = 13 passed
CA_INTEGRITY_TESTS              = 158 passed
FULL_PYTEST                     = 376 passed
COMPILEALL                      = PASS
GIT_DIFF_CHECK                  = PASS
ARTIFACT_VALIDATION             = PASS; 0 retained-document hash failures
DETERMINISTIC_COMPARISON        = PASS; 20/20 non-manifest files identical
```

This checkpoint is complete and returned for ChatGPT review. Push and exact-
head CI status are recorded in the accompanying handoff. Do not merge PR
#108/#103 and do not execute production or scientific evaluation.
