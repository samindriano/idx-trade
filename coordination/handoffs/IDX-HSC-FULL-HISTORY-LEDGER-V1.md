# Handoff — HSC Full-History Ledger V1

from: ChatGPT/HSC-Full-History-Ledger
to: Codex/HSC-Full-History-Ledger
branch: `data/idx-hsc-full-history-ledger-v1`
status: `CONTRACT_PREPARED_OFFICIAL_FULL_LEDGER_RECOVERY_REQUIRED`

## First coordination step

Before any runtime/network work:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer lane owns HSC full-history ledger recovery;
3. add/update the canonical TEAM_STATUS entry for this existing lane only:

`HSC full-history ledger V1 | ACTIVE | Codex/HSC-Full-History-Ledger | data/idx-hsc-full-history-ledger-v1 | recover official HSC/RSC/correction events through 2026-08-15 and require exact current-state reconciliation; no free-float inference/features/models`

Do not overwrite concurrent TEAM_STATUS changes.

## Read first

- `AGENTS.md`
- `docs/checkpoints/2026-08-15_HSC_SOURCE_REMEDIATION.md` from parent/source lineage
- `docs/checkpoints/2026-08-15_HSC_FULL_HISTORY_LEDGER_RECONCILIATION_PREP.md`
- `docs/checkpoints/2026-08-15_HSC_FULL_HISTORY_LEDGER_CONTRACT_PREP.md`
- `src/idx_trade/hsc_ledger.py`
- `src/idx_trade/hsc_ledger_io.py`
- `tests/test_hsc_ledger.py`
- `tests/test_hsc_ledger_io.py`

Accepted source parent:
`data/idx-ownership-hsc-source-remediation-v1@ba03d0d0ebe89f9219a2ac885af758b5e51c68ef`

Accepted source artifact root:
`D:\Documents\Project\idx-ownership-hsc-source-remediation-20260815-v1`

Parent manifest SHA-256:
`8cae847d2aa2aad2c16f7510d2c94d4578af522cf37e9f634caaf60bd2b6925c`

## Objective

Build the complete canonical official HSC/RSC event ledger from launch through
2026-08-15 and prove that publication-time state replay reconciles exactly to
the latest official/current HSC state.

This is event/data work only. Do not create trading/model features.

## Reuse the already accepted source transport

Do not rediscover or replace transport unnecessarily.

Parent audit established:

- preserved official IDX `GetAnnouncement` metadata locators;
- exact official IDX StaticData attachment retrieval via working IDX host;
- raw metadata/PDF bytes and hashes;
- publication timestamp vs ownership-as-of separation;
- scrip+scripless HSC semantics;
- correction and explicit RSC/removal evidence.

Use the same provenance discipline.

## Known official/published chronology anchors

Already official/hash-pinned in parent:

- 9 initial April HSC events: AGII, BREN, DSSA, IFSH, LUCY, MGLV, RLCO, ROCK, SOTS
- MGRO original + correction lineage
- DGWG
- LUCY RSC/removal

Additional high-confidence locator targets that still require official byte
recovery in this full ledger:

- WBSA:
  - `Peng-00010-HSC/BEI.WAS/05-2026`
  - `KSEI-3075/DIR/0526`
  - ownership as-of 2026-05-07
  - 95.82%
- TCPI:
  - `Peng-00011-HSC/BEI.WAS/05-2026`
  - `KSEI-3492/DIR/0526`
  - ownership as-of 2026-05-25
  - 94.10%
- SATU:
  - ownership as-of 2026-05-29
  - 94.27%
  - public chronology says it is the thirteenth HSC name
  - DO NOT infer its exact IDX/KSEI announcement numbers from sequence; recover them
- HATM:
  - `Peng-00015-HSC/BEI.WAS/07-2026`
  - `KSEI-4628/DIR/0726`
  - ownership as-of 2026-06-30
  - 96.09%

After explicit LUCY removal, there should be 14 active pre-expansion names:

AGII, BREN, DSSA, IFSH, MGLV, RLCO, ROCK, SOTS, WBSA, TCPI, MGRO, SATU,
DGWG, HATM.

## July expansion recovery

Recover official metadata + official attachment bytes for every July
Price-Impact-revision addition. The public reconciliation target contains 37
new names:

