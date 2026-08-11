# PIT Sector 2024 Effective-Date Evidence Result

Date: 2026-08-11 (Asia/Jakarta)  
Branch: `data/idx-pit-sector-history-v1`  
Status: `2024_EFFECTIVE_DATE_RESOLVED_REMAINING_THREE_BLOCKED`

## Scope

This bounded discovery pass prioritized official 2024 effective-date evidence
for canonical `Peng-00128/BEI.POP/06-2024`, then queried official IDX history
for 2026 and the dedicated 2022/2023 annual sources. No parser/materialization,
IPO or incidental census expansion, model work, outcomes, or `main` merge was
started.

## 2024 official recovery

The official endpoint was queried through:

`https://www.idx.id/primary/ListedCompany/GetAnnouncement`

MDKA query:

`?kodeEmiten=MDKA&emitenType=*&indexFrom=0&pageSize=100&dateFrom=20250101&dateTo=20250131&lang=id&keyword=Perubahan%20Klasifikasi%20Industri`

The response returned:

```text
Peng-00001/BEI.PP1/01-2025
TglPengumuman: 2025-01-22T17:46:47
FullSavePath:
https://www.idx.co.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/
From_EREP/202607/ca7aa2745d_f7e429b92b.pdf
```

The official PDF was acquired from the equivalent official `idx.id` path,
because the `.co.id` host returned HTTP 403 in this runtime. PDF inspection
confirmed:

- title: `Perubahan Klasifikasi Industri`;
- ticker: `MDKA`;
- reference: `Peng-00001/BEI.PP1/01-2025`;
- attachment reference: `PKIE Peng-00128.pdf`;
- explicit effective date: `24 June 2024`;
- issuer classification: `Gold` to `Diversified Metals & Minerals`;
- document size: 5,709 bytes;
- SHA-256: `860a0ab9aa0227b182d7a9c11f68a76fd775651763a962427cfca8cdc66d8f9f`.

PANI was queried independently and returned `Peng-00004/BEI.PP3/01-2025`,
also announced 2025-01-22. Its official PDF references `PKIE Peng-00128.pdf`
and independently states effective 24 June 2024. PANI SHA-256 is
`a815a268a3da6a964e13f844523e3e16519e1c291d2b8ca0c228f3518903b257` and its
size is 5,714 bytes.

## Provenance-contract decision

MDKA is promoted as the single decision-critical supporting document under the
existing multi-document contract. The canonical inventory now records:

```text
canonical source: IDX_IC_ANNUAL_CLASSIFICATION_2024
canonical ref:    Peng-00128/BEI.POP/06-2024
canonical SHA:    4ecf5ebb2809c9007b68bfe0aa1c426428d77178ff9acbf744364afba00ad223
effective_from:   2024-06-24
evidence ref:     Peng-00001/BEI.PP1/01-2025
evidence date:    2025-01-22
knowledge_at:     2025-01-22
status:           READY_FOR_ACQUISITION
```

The later publication date is not backdated. The legal/effective date is
2024-06-24, but the classification is not PIT-usable before 2025-01-22 because
the decision-critical official evidence was published then.

## Remaining discovery

- 2026: targeted official queries for `ARGO`, `HRUM`, `PACK`, and exchange-wide
  announcements found canonical `Peng-00100` and reconciliation `Peng-00099`,
  but no linked official document stating the effective date. No date was
  inferred.
- 2022 and 2023: historical `GetAnnouncement` queries for the June–July
  windows returned no canonical records. `Peng-00150` and `Peng-00156` remain
  sector-index reconciliation packages, not canonical issuer-classification
  history. No reference or date was invented.

Inventory state: `5 ready / 3 blocked`.

## Validation

- JSON inventory validation: passed.
- Focused PIT tests: `18 passed`.
- Full repository pytest: `489 passed, 0 failed, 3 existing FutureWarnings`.
- Inventory audit: `8 total`, `5 ready`, `3 blocked`,
  `effective_date_evidence_validated=2`.

## Boundary

No parser/materialization, IPO census, incidental census expansion, model,
outcome, Path Risk, V3-D/V3-B, execution/PnL, paper/live, or `main` merge was
started. Stop for ChatGPT review after this factual source-discovery result.
