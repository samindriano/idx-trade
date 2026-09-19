# Alpha Research Lane Integrity Attestation Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Baseline: `58f094b8b59b8933bee6cf2f9996f433a57391a4`  
Attestation implementation: `f40fd48a2e4ee7c8084659b4da9b5c082dc8f22b`

## Result

`PASS — ISOLATED RESEARCH PROCESS SCOPE`

The verifier confirms:

- expected branch and worktree path;
- baseline commit exists and is an ancestor;
- every continuation delta since the baseline is under
  `docs/checkpoints/` or `research/`;
- clean worktree;
- expected isolated staging root;
- 153 staging files present with no protected-looking filename;
- outcome/provider/target/cloud/canonical-mutation flags are false.

The staging filename digest for this run is
`5c7e71ceb44098e66bbda1a38e9f13a24ddfd2c8f1216141255f2fc6939d05da`.

## Scope limitation

This is a process-scope attestation for branch, path, worktree, and staging
boundaries. It does **not** independently prove that a runtime never accessed
protected data. The absolute target firewall and no-outcome boundary remain in
force, and this artifact does not authorize protected evaluation or production
mutation.

## Reusable control

Implementation: `research/verify_alpha_research_lane_integrity_v1.py`. Future
continuation milestones should rerun it with the last trusted lane baseline and
write the result only inside the isolated staging root.
