# Handoff — IDX-V4-CA-RESIDUAL-DOCUMENT-CONTINUITY-REPLAY-V1

from: ChatGPT
to: local Windows operator / Codex
task_id: `IDX-V4-CA-RESIDUAL-DOCUMENT-CONTINUITY-REPLAY-V1`
branch: `data/idx-v4-ca-residual-document-continuity-replay-v1`
parent result: `data/idx-v4-ca-residual-document-semantics-v1@67fc2c7f3bef7feee4c95890ea4c074ffb373712`

## Mission

Run **Stage B only**, exactly once, using the already completed immutable Stage-A evidence bundle. The previous Stage-B attempt failed before continuity evaluation solely because the handoff used the wrong filename for the original V4 CA gate event evidence.

Do not rerun Stage A. Do not patch code/config/tests. Do not access provider/network, target/model/performance, protected outcomes, or fresh-forward outcomes.

## Provenance correction

The intended prior event evidence is the repository-promoted artifact:

`docs/artifacts/ranking_v4_ca_continuity_gate_v1/event_family_evidence.csv`

The original V4 CA gate manifest records its logical output as `event_evidence` and pins SHA-256:

`4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

The frozen `scripts/run_v4_ca_event_window_support.py` parent runner independently pins `prior_event_evidence` to the same SHA. Therefore using the repository path above is an exact byte-identity correction, not source substitution.

## Step 0 — canonical coordination hard gate

Before any local execution:

1. fetch latest `origin/main:coordination/TEAM_STATUS.md`;
2. confirm no newer `ACTIVE` lane owns this exact residual CA continuity replay scope;
3. add/update `V4 CA residual document continuity replay V1` to `ACTIVE`, owner `Codex/V4-CA-Residual-Continuity-Replay`, branch `data/idx-v4-ca-residual-document-continuity-replay-v1`, scope `Stage-B-only replay using hash-pinned promoted event_family_evidence; no Stage-A rerun/provider/target/model/outcome`;
4. push only that coordination update to `main` under the safe shared-file rule.

If an overlapping active lane exists, STOP.

## Step 1 — exact branch and immutable-input preflight

Checkout/pull this branch. Verify it contains parent result commit:

`67fc2c7f3bef7feee4c95890ea4c074ffb373712`

Worktree must be clean before execution.

Verify SHA-256 of:

`docs/artifacts/ranking_v4_ca_continuity_gate_v1/event_family_evidence.csv`

must equal exactly:

`4c9973781a3c254ad5c82d66d7f6f27afc3bc977681015236693b96d7be638b7`

Verify Stage-A root exists:

`D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1`

and its `MANIFEST.json` SHA-256 equals:

`6f2070dbd89307c39579aa9617807c2c8ae746390466476f29504b31ae4988a5`

Also verify the following unchanged external inputs exist; the frozen runner will enforce their hashes:

- continuity ledger: `D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv`
- KSEI census root: `D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1`
- official calendar: `D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv`

Do **not** use the failed/missing name `corporate_action_event_evidence.csv`.

Use a fresh output root. Do not delete or overwrite any earlier failed Stage-B directory:

`D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2`

If this fresh root already exists, STOP and report collision. Do not choose another root without ChatGPT review.

## Step 2 — one exact Stage-B run

From repository root, run exactly:

```powershell
python scripts/run_v4_ca_residual_document_continuity.py `
  --continuity-ledger "D:\Documents\Project\idx-v4-corporate-action-continuity-gate-20260817-v3\v4_frozen_continuity_ledger.csv" `
  --prior-event-evidence "docs\artifacts\ranking_v4_ca_continuity_gate_v1\event_family_evidence.csv" `
  --ksei-census-root "D:\Documents\Project\idx-v4-ksei-ca-history-census-20260817-v1" `
  --official-calendar "D:\Documents\Project\idx-trade-data-gate-20260808v\research_feasibility_1260_20260809\official_exchange_sessions_1260.csv" `
  --document-root "D:\Documents\Project\idx-v4-ca-residual-document-semantics-20260818-v1" `
  --output-dir "D:\Documents\Project\idx-v4-ca-residual-document-continuity-20260818-v2"
```

This is the only authorized continuity execution. STOP after it whether PASS, BLOCKED, or error.

## Step 3 — report/promote only small result artifacts

If Stage B completes and emits a valid result:

- record exact continuity verdict;
- record `corporate_action_continuity_certified`;
- relevant/exact/schedule-required event counts;
- H5/H10/consensus dates passing the frozen `>=0.90` gate;
- minimum H5/H10/consensus continuity rates;
- exact hashes for summary, event semantics, per-date, manifest, and residual overlay;
- provider/model/target/outcome access flags.

Promote only small summary/manifest/per-date/event-semantics/overlay metadata as appropriate. Keep the full continuity ledger external.

If Stage B errors, record the exact first error and STOP. No patch/retry.

Update the canonical TEAM_STATUS continuation row to `REVIEW` with exact result/blocker and push. Keep worktree clean/synced.

## Hard boundaries

No Stage-A rerun, parser change, policy change, source substitution, provider call, threshold change, 610-ticker recrawl, R5/R10, target/rank materialization, model fit, predictions, performance metrics, bootstrap, protected outcomes, or fresh-forward access.