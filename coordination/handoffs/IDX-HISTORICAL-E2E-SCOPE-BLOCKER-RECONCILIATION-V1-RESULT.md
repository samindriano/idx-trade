# Handoff

from: Codex
to: ChatGPT / MAIN
task_id: IDX-HISTORICAL-E2E-SCOPE-BLOCKER-RECONCILIATION-V1
model_used: GPT-5
reasoning_level: high
source_repository: `C:\Users\Sam\OneDrive\Documents\Project\idx-trade`
source_commit: `13a854538f8cdfd0d8b033d45dede48fd44e9fac`
branch: `research/idx-historical-e2e-replay-v1`
head_commit: `8289a64ab0392ecc42c6f2a4f7442d83f0912347`
scope: outcome-blind support-run reconciliation only
files_changed:
  - `docs/checkpoints/2026-08-24_HISTORICAL_E2E_SCOPE_BLOCKER_RECONCILIATION_V1.md`
  - this handoff

findings:
  - 376/600 sessions have complete positive Open support for all Decision V2
    BUY intents; the longest consecutive run is 34.
  - CA exposure continuity is strict-resolved for 4,471/5,693 rows (78.55%).
  - 164/600 dates reach the CA >=90% gate; the longest run is 15.
  - Open-ready and CA>=90% intersect on 107 dates; the longest run is 9.
  - The dividend corpus is independently incomplete after an official IDX
    HTTP 403 boundary and cannot provide market-wide no-event proof.

decisions_made:
  - No performance, NAV, Monte Carlo, labels, or protected outcomes were read.
  - No frozen gate, target, evaluator, or live runtime was changed.
  - No shorter segment or relaxed threshold was substituted for 6x100.

decisions_needed:
  - Independent review whether to authorize new official CA/dividend source
    remediation, or close this historical replay as data-blocked.

blocking_risks:
  - Current frozen artifacts cannot produce the required 6x100 eligible
    session scope even before the missing dividend proof is resolved.

validation_run:
  - Offline pandas diagnostics over the accepted CA exposure ledger and
    strict-scope JSON.
  - No provider calls and no protected-outcome access.

recommended_next_action: Do not run historical metrics or Monte Carlo. Require
  a separately reviewed evidence-remediation contract before additional
  provider activity.
