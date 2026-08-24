# Stockbit Stream Schema-Diagnostic Remediation V1

## Scope

This checkpoint covers only the prospective GitHub Actions capture path:

`GitHub Actions -> Zapi Stockbit Stream -> immutable R2 archive`

It does not change model inputs, counters, outcomes, local IDX-Trade
automations, or historical backfill behavior.

## Triggering evidence

GitHub Actions run `32716493115` (`main`, 2026-08-24) completed 200 planned
stream calls and returned:

- 199 `OK` responses;
- 1 `ITEM_SCHEMA_ERROR`;
- status `PARTIAL_FAILURE`;
- exit code `2`;
- `counter_mutated=false`;
- `model_accessed=false`;
- `outcome_accessed=false`.

The public GitHub log exposed only the aggregate classification. No workflow
artifact was attached, so the exact offending ticker cannot be recovered from
GitHub alone. The parser identifies the possible item-level causes as a
non-object item, missing/blank `id`, non-string `createdAt`, or missing
`content`.

## Diagnosis

The run is not evidence of a successful capture: the all-final-records gate
correctly kept it `PARTIAL_FAILURE`. The other 199 responses were normalized,
and no model, outcome, or counter path was accessed. A previous pre-open run
(`32684333136`) completed `DATA_READY` with 200/200 responses; a separate
midday run (`32694723874`) timed out and also failed closed.

The exact malformed item is not recoverable from public Actions output. The
existing strict parser contract is therefore retained; this remediation does
not guess whether the upstream item was transient or permanently malformed.

## Remediation

The parser now exposes a backward-compatible detailed API that attaches a
non-sensitive `validation_detail` such as `item[0].missing_content` to the
per-ticker request record. This makes the next incident actionable without
persisting post content or author identity.

The cloud runner also emits a `validation_diagnostics` list in its final
stdout summary containing only ticker, classification, and validation reason.
This closes the observability gap without exposing post content, author
identity, response bytes, or credentials.

## Controlled cloud verification

Run `32720866941` on commit `b9319645` reproduced the incident and exposed the
exact safe diagnostic:

- ticker: `PADI`;
- classification: `ITEM_SCHEMA_ERROR`;
- reason: `item[9].missing_content`;
- planned/completed calls: `200/200`;
- valid responses: `199`;
- normalized rows: `5903`;
- final status: `PARTIAL_FAILURE`;
- manifest SHA-256: `ef8487f875c44575362aba3ca4f3b6cead9c3f9eff82681f4ea1d2ff0028a8a2`.

The same bounded capture was not retried by the runner and no second provider
attempt was introduced for the malformed response. The result confirms the
remaining issue is an upstream PADI item-schema defect, not a scheduler,
credential, quota, R2, model, outcome, or counter failure. PADI must not be
silently dropped or synthesized; changing that policy requires a separate
contract review.

The capture runner continues to retry only the already accepted transport
classes: request exceptions and the allowlisted transient HTTP 5xx statuses.
It does **not** retry malformed/empty/schema-invalid 200 responses, does not
relax the schema, and does not silently accept partial records. A persistent
schema failure remains `PARTIAL_FAILURE` and `DATA_READY` still requires every
planned ticker to finish `OK`.

## Validation

Focused capture/archive tests cover:

- field-level diagnostics for malformed item schema;
- persistent malformed response remains fail-closed after one provider call;
- existing HTTP 5xx and request-exception recovery;
- immutable/resume behavior and the legacy three-value parser API.

No credential value was printed or written to the repository. No provider,
model, outcome, counter, local scheduler, or R2 mutation was performed by this
remediation.

## Remaining operational check

After review and integration, run one controlled `workflow_dispatch` capture
on the integrated main path. A fully valid run should be `DATA_READY`; a
persistent `ITEM_SCHEMA_ERROR` should remain visible as a fail-closed incident
with the offending field detail.

This diagnostics-only phase is superseded for implementation review by the
bounded schema-retry follow-up in
`2026-08-24_STOCKBIT_STREAM_SCHEMA_RETRY_REMEDIATION_V2.md`. The original
incident evidence and strict fail-closed result remain unchanged.
