# Cloudflare Version-Level Deployed-Byte Attestation Capability Probe V1

## Scope and verdict

Task: `CLOUDFLARE_VERSION_LEVEL_DEPLOYED_BYTE_ATTESTATION_CAPABILITY_PROBE_V1`.

This was a bounded non-production capability probe after
`PR122_V2_ADVERSARIAL_REAUDIT_REWORK_REQUIRED` at PR #122 candidate
`b76fb4aacf43963affde909948782d9220ca5c6a`.

Final capability verdict:

`CLOUDFLARE_VERSION_ATTESTATION_CAPABILITY_PROVEN_READY_FOR_V2_FINAL_REWORK`

Attestation contract:

`DIRECT_VERSION_BYTE_ATTESTATION_AVAILABLE`

This proves the capability needed for a future V2 integration. It is not a
production activation or a claim that PR #122 is merge-ready. No production
Worker, version, deployment, secret, Cron Trigger, Windows controller, GitHub
workflow, provider, R2, PaperState/counter, model, or protected outcome was
accessed or changed.

## Capability

| Capability | Result |
|---|---|
| Worker Version upload without traffic deployment | **PROVEN**. Cloudflare documents `POST .../scripts/{script_name}/versions` as uploading a version without deploying it. Wrangler 4.127.0 returned a Version ID and explicitly instructed that a separate `wrangler versions deploy` command is required for traffic. The candidate Version IDs were absent from the deployment list. |
| Exact standard Version-detail readback | **PROVEN**. `wrangler versions view --json` returned the exact Version ID, sequential number, metadata, annotations, `resources.script`, `script_runtime`, and bindings. |
| Commit SHA annotation | **NOT PRESERVED in the tested Wrangler path**. `COMMIT_SHA` was set to the exact full audited SHA, but `wrangler versions upload` emitted only message/tag/triggered-by annotations. The upload API documentation accepts `workers/commit_sha`; this probe did not bypass Wrangler with a raw API upload. |
| Script etag | `6057eb0d7762ceab41bb9c800e416040d447b67e6cbdf7f5944c03ae4221183d` on all three probe versions. It is documented as hashed script content, but it did not equal the local compiled-module SHA-256. Treat it as opaque but empirically stable, not as a presumed algorithm. |
| Etag stability | **YES for this three-upload sample**. Byte-identical bootstrap, first upload, and second upload all returned the same etag despite different version annotations. This is evidence of stability, not a universal algorithm claim. |
| Arbitrary version byte readback | **PROVEN via the current documented beta API**: `GET /accounts/{account_id}/workers/workers/{worker_id}/versions/{version_id}?include=modules` accepted the Worker name and returned `modules` containing base64 code content for the exact Version ID. |
| Current-content endpoint | `GET /accounts/{account_id}/workers/scripts/{script_name}/content/v2` returned a script-level `multipart/form-data` response with an ETag and no version path parameter. A `version_id` query did not change the ETag and is not a documented selector; this endpoint is not the version-specific proof path. |
| Deployment traffic readback | **PROVEN**. `GET .../deployments` returned deployment ID, source, percentage strategy, Version IDs, percentages, timestamps, and annotations. The documented first deployment is the latest actively serving deployment. |

