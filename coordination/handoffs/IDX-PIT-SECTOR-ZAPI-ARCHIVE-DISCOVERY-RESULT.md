# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-PIT-SECTOR-ZAPI-ARCHIVE-DISCOVERY
model_used: Codex MAIN with two Luna xhigh read-only investigators
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `f5689ee0f7e6faafaf2496786994590b6f27a108`
branch: `data/idx-pit-sector-history-v1`

## Scope

Prioritized the 2026 effective-date blocker, then investigated annual 2022 and
2023 through Zapi discovery/raw access and the official archive route. No
public 2022/2023 `NewsAnnouncement/GetAllAnnouncement` query was repeated.

## Findings

- 2026 ARGO/HRUM/PACK issuer histories were searched from 2026-06-24 through
  the latest available 2026-08-11 records. Window rows were 6/8/25 and
  classification-keyword matches were 0/0/0.
- Zapi raw issuer probes returned `ResultCount=0` for the classification/
  industry/IDX-IC searches.
- `Peng-00100/BEI.POP/06-2026` remains official and hash-pinned, but its PDF
  has no explicit effective date. `Peng-00099` remains non-canonical
  sector-index reconciliation evidence.
- Existing Zapi raw 2022/2023 captures both return `Items=[]`, `ItemCount=0`.
- No dedicated annual 2022/2023 ref, official attachment, bytes/SHA, or
  effective-date proof was recovered.
- Zapi documents raw `/primary/...` passthrough, but no accessible historical
  archive beyond the public retention boundary was established.
- The next highest-value route is authorized access to official TICMI/TICMIDATA
  archive/data services. No TICMI file was acquired or promoted in this pass.

## Decision

`BLOCKED`; inventory remains 5 `READY_FOR_ACQUISITION` / 3
`DISCOVERY_REQUIRED`.

No announcement ref or effective date was guessed. `config/pit_sector_sources_v1.json`
and tests were intentionally unchanged because no blocker met the promotion
contract.

## Files changed

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- `docs/checkpoints/2026-08-11_PIT_SECTOR_ZAPI_ARCHIVE_DISCOVERY_RESULT.md`
- `coordination/handoffs/IDX-PIT-SECTOR-ZAPI-ARCHIVE-DISCOVERY-RESULT.md`

External raw/Zapi captures remain outside Git at
`D:\Documents\Project\idx-pit-sector-official-raw-20260811`.

## Validation and next action

This pass changed documentation only; no test suite was rerun. Keep all three
blockers fail-closed. The next authorized step should obtain the exact
2022/2023 canonical documents through TICMI/TICMIDATA or another immutable
official archive, and a later official issuer disclosure linked to `Peng-00100`
with an explicit effective date.
