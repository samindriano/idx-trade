# INC-001 Authority Source-Contract Reconnaissance V1

Date: 2026-08-31 Asia/Jakarta  
Repository: `samindriano/idx-trade`  
Lane: `data/ca-aware-feature-basis-remediation-v1`  
Lane HEAD: `7e72cedd7c53e95ab98b920e20e15aa0b4039f02`  
Mode: read-only, outcome-blind, no credentials

## Purpose

This bounded investigation tested whether a defensible authoritative source
contract can close population completeness and historical-as-of authority for
the frozen V4-X1 historical scope. It does not implement a provider,
adapter, gate, runtime path, versioned successor, or science change.

## Decision

`SOURCE_CONTRACT_REQUIRES_VENDOR_ACCESS`

No inspected public source proves all of the following at once:

1. one population-wide identity/session enumeration for the frozen scope;
2. explicit exhaustive no-event semantics for every required family and
   interval;
3. stable PIT identity/listing/delisting/relisting semantics;
4. source knowledge/as-of and observed-through boundaries;
5. immutable correction/revision/supersession lineage;
6. exact transition semantics with source-bound provenance; and
7. replayable full snapshot plus delta semantics.

A composite of public IDX, KSEI, OJK, issuer, and ZAPI material does not close
the gap without inference. The existing admission boundary remains blocked.

## Findings

### Official primary sources

- Public IDX corporate-action and announcement pages provide positive
  discovery, categories, filters, attachments, publication metadata, and
  visible result sets. The announcement page explicitly limits displayed
  history to three years. These surfaces do not prove complete universe,
  exhaustive no-event, PIT/as-known history, or revision replay.
- IDX Data Reference and IDX-SISCA are credible licensed acquisition
  candidates. Their public product/terms material does not itself provide the
  required population, no-event, PIT, revision, and replay contract.
- KSEI public schedules/downloads and issuer pages provide positive events,
  date fields, and statuses including active/cancelled examples. They do not
  establish complete identity/session intervals, explicit no-event rows, PIT
  retrieval, or revision replay.
- OJK publications provide period-labeled positive/aggregate tables and
  disclosure rules. Issuer documents can establish exact event mechanics and
  bounded issuer/year/class negatives, but neither generalizes to the
  market-wide frozen population.

### ZAPI

ZAPI remains classified as:

`DISCOVERY_ROUTER_ONLY_NOT_TRANSITION_AUTHORITY`

It can return rows for a requested endpoint/category/window, but the bounded
review did not establish complete pagination, stable issued-event identity,
deleted/replaced-row semantics, source knowledge time, or an empty-result
contract. Query emptiness therefore remains `UNKNOWN`, not no-event.

### Professional candidates

- EDI is the strongest public XIDX coverage lead; its public material exposes
  XIDX in the coverage table, historical access, date fields, identifier and
  change/source fields. It still needs XIDX completeness, PIT snapshots,
  retained corrections/deletions, and replay evidence.
- LSEG has strong public evidence for broad event/history coverage and
  operational delivery; exact XIDX coverage, archived versions, and
  no-event/PIT semantics remain unverified.
- SIX has the clearest public full-initial-load plus delta and multi-year
  history claim; XIDX coverage, PIT vintage, retained revisions, and source
  lineage remain unverified.
- ICE has strong public inactive/security/history and lifecycle claims; exact
  XIDX depth, PIT, replay, and source-document binding remain unverified.
- Morningstar, Bloomberg, S&P/Capital IQ, and FactSet remain RFI candidates,
  not admitted authorities.

No vendor was accessed beyond public documentation. “Complete,” “historical,”
“audit trail,” or “PIT” marketing language is a shortlist signal only.

## Adversarial conclusion

The following cases remain fail-closed / `UNKNOWN` without an explicit source
contract: inactive or omitted ticker; empty page/category; missing pagination
count; deleted or replaced event; corrected date/ratio; event date before or
after the requested knowledge cutoff; issuer archive silence; current
Security Master absence; normalized vendor row without source-document
lineage; and unsupported/permission-denied/partial query.

## Retained external evidence

The deterministic external evidence tree is:

`D:\Documents\Project\idx-ca-authority-source-contract-recon-20260831-v1`

Manifest SHA-256 at checkpoint:
`cbdb7fbaaf21dc4ee16dfcc69907deecba4b0a7fa954d14a0624621a421e464e`

It contains 33 raw-evidence index records, 32 captured payload hashes, a
machine-readable source matrix, a 144-cell requirement matrix, a human-
readable matrix, a 10-case adversarial table, and the vendor RFI. Public
retrieval used unauthenticated direct requests only. WAF/HTTP errors,
unsupported binary parsing, and archive extraction limitations were retained
as probe results; no bypass was attempted.

## Acceptance boundary and next action

The existing canonical R3 population gate remains the only admission owner.
The next external action is a written RFI plus a bounded licensed sample,
without purchase or credential configuration in this lane. The minimum
sample must include XIDX coverage, active/inactive identity intervals,
full-plus-delta replay, explicit no-event/unsupported distinctions, PIT
knowledge timestamps, corrections/deletions, source-document provenance, and
hash-bound manifests. Until independently verified, INC-001 admission and
historical application remain blocked.

No application/runtime/science code, frozen artifact, provider state,
outcome/target, counter, PaperState, R2, production state, scheduler,
deployment, backfill, or admission state was changed.
