# E2E Cloud PREOPEN Official Open Admission Auditability V1

Status: REVIEW pending independent review. No merge, provider/R2 call,
scheduler activation, model/outcome access, or live execution was performed.

Branch: `integration/e2e-cloud-first-orchestration-v1`.
Parent before this remediation: `d2e1a6313775f5077ec16d2fbe3283b1340b125f`.

## Root cause

The existing `materialize_official_open_from_cloud()` and
`wait_for_official_open_from_cloud()` path already verified the Official Open
cloud slot, timing, producer provenance, child hashes, and execution-admission
boundary. The E2E cloud runner discarded that return value before creating the
PREOPEN stage result. Consequently, the stage result/commit hash proved that a
PREOPEN run occurred, but did not expose which admitted cloud slot authorized
the run.

## Bounded remediation

- The validated materializer return now carries the exact admitted evidence:
  session, slot, slot-manifest SHA, source-manifest SHA, expected and actual
  producer capture-code refs, producer runner/event, scheduled and source
  capture timestamps, capture lag, producer capture-only admission marker,
  downstream `execution_admitted`, and the prospective admission window.
- `run_e2e_paper_cloud_v1.py` passes that return value into the PREOPEN stage
  result. A PREOPEN run with no admitted Open records
  `official_open_cloud_admission: null`; it never claims execution admission.
- Stage-result creation and replay validation fail closed when an explicit
  admission object is malformed, has a session/slot/hash/ref/timestamp/lag
  mismatch, or does not identify the scheduled capture-only producer path.
- The existing create-only result object remains referenced by its exact SHA
  in the immutable stage commit. `CloudPaperArchive.existing_commit()` reads
  and verifies that result and the runtime snapshot, so the persisted
  admission identity is covered by the existing commit/replay chain.
- Genuinely older PREOPEN results without this new field remain readable for
  compatibility, but absence is not treated as an admission claim.

No Official Open admission rule, authority, timing window, producer behavior,
PaperState behavior, execution timing, or retroactive guard was changed.

## Tests

Added synthetic coverage for:

1. successful PREOPEN capture preserving the exact materializer return in the
   stage result and replaying the same provenance; the idempotent retry keeps
   the same stage commit;
2. persisted admission identity tampering failing closed through the immutable
   result SHA;
3. waiting/no-Open PREOPEN returning `null` admission and creating no terminal
   stage commit.

Validation performed after the final executable change:

- focused cloud tests: 38 passed;
- E2E/Official Open regression group: 152 passed;
- full pytest: 882 passed, 0 failed, 0 skipped;
- full-suite warnings: 3 pre-existing `FutureWarning`s in curated identity and
  tradability-anchor tests;
- `py_compile` for the changed runtime and runner: PASS;
- import smoke for both modules: PASS;
- YAML parse for 3 workflow files: PASS;
- `git diff --check`: PASS.

## Boundary

No provider/network request, R2/live-storage operation, scheduler mutation,
model fit/rescore, realized/protected outcome access, merge, or counter change
was performed.
