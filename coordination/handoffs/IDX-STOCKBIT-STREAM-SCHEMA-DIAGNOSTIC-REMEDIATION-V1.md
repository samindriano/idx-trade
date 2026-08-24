# Handoff: Stockbit Stream Schema-Diagnostic Remediation V1

from: Codex
to: ChatGPT review / MAIN
task_id: IDX-STOCKBIT-STREAM-SCHEMA-DIAGNOSTIC-REMEDIATION-V1
model_used: gpt-5.6-luna
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: 00c47c9d2800f526fd6c32be955c5b194e3dbf75
branch: fix/stockbit-stream-schema-diagnostics-v1
head_commit: pending final commit

## Scope

Add actionable item-level schema diagnostics to the prospective GitHub
Actions Stockbit Stream capture path. Preserve the existing strict acceptance
and retry contract. Do not change models, counters, outcomes, local
schedulers, historical data, provider fallback, or R2 policy.

## Findings

GitHub Actions run `32716493115` processed 200 calls and failed closed with
199 `OK` and one `ITEM_SCHEMA_ERROR`. The aggregate log did not identify the
ticker or item field, and no GitHub artifact was attached. The possible parser
reasons are item object shape, `id`, string `createdAt`, or `content`.

## Changes

- Added a detailed parser API while preserving the existing three-value parser
  API.
- Added non-sensitive `validation_detail` to the final per-ticker request
  record.
- Added a safe `validation_diagnostics` stdout summary for CI logs containing
  only ticker, classification, and validation reason.
- Kept transport/request retries and allowlisted transient HTTP 5xx retries
  unchanged.
- Explicitly kept malformed, empty, duplicate, and schema-invalid responses
  fail-closed with no schema retry or silent acceptance.
- Added regression coverage for diagnostics and persistent schema failure.

## Controlled cloud result

Run `32720866941` on `b9319645` reproduced the single malformed response:
`PADI`, `ITEM_SCHEMA_ERROR`, `item[9].missing_content`. The run completed
`200/200` calls with `199` valid responses and `5903` normalized rows, then
correctly remained `PARTIAL_FAILURE`. Manifest SHA-256:
`ef8487f875c44575362aba3ca4f3b6cead9c3f9eff82681f4ea1d2ff0028a8a2`.

This is an upstream item-schema defect. PADI is intentionally not silently
dropped or synthesized; a policy change would need a separate contract review.

## Validation

Run the focused capture/archive tests with an isolated pytest temp root,
`py_compile`, `git diff --check`, and the full suite where the repository
baseline permits. Record exact results in the final review.

## Decisions needed

1. Review the diagnosis and diagnostics-only remediation.
2. After integration, run one controlled `workflow_dispatch` capture and
   verify `DATA_READY` or the now-actionable fail-closed diagnostic.

## Boundaries

No protected outcome access, model/counter access, local scheduler changes,
historical backfill, credential persistence, or provider call by this branch.
Only MAIN may update `coordination/TEAM_STATUS.md`.
