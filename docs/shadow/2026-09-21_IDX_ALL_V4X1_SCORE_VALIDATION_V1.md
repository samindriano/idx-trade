# IDX-Trade All V4-X1 Real Score Validation V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **15 CLEAN SCORE ARTIFACTS PASS / 1 LEGACY MODEL-ID REJECTED / REPLAY BLOCKED**

## Boundary and method

This check used the 16 real V4-X1 score manifests found under the retained
`model_runs` root. Each score artifact was copied to a new isolated shadow
root. Each copied manifest was represented by a derived shadow adapter that
changed only `output.artifact_path` to the hash-identical local copy. Source
manifests and score artifacts were not rewritten.

No provider, protected outcome, counter, scheduler, cloud/R2, paper state, CA
ledger, or live runtime was accessed. The adapter is not a production
manifest.

Shadow root:

`C:\Users\Sam\AppData\Local\IDXTrade\shadow-runtime-precanary-20260921-v4x1-scores`

Copy attestation:

- 16 source manifest/artifact pairs discovered;
- 16 score artifacts copied;
- 16 derived adapters created;
- artifact source/copy SHA mismatches: `0`.

## Candidate verifier result

| Session | Real model id | Rows | Candidate result | Tie rows / reason |
|---|---|---:|---|---|
| 2026-08-19 | `V4_X1_GEOMETRY3_PROSPECTIVE` | 290 | REJECT | legacy model id does not equal clean candidate id |
| 2026-08-21 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 294 | PASS | 96 |
| 2026-08-24 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 292 | PASS | 96 |
| 2026-08-26 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 292 | PASS | 74 |
| 2026-08-28 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 294 | PASS | 99 |
| 2026-08-31 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 294 | PASS | 71 |
| 2026-09-02 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 290 | PASS | 101 |
| 2026-09-04 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 289 | PASS | 103 |
| 2026-09-07 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 289 | PASS | 101 |
| 2026-09-08 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 286 | PASS | 96 |
| 2026-09-09 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 288 | PASS | 106 |
| 2026-09-10 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 291 | PASS | 90 |
| 2026-09-11 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 291 | PASS | 104 |
| 2026-09-14 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 292 | PASS | 83 |
| 2026-09-15 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 294 | PASS | 91 |
| 2026-09-17 | `V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1` | 296 | PASS | 82 |

Aggregate: `15 PASS`, `1 REJECT`, `0 verifier errors`.

The legacy rejection is expected fail-closed behavior, not a candidate
artifact corruption finding: the 2026-08-19 manifest declares
`V4_X1_GEOMETRY3_PROSPECTIVE`, while the candidate contract requires
`V4_X1_CLEAN_GEOMETRY3_PROSPECTIVE_V1`.

## Disposition

`REAL_SCORE_VALIDATION = PASS WITH LIMITATION`.

This closes a real score-artifact validation surface for the 15 clean
candidate-id manifests and records one explicit legacy incompatibility. It
does not establish historical session replay, paper-state migration, CA
composition, old-vs-candidate economics, recovery, or canary readiness. The
absolute-path adapter and unresolved session-calendar lineage remain outside
the production contract.
