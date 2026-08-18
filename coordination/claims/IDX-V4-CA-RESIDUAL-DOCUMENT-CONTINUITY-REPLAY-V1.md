# Claim — IDX-V4-CA-RESIDUAL-DOCUMENT-CONTINUITY-REPLAY-V1

Status: `PREPARED_LOCAL_CLAIM_REQUIRED_BEFORE_EXECUTION`

Owner: `ChatGPT/V4-CA-Residual-Continuity-Review` -> local operator/Codex

Branch: `data/idx-v4-ca-residual-document-continuity-replay-v1`

Scientific/result parent: `data/idx-v4-ca-residual-document-semantics-v1@67fc2c7f3bef7feee4c95890ea4c074ffb373712`

## Scope

Command-only continuation of the already completed Residual Document Semantics V1 Stage A. The prior Stage-B attempt failed before continuity evaluation because the handoff named a non-existent external filename `corporate_action_event_evidence.csv`.

Repository provenance proves the intended immutable input is the promoted original V4 CA gate artifact:

`docs/artifacts/ranking_v4_ca_continuity_gate_v1/event_family_evidence.csv`

Its parent manifest identifies the output as `event_evidence` with SHA-256:

`4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

This is exactly the SHA pinned by the frozen `run_v4_ca_event_window_support.py` parent runner. Therefore this continuation changes only the path/name used to identify the already pinned bytes; it does not substitute evidence or change semantics.

## Boundaries

- Do not rerun Stage A.
- Do not patch source/config/tests.
- Do not call any provider/network source.
- Do not change event semantics, evidence admission rules, 90% gate, universe, folds, or target contract.
- Do not access R5/R10, ranks, model, predictions, performance, protected outcomes, or fresh-forward outcomes.
- Execute Stage B exactly once from a fresh output root after exact SHA checks.
- Stop after Stage B regardless of verdict.

Canonical `origin/main:coordination/TEAM_STATUS.md` was inspected before preparation and the parent residual-document lane is `REVIEW`; no separate active residual-continuity replay lane was observed. Because the shared ledger is large and GitHub connector mutation would require unsafe full-file replacement, the local operator must add/update the canonical continuation lane to `ACTIVE` before execution, then `REVIEW` with the exact result.