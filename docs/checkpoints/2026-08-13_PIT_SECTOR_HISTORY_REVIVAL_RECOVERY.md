# PIT Sector History Revival — Targeted Recovery Result

Date: 2026-08-13 (Asia/Jakarta)
Status: `REVIVAL_REVIEW_BLOCKED_5_READY_3_BLOCKED`
Branch: `data/idx-pit-sector-history-revival-v1`
Starting HEAD: `620480cd768ea784b82b71b14c1232d406b39143`

## Scope

This checkpoint records one bounded local recovery attempt for the three
remaining annual/effective-date blockers. The attempt did not alter the PIT
event contract, source methodology, canonical artifacts, model code, or
runtime market data. The external evidence root is:

`D:\Documents\Project\idx-pit-sector-official-raw-20260811\revival-targeted-20260813`

No credentialed source was used.

## Results

### 2022 annual classification

The exact dedicated official IDX reference remains unresolved. The bounded
static-path probe covered `Peng-00140` through `Peng-00155`, including the
known index-only `Peng-00150`, with the small gaps `Peng-00147` and the
already-known/non-canonical paths recorded separately.

Successful official ZIP candidates were inspected by archive member/title:

- `Peng-00140`: HOMI;
- `Peng-00141`: HOMI;
- `Peng-00142`: ESTA;
- `Peng-00143`: BULL-W2;
- `Peng-00144` and `Peng-00145`: PBSA;
- `Peng-00146`: index evaluation;
- `Peng-00148`: watchlist;
- `Peng-00149`: PKIE;
- `Peng-00151`: watchlist;
- `Peng-00152`: EAST-W;
- `Peng-00153`: ESTA-R;
- `Peng-00154`: index evaluation;
- `Peng-00155`: watchlist.

None is the dedicated `Perubahan Klasifikasi Industri Perusahaan Tercatat`
event for BIPI, TELE, MITI, YELO, IATA, RISE, and WIFI. The existing
`Peng-00150` remains reconciliation/index evidence only. No 2022 source row
was promoted.

### 2023 annual classification

The exact annual reference was recovered from a secondary copy as
`Peng-00158/BEI.POP/06-2023`. The preserved annual mirror has SHA-256
`9a7a0a594e8be535d154b0bfba7f59625d0825dfc0513b33ef893adaf1fdc81c` and
contains the official IDX document title, the 14-company statement, BMTR, and
the event date 22 June 2023.

A separate BMTR issuer-document mirror has SHA-256
`4dc7a816f4ca75f94168b0938b7bc00abe1884e35ba0253b64615c1823b37fe4`. It
states that BMTR's change is effective 03 July 2023 and links
`Klasifikasi Peng-00158.pdf` as an attachment.

The official IDX static path
`https://www.idx.id/StaticData/NewsAndAnnouncement/ANNOUNCEMENTSTOCK/Exchange/Peng-00158_BEI.POP_06-2023.zip`
returned HTTP 200 but only an empty ZIP of 22 bytes, SHA-256
`8739c76e681f900923b900c9df0ef75cf421d39cabb54650c4b9ad19b6a76d85`.
The tested official filename variants returned HTTP 404. Therefore the exact
ref is now known, but the direct official IDX annual bytes/provenance are not
available and the event-wide effective date for all 14 companies is not
proven. The source remains `DISCOVERY_REQUIRED`.

### 2026 annual classification

The canonical `Peng-00100/BEI.POP/06-2026` source remains unchanged. The
official IDX API query returned that canonical announcement; its preserved
official PDF has SHA-256
`8b5413f18a6fc75cc17260c2400611d710e8f270d46a49c5a396f557b27cf8b25` and
does not state an effective date.

The existing official related index-evaluation PDF
`Peng-00099/BEI.POP/06-2026` explicitly states index constituent periods
beginning 1 July 2026 and includes ARGO/HRUM. Its SHA-256 is
`a929bc3ab70b9d51235c29de0acb347957bd6afe976344a21d8ae332f482abcf`.
This is explicit index applicability, not an event-specific classification
effective-date statement, so it was not used to infer or promote the
`Peng-00100` effective date. The direct UTRADE mirror request returned HTTP
403 in the raw fetch; no canonical promotion was made.

An official ListedCompany query for BMTR in the 2023 date range was also
attempted on both IDX hosts and returned HTTP 403 (`idx.co.id`) and HTTP 503
(`idx.id`); no response bytes were obtained. The exact query and statuses are
preserved in `api-2023-BMTR-listed-announcement_attempt.json`.

## External artifact integrity

The recovery root contains 33 hashed files. The complete artifact manifest is:

`D:\Documents\Project\idx-pit-sector-official-raw-20260811\revival-targeted-20260813\artifact_hash_manifest.json`

Manifest SHA-256: `e9de303c5351b24d2d2f67f577a2785b6cf0578deb7c208973914b7667a725cb`

The existing canonical raw root was not modified by this attempt.

## Canonical decision

`config/pit_sector_sources_v1.json` remains unchanged:

- ready: 5;
- discovery-blocked: 3;
- canonical status: `SOURCE_DISCOVERY_BOUNDED_COMPLETE_RAW_ATTACHMENTS_INCOMPLETE`.

No guessed announcement number or URL was promoted. No sector intervals were
rebuilt from secondary evidence. No sector model, V3-D, retraining, forward
outcome, O2, OPEN, Path Risk, or main merge was started.

## Validation

- focused PIT-sector tests: **23 passed**;
- full pytest: **494 collected, exit 0**.

Committed documentation HEAD: `a2bf0357dd5549f104c94936d4dfc0b6b3749376`.
