# IDX Decision V3 Graded Evidence Structural Replay Runner V2 — Claim

Date: 2026-08-21 Asia/Jakarta

Status: `ACTIVE`

Owner: `ChatGPT/Decision-V3-Graded-Evidence-Structural-Replay-Runner-V2`

Branch: `research/idx-decision-v3-graded-evidence-structural-replay-runner-v2`

Controlling implementation branch: `research/idx-decision-v3-graded-evidence-implementation-v2`.

Controlling rule ID: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`.

Scope:

- freeze the exact structural replay runner/reporting contract before executable runner work;
- implement the pinned 600-session structural replay orchestration without executing it;
- implement strict source projection, exact session adjacency, continuous state and two-pass determinism;
- implement all frozen V3 hard gates and required structural metrics;
- implement Tier-A/B/C/D permission validation, Tier-C lifecycle diagnostics and high-churn mechanism attribution;
- add fail-closed artifact output and execution interlock;
- validate with repository CI;
- perform a separate adversarial runner audit before any historical replay.

Explicitly out of scope:

- no historical Decision V3 600-OOS execution;
- no returns/PnL/outcome access;
- no alternative threshold or policy simulation;
- no H5/H10 rescue;
- no alpha refit/retune;
- no sizing/execution/paper activation.
