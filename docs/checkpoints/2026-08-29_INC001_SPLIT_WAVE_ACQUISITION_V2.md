# INC-001 split/reverse transition acquisition wave V2

Date: 2026-08-29
Lane: `data/ca-aware-feature-basis-remediation-v1`
Scope: official-source acquisition and outcome-blind economic reconciliation only

## Authority and boundaries

This checkpoint is a narrow follow-up to the controlling V4 unresolved-gap
decomposition. It does not run Phase-E, call providers beyond the explicitly
authorized official-source fetches, access outcomes or targets, fit/refit/score
models, mutate counters, rewrite canonical historical data, execute production
work, or merge PR #103/#108.

The controlling decomposition remains immutable:

- V4 root: `D:\Documents\Project\idx-ca-unresolved-economic-gap-decomposition-20260829-v4`
- V4 manifest SHA-256:
  `3af6a92738f560f26699725e2f8cf6200dc1dff3fcc6a79d899cb9911d6499bc`
- V4 deterministic rerun remains the prior audit rerun; V4 is still the
  controlling decomposition and was not rewritten.

The prior reconciliation and source-authority pins remain immutable:

- reconciliation V3 manifest:
  `60d4b5caf9fbadd81c8f63edf4976f2d476ead6a26884c9d74f965759250a746`;
- source-authority V8 manifest:
  `556ab328b8f5663ce98450de46e8e7eed0f9e86d42d8d51506158b5fec323b71`.

## Exact acquisition scope

The V4 residual inventory was checked before acquisition: exactly 21
`STOCK_SPLIT` source events plus one `REVERSE_SPLIT` BBRM source event. The
stale `CAPABILITY-V11-KSEI-REPRESENTATIVE-3` unit was closed as
`CLOSED_PREVIOUSLY_EXECUTED_NO_RETRY`; AADI, ADRO, and AALI were not retried,
and V4's 190-event decomposition was not changed. Rights and the other 97
events were untouched.

Only retained official KSEI index hrefs and the one-event BBRM official probe
were used. The initial acquisition fetched five exact official URLs once (five
HTTP 200 responses). The corrected immutable acquisition successor reused
those retained bytes and did not redownload them:

- acquisition root:
  `D:\Documents\Project\idx-ca-stock-split-acquisition-20260829-v3`;
- acquisition manifest SHA-256:
  `cdd96f746df3edf224f314a82993aac61d79324b4e8b46d96bcad74fe673a1a6`;
- its predecessor V2 had a staging-path manifest defect and is immutable
  historical intermediate evidence only.

The accepted transition semantic was only the explicit
`REGULAR_MARKET_FIRST_NEW_BASIS_TRADING_DATE`. Candidate, record,
distribution, listing, C-BEST, and date-proximity values were not promoted.

Target results for the exact 22-row wave:

| Result | Count | Identities |
|---|---:|---|
| `RESOLVED_EXACT` | 2 | HEAL 2021-07-29; SCMA 2021-10-28 |
| `DOCUMENT_FOUND_SEMANTIC_INSUFFICIENT` | 1 | BBRM 2022-02-17 (`REVERSE_SPLIT`) |
| `DOCUMENT_NOT_FOUND` | 19 | AKRA (2022-01-11, 2022-01-12), AMOR (2021-12-08), BMRI (2023-04-03, 2023-04-04), BYAN (2022-12-01, 2022-12-02), DIVA (2021-09-01, 2021-09-02), HRUM (2022-05-31, 2022-06-02), MTDL (2021-12-30), SKRN (2023-01-06), SMDR (2023-01-30, 2023-01-31), TMAS (2023-05-22, 2023-05-23), TUGU (2023-05-23, 2023-05-24) |

HEAL's retained official schedule explicitly states stock split, ratio 1:5,
last old-basis date 2021-07-29, and first new-basis regular/negotiation date
2021-07-30. SCMA's retained official schedule explicitly states stock split,
ratio 1:5, last old-basis date 2021-10-28, and first new-basis
regular/negotiation date 2021-10-29. BBRM's three official reverse-stock
plan/odd-lot documents do not prove the accepted first-new-basis semantic for
the 2022-02-17 event, so BBRM remains unresolved.

`DOCUMENT_NOT_FOUND` means not found within the retained official index scope;
it is not a historical negative-authority claim. The independent authority
blockers remain unchanged:

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY           = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY               = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
```

## Reconciliation result

The new immutable post-acquisition reconciliation is:

- controlling root:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v7-split-wave`;
- manifest SHA-256:
  `575982a3f1f179ff3b0267d40589f4886db6f593be49bcedb8aa1885f1b2725d`;
- deterministic rerun:
  `D:\Documents\Project\idx-ca-economic-event-reconciliation-20260829-v7-split-wave-rerun`;
- rerun manifest SHA-256:
  `fc7aee5784b0a78dfc34015c8ffd910bce7debcda149d1ab82aa3af0adbe9f21`.

Before and after counts are:

```text
                         BEFORE V3   AFTER V7   DELTA
SOURCE_EVIDENCE_ROWS          412        412       0
PHYSICAL_EVENTS               389        389       0
RESOLVED_TRANSITIONS          153        155      +2
UNRESOLVED_TRANSITIONS        190        188      -2
NON_BASIS_EXCLUDED             46         46       0
```

The 20 residual split/reverse events are the 19 remaining `STOCK_SPLIT`
events plus BBRM `REVERSE_SPLIT`. The full 188-event unresolved geometry is
partitioned exactly in `future_acquisition_plan_v2.json`; the five units are
the closed capability unit plus 20 split/reverse, 71 rights, 46 source-
authority, 47 operational-taxonomy, and 4 unknown-taxonomy event IDs. The
plan records tickers from source-event linkage and keeps capability
verification separate from later bulk acquisition.

The V7/V8 reconciliation comparison found 14/14 non-manifest files
byte-identical (`differences=0`, `PASS`). Retained-document verification was
36 rows with zero hash failures; the BBRM semantic-insufficient result and
all arithmetic checks passed. No provider call occurred during reconciliation.

## Scientific state

```text
DATA_ADMISSION          = FAIL
RESEARCH_ADMISSION      = FAIL
MODEL_PROMOTION         = NOT_EVALUATED
HISTORICAL_APPLICATION  = BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED        = FALSE
COUNTER_ACTION          = NONE
```

## Validation

- focused CA/economic/source-authority tests: 48 passed;
- all CA/integrity tests (12 files): 131 passed;
- full pytest: 370 passed;
- `py_compile` over `src`, `scripts`, and `tests`: 84 files passed;
- `git diff --check`: PASS;
- deterministic V7/V8 comparison: 14/14 non-manifest files, PASS;
- exact-head GitHub Actions run `33258560263` on commit `0e983dc9`: PASS,
  `370 passed, 5 warnings`; the separate GitHub annotation is the Node.js 20
  deprecation warning for `actions/checkout@v4` and `actions/setup-python@v5`.

This checkpoint stops at review/handoff. No merge or further production
execution is authorized.
