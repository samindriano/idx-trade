# Handoff: INC-001 bounded official distribution-source wave V1

from: local Codex continuation
to: ChatGPT review / next authorized INC-001 action
task_id: `INC001-DISTRIBUTION-OFFICIAL-SOURCE-WAVE-V1`
lane: `data/ca-aware-feature-basis-remediation-v1`

## Review boundary

Review the single controlling official-source acquisition artifact for exactly
18 unresolved V14 events:

```text
BONUS_SHARES = 11
STOCK_DIVIDEND = 7
ACQUISITION_ROOT = D:\Documents\Project\idx-ca-official-distribution-acquisition-20260830-v4-final
ACQUISITION_MANIFEST_SHA256 = 33297117036972e91609f635175a3cce88aeada6a94b0c637edf1cf81a700c0d
```

The wave used only official KSEI share-bonus/share-dividend indexes and exact
official IDX event-date requests. It made no market-provider call, no broad
crawl, no retry, and no request for another family.

## Result

```text
RESOLVED_EXACT = 3
OFFICIAL_EVENT_EVIDENCE_FOUND_DOCUMENT_UNAVAILABLE = 5
NO_OFFICIAL_EVENT_DOCUMENT_DISCOVERED = 5
PROVIDER_DISCOVERY_FAILURE = 5
SEMANTIC_INSUFFICIENT = 0
LINKAGE_AMBIGUOUS = 0
TOTAL = 18
```

Exact official KSEI regular-market Ex evidence was proven for KLAS
(`2024-11-11`), UFOE (`2024-12-04`), and CLEO (`2025-06-10`). Their source URL
and PDF SHA-256 are recorded in `target_event_results.csv` and
`official_document_evidence.csv`.

The corrected successor reconciliation is:

```text
RECONCILIATION_ROOT = D:\Documents\Project\idx-ca-economic-event-reconciliation-20260830-v15-distribution-wave
RECONCILIATION_MANIFEST_SHA256 = d5a4a21beb2f065502fef3899b3a4f4f7204e0fbbed6f05ae7f4a0119fed6025
BEFORE = 412 / 387 / 160 / 181 / 46 / 27
AFTER  = 412 / 387 / 163 / 178 / 46 / 27
```

The six values are source rows / economic events / resolved / unresolved /
non-basis / proven linkages. There are zero new linkages. The 15 remaining
events remain unresolved; this is not negative historical authority.

## Controls

The accepted transition semantic is exactly `REGULAR_MARKET_EX_DATE`.
Candidate, cum, record, distribution, payment, listing, issued-share, and
next-session dates were not used as transition authority. CNMA and MEJA were
not resolved by reaccepting retained mechanics. V14 source bytes and the 17
research/operational blockers remain unchanged.

No outcomes, Phase-E, model/refit/score, counter, PaperState, production,
backfill, canonical historical rewrite, or merge occurred. No application,
runtime, or science code changed.

## Review decision requested

Review the acquisition artifact and V15 successor. If further work is desired,
authorize a new bounded path only after reviewing the five provider failures
and five document-unavailable results; do not retry or backfill this wave.
