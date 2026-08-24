# Handoff: Stockbit Stream Schema-Retry Remediation V2

from: Codex
to: ChatGPT review / MAIN
task_id: IDX-STOCKBIT-STREAM-SCHEMA-RETRY-REMEDIATION-V2
source_repository: samindriano/idx-trade
source_commit: 2507e5f86b92b7fcaa21e7938ae91933200c0082
branch: fix/stockbit-stream-schema-diagnostics-v1
head_commit: pending final commit

## Scope

Bounded recovery for transient item-schema responses in the prospective
Stockbit Stream GitHub Actions archive. No model, outcome, counter, local
scheduler, or historical-data changes.

## Evidence

Cloud run `32720866941` identified `PADI` item 9 as
`ITEM_SCHEMA_ERROR / item[9].missing_content`. A later one-request live probe
of PADI returned the same item position with `content` present. This supports
a retryable transient source response.

## Change

Retry only `ITEM_SCHEMA_ERROR` once within the existing `MAX_STREAM_ATTEMPTS=2`
budget. Persist the first malformed bytes and SHA under an immutable
attempt-specific raw key. Normalize only a final fully valid response. A
persistent error remains `PARTIAL_FAILURE`; no silent drop or synthetic field
is allowed, and the all-final-records `DATA_READY` gate remains unchanged.

## Validation required

Focused capture/archive tests, `py_compile`, full pytest, `git diff --check`,
and one controlled workflow dispatch on the updated branch. Record the final
run summary and manifest SHA for review. Only MAIN may update
`coordination/TEAM_STATUS.md` or merge the PR.
