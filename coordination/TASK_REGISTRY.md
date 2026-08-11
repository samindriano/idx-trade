# IDX Trade task registry

Only MAIN changes task ownership, dependencies, parallel grouping, model routing, or status.

`docs/CURRENT_STATUS.md` is authoritative when older registry state conflicts.

| Task ID | Owner | Scope | Model / reasoning | Base source commit | Branch/worktree | Parallel group | Dependencies | Status |
|---|---|---|---|---|---|---|---|---|
| IDX-PRV2-PREFLIGHT-TESTS | VALIDATION | Verify current-checkout import resolution and run/assess the full repository test suite required before the frozen Path Risk V2 discovery run | Luna xhigh / xhigh | current branch HEAD | source checkout or isolated validation worktree | `PRV2-PREFLIGHT` | current source state | READY |
| IDX-PRV2-PREFLIGHT-AUDIT | VALIDATION | Read-only audit that frozen PR-002/PR-003 definitions, immutable V1 joined table identity, F1-F4-only discovery boundary, and F5/F6 seal still match controlling specs/checkpoints | Luna xhigh / xhigh | current branch HEAD | read-only | `PRV2-PREFLIGHT` | current source state | READY |
| IDX-PRV2-DISCOVERY-RUN | EXPERIMENT | Execute exactly one frozen PR-002/PR-003 Path Risk V2 F1-F4 development run using the authorized handoff; no new candidate; no F5/F6 | Luna xhigh / xhigh | post-preflight same source state | authoritative local execution checkout | `SEQUENTIAL_EVIDENCE_RUN` | both preflight checks PASS | BLOCKED_ON_PREFLIGHT |
| IDX-PRV2-RESULT-REVIEW | MAIN / VALIDATION | Verify evidence against frozen gates and record winner/fail-close without touching F5/F6 | Luna xhigh; Sol High only for decision-changing ambiguity | discovery run result | read-only review | `POST_RUN_REVIEW` | discovery result | BLOCKED_ON_RUN |
| IDX-FORWARD-OUTCOME-BLOCK | MAIN | Preserve the 100-session H10-mature post-2026-07-31 fresh-forward one-shot boundary and realized-outcome lock | n/a | final V3-B freeze | policy guard | `SEQUENTIAL_GUARD` | final alpha freeze | ACTIVE_GUARD |

## Closed state

- V3/V4 alpha architecture search: `CLOSED`.
- final alpha ranker: `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`.
- Path Risk V1 PR-001: `FAILED_CLOSED`; no rescue.
- Path Risk V2 PR-002/PR-003: only frozen current discovery candidates.

## Parallel launch rule

`IDX-PRV2-PREFLIGHT-TESTS` and `IDX-PRV2-PREFLIGHT-AUDIT` may run together when checkouts/ownership remain non-overlapping. The evidence-producing discovery run itself stays serialized until both preflight checks pass.

For future meaningful tasks, MAIN should explicitly create the execution frontier and launch independent READY tasks in the same parallel group together rather than processing them serially by habit.

Do not mark scientifically dependent later experiments READY before the current evidence exists.
