# Historical E2E CA Target Attachment Audit V1

Date: 2026-08-24 Asia/Jakarta  
Branch: `research/idx-historical-e2e-replay-v1`  
Mode: outcome-blind official IDX attachment remediation

## Purpose

This checkpoint records a bounded attempt to turn the complete announcement
source corpus into exact corporate-action schedule evidence for the frozen V4
historical E2E trajectory. It does not rewrite or reinterpret the accepted
V4 CA event-window ledger, and it does not open returns, labels, outcomes, or
performance metrics.

## Discovery coverage

Inputs:

- frozen schedule-needs SHA-256:
  `441253ec7a40a789eac00b4dd4159fc9470c6e4dcab23cd7c2c20bc9596cffed`;
- target announcement discovery CSV SHA-256:
  `c140dd08739c2a7ab2a9d9a30e1dc395c064fd85237b8ca7ad88a694e441ffb0`;
- complete announcement source batch SHA-256:
  `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`;
- provider commit:
  `75d6c0f74fa360d225794c70c383348977de6798`.

The schedule-needs ledger contains 94 unique event IDs across 74 tickers.
The bounded matching pass found:

- 62/94 event IDs with any issuer announcement in the existing +/-14-day
  discovery window;
- 35/94 event IDs with an action-specific title or equivalent CA keyword;
- 59/94 event IDs without an action-specific announcement candidate in this
  corpus/window.

The absence of a candidate is not treated as proof that no event occurred.

## Official attachment acquisition

Two external, immutable capture roots were used. Raw source files and PDFs
remain outside Git:

- `D:\Documents\Project\idx-historical-e2e-ca-target-attachment-audit-20260824-v2`
  - 60 unique announcements;
  - 138 attachment requests;
  - 133 PDF responses with HTTP 200 and PDF magic;
  - manifest SHA-256:
    `e8ae75db0bf6f8314c5c7e582a6bc98e5bb903fbfa3ce73f96d3f9685f82db3f`.
- `D:\Documents\Project\idx-historical-e2e-ca-target-attachment-zip-remediation-20260824-v2`
  - 7 official BEI `No. Peng-...` ZIP notices;
  - 7/7 HTTP 200 ZIP responses;
  - manifest SHA-256:
    `03d842b17cf9f2dd28cd98e9d4fe88e87737395ab6b1ec82b339b326425e8d83`.

The ZIP remediation corrected a format assumption only. It did not substitute
another provider or alter the source bytes.

## Evidence found

The following are exact official-attachment candidates, not yet entries in the
frozen CA ledger:

- `INDS` stock split: official issuer/IDX attachments state the old-basis last
  trading date as 2024-07-03, new-basis regular/negotiation trading from
  2024-07-04, recording date 2024-07-05, and cash-market new-basis trading from
  2024-07-08.
- `PTRO` stock split: attachments state 2025-01-02 as the last old-basis
  trading date, 2025-01-03 as the first new-basis regular/negotiation date, and
  2025-01-07 for the cash market; the issuer document states a 1:10 split.
- `MFIN` merger: the final schedule attachment states the merger effective
  date as 2025-10-01 and MFIN delisting as 2025-10-02. This is a direct
  schedule candidate, but it still requires exact mapping to the frozen event
  identity and policy transition semantics.
- `INET` HMETD: the correction attachment states effective OJK date
  2025-12-22, regular/negotiation cum 2026-01-02, ex 2026-01-05, record date
  2026-01-06, and HMETD trading/implementation dates through January 2026.
- Official ZIP notices: BUVA states 2025-11-03 cum, 2025-11-04 theoretical
  price, HMETD trading 2025-11-07..13, and removal from the list from
  2025-11-14; COCO states 2025-10-08 cum, 2025-10-09 theoretical price,
  trading 2025-10-14..20, and removal from 2025-10-21. MEJA, MMIX, and RISE
  provide official bonus-share theoretical-price notices with explicit cum and
  next-session dates.

All dates above are quoted as source-backed candidate evidence. No generic
`TanggalPencatatan` substitution was made, and no event was promoted solely
from an announcement date or title.

## Dividend boundary

The 347-ticker announcement corpus remains source-complete, but its 844 cash
dividend candidates still require attachment-level economic-event review. The
146 tickers without dividend-keyword candidates are not certified no-event.
This remediation therefore does not close the market-wide dividend
no-event/entitlement blocker.

## Verdict

`CA_TARGET_ATTACHMENT_SOURCE_PARTIALLY_RECOVERED_CONTINUITY_NOT_CERTIFIED`

The official IDX source path is viable for targeted schedule recovery, and the
ZIP format is now understood. However, only 35/94 event IDs currently have an
action-specific candidate, and the candidate evidence has not been reconciled
into the frozen event-window ledger. The strict 6x100 historical replay scope
therefore remains empty. No returns, P&L, NAV, CAGR, drawdown, Monte Carlo,
labels, protected outcomes, or model metrics were accessed.

`coordination/TEAM_STATUS.md` was not edited because MAIN owns that file.
