# Historical E2E Dividend Corpus Complete Source V1

Date: 2026-08-24 Asia/Jakarta  
Branch: `research/idx-historical-e2e-replay-v1`  
Mode: outcome-blind official IDX source normalization

## Source corpus

The bounded batch collector captured the exact official IDX
`ListedCompany/GetAnnouncement` response for every required exposure ticker:

- required tickers: `347/347`
- raw response files: `347`
- source rows: `53,637`
- every response: HTTP 200 JSON with `len(Replies) == ResultCount`
- date window: `2023-12-28..2026-07-17`
- provider commit: `75d6c0f74fa360d225794c70c383348977de6798`
- batch manifest SHA-256: `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`
- normalized manifest SHA-256: `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`

External roots:

- raw/batch: `D:\Documents\Project\idx-historical-e2e-dividend-corpus-batch-20260824-v1`
- normalized: `D:\Documents\Project\idx-historical-e2e-dividend-corpus-normalized-20260824-v1`

The four initial parser failures were resolved offline from the immutable raw
bytes. They were non-common `Kode_Emiten` metadata forms (`C-BBTN`, `B-BJTM`,
and descriptive labels), not missing provider rows. The source raw bytes were
not rewritten.

## Candidate inventory

- total dividend-related candidates: `921`
- cash-dividend candidates: `844`
- ambiguous dividend candidates: `60`
- unsupported non-cash candidates: `17`
- tickers with cash candidates: `201`
- tickers without dividend-keyword candidates: `146`
- cash-candidate attachments referenced: `2,023`
- cash candidates without attachment metadata: `0`

This is a complete announcement *source* corpus, not yet a complete
economic dividend-event corpus. A title-level cash candidate can represent a
notice, correction, schedule, or another document whose exact ex-date,
entitlement, gross amount, payment date, and knowledge-time semantics require
attachment review. The 146 ticker-level absence results are therefore not yet
promoted to `CERTIFIED_NO_RELEVANT_EVENT`.

## Verdict

`DIVIDEND_ANNOUNCEMENT_SOURCE_COMPLETE_ATTACHMENT_SEMANTICS_PENDING`

The old 11-candidate/7-event bounded corpus is superseded for source coverage
diagnostics, but the frozen dividend gate remains blocked until candidate
semantic evidence is resolved or a separately approved conservative policy
can certify the no-event and event rows. No outcome, label, return, or model
metric was accessed.
