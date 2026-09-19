# Future Evaluation Packet V2 Contract Closure — Result V1

Date: 2026-09-19 (Asia/Jakarta)
Lane: `codex/alpha-available-data-20260919`
Verified source baseline: `731591e6`
Verdict: `PASS_STATIC_CONTRACT / NO-GO_FOR_REENTRY`

## Purpose

An independent read-only re-entry audit identified stale attestation and
contract gaps in the V1 packet. This closure adds a V2 packet and a
machine-readable contract without changing the protected candidate budget,
opening targets, or changing any canonical/production state.

## Closure implemented

- Direct SHA-256 bindings for panel, financial bundle, official sessions,
  tradability anchors, guarded features, Stage-A manifest, corrected code, and
  protocol.
- Exact panel/feature row counts and key digests.
- Candidate-specific feature-missingness rules, including an explicit
  `BLOCKED_C3_PIT_COVERAGE` gate with `execute=false`.
- Candidate rank tie method, percentile convention, score direction, and
  deterministic Top-30 ticker tie-break.
- Hash-bound structural/PIT/CA/capacity evidence checklist.
- Explicit one-shot, purge, bootstrap, friction, and fail-closed admission
  requirements.
- A verifier that checks all explicit files and the V2 packet text without
  reading protected targets or outcomes.

## Independent verification

`research/verify_alpha_future_evaluation_packet_v2.py` returned `PASS` with all
checks true:

- source, manifest, implementation, and protocol hashes matched;
- panel and feature artifacts both had `981,940` rows;
- panel and feature key digests both equaled
  `a883c33301605209f3802054a38e1231b1a89d3820e79f3a55bebc7657237fa3`;
- key sets were equal;
- C3 execution was fail-closed;
- packet required clauses, ranking, one-shot, and admission preconditions
  passed;
- worktree was clean at verification time.

The outcome-blind target firewall also returned `PASS` for the verifier,
contract, and verification output. No provider/network import, protected path,
target, outcome, cloud, incumbent-predictive, or canonical mutation was used.

## Artifact hashes

- V2 packet: `alpha_future_evaluation_packet_v2.md` — SHA-256
  `44fb9b2202a120076bb5fb40610a30baaf9ff3515d3df9efdb1a58b32862c049`.
- Machine contract: `alpha_future_evaluation_packet_v2_contract.json` — SHA-256
  `3f46b1d810928f50c1c85fa76146dff881cdd38bc7f4e4315d2862de7c9dbfd8`.
- Verifier code SHA-256:
  `28d73ae0277b030668d0ad98b0d99dc71b8a5c249725d282d9c7d75e2eceb062`.
- Verification output SHA-256:
  `20fe7c5138275c4491c3c20785504e6cb0cf24a07ee80c4dfce733d960ea19bc`.
- Firewall output SHA-256:
  `71ea4f84dee8effbd2b7b8484546c7ce2fdf7f06859449a034b654d6fd2d7fed`.

All outputs are in the isolated external staging root:

`D:\Documents\Project\idx-alpha-available-data-staging-20260919\stage-a-final-guarded\20260919T-finalized-guarded\`

## Disposition

This closes the static packet-contract gaps but does not clear the scientific
admission blocker. The packet remains:

`SPECIFICATION_ONLY / BLOCKED_BY_DATA_ADMISSION`

No candidate is `READY_FOR_REENTRY`; C3 remains explicitly disabled. A fresh
independent Data QA admission artifact is still required before any protected
target read. The stale V2 audit is preserved as historical evidence and is not
used as the current attestation.
