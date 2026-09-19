# Alpha Research Lane Integrity Attestation Result V1

Date: 2026-09-20 (Asia/Jakarta)  
Lane: `codex/alpha-available-data-20260919`  
Baseline: `58f094b8b59b8933bee6cf2f9996f433a57391a4`  
Attestation implementation: `76064de20abeedf1636f13c1e8f1ba0858e02505`

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

## Latest rerun — 2026-09-20

The same verifier was rerun after the packet-contract hardening commits. The
reference HEAD for that rerun was `7c0605c052e24d5912a0cc28eb477f068076488b`;
it returned `PASS` on all 10 checks. The staging root contained 157 files with
filename digest
`bf5c6f077f07039a3d4bdaebfa6b608b6dec56885167fcb0e2b3ef9b3f525aa6`, with no
protected-looking filename and all scope flags false. This remains process-
scope evidence only, not proof of runtime access absence.
