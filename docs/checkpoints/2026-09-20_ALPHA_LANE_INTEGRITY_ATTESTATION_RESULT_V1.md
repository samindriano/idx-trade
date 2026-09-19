# Alpha Research Lane Integrity Attestation Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Baseline: `58f094b8b59b8933bee6cf2f9996f433a57391a4`  
Attestation implementation: `22d4b1c15fd455859d6b1deb5ec328f8c70dff8b`

## Result

`PASS — ISOLATED RESEARCH PROCESS SCOPE`

The verifier confirms:

- expected branch and worktree path;
- baseline commit exists and is an ancestor;
- every continuation delta since the baseline is under
  `docs/checkpoints/` or `research/`;
- clean worktree;
- expected isolated staging root;
- 150 staging files present with no protected-looking filename;
- outcome/provider/target/cloud/canonical-mutation flags are false.

The staging filename digest for this run is
`f1d540a724fb56fea1e9dd7523c50f053ea3ff5a9b9d6b5d0cac4a24d219bd36`.

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
