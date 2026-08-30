# INC-001 retained-evidence taxonomy adjudication — V1

Date: 2026-08-31 Asia/Jakarta  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Scope: exactly the four current V15 `UNKNOWN_TAXONOMY` economic events

## Controlling state and boundary

The controlling reconciliation remains:

```text
ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
MANIFEST SHA-256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
SOURCE_EVIDENCE_ROWS = 412
ECONOMIC_EVENTS = 387
RESOLVED = 163
UNRESOLVED = 178
NON_BASIS = 46
PROVEN_LINKAGES = 27
UNKNOWN_TAXONOMY = 4
```

This was a retained-evidence-only adjudication. It read the four selected
rows, their retained source-ledger mappings, and the existing KSEI HTML bytes.
No live KSEI/IDX/provider request, web search, crawl, retry, or new source
acquisition occurred.

## Retained evidence findings

Each selected retained KSEI page has the expected source SHA and explicitly
contains two `Active` `Mixed Dividend` rows with the same issuer and the same
date set: one issuer-share entitlement and one IDR cash entitlement.

| ticker | economic event | target source event | retained SHA-256 | share leg | cash leg |
|---|---|---|---|---|---|
| CNMA | `DERIVED-4e2db5111bc0b70d5bd6b9e77cda6703dea8ff60d18a033787e75e04999e4d60` | `aad3d51ec0e1cbbfc4637b47a64fd5a9ac98c2ec6ea61b387998b44e66be8cc4` | `e7656e6126b5be6091a805621de843b7f8bd2e72f500ecea5dac98ca86efc5d9` | `(50 CNMA : 1 CNMA)` | `(50 CNMA : 7 IDR)` |
| KKGI | `DERIVED-893338349f1dc1ac85f83e9a5476f2a5967f5c28b0c4bdf26a20c28ae0264c92` | `389ab4a10c6df68b58979afdf86ee369174c6637a2418a22a8bfaa926de04d26` | `c674ef6469147656a057c09a617e5d95c9ea8e6761e4c75c4638f4d26ab55e78` | `(10000 KKGI : 53 KKGI)` | `(10000 KKGI : 15 IDR)` |
| WINS | `DERIVED-7d3d4fb644bfac02abc1ff6f2aac5cb20c895eb1e0a571d42291759ea62a1ea8` | `0b4dd5c52fcf6dc2f12710099bb77a5d16c842f1a51ac584a9929532ecac5732` | `d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f` | `(46 WINS : 1 WINS)` | `(46 WINS : 2 IDR)` |
| WINS | `DERIVED-ff06b7cd6b57d1c4d7a0b5b21a8d6e44bd0b493fc5e18aebc3960b26f3b6022f` | `6f449d4210b1ae38dcfdd8e1084165729cd7d07fb7dc74640a698673de0ef49a` | `d2269bfed3d9f14ba06160641904a75d4753db706a8946793359fbcc5302280f` | `(71 WINS : 1 WINS)` | `(71 WINS : 2 IDR)` |

The exact retained page paths and source references are recorded in
`D:\Documents\Project\idx-ca-unknown-taxonomy-adjudication-20260831-v1\retained_evidence_inventory.csv`.
The complete parsed paired rows are recorded in
`raw_composite_rows.json` in that artifact root.

## Adjudication

```text
PROVEN_COMPOSITE_SHARE_DISTRIBUTION_REQUIRES_POLICY = 4
PROVEN_NON_BASIS                                      = 0
PROVEN_STOCK_DIVIDEND                                 = 0
PROVEN_BONUS_SHARES                                   = 0
PROVEN_EXISTING_ECONOMIC_FAMILY                      = 0
RETAINED_EVIDENCE_TAXONOMY_INSUFFICIENT              = 0
```

The four retained records are proven to have composite share-plus-cash
mechanics, but no existing single canonical family represents both legs. A
taxonomy/policy decision is therefore required. The source-native label is
not promoted to `STOCK_DIVIDEND` or `CASH_DIVIDEND`; no basis effect is
promoted from the composite finding.

No regular-market transition is present in the retained evidence. Candidate,
record, distribution, publication, or next-session dates are not transition
authority.

The adjacent share rows have existing `STOCK_DIVIDEND` source representations,
but no new `PROVEN_SAME_ECONOMIC_EVENT` linkage is added. The existing linkage
contract requires source-bound accepted event-binding authority; same page,
issuer, dates, and row adjacency are not sufficient to collapse the two source
IDs or to assert a transition.

## Linkage and reconciliation

```text
PRIOR_PROVEN_LINKAGES       = 27
RECOMPUTED_PROVEN_LINKAGES  = 27
NEW_PROVEN_LINKAGES         = 0
REMOVED_OR_CONFLICTING      = 0
```

V15 remains the controlling reconciliation. No no-op successor was created:

```text
BEFORE = 412 / 387 / 163 / 178 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
```

The canonical V15 `UNKNOWN_TAXONOMY` residual remains 4 because policy,
basis-effect, and exact-transition semantics were not promoted. The artifact
records the more specific residual as four
`PROVEN_COMPOSITE_SHARE_DISTRIBUTION_REQUIRES_POLICY` results.

## Artifact and validation

```text
ARTIFACT_ROOT = D:\Documents\Project\idx-ca-unknown-taxonomy-adjudication-20260831-v1
ARTIFACT_MANIFEST_SHA-256 = ee7ac86764f7edda8a5886e5697b128085b32eaf1b487a9d5eac1132413a88ca
V15_INPUT_MANIFEST = PASS
TARGET_CONSERVATION = PASS (4/4)
RETAINED_SOURCE_HASHES = PASS (4/4)
ARTIFACT_OUTPUT_HASHES = PASS (7/7 excluding MANIFEST.json)
DETERMINISTIC_UNCHANGED_STATE_COMPARISON = PASS; no replay required
NEW_SUCCESSOR_RECONCILIATION = FALSE
GIT_DIFF_CHECK = PASS
```

The temporary builder was removed. No application, runtime, science, model,
outcome, target, counter, PaperState, canonical historical data, production,
backfill, or merge action occurred. No repository source/runtime/science file
changed.

## Blocking state and next action

```text
IDX_HISTORICAL_NEGATIVE_AUTHORITY = UNSUPPORTED
IDX_HISTORICAL_ASOF_AUTHORITY = UNKNOWN
KSEI_HISTORICAL_COMPLETE_INTERVAL_AUTHORITY = UNKNOWN
DATA_ADMISSION = FAIL
RESEARCH_ADMISSION = FAIL
PHASE_E_AUTHORIZED = FALSE
REFIT_AUTHORIZED = FALSE
COUNTER_ACTION = NONE
```

Next action is a separately authorized taxonomy/policy decision for composite
share-plus-cash distributions, or a separately bounded source acquisition if
policy requires additional event-specific authority. Do not infer a family,
basis effect, transition, linkage, or historical negative authority from this
retained-only pass.

## Review handoff

The MAIN coordination row was marked `ACTIVE` before this work at
`origin/main@cc54e011`. After this lane result is pushed, MAIN-owned
coordination will return that row to `REVIEW` with this artifact and the
unchanged V15 result. This checkpoint is for ChatGPT review; no subsequent
family lane is authorized by it.
