# Handoff

from: PRIMARY IMPLEMENTER + AUDITOR
to: MAIN / independent reviewer
task_id: IDX-E2E-DIVIDEND-ACQUISITION-V1-2
model_used: Codex
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `c3cdc2e188801bddc31be2130544b9f5945050cd`
branch: `integration/idx-e2e-baseline-paper-v1`
head_commit: `9d304c3a`  

## scope

Finish and validate the V1.2 official IDX cash-dividend acquisition layer:
provenance, semantic extraction, temporal disposition, correction lineage,
batch finalization, restart safety, and exact recovery.

## files_changed

- `scripts/capture_forward_dividend_candidate_attachments_v1.py`
- `scripts/review_forward_dividend_candidate_attachments_v1.py`
- `scripts/review_forward_dividend_candidate_attachments_v1_2.py`
- `scripts/run_forward_dividend_acquisition_batch_v1.py`
- `src/idx_trade/forward_dividend_orchestration_v1.py`
- `src/idx_trade/forward_dividend_provenance_v1_2.py`
- `src/idx_trade/forward_dividend_semantic_review_v1_2.py`
- `src/idx_trade/forward_dividend_disposition_v1_2.py`
- focused dividend/CA tests under `tests/test_forward_dividend_*.py`
- `docs/checkpoints/2026-08-23_E2E_DIVIDEND_ACQUISITION_V1_2_ACCEPTANCE.md`

## findings

The fresh real D2B batch completed for 11 candidates with 1 live event, 6
historical observations, 2 corroborating records, 2 superseded correction
predecessors, and 0 live blockers. A second identical invocation recovered the
immutable batch with no network access and the same journal hash.

The fresh offline replay re-ran the actual certifier and disposition layer
against copied immutable v6 evidence. Seven economic values were exact:
BBCA 55/281/20/25, BBRI 137/209, and TLKM 223.1658777. No duplicate payable
event was admitted.

The producer no longer persists transient `.partial.` discovery paths. V1.2
source-chain verification still supports old stale paths only through exact
SHA resolution inside a bounded batch root.

## decisions_made

- Historical completed events remain evidence and are not injected as fresh
  paper cash flows.
- Only the BBCA Aug event is `CERTIFIED_LIVE` at as-of 2026-08-22.
- BBRI advertisement/post-event records are corroborating only.
- TLKM predecessor/correction records are superseded by the final correction.
- Official corrections published after an economic cum-date are valid when
  their own announcement/attachment chain is proven; knowledge time is not
  backdated.
- The old BBCA V1.2-looking `8c3ace…` hash is not admitted: it encodes the
  total payout `3071043782500`. The corrected DPS-25 evidence derives
  `0ba8da55aac01313f2174243d9aa47ab44cf9423a12b46b7f434297f93a4f41f`.

## decisions_needed

Independent review should confirm the identity migration note above and
whether the corrected event SHA should replace the earlier provisional
`8c3ace…` reference in any downstream documentation. No source evidence was
rewritten.

## blocking_risks

- Gross-versus-tax/net dividend treatment is intentionally unresolved; no
  haircut is applied.
- The historical query-window artifact's old event hash was generated before
  the total-payout-vs-DPS correction. Current unit coverage proves the
  window-independent identity algorithm; a second raw query-window capture
  was not repeated because the original discovery root is ACL-blocked and no
  provider retry is authorized for this lane.

## validation_run

- focused: `69 passed`, exit `0`;
- full: `608 passed`, exit `0`, 3 existing pandas warnings;
- `git diff --check`: PASS;
- offline replay result SHA:
  `454213df35c3ffd741cc137c24d502f1fc45cd46e229c1c553852b2418e07aac`;
- v6 batch manifest SHA:
  `f13195237dd2efc5ac9e2cde49daa09bf385afcdc7769f16e4a0055ecea9e90f`;
- v6 discovery manifest SHA:
  `49860596da3522e0920e8c9fe5215465d9d0b8d4d38b1d9b90d5c95ce14cd88e`;
- v6 journal file SHA:
  `e8ee29fa6f04d3261a6caafd620b18943637912c9693f575dc69e590593c4e53`;
- v6 journal-declared SHA:
  `e6493eb9e1ddc9ca6269ebf1d755f32015f817daa204366e342a31ae872f2fb4`.

## recommended_next_action

Review the identity migration note, then integrate the changed source/tests
and checkpoint in one commit. Do not install the scheduler or access outcomes
as part of this lane.
