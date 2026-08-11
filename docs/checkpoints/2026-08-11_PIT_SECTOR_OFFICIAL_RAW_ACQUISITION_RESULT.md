# PIT Sector Official Raw Acquisition Result

Date: 2026-08-11  
Branch: `data/idx-pit-sector-history-v1`  
Source commit before documentation: `59cfb2129350146e322c7a9e31ae3e52bee44899`  
Status: `RAW_ATTACHMENTS_ACQUIRED_CANONICAL_INVENTORY_STILL_INCOMPLETE`

## Scope and boundary

This checkpoint records official IDX raw attachment discovery, acquisition,
SHA-256 verification, and layout inspection only. Raw bytes are stored outside
Git at:

`D:\Documents\Project\idx-pit-sector-official-raw-20260811`

No raw market/source files were added to the repository. No sector model,
V3-D score, Path Risk run, fresh-forward outcome, or frozen V3-B artifact was
accessed or changed.

## Official portal

The IDX announcement API used for current discovery was:

`https://www.idx.id/primary/NewsAnnouncement/GetAllAnnouncement`

The equivalent attachment paths were requested on `idx.co.id` where exposed by
the portal and acquired from the identical official `idx.id` path when the
former returned HTTP 403 in this runtime. All acquired final URLs remained
within the official IDX host family and returned HTTP 200.

## Acquired and inspected packages

| Source / role | Announcement ref | Announced | Effective evidence | Official acquired URL | SHA-256 | Size / layout | Canonical status |
|---|---|---:|---|---|---|---|---|
| Initial baseline | `Peng-00007/BEI.POP/01-2021` | 2021-01-13 | 2021-01-25 | `https://www.idx.id/media/9594/idx-industrial-classification.zip` | `0b6b2e136e0e729fc80fb5bd97e73623aab7c461af89552d6e030837635bbcdd` | 1,617,051 B; ZIP containing `IDX Industrial Classification(1).rar` | READY |
| Annual classification 2021 | `Peng-00171/BEI.POP/06-2021` | 2021-06-24 | Raw PDF explicitly says effective 1 July 2021 | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00171_BEI.POP_06-2021.zip` | `2eb49058d63dcf16e8bb81dd3788364374adefdf1b92baa4b5fd406bcec51fbf` | 176,549 B; ZIP with 2-page `Klasifikasi Industri Peng-00171.pdf` | READY |
| Sector-index reconciliation only | `Peng-00150/BEI.POP/06-2022` | 2022-06-24 | 1 July 2022 applies to index evaluation, not canonical issuer classification | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00150_BEI.POP_06-2022.zip` | `1f13b7b3cdc75ed22b9848c08666a18488690009a98aaaa6586f745a6e9c18be` | 1,266,053 B; 69-page PDF plus 7 XLSX index attachments | RECONCILIATION |
| Sector-index reconciliation only | `Peng-00156/BEI.POP/06-2023` | 2023-06-22 | Raw PDF states July 2023–June 2024 index period; exact classification effective date absent | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00156_BEI.POP_06-2023.zip` | `da4589ee59889e606e5f8cd26cce19b119107e1a89bd9aa13b763b9071a06aca` | 687,933 B; 29-page PDF plus 1 XLSX index attachment | RECONCILIATION |
| PALM incidental classification | `Peng-00236/BEI.POP/09-2023` | 2023-09-29 | Canonical raw PDF does not state effective date; supporting official IDX issuer disclosure states 2 October 2023 | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00236_BEI.POP_09-2023.zip` | `3b85b0f1bbd0cdee1ef6dc99de2b5570da892e908458303d0fbfe29bf81959d9` | 214,514 B; ZIP with 1-page `Insidental Peng-00236.pdf` | BLOCKED ON CANONICAL DATE |
| Annual classification 2024 | `Peng-00128/BEI.POP/06-2024` | 2024-06-24 | Raw PDF does not state an effective date | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00128_BEI.POP_06-2024-ID.zip` | `4ecf5ebb2809c9007b68bfe0aa1c426428d77178ff9acbf744364afba00ad223` | 199,188 B; ZIP with 4-page `PKIE Peng-00128.pdf` | BLOCKED ON DATE |
| Annual classification 2025 | `Peng-00110/BEI.POP/06-2025` | 2025-06-23 | Raw PDF explicitly says effective 1 July 2025 | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/No.%20Peng-00110_BEI.POP_06-2025-ID.zip` | `09ecc0b059b6c486aa3220faacb55fa638e1991d26c37e26d9455fec0ceec7de` | 276,316 B; ZIP with 1-page `Klasifikasi Peng-00110.pdf` | READY |
| Annual classification 2026 | `Peng-00100/BEI.POP/06-2026` | 2026-06-24 | Raw PDF does not state an effective date | `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/No.%20Peng-00100_BEI.POP_06-2026-ID.zip` | `d95b27f4bab74a2da9ab737c3bdd96bc4626cfb97635ffa32a9449be78d7db98` | 290,000 B; ZIP with 2-page `Peng-00100-ID.pdf` | BLOCKED ON DATE |

## Supporting official PALM evidence

The official IDX issuer disclosure `Peng-00016/BEI.PP1/10-2023` was acquired
and inspected because it embeds the `Peng-00236` attachment and explicitly says
the PALM change is effective 2 October 2023:

- URL: `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202310/3fc602c18b_d3dffbcb7c.pdf`
- SHA-256: `2088a9fde16bc8ac8c0da687901eb79cc7dc2124bf9c673315ebb70c1c496fb4`
- Size/layout: 5,738 B, 4-page PDF.

The matching issuer attachment was also retained outside Git:

- URL: `https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/From_EREP/202310/33b2c3838a_8795596a1d.pdf`
- SHA-256: `69427f9a33614d89faff38d99902549cb884b05bc847a268fef4aaa4203035cf`
- Size/layout: 325,652 B, 1-page PDF.

This is supporting evidence only; the canonical PALM source remains blocked in
the inventory until its effective-date binding is accepted by the source
contract.

## Inventory audit and validation

After metadata update, the existing inventory CLI returned:

```text
sources_total=8
sources_ready=3
sources_blocked=5
complete_for_acquisition=false
```

Blocked canonical sources are annual 2022, annual 2023, PALM incidental 2023,
annual 2024, and annual 2026. The dedicated annual classification references
for 2022 and 2023 remain unresolved; the recovered `Peng-00150` and
`Peng-00156` packages are explicitly retained only as sector-index
reconciliation evidence.

Focused regression validation: `tests/test_pit_sector_history.py` passed
`8/8`.

## Next authorized step

Resolve the dedicated annual 2022/2023 classification announcements and the
canonical effective-date facts for PALM, 2024, and 2026. Only after every
required canonical source is `READY_FOR_ACQUISITION` may the fail-closed bulk
acquisition CLI run.
