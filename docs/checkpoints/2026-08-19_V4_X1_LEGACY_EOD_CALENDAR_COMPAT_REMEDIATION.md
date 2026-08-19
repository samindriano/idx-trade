# V4-X1 Legacy Canonical-EOD Calendar Compatibility Remediation

Date: 2026-08-19 Asia/Jakarta
Status: IMPLEMENTED_LOCAL_VALIDATION_PENDING
Branch: `integration/v4-x1-eod-auto-score-v1`

## Trigger

Post-merge runtime smoke of the accepted canonical EOD adversarial hardening failed closed on canonical session `2026-08-10`.

Local forensic evidence established:
- registry snapshot/evidence/manifest hashes all match their current bytes exactly;
- the legacy manifest does not declare modern raw/index/OHLCV sidecars;
- the declared capture-time calendar SHA-256 `9dde2787c9a2e4d57267efcc1db594ef339c027ab858a88f18eb767135be010c` no longer exists anywhere under the runtime root;
- the current shared calendar path has later bytes, so the failure is a legacy provenance-parent compatibility issue, not canonical market-data corruption.

## Remediation

The accepted `canonical_eod_calendar_parent_attestation_v1` implementation is vendored byte-identically from accepted branch `integration/canonical-eod-calendar-parent-attestation-v1@32c30d17c7a2d1d5f434f9f6df0c7fb88e2b13ae`.

The V4-X1 automation wrapper now uses a process-local compatibility shim. The global hardening verifier is unchanged.

Order of acceptance:
1. modern strict verifier;
2. legacy accepted artifact contract + byte-identical declared calendar parent;
3. immutable strict calendar-parent attestation for an unrecoverable declared calendar parent.

All paths require the registry's snapshot/evidence/manifest bytes to remain exact. Any tamper, missing proof, invalid proof, or failed strict verification remains fail-closed.

A one-shot writer `scripts/create_v4_x1_legacy_calendar_attestation.py` can create only the accepted immutable attestation using the exact accepted bridge calendar SHA-256 `51d36148c692e8dd4921ef923e3670c95abb3b2597bc1a94fb42397d15b91b7e`. It performs zero provider calls and does not rewrite the canonical session.

No scheduler deployment is authorized until focused tests, attestation creation/verification for `2026-08-10`, and the merged-branch runtime smoke all pass.
