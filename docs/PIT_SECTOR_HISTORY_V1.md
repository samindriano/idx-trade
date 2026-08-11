# PIT Historical IDX-IC Sector History V1

Date: 2026-08-11
Status: `DATA_FOUNDATION_IMPLEMENTATION_STARTED_SOURCE_INVENTORY_INCOMPLETE`
Branch: `data/idx-pit-sector-history-v1`

## Goal

Build a provenance-preserving point-in-time historical IDX-IC classification layer that can answer:

> For ticker `X` and signal date `t`, which IDX-IC sector classification was both effective and already knowable at `t`?

This is a data-foundation track only. It does not authorize a sector-relative model experiment.

## Source hierarchy

1. Official IDX classification announcement/attachment.
2. Official IPO/prospectus/listing evidence for a newly listed company.
3. Official current IDX classification only as terminal-state reconciliation.
4. Third-party material may be used to discover an official reference, not as silent canonical history.

The first known source is the January 2021 IDX-IC baseline package referenced by announcement `Peng-00007/BEI.POP/01-2021`, effective 25 January 2021.

Annual classification sources for 2021-2026 must be fully inventoried before bulk acquisition. Known 2024/2025 announcement references are recorded in `config/pit_sector_sources_v1.json`; unresolved years remain explicit blockers rather than guessed dates or URLs.

## Source inventory semantics

`config/pit_sector_sources_v1.json` uses two statuses:

- `READY_FOR_ACQUISITION`: official HTTPS IDX URL, announcement date and effective date are all verified;
- `DISCOVERY_REQUIRED`: at least one decision-critical source fact is unresolved.

The acquisition runtime fails closed if even one required source remains `DISCOVERY_REQUIRED`. This prevents a partial annual history from being mistaken for complete PIT coverage.

## Official raw acquisition update — 2026-08-11

Official IDX attachment resolution and inspection was completed without placing
raw bytes in Git. The raw acquisition directory is
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

The verified canonical raw attachments are recorded in
`config/pit_sector_sources_v1.json` and the dated checkpoint
`docs/checkpoints/2026-08-11_PIT_SECTOR_OFFICIAL_RAW_ACQUISITION_RESULT.md`.
The files were fetched from the official `idx.id` host because the equivalent
`idx.co.id` attachment URLs returned HTTP 403 in this runtime; no external host
or substitute dataset was used.

Current canonical inventory state:

- `IDX_IC_BASELINE_2021`, `IDX_IC_ANNUAL_CLASSIFICATION_2021`,
  `IDX_IC_INCIDENTAL_PALM_2023`, and `IDX_IC_ANNUAL_CLASSIFICATION_2025`
  have verified official provenance and explicit effective dates, so they are
  `READY_FOR_ACQUISITION`.
- Raw attachments for `IDX_IC_ANNUAL_CLASSIFICATION_2024` and
  `IDX_IC_ANNUAL_CLASSIFICATION_2026` were recovered and inspected but remain
  `DISCOVERY_REQUIRED` because no explicit effective-date evidence has yet
  been bound to those canonical events. No date is inferred from an
  announcement date or a generic July convention.
- `Peng-00150/06-2022` and `Peng-00156/06-2023` were recovered as official
  sector-index evaluation packages and remain reconciliation evidence, not
  canonical issuer classification events. The dedicated annual classification
  sources for 2022 and 2023 therefore remain unresolved.

The CLI inventory audit reports `4` ready and `4` discovery-blocked canonical
sources. Full acquisition remains intentionally blocked until every required
canonical source has verified key dates and provenance.

## Multi-document effective-date provenance contract — 2026-08-11

A separate official IDX document may establish the effective date of a
canonical classification event. This is valid only when the nested
`effective_date_evidence` object contains:

- an official HTTPS IDX URL and its 64-hex SHA-256;
- an explicit announced date and effective date;
- a distinct official announcement reference;
- explicit linkage to the canonical `source_id`, announcement reference, and
  canonical raw SHA-256;
- a non-empty affected-ticker list, classification-change description, and
  linkage statement.

The canonical source's top-level `effective_from` remains mandatory. The
nested evidence may validate that date, but can never populate or infer a
missing canonical date. When acquisition is complete, the linked evidence is
downloaded, hash-checked, and recorded as a nested manifest entry alongside
the canonical raw document.

PALM validates this contract: canonical `Peng-00236/09-2023` supplies the
classification change and linked official `Peng-00016/10-2023` supplies the
explicit 2 October 2023 effective date.

