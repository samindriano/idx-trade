# IDX Decision V3 Graded Evidence Implementation V2 — Claim

Date: 2026-08-21 Asia/Jakarta

Status: `REVIEW`

Owner: `ChatGPT/Decision-V3-Graded-Evidence-Implementation-V2`

Branch: `research/idx-decision-v3-graded-evidence-implementation-v2`

Controlling preregistration: `research/idx-decision-v3-graded-evidence-prereg-v2` at `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`.

Implementation checkpoint: `docs/checkpoints/2026-08-21_DECISION_V3_GRADED_EVIDENCE_IMPLEMENTATION_V2.md`.

Validated implementation code HEAD: `c89ecb4f88e98cc23c140f15dee13ca423a92f5c`.

Final validation: GitHub Actions run #1120, `504 passed`, `26 warnings`, `0 failed`.

Scope completed:

- exact Decision V3 Graded Evidence V2 state machine implemented;
- Decision V2 implementation remained immutable;
- V4-X1 adapter/profile binding added;
- focused, adversarial, boundary and property-style tests added;
- V4-X1 non-bootstrap runtime state hardened to require exact rule binding;
- no historical replay performed.

Next boundary:

- independent implementation audit on `audit/idx-decision-v3-graded-evidence-implementation-v2`;
- if accepted, only replay-runner preparation becomes authorized;
- historical 600-OOS replay remains unauthorized until the future runner is separately implemented and audited.

Still explicitly out of scope:

- historical 600-OOS Decision V3 replay;
- alternative thresholds or policy variants;
- returns/PnL/outcome access;
- H5/H10 rescue;
- alpha refit/retune;
- sizing/execution/paper activation.
