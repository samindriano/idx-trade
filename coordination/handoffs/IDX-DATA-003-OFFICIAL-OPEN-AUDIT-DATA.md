# Handoff
from: Codex parent control plane
to: ChatGPT / MAIN reviewer
task_id: IDX-DATA-003-OFFICIAL-OPEN-AUDIT
model_used: Codex
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: ffca7c51312ef96ce786913541c36a55edd4588c
branch: data/idx-data-002c
head_commit: be832d7b3fbfd1f4b47939de601b699acd1fc20f
scope: bounded official IDXData3 Stock_First_Trx availability and schema audit
files_changed:
  - docs/PROJECT_CONTEXT_MASTER.md
  - docs/PROJECT_LEDGER.md
  - docs/checkpoints/2026-08-09_IDXDATA3_OFFICIAL_OPEN_AUDIT_STOP.md
  - coordination/handoffs/IDX-DATA-003-OFFICIAL-OPEN-AUDIT-DATA.md
findings:
  - exact remaining requirement regenerated as 390 rows over 233 unique dates
  - FREN 196 rows, MASA 22 rows, MFIN 172 rows
  - all 233 target SO files ended FILE_NOT_FOUND after a controlled retry
  - official directory listing exposed only 133 SO files from 2020-02-03 through 2020-08-19
  - one available 2020 archive was legacy DBF with STK_FIRST only and was outside target dates
  - zero target opening rows were verified; all 390 rows remain SO_FILE_MISSING
decisions_made:
  - stop under the zero/negligible official-source-coverage condition
  - do not implement a production SO parser/provider
  - do not rerun the 504/126 ladder or start 252/1260
  - do not weaken the raw-price gate or synthesize/forward-fill Open
  - preserve certified 43/126 artifacts unchanged
decisions_needed:
  - identify another normally accessible authoritative opening-price source, or explicitly accept a shorter defensible historical horizon
blocking_risks:
  - FREN/MASA/MFIN remain without defensible opening evidence for 390 ACTIVE-session rows
  - 504 cannot be certified from this audit
validation_run:
  - exact target date regeneration and 233 direct-file attempts
  - controlled retry of 221 initial HTTP 503 responses; all returned HTTP 404
  - one available archive schema inspection
  - no new pytest run; prior checkpoint recorded 149 passed with three non-blocking warnings
recommended_next_action: review the checkpoint and choose a new authoritative source or bounded-horizon decision before any 504 rerun