### PIT knowledge-time refinement

Supporting official evidence is allowed to be published **after** the stated
effective date. Such evidence is still valid historical provenance; rejecting
it would be unnecessarily strict. However, it cannot make the classification
knowable before the evidence itself existed.

The source validation therefore keeps three distinct dates:

```text
effective_from
canonical announced_at
supporting evidence announced_at
```

For linked effective-date evidence the validation derives:

```text
knowledge_at = max(
  effective_from,
  canonical announced_at,
  supporting evidence announced_at
)
```

Example:

```text
effective_from                 2024-07-01
canonical announced_at         2024-06-24
supporting evidence announced  2024-07-05

knowledge_at / PIT usable      2024-07-05
```

The event is historically effective on 1 July, but a backtest may not use that
classification before 5 July because the decision-critical supporting evidence
was not yet knowable.

PALM is unchanged by this refinement because its supporting official evidence
was announced on the same date as its effective date: 2 October 2023.

## Raw acquisition contract

`src/idx_trade/pit_sector_history.py`:

- accepts HTTPS URLs only under `idx.co.id`, `idx.id`, or their subdomains;
- rejects redirects that leave the official IDX host family;
- rejects empty and non-200 responses;
- stores raw source bytes outside Git;
- records exact SHA-256, requested/final URL, retrieval timestamp, content type, announcement reference and effective date;
- records linked evidence `announced_at` and derived `knowledge_at` in the acquisition manifest;
- never rewrites a source into a synthetic historical snapshot.

CLI audit only:

```powershell
python -m idx_trade.pit_sector_history `
  --inventory config/pit_sector_sources_v1.json
```

Acquisition is intentionally blocked until the inventory is complete:

```powershell
python -m idx_trade.pit_sector_history `
  --inventory config/pit_sector_sources_v1.json `
  --output-dir <OUTSIDE_GIT_DIR> `
  --acquire
```

## Canonical parsed event schema

At minimum:

```text
ticker
sector_code
effective_from
announced_at
source_id
source_sha256
```

When a decision-critical linked document becomes knowable later than the
canonical announcement, the parser/event builder must also carry:

```text
knowledge_at
```

If no later decision-critical evidence is needed, `knowledge_at` defaults to
`announced_at` for backward-compatible event construction.

Optional lower IDX-IC hierarchy fields:

```text
subsector_code
industry_code
subindustry_code
```

The implementation derives:

```text
pit_from = max(effective_from, announced_at, knowledge_at)
```

This distinction is deliberate. A classification cannot be used by the model before it is both effective and knowable from all decision-critical official evidence.

## PIT join behavior

For every `ticker x signal_date`, `attach_sector_asof` selects the latest event whose `pit_from <= signal_date`.

Consequences:

- current sector labels are never backfilled into the past;
- an announcement made before its effective date starts only on the effective date;
- a supporting official document published after the effective date delays PIT usability until that document's announcement date;
- a late-discovered/late-announced classification starts only when knowable;
- no prior event means `sector_pit_known=false`, not a guessed current sector.

Conflicting sector codes for the same ticker and effective date fail closed.

## Implementation stages

```text
source inventory
    ↓
official raw acquisition + SHA
    ↓
source-specific parsing
    ↓
canonical classification events
    ↓
PIT interval/as-of audit
    ↓
coverage + conflict reconciliation
    ↓
freeze data artifact
    ↓
separate sector-relative research spec (not authorized yet)
```

The current branch implements the inventory/acquisition contract and canonical event/PIT join semantics. Source-specific attachment parsers are deliberately deferred until the exact official raw formats are acquired and inspected.

## Current blockers

Before raw acquisition may run, resolve the remaining four canonical blockers:

- annual 2022 dedicated issuer-classification source;
- annual 2023 dedicated issuer-classification source;
- annual 2024 explicit official effective-date evidence;
- annual 2026 explicit official effective-date evidence.

After the annual/event foundation is complete, separately enumerate IPO classifications and other incidental changes before treating historical coverage as complete.

Do not infer missing annual events from the current IDX sector list.

## Hard boundaries

This track does not authorize:

- modifying the frozen V3-B ranker;
- running V3-D or another sector-relative model;
- fresh-forward realized outcome access;
- using current sector labels as historical truth;
- silently ingesting third-party historical sector datasets;
- Path Risk rescue work;
- execution/PnL/Kelly/paper/live work;
- merge to `main`.
