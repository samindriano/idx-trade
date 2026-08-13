# Handoff

from: Codex/Clean-V2-Open-Alpha-Prereg  
to: ChatGPT/Open-Alpha-Research  
task_id: IDX-V2-OPEN-ALPHA-PREREG  
model_used: Luna xhigh  
reasoning_level: xhigh  
source_repository: samindriano/idx-trade  
source_commit: `504c51bad25517bf496ee14856be704935d0f5d4`  
branch: `research/idx-v2-open-alpha-prereg-v1`  
scope: Freeze CONTROL + V2.1 exact same-day Open geometry + V2.2 previous-active-range Open displacement; build one outcome-blind common-support cache and audit only.  
head_commit: final pushed branch HEAD is reported with this handoff  

## Files changed

- `src/idx_trade/open_alpha_prereg.py`
- `tests/test_open_alpha_prereg.py`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_PREREGISTRATION.md`
- `docs/checkpoints/2026-08-13_CLEAN_V2_OPEN_ALPHA_OUTCOME_BLIND_AUDIT_RUNTIME.md`
- `coordination/handoffs/IDX-V2-OPEN-ALPHA-PREREG.md`

## Findings

- clean V2 source: 292,631 rows / 737 tickers;
- one exact common support for all three eventual models: **277,244 rows / 729 tickers**;
- common-support key SHA: `e058e5ce4ce650eeab5acd57a7d697c155548e40bbbb8ffe0eab120987d857df`;
- exclusions: 12,589 current Open unavailable, 1,876 current flat range, 922 previous ACTIVE flat range;
- zero duplicate keys, listing invalid rows, current non-ACTIVE rows, calendar unresolved rows, and regular suspension conflicts;
- previous ACTIVE gap min/median/max: 1 / 1 / 39 sessions;
- Open-related maximum absolute correlation: 0.582885;
- future-row causal invariance: true;
- no target/outcome loaded, model fit/score, provider call, protected outcome access, or panel write.

## Decisions made

- V2 remains the clean parent.
- V3-B remains closed/failed; old O2 remains orphaned diagnostic only.
- Flat current/previous ranges fail closed; no synthetic fill or feature rescue.
- The candidate population is measured from corrected lineage and is not copied from the prior 278,168-row artifact.

## Validation

- focused tests: 5 passed;
- full pytest: 44 passed, 1 pre-existing `test_storage.py` failure unrelated to this lane.
- Runtime artifacts and hashes are in:
  `D:\Documents\Project\idx-trade-data-gate-20260808v\open_alpha_prereg_v1_20260813_001_retry2`.

## Blocking risks / review requests

- ChatGPT should independently verify the exact common-support key and the
  fail-closed interpretation of the 1,876 flat-range source rows.
- Do not open historical outcomes or fit/score models until this checkpoint is
  independently reviewed and the existing storage-test baseline failure is
  either accepted as unrelated or separately owned.

recommended_next_action: independent ChatGPT review; only after acceptance may a separately authorized lane run the frozen historical comparison on the exact cached population.
