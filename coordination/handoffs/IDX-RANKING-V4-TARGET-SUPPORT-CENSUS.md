# Handoff

from: Codex
to: ChatGPT independent review
task_id: IDX-RANKING-V4-TARGET-SUPPORT-CENSUS
model_used: Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `86981922c41354bc5629c5e6a327839667ccc6c6`
branch: `research/idx-v4-target-support-census-v1`
head_commit: pending final commit
scope: Outcome-blind V4 target/Open/continuity support census using accepted canonical artifacts and the verified 2,184-row Historical Open overlay.
files_changed:
  - `scripts/run_v4_target_support_census.py`
  - `docs/checkpoints/2026-08-17_RANKING_V4_TARGET_SUPPORT_CENSUS.md`
  - `coordination/handoffs/IDX-RANKING-V4-TARGET-SUPPORT-CENSUS.md`
findings:
  - 981,940 active signal rows, 945 tickers, 1,260 official sessions.
  - Open(t+1) support 532,028 rows; H5 Close 961,366; H10 Close 954,379.
  - H5 target support 523,956; H10 target support 518,145; both 515,257.
  - Both-target date gate passes on 264/1,260 dates; both CA gate passes on 1,250/1,260 dates.
  - Consensus eligible identity list has 264 dates, SHA-256 `cdad58189694d71d1ca4ebce1c12da7dea4a663d3930262325a637ca53fca7dc`.
  - Longest official-calendar-consecutive eligible run is 196 sessions.
  - The exact manifest-pinned signal contract file is missing and was not substituted.
decisions_made:
  - Verdict is `BLOCKED_6X100_TARGET_SUPPORT`.
  - No labels, outcomes, returns, IC/performance, model fit, provider calls, CA acquisition, or V4 contract changes.
  - The canonical signal panel remains unchanged; the overlay is joined only in-memory for support accounting.
decisions_needed:
  - ChatGPT review of the blocked 6x100 feasibility result and the missing pinned signal-contract provenance.
blocking_risks:
  - 6x100 requires 600 eligible signal sessions but only 264 pass the frozen both-target/continuity date gates.
  - V4-2 does not fully specify the identity-list consecutiveness interpretation; no downstream choice was made here.
  - Accepted 1260 strict execution grade remains FAIL; this census does not promote it.
validation_run:
  - `python -m py_compile scripts/run_v4_target_support_census.py` — PASS
  - External manifest/input hash verification — PASS except the explicitly recorded missing pinned signal-contract path
  - Generated census manifest — outcome-blind, no labels/outcomes/model fit
recommended_next_action: Stop for ChatGPT review. Do not materialize V4 targets or fit H5/H10 models without a new authorized decision.
