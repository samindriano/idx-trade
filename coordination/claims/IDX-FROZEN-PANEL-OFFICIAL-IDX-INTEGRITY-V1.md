# IDX Frozen-Panel Official IDX Integrity Audit V1

Status: `ACTIVE`
Owner: `ChatGPT/Frozen-Panel-Official-IDX-Integrity`
Branch: `audit/frozen-panel-official-idx-integrity-v1`
Date: 2026-08-20 Asia/Jakarta

## Scope

Independent, outcome-blind forensic audit of the frozen signal-research panel against already-captured official IDX Stock Summary evidence.

This lane intentionally does **not** duplicate the active price-basis remediation scope. In particular it does not repeat the remediation branch's bounded 1,657-row Volume/Value audit or Open/HLC recertification. Its distinct scope is:

- full-panel Volume parity against official IDX on every exact overlap;
- official-session/calendar witness diagnostics;
- census of official ACTIVE + valid-HLC ticker/session rows absent from the frozen panel, emphasizing interior gaps;
- bounded in-memory downstream impact of any full-panel Volume mismatch on `relative_volume_20` representation;
- field-level provenance-schema diagnostics.

## Guardrails

No provider/network calls, model fit/scoring, target/outcome access, protected-forward access, canonical panel mutation, remediation, or refit authorization.
