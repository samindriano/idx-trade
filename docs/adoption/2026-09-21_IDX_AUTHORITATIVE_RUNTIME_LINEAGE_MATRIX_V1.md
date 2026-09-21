# Authoritative Runtime Lineage Matrix V1

Date: 2026-09-21 (Asia/Jakarta)

This is a read-only adjudication of the runtime lineage relevant to the
adoption candidate. It records what is active, retained, divergent, and
candidate-only. It does not authorize source or operational changes.

## Ref matrix

| Ref | Role | Relation | Classification |
|---|---|---|---|
| 32eaaa8e50d0521de7faef98faa8081219bc667b | pinned Windows E2E checkout | ancestor of 402; actual task source | ACTIVE_OPERATIONAL |
| 402fca4b27e91cf8c82d21ff1394ba2d6da73656 | forward reliability integration | 12 commits ahead of 32 | RETAINED_RUNTIME / CANDIDATE_BASE |
| 8ceec523d49500949b5ecf46e3b862cd4eb1c4fd | completed contract hardening | 109 commits ahead of 402 | IMMUTABLE_DEVELOPMENT_EVIDENCE |
| 8b5bc6db1a4d89ca0fb2a49760899d3f18453f23 | current origin/main | 671 commits only on 402 side and 763 only on main side | COORDINATION/CLOUD MAIN; NOT SILENTLY ADOPTED |
| d007077694ad861abd86f21cc8f42f7575837298 | system frontier challenge | research checkpoint | RESEARCH EVIDENCE ONLY |

The exact graph counts were independently verified:

    32eaaa8e... -> 402fca4b...       0 / 12
    402fca4b... -> 8ceec523...       0 / 109
    402fca4b... <-> origin/main      671 / 763
    8ceec523... <-> origin/main      780 / 763

## Active operational checkout audit

| Surface | Read-only observation | Authority classification |
|---|---|---|
| IDXTrade-E2E-Paper | Enabled; action invokes C:UsersSam.codexworktreesidx-e2e-baseline-paper-pinned-20260824scriptsun_e2e_paper_scheduled_v2.py; checkout HEAD is 32eaaa8e | ACTIVE_OPERATIONAL |
| IDXTrade-E2E-OfficialOpen | Enabled; wrapper at the runtime root delegates to run_official_open_capture_v2.ps1 in the same pinned 32eaaa8e checkout | ACTIVE_OPERATIONAL |
| IDXTrade-ForwardEOD | Enabled; separate idx-v4-x1-clean-prospective-score-v1 checkout and data root | SEPARATE_ALPHA_RUNTIME; OUT OF SCOPE |
| IDXTrade-ForwardOpenArchive | Disabled; retained legacy path | PARKED |
| forward-e2e-operational checkout | Branch runtime/idx-e2e-baseline-paper-v1, HEAD 402fca4b, clean, behind its remote integration ref | RETAINED / NOT TASK-BINDING |
| origin/main cloud workflow | Workflow pins implementation ref 045e25a1 and uses an external provider checkout | CLOUD LINEAGE; NOT THIS CANDIDATE |

The OfficialOpen wrapper is important: the file is stored under the runtime
root, but its repo variable points to the pinned 32eaaa8e checkout. The
runtime-root location must not be mistaken for the executable source identity.

## The 12 commits from 32eaaa8e to 402fca4b

| Commit | Change type | Runtime behavior | Evidence/capture behavior | Adoption determination |
|---|---|---|---|---|
| 7d6a53f4a54349bfc57d947b74006788e1a31f39 | Official Open transport/replay implementation | YES: bounded retries, replay verification, malformed direct evidence fail-closed | YES: Official Open evidence integrity | CARRY FORWARD; required for the retained reliability contract |
| 839fa77b1e1c4bc6351679ef99d3e4bdd87689ab | checkpoint/handoff docs | NO | NO | EVIDENCE-ONLY; carry as provenance, not runtime dependency |
| 1ffeadb01159ce1cf8f6882757c01f133907b37b | evidence-health module/script/tests | Diagnostic runtime only; no execution science | YES: outcome-blind artifact health | CARRY FORWARD for adoption diagnostics and consumer compatibility |
| 5842d1db36c6f4ab393f5fcb91234acb4f8f7281 | evidence-health handoff pin | NO | NO | EVIDENCE-ONLY |
| 708ae759110e2beb5606b1168cdf7468cabb4401 | evidence-health attestation hardening | Diagnostic semantics changed | YES: hash/session/guard attestations | CARRY FORWARD; required for trustworthy readiness diagnostics |
| 3bef0060ffaf7a480d9a627c24d492340442bd99 | evidence-health remediation pin | NO | NO | EVIDENCE-ONLY |
| e0e8a52d059594d3a974672944fe4a8fc7444cfc | scheduler runner binding | YES: runner invokes remediated Official Open runtime | YES: installed entrypoint identity | CARRY FORWARD; required to avoid legacy v1 dispatch |
| b9d3d267f87823fef36e7dc5318fbe6ae9935a59 | scheduler remediation pin | NO | NO | EVIDENCE-ONLY |
| cb0f9f5680b608be16e4fd09999ae2da8991e4a4 | merge marker | NO new tree content beyond parents | Lineage marker only | PRESERVE AS HISTORY; no separate adoption payload |
| 2d57192b917213647fd87c4ff748af586469d35b | E2E integration lineage docs | NO | NO | EVIDENCE-ONLY |
| 9a2d5f45ab8ee7d79d8714139a25b9ee11f663d5 | merge marker | NO new tree content beyond parents | Lineage marker only | PRESERVE AS HISTORY; no separate adoption payload |
| 402fca4b27e91cf8c82d21ff1394ba2d6da73656 | final reliability closeout docs | NO | NO | EVIDENCE-ONLY; base pin and operational evidence |

The four implementation-bearing commits are therefore not obsolete merely
because the active task remains on 32eaaa8e. The task is behind the retained
reliability integration; that is a compatibility/adoption gate, not permission
to edit the task.

## Runtime-file disposition versus origin/main

The reliability files introduced or modified by 402 are deleted from current
origin/main:

- src/idx_trade/official_open_capture_runtime_v2.py
- src/idx_trade/official_open_evidence_v1.py
- src/idx_trade/forward_evidence_health_v1.py
- scripts/report_forward_evidence_health_v1.py
- scripts/run_official_open_capture.ps1
- their focused tests and reliability checkpoints

This is a REMOVED_FROM_MAIN / SUPERSEDED-LINEAGE relationship, not proof
that the 402 implementation is invalid. Current main has a different cloud
execution surface and must be reviewed separately.

## Decision

402fca4b is selected as the isolated candidate base. The selection does not
alter the active 32eaaa8e tasks. A future operational adoption must explicitly
reconcile the task checkout, config hash, runner identity, and the candidate
contract stack in a separate authorization.
