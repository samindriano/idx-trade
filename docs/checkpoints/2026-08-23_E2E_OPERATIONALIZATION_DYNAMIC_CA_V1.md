# E2E Paper Operationalization — Dynamic CA Phase Capture V1

Date: 2026-08-23 (Asia/Jakarta)
Branch: `integration/idx-e2e-baseline-paper-v1`
Implementation commits: `0e1fa9c2a03dc2b87c22c10c91524a2d034b7af6`,
`ffd138a2db2df20b3a75703a21bf3b073a1d0b46`,
`6cd9868780692494424016748e443fc6e4744f99`,
`86c608e95404fcf59b367a63b919a0656971fb97`

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
- Phase publication now has a recoverable two-artifact transaction marker. The
  V1.2 attestation is built to a pending immutable file, the final manifest
  path/SHA is bound before publication, and a retry validates exact
  phase/from/through/ticker scope plus the real execution-consumer V1.2
  verifier before clearing `PUBLISH.json`. A crash between the two renames is
  therefore resumable without provider access and cannot be accepted under a
  changed invocation window.
- Built V1.2 attestations with timezone-aware UTC capture time, exact phase
  window, required tickers, phase-manifest path/SHA, and evidence rows.
- The V1.2 builder now requires the raw calendar fingerprint to equal the
  frozen production fingerprint before publication, and publishes the
  attestation through an immutable temporary-file/replace path.
- Updated the operational controller to bind the actual per-window attestation
  into the existing dividend/CA consumers, including the exact next-session
  `through_session` boundary. Existing static attestations remain compatible.
- Updated the external runtime-config loader with fail-closed all-or-none
  dynamic CA fields:
  `ca_attestation_root`, `ca_capture_script`, and
  `ca_capture_script_sha256`.
- Added exact `through_session_date` binding to the durable CA phase sidecar;
  stale same-session attestations for another forward window are rejected on
  reuse.

## Validation

- Focused CA capture/controller/attestation remediation tests: PASS (`24 passed`).
- Focused scheduler contract tests: PASS (`20 passed`).
- Full repository pytest: PASS; only the repository's existing three pandas
  `FutureWarning`s were emitted.
- `py_compile`: PASS for all changed Python modules/scripts.
- `git diff --check`: PASS.
- No provider capture, model scoring, or protected outcome access was
  performed in this increment.
- The external runtime config was created outside Git, but the new task was
  not installed: the final `Register-ScheduledTask` call failed with
  `Access is denied (HRESULT 0x80070005)`. No UAC/security bypass was used;
  no existing task was changed.
- `coordination/TEAM_STATUS.md` was intentionally not modified; only MAIN may
  edit that file.

## Deployment boundary

External runtime config exists under the user-local runtime root and was
repinned to the final branch HEAD before the deployment smoke; any later
repository commit requires another repin.
`IDXTrade-E2E-Paper` Task Scheduler installation remains blocked on legitimate
interactive elevation. No static or synthetic CA artifact is accepted as the
live authority. Deployment must use the external dynamic config and capture
each exact window through the new collector.

The final pre-install smoke on 2026-08-23 returned
`WEEKEND_OR_HOLIDAY_NOOP`, with `provider_calls=false` and
`outcome_access=false`. The task was not registered because
`Register-ScheduledTask` returned `Access is denied (HRESULT 0x80070005)`.

## Decision

`IMPLEMENTATION_REMEDIATED_REVIEWED_SCHEDULER_ELEVATION_REQUIRED`

Next safe action: provide one normal administrator-approved deployment path,
repin the external config to the final repository HEAD, install only the new
task, and perform the authorized weekend/no-session smoke. A weekday capture
and paper cycle remain unproven.
