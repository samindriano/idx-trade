# IDX-Trade Real Classifier Admission Audit V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **REAL INPUT ADMISSION FAIL-CLOSED / NO STATE ENVELOPE FABRICATED**

## Scope

This check exercised the candidate's existing
`classify_legacy_evidence` admission boundary against one actual representative
row/object from every real input class admitted into the shadow census. It used
only immutable copies. It did not construct a migration envelope, infer state,
write provenance, create V2 state, activate anything, or run replay.

The classifier accepts only the exact canonical schema
`idx_trade_legacy_execution_evidence_v1`. A market/model/CA/anchor input must
be rejected before the migration shape classifier is invoked.

## Results

| Real input class | Representative copied artifact | Result | Source SHA-256 |
|---|---|---|---|
| Session manifest | `sessions/2026-09-16/manifest.json` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `27912cb5b6a8e04608e0a44bf2e9f8eb8e207cf0492585d1eb9421a2340d7119` |
| Model input | `sessions/2026-09-16/model_input.parquet` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `f5d39e7ee642f376ee9b50949a4fe77adfceda607eb436e304592e538fb3efde` |
| Session evidence | `sessions/2026-09-16/session_evidence.parquet` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `aa86b96e88311891acfe6f48bf3190344ff4ead0caf231a32119b4eb08549639` |
| CA event registry | `corporate_actions/idx_actions.csv` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `40c0ade2a3d2f4a73483d7016c61eef751eda961ead3f9c6a6cfaa7217a20aa6` |
| Execution-anchor input | `execution/idx_execution_anchors.csv` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `06fc978b939d1de51a435b2c85bbd14a66274a7664ecdbf720f22309cd0d9aba` |
| Historical calendar | `sessions/exchange_sessions.csv` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `3a3bdb6db642e26eaee9b5d9f85b0e1ac16e9d6a70ea3ddd60c0d032e99c6279` |
| Official Open metadata | `forward_open_archive_windows_20260810/forward_open_archive/latest_run.json` | `MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL` | `c9bc5aa4fbb129ea274e13037a9f7f39ce9c0cd8a7718d0a37c3db040347d786` |

The classifier rejected all seven representatives with
`MIGRATION_COMPATIBILITY_PAYLOAD_NOT_CANONICAL`. No input row was force-fit
into a legacy execution-evidence envelope.

## Interpretation

This is an admission-boundary result, not a claim that one representative row
is the entire migration census. The complete census remains in the real
classification registry, which records zero real paper-state candidates and
classifies the observed classes as input-only/unavailable. The admission check
proves that those observed input classes cannot be silently routed into the
legacy execution-evidence classifier without an exact state envelope.

`REAL_CLASSIFIER_ADMISSION = PASS FAIL-CLOSED; REAL_MIGRATION = BLOCKED BY ABSENT STATE`.
