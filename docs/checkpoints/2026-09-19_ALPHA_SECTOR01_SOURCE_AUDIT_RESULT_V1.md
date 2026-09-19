# SECTOR-01 Official IDX-IC Archive — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Status: `SOURCE_PARTIAL_STRUCTURAL_SIGNAL / NOT_ADMITTED / NO CANDIDATE`

## Decision

The locally available official IDX-IC archive contains structured sector
constituent workbooks for 2022 and 2023, plus PDF-only classification/index
artifacts for other frozen years. The structured workbooks are parseable and
internally coherent at the sheet level, but they do not provide a PIT-safe
daily sector-membership surface. The result remains a source capability only;
no sector feature or candidate was created.

## Inventory and quality profile

The frozen inventory contains `7` archives:

| Archive | Structured sector rows | Unique tickers | Disposition |
|---|---:|---:|---|
| `IDX_IC_2021_Peng-00171.zip` | PDF only | — | inventory only |
| `IDX_IC_2022_Peng-00150.zip` | `769` current + `4` exit rows across `11` sheets | `769` current | structured snapshot |
| `IDX_IC_2023_Peng-00156.zip` | `838` current + `10` exit rows across `11` sheets | `836` current | structured snapshot; 2 cross-sheet duplicates |
| `IDX_IC_2024_Peng-00128-ID.zip` | PDF only | — | inventory only |
| `IDX_IC_2025_Peng-00110-ID.zip` | PDF only | — | inventory only |
| `IDX_IC_2026_Peng-00100-ID.zip` | PDF only | — | inventory only |
| `IDX_IC_BASELINE_2021_idx-industrial-classification.zip` | RAR only | — | inventory only |

Across the two structured workbooks there are `22` sector sheets, `1,607`
current constituent rows plus `14` explicitly separated exit rows, and `837`
unique current ticker codes observed. All sheets have a
recognizable `Kode` header, non-empty announcement-date text, and effective
period text. No duplicate ticker occurs within a sheet.

The 2023 workbook has two cross-sheet duplicate codes:

- `GWSA`: `E CYCLIC` and `H PROPERT`.
- `KOTA`: `E CYCLIC` and `H PROPERT`.

This may reflect source classification semantics, but the available package
does not provide an identity/sector-transition authority that resolves it.
It is therefore recorded as an ambiguity rather than silently choosing one
sector.

The structured snapshots state periods of `Juli 2022 s.d. Juni 2023` and
`Juli 2023 s.d. Juni 2024`, with announcement text dated `24 Juni 2022` and
`22 Juni 2023`. These are document-level dates/periods, not row-level
available-at timestamps or daily membership intervals.

## Missing admission gates

| Gate | Result |
|---|---|
| Archive presence and SHA-256 inventory | `PASS` |
| Workbook/sheet parse and header shape | `PASS` |
| Within-sheet ticker validity/uniqueness | `PASS` |
| Cross-sheet sector partition | `UNKNOWN — GWSA/KOTA duplicates` |
| Daily membership intervals | `ABSENT` |
| Row-level public available-at | `ABSENT` |
| Issuer/ISIN/security transition chain | `ABSENT` |
| Revision/vintage history | `ABSENT` |
| Full 2021–2026 structured coverage | `ABSENT / PDF-only gaps` |
| Predictive admissibility | `NOT ADMITTED` |

Do not expand these snapshots across every trading day, forward-fill sector
labels, resolve duplicate classifications by ticker alone, or treat document
announcement/effective dates as PIT publication authority. The source can
support a future sector-history contract only after publication timing, daily
membership, identity continuity, and revision rules are independently
established.

## Reproducibility and integrity

- Preregistration: `docs/checkpoints/2026-09-19_ALPHA_SECTOR01_SOURCE_PREREGISTRATION_V1.md`.
- Generator: `research/alpha_sector01_source_audit_v1.py`; SHA-256
  `0b825267e266b996793ea8af3cfab1ce5c9ee7834ef6b427480f206b2ed3f0e1`.
- Result JSON SHA-256:
  `ef9e6ee870b1153c174b0a5c906f1fbe4e9a8bd08bb6d59d3646268554dc17b9`.
- Independent verifier: `research/verify_alpha_sector01_source_audit_v1.py`;
  SHA-256 `e1fc7dc5656407de0508b554c13d2b82ebe10f08206a3a7a02d2199298cc75fb`.
- Independent verification: `PASS`; output SHA-256
  `81c8fd878d8c84cbf8de77299ded6cf6e95aeee8cd84af31b64eee78659eb4db`.
- Artifact hash-contract verifier: `PASS`; output SHA-256
  `8121fa7e9651d1eecebd3b89a51e9d69c96584d2e4a58d7c7131b3bb0b1a2493`.
- Hash-contract verifier code SHA-256:
  `c587bba69fbfdd77cf9ea4f5ce0dbda191ec5efd191bff55355f0b32cf9ca138`.

Source archive SHA-256 values are recorded in the result JSON and bind the
exact frozen inventory. No target/outcome/provider/cloud/incumbent/canonical
data/capture/scheduler/telemetry/production state was accessed or modified.

## Next allowed action

No sector feature or candidate is justified from this package. The next
useful step requires a separate source contract for daily constituent
membership, document publication timing, identity continuity, and revisions;
otherwise retain SECTOR-01 as a documented partial capability and do not retry
with imputation or provider fallback.
