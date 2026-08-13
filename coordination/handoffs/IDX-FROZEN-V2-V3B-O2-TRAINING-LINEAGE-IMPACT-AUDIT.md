# Handoff

from: Codex/Frozen-Lineage-Impact-Audit
to: MAIN / ChatGPT independent review
task_id: IDX-FROZEN-V2-V3B-O2-TRAINING-LINEAGE-IMPACT-AUDIT
model_used: Codex Luna xhigh root with four read-only Luna xhigh workers
reasoning_level: xhigh
source_repository: C:\Users\Sam\OneDrive\Documents\Project\idx-trade
source_commit: a22c87cf7cef8708d4b0de77923460a26715c253
branch: codex/frozen-lineage-impact-audit-v1
head_commit: pending documentation commit
scope: Forensic read-only impact audit of the exact frozen historical V2, V3-B, and O2 training lineage against accepted repository P1 fail-open risks.
files_changed:
- docs/checkpoints/2026-08-13_FROZEN_V2_V3B_O2_TRAINING_LINEAGE_IMPACT_AUDIT.md
- coordination/handoffs/IDX-FROZEN-V2-V3B-O2-TRAINING-LINEAGE-IMPACT-AUDIT.md
findings:
- Frozen model, table, panel, calendar, security-master, Open coverage, Open provenance, and O2 bundle hashes match documented values.
- V2 and V3-B use the exact 292,633-row / 737-ticker population; O2 is the exact 278,168-row / 729-ticker subset with common-support SHA 716bed364b5ba0dcb034f335bc7b09b4abac23eb1236a7c718fe6e0f6a78577a.
- KOCI has a panel row on 2023-10-06 but listed_from is 2023-10-07. The row is included in pre-filter causal feature construction and changes the retained KOCI row and market context at session 613. O2 inherits KOCI 2023-11-02 in common support.
- The V3-B checkpoint's "non-finite values: 0" statement conflicts with raw-table null counts; the frozen imputer explains the expected missingness. This is documented as a measurement-definition inconsistency only.
- Current final row dates map to the official calendar and listing intervals, but this does not clear upstream PIT/tradability authority or publication-history gaps.
decisions_made:
- V2 verdict: TRAINING_LINEAGE_IMPACT_FOUND.
- V3-B verdict: TRAINING_LINEAGE_IMPACT_FOUND.
- O2 verdict: TRAINING_LINEAGE_IMPACT_FOUND.
- No remediation of model/data semantics was performed because a repair would require a separately authorized, preregistered reproduction.
- No provider, network, outcome, holdout, prospective archive, retraining, refit, or rescore work was performed.
decisions_needed:
- ChatGPT independent review must decide whether to authorize a separate PIT-safe lineage remediation/reproduction.
- Do not reuse current frozen model verdicts as if this audit had repaired or refit them.
blocking_risks:
- Confirmed KOCI PIT contamination in causal historical feature construction.
- Source authority, full tradability-domain evidence, raw-source fingerprint completeness, and immutable publication history remain incomplete.
- Existing repository fail-open paths remain owned by active EOD/provenance lanes.
validation_run:
- Direct read-only artifact SHA, schema, row identity, calendar, listing-boundary, duplicate-key, and provenance scans completed.
- No source-code utility or model code changed; no pytest run was required for this documentation-only checkpoint.
recommended_next_action: Stop for ChatGPT review. If approved later, create a new frozen remediation specification; do not refit or reinterpret current models in this lane.
