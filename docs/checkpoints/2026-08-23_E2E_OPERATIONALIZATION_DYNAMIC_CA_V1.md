# E2E Paper Operationalization — Dynamic CA Phase Capture V1

Date: 2026-08-23 (Asia/Jakarta)
Branch: `integration/idx-e2e-baseline-paper-v1`
Implementation commit: `0e1fa9c2a03dc2b87c22c10c91524a2d034b7af6`

## Scope

This checkpoint records an outcome-blind implementation increment for the
accepted IDX-Trade E2E PAPER controller. It does not change V4-X1, Decision V2,
Sizing V1, Execution V1, target definitions, or protected outcomes.

The live controller can now obtain a separate, immutable V1.2 corporate-action
attestation for each exact `POST_EOD` / `PREOPEN` decision window. The static
attestation path remains supported for deterministic replay and legacy
bootstrap configurations.

## Changes

- Added `scripts/capture_forward_ca_idx_bei.py` using the pinned
  `nichsedge/idx-bei` checkout at provider commit
  `75d6c0f74fa360d225794c70c383348977de6798`.
- Captured source legs are limited to official IDX issued-history,
  issuer-announcement, and monthly all-market calendar endpoints.
- Raw JSON is hash-recorded in an external phase manifest. The final phase
  directory is published only after the manifest passes the existing
  `forward_ca_attestation_v1.verify_phase_manifest` gate; failures remain in a
  `.partial.*` staging directory and never appear as a final capture.
- Built V1.2 attestations with timezone-aware UTC capture time, exact phase
  window, required tickers, phase-manifest path/SHA, and evidence rows.
- Updated the operational controller to bind the actual per-window attestation
  into the existing dividend/CA consumers, including the exact next-session
  `through_session` boundary. Existing static attestations remain compatible.
- Updated the external runtime-config loader with fail-closed all-or-none
  dynamic CA fields:
  `ca_attestation_root`, `ca_capture_script`, and
  `ca_capture_script_sha256`.

## Validation

- Focused CA capture/config/controller/attestation tests: PASS (`30 passed`).
- Full repository pytest: PASS; only the repository's existing three pandas
  `FutureWarning`s were emitted.
- `py_compile`: PASS for all changed Python modules/scripts.
- `git diff --check`: PASS.
- No provider capture, model scoring, protected outcome access, or scheduler
  installation was performed in this increment.
- `coordination/TEAM_STATUS.md` was intentionally not modified; only MAIN may
  edit that file.

## Deployment boundary

External runtime config and `IDXTrade-E2E-Paper` Task Scheduler installation
remain pending independent review of this implementation. No static or
synthetic CA artifact is accepted as the live authority. A future deployment
must use an external dynamic config pinned to the final repository HEAD and
capture each exact window through the new collector.

## Decision

`IMPLEMENTATION_PUSHED_REVIEW_REQUIRED`

Next safe action: independent review, then create the external hash-pinned
config and perform only the authorized weekend/no-session deployment smoke
before waiting for the first real weekday cycle.
