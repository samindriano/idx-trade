# PRESERVE_FROZEN_SCIENCE_DECOUPLE_RUNTIME

Date: 2026-08-29

This checkpoint records the activation-readiness bridge for the accepted Path-A
population gate. It does not authorize production activation, deployment,
workflow dispatch, provider access, outcome access, PaperState mutation, or
counter mutation.

## Boundary

The shared `listed_to` field is compatibility and veto evidence only. It must
never rewrite the shared frozen V4-X1 scorer population. Path-A is the
superseding runtime/science boundary: it can admit a session only when the
runtime identity and tradability evidence are provably compatible, and it
blocks before scorer entry otherwise.

The historical checkpoint
`2026-08-27_E2E_SECURITY_MASTER_ACTIVATION_PROVENANCE_V1.md` is retained
unchanged. Its older statement about propagating explicit current `listed_to`
into the clean scorer overlay is superseded by this boundary.

## Runtime tradability bootstrap

The outer V2 operational adapter now runs a create-only bootstrap after the
runtime Security Master refresh and before the canonical clean EOD pipeline.
It discovers the three canonical runtime artifacts using the same candidate
and ranking semantics as frozen `forward_monitoring`, validates their canonical
schemas, preserves valid existing runtime evidence byte-for-byte, and seeds a
missing family only from the pinned repository seed. Ambiguous, malformed,
missing-seed, or immutable-conflict cases fail closed.

The bootstrap reports `TRADABILITY_RUNTIME_READY` with per-family resolution,
source/runtime paths and hashes, row counts, code commit, and explicit
outcome/provider/PaperState/counter guards. Empty coverage and anchor seeds
remain empty; they do not claim complete coverage or same-session observation.
Path-A continues to bind the selected runtime artifact hashes in its
attestation.

No CloudInputBundle role was added because the seed artifacts are already in
the pinned code checkout. Snapshot creation and restore carry the materialized
files through the existing runtime roots.
