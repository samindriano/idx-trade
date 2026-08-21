# IDX Decision V3 Graded Evidence Implementation V2 — Claim

Date: 2026-08-21 Asia/Jakarta

Status: `ACTIVE`

Owner: `ChatGPT/Decision-V3-Graded-Evidence-Implementation-V2`

Branch: `research/idx-decision-v3-graded-evidence-implementation-v2`

Controlling preregistration: `research/idx-decision-v3-graded-evidence-prereg-v2` at `e9882e1b436f19e860d826a9c02a6bb3f1d46dcc`.

Scope:

- implement the exact Decision V3 Graded Evidence V2 state machine;
- keep Decision V2 implementation immutable;
- add V4-X1 adapter/profile binding;
- add focused, adversarial and property-style tests;
- validate with repository CI;
- perform a separate independent implementation audit after code is frozen.

Explicitly out of scope:

- no historical 600-OOS Decision V3 replay;
- no alternative thresholds or policy variants;
- no returns/PnL/outcome access;
- no H5/H10 rescue;
- no alpha refit/retune;
- no sizing/execution/paper activation.
