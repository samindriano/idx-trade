# Historical E2E Dividend Attachment Bounded Sample V1

Status: `BOUNDED_DIVIDEND_ATTACHMENT_SAMPLE_INSUFFICIENT_FOR_REPLAY`

This checkpoint records one bounded official-attachment acquisition sample. It
does not amend the frozen dividend ledger, exposure gap, or replay scope.

## Scope and provenance

- branch result lane: `research/idx-historical-e2e-replay-v1`
- code fix commit: `8612c5fe0fb4af19fb6d27d78a9693367a51fc59`
- normalized candidate manifest SHA-256:
  `a94a04b7d8c2dcefafbd8397e03e36059efbdeaab609068644d53371d1b6b167`
- parent raw manifest SHA-256:
  `9c89e0e089827a46c51a18ee3d2ddba36861fc02660f677942315d9d367e25bf`
- parent raw manifest status: `INCOMPLETE`
- parent raw failed tickers: `BBTN`, `BJTM`, `CYBR`, `RAJA`
- scoped discovery manifest SHA-256:
  `4ab091edad907b9fe4df3f445ce6b80168bd8500730bc19dd123243ba8fa556e`
- selection manifest SHA-256:
  `19e9e8f6b51e73548103fa84ade30d01cd6fad9f2dcd03648994c4f27a302499`

The scoped discovery inventory is complete only for normalized cash-candidate
tickers whose local raw page bytes match the normalized `source_raw_sha256`.
It is not evidence that the parent 347-ticker corpus is complete and it is not
a no-dividend-event ledger.

## Bounded acquisition

The exposure-window selection contained 219 matching cash candidates. The first
10 deterministic candidates were captured with one attempt per attachment and
the pinned official IDX transport. No retry or alternate provider was used.

- candidates selected/captured: `10 / 10`
- PDF attachment count: `25`
- capture failures: `0`
- semantic review PASS: `7`
- semantic review fail-closed: `3`
- exposure overlaps among the 7 semantic PASS events: `2` rows
- no-event promotions: `0`
- dividend ledger updates: `0`
- replay scope updates: `0`

The two ABMM overlap records are not promoted. They have the same economic
dates and amount but distinct announcement evidence and different payment
dates, so the correction/duplicate lineage must be reconciled before an event
can be admitted. The AKRA PASS records also contain multiple announcement
identities for the same economic dates and amount and remain evidence-only.

The three rejected reviews were:

- AALI 2025-04-29: non-unique generic per-share amounts;
- AALI 2026-04-17: non-unique generic per-share amounts;
- AKRA 2024-08-09: no uniquely attributable amount.

These are intended fail-closed outcomes, not parser failures.

## Decision

The sample proves that the corrected manifest adapter can consume the pinned
normalized candidate inventory and that official PDF bytes can be captured and
reviewed with immutable hashes. It does not establish market-wide no-event
proof, complete dividend exposure coverage, or a contiguous replay scope.

The controlling blocker remains:

`DIVIDEND_EXPOSURE_WINDOW_PROOF_INCOMPLETE`

No historical paper replay, performance calculation, return/outcome access, or
Monte Carlo calculation is authorized from this sample.

