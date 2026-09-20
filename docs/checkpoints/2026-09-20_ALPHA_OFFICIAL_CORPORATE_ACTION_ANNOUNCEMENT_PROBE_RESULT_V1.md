# IDX-Trade official corporate-action announcement probe

Date: 2026-09-20
Scope: outcome-blind event-document semantics only

## Verdict

`PASS_BOUNDED_CORPORATE_ACTION_EVENT_EVIDENCE`

Five retained documents from the official `Pemecahan Saham` announcement search
were inspected as event-family evidence. They do not establish an executable
price-basis transition.

## Findings

- BPII’s 8 March and 3 April 2024 filings describe a stock-split plan and
  shareholder approval at an RUPSLB scheduled for 16 April 2024. Neither body
  states that the market transition had become effective.
- PBID’s 17 May 2024 filing is proof that a stock-split schedule was advertised
  in print/web media. The announcement date is not itself an effective trading
  date.
- RMKE’s 2 July 2026 correction records the underlying event date as 20 May
  2026 and points to a detailed attachment, but the retained correction body
  does not state the effective market-transition date. The 20 May original
  attachment returned HTTP 403 and was excluded as evidence.

## Authority boundary

These documents support event-family classification and the separation of plan,
approval, advertisement, correction, event, and effective-transition concepts.
They do not supply exchange trading adjustment dates, first-session basis,
available-at/knowledge time, revision lineage, or population-wide event-to-price
linkage. No price or canonical data was changed.

Machine summary: `research_knowledge/official_corporate_action_announcement_probe_v1.json`
