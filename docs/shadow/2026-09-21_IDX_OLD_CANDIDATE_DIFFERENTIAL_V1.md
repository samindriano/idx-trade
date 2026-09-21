# IDX-Trade Old Runtime versus Candidate Differential V1

Date: 2026-09-21 (Asia/Jakarta)

Status: **STATIC/SYNTHETIC EVIDENCE ONLY; REAL DIFFERENTIAL BLOCKED**

## Runtime identities

| Surface | Identity |
|---|---|
| Active scheduled runtime | `32eaaa8e50d0521de7faef98faa8081219bc667b` |
| Retained reliability integration | `402fca4b27e91cf8c82d21ff1394ba2d6da73656` |
| Candidate code tested earlier | `66140b05872e60191ae4090811f168aaef6d71a7` |
| Shadow documentation branch | `codex/idx-shadow-runtime-precanary-20260921` |

## Candidate-only commit sequence

1. `1a99ab3d` — record runtime lineage and extraction contract.
2. `37a214d3` — extract hardened contracts and state integration.
3. `370c6e9d` — bind controller recovery and phase entrypoints.
4. `c602017f` — add migration compatibility and V1/V2 config mode gates.
5. `25b69a17` — record synthetic rehearsal matrix.
6. `66140b05` — add shadow migration rehearsal.

## Differential status

| Differential question | Result |
|---|---|
| Does the active task still point at the old pinned checkout? | Yes, observed read-only |
| Was the active checkout changed? | No |
| Were real state artifacts loaded by both runtimes? | No; no eligible state population was found |
| Was old-vs-candidate output equality measured on real inputs? | No |
| Was candidate synthetic behavior tested? | Yes, in the preceding adoption packet |
| Can the candidate be promoted from this record? | No |

The real differential is blocked because the input pair needed for an
old-versus-candidate comparison is absent. Source-level similarity and
synthetic tests cannot substitute for artifact-level equivalence.