POLU, BBHI, BNLI, BTPN, BYAN, BINA, BELI, YUPI, PGUN, KING, FITT, CMNT, DCII,
BNII, ALII, CMNP, MEGA, PRAY, STTP, LIFE, RISE, FAPA, KONI, SMAR, MPRO, ELPI,
SILO, MCOL, BBSI, MORA, SRAJ, MKPI, MLPT, SOHO, DNET, GEMS, FILM.

Reported percentages from public BEI-derived coverage are available in the
reconciliation-prep checkpoint, but DO NOT promote a row until official bytes
supply/verify its exact percentage, ownership date, publication timestamp,
announcement numbers and source identity.

For July additions use:
`determination_methodology_version = HSC_2026_PRICE_IMPACT_REVISION`
only when official timing/evidence establishes that the event belongs to the
revised methodology publication set.

Old active names remain `HSC_2026_INITIAL` unless a distinct official new
determination event justifies changing their determination methodology.

## Search after the 51-name expansion

Do not assume July 15 is current just because web search found no later list.
Search official/preserved IDX metadata and attachment locators through the
milestone cutoff 2026-08-15 for:

- HSC additions;
- RSC/removals;
- KOREKSI/corrections.

Admit only official deterministic records. Preserve negative-search/query
coverage metadata so the cutoff claim is auditable.

## External artifact root

Create a new external root, for example:

`D:\Documents\Project\idx-hsc-full-history-ledger-20260815-v1`

Do not put bulk/raw official bytes in Git.

At minimum preserve:

- official metadata response bytes used for each locator;
- each official PDF/attachment;
- per-byte SHA-256;
- normalized `hsc_events.csv` using EXACT `HSC_EVENT_COLUMNS` order;
- normalized JSON equivalent;
- exact 51-target file derived from the verified official complete-list evidence;
- replay/reconciliation report JSON;
- negative-search/cutoff coverage report;
- final manifest with hashes of every derived artifact.

## Required replay

Load with:

`src/idx_trade/hsc_ledger_io.py::load_hsc_events_csv`

Replay with:

`src/idx_trade/hsc_ledger.py::replay_hsc_events`

Validate with:

`validate_active_reconciliation(replay, expected_active_tickers)`

Required checkpoints:

1. after initial April events: expected 9 active;
2. after WBSA: 10;
3. after TCPI: 11;
4. after MGRO: 12;
5. after SATU: 13;
6. after DGWG + HATM: 15;
7. after LUCY removal: 14;
8. after July revised-method additions: exactly 51;
9. after all admitted events through 2026-08-15: current state must match the
   latest official state discovered by the cutoff audit.

Any mismatch is a blocker, not something to patch with a synthetic event.

## Correction semantics

- preserve each raw original/correction attachment independently;
- correction event requires deterministic `supersedes_event_id`;
- never overwrite the original raw record;
- correction publication timestamp is its own knowledge time;
- if correction lineage is ambiguous, fail closed.

## Validation

Run before live normalization:

`python -m pytest tests/test_hsc_ledger.py tests/test_hsc_ledger_io.py -q`

Then after materialization:

`python -m pytest tests/test_hsc_ledger.py tests/test_hsc_ledger_io.py -q`
`python -m pytest -q`
`git diff --check`

If the known unrelated `tests/test_storage.py::test_explicit_revision_mode_returns_audit_conflicts`
continues to fail, report it exactly and do not modify storage in this lane.

## Hard boundaries

Do NOT:

- calculate `100 - concentration_pct` as free float;
- calculate `effective_free_float_pct`;
- infer locked shares from every >=1% holder;
- compute HHI/top-holder/model features yet;
- make a daily forward-filled HSC panel;
- join HSC into Foreign Flow/volume/price data;
- fit or score any model;
- access labels/protected outcomes;
- touch Financial PIT, Corporate Action, O2, TradingView, or AKSes lanes.

## Final output required

Return:

- final branch HEAD and clean/synced state;
- TEAM_STATUS main commit;
- focused/full pytest counts + diff-check;
- external artifact root;
- final manifest SHA-256;
- event count by ORIGINAL/CORRECTION/REMOVAL;
- event count by determination methodology;
- exact full chronology;
- pre-expansion 14-set reconciliation;
- exact final active count and ticker set;
- official evidence for all 37 July additions;
- all corrections/removals after July expansion through 2026-08-15;
- negative-search/cutoff coverage evidence;
- verdict:
  - `HSC_FULL_HISTORY_LEDGER_READY_FOR_OWNERSHIP_CONCENTRATION_CONTRACT`
  - or `HSC_FULL_HISTORY_LEDGER_INCOMPLETE`.
