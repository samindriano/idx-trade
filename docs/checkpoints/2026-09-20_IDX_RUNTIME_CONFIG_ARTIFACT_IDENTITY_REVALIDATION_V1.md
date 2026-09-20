# IDX-Trade — Runtime Config / Artifact Identity Revalidation V1

Date: 2026-09-20
Lane: isolated `codex/alpha-available-data-20260919`
Status: `CURRENT_HEAD_GAP_RECONFIRMED / NO_RUNTIME_CHANGE`

This checkpoint revalidates the earlier runtime-config lineage finding against
the newer pinned runtime HEAD. It is a read-only source audit; it does not load
live configuration, execute a controller, modify artifacts, or touch production,
cloud/capture/telemetry, canonical data, or protected outcomes.

## 1. Current pinned evidence

- Runtime worktree: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade-runtime\forward-e2e-operational`
- HEAD: `402fca4b27e91cf8c82d21ff1394ba2d6da73656`
- `e2e_paper_orchestration_v1.py` SHA-256:
  `D10ACE3F01E407ED8198460D5571F26E92107F681F3268AD60BE1D42CC081EEC`
- `e2e_paper_runtime_config_v1.py` SHA-256:
  `DF1E88C4B1F994FC44514A3910E5F066AEE4754260E8C7A05E75C4550969631D`
- `e2e_paper_runtime_config_v2.py` SHA-256:
  `0907F0FD02AF7F61E48959C7F1318A0C6559EF78BA9F34C7DDFC5FD494C356E6`

Probe: `research/idx_runtime_config_artifact_lineage_probe_v1.py`  
Test: `tests/test_idx_runtime_config_artifact_lineage_probe_v1.py`

Focused result: `1 passed`; `py_compile` and `git diff --check` passed.

## 2. Revalidation result

| Check | Result |
|---|---|
| Runtime config loader exposes `config_sha256` and `runner_sha256` | `PRESENT` |
| Runtime config V2 carries both fields | `PRESENT` |
| Current orchestration exposes `prepare_post_eod`, `execute_preopen`, and `_execution_plan_payload` | `PRESENT` |
| Current orchestration source contains `config_sha256` / `runner_sha256` artifact fields | `ABSENT` |
| Current prepared/execution artifact identity therefore binds full config/runner identity | `NO` |

The previous finding is therefore not stale-only evidence. The config loader is
hash-aware, but the orchestration artifact serializer/API does not carry those
identity fields into the prepared or completed execution lineage at this HEAD.

## 3. Blast radius and boundary

The gap is an artifact-lineage and reproducibility risk, not evidence that a
live configuration changed. A run can retain valid score/EOD/Open/CA/state
parents and recomputed plan hashes while the exact external config or runner
identity remains absent from the durable prepared/execution identity.

The evidence does not justify claiming that a particular production run was
contaminated. It does justify keeping full runtime-config lineage
`NO-GO` until the stage handoff and artifact schema bind and compare the exact
config/runner identity.

No implementation was authorized or applied.

## 4. Verdict

`RUNTIME_CONFIG_LOADER_PINNED = YES`

`PREPARED_EXECUTION_CONFIG_IDENTITY = ABSENT`

`RUNTIME_CONFIG_IDENTITY_CERTIFICATION = NO-GO`

This is a current-HEAD revalidation of the earlier checkpoint, not a retry of a
live run.
