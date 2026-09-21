# IDX-Trade Shadow Runtime Review Index V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **DOCUMENTATION PUSH / SHADOW QUALIFICATION NOT COMPLETE**

This index is the review entry point for the isolated shadow-runtime lane. It
records the real retained-artifact census performed so far and links the
earlier authoritative-runtime adoption packet. It does not claim that a real
runtime migration, replay, fallback rehearsal, canary, or production action
was executed.

## Lane identity

- Branch: `codex/idx-shadow-runtime-precanary-20260921`
- Base before this documentation commit: `221e95640be73dd6f4887a27863ca93c2fd1b0d6`
- Candidate code under review: `66140b05872e60191ae4090811f168aaef6d71a7`
- Candidate base: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- Active operational checkout: `32eaaa8e50d0521de7faef98faa8081219bc667b`
- Active operational task source was not modified.

## Read first

The inherited adoption packet has a separate doc-only audit:
2026-09-21_IDX_ADOPTION_DOCUMENTATION_AUDIT_V1.md.

The actual copy attestation is in:
2026-09-21_IDX_IMMUTABLE_SHADOW_INPUT_MANIFEST_V2.md.

The copy-only schema and hash verification is in:
2026-09-21_IDX_REAL_COPY_SCHEMA_CENSUS_V1.md.

The complete 29-session discovery copy and expanded root census is in:
2026-09-21_IDX_FULL_SESSION_SHADOW_CENSUS_V1.md.

The per-file source/copy hash table is in:
2026-09-21_IDX_FULL_SESSION_COPY_ATTESTATION_V1.md.

The real score validation and isolated timestamp fix are in:
2026-09-21_IDX_REAL_SCORE_VALIDATION_V1.md.

The copied-session legacy shape and ambiguity check is in:
2026-09-21_IDX_REAL_LEGACY_AMBIGUITY_HUNT_V1.md.

1. `2026-09-21_IDX_SHADOW_QUALIFICATION_MASTER_DOSSIER_V1.md`
2. `2026-09-21_IDX_REAL_RUNTIME_ARTIFACT_CENSUS_V1.md`
3. `2026-09-21_IDX_IMMUTABLE_SHADOW_INPUT_MANIFEST_V1.md`
4. `2026-09-21_IDX_PRECANARY_GAP_REGISTER_V1.md`
5. `2026-09-21_IDX_CONTROLLED_CANARY_DESIGN_V1.md`

## Durable shadow records

The pre-copy record remains V1; the actual copy attestation is V2.

- `2026-09-21_IDX_REAL_RUNTIME_ARTIFACT_CENSUS_V1.md`
- `2026-09-21_IDX_FULL_SESSION_SHADOW_CENSUS_V1.md`
- `2026-09-21_IDX_FULL_SESSION_COPY_ATTESTATION_V1.md`
- `2026-09-21_IDX_IMMUTABLE_SHADOW_INPUT_MANIFEST_V1.md`
- `2026-09-21_IDX_REAL_MIGRATION_CLASSIFICATION_REGISTRY_V1.md`
- `2026-09-21_IDX_OLD_CANDIDATE_DIFFERENTIAL_V1.md`
- `2026-09-21_IDX_REAL_REPLAY_MATRIX_V1.md`
- `2026-09-21_IDX_REAL_LEGACY_AMBIGUITY_HUNT_V1.md`
- `2026-09-21_IDX_SHADOW_RECOVERY_MATRIX_V1.md`
- `2026-09-21_IDX_FORWARD_FALLBACK_REHEARSAL_V1.md`
- `2026-09-21_IDX_SHADOW_IDENTITY_INTERFACE_V1.md`
- `2026-09-21_IDX_PRECANARY_GAP_REGISTER_V1.md`
- `2026-09-21_IDX_CONTROLLED_CANARY_DESIGN_V1.md`
- `2026-09-21_IDX_SHADOW_ACTIVE_FRONTIER_HANDOFF_V1.md`
- `2026-09-21_IDX_SHADOW_NO_RETRY_LOG_V1.md`

## Earlier adoption records

The preceding candidate-only work is retained under `docs/adoption/`, including
the master dossier, lineage matrix, extraction map, migration matrix,
multi-session synthetic rehearsal, entrypoint/config matrix, rollback matrix,
independent challenge, active frontier, and no-retry log. Those records are
not replaced by this shadow packet; this packet adds the real retained-runtime
qualification boundary.

## Review headline

The real retained inventory contains 29 session-date directories and a real
forward-monitoring corpus. The active E2E runtime contains operational metadata,
logs, and a no-prepared-execution terminal state, but no retained paper-state
population was found in the bounded artifact census. Therefore the real
migration and real replay gates are blocked by missing eligible state, not
green-lit by synthetic tests.

No provider checkout, provider call, scheduler mutation, cloud/R2 mutation,
canonical-data rewrite, counter reset, protected-outcome access, alpha change,
or live runtime write belongs to this branch.
