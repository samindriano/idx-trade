# Definitive public IDX Equity EoD entitlement boundary

Date: 2026-08-09

Branch checkpoint before this note: `data/idx-data-002c` at `76d347d8a1e28927a116594c2f35b6497146a959`.

## Decision

The 504-session failure is now classified as a **source entitlement / public-retention boundary**, not as an unresolved parser bug and not as evidence that the official IDX opening-price report never existed.

The bounded `Stock_First_Trx / SOYYMMDD.zip` audit found:

- target missing ACTIVE rows: 390 total;
- FREN: 196;
- MASA: 22;
- MFIN: 172;
- unique required sessions: 233;
- target-window SO files publicly available: 0/233;
- classification: 233 `FILE_NOT_FOUND`;
- observed public SO retention: 2020-02-03 through 2020-08-19;
- legacy sample archive: DBF with `STK_FIRST`, outside the 504 target window.

This result is consistent with the official IDX announcement `S-07014/BEI.LDT/11-2020` dated 27 November 2020. IDX states that the EoD data under Market Summary, Download data/Daily, and T1/T2 are the `IDX Equity EoD` data-service product. Effective 4 January 2021, IDX stopped uploading those EoD datasets to the public idxdata/idxdata2/idxdata3 daily folders. Access thereafter requires an IDX Data Services agreement and a subscription fee.

Official notice:

- https://www.idxdata3.co.id/Pengumuman/SIGNED_1410257_1927-S-07014-BEI.LDT-11-2020-%2827-11-20%29---Pelanggan-Data-BEI---Peralihan-Media-Distribusi-IDX-Equity-EoD.pdf

Official contact in that notice:

- `idxdata@idx.co.id`

## Permanent interpretation

Do not repeat public `SOYYMMDD.zip` probing for post-2020 dates as though a different URL or parser is likely to recover the missing 2024-2025 opening-price rows. The lack of public files is explained by the official distribution-policy change.

The free/public-only data contract therefore has a demonstrated boundary for these exact historical opening-price cases.

This does **not** mean the historical official data do not exist. It means they are no longer distributed through the old public daily folders. A defensible next attempt requires one of:

1. properly entitled `IDX Equity EoD` data from IDX Data Services;
2. another officially licensed/authoritative data channel such as TICMI if it provides the required fields and historical coverage under an acceptable license;
3. a separately reviewed research-contract change that genuinely removes the need for opening prices. Such a contract change must be justified by the future execution/label specification and must not be introduced merely to force the 504 gate green.

## Current certification status

- 43 sessions: certified PASS;
- 126 sessions: certified PASS;
- 504 sessions: FAIL / not certified;
- 1260 sessions: not started; preparation only.

No 504 panel or manifest exists. No modelling, `IDX-VAL-002`, main merge, paper trading, or live trading is authorized by this checkpoint.

## Recommended next decision

Choose explicitly between:

- acquiring entitled official historical EoD data and continuing 504 -> 1260 certification; or
- freezing long-history data certification as blocked-by-entitlement and allowing only bounded Stage-2 research/specification work on the already certified 126-session snapshot, without presenting short-window modelling as robust performance evidence.
