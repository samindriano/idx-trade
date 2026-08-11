# Handoff

from: Codex MAIN
to: ChatGPT reviewer
task_id: IDX-PIT-SECTOR-TICMI-AVAILABILITY
model_used: Codex MAIN
reasoning_level: xhigh
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `39c60475bfa3fed3adbff5d87e63c4ac15f1014f`
branch: `data/idx-pit-sector-history-v1`

## Scope

Bounded public-only TICMI/TICMIDATA availability investigation for the missing
2022 and 2023 annual IDX-IC canonical announcements. No purchase, login,
credential use, parser/materialization, census, model, outcome, OPEN, Path Risk,
execution/PnL, or main work.

## Findings

- Public IDX terms direct company history older than three years to TICMI.
- TICMIDATA sitemap exposes application routes including pricing, pay-per-use,
  custom data, document area, and customer area, but the public routes render a
  Flutter shell without historical announcement records or attachment metadata.
- The public TICMI data-service terms describe general data and a special/custom
  service for data not available in the general service, including custom
  `.xlsx`, `.txt`, and `.pdf` output.
- The legacy public TICMI paths `/datapasarmodal` and `/datapasarmodal-lainnya`
  currently return 404; this does not prove archive absence.
- No public title, announcement ref, attachment path, source bytes/SHA, or
  effective-date evidence was found for the 2022 or 2023 annual targets.
- A narrow TICMI custom-data request is the highest-value next step. It should
  request the two dedicated Exchange announcements and the provenance fields
  required by the PIT contract, rather than buying a broad market package.
- Exact price and single-file fulfillment are not visible publicly and require a
  TICMI response. No purchase was made.

## 2026 boundary

The existing bounded 2026 search remains exhausted for now: canonical
`Peng-00100` exists without an explicit effective date; no linked ARGO/HRUM/PACK
evidence was found through 2026-08-11; `Peng-00099` remains reconciliation-only.

## Decision

`TICMI_PUBLIC_METADATA_INSUFFICIENT_FOR_PROMOTION`; inventory remains 5 ready / 3
blocked. No config entry changed and no source was promoted.

## Fail-closed policy recorded

If approved official archive escalation permanently fails, retain the item as
`DISCOVERY_REQUIRED` or explicitly review/promote a
`PIT_SECTOR_SOURCE_UNRESOLVED_PERMANENT` status. Never infer dates or sectors;
keep affected PIT assignments unknown, fail downstream sector data gates, and
do not materialize/score V3-D sector features from incomplete history.

## Files changed

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_LEDGER.md`
- `docs/checkpoints/2026-08-11_PIT_SECTOR_TICMI_AVAILABILITY_RESULT.md`
- `coordination/handoffs/IDX-PIT-SECTOR-TICMI-AVAILABILITY-RESULT.md`

## Validation

Documentation-only change; no pytest run because no executable code or inventory
contract changed. Working tree must be clean after commit/push.

## Recommended next action

Ask TICMI Data Services whether it can fulfill an individually scoped custom
request for the dedicated 2022 and 2023 annual IDX-IC Exchange announcements,
with original file/immutable archive identity, ref, timestamp, explicit
effective-date wording, and availability date. Do not start parser or sector
materialization until the PIT source contract is satisfied.
