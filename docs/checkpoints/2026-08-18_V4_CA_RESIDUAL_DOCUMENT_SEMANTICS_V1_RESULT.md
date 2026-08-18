# V4 CA Residual Document Semantics V1 — Result

Status: `REVIEW`

## Scope and validation

- branch: `data/idx-v4-ca-residual-document-semantics-v1`
- execution HEAD: `3e99d4a596e3878a6df24d920ed54badd6c3d310`
- scientific/preflight anchor: `6cced713d13e9933f1c9243695f8e59464c0b407`
- scientific parent: `data/idx-v4-ca-voluntary-conversion-forensic-replay-v1@c2246e5e82dc642950017e38e57cd97700e15199`
- focused pytest: `23 passed in 0.62s`
- `py_compile`: PASS
- `git diff --check`: PASS
- provider calls: `0`

The exact Stage-2 attestation passed:

- status: `V4_CA_STAGE2_RAW_CORPUS_ATTESTED`
- candidate documents: `100`
- successful documents: `98`
- verified raw file paths: `97`
- provider-failed documents: `2`
- source substitution: `false`
- Stage-2 manifest SHA: `5073adb3178a90e71ea9105ddb6ff737896e86a709d1998eefbdb14ca12b6f8c`
- parse audit SHA: `d7ded2bf29ad8355ff7ce22af89004a4bbe7e7fd0bb01524f582be2ad1e4e796`
- request records SHA: `96a7a2d6013f6a6f86bc7548c9cda90514eb03a50d9b56039ec15c07969f6155`

## Stage A — residual document semantics

Exactly one hardened Stage-A run completed offline with status:

`V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_COMPLETE`

| Measure | Count |
|---|---:|
| Successful Stage-2 raw documents verified | 97 |
| Event-document candidate rows | 241 |
| Residual events | 61 |
| Residual Voluntary Conversion events | 29 |
| Exact non-blocking events | 22 |
| Exact transition events | 1 |
| Conflict events | 0 |
| Unresolved events | 38 |
| Linkage `EXACT` | 1 |
| Linkage `EXACT_NON_BLOCKING` | 22 |
| Linkage `UNRESOLVED` | 38 |

Stage-A output root:
`D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`

Stage-A hashes:

- `MANIFEST.json`: `6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`
- `summary.json`: `e8141848cf6aa84a76c2e826e823e2616e768b8843042ddd7a096255489eeaeb`
- `residual_document_audit.csv`: `762f283b349256960d1023d91aff2ac162c83323a30b1e40e14cd48838c5f317`
- `residual_event_document_evidence.csv`: `6be49b4fc8a930c9bc61fde64a0652a7cb6233459f5a2e140cb4b4ad0f56592e`

## Stage B — exact command and fail-closed blocker

Because Stage A was valid, the exact Stage-B command from the handoff was
attempted once. It stopped before producing a Stage-B manifest with:

`REQUIRED_INPUT_MISSING:prior_event_evidence:D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\corporate_action_event_evidence.csv`

The specified continuity root contains `event_family_evidence.csv`, not the
handoff-required `corporate_action_event_evidence.csv`. No alternate filename
was substituted and the command was not retried.

Therefore:

- Stage-B continuity verdict: `NOT_AVAILABLE_STAGE_B_INPUT_MISSING`
- `corporate_action_continuity_certified`: not evaluated
- final relevant/exact/schedule-required counts: not produced
- H5/H10/consensus passing dates and minimum rates: not produced
- Stage-A overlay in continuity: not produced
- Stage-B output manifest/hashes: not produced

The Stage-B output root was not deleted or overwritten. No source/config patch,
provider call, schedule acquisition, target/rank materialization, model,
performance, or protected/fresh-forward outcome access occurred.

## Promotion and stop condition

Only the small Stage-A result bundle was promoted. Raw Stage-2 files and any
full continuity ledger remain external. This lane stops for ChatGPT review;
resolving the filename/input mismatch requires a separate authorized
continuation.
