# Cloudflare Direct Version-Byte Attestation V2 Final Rework

## Scope and implementation

Task: `PR122_V2_FINAL_DIRECT_VERSION_BYTE_ATTESTATION_REWORK`.

Repository: `samindriano/idx-trade`.

Branch: `codex/cloud-runtime-recovery-integration-v1`.

Implementation commit: `e03893f344c188ae82856bd833c7aa1614f246eb`.

The remediation adds a strict raw Cloudflare beta Version parser and the
`verifyVersionModulesAgainstCandidate()` primitive. It decodes every raw
`modules[].content_base64` value and compares the exact order-independent set
of module name, content type, byte length, and SHA-256, including the main
module. It rejects missing/extra/duplicate/unknown modules, malformed base64,
ambiguous envelopes, and Version-ID mismatch. The raw Version and raw
Deployment JSON byte hashes are retained in the checker and V2 receipt.

The candidate generator now inventories actual compiled Wrangler output rather
than treating `src/index.js` as deployable identity. The readiness profiles
remain separate:

- `DIRECT_VERSION_BYTE_ATTESTATION_PROVEN` proves exact local-to-Version bytes.
- `EXACT_CANDIDATE_VERSION_100_PERCENT_ACTIVE` independently proves the latest
  raw Deployment allocation is exactly one attested Version at 100%.
- `CLOUDFLARE_PRODUCTION_PREPARED_NONAUTOMATIC` is valid for an attested
  uploaded Version with no deployment traffic; it is not activation or capture
  success.

ETag, version number, tag/message, and receipt fields are informational or
indexing evidence only. The tested Wrangler upload path did not preserve
`workers/commit_sha`, so the annotation is not a required remote authority.
The direct module API depends on the beta `include=modules` capability and
blocks closed if that capability or its schema disappears.

## Deterministic identity

- Wrangler: `4.127.0`.
- Candidate Git SHA: `e03893f344c188ae82856bd833c7aa1614f246eb`.
- Bundle size: `94,520` bytes.
- Bundle SHA-256: `f83fce1e9cf7683b5760f58c53e6b151e126270266e1f2425c60d75f221fe018`.
- Production-active canonical manifest SHA-256:
  `5bd48c695b1ea3003e2826b0aa4cf989e421f465185ec4264432c111b0954a0b`.
- Production-preparation canonical manifest SHA-256:
  `57c876be411bacf1b850cb5e929eff45bac7e0fc6bc96740caaf9589f07f5068`.
- Each profile produced the same manifest hash on two fresh Wrangler dry-runs.

These are local synthetic/dry-run identity results. They are not evidence of
production deployment or active traffic.

## Validation

| Check | Result |
|---|---|
| Direct/readiness adversarial Node tests | **125/125 PASS** |
| Full Python suite | **PASS**, exit 0; three existing `FutureWarning`s |
| JavaScript syntax checks | **PASS** for changed modules/scripts and existing runtime modules |
| Wrangler staging-live dry-run | **PASS**, Wrangler 4.127.0 |
| Wrangler production-preparation dry-run | **PASS**, Wrangler 4.127.0 |
| Wrangler production dry-run | **PASS**, Wrangler 4.127.0 |
| Deterministic candidate generation | **PASS** for both profiles, two runs each |

The adversarial cases cover wrong bytes with a correct ETag, one-byte and
content-type changes, missing/extra/duplicate/reordered modules, malformed
base64, stale/wrong Version IDs, ambiguous raw envelopes, candidate 99%/0%,
split/stub/conflicting deployment evidence, receipt hash provenance, and the
preparation-versus-active CLI distinction. Raw API-shaped mutation fixtures
are synthetic and are labeled as such; the real capability-probe evidence is
retained in the V1 checkpoint.

## Boundaries and verdict

No production deployment, secret or Cron mutation, Windows change, GitHub
dispatch, provider call, R2/PaperState/counter write, outcome access, model
operation, merge, or manual workflow dispatch was performed. Natural canary and
canonical capture completion remain later production-certification gates.

Final verdict:

`PR122_V2_FINAL_DIRECT_BYTE_ATTESTATION_READY_FOR_ADVERSARIAL_REAUDIT`
