# Stockbit Stream R2 Retention V1

Status: `ACTIVE_AND_VERIFIED`

## Scope

The Stockbit stream capture path remains unchanged. This checkpoint adds a
bounded, manual-only Cloudflare R2 lifecycle control plane so storage growth is
limited without touching capture scheduling, source data, model artifacts, or
outcomes.

The pinned policy is:

- `stockbit-stream-v2/raw/` expires after 180 days;
- `stockbit-stream-v2/normalized/` expires after 180 days;
- `stockbit-stream-v2/manifests/` is preserved;
- `stockbit-stream-v2/universe_inputs/` is preserved.

The 180-day window is intentionally longer than the expected 100-session
forward audit horizon while keeping the observed archive comfortably below the
10 GB-month free storage allowance at the current capture volume. It is a
storage policy, not a scientific eligibility rule; expired payloads must never
be treated as evidence that a capture did not occur.

The user-provided R2 dashboard snapshot on 2026-08-23 showed approximately
4.1k objects, 93.69 MB in the Stockbit bucket, and $0 billable usage for the
current period. This is a baseline observation, not a substitute for a
provider-side lifecycle verification.

## Safety and activation

No R2 object was listed, read, deleted, or overwritten by this change. The
capture workflow does not depend on the retention workflow.

Cloudflare's S3-compatible API does not support Object Lifecycle. The utility
therefore uses the Cloudflare account REST lifecycle endpoint, with a separate
`CLOUDFLARE_API_TOKEN` supplied only at manual activation time. The GitHub
workflow is `workflow_dispatch` only. Before its PUT, it performs a GET
preflight, preserves all existing lifecycle rules verbatim, and appends only
the two owned Stockbit rules. An existing rule that collides with an owned rule
ID causes a fail-closed stop. It then performs a GET verification of the full
merged configuration. It also fails closed if the token, account, or bucket is
missing, or if the remote rules differ from the applied payload.

Activation was completed through the manual GitHub Actions workflow after the
narrowly scoped `CLOUDFLARE_API_TOKEN` secret was added. The R2 S3 access key
was not used for lifecycle configuration. Secret values were not printed or
stored in the repository.

The successful activation run was:

- workflow run: `32624790465`
- result: `APPLIED_AND_VERIFIED`
- applied merged lifecycle payload SHA-256:
  `bff7dfc38185501163986cc4261d5d237d529133293f07cf7ee2ddc3e69ce1c6`
- existing remote rule preserved verbatim: `Default Multipart Abort Rule`

The two owned rules now apply the 180-day expiry to the raw and normalized
prefixes. The workflow only changed lifecycle configuration; it did not list,
read, delete, or overwrite any R2 object. Future expiry is provider-managed;
no manual cleanup or capture rerun was performed.

## Verification

The local dry-run emits a deterministic lifecycle payload and SHA-256. Tests
prove that only raw/normalized prefixes can expire, provenance prefixes cannot
be selected, dry-run performs no network call, and missing activation
credentials fail closed. The activation workflow additionally verified the
full merged remote lifecycle configuration after the PUT.

## Boundaries

This lane does not change Stockbit capture, Zapi/IDX acquisition, R2 object
contents, model/runtime artifacts, counters, labels, outcomes, or forward
eligibility.
