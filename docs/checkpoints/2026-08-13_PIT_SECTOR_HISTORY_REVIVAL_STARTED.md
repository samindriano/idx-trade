# PIT Sector History Revival — targeted evidence recovery

Date: 2026-08-13 Asia/Jakarta
Branch: `data/idx-pit-sector-history-revival-v1`
Status: `REVIVAL_ACTIVE_CANONICAL_GATE_STILL_5_READY_3_BLOCKED`

## Why this revival exists

The original PIT IDX-IC source audit stopped with five canonical sources ready and three blocked: annual 2022, annual 2023, and the 2026 effective date. This revival was explicitly authorized to make one more targeted recovery attempt. It does not authorize V3-D/sector-relative modeling, fresh-forward outcome access, current-label backfilling, or weaker source standards.

The canonical source contract remains `config/pit_sector_sources_v1.json`. Official IDX announcement/attachment provenance is still required before a blocked annual event can become `READY_FOR_ACQUISITION`.

## New recovery evidence

### 2022

A contemporaneous IDXChannel report reproduces the BEI annual classification-change event dated 24 June 2022 and explicitly states that the classification/index-sector changes became effective 1 July 2022. It identifies seven affected issuers:

`BIPI`, `TELE`, `MITI`, `YELO`, `IATA`, `RISE`, `WIFI`.

Discovery URL:
`https://www.idxchannel.com/market-news/bersama-lima-emiten-iata-dan-tele-ubah-klasifikasi-industri/all`

A second IDXChannel report independently states that WIFI entered IDXTECHNO effective 1 July 2022 based on BEI's classification announcement:
`https://www.idxchannel.com/market-news/solusi-digital-wifi-masuk-sektor-teknologi-di-bei-mulai-hari-ini-bagaimana-potensinya`

This materially strengthens the event/effective-date reconstruction but does **not** reveal the dedicated canonical BEI announcement reference or raw attachment. `Peng-00150/BEI.POP/06-2022` remains sector-index evaluation/reconciliation evidence only and is not promoted.

### 2023

Investor.id content mirrored by IndoPremier/IPOT reports a BEI announcement dated 22 June 2023 covering 14 listed companies whose industry classifications changed. It explicitly identifies BMTR and its move from Industrials to Consumer Cyclicals / Media & Entertainment.

Discovery URL:
`https://www.indopremier.com/ipotnews/newsDetail.php?group_news=RESEARCHNEWS&halaman=1&jdl=Ada_Info_Baru_nih_terkait_Emiten_Jagoan_Lo_Kheng_Hong_%28BMTR%29&name=&news_date=&news_id=425243&q=Global+Mediacom&search=y_general&taging_subtype=BMTR`

Issuer corroboration from PT Selamat Sempurna Tbk cites `Peng-00156/BEI.POP/06-2023` dated 22 June 2023 and records the IDXCYCLIC period July 2023-June 2024:
`https://smsm.co.id/pressreleasedet.php?id=News189-1`

`Peng-00156` remains index-sector evaluation evidence, not the missing dedicated annual classification-change source. No event-specific official effective-date statement was recovered in this pass, so 2023 remains blocked.

### 2026

The public UOB Kay Hian / UTRADE important-notice archive independently lists `Perubahan Klasifikasi Industri Perusahaan Tercatat` on 25 June 2026:
`https://www.utrade.co.id/`

This is useful archive/distribution corroboration only. It does not supply an explicit effective date for canonical `Peng-00100/BEI.POP/06-2026`; 2026 therefore remains blocked.

## Implementation in this branch

Added `src/idx_trade/pit_sector_discovery.py` and `config/pit_sector_revival_evidence_v1.json` so secondary, issuer, and broker leads can be retained reproducibly without weakening the canonical PIT gate.

The discovery registry accepts only explicit non-canonical roles:

- `SECONDARY_DISCOVERY_NOT_CANONICAL`
- `ISSUER_CORROBORATION_NOT_CANONICAL`
- `BROKER_MIRROR_NOT_CANONICAL`

It may target only canonical sources that are still `DISCOVERY_REQUIRED`, validates HTTPS/date/ticker/count semantics, and always reports:

- `canonical_promotions_authorized = 0`
- `canonical_gate_unchanged = true`

`tests/test_pit_sector_discovery.py` locks these fail-closed semantics and asserts that the committed canonical inventory still has exactly the same three blockers: 2022, 2023, and 2026.

## Current decision

The revival has produced materially better discovery evidence, especially for 2022, but **no canonical source is promoted yet**. Inventory remains `5 ready / 3 blocked`.

The remaining decision-changing work is byte-level recovery on the local machine:

1. locate/recover the exact official IDX dedicated 2022 and 2023 classification-change announcement refs/attachments;
2. hash and inspect candidate ZIP/PDF bytes and verify title/ref/date/content rather than trusting guessed URL patterns;
3. search the local/raw/web-accessible official evidence trail for a linked 2026 issuer/exchange document that explicitly states the effective date of `Peng-00100`;
4. run focused PIT-sector tests and full pytest.

Raw bytes must remain outside Git. Secondary/broker/issuer material remains discovery/corroboration only unless an independently acceptable official-source rule is separately authorized.
