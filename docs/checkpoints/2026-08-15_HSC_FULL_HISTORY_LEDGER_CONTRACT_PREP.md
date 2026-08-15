# HSC Full-History Ledger V1 — Contract Preparation

Date: 2026-08-15 Asia/Jakarta
Branch: `data/idx-hsc-full-history-ledger-v1`
Source parent: `data/idx-ownership-hsc-source-remediation-v1@ba03d0d0ebe89f9219a2ac885af758b5e51c68ef`
Status: `CONTRACT_PREPARED_OFFICIAL_FULL_LEDGER_RECOVERY_REQUIRED`

## Purpose

Prepare a strict, point-in-time HSC/RSC event ledger and state-replay contract
before any ownership-concentration feature design.

This branch does not calculate statutory/effective free float, HHI,
supply-tightness scores, daily panels, Foreign Flow interactions, model scores,
or outcomes.

## Reconciliation target

The accepted source parent recovered official bytes for the nine initial April
HSC determinations, MGRO (including correction lineage), DGWG, and LUCY removal.
Subsequent web forensic work reconstructed the public chronology sufficiently
to identify the missing official evidence set:

1. initial nine on 2026-04-02;
2. WBSA as HSC #10 (`Peng-00010-HSC/BEI.WAS/05-2026`,
   `KSEI-3075/DIR/0526`, 95.82%, ownership as-of 2026-05-07);
3. TCPI as HSC #11 (`Peng-00011-HSC/BEI.WAS/05-2026`,
   `KSEI-3492/DIR/0526`, 94.10%, ownership as-of 2026-05-25);
4. MGRO as HSC #12 (official bytes already preserved in parent);
5. SATU as the thirteenth active HSC name (94.27%, ownership as-of
   2026-05-29); exact official announcement numbers remain to be recovered and
   must not be inferred from sequence numbering;
6. DGWG #14 (official parent evidence);
7. HATM #15 (`Peng-00015-HSC/BEI.WAS/07-2026`,
   `KSEI-4628/DIR/0726`, 96.09%, ownership as-of 2026-06-30);
8. explicit LUCY RSC/removal, leaving 14 active names;
9. revised July methodology adds 37 names, producing a public current-state
   reconciliation target of 51 active tickers.

The public 51-name list and reported percentages are reconciliation targets,
not canonical event evidence. The final ledger must obtain/hash official
IDX/KSEI bytes for every admitted transition.

## July methodology boundary

BEI publicly stated on 2026-07-14 that HSC screening was expanded with a Price
Impact Ratio criterion for shares with market capitalization above Rp10
trillion. Price Impact Ratio relates price movement to transaction velocity,
and velocity uses average trading volume relative to public/free-float shares.
This created 37 new HSC names and raised the active set from 14 to 51.

The implementation therefore distinguishes:

- `HSC_2026_INITIAL`
- `HSC_2026_PRICE_IMPACT_REVISION`

The field is deliberately named `determination_methodology_version`.
It describes the methodology associated with the event that established the
currently known active state. Existing HSC names are never silently relabelled
when screening methodology later changes. If an issuer is reviewed under a new
methodology but BEI does not publish a new HSC event because it remains HSC,
this ledger does not invent a new determination event.

## Implemented contract

### `src/idx_trade/hsc_ledger.py`

`HSCEvent` requires:

- unique `event_id`;
- valid IDX ticker;
- `HSC_ACTIVE` / `HSC_REMOVED` status;
- ownership-as-of date;
- timezone-aware official publication timestamp;
- explicit concentration percentage for every active original/correction;
- determination methodology version;
- explicit IDX and KSEI announcement numbers;
- `ORIGINAL`, `CORRECTION`, or `REMOVAL` revision semantics;
- deterministic correction lineage via `supersedes_event_id`;
- official IDX source URL;
- raw attachment SHA-256;
- metadata-source SHA-256.

Fail-closed invariants:

- ownership-as-of cannot be after publication date;
- active original/correction cannot omit concentration percentage;
- duplicate event IDs fail;
- duplicate raw attachment hash across distinct events fails;
- duplicate active additions fail;
- inactive removals fail;
- correction of unknown/not-yet-published event fails;
- correction ticker mismatch fails;
- correction must be strictly later than superseded event;
- correction cannot revive an inactive state;
- correction must supersede the exact current-state event;
- removal must occur strictly after the active state begins;
- cutoffs must be timezone-aware;
- final expected active-set reconciliation is exact, not cardinality-only.

### `src/idx_trade/hsc_ledger_io.py`

Defines an exact CSV contract and strict loader. Header order is fixed. ISO
ownership date and timezone-bearing ISO publication timestamp are required.
The loader emits `HSCEvent` objects and the replay report records:

- event count;
- active count;
- sorted active tickers;
- first/last publication timestamp;
- active state counts by determination methodology.

The library intentionally does not hard-code the public list of 51 tickers.
The official/current target is an external reconciliation input.

## Tests prepared

- `tests/test_hsc_ledger.py`
- `tests/test_hsc_ledger_io.py`

Coverage includes:

- original → correction → removal PIT state;
- publication-time cutoff;
- duplicate active addition;
- inactive removal;
- unknown/stale correction lineage;
- exact active-set reconciliation;
- naive timestamp rejection;
- ownership date after publication rejection;
- correction/removal chronology;
- explicit concentration requirement for active events;
- methodology-version persistence across the July revision;
- absence of free-float/effective-supply output fields;
- strict CSV header/date/timestamp loading;
- removal blank-concentration handling;
- reconciliation report methodology counts.

A repository checkout is unavailable in the current ChatGPT container, so exact
branch/full pytest execution remains local-runtime work. The prior parent source
lane's provider suite was 10 passed and full repo pytest had only the known
unrelated storage expectation failure.

## Required official recovery milestone

Use the already accepted official transport/provenance method from the parent
source-remediation lane. Recover all missing official HSC/RSC/correction events
through the milestone cutoff 2026-08-15, especially:

- WBSA;
- TCPI;
- SATU;
- HATM;
- all 37 July additions;
- any post-expansion correction/removal/addition through 2026-08-15.

Preserve exact official metadata locator bytes and StaticData PDF bytes outside
Git. Do not derive official announcement numbers from sequence assumptions.

Normalize all accepted events to the exact CSV schema and replay them in
publication-time order.

Acceptance gates:

1. every active event has official IDX/KSEI provenance bytes and hashes;
2. every correction has deterministic supersession lineage;
3. every removal applies to a previously active ticker;
4. no synthetic event is created from a press article/current-list snapshot;
5. replay after LUCY removal yields the evidence-supported pre-expansion state;
6. replay after the July expansion yields exactly 51 active unique tickers;
7. exact active ticker set equals the official complete July/current set;
8. search/capture through 2026-08-15 finds and processes any subsequent HSC,
   RSC, or correction rather than assuming none exists;
9. output manifest pins event CSV/JSON, raw attachments, metadata captures,
   report, and all SHA-256 hashes.

## Scientific boundary

Not authorized in this milestone:

- `100 - concentration_pct` as free float;
- `effective_free_float_pct`;
- treating every >=1% holder as locked;
- HHI/top-holder features;
- daily forward-fill feature panel;
- Foreign Flow / price / volume interaction features;
- model fitting/scoring;
- labels or protected outcomes.

## Verdict

`CONTRACT_PREPARED_OFFICIAL_FULL_LEDGER_RECOVERY_REQUIRED`
