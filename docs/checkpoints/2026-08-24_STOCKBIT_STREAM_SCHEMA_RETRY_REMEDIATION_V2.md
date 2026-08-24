# Stockbit Stream Schema-Retry Remediation V2

## Decision basis

The diagnostics-only run `32720866941` identified `PADI` item 9 as
`missing_content`. A bounded direct probe of the same Zapi stream endpoint
later returned HTTP 200 with a valid PADI item 9 containing `content`.
This establishes a transient upstream item-schema response, not a permanent
PADI identity or universe defect.

## Frozen bounded policy

For a response classified `ITEM_SCHEMA_ERROR` only:

1. retain and SHA-pin the malformed first response under an immutable
   attempt-specific raw key;
2. make at most one additional stream request within the existing
   two-attempt/provider-call budget;
3. accept and normalize only when the final response passes the existing full
   schema validator;
4. if the second response is still invalid, retain the final raw response and
   return `PARTIAL_FAILURE`.

No item is dropped, synthesized, or treated as valid. `DATA_READY` still
requires every planned ticker's final response to be `OK`. Existing request
exception and allowlisted HTTP 5xx retry behavior is unchanged; no other
validation class is retried.

## Provenance and safety

The manifest preserves both attempt classifications, validation detail, raw
SHA-256 values, and the final normalized artifact only for a valid response.
The stdout summary exposes only ticker, classification, and safe validation
reason. Post content, author identity, API keys, models, outcomes, and
counters remain outside the diagnostic surface.

## Required validation

Focused tests must prove schema-error recovery and persistent schema failure;
full pytest and `git diff --check` must pass. One controlled cloud run on the
updated branch must verify that the PADI-style transient case can become
`DATA_READY` when the bounded second response is valid, while persistent
malformation remains `PARTIAL_FAILURE`.

## Controlled cloud result

Run `32722871440` on commit `d6b48fd6` completed successfully:

- planned/completed calls: `200/200`;
- response classifications: `OK=200`;
- normalized rows: `5931`;
- final status: `DATA_READY`;
- `validation_diagnostics=[]`;
- manifest SHA-256:
  `3e160e6024c1fddb40109184205baf54ebc7c0d89f9ca1ab5fadaf7ec7343e1b`;
- `model_accessed=false`;
- `outcome_accessed=false`;
- `counter_mutated=false`.

This verifies that a transient PADI-style schema response can recover within
the bounded second attempt while the strict final validator and all-ticker
`DATA_READY` gate remain active.
