# INC-001 bounded STOCK_SPLIT discovery and V8 reconciliation

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: exact residual `STOCK_SPLIT` discovery and outcome-blind transition reconciliation

## Review boundary

This is a narrow continuation of the INC-001 lane. The bounded official-source
discovery scope was exactly the 19 residual `STOCK_SPLIT` economic events in
the immutable V7 ledger. It did not touch BBRM, `RIGHTS_HMETD`, other families,
AADI/ADRO/AALI, Phase-E, outcomes or targets, fit/refit/scoring, counters,
canonical historical data, production, or PR #103/#108 merges.

Discovery and resolution remain separate. Only a retained official document
with the explicit `REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE` semantic can
resolve a transition. Candidate, record, distribution, listing, C-BEST, and
date-proximity values were not promoted.

## Immutable inputs and controlling outputs

- V7 predecessor reconciliation:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v7-split-wave`
  - manifest SHA-256:
    `575982a3f1f179ff3b0267d40589f4886db6f593be49bcedb8aa1885f1b2725d`
- Live official discovery evidence root (underlying bounded provider run):
  `D:\Documents\Project\idx-ca-stock-split-discovery-20260829-v2`
  - manifest SHA-256:
    `88a4483a07c970d65bbceb8595031b4a25f8d6a692d736202da08b8026a96ca3`
  - `provider_calls=true`; this is retained live evidence, not a population-
    completeness claim.
- Controlling normalized immutable discovery root:
  `D:\Documents\Project\idx-ca-stock-split-discovery-20260829-v5`
  - manifest SHA-256:
    `df44d4f17fe3062ba3c2b97ad773b180fcd0a52d8f74000c0f91f768f0eacfcc`
  - deterministic reuse of the retained V2 bytes; no new provider call.
- Controlling V8 reconciliation successor:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v8-stock-split-discovery-final2`
  - manifest SHA-256:
    `df5e622da2e7577090735e7c2e4905502bb4432f2d29c175c10c966ea66020c1`
- Deterministic reconciliation rerun:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v8-stock-split-discovery-final2-rerun`
  - manifest SHA-256:
    `662e402b7b4d07ef33af7d0d7bcd8ce07a05ea107a71ab023d3d461819e99be6`
  - all 15/15 non-manifest files are byte/hash identical to controlling V8;
    manifest differences are only the immutable `artifact_root` value.

V8/new final2 is the controlling result. Earlier V8 first/final roots and V6
/V7 roots remain immutable intermediate/predecessor evidence and are not
authoritative over V8 final2.

## Discovery result for exactly 19 targets

| Classification | Count | Identities |
|---|---:|---|
| `RESOLVED_EXACT` | 6 | AKRA 2022-01-11 and 2022-01-12; AMOR 2021-12-08; HRUM 2022-05-31 and 2022-06-02; MTDL 2021-12-30 |
| `NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED` | 2 | DIVA 2021-09-01 and 2021-09-02 |
| `PROVIDER_DISCOVERY_FAILURE` | 11 | BMRI 2023-04-03 and 2023-04-04; BYAN 2022-12-01 and 2022-12-02; SKRN 2023-01-06; SMDR 2023-01-30 and 2023-01-31; TMAS 2023-05-22 and 2023-05-23; TUGU 2023-05-23 and 2023-05-24 |

The six exact results are backed by four official KSEI documents. The 11
provider failures reflect bounded official-path instability and are not
historical negative authority. The two DIVA results are not a population-
level historical negative either. Discovery made 9 KSEI monthly-index and 13
IDX exact-event requests. Path verdict:
`CAPABILITY_NOT_RELIABLY_REPEATABLE`.

Authority blockers remain unchanged:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY           = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

## Reconciliation and acquisition-plan result

V8 final2 preserves the accepted V7 physical-event/linkage census and adds
only transition attestations:

```text
SOURCE_EVIDENCE_ROWS       412 -> 412   delta  0
PHYSICAL_EVENTS             389 -> 389   delta  0
RESOLVED_TRANSITIONS        155 -> 159   delta +4
UNRESOLVED_TRANSITIONS      188 -> 184   delta -4
NON_BASIS_EXCLUDED           46 -> 46    delta  0
CROSS_SOURCE_COLLAPSES       20 -> 20    delta  0
SAME_SOURCE_COLLAPSES         3 -> 3    delta  0
```

The six exact target rows produce four new transition attestations because
the two duplicate-date rows link to the same underlying economic events. No
new source linkage or physical event was created. BBRM remains unchanged and
unresolved from its predecessor.

The controlling `future_acquisition_plan_v11_291.json` preserves exactly 291
unresolved physical-event identities and separates:

```text
CAPABILITY_VERIFICATION_REQUESTS = 24
LATER_BULK_ACQUISITION_REQUESTS  = 13
BASELINE_UNRESOLVED_EVENTS       = 291
```

The current wave is explicitly not the 291-event bulk acquisition. The
post-acquisition `future_acquisition_plan_v2.json` count of 184 is only
current residual accounting and does not replace the baseline 291 plan.

## Scientific state and invariants

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

The following remain mandatory: no candidate date becomes transition
authority; incomplete official intervals cannot establish negative coverage;
physical-event, source-document, and taxonomy counts remain separate; no
provider retry/backfill beyond the named 19-row wave; no canonical rewrite;
and no scientific admission follows this reconciliation.

## Validation

- focused discovery/economic/source-authority tests: **33 passed**;
- CA/integrity subset (14 files): **152 passed**;
- full pytest: **372 passed**;
- `python -m compileall -q src scripts tests`: **PASS** (86 Python files);
- `git diff --check`: **PASS**;
- deterministic V8 comparison: **15/15 non-manifest files identical**;
- exact-head GitHub Actions validation is to be recorded after this lane
  commit is pushed. GitHub warnings must be reported as warnings; they are
  not to be described as zero-warning success.

This checkpoint stops for ChatGPT review. PR #108 and PR #103 remain
unmerged, and no production execution is authorized.
