# PIT Sector Exchange-Announcement Discovery Result

Date: 2026-08-11  
Branch: `data/idx-pit-sector-history-v1`  
Scope: official IDX exchange-level announcement retrieval only

## Result

The exchange-level retrieval path was recovered from the official IDX public
announcements frontend. The page calls:

```text
/primary/NewsAnnouncement/GetAllAnnouncement
```

with query parameters `keywords`, `pageNumber`, `pageSize`, `dateFrom`,
`dateTo`, and `lang`. The frontend uses `Attachments[].FullSavePath`; it
selects the attachment with `IsAttachment=0` as the primary announcement file
and exposes the remaining attachments separately. The page also discloses that
its public listing contains only the latest three years and sends older history
to TICMI.

The frontend bundles used for this audit and the acquired 2026 documents are
retained outside Git at:

```text
D:\Documents\Project\idx-pit-sector-official-raw-20260811
```

## Targeted exchange queries

| Target | Query window | Official endpoint result | Decision |
|---|---|---:|---|
| Annual IDX-IC 2022 | 2022-06-01 through 2022-07-31, classification keyword | `ItemCount=0` | remains blocked; no ref/date guessed |
| Annual IDX-IC 2023 | 2023-06-01 through 2023-07-31, classification keyword | `ItemCount=0` | remains blocked; no ref/date guessed |
| 2026 classification | 2026-06-01 through 2026-06-30, classification keyword | canonical `Peng-00100/BEI.POP/06-2026` returned | attachment acquired; effective date still blocked |

The zero-result 2022/2023 calls are a public-retention limitation, not proof
that the historical announcements did not exist. The previously acquired
`Peng-00150/BEI.POP/06-2022` and `Peng-00156/BEI.POP/06-2023` documents remain
sector-index evaluation/reconciliation evidence and are not promoted as
canonical issuer-classification sources.

## 2026 evidence

The exchange listing returned `Peng-00100/BEI.POP/06-2026`, published
2026-06-24 18:55, titled `Perubahan Klasifikasi Industri Perusahaan
Tercatat`, with official PDF and ZIP attachments. The PDF was downloaded from
the equivalent official `idx.id` host because the `idx.co.id` attachment host
returned HTTP 403 in this runtime.

```text
PDF bytes: 312989
PDF SHA-256: 8b5413f18afc75cc17260c2400611d710e8f270d46a49c5a396f557b27cf8b25
```

The PDF explicitly lists issuer classification changes but does not state an
effective date. The nearby `Peng-00099/BEI.POP/06-2026` sector-index evaluation
states that its index period begins 2026-07-01. It is not canonical issuer
classification evidence, so it was not promoted and 2026-07-01 was not
inferred as the classification effective date.

## Inventory decision

No canonical source was promoted in this audit. The inventory remains:

```text
5 ready / 3 blocked
```

Blocked sources are dedicated annual 2022, dedicated annual 2023, and linked
official effective-date evidence for canonical 2026 `Peng-00100`.

No parser/materialization, IPO or incidental census expansion, model, outcome,
Path Risk, fresh-forward access, or `main` merge was started.

## Validation

- Focused: `python -m pytest tests/test_pit_sector_history.py -q` — 18 passed.
- Full: `python -m pytest -q` — 489 passed, 0 failed, 3 existing
  FutureWarnings.
