# Handoff

from: Codex/Scientific-Integrity-Audit
to: ChatGPT independent reviewer
task_id: IDX-REPOSITORY-SCIENTIFIC-INTEGRITY-AUDIT
model_used: Luna xhigh root; prior five read-only auditors preserved from Sol HEAVY run
reasoning_level: xhigh
source_repository: C:\Users\Sam\.codex\worktrees\idx-scientific-integrity-audit-v1
source_commit: 612c11cdde5a942428fe74e3059811480fc0ceb2
branch: codex/scientific-integrity-audit-v1
head_commit: pending documentation commit
scope: Repository-wide outcome-blind scientific-integrity and reproducibility audit; no experiment rerun or protected-outcome access.
files_changed:
  - docs/checkpoints/2026-08-13_REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT_RECOVERY.md
  - docs/checkpoints/2026-08-13_REPOSITORY_SCIENTIFIC_INTEGRITY_AUDIT.md
  - coordination/handoffs/IDX-REPOSITORY-SCIENTIFIC-INTEGRITY-AUDIT.md
findings:
  - Overall verdict: NO-GO_FOR_REPRODUCIBLE_RESEARCH_RELEASE.
  - Confirmed fail-open paths include textual boolean coercion, malformed finite dates becoming open-ended, conflicting duplicate last-write-wins, missing provenance fingerprints, mutable manifest replacement, incomplete PIT observation-domain validation, source-authority/status gaps, and empty-month calendar completion.
  - Canonical EOD task is installed/Ready, but its executing branch lacks accepted O2.1 and Reliability V1 sidecar modules; future automatic sidecar production is not established.
  - V2, V3-B, and O2 model hashes and feature-order hashes checked against external runtime evidence and matched frozen values.
  - Historical decision chains remain coherent; no verdict reversal was found.
  - Documentation/lineage contains stale branch snapshots, ambiguous Stockbit verification anchoring, unresolved handoff head placeholders, and outdated project-context claims.
decisions_made:
  - No model, data, provider, scheduler, forward-runtime, or outcome-lock semantics were changed.
  - All executable findings overlapping active EOD/provenance/forward-evaluator lanes are marked COORDINATE_WITH_ACTIVE_LANE.
  - Existing Stage-5 holdout remains consumed and was not reopened.
decisions_needed:
  - Independent ChatGPT review should decide whether to authorize owner-scoped remediation lanes for strict parsers, immutable bundle publication, canonical release/sidecar integration, and provenance/environment enforcement.
blocking_risks:
  - Current generic data foundation is not safe to call PIT/reproducible because several ambiguous inputs can pass.
  - Accepted sidecar artifacts exist, but scheduled canonical production is not proven.
  - Dependency and imported-source lineage are not repository-locked/enforced.
  - Current baseline has a storage-test expectation mismatch: prior targeted run reported 39 passed / 1 failed.
validation_run:
  - Read latest origin/main TEAM_STATUS at 7436c213c625ea3856b8376e74c5927ff84a7eea.
  - Existing five auditor outputs synthesized without respawn.
  - Direct read-only reproductions confirmed textual False -> True/ACTIVE, malformed listed_to -> LISTED, duplicate conflicting OHLCV last-row retention, and missing source fingerprint -> None.
  - External V2/V3-B/O2 model and manifest hashes matched frozen constants.
  - No provider call, experiment rerun, model fit, scoring, panel write, or protected outcome access.
recommended_next_action: Independent ChatGPT review; then assign strict data/provenance fixes to the active owners and separately reconcile canonical forward sidecar integration. Do not merge this audit branch into main automatically.
