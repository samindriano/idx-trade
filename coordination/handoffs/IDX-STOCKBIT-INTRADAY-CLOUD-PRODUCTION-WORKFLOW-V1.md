# Handoff

from: Codex
to: MAIN / ChatGPT review
task_id: IDX-STOCKBIT-INTRADAY-CLOUD-PRODUCTION-WORKFLOW-V1
model_used: GPT-5
reasoning_level: high
source_repository: samindriano/idx-trade
source_commit: 18d0206eba3aff591b099a45e8bb64aec4f1c5ed
branch: ops/stockbit-intraday-cloud-migration-v1
head_commit: see final branch HEAD; do not use this field as a self-reference
scope: Add one production GitHub Actions schedule around the existing Stockbit Intraday cloud runner.
files_changed:
  - .github/workflows/stockbit-intraday-cloud-production.yml
  - docs/checkpoints/2026-08-27_STOCKBIT_INTRADAY_CLOUD_PRODUCTION_WORKFLOW.md
  - coordination/handoffs/IDX-STOCKBIT-INTRADAY-CLOUD-PRODUCTION-WORKFLOW-V1.md
findings:
  - Main had no Stockbit Intraday production workflow; only the PR preflight existed.
  - The workflow uses the existing runner/archive and current-date-only guards.
  - Existing Windows fallback and other capture workflows are not modified.
decisions_made:
  - Use weekday GitHub cron slots 18:30/19:30/20:30 Asia/Jakarta.
  - Bind the production checkout and implementation pin to the exact workflow SHA.
  - Restrict manual dispatch to main and explicit slot choices.
decisions_needed:
  - Main integration/merge and exact-current-main CI.
  - Isolated throwaway R2 smoke and read-only accepted-E2E bridge preflight.
  - Single-writer cutover plan and one controlled future-session proof.
blocking_risks:
  - No live production write or scheduler activation is claimed until the above gates pass.
validation_run:
  - Existing Stockbit focused suite and full pytest passed before this workflow-only addition.
  - Workflow YAML and shell mapping require CI validation on the branch.
recommended_next_action: Run exact-head CI plus isolated cloud gates; only then merge and activate from main.
