# Free historical authority recovery — result

Date: 2026-09-20
Branch: `codex/alpha-available-data-20260919`
Scope: outcome-blind source-authority research only

## Verdict

`SUPPORTED_BOUNDED_SURFACE_RECOVERY_NO_ADMISSION`

The search recovered meaningful bounded identity, event, and report-archive
evidence. It did not recover a population-wide PIT, revision, sector-history,
price-basis, or execution-capacity authority. Historical predictive research
remains blocked. No protected outcomes, canonical data, provider, production,
cloud, capture, telemetry, scheduler, or incumbent state was accessed or
changed.

## What the CNTX result proves

The frozen panel contains zero CNTX rows, while the retained anchor contains
1,258 CNTX rows: 458 `ACTIVE` rows from 2021-04-29 through 2024-08-01 and 800
`NO_TRADE` rows through 2026-07-29. The official per-security trading route has
1,581 CNTX rows from 2020-01-02 through 2026-07-29.

This proves that panel replay is not a population enumerator and that
panel-absence cannot be interpreted as historical population absence. It does
not prove that the anchor is population-complete, that CNTX was eligible on
every active date under the intended policy, or that the corpus is
survivorship-safe. The earlier 981,940-key zero-mismatch result remains an
observed-panel replay result only; it is not population-completeness evidence.

KSEI’s public security record identifies CNTX as Series A preference security
`ID2000081902`, distinct from Series B common security CNTB. The issuer’s 2022
financial statements independently describe the two series and their 2016
nominal-value split. This is a bounded identity upgrade: ticker-only logic can
conflate security class and issuer. It is not a complete issuer/ISIN transition
master.

## Blocker matrix

| Blocker | Evidence recovered | Authority upgrade | Residual | Verdict |
|---|---|---|---|---|
| Financial PIT/revision | Toray/Centex annual pages 2013–2022; 2022-period financial-statement PDF | Bounded report-content and issuer archive | No publication/knowledge time, revision lineage, or deterministic as-of retrieval | `BLOCKED` |
| Universe/identity | CNTX anchor/trading counterexample; KSEI security/ISIN pages; Series A/B issuer evidence | Panel-absence-as-population-absence disproven; CNTX sample identity bounded | No population-wide daily PIT master, ticker reuse, relisting, or survivorship proof | `BLOCKED` |
| PIT sector/industry | KSEI current activity-sector fields; official ratio labels | Current sampled cross-check only | No historical effective/knowledge timeline; retained `industryCode` empty | `BLOCKED` |
| CA/price basis | KSEI CNTX/CNTB CA history and 2016 notice; issuer split/listing history | Bounded security/event taxonomy and one explicit transition schedule | No population-wide exchange-effective basis or event-to-window contract | `BLOCKED` |
| Execution/capacity | Official CNTX rows and derived mirror | Raw field discoverability only | No PIT ADV/spread/queue/fill/capacity semantics | `BLOCKED` |

## Source classes and their limits

1. KSEI registered-securities pages and filtered ISIN/KSEI archives. Public
   year selectors reach back to 2003 for ISIN notices and 2000 for KSEI
   announcements. January 2021 and January 2019 queries returned 52 and 110
   dated new-ISIN notices respectively. A direct retained CNTX page returned
   `UNDEFINED/UNKNOWN`, so the populated identity claim is kept as a web-search
   record and is not silently substituted with the failed direct fetch.
2. Issuer IR archive. Centex/Toray year pages 2013–2022 were reachable; the
   retained 2022-period financial statement documents Series A/B share counts,
   old listing history, and the 2016 split. The archive does not expose a
   researcher-knowledge timestamp contract.
3. Official IDX current/trading surfaces. CNTX raw trading history is present,
   but current directories and dated rows do not establish historical daily
   population, identity continuity, revision, or PIT availability.
4. Derived GitHub mirror. Pholenk’s pinned `IDX-Dataset` commit reproduces all
   ten compared numeric fields for 1,243 CNTX dates against the local public
   dataset. It has no delisting-date field and is explicitly a derived mirror;
   exact overlap is not independent authority.
5. OJK issuer list and IDX delisted download surfaces were inspected. The OJK
   request was rejected by the public web surface, and the IDX delisted page
   exposed a download control/API alias but direct script/download retrieval
   returned HTTP 403. These are recorded as access-limited source leads, not
   negative evidence and not silently treated as exhausted authority.

## Durable artifacts

- Machine audit: `research_knowledge/free_historical_authority_recovery_v1.json`
- Reproducible read-only probe: `research/alpha_free_historical_authority_recovery_v1.py`
- Focused tests: `tests/test_alpha_free_historical_authority_recovery_v1.py`
- External retained source root:
  `D:\Documents\Project\idx-alpha-available-data-staging-20260919\public-source-probes\free-authority-research`
- External source hashes and exact bounded counts are recorded in the machine
  artifact. The recovery audit itself uses no network and performs no canonical
  writes.

## What should not be retried

- Do not rerun panel-only replay or zero-mismatch checks as population proof.
- Do not treat KSEI current pages, issuer reports, or derived GitHub files as a
  population-wide PIT security master.
- Do not infer price adjustment or eligibility from a CA record date, listing
  date, or issuer report alone.
- Do not repeat the same direct OJK/IDX download request without a genuinely
  new public access path or owner-provided artifact.

## What would reopen the blocked issues

A versioned historical exchange membership/security master with issuer/ISIN
continuity, effective and knowledge time, revision lineage, exchange-effective
price basis, and—if execution claims are intended—historical capacity data or
an explicit policy-authorized proxy. Otherwise the remaining gap requires an
explicit project-owner eligibility policy decision.
