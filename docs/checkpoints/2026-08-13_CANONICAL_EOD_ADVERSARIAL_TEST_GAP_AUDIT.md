# Canonical EOD Adversarial Test-Gap Audit

Date: 2026-08-13 (Asia/Jakarta)
Status: implementation complete; independent ChatGPT review required
Branch: `codex/idx-eod-adversarial-tests-v1`
Canonical runtime base: `b94b272eddede0432e2fbe4acb2915e57a716bcb`
Recovered-state checkpoint: `45a553f` (`chore(eod): checkpoint recovered adversarial hardening`)

## Scope and safety boundary

This was a bounded engineering-only audit of the canonical IDXTrade EOD
runtime and its official source/artifact validation. No provider or data
network calls, model execution, protected outcome access, Stage 5 rerun,
forward outcome inspection, retraining, or scientific/model behavior change
was performed.

The v0/v1 split was intentional: v0 was created from `main` for the shared
coordination claim and TEAM_STATUS edit; v1 was created from the canonical EOD
runtime branch at `b94b272` for implementation and tests. The v0 local
coordination edit was preserved and was not used to overwrite v1.

## Confirmed hardening completed

- EOD catch-up now verifies the returned `DATA_READY.session_date` exactly
  matches the requested official session and stops on no chronological
  progress instead of looping.
- Session calendars reject invalid or duplicate dates; timezone-aware dates
  are resolved in Asia/Jakarta before session normalization.
- Canonical session completion and stale recovery verify manifest status,
  exact session, outcome-lock flags, core and context artifact paths/hashes,
  official source dates, raw JSON shape, model-input/evidence uniqueness, and
  exact OHLCV sibling reconciliation. Missing/partial/corrupt `DATA_READY`
  rows are failed closed as `INCOMPLETE_ARTIFACTS`.
- Stale session reconciliation uses the original lease owner and heartbeat in
  the update predicate, preventing a dead worker from overwriting a newer
  lease.
- Raw and downloaded provider rows reject duplicate session rows and filename
  or requested-ticker identity conflicts. Non-finite OHLC/volume values are
  rejected.
- Ambiguous tied canonical table artifacts fail closed instead of being
  selected by filename order.
- Model recovery validates `DONE` manifest status, session, model ID,
  generation, fingerprint, artifact path/hash, score schema, exact session,
  duplicate keys, row counts, and protected outcome flags. Model fan-out also
  refuses an integrity-unverified `DATA_READY` input.
- O2 counter writes are atomic and retrying the same last official session is
  idempotent; a non-owner cannot release the model-worker lock.
- Official Stock Summary and Index Summary adapters reject null identities,
  non-integral/boolean/non-finite completeness counts, non-finite numeric
  index metrics, and duplicate normalized stock rows. The JSON session parser
  rejects malformed/invalid rows rather than silently dropping them.

## Validation

- Focused EOD/source suite: **69 passed**.
- Full repository suite: **286 collected, 286 passed**.
- Full-suite warnings: 3 existing `FutureWarning` messages in curated identity
  and tradability-anchor reconstruction; no failures.
- `git diff --check`: PASS.

## Findings coordinated with active lanes

The following were observed but deliberately not duplicated or broadened here:

- Official-calendar completeness/provenance policy and source-registry
  contradiction handling: `COORDINATE_WITH_ACTIVE_LANE` with the active
  scientific-integrity and canonical data-source/provenance lanes.
- Deep outcome-marker ordering/hash validation and forward evaluator contract:
  `COORDINATE_WITH_ACTIVE_LANE` with the active Forward 100-session evaluator
  review/remediation lane. This audit only validates the outcome-lock fields
  already present in canonical EOD/model manifests.
- Model output directory naming does not include the fingerprint. Current
  recovery refuses a fingerprint/manifest mismatch, but a future multi-
  fingerprint artifact namespace change should be separately reviewed with
  the model-runtime owner; no scientific behavior was changed here.

## Decision

Engineering hardening is ready for independent ChatGPT review on this branch.
The runtime remains outcome-blind and no readiness/promotion decision for any
model or data source is made by this checkpoint.
