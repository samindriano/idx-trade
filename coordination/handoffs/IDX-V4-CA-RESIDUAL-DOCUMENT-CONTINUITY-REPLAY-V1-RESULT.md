# Handoff

from: Codex
to: ChatGPT reviewer
task_id: IDX-V4-CA-RESIDUAL-DOCUMENT-CONTINUITY-REPLAY-V1
model_used: Codex Luna xhigh
reasoning_level: xhigh
source_repository: samindriano/idx-trade
source_commit: `ef1beef0f3b91f15772c10b5dbf44756c5399788`
branch: `data/idx-v4-ca-residual-document-continuity-replay-v1`
head_commit: result documentation commit follows the frozen Stage-B anchor
scope: Stage-B-only offline continuity replay using promoted Stage-A evidence

## Preflight

- parent result `67fc2c7f3bef7feee4c95890ea4c074ffb373712`: present
- prior event evidence SHA: `4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`
- Stage-A manifest SHA: `6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`
- fresh output root: clear before execution
- Stage A rerun: `NO`
- provider calls: `0`

## Stage-B result

Exactly one replay completed:

- verdict: `V4_CA_EVENT_WINDOW_CONTINUITY_STILL_BLOCKED`
- corporate_action_continuity_certified: `false`
- relevant/exact/schedule-required: `80 / 42 / 38`
- schedule-required tickers: `34`
- frozen dates passing H5/H10/consensus `>=90%`: `0 / 0 / 0`
- minimum H5/H10/consensus rates: `0.8237179487 / 0.8216560510 / 0.8216560510`
- overlay Stage-A counts: exact non-blocking `22`, exact transition `1`, conflicts `0`, unresolved `38`

## Promoted files

- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/MANIFEST.json`
- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/summary.json`
- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/event_semantics_audit.csv`
- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/schedule_evidence_needs.csv`
- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/v4_frozen_continuity_per_date_event_window.csv`
- `docs/artifacts/v4_ca_residual_document_continuity_replay_20260818_v2/residual_document_continuity_overlay.json`

Manifest file SHA: `89c3bcf45d115d1ae0f8e6cc9ac4cb8e11672d56220f08ded34c39347fcb0827`.

Full continuity ledger remains external. No source/config patch, provider,
Stage-A rerun, target/model, performance, protected outcome, or fresh-forward
access occurred. Update the matching TEAM_STATUS row to `REVIEW`, push, and
stop.
