# E2E Paper Cloud-First Orchestration V1

Status: `IMPLEMENTATION_REVIEW`
Branch: `integration/e2e-cloud-first-orchestration-v1`
Base: `origin/integration/idx-e2e-baseline-paper-v1@8a96a3d9caebfbd2c0235234e9394afc04693efa`
Main audit anchor: `origin/main@acfdc3d383e8fcbf01aac4cb050be78361b5bb0d`

## Objective

Move routine E2E PAPER orchestration from a Windows-only local runtime toward a
GitHub Actions/R2 execution surface while preserving the existing controller,
PaperState, Decision V2, Sizing V1, Execution V1, Official Open authority, and
outcome-blind rules. This change is an adapter/control-plane foundation; it is
not a claim that the live cloud deployment is armed.

## What was implemented

`src/idx_trade/e2e_paper_cloud_runtime_v1.py` provides:

- a create-only local store and an S3/R2 store using conditional
  `If-None-Match: *` writes;
- hash-verified input manifests with portable relative paths;
- exact official trading schedule plus source-document verification;
- deterministic ZIP runtime snapshots with stable root names and no secret,
  outcome, or credential paths;
- immutable stage result/snapshot/commit objects;
- replay verification of every child object before `ALREADY_COMMITTED` is
  returned;
- idempotent known-key recovery of the first valid Official Open slot from the
  existing `official-open-v1` archive;
- no-op handling before any provider work on a planned-schedule holiday.

`scripts/run_e2e_paper_cloud_v1.py` is a thin adapter over the existing engines:

1. verify the cloud input bundle and planned schedule;
2. restore the latest committed runtime snapshot to fixed ephemeral paths;
3. for `POST_EOD`, call the existing clean EOD pipeline and then the existing
   dual-calendar controller;
4. for `PREOPEN`, rehydrate verified Official Open evidence and call the same
   dual-calendar controller;
5. upload a deterministic runtime snapshot and write the stage commit marker
   only for terminal controller states.

The workflow is intentionally one serialized control-plane job with six
triggers. It is a candidate implementation workflow; scheduled Actions only
run after the thin launcher is promoted to the default branch and pinned to
this implementation commit. The three later triggers are idempotent POST_EOD
retry windows so a delayed upstream EOD/score does not wait until the next
calendar day.

The cloud runner rejects an explicit session date unless it is today's Jakarta
date. This keeps workflow dispatch from becoming a historical backfill or
retroactive execution surface. Before the existing EOD engine is called, the
runner verifies the provider checkout, pinned provider commit, executables, CA
capture script hash, and attestation configuration through the accepted
operational guard.

## Exact cloud object contracts

The private E2E R2 prefix is `e2e-paper-v1`. The input manifest key is
`inputs/manifest.json`, schema `idx_trade_e2e_cloud_inputs_v1`. It must include
hash-pinned objects for:

- execution schedule attestation;
- the official schedule source document;
- accepted clean panel;
- accepted clean security master;
- the accepted clean model `MANIFEST.json` and all model files in its declared
  parent directory;
- optional initial CA journal, if the dynamic CA contract requires one.

The manifest itself is only accepted with portable relative paths. Schedule
attestations containing an absolute local source-document path are rejected;
the official source document must be included as a separate immutable object.

The model bundle is explicit rather than inferred from the manifest's parent:
the input manifest must declare `model_control_h5`, `model_control_h10`,
`model_challenger_h5`, `model_challenger_h10`, and `model_fit_log` in addition
to `model_manifest`. Missing any child is a fail-closed input error.

The runtime snapshot uses fixed Linux paths so absolute paths already embedded
by the existing E2E artifacts remain stable after rehydration:

```text
/tmp/idx-trade-e2e-paper-runtime
/tmp/idx-trade-e2e-forward-runtime
/tmp/idx-trade-e2e-official-open
/tmp/idx-trade-e2e-ca
/tmp/idx-trade-e2e-inputs
```

This is a portability constraint, not a new scientific path or data source.

## Boundaries and unresolved activation gates

No provider request, live R2 request, model fit/rescore, or protected outcome
access was performed while building this branch. The implementation cannot be
called live-ready until all of these are separately proven:

1. the immutable input manifest and the large model/panel/security-master
   objects are provisioned under private R2;
2. the pinned `nichsedge/idx-bei` checkout and its dependencies are available
   in Actions;
3. the default-branch thin launcher checks out this implementation SHA and
   the cloud workflow is enabled there;
4. the current `official-open-v1` workflow is independently reviewed for its
   existing artifact-verification/retention limitations; this branch consumes
   its evidence but does not modify or duplicate that capture system;
5. one future real session completes through cloud post-EOD, PREOPEN/Official
   Open reconciliation, and PaperState recovery with no Windows task or manual
   command. Until then the verdict remains
   `CLOUD_RUNTIME_IMPLEMENTATION_READY_LIVE_PROOF_PENDING`.

An existing committed stage is only returned as already committed after its
result and snapshot children, stage status, guard flags, schedule hash, and
input-manifest hash are verified. A same-session run with a changed schedule or
input manifest fails closed instead of silently accepting the old stage.

The main branch currently contains the Official Open workflow but not the E2E
controller implementation. The integration and main refs therefore must not
be merged wholesale: the implementation is pinned as a dependency, just as
the accepted Official Open cloud capture currently is.

## Tests

Focused cloud control-plane tests cover create-only storage, complete model
input roles, input/schedule hashes, portable schedule source binding,
deterministic snapshot/restore, stage child verification/idempotent commit,
identity conflicts, Official Open artifact rehydration from a later slot,
holiday no-op, waiting/missing Open, retroactive-date rejection, dependency
preflight ordering, controller-crash recovery, and forbidden snapshot paths.
The focused cloud suite is 13 passed on the current implementation. Existing
E2E orchestration and dual-calendar tests remain the scientific authority and
are not replaced.
