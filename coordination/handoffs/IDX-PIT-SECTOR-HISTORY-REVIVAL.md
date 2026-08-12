# Handoff

from: Codex
to: ChatGPT / PIT-sector revival reviewer
task_id: IDX-PIT-SECTOR-HISTORY-REVIVAL
model_used: Codex
reasoning_level: Luna xhigh / LIGHT bounded recovery
source_repository: samindriano/idx-trade
source_commit: 620480cd768ea784b82b71b14c1232d406b39143
branch: data/idx-pit-sector-history-revival-v1
head_commit: 620480cd768ea784b82b71b14c1232d406b39143
scope: One bounded local recovery attempt for 2022 and 2023 dedicated annual IDX-IC classification evidence and 2026 event-specific effective-date provenance.
files_changed:
  - docs/checkpoints/2026-08-13_PIT_SECTOR_HISTORY_REVIVAL_RECOVERY.md
  - coordination/handoffs/IDX-PIT-SECTOR-HISTORY-REVIVAL.md
  - coordination/TEAM_STATUS.md
findings:
  - 2022 exact dedicated official IDX classification ref/attachment remains unresolved after bounded static-path probes; all successful nearby refs were unrelated or index/watchlist evidence.
  - 2023 exact annual ref is corroborated as Peng-00158/BEI.POP/06-2023 by a secondary copy; the direct official IDX path returned an empty 22-byte ZIP and variants returned 404.
  - 2023 BMTR mirror states effective 03 July 2023 and links Klasifikasi Peng-00158.pdf, but it is not direct official IDX bytes and does not establish the event-wide date for all 14 issuers.
  - 2026 Peng-00100 remains canonical but has no effective date; Peng-00099 explicitly dates index applicability to 1 July 2026 and is not sufficient to infer the classification-event date under the frozen contract.
  - external artifact manifest SHA-256: e9de303c5351b24d2d2f67f577a2785b6cf0578deb7c208973914b7667a725cb.
decisions_made:
  - preserve fail-closed status; do not modify config or promote any guessed ref, URL, or effective date.
  - retain canonical inventory at 5 ready / 3 discovery-blocked.
  - preserve all candidate bytes and request metadata outside Git under D:\Documents\Project\idx-pit-sector-official-raw-20260811\revival-targeted-20260813.
decisions_needed:
  - independent reviewer to decide whether to authorize a future source-specific recovery attempt for direct official 2022/2023 bytes or event-specific 2026 effective-date evidence.
blocking_risks:
  - direct official IDX bytes are unavailable for the 2023 annual ref discovered through a mirror.
  - 2022 dedicated announcement ref remains unknown.
  - 2026 related index period is not equivalent to a classification-event effective date.
validation_run:
  - python -m pytest tests/test_pit_sector_history.py tests/test_pit_sector_discovery.py -q --disable-warnings: 23 passed.
  - python -m pytest -q --disable-warnings: 494 collected, exit 0.
recommended_next_action: Independent ChatGPT review. Keep all three source rows DISCOVERY_REQUIRED unless direct official evidence is recovered and hash-pinned.
