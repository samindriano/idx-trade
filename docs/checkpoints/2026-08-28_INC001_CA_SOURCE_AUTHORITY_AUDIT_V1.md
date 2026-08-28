# INC-001 CA-Aware Feature-Basis Remediation — Source Authority Audit V1

Date: 2026-08-28 Asia/Jakarta
Branch: `data/ca-aware-feature-basis-remediation-v1`
Reviewed implementation head: `a4e644b655fb7b7980b59c008b7d3dd26f364371`
Audit status: `SOURCE_AUTHORITY_GAP_CONFIRMED_PHASE_E_BLOCKED`

## Scope and boundaries

This audit uses only retained/local artifacts and source bytes. It does not
call providers, access outcomes or targets, fit/refit/score models, run
Phase-E, mutate counters, rewrite canonical historical data, or merge PR #108
or #103. The audit generator is
`src/idx_trade/ca_source_authority_audit_v1.py`; its tests are
`tests/test_ca_source_authority_audit_v1.py`.

## Current local facts versus historical notes

The current audit revalidated the accepted R3.1 population artifacts and
source-byte hashes. The accepted identity populations are:

| Population | Rows | Tickers | Ticker-set SHA-256 |
|---|---:|---:|---|
| Final fit union | 240,344 | 629 | `fca0ff7c02038cdd9f4e1886f796b29d00eb4721ca5f6cbcdd22a71d52fee797` |
| Cross-sectional application | 276,153 | 716 | `6f9542f6d7b218ca871c154a7ce2aff877086e095fbf006262141d625c78ea9b` |
| Observed backward dependency closure | 365,968 | 716 | `6f9542f6d7b218ca871c154a7ce2aff877086e095fbf006262141d625c78ea9b` |

Closure interval is `2021-04-29—2026-07-17`; application uses 980 dates.
KSEI retained history covers 610 tickers: 567 certified and 43 unresolved;
106 application/closure tickers are absent from that census. The IDX retained
issued-history capture observes 533 of the 716 application tickers, but this
is positive/candidate event evidence and not no-event coverage.

Historical R3/R3.1 summaries remain useful only as hash-pinned identity and
scope evidence. Prior derived `EXACT_TRANSITION` labels are not promoted by
this audit where the semantic row lacks row-level source-hash linkage. KSEI
retrieval timestamps are not historical as-of attestations, and
`TanggalPencatatan`, record, distribution, or candidate dates are not generic
market-transition dates.

## Retained source inventory

The immutable inventory contains 1,137 pins: 1,121 source-byte rows, 3
capture manifests, 11 derived audit artifacts, and 2 source-contract
documentation rows. 1,129 bytes/artifacts exist and match all 1,113 recorded
source hashes; 8 request records are genuine missing failed captures (one PIT
KSEI request and seven targeted schedule-document retry records). No missing
byte was treated as no-event evidence.

The inventory includes the KSEI registered-security history census and raw
capture records, IDX issued-history/announcement captures and attachments,
targeted KSEI schedule captures, the strict 26-event artifacts, prior
continuity/event-window artifacts, and the local IDX source-contract
documentation. Each source pin records path, local SHA-256, capture time when
the source record supplied one, source reference, contract, population/date
scope, event family, polarity, and transition semantics.

## Authority and gap result

All frozen structural families have at most partial positive-event evidence;
none has full source-defined no-event authority or full population/date-level
transition authority. `REVERSE_SPLIT` has no retained positive rows and no
negative authority. `MERGER`/`gabungUsaha` is explicitly left `UNKNOWN`; it is
not silently mapped to `CAPITAL_RESTRUCTURING`. Retained cross-source conflict
identities include `ISAT`, `MEGA`, and `SCMA`; conversion taxonomy also remains
unresolved.

Temporal authority is `UNKNOWN`/`FAIL`: retained data has source-native event
dates and retrieval/document timestamps, but no complete per-session
historical as-of/no-event attestation for the full 716-ticker closure.

The strict 26-event reconciliation contains all 26 rows as `UNRESOLVED` and
certified transition rows remain zero. The retained relevant-event audit adds
136 rows; its historical semantic labels are retained for comparison but are
not current source authority without hash-bound transition evidence.

The exact gap matrix is:

```text
G001 FULL_716_SOURCE_COVERAGE       FAIL
G002 STRUCTURAL_FAMILY_COVERAGE     FAIL_OR_UNKNOWN
G003 TEMPORAL_ASOF                  UNKNOWN
G004 TRANSITION_SEMANTICS           FAIL_OR_UNKNOWN
G005 CROSS_SOURCE_CONFLICTS         UNKNOWN
G006 MERGER_MAPPING                 UNKNOWN
G007 IDENTITY_CONTAINMENT            PASS_IDENTITY_ONLY
G008 NO_EVENT_AUTHORITY              FAIL
```

Acquisition requirements are recorded in `acquisition_requirements.json`.
They require separate authorization before any network/provider work and
require source-bound identity coverage, exact family contracts, negative
coverage semantics, per-session/as-of provenance, transition semantics, and
conflict adjudication. Until every required gate is `PASS`, Phase-E remains
STOP.

## Scientific verdict unchanged

```text
DATA_ADMISSION=FAIL
RESEARCH_ADMISSION=FAIL
MODEL_PROMOTION=NOT_EVALUATED
HISTORICAL_APPLICATION=BLOCKED_PHASE_E_NOT_RUN
REFIT_AUTHORIZED=FALSE
COUNTER_ACTION=NONE
```

## Immutable audit root

Root: `D:\Documents\Project\idx-ca-source-authority-audit-20260829-v5-final`
`MANIFEST.json` SHA-256: `71639eaef1a7327f3ab5e2b003fa493f6560c9744915312607c148f1a9f45efd`
`summary.json` SHA-256: `decc4927424970e7b6474caf5e649fc2f948d5803262588616866f437d6850a3`

The fresh-root deterministic rerun is
`D:\Documents\Project\idx-ca-source-authority-audit-20260829-deterministic-rerun-v2`;
all 9 file SHA-256 values match the final root exactly. The generator uses a
stable placeholder for the physical output path in `summary.json`, so root
location does not alter the evidence hashes.

Output hashes:

```text
ca_source_inventory.csv                  c420c492998a0e77aba063755019e3460e2d0c1e982c0ee2dfd0c27b5e1c9739
ca_source_family_authority_matrix.csv    8dcafd79106653b9501b13e4727e42452ae54cb5375e851d5ddede288fcc9f6d
ca_source_population_reconciliation.csv  4cc35f29ae864baf9ff6ba57c44f7e60610b2faa98f7a81b2b065a09394659e2
ca_temporal_authority_matrix.csv         c63841316ff04f8466d8f28e067a1d4debee1322e12f535f34ed99f7cbeb684e
ca_transition_semantics_reconciliation.csv fd3baafe16e94aaf7e57ba1b715c2995e2ae9c6169002ecb39f13f8648b0137c
ca_remaining_gap_matrix.csv              7b3d850f16106d8d792716406ae0d456f517200de41dbc4581df8b801da88603
acquisition_requirements.json            a772fde10bb59346bd38e6a43d3ae7fa7fe5be916f75bf61d50fef2f6749d95b
```

This checkpoint is a review handoff, not authorization for source
acquisition, Phase-E, production execution, or historical mutation.
