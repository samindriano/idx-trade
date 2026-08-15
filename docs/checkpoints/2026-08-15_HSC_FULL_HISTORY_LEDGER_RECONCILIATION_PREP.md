# HSC Full-History Ledger Reconciliation — Preparation

Date: 2026-08-15 Asia/Jakarta
Parent source branch: `data/idx-ownership-hsc-source-remediation-v1`
Parent accepted source HEAD: `ba03d0d0ebe89f9219a2ac885af758b5e51c68ef`
Status: `RECONCILIATION_TARGET_IDENTIFIED_OFFICIAL_JULY_BYTES_REQUIRED`

## Scope

This checkpoint prepares the next HSC/ownership-concentration milestone only.
It does not create an effective-free-float estimate, daily feature panel, HHI,
Foreign Flow integration, model input, score, or outcome result.

The parent source audit already established official HSC/RSC publication
transport and PIT semantics. The remaining prerequisite before freezing an
Ownership Concentration Contract is to reconstruct the complete event ledger
from the program launch through the latest known current state and prove that
state transitions reconcile exactly to the published active set.

## Current chronology established

The following chronology is supported by the accepted official source audit
plus bounded public cross-checks. Public cross-checks in this document are
**reconciliation targets only**, not canonical replacement for official IDX/KSEI
attachment bytes.

### 1. Initial cohort — 2026-04-02

Nine official HSC events were already recovered and hash-pinned in the parent
source-remediation artifact:

- AGII
- BREN
- DSSA
- IFSH
- LUCY
- MGLV
- RLCO
- ROCK
- SOTS

All have ownership-as-of 2026-03-31 in the accepted source audit.

### 2. WBSA — May 2026

WBSA became the tenth active HSC name. Public reports identify:

- IDX announcement: `Peng-00010-HSC/BEI.WAS/05-2026`
- KSEI announcement: `KSEI-3075/DIR/0526`
- ownership-as-of: 2026-05-07
- explicit concentration: 95.82%

This event was not part of the bounded 13-row parent event sample and must be
recovered from official bytes for the full ledger.

### 3. TCPI and MGRO — late May / early June 2026

Public reporting and the accepted MGRO source evidence establish:

- TCPI ownership-as-of 2026-05-25, concentration 94.10%
- MGRO ownership-as-of 2026-05-26, concentration 93.76%
- MGRO has preserved original + `KOREKSI` publication lineage in the parent
  source artifact.

The sequential announcement numbering strongly indicates TCPI immediately
precedes MGRO; the official TCPI attachment/metadata must be recovered rather
than inferred from numbering.

### 4. SATU — early June 2026

SATU became the thirteenth active HSC name:

- ownership-as-of: 2026-05-29
- explicit concentration: 94.27%

Official attachment/metadata recovery remains required for the full ledger.

### 5. DGWG and HATM — 2026-06-30 / 2026-07-01

The parent source audit already recovered DGWG official evidence. Public
cross-checks identify:

- DGWG: `Peng-00014-HSC/BEI.WAS/06-2026`, `KSEI-4448/DIR/0626`,
  concentration 97.35%
- HATM: `Peng-00015-HSC/BEI.WAS/07-2026`, `KSEI-4628/DIR/0726`,
  ownership-as-of 2026-06-30, concentration 96.09%

Immediately after HATM, the program had 15 active HSC names.

### 6. LUCY explicit removal — July 2026

The accepted source audit recovered the official LUCY RSC event:

- `Peng-RSC-00001/BEI.WAS/07-2026`
- `KSEI-4604/DIR/0726`
- explicit status: `HSC_REMOVED`
- source methodology date: 2026-06-29

After this explicit removal, the active HSC set was 14 names. Public BEI
reporting on 2026-07-09 independently confirms 15 names on 2026-07-01 and 14
after LUCY left.

### 7. Methodology revision and 37-name expansion — 2026-07-14/15

BEI publicly stated that the methodology was revised by adding a Price Impact
Ratio screening criterion for shares with market capitalization above
Rp10 trillion. The Price Impact Ratio compares price movement with transaction
velocity; velocity uses average trading volume relative to public/free-float
shares. BEI stated that 37 new names entered HSC under the revised methodology,
raising the active set from 14 to 51.

The 14 names already active before the expansion were:

