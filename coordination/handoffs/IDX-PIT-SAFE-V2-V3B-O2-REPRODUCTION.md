# Handoff

from: Codex/PIT-Safe-Lineage-Reproduction  
to: MAIN / ChatGPT independent review  
task_id: IDX-PIT-SAFE-V2-V3B-O2-REPRODUCTION  
model_used: Codex Luna xhigh root with bounded Luna xhigh workers  
reasoning_level: xhigh  
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`  
source_commit: `cb198437940d1846c311482353cab7579f1511b4`  
branch: `codex/pit-safe-v2-v3b-o2-reproduction-research-v1`  
head_commit: pending final documentation commit  

## Scope

Fresh historical replay only, after the corrected H10 boundary audit. No
provider calls, protected fresh-forward outcome access, canonical model
overwrite, forward counter, calibration, execution-grade promotion, or model
deployment work.

## Inputs

External corrected input root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_v2_v3b_o2_reproduction_v1_20260813_002_fast_h10`

- fast-H10 SHA: `a447b3f2208cbc320f7ec7cfa16c3dbb51107286891deca130f2fb848895b677`;
- corrected V2 table SHA: `b27a603cea39298f18996629a16f25990d3d04422b12ccb5d9bd1e45dbb34af8`;
- corrected V3-B table SHA: `7faf7f68b78dff336a908a69e8b02f6b0f741434b4ada6e17c6b1ef8d9385753`;
- corrected O2 table SHA: `8b1f6c917c013a6fb9cb5733d8096b45e0b5712dfa318ad49ca7f9ca43321585`;
- corrected V2 key SHA: `79d33b233f65b282189917c7226e979956da7f0599a5ba484d82a154ed1ea826`;
- corrected O2 key SHA: `77dbe5aaa32fa7e35779f273bc09501140e1a1363861aa262567f59354dd0644`;
- immutable panel SHA: `67d3d2b528c362137e3036ddddcdbc414b09dc15c392af67c2f4ff796c459b76`.

## Runtime

Replay root:
`D:\Documents\Project\idx-trade-data-gate-20260808v\pit_safe_historical_replay_v1_20260813_001`

Exactly these models were fit using the same frozen six folds and H10 labels:

- V2: `V1_HGB_CONTROL`, `LOGISTIC_XS`, `HGB_XS`, `HGB_XS_MARKET`,
  `PAIRWISE_LOGISTIC_XS`;
- V3-B: common-support baseline and
  `V3-B-STRUCTURE-LITE-V1-CANDIDATE-005`;
- O2: common-support baseline and `O2_OPEN_GEOMETRY`.

Results:

- V2 selected historical champion: `HGB_XS_MARKET`;
- V3-B: `V3_FINAL_STRUCTURE_LITE_LATE_DEV_FAIL_RETAIN_V2`;
- O2: `O2_SURVIVOR` on corrected historical development rows only;
- no new canonical model lineage or prospective counter was created.

The full metric tables and exact paired fold evidence are in
`docs/checkpoints/2026-08-13_PIT_SAFE_V2_V3B_O2_REPLAY_RUNTIME.md` and the
external artifact manifest. Manifest SHA:
`9ed7079a510e2e5e070211e69ab9f811fb9ced51e72230e53e28de20d63b874f`;
72/72 artifact hashes verified.

## Validation

- focused replay tests: `4 passed`;
- full pytest: `494 passed, 0 failed`, four existing warnings only;
- `git diff --check`: PASS before documentation commit;
- fresh-forward outcomes accessed: `false`;
- provider calls: `false`;
- execution-grade promoted: `false`;
- canonical models overwritten: `false`.

## Decisions and blockers

- Old V2/V3-B/O2 remain immutable `LEGACY_CONTAMINATED_REFERENCE`: useful
  historical evidence of the contaminated lineage, not canonical PIT-safe
  release artifacts.
- Corrected inputs remain `PIT-SAFE-RECONSTRUCTION-V1`.
- V3-B is not accepted on the corrected lineage because the exact late paired
  gate fails at V2F5/V2F6; do not rescue or tune it.
- O2 historical survival does not authorize forward scoring or a new counter.
- A new PIT-safe model identity should only be created after independent review
  decides whether this replay is accepted as the preregistered clean historical
  development lineage.

## Recommended next action

Independent ChatGPT review of the checkpoint and external metrics. If accepted,
freeze the clean historical decision separately from the legacy models; do not
start forward scoring or overwrite the existing O2 prospective diagnostic in
this handoff.