The official references are [Upload Version](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/versions/methods/create/), [beta Get Version with `include=modules`](https://developers.cloudflare.com/api/typescript/resources/workers/subresources/beta/subresources/workers/subresources/versions/methods/get/), [List Deployments](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/deployments/methods/list/), and [Wrangler version/deployment commands](https://developers.cloudflare.com/workers/wrangler/commands/workers/).

## Probe evidence

### Frozen candidate

- Git SHA: `b76fb4aacf43963affde909948782d9220ca5c6a`.
- Wrangler: `4.127.0`.
- Config basis: observe-only, `workers_dev=false`, no routes, no Cron, no
  secret file, `DISPATCH_MODE=observe_only`.
- Main module: `index.js`.
- Local compiled main module: `94,520` bytes.
- Local compiled main-module SHA-256:
  `f83fce1e9cf7683b5760f58c53e6b151e126270266e1f2425c60d75f221fe018`.
- Wrangler dry-run also emitted a source map and README output, but the
  uploaded Version module set contained the single runtime module `index.js`.

The configured staging Worker did not exist (`10007`). Wrangler also refuses
`versions upload` for a nonexistent Worker. A dedicated Worker named
`idx-trade-attestation-b76-20260908` was therefore created with a temporary
probe config that had no route, no workers.dev exposure, no Cron, no secrets,
and only the existing declarative R2/DO bindings. Wrangler reported
`No targets deployed` for the bootstrap operation. The independent deployment
list contained only the bootstrap Version 1 at 100%; no candidate Version was
assigned to that deployment.

### Version detail and upload results

Bootstrap Version 1:

- Version ID: `e170d069-94ce-4022-890c-ef14d82275a8`.
- Standard detail number: `1`.
- Source: `wrangler`.
- Handler: `scheduled`.
- Named handler: `SchedulerCoordinator` / `class`.
- Runtime: compatibility date `2026-08-27`, usage model `standard`.
- Etag: `6057eb0d7762ceab41bb9c800e416040d447b67e6cbdf7f5944c03ae4221183d`.
- Binding types read back: `r2_bucket`, `durable_object_namespace`, and
  `plain_text`; no secret binding was included in the probe config.

First non-deployed `wrangler versions upload`:

- Version ID: `ba3f4565-ecd4-4b84-905d-46d64f82a8a9`.
- Standard detail number: `2`.
- Source: `wrangler`; `has_preview=false`.
- Tag: `idx-trade-attestation-probe-b76-1`.
- Message included the full audited SHA.
- Server annotation: `workers/triggered_by=version_upload`.
- Etag: `6057eb0d7762ceab41bb9c800e416040d447b67e6cbdf7f5944c03ae4221183d`.
- Handlers, named handlers, runtime, exports, and binding identity matched the
  bootstrap.

Second byte-identical non-deployed upload:

- Version ID: `b888ed2d-f28f-49e3-afee-07c5148b7aff`.
- Standard detail number: `3`.
- Source: `wrangler`; `has_preview=false`.
- Tag: `idx-trade-attestation-probe-b76-2`.
- Etag: `6057eb0d7762ceab41bb9c800e416040d447b67e6cbdf7f5944c03ae4221183d`.
- Handlers, named handlers, runtime, exports, and binding identity matched
  Version 2.

The upload command has no `--json` option. Its durable machine-checkable
follow-up was the raw `versions view --json` readback, which confirmed
`readback.id == uploaded Version ID` for both uploads. No `workers/commit_sha`
field appeared in either raw response.

### Direct version-specific module readback

The beta endpoint was called independently for both non-deployed Version IDs
with `include=modules`:

| Version ID | HTTP | Returned module | Content type | Decoded bytes | Decoded SHA-256 | Exact local match |
|---|---:|---|---|---:|---|---|
| `ba3f4565-ecd4-4b84-905d-46d64f82a8a9` | 200 | `index.js` | `application/javascript+module` | 94,520 | `f83fce1e9cf7683b5760f58c53e6b151e126270266e1f2425c60d75f221fe018` | `true` |
| `b888ed2d-f28f-49e3-afee-07c5148b7aff` | 200 | `index.js` | `application/javascript+module` | 94,520 | `f83fce1e9cf7683b5760f58c53e6b151e126270266e1f2425c60d75f221fe018` | `true` |

The response also returned the exact requested Version ID and sequential
number. `urls` was empty for both versions, consistent with the unrouted probe
configuration.

### Current-content endpoint characterization

The script-level `content/v2` endpoint returned HTTP 200 and
`multipart/form-data`; the raw transport body was 94,769 bytes. Its raw body
hash changed between calls because the multipart boundary changed, while the
HTTP ETag remained the same `6057...183d`. Supplying an undocumented
`version_id` query returned the same ETag and body size, so it was not treated
as version selection. The endpoint is therefore supplementary current-script
readback only; it is not the authoritative arbitrary-Version path.

### Upload form and etag characterization

Two Wrangler `versions upload --dry-run --no-bundle --outfile` runs produced
equal-size (95,926-byte) multipart forms with different SHA-256 hashes because
the multipart boundary is generated per request. No canonical multipart hash
construction is documented or inferred. The etag did not equal the local main
module SHA-256 or either raw multipart transport hash. The probe records:

`CLOUDFLARE_ETAG_OPAQUE_BUT_VERSION_STABLE`

## Correct V2 contract delta

The existing V2 receipt/manifest must not promote a self-authored hash or
message into remote byte authority. The minimal design delta is:

1. Preserve the exact local candidate identity and compiled module inventory,
   including Git SHA, main-module bytes/hash, module names/types, Wrangler
   version, config hash, and raw upload form/evidence hashes.
2. Preserve the raw upload response/CLI-derived Version ID, then independently
   fetch standard Version detail and require the returned `id` to equal that
   Version ID.
3. Fetch the beta Version detail with `include=modules` for that exact Version
   ID. Decode every returned module by its authoritative `name` and
   `content_base64`, compare the complete module set and byte hashes against
   the frozen local upload artifact, and hash the raw response separately.
4. Treat the Cloudflare etag as a supplementary stable remote identifier. Do
   not equate it with SHA-256 unless Cloudflare documents a reproducible
   construction and the implementation proves it.
5. Read the raw Deployments API after any separately authorized deployment and
   require the exact Version ID to be the sole 100% allocation in the selected
   active deployment. Retain deployment ID, raw response hash, timestamp, and
   allocation list.
6. Treat absent `workers/commit_sha` as a provenance gap in the Wrangler path,
   not as permission to trust the message/tag. The independently downloaded
   module bytes plus the frozen Git/build record are the byte authority; a
   future raw-API upload may optionally add and verify the commit annotation.
7. Keep `/scripts/{script_name}/content/v2` out of the Version-ID proof unless
   the contract explicitly labels it current-script readback. Do not use an
   undocumented query parameter as a version selector.

The integration should remain fail-closed if the beta endpoint is unavailable,
`modules` is missing, a module name/type/content differs, Version IDs disagree,
or the deployment allocation is absent/ambiguous. No large patch was made in
this probe because the repository’s current receipt schema needs an explicit
decision on beta API support and raw-evidence storage.

## Boundaries and repository state

- No optional active-content deployment was performed: direct version-specific
  byte retrieval was available, so Phase E was not authorized or needed.
- No production Worker or deployment was queried for mutation or changed.
- No secrets or tokens were emitted or stored in the repository.
- The temporary probe config was removed after use.
- Repository code was not changed. Only this checkpoint and the relevant
  coordination status row were updated; the unrelated user authorization-packet
  edit remains preserved and unstaged.

Final task verdict:

`CLOUDFLARE_VERSION_ATTESTATION_CAPABILITY_PROVEN_READY_FOR_V2_FINAL_REWORK`