AGII, BREN, DSSA, IFSH, MGLV, RLCO, ROCK, SOTS, WBSA, TCPI, MGRO, SATU,
DGWG, HATM.

The 37 July additions used as the current reconciliation target are:

- POLU 99.94%
- BBHI 92.71%
- BNLI 99.92%
- BTPN 99.78%
- BYAN 98.50%
- BINA 94.79%
- BELI 93.83%
- YUPI 99.91%
- PGUN 99.95%
- KING 98.40%
- FITT 95.00%
- CMNT 99.41%
- DCII 99.96%
- BNII 99.14%
- ALII 97.62%
- CMNP 96.64%
- MEGA 95.68%
- PRAY 99.84%
- STTP 94.95%
- LIFE 99.21%
- RISE 98.03%
- FAPA 99.77%
- KONI 95.08%
- SMAR 99.58%
- MPRO 99.99%
- ELPI 98.90%
- SILO 96.70%
- MCOL 98.62%
- BBSI 99.95%
- MORA 95.65%
- SRAJ 97.21%
- MKPI 97.02%
- MLPT 99.42%
- SOHO 99.93%
- DNET 98.06%
- GEMS 99.24%
- FILM 92.98%

The complete current active-state reconciliation target is therefore exactly
51 unique tickers: the 14 pre-existing active names plus these 37 additions.

## Current-state freshness check

A web search performed on 2026-08-15 found the July 15 list of 51 as the latest
published complete HSC list and did not identify a later August HSC addition or
RSC/removal announcement. This is a search finding, not proof of absence; the
canonical current-state claim must ultimately be based on official event
capture through the chosen cutoff.

## Methodology versioning requirement

The event/state contract must not silently treat all 2026 HSC determinations as
methodologically identical.

At minimum the ledger must preserve:

- `methodology_version = HSC_2026_INITIAL` for determinations under the launch
  framework before the July revision;
- `methodology_version = HSC_2026_PRICE_IMPACT_REVISION` for determinations
  under the revised July framework where Price Impact Ratio screening applies;
- the exact publication timestamp at which any methodology revision becomes
  usable for research.

Do not infer a quantitative Price Impact Ratio threshold unless an official
source explicitly supplies it.

## Required ledger semantics

The eventual canonical event ledger should include at least:

- `ticker`
- `status` (`HSC_ACTIVE` or `HSC_REMOVED`)
- `ownership_as_of_date`
- `published_at_local`
- `published_at_utc`
- `concentration_pct` when explicitly stated
- `methodology_version`
- `idx_announcement_no`
- `ksei_announcement_no`
- `revision_kind` (`ORIGINAL`, `CORRECTION`, `REMOVAL`)
- `supersedes_event_id` when a correction is deterministically linked
- `source_url`
- `source_sha256`
- `metadata_source_sha256`

State transition policy:

1. An HSC state becomes usable only at its own official IDX publication time.
2. An active state persists until an explicit official RSC/removal event or
   another separately approved terminating event.
3. Absence of reannouncement is never interpreted as removal.
4. Corrections preserve raw event lineage and supersede only when linkage is
   deterministic.
5. Ownership-as-of dates never substitute for research knowledge time.

## Next required evidence step

Before the ledger can be frozen as canonical, recover/hash official evidence
for all missing transitions, especially:

1. WBSA;
2. TCPI;
3. SATU;
4. HATM if not already fully preserved in the parent external artifact;
5. all 37 July additions under the revised methodology;
6. any HSC/RSC/correction event after the July expansion through the chosen
   cutoff (2026-08-15 for this milestone).

Then replay events in publication-time order and require:

- zero duplicate active additions without explicit revision semantics;
- zero removals of inactive tickers;
- zero ambiguous correction lineage admitted;
- final active-set cardinality exactly 51;
- final active ticker set exactly equal to the official July/current list;
- every active state backed by official IDX/KSEI provenance bytes.

## Scientific boundary

This milestone does **not** authorize:

- `100 - concentration_pct` as free float;
- inferred `effective_free_float_pct`;
- classifying every disclosed large holder as locked;
- HHI / concentration feature materialization;
- daily forward-fill panel production;
- Foreign Flow interaction features;
- model fitting/scoring or outcome access.

## Preparation verdict

`RECONCILIATION_TARGET_IDENTIFIED_OFFICIAL_JULY_BYTES_REQUIRED`
