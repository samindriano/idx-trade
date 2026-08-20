# Claim — V4-X1 Clean Phase-A Open-Lineage Remediation V1

Date: 2026-08-20 (Asia/Jakarta)
Status: `DONE_PHASE_A_ACCEPTED_PHASE_B_PREPARATION_NEXT`
Owner: `ChatGPT/V4-X1-Clean-Phase-A-Open-Lineage-Remediation`
Branch: `research/idx-v4-x1-clean-phase-a-open-lineage-remediation-v1`
Base: `bca6c9cc8e78608cfa97e3c8a8fe96b115877e50`

## Scope

Remediate the Phase-A replay implementation only. Preserve the accepted parent executable-Open evidence on every non-Stage-A Open-remediation identity, and override only the exact accepted Stage-A candidate population (`1,657` rows: `1,655` admitted clean Open + `2` fail-closed unavailable).

The first Phase-A runtime manifest `1dedb76db7c1fc620e4feb286e409d0266bf367581cbf7dab28bc862f298787c` remains immutable forensic evidence and is not reinterpreted as a scientific CA80 failure.

## Frozen implementation

- remediation wrapper: `scripts/run_v4_x1_clean_phase_a_open_lineage_remediation.py`
- wrapper blob: `91ecfd719c04fbd2749d2e1cf0d0f3bc0c2bec9a`
- focused tests: `tests/test_v4_x1_clean_phase_a_open_lineage_remediation.py`
- tests blob: `23268a37c5154895e1ed5a11ac15bb17131697f4`
- machine contract: `config/ranking_v4_x1_clean_phase_a_open_lineage_remediation_v1.json`
- prepared checkpoint: `docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_A_OPEN_LINEAGE_REMEDIATION_PREPARED.md`
- local execution handoff: `coordination/handoffs/IDX-V4-X1-CLEAN-PHASE-A-OPEN-LINEAGE-REMEDIATION-LOCAL-RUNTIME.md`

## Final accepted result

Local validation:

- focused pytest: `17 passed`
- `py_compile`: PASS
- `git diff --check`: PASS

One-shot remediated runtime:

- status: `V4_X1_CLEAN_PHASE_A_STRUCTURAL_REPLAY_COMPLETE_INDEPENDENT_REVIEW_REQUIRED`
- final authoritative manifest SHA-256: `f6b73ebc9f092d1869166de125bbb7afd24a02d3597fa5fa9d6fea8853a70dda`
- Open lineage policy: `PRESERVE_PARENT_EXECUTABLE_OPEN_EXCEPT_ACCEPTED_STAGE_A_CANDIDATES_V1`
- old Stage-C support oracle exact match: PASS
- clean inherited CA80 gate: PASS
- frozen H5 minimum: `0.8396624472573839`
- frozen H10 minimum: `0.8360655737704918`
- frozen consensus minimum: `0.8360655737704918`
- frozen 600 all eligible: PASS
- tail-600 identity unchanged: PASS
- eligible sessions after frozen end: `0`
- all 12 fold/head training sets non-empty: PASS
- all provider/network/target/model/performance/forward/counter/data-mutation safety flags: false

Independent acceptance checkpoint:

`docs/checkpoints/2026-08-20_V4_X1_CLEAN_PHASE_A_OPEN_LINEAGE_REMEDIATION_ACCEPTED.md`

Decision:

`V4_X1_CLEAN_PHASE_A_REMEDIATION_ACCEPTED_PHASE_B_PREPARATION_AUTHORIZED_REFIT_NOT_RUN`

## Prohibited / next boundary

This remediation lane is closed. No further Phase-A replay or rescue is authorized.

Next work must be a separate Phase-B preparation/freeze lane. Until that contract is frozen and reviewed:

- no model refit/scoring/performance;
- no protected/fresh-forward outcome access;
- no forward-counter mutation/reset;
- no CA80/session/universe/feature/model semantic change;
- no V4-X2 mixing;
- no data/provider acquisition.

Canonical `main:coordination/TEAM_STATUS.md` was refetched during independent review. The large shared ledger could not be safely rewritten from this connector without replacing a truncated representation; therefore the canonical remediation row/result still requires a small safe coordination-only update from a local agent before Phase-B execution.
