# IDX Decision V3 Graded Evidence Structural Replay Runner V2 — Handoff

Date: 2026-08-21 Asia/Jakarta

Status: `IMPLEMENTED_AWAITING_CI_AND_AUDIT_NO_REPLAY`

Branch: `research/idx-decision-v3-graded-evidence-structural-replay-runner-v2`

Rule ID: `V4_X1_DECISION_V3_GRADED_EVIDENCE_V2`

Frozen contract canonical SHA-256: `4d16f2f8ca1a274e7d98cc8be24daaa0f4eb77bfc6e56ecf90c6f42f1b13239f`.

The runner implementation is complete enough for CI and independent adversarial review. The historical 600-OOS source has not been executed.

Runner audit must explicitly verify:

1. preregistration ↔ machine profile ↔ replay-contract ↔ runtime gate parity;
2. canonical contract hash and comparator pins;
3. strict parquet projection and absence of H5/H10/return/target/outcome reads;
4. CLI authorization ordering;
5. exact bootstrap, score-session adjacency, continuous state and no fold reset/pre-roll;
6. independent A/B/C vacancy priority and permission validation;
7. Tier D prohibition and Tier B/C soft-replacement prohibition;
8. severe >50 immediate exit and no second consecutive 21..50 retention;
9. unchanged churn/holding/rank/capacity hard thresholds;
10. Tier-C lifecycle diagnostics and high-churn attribution remain descriptive only;
11. two-pass determinism uses identical in-memory source and identical policy;
12. fail-closed staged output and manifest hashing;
13. no historical replay, returns/PnL, provider/network, protected/fresh-forward access, or alpha retune.

Only an accepted runner audit may authorize one local historical replay using the frozen CLI interlock token.
