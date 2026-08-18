# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-V4-CA-RESIDUAL-DOCUMENT-SEMANTICS-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `3e99d4a596e3878a6df24d920ed54badd6c3d310`
branch: `data/idx-v4-ca-residual-document-semantics-v1`
head_commit: result documentation commit follows the frozen execution anchor
scope: Stage-2 raw corpus attestation, one offline Stage A, and one exact Stage B attempt

## Validation and attestation

- focused pytest: `23 passed in 0.62s`
- `py_compile`: PASS
- `git diff --check`: PASS
- Stage-2 status: `V4_CA_STAGE2_RAW_CORPUS_ATTESTED`
- Stage-2 candidates/successful/verified paths/provider-failed: `100 / 98 / 97 / 2`
- provider calls in this lane: `0`

## Stage A

Stage A completed exactly once with status
`V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_COMPLETE`:

- candidate rows `241`
- exact non-blocking `22`
- exact transition `1`
- conflicts `0`
- unresolved `38`
- residual events `61`

Promoted Stage-A manifest SHA:
`6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`

## Stage B

The exact Stage-B command was attempted once after Stage A, then stopped
fail-closed because the handoff-required input was missing:

`D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\corporate_action_event_evidence.csv`

The available file is `event_family_evidence.csv`; it was not substituted.
No Stage-B manifest or continuity verdict was produced. Do not infer
continuity certification or run any next-stage V4 work.

## Promoted files

- `docs/artifacts/v4_ca_residual_document_semantics_20260818_v1/MANIFEST.json`
- `docs/artifacts/v4_ca_residual_document_semantics_20260818_v1/summary.json`
- `docs/artifacts/v4_ca_residual_document_semantics_20260818_v1/residual_event_document_evidence.csv`
- `docs/artifacts/v4_ca_residual_document_semantics_20260818_v1/residual_document_audit.csv`
- result checkpoint at `docs/checkpoints/2026-08-18_V4_CA_RESIDUAL_DOCUMENT_SEMANTICS_V1_RESULT.md`

Update only this TEAM_STATUS row to `REVIEW`, push, and stop. No source/config,
provider, target/model, performance, protected-outcome, or fresh-forward work
was performed.
