# Handoff

from: Codex/Financial-PIT-Offline-Reclassification
to: ChatGPT independent review
task_id: IDX-FINANCIAL-PIT-OFFLINE-SCOPE-RECLASSIFICATION
model_used: gpt-5.6-luna xhigh with one read-only Orchestra audit worker
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `e4537c16c5011d8cafc55bc72e8f04017b874baf`
branch: `data/financial-pit-offline-scope-reclassification-v1`
head_commit: recorded by the final pushed branch HEAD

## Scope

Apply the accepted statement-scope resolver offline to the accepted
`D:\Documents\Project\idx-trade-financial-pit-adapter-census-20260813-v1`
captures. Do not call providers or redownload files. Do not derive financial
facts/features, model, or access protected outcomes.

## Findings

- Exact report-announcement byte joins: **6,108 / 7,370**.
- `CONSOLIDATED`: **4,410**.
- `SEPARATE`: **1,555**.
- `UNRESOLVED`: **143**.
- Mixed/conflicting authoritative scope: **0**.
- Recognized XLSX / XBRL / PDF / unsupported: **5,966 / 2 / 0 / 140**.
- Explicit-scope PIT-ready: **5,965**.
- PIT-ready: **97.658808% of exact joins**, **80.936228% of all expected issuer-periods**.
- Preserved outside exact-join set: **74 ambiguous attachments, 2 hash
  conflicts, 28 HTTP failures, 1,158 publication/attachment linkage gaps**.

Every output row contains ticker, year, period, UTC publication timestamp,
source attachment SHA, representation, scope, exact resolver evidence
location/kind, prior-chain gate status, and PIT-ready status.

## Artifacts

Canonical external output root:

`D:\Documents\Project\idx-trade-financial-pit-scope-reclassification-20260813-v2`

- `scope_reclassification_rows.jsonl`: 6,108 rows;
  SHA-256 `656807e74f84aa7bde74f30ffe7f2b11fed921e343c485dcc81cdcc617ac3cd9`.
- `scope_reclassification_summary.json`:
  SHA-256 `d1cb01448361b2f95236eba49440d78dbd9cc89dda1280b2fea0a379ccc6a974`.
- `MANIFEST.json`:
  SHA-256 `a38fdb52225da8e1c5306e1d7bb658e34e069e6920e074c59ad1f607ff01249f`.

Input hashes:

- `coverage_rows.jsonl`: `dbb307fecac4eedcdf4a2d692a148c225c48fdf23fbd55c7b499cb8f275c377b`.
- `MANIFEST__rerun_v6.json`: `e675a258e5281eb01032d6d4b73c7a94f41871b06550e2253df3b7ac7cd9946e`.

## Decisions and blockers

- Decision: `FINANCIAL_PIT_SCOPE_RECLASSIFIED_PIT_READY_COVERAGE_INCOMPLETE`.
- No financial fact table or model input was created.
- The 140 unsupported files remain unresolved even where their filenames end
  in `.xlsx`; captured bytes are not valid XLSX packages.
- The 143 explicit-join unresolved rows remain fail-closed.
- Prior publication/linkage failures, ambiguous attachments, hash conflicts,
  and provider failures were not repaired.

## Validation

- Focused tests were run before the final percentage/mixed-count hardening;
  full pytest and final focused tests are required after the final patch.
- No network/provider calls were made during this lane.

## Recommended next action

ChatGPT review of the offline classification and coverage percentages. Keep
the lane in `REVIEW`; do not consume PIT-ready rows for facts/features until
the remaining blockers and representation policy are separately accepted.
